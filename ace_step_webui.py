"""Standalone Gradio client for a remote ACE-Step 1.5 API server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import gradio as gr

from ace_step_client import (
    DEFAULT_SERVER,
    download_audio,
    request_json,
    submit_audio_task,
    wait_for_task,
)


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "ace_step_webui"
WEBUI_CSS = """
.ace-title {letter-spacing:-0.02em; margin-bottom:0!important}
.ace-subtitle {color:#8f9bad; margin-top:0!important}
.primary-card {border:1px solid rgba(120,140,180,.25); border-radius:16px; padding:8px}
"""


def _first_output(record: dict[str, Any]) -> dict[str, Any]:
    """Return the first normalized ACE-Step result object."""

    outputs = record.get("outputs") or []
    if not outputs or not isinstance(outputs[0], dict):
        raise RuntimeError(f"ACE-Step task completed without an output: {record}")
    return dict(outputs[0])


def check_connection(server: str, api_key: str) -> str:
    """Return a concise status message for the configured API server."""

    payload = request_json(server, "health", api_key=api_key, timeout=15)
    data = payload.get("data") or {}
    if data.get("status") != "ok":
        raise gr.Error(f"ACE-Step health check failed: {payload}")
    model_state = "loaded" if data.get("models_initialized") else "lazy / not loaded"
    lm_state = "loaded" if data.get("llm_initialized") else "not loaded"
    return (
        f"Connected · {data.get('service', 'ACE-Step')} {data.get('version', '')} · "
        f"DiT {model_state} · LM {lm_state}"
    )


def analyze_source(source_audio: str, server: str, api_key: str):
    """Analyze uploaded source audio and return editable generation metadata."""

    if not source_audio:
        raise gr.Error("Choose a source audio file first.")
    task_id = submit_audio_task(
        source_audio,
        server=server,
        task_type="cover",
        full_analysis_only=True,
        api_key=api_key,
    )
    record = wait_for_task(task_id, server=server, api_key=api_key, timeout=3600)
    result = _first_output(record)
    prompt = str(result.get("prompt") or "")
    lyrics = str(result.get("lyrics") or "[Instrumental]")
    bpm = result.get("bpm") or 120
    key_scale = str(result.get("keyscale") or "")
    time_signature = str(result.get("timesignature") or "4")
    duration = result.get("duration") or 20
    details = json.dumps(record, ensure_ascii=False, indent=2)
    status = f"Analysis complete · task {task_id} · {bpm} BPM · {key_scale} · {duration}s"
    return prompt, lyrics, bpm, key_scale, time_signature, duration, status, details


def generate_cover(
    source_audio: str,
    reference_audio: str | None,
    use_source_reference: bool,
    prompt: str,
    lyrics: str,
    bpm: float,
    key_scale: str,
    time_signature: str,
    duration: float,
    cover_strength: float,
    inference_steps: int,
    random_seed: bool,
    seed: int,
    server: str,
    api_key: str,
):
    """Generate, download, and return one ACE-Step cover result."""

    if not source_audio:
        raise gr.Error("Choose a source audio file first.")
    if not prompt.strip():
        raise gr.Error("Analyze the audio or enter a prompt before generating.")
    timbre_reference = reference_audio or (source_audio if use_source_reference else None)
    task_id = submit_audio_task(
        source_audio,
        server=server,
        prompt=prompt.strip(),
        lyrics=lyrics.strip() or "[Instrumental]",
        task_type="cover",
        cover_strength=float(cover_strength),
        reference_audio=timbre_reference,
        bpm=int(bpm) if bpm else None,
        key_scale=key_scale,
        time_signature=time_signature,
        audio_duration=float(duration) if duration else None,
        inference_steps=int(inference_steps),
        seed=None if random_seed else int(seed),
        api_key=api_key,
    )
    record = wait_for_task(task_id, server=server, api_key=api_key, timeout=3600)
    result = _first_output(record)
    file_url = str(result.get("file") or "")
    if not file_url:
        raise RuntimeError(f"ACE-Step returned no audio URL: {result}")
    output_path = OUTPUT_DIR / f"ace_cover_{task_id[:8]}.mp3"
    download_audio(file_url, output_path, server=server, api_key=api_key)
    info = str(result.get("generation_info") or "Generation complete")
    status = f"Cover complete · task {task_id}\n\n{info}"
    return (
        str(output_path),
        str(output_path),
        status,
        json.dumps(record, ensure_ascii=False, indent=2),
    )


def build_webui() -> gr.Blocks:
    """Build the standalone ACE-Step client interface."""

    with gr.Blocks(title="ACE-Step Music Cover") as demo:
        gr.Markdown("# ACE-Step 1.5 Music Cover", elem_classes="ace-title")
        gr.Markdown(
            "分析参考音乐、自动填写参数，然后生成保留旋律与结构的 Cover。",
            elem_classes="ace-subtitle",
        )

        with gr.Accordion("服务器连接", open=False):
            with gr.Row():
                server = gr.Textbox(label="ACE-Step API", value=DEFAULT_SERVER, scale=3)
                api_key = gr.Textbox(label="API Key（可选）", type="password", scale=2)
                connect = gr.Button("测试连接", variant="secondary")
            connection_status = gr.Textbox(label="连接状态", interactive=False)

        with gr.Row(equal_height=False):
            with gr.Column(scale=1, elem_classes="primary-card"):
                source_audio = gr.Audio(
                    label="源音频 · 控制旋律 / 节奏 / 结构",
                    sources=["upload"],
                    type="filepath",
                )
                reference_audio = gr.Audio(
                    label="可选独立参考音频 · 控制音色 / 混音 / 演奏",
                    sources=["upload"],
                    type="filepath",
                )
                use_source_reference = gr.Checkbox(
                    label="未上传独立音色时，同时用源音频控制音色/混音（默认）",
                    value=True,
                )
                analyze = gr.Button("分析并自动填写", variant="secondary")
                cover_strength = gr.Slider(
                    0.0, 1.0, value=1.0, step=0.05, label="Cover 强度"
                )
                generate = gr.Button("生成 Cover", variant="primary")

            with gr.Column(scale=2, elem_classes="primary-card"):
                prompt = gr.Textbox(label="Prompt", lines=8, placeholder="分析音频后自动填写")
                lyrics = gr.Textbox(label="Lyrics", lines=5, value="[Instrumental]")
                with gr.Row():
                    bpm = gr.Number(label="BPM", value=120, precision=0)
                    key_scale = gr.Textbox(label="调性")
                    time_signature = gr.Textbox(label="拍号", value="4")
                    duration = gr.Number(label="时长（秒）", value=20)
                with gr.Accordion("生成设置", open=False):
                    inference_steps = gr.Slider(1, 20, value=8, step=1, label="Turbo Steps")
                    random_seed = gr.Checkbox(label="随机 Seed", value=False)
                    seed = gr.Number(label="Seed", value=20260913, precision=0)

        status = gr.Markdown("就绪")
        output_audio = gr.Audio(label="生成结果", type="filepath")
        output_download = gr.File(label="下载成品")
        with gr.Accordion("原始 API 结果", open=False):
            raw_result = gr.Code(label="Result JSON", language="json")

        connect.click(check_connection, [server, api_key], connection_status)
        analyze.click(
            analyze_source,
            [source_audio, server, api_key],
            [prompt, lyrics, bpm, key_scale, time_signature, duration, status, raw_result],
        )
        generate.click(
            generate_cover,
            [
                source_audio,
                reference_audio,
                use_source_reference,
                prompt,
                lyrics,
                bpm,
                key_scale,
                time_signature,
                duration,
                cover_strength,
                inference_steps,
                random_seed,
                seed,
                server,
                api_key,
            ],
            [output_audio, output_download, status, raw_result],
        )
    return demo


def main() -> None:
    """Launch the local browser client."""

    parser = argparse.ArgumentParser(description="ACE-Step 1.5 client WebUI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=7868, type=int)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    build_webui().queue(default_concurrency_limit=1).launch(
        server_name=args.host,
        server_port=args.port,
        inbrowser=not args.no_browser,
        show_error=True,
        theme=gr.themes.Soft(),
        css=WEBUI_CSS,
    )


if __name__ == "__main__":
    main()
