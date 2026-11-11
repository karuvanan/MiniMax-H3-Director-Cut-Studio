import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from tqdm import tqdm
from typing import Optional, Dict, Any, List, Tuple
from contextlib import nullcontext

from soulxsinger.models.modules.vocoder import Vocoder
from soulxsinger.models.modules.decoder import CFMDecoder
from soulxsinger.models.modules.mel_transform import MelSpectrogramEncoder
from soulxsinger.models.modules.whisper_encoder import WhisperEncoder


def _autocast_if(enabled: bool):
    """Return autocast(context) if enabled else no-op context. Use: with _autocast_if(use_amp): ..."""
    return torch.amp.autocast(device_type="cuda", enabled=True) if enabled else nullcontext()

class SoulXSingerSVC(nn.Module):
    """
    SoulXSinger SVC model.
    """
    def __init__(self, config: Dict):
        super(SoulXSingerSVC, self).__init__()
        self.audio_cfg = config.audio
        enc_cfg = config.model.encoder
        cfm_cfg = config.model.flow_matching
        
        self.whisper_encoder = WhisperEncoder()
        self.f0_encoder = nn.Embedding(enc_cfg["f0_bin"], enc_cfg["f0_dim"])
        self.cfm_decoder = CFMDecoder(cfm_cfg)

        self.mel = MelSpectrogramEncoder(self.audio_cfg)
        self.vocoder = Vocoder()

    @staticmethod
    def f0_to_coarse(f0, f0_bin=361, f0_min=32.7031956625, f0_shift=0):
        """
        Convert continuous F0 values to discrete F0 bins (SIL and C1 - B6, 361 bins).
        args:
            f0: continuous F0 values
            f0_bin: number of F0 bins
            f0_min: minimum F0 value
            f0_shift: shift value for F0 bins
        returns:
            f0_coarse: discrete F0 bins
        """
        is_torch = isinstance(f0, torch.Tensor)
        uv_mask = f0 <= 0    

        if is_torch:  
            f0_safe = torch.maximum(f0, torch.tensor(f0_min))
            f0_cents = 1200 * torch.log2(f0_safe / f0_min)
        else:
            f0_safe = np.maximum(f0, f0_min)
            f0_cents = 1200 * np.log2(f0_safe / f0_min)

        f0_coarse = (f0_cents / 20) + 1
        
        if is_torch:
            f0_coarse = torch.round(f0_coarse).long()
            f0_coarse = torch.clamp(f0_coarse, min=1, max=f0_bin - 1)
        else:
            f0_coarse = np.rint(f0_coarse).astype(int)
            f0_coarse = np.clip(f0_coarse, 1, f0_bin - 1)

        f0_coarse[uv_mask] = 0

        if f0_shift != 0:
            if is_torch:
                voiced = f0_coarse > 0
                if voiced.any():
                    shifted = f0_coarse[voiced] + f0_shift
                    f0_coarse[voiced] = torch.clamp(shifted, 1, f0_bin - 1)
            else:
                voiced = f0_coarse > 0
                if np.any(voiced):
                    shifted = f0_coarse[voiced] + f0_shift
                    f0_coarse[voiced] = np.clip(shifted, 1, f0_bin - 1)
        
        return f0_coarse

    @staticmethod
    def build_vocal_segments(
        f0,
        f0_rate: int = 50,
        uv_frames_th: int = 5,
        min_duration_sec: float = 5.0,
        max_duration_sec: float = 30.0,
        num_overlaps: int = 1,
        ignore_silent_segments: bool = True,
    ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """Build vocal segments based on F0 contour. First split by long silent runs, then merge into segments based on min and max duration constraints.
        args:
            f0: F0 contour of the audio, 1D array or tensor with shape (T,)
            f0_rate: F0 sampling rate in Hz (e.g., 50 for 20ms hop size)
            uv_frames_th: number of consecutive zero F0 frames to consider as a split point
            min_duration_sec: minimum duration of each segment in seconds
            max_duration_sec: maximum duration of each segment in seconds
            num_overlaps: number of overlapping segments to create for each non-overlapping segment (for smooth inference)
            ignore_silent_segments: whether to ignore segments that are mostly silent (e.g., > 95% zero F0)
        returns:
            overlap_segments: list of (overlap_start_sec, overlap_end_sec) for each segment, which may overlap with adjacent segments for smooth inference
            segments: list of (seg_start_sec, seg_end_sec) for each segment, which are non-overlapping and used for final merging
        """
        if isinstance(f0, torch.Tensor):
            f0_np = f0.detach().float().cpu().numpy()
        else:
            f0_np = np.asarray(f0, dtype=np.float32)
        f0_np = np.squeeze(f0_np)

        total_frames = int(f0_np.shape[0])
        if total_frames == 0:
            return [], []

        min_frames = max(1, int(round(min_duration_sec * f0_rate)))
        max_frames = max(1, int(round(max_duration_sec * f0_rate)))

        split_points = [0]      # silence split points in frame indices, starting with 0 and ending with total_frames

        def append_split_point(point: int):
            # Ensure split points are within valid range and respect max_frames constraint
            point = int(max(0, min(point, total_frames)))
            while point - split_points[-1] > max_frames:
                split_points.append(split_points[-1] + max_frames)
            if point > split_points[-1]:
                split_points.append(point)

        idx = 0
        while idx < total_frames:
            if f0_np[idx] == 0:
                run_start = idx
                while idx < total_frames and f0_np[idx] == 0:
                    idx += 1
                run_end = idx
                if (run_end - run_start) >= uv_frames_th:
                    split_point = max(run_end - 5, (run_start + run_end) // 2)
                    append_split_point(split_point)
            else:
                idx += 1
        append_split_point(total_frames)
        # print(f"Initial split points (in seconds): {[round(p / f0_rate, 2) for p in split_points]}")

        segments: List[Tuple[int, int]] = []
        overlap_segments: List[Tuple[int, int]] = []

        def append_segment(start_idx: int, end_idx: int, num_overlaps: int = num_overlaps):
            segments.append((split_points[start_idx] / f0_rate, split_points[end_idx] / f0_rate))
            overlap_start_idx = start_idx
            if start_idx > 0 and (split_points[end_idx] - split_points[start_idx - num_overlaps]) <= max_frames:
                overlap_start_idx = start_idx - num_overlaps
            overlap_segments.append((split_points[overlap_start_idx] / f0_rate, split_points[end_idx] / f0_rate))

        segment_start, segment_end = 0, 1
        
        while segment_start < len(split_points) - 1:
            while segment_end < len(split_points) and (split_points[segment_end] - split_points[segment_start]) < min_frames:
                segment_end += 1

            if segment_end >= len(split_points):
                append_segment(segment_start, len(split_points) - 1, num_overlaps=num_overlaps)
                break
            append_segment(segment_start, segment_end, num_overlaps=num_overlaps)
            segment_start = segment_end
            segment_end = segment_start + 1

        # print(f"Final segments (overlap_start, overlap_end, seg_start_time, seg_end_time) in seconds: {overlap_segments}")
        if ignore_silent_segments:
            filtered_idx = []
            for i, seg in enumerate(overlap_segments):
                start_frame = int(seg[0] * f0_rate)
                end_frame = int(seg[1] * f0_rate)
                total_frames = end_frame - start_frame
                voice_frames = np.sum(f0_np[start_frame:end_frame] > 0)
                if voice_frames / total_frames > 0.05 and voice_frames >= 10:   # at least 10 voiced frames and >5% voiced frames
                    filtered_idx.append(i)

            overlap_segments = [overlap_segments[i] for i in filtered_idx]
            segments = [segments[i] for i in filtered_idx]
            # print(f"Filtered segments with mostly silence removed: {overlap_segments}")

        return overlap_segments, segments
    
    def infer(
        self, 
        pt_wav: str|torch.Tensor,
        gt_wav: str|torch.Tensor,
        pt_f0: str|torch.Tensor,
        gt_f0: str|torch.Tensor,
        auto_shift=False,
        pitch_shift=0,
        n_steps=32,
        cfg=3,
        use_fp16=False,
        progress_cb=None,
        crossfade: bool = True,
        seam_fade_sec: float = 0.2,
    ):
        """
        SVC inference pipeline. First build vocal segments based on F0 contour, then run inference for each segment and merge results.
        args:
            pt_wav: prompt waveform path or tensor
            gt_wav: target waveform path or tensor
            pt_f0: prompt F0 path or tensor
            gt_f0: target F0 path or tensor
            auto_shift: whether to automatically calculate pitch shift based on median F0 of prompt and target
            pitch_shift: manual pitch shift in semitones (overrides auto_shift if > 0)
            n_steps: number of diffusion steps for inference
            cfg: classifier-free guidance scale for inference
            use_fp16: if True, run in FP16 except mel extraction to save memory and speed.
            progress_cb: optional ``fn(done_segments, total_segments)`` hook for long files
            crossfade: crossfade ``seam_fade_sec`` of audio across each split point
                instead of hard-cutting, which is what made long files click
            seam_fade_sec: length of that boundary crossfade in seconds
        """

        # calculate auto pitch shift
        if auto_shift and pitch_shift == 0:
            if gt_f0 is not None and pt_f0 is not None:
                gt_f0_median = torch.median(gt_f0[gt_f0 > 0])
                pt_f0_median = torch.median(pt_f0[pt_f0 > 0])
                pitch_shift = torch.round(torch.log2(pt_f0_median / gt_f0_median) * 1200 / 100).int().item()
            else:
                print("Warning: pitch_shift is True but note_pitch or f0 is None. Set f0_shift to 0.")
                pitch_shift = 0
        else:
            pitch_shift = pitch_shift

        use_fp16 = use_fp16 and pt_wav.is_cuda
        # mel is kept in fp32 (see build_model: model.mel.float() after model.half())
        pt_mel = self.mel(pt_wav.float() if pt_wav.dtype != torch.float32 else pt_wav)
        if use_fp16:
            pt_mel = pt_mel.half()
            pt_wav = pt_wav.half()
            gt_wav = gt_wav.half()
            pt_f0 = pt_f0.half()
            gt_f0 = gt_f0.half()

        # if target audio is less than 30 seconds, infer the whole audio
        if gt_wav.shape[-1] < 30 * self.audio_cfg.sample_rate:
            with _autocast_if(use_fp16):
                generated_audio = self.infer_segment(
                    pt_mel=pt_mel,
                    pt_wav=pt_wav,
                    gt_wav=gt_wav,
                    pt_f0=pt_f0,
                    gt_f0=gt_f0,
                    pitch_shift=pitch_shift,
                    n_steps=n_steps,
                    cfg=cfg,
                )
            if progress_cb is not None:
                progress_cb(1, 1)
            return generated_audio, pitch_shift

        # if target audio is longer than 30 seconds, build vocal segments and infer each segment
        generated_audio = []

        f0_rate = self.audio_cfg.sample_rate // self.audio_cfg.hop_size

        wav_sec = gt_wav.shape[-1] / self.audio_cfg.sample_rate
        f0_sec = gt_f0.shape[-1] / f0_rate
        if f0_sec < wav_sec - 0.5:
            print(
                f"Warning: target f0 covers only {f0_sec:.1f}s of a {wav_sec:.1f}s target; "
                f"the last {wav_sec - f0_sec:.1f}s will be left silent.",
                flush=True,
            )
        
        overlap_segments, segments = self.build_vocal_segments(
            gt_f0,
            f0_rate=f0_rate,
            uv_frames_th=10,
            min_duration_sec=15.0,
            max_duration_sec=30.0,
        )
        if len(segments) == 0:
            segments = [(0.0, gt_wav.shape[-1] / self.audio_cfg.sample_rate)]
            overlap_segments = [(0.0, gt_wav.shape[-1] / self.audio_cfg.sample_rate)]

        generated_audio = torch.zeros_like(gt_wav)
        for idx in tqdm(range(len(segments)), total=len(segments), desc="Inferring segments (SVC)", dynamic_ncols=True):
            overlap_start_sec, overlap_end_sec = overlap_segments[idx]
            seg_start_sec, seg_end_sec = segments[idx]

            wav_start = int(round(overlap_start_sec * self.audio_cfg.sample_rate))
            wav_end = int(round(overlap_end_sec * self.audio_cfg.sample_rate))
            f0_start = int(round(overlap_start_sec * f0_rate))
            f0_end = int(round(overlap_end_sec * f0_rate))

            wav_start = max(0, min(wav_start, gt_wav.shape[-1]))
            wav_end = max(wav_start, min(wav_end, gt_wav.shape[-1]))
            f0_start = max(0, min(f0_start, gt_f0.shape[-1]))
            f0_end = max(f0_start, min(f0_end, gt_f0.shape[-1]))

            segment_gt_wav = gt_wav[:, wav_start:wav_end]
            segment_gt_f0 = gt_f0[:, f0_start:f0_end]
            with _autocast_if(use_fp16):
                segment_generated_audio = self.infer_segment(
                    pt_mel=pt_mel,
                    pt_wav=pt_wav,
                    gt_wav=segment_gt_wav,
                    pt_f0=pt_f0,
                    gt_f0=segment_gt_f0,
                    pitch_shift=pitch_shift,
                    n_steps=n_steps,
                    cfg=cfg,
                )

            segment_start = int(round(seg_start_sec * self.audio_cfg.sample_rate))
            segment_end = int(round(seg_end_sec * self.audio_cfg.sample_rate))

            core_audio = segment_generated_audio[segment_start - wav_start: segment_end - wav_start]

            # The generated block reaches back to wav_start for context, but that look-back
            # region was already rendered by the previous segment. Blend only a short seam
            # around the boundary (not the whole look-back, which would double the audio);
            # a hard cut there is what produced clicks on long files.
            if crossfade and segment_generated_audio.numel() > 0:
                fade_len = max(0, int(round(seam_fade_sec * self.audio_cfg.sample_rate)))
                blend_end = min(segment_start, generated_audio.shape[-1])
                blend_start = max(wav_start, blend_end - fade_len)
                if blend_end > blend_start and blend_start >= wav_start:
                    n = blend_end - blend_start
                    prev = generated_audio[:, blend_start:blend_end].reshape(1, n).float()
                    new = segment_generated_audio[blend_start - wav_start: blend_end - wav_start].reshape(1, n).float()
                    if new.numel() == n:
                        ramp = torch.linspace(0.0, 1.0, n, device=prev.device, dtype=torch.float32).unsqueeze(0)
                        generated_audio[:, blend_start:blend_end] = (prev * (1.0 - ramp) + new * ramp).to(generated_audio.dtype)

            n_core = min(core_audio.numel(), generated_audio.shape[-1] - segment_start)
            if n_core > 0:
                generated_audio[:, segment_start:segment_start + n_core] = core_audio[:n_core].reshape(1, n_core)

            if progress_cb is not None:
                progress_cb(idx + 1, len(segments))
    
        return generated_audio, pitch_shift

    def infer_segment(self, pt_mel, pt_wav, gt_wav, pt_f0, gt_f0, pitch_shift=0, n_steps=32, cfg=3):
        len_prompt_mel = pt_mel.shape[1]
        pt_f0 = F.pad(pt_f0, (0, 0, 0, max(0, len_prompt_mel - pt_f0.shape[1])))[:, :len_prompt_mel]

        f0_course_pt = self.f0_to_coarse(pt_f0)
        f0_course_gt = self.f0_to_coarse(gt_f0, f0_shift=pitch_shift * 5)
        f0_course = torch.cat([f0_course_pt, f0_course_gt], 1)

        pt_content_feat = self.whisper_encoder.encode(pt_wav, sr=self.audio_cfg.sample_rate)
        gt_content_feat = self.whisper_encoder.encode(gt_wav, sr=self.audio_cfg.sample_rate)
        t_pt, t_gt = f0_course_pt.shape[1], f0_course_gt.shape[1]
        pt_content_feat = F.pad(pt_content_feat, (0, 0, 0, max(0, t_pt - pt_content_feat.shape[1])))[:, :t_pt, :]
        gt_content_feat = F.pad(gt_content_feat, (0, 0, 0, max(0, t_gt - gt_content_feat.shape[1])))[:, :t_gt, :]

        content_feat = torch.cat([pt_content_feat, gt_content_feat], 1)

        f0_feat = self.f0_encoder(f0_course)
        features = content_feat + f0_feat
        
        gt_decoder_inp = features[:, len_prompt_mel:, :]
        pt_decoder_inp = features[:, :len_prompt_mel, :]

        generated_mel = self.cfm_decoder.reverse_diffusion(
            pt_mel,
            pt_decoder_inp,
            gt_decoder_inp,
            n_timesteps=n_steps,
            cfg=cfg
        )
        
        generated_audio = self.vocoder(generated_mel.transpose(1, 2)[0:1, ...])
        generated_audio = generated_audio.squeeze().float()

        # cut or pad to match gt_wav length
        if generated_audio.shape[-1] > gt_wav.shape[-1]:
            generated_audio = generated_audio[:gt_wav.shape[-1]]
        elif generated_audio.shape[-1] < gt_wav.shape[-1]:
            generated_audio = F.pad(generated_audio, (0, gt_wav.shape[-1] - generated_audio.shape[-1]))

        return generated_audio