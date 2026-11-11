"""Frozen Whisper encoder wrapper (wav -> encoder embeddings)."""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torchaudio
from transformers import WhisperFeatureExtractor, WhisperModel

WHISPER_MEL_FRAMES = 3000        # 3000 frames at 16000 Hz
WHISPER_MAX_SEC = 30.0           # native Whisper window


class WhisperEncoder():

    def __init__(
        self,
        device: Optional[str] = None,
    ) -> None:
        self.fe = WhisperFeatureExtractor.from_pretrained("openai/whisper-base")
        self.model = WhisperModel.from_pretrained("openai/whisper-base")
        self.model = self.model.to(device or ("cuda" if torch.cuda.is_available() else "cpu"))

    def encode(
        self,
        wav: torch.Tensor,
        sr: int,
    ) -> torch.Tensor:
        """Whisper encoder embeddings for ``wav``, one frame per 20 ms (50 Hz).

        Whisper itself only ever looks at 30 s, so feeding a longer clip used to
        silently truncate: everything past 30 s got zero content features. Any input
        longer than the native window is now split into consecutive windows aligned
        to the 50 Hz grid and the embeddings are concatenated.
        """
        wav = torchaudio.functional.resample(wav, orig_freq=sr, new_freq=self.fe.sampling_rate) if sr != self.fe.sampling_rate else wav
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)

        sr16 = int(self.fe.sampling_rate)
        max_samples = int(WHISPER_MAX_SEC * sr16)
        if wav.shape[-1] <= max_samples:
            return self._encode_window(wav)

        hop = sr16 // 50  # 320 samples at 16 kHz == one 20 ms feature frame
        chunk = max_samples - (max_samples % hop)
        total = wav.shape[-1]
        outs = []
        pos = 0
        while pos < total:
            end = min(pos + chunk, total)
            if end - pos < hop:  # ragged sub-frame tail: widen the last window instead
                pos = max(0, total - chunk)
                end = total
            outs.append(self._encode_window(wav[:, pos:end]))
            pos = end
        return torch.cat(outs, dim=1)

    def _encode_window(
        self,
        wav: torch.Tensor,
    ) -> torch.Tensor:
        wav_np = wav.cpu().detach().numpy().astype("float32", copy=False)

        inputs = self.fe(
            wav_np,
            sampling_rate=self.fe.sampling_rate,
            return_tensors="pt",
            padding=False,
            truncation=False,
            return_attention_mask=True,
        )

        input_features = inputs.input_features
        num_frames = input_features.shape[-1]
        if num_frames < WHISPER_MEL_FRAMES:
            pad = WHISPER_MEL_FRAMES - num_frames
            input_features = torch.nn.functional.pad(input_features, (0, pad))
        else:
            input_features = input_features[..., :WHISPER_MEL_FRAMES]

        input_features = input_features.to(wav.device)
        if self.model.device != wav.device:
            self.model = self.model.to(wav.device)
        attention_mask = inputs.attention_mask.to(wav.device) if inputs.attention_mask is not None else None

        encoder_out = self.model.encoder(input_features).last_hidden_state

        if attention_mask is not None:
            valid_mel_frames = attention_mask.sum(dim=1)
            valid_enc_frames = (valid_mel_frames + 1) // 2
            max_valid_enc_frames = min(int(valid_enc_frames.max().item()), encoder_out.shape[1])
            encoder_out = encoder_out[:, :max_valid_enc_frames, :]
            valid_len = min(int(valid_enc_frames[0].item()), max_valid_enc_frames)
            if valid_len < max_valid_enc_frames:
                encoder_out[0, valid_len:, :] = 0

        return encoder_out


if __name__ == "__main__":
    torch.manual_seed(0)
    audio = torch.randn(1, 24000 * 25).float().to("cuda")
    encoder = WhisperEncoder()
    whisper_encoder_out = encoder.encode(audio, sr=24000)
    print(whisper_encoder_out.shape)
