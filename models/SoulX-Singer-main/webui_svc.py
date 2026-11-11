import os
import random
import sys
import traceback
import gc
from datetime import datetime
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).parent
os.environ.setdefault("NUMBA_CACHE_DIR", str(ROOT / "outputs" / "numba_cache"))

import gradio as gr
import librosa
import numpy as np
import soundfile as sf
import torch

from preprocess.pipeline import PreprocessPipeline
from soulxsinger.utils.device_utils import empty_device_cache, is_cuda_device, is_directml_device, resolve_device
from soulxsinger.utils.file_utils import load_config
from cli.inference_svc import build_model as build_svc_model, process as svc_process


SAMPLE_RATE = 44100
# The prompt is the timbre reference and Whisper only ever looks at 30 s, so the
# prompt stays capped at 30 s.
PROMPT_MAX_SEC_DEFAULT = 30
# The target may be a whole song: 0 means "no limit" (long targets are converted in
# segments automatically), instead of the old hard 10-minute cut.
TARGET_MAX_SEC_DEFAULT = 0
TARGET_MAX_SEC_CHOICES = (0, 120, 300, 600, 1800, 3600, 7200)

SVC_EXAMPLE_PROMPT_AUDIO = "example/audio/svc_prompt_demo.mp3"
SVC_EXAMPLE_TARGET_AUDIO = "example/audio/svc_target_demo.mp3"

EXAMPLE_LIST = [[
	str(ROOT / SVC_EXAMPLE_PROMPT_AUDIO),
	str(ROOT / SVC_EXAMPLE_TARGET_AUDIO),
	False,
	True,
	True,
	True,
	0,
	32,
	1.0,
	42,
]]

_I18N = dict(
	display_lang_label=dict(en="Display Language", zh="显示语言"),
	title=dict(en="## SoulX-Singer SVC", zh="## SoulX-Singer SVC"),
	prompt_audio_label=dict(en=f"Prompt audio", zh=f"Prompt 音频"),
	target_audio_label=dict(en=f"Target audio", zh=f"Target 音频"),
	prompt_vocal_sep_label=dict(en="Prompt vocal separation", zh="Prompt 人声分离"),
	target_vocal_sep_label=dict(en="Target vocal separation", zh="Target 人声分离"),
	auto_shift_label=dict(en="Auto pitch shift", zh="自动变调"),
	auto_mix_acc_label=dict(en="Auto mix accompaniment", zh="自动混合伴奏"),
	target_max_sec_label=dict(en="Target length limit (seconds, 0 = no limit)", zh="Target 时长上限（秒，0 = 不限制）"),
	device_label=dict(en="Device", zh="Device"),
	fp16_label=dict(en="FP16 (CUDA only)", zh="FP16 (CUDA only)"),
	pitch_shift_label=dict(en="Pitch shift (semitones)", zh="指定变调（半音）"),
	n_step_label=dict(en="n_step", zh="采样步数"),
	cfg_label=dict(en="cfg scale", zh="cfg系数"),
	seed_label=dict(en="Seed", zh="种子"),
	examples_label=dict(en="Reference example (click to load)", zh="参考样例（点击加载）"),
	run_btn=dict(en="🎤Singing Voice Conversion", zh="🎤歌声转换"),
	output_audio_label=dict(en="Generated audio", zh="合成结果音频"),
	warn_missing_audio=dict(en="Please provide both prompt audio and target audio.", zh="请同时上传 Prompt 与 Target 音频。"),
	instruction_title=dict(en="Usage", zh="使用说明"),
	instruction_p1=dict(
        en="Upload the Prompt and Target audio, and configure the parameters",
        zh="上传 Prompt 与 Target 音频，并配置相关参数",
    ),
    instruction_p2=dict(
        en="Click「🎤Singing Voice Conversion」to start singing voice conversion.",
        zh="点击「🎤歌声转换」开始最终生成。",
    ),
	tips_title=dict(en="Tips", zh="提示"),
	tip_p1=dict(
        en="Input: The Prompt audio is recommended to be a clean and clear singing voice, while the Target audio can be either a pure vocal or a mixture with accompaniment. If the audio contains accompaniment, please check the vocal separation option.",
        zh="输入：Prompt 音频建议是干净清晰的歌声，Target 音频可以是纯歌声或伴奏，这两者若带伴奏需要勾选分离选项",
    ),
	tip_p2=dict(
        en="Pitch shift: When there is a large pitch range difference between the Prompt and Target audio, you can try enabling auto pitch shift or manually adjusting the pitch shift in semitones. When a non-zero pitch shift is specified, auto pitch shift will not take effect. The accompaniment of auto mix will be pitch-shifted together with the vocal (keeping the same octave).",
        zh="变调：Prompt 音频的音域和 Target 音频的音域差距较大的时候，可以尝试开启自动变调或手动调整变调半音数，指定非0的变调半音数时，自动变调不生效，自动混音的伴奏会配合歌声进行升降调（保持同一个八度）",
    ),
	tip_p3=dict(
        en="Model parameters: Generally, a larger number of sampling steps will yield better generation quality but also longer generation time; a larger cfg scale will increase timbre similarity and melody fidelity, but may cause more distortion, it is recommended to take a value between 1 and 3.",
        zh="模型参数：一般采样步数越大，生成质量越好，但生成时间也越长；一般cfg系数越大，音色相似度和旋律保真度越高，但是会造成更多的失真，建议取1～3之间的值",
    ),
	tip_p4=dict(
        en="Long audio is now handled for you: a whole song (10+ minutes) can be loaded directly and is converted in 15-30 s vocal segments with crossfaded joins. Only if the timbre still drifts where the pitch range jumps should you try converting in segments.",
        zh="长音频已自动处理：可直接导入整首歌（10 分钟以上），内部会按 15~30 秒的人声分段转换并做淡入淡出拼接；只有在音域剧烈跳变处仍存在音色漂移时，才建议手动分段",
    ),
    tip_p5=dict(
        en="Prompt audio uses its first 30 seconds (the Whisper content encoder only sees 30 s); the target length limit can be set below, 0 means unlimited.",
        zh="Prompt 音频只取前 30 秒（Whisper 内容编码器窗口为 30 秒）；Target 的时长上限可在下方设置，填 0 表示不限制",
    )
)

_GLOBAL_LANG: Literal["zh", "en"] = "zh"


def _i18n(key: str) -> str:
	return _I18N[key][_GLOBAL_LANG]


def _print_exception(context: str) -> None:
	if sys.stderr is not None:
		print(f"[{context}]\n{traceback.format_exc()}", file=sys.stderr, flush=True)


def _get_device(device_choice: str | None = None):
	return resolve_device(device_choice or os.environ.get("SOULX_DEVICE", "auto"))


def _session_dir() -> Path:
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
	return ROOT / "outputs" / "gradio" / "svc" / timestamp


def _normalize_audio_input(audio):
	return audio[0] if isinstance(audio, tuple) else audio


def _trim_and_save_audio(src_audio_path: str, dst_wav_path: Path, max_sec: int | None, sr: int = SAMPLE_RATE) -> None:
	"""Load audio and save as wav, trimming only when ``max_sec`` is positive."""
	audio_data, _ = librosa.load(src_audio_path, sr=sr, mono=True)
	full_sec = len(audio_data) / sr
	if max_sec and max_sec > 0 and full_sec > max_sec:
		audio_data = audio_data[: int(max_sec) * sr]
		print(f"[svc] trimmed {Path(str(src_audio_path)).name}: {full_sec:.1f}s -> {int(max_sec)}s", flush=True)
	dst_wav_path.parent.mkdir(parents=True, exist_ok=True)
	sf.write(dst_wav_path, audio_data, sr)


def _usage_md() -> str:
	return "\n\n".join([
		f"### {_i18n('instruction_title')}",
		f"**1.** {_i18n('instruction_p1')}",
		f"**2.** {_i18n('instruction_p2')}",
	])


def _tips_md() -> str:
	return "\n\n".join([
		f"### {_i18n('tips_title')}",
		f"- {_i18n('tip_p1')}",
		f"- {_i18n('tip_p2')}",
		f"- {_i18n('tip_p3')}",
		f"- {_i18n('tip_p4')}",
		f"- {_i18n('tip_p5')}",
	])


class AppState:
	def __init__(self, device_choice: str = "auto", use_fp16: bool = False) -> None:
		self.device_choice = device_choice or "auto"
		self.device = _get_device(self.device_choice)
		self.use_fp16 = use_fp16 and is_cuda_device(self.device)
		self.preprocess_device = "cpu" if is_directml_device(self.device) else self.device
		self.preprocess_pipeline = PreprocessPipeline(
			device=self.preprocess_device,
			language="Mandarin",
			save_dir=str(ROOT / "outputs" / "gradio" / "_placeholder" / "svc"),
			vocal_sep=True,
			max_merge_duration=60000,
			midi_transcribe=False,
		)

		self.svc_config = load_config("soulxsinger/config/soulxsinger.yaml")
		self.svc_model = build_svc_model(
			model_path="pretrained_models/SoulX-Singer/model-svc.pt",
			config=self.svc_config,
			device=self.device,
			use_fp16=self.use_fp16,
		)

	def run_preprocess(self, audio_path: Path, save_path: Path, vocal_sep: bool) -> tuple[bool, str, Path | None, Path | None]:
		try:
			self.preprocess_pipeline.save_dir = str(save_path)
			self.preprocess_pipeline.run(
				audio_path=str(audio_path),
				vocal_sep=vocal_sep,
				max_merge_duration=60000,
				language="Mandarin",
			)
			vocal_wav = save_path / "vocal.wav"
			vocal_f0 = save_path / "vocal_f0.npy"
			if not vocal_wav.exists() or not vocal_f0.exists():
				return False, f"preprocess output missing: {vocal_wav} or {vocal_f0}", None, None
			gc.collect()
			empty_device_cache(self.device)
			return True, "ok", vocal_wav, vocal_f0
		except Exception as e:
			return False, f"preprocess failed: {e}", None, None

	def run_svc(
		self,
		prompt_wav_path: Path,
		target_wav_path: Path,
		prompt_f0_path: Path,
		target_f0_path: Path,
		session_base: Path,
		auto_shift: bool,
		auto_mix_acc: bool,
		pitch_shift: int,
		n_step: int,
		cfg: float,
		seed: int,
		progress_cb=None,
	) -> tuple[bool, str, Path | None]:
		try:
			torch.manual_seed(seed)
			np.random.seed(seed)
			random.seed(seed)

			save_dir = session_base / "generated"
			save_dir.mkdir(parents=True, exist_ok=True)

			class Args:
				pass

			args = Args()
			args.device = self.device
			args.prompt_wav_path = str(prompt_wav_path)
			args.target_wav_path = str(target_wav_path)
			args.prompt_f0_path = str(prompt_f0_path)
			args.target_f0_path = str(target_f0_path)
			args.save_dir = str(save_dir)
			args.auto_shift = auto_shift
			args.pitch_shift = int(pitch_shift)
			args.n_steps = int(n_step)
			args.cfg = float(cfg)
			args.use_fp16 = self.use_fp16

			svc_process(args, self.svc_config, self.svc_model, progress_cb=progress_cb)

			generated = save_dir / "generated.wav"
			if not generated.exists():
				return False, f"inference finished but output not found: {generated}", None

			if auto_mix_acc:
				acc_path = session_base / "transcriptions" / "target" / "acc.wav"
				if acc_path.exists():
					vocal_shift = args.pitch_shift
					mul = -1 if vocal_shift < 0 else 1
					acc_shift = abs(vocal_shift) % 12
					acc_shift = mul * acc_shift
					if acc_shift > 6:
						acc_shift -= 12
					if acc_shift < -6:
						acc_shift += 12

					mix_sr = self.svc_config.audio.sample_rate
					vocal, _ = librosa.load(str(generated), sr=mix_sr, mono=True)
					acc, _ = librosa.load(str(acc_path), sr=mix_sr, mono=True)
					if acc_shift != 0:
						acc = librosa.effects.pitch_shift(acc, sr=mix_sr, n_steps=acc_shift)
						print(f"Applied pitch shift of {acc_shift} semitones to accompaniment to match vocal shift of {vocal_shift} semitones.")
						
					mix_len = min(len(vocal), len(acc))
					if mix_len > 0:
						mixed = vocal[:mix_len] + acc[:mix_len]
						peak = float(np.max(np.abs(mixed))) if mixed.size > 0 else 1.0
						if peak > 1.0:
							mixed = mixed / peak
						mixed_path = save_dir / "generated_mixed.wav"
						sf.write(str(mixed_path), mixed, mix_sr)
						generated = mixed_path
			gc.collect()
			empty_device_cache(self.device)
			return True, "svc inference done", generated
		except Exception as e:
			return False, f"svc inference failed: {e}", None


_APP_STATES: dict[tuple[str, bool], AppState] = {}


def _normalize_device_choice(device_choice: str | None) -> str:
	device_choice = (device_choice or "auto").strip().lower()
	return "directml" if device_choice == "dml" else device_choice


def get_app_state(device_choice: str = "auto", use_fp16: bool = False) -> AppState:
	device_choice = _normalize_device_choice(device_choice)
	cache_key = (device_choice, bool(use_fp16))
	if cache_key not in _APP_STATES:
		_APP_STATES[cache_key] = AppState(device_choice=device_choice, use_fp16=use_fp16)
	return _APP_STATES[cache_key]


def _emit_progress(progress, fraction: float, message: str) -> None:
	fraction = max(0.0, min(1.0, float(fraction)))
	if progress is None:
		return
	try:
		progress(fraction, desc=message)
		return
	except TypeError:
		pass
	try:
		progress(fraction, message)
		return
	except TypeError:
		pass
	progress(message)


def run_svc_conversion(
	prompt_audio,
	target_audio,
	prompt_vocal_sep,
	target_vocal_sep,
	auto_shift,
	auto_mix_acc,
	pitch_shift,
	n_step,
	cfg,
	seed,
	target_max_sec: int | None = TARGET_MAX_SEC_DEFAULT,
	device_choice: str = "auto",
	use_fp16: bool = False,
	progress=None,
) -> Path:
	def report(fraction: float, message: str) -> None:
		_emit_progress(progress, fraction, message)
		if sys.stdout is not None:
			print(message, flush=True)

	prompt_audio = _normalize_audio_input(prompt_audio)
	target_audio = _normalize_audio_input(target_audio)
	if not prompt_audio or not target_audio:
		raise ValueError(_i18n("warn_missing_audio"))

	report(0.02, "[svc] loading models")
	state = get_app_state(device_choice=device_choice, use_fp16=use_fp16)
	report(0.08, f"[svc] device={state.device}, preprocess_device={state.preprocess_device}, fp16={state.use_fp16}")

	session_base = _session_dir()
	audio_dir = session_base / "audio"
	prompt_raw = audio_dir / "prompt.wav"
	target_raw = audio_dir / "target.wav"
	report(0.12, "[svc] preparing audio")
	_trim_and_save_audio(prompt_audio, prompt_raw, PROMPT_MAX_SEC_DEFAULT)
	_trim_and_save_audio(target_audio, target_raw, target_max_sec)

	report(0.18, "[svc] preprocessing prompt")
	prompt_ok, prompt_msg, prompt_wav, prompt_f0 = state.run_preprocess(
		audio_path=prompt_raw,
		save_path=session_base / "transcriptions" / "prompt",
		vocal_sep=bool(prompt_vocal_sep),
	)
	if not prompt_ok or prompt_wav is None or prompt_f0 is None:
		raise RuntimeError(prompt_msg)

	report(0.42, "[svc] preprocessing target")
	target_ok, target_msg, target_wav, target_f0 = state.run_preprocess(
		audio_path=target_raw,
		save_path=session_base / "transcriptions" / "target",
		vocal_sep=bool(target_vocal_sep),
	)
	if not target_ok or target_wav is None or target_f0 is None:
		raise RuntimeError(target_msg)

	def segment_progress(done: int, total: int) -> None:
		if not total:
			return
		done = max(0, min(int(done), int(total)))
		report(0.66 + 0.32 * (done / total), f"[svc] converting segments {done}/{total}")

	report(0.66, "[svc] running conversion")
	ok, msg, generated = state.run_svc(
		prompt_wav_path=prompt_wav,
		target_wav_path=target_wav,
		prompt_f0_path=prompt_f0,
		target_f0_path=target_f0,
		session_base=session_base,
		auto_shift=bool(auto_shift),
		auto_mix_acc=bool(auto_mix_acc),
		pitch_shift=int(pitch_shift),
		n_step=int(n_step),
		cfg=float(cfg),
		seed=int(seed),
		progress_cb=segment_progress,
	)
	if not ok or generated is None:
		raise RuntimeError(msg)
	report(1.0, f"[svc] done: {generated}")
	return generated


def _start_svc(
	prompt_audio,
	target_audio,
	prompt_vocal_sep,
	target_vocal_sep,
	auto_shift,
	auto_mix_acc,
	device_choice,
	use_fp16,
	pitch_shift,
	n_step,
	cfg,
	seed,
	# H3 Director Cut Studio talks to this callback through its own
	# /_studio_start_svc endpoint, which only publishes the twelve parameters
	# above and calls by keyword. A required 13th parameter would push that
	# call onto the positional fallback and misplace every value after
	# auto_mix_acc, so the new target cap stays a defaulted tail parameter:
	# the Studio path keeps working and simply uses the unlimited default.
	target_max_sec=TARGET_MAX_SEC_DEFAULT,
	progress=gr.Progress(track_tqdm=True),
):
	try:
		generated = run_svc_conversion(
			prompt_audio=prompt_audio,
			target_audio=target_audio,
			prompt_vocal_sep=prompt_vocal_sep,
			target_vocal_sep=target_vocal_sep,
			auto_shift=auto_shift,
			auto_mix_acc=auto_mix_acc,
			pitch_shift=pitch_shift,
			n_step=n_step,
			cfg=cfg,
			seed=seed,
			target_max_sec=int(target_max_sec or 0),
			device_choice=device_choice,
			use_fp16=use_fp16,
			progress=progress,
		)
		return str(generated)
	except ValueError as e:
		gr.Warning(str(e))
		return None
	except Exception:
		_print_exception("_start_svc")
		return None


def render_interface(default_device: str = "auto", default_fp16: bool = False) -> gr.Blocks:
	default_device = _normalize_device_choice(default_device)
	if default_device not in {"auto", "cuda", "directml", "cpu"}:
		default_device = "auto"
	with gr.Blocks(title="SoulX-Singer-SVC Demo", theme=gr.themes.Default()) as page:
		gr.HTML(
            '<div style="'
            'text-align: center; '
            'padding: 1.25rem 0 1.5rem; '
            'margin-bottom: 0.5rem;'
            '">'
            '<div style="'
            'display: inline-block; '
            'font-size: 1.75rem; '
            'font-weight: 700; '
            'letter-spacing: 0.02em; '
            'color: #1a1a2e; '
            'line-height: 1.3;'
            '">SoulX-Singer-SVC</div>'
            '<div style="'
            'width: 80px; '
            'height: 3px; '
            'margin: 1rem auto 0; '
            'background: linear-gradient(90deg, transparent, #6366f1, transparent); '
            'border-radius: 2px;'
            '"></div>'
            '</div>'
        )
		with gr.Row(equal_height=True):
			lang_choice = gr.Radio(
				choices=["中文", "English"],
				value="中文",
				label=_i18n("display_lang_label"),
				type="index",
				interactive=True,
			)

		usage_md = gr.Markdown(_usage_md())

		with gr.Row(equal_height=True):
			prompt_audio = gr.Audio(
				label=_i18n("prompt_audio_label"),
				type="filepath",
				editable=False,
				interactive=True,
			)
			target_audio = gr.Audio(
				label=_i18n("target_audio_label"),
				type="filepath",
				editable=False,
				interactive=True,
			)

		with gr.Row(equal_height=True):
			prompt_vocal_sep = gr.Checkbox(label=_i18n("prompt_vocal_sep_label"), value=False, scale=1)
			target_vocal_sep = gr.Checkbox(label=_i18n("target_vocal_sep_label"), value=True, scale=1)
			auto_shift = gr.Checkbox(label=_i18n("auto_shift_label"), value=True, scale=1)
			auto_mix_acc = gr.Checkbox(label=_i18n("auto_mix_acc_label"), value=True, scale=1)

		with gr.Row(equal_height=True):
			device_choice = gr.Dropdown(
				label=_i18n("device_label"),
				choices=[
					("Auto", "auto"),
					("CUDA", "cuda"),
					("DirectML", "directml"),
					("CPU", "cpu"),
				],
				value=default_device,
				interactive=True,
				scale=1,
			)
			use_fp16 = gr.Checkbox(label=_i18n("fp16_label"), value=default_fp16, scale=1)
			target_max_sec = gr.Slider(
				label=_i18n("target_max_sec_label"),
				value=TARGET_MAX_SEC_DEFAULT,
				minimum=0,
				maximum=7200,
				step=30,
				interactive=True,
				scale=1,
			)

		with gr.Row(equal_height=True):
			pitch_shift = gr.Slider(label=_i18n("pitch_shift_label"), value=0, minimum=-36, maximum=36, step=1, scale=1)
			n_step = gr.Slider(label=_i18n("n_step_label"), value=32, minimum=1, maximum=200, step=1, scale=1)
			cfg = gr.Slider(label=_i18n("cfg_label"), value=1.0, minimum=0.0, maximum=10.0, step=0.1, scale=1)
			seed_input = gr.Slider(label=_i18n("seed_label"), value=42, minimum=0, maximum=10000, step=1, scale=1)

		with gr.Row():
			run_btn = gr.Button(value=_i18n("run_btn"), variant="primary", size="lg")

		with gr.Row():
			output_audio = gr.Audio(label=_i18n("output_audio_label"), type="filepath", interactive=False)

		gr.Examples(
			examples=EXAMPLE_LIST,
			inputs=[prompt_audio, target_audio],
			label=_i18n("examples_label"),
		)

		tips_md = gr.Markdown(_tips_md())

		run_btn.click(
			fn=_start_svc,
			inputs=[
				prompt_audio,
				target_audio,
				prompt_vocal_sep,
				target_vocal_sep,
				auto_shift,
				auto_mix_acc,
				device_choice,
				use_fp16,
				pitch_shift,
				n_step,
				cfg,
				seed_input,
				target_max_sec,
			],
			outputs=[output_audio],
		)

		def _change_language(lang):
			global _GLOBAL_LANG
			_GLOBAL_LANG = ["zh", "en"][lang]
			return [
				gr.update(label=_i18n("display_lang_label")),
				gr.update(value=_usage_md()),
				gr.update(label=_i18n("prompt_audio_label")),
				gr.update(label=_i18n("target_audio_label")),
				gr.update(label=_i18n("prompt_vocal_sep_label")),
				gr.update(label=_i18n("target_vocal_sep_label")),
				gr.update(label=_i18n("auto_shift_label")),
				gr.update(label=_i18n("auto_mix_acc_label")),
				gr.update(label=_i18n("device_label")),
				gr.update(label=_i18n("fp16_label")),
				gr.update(label=_i18n("target_max_sec_label")),
				gr.update(label=_i18n("pitch_shift_label")),
				gr.update(label=_i18n("n_step_label")),
				gr.update(label=_i18n("cfg_label")),
				gr.update(label=_i18n("seed_label")),
				gr.update(value=_i18n("run_btn")),
				gr.update(label=_i18n("output_audio_label")),
				gr.update(value=_tips_md()),
			]

		lang_choice.change(
			fn=_change_language,
			inputs=[lang_choice],
			outputs=[
				lang_choice,
				usage_md,
				prompt_audio,
				target_audio,
				prompt_vocal_sep,
				target_vocal_sep,
				auto_shift,
				auto_mix_acc,
				device_choice,
				use_fp16,
				target_max_sec,
				pitch_shift,
				n_step,
				cfg,
				seed_input,
				run_btn,
				output_audio,
				tips_md,
			],
		)

	return page


if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser()
	parser.add_argument("--port", type=int, default=7861, help="Gradio server port")
	parser.add_argument("--share", action="store_true", help="Create public link")
	parser.add_argument("--fp16", action="store_true", help="Use FP16 for SVC model and inference")
	parser.add_argument(
		"--device",
		type=str,
		default=os.environ.get("SOULX_DEVICE", "auto"),
		choices=["auto", "cuda", "directml", "dml", "cpu"],
		help="Inference device: auto, cuda, directml/dml, or cpu",
	)
	args = parser.parse_args()

	page = render_interface(default_device=args.device, default_fp16=args.fp16)
	page.queue()
	page.launch(share=args.share, server_name="0.0.0.0", server_port=args.port)
