# H3 Director Cut common AI runtime

This folder is the self-contained runtime used by H3 Director Cut Studio.

- `python_env/` — Python 3.11, PySide6, Pillow, Torch, CUDA runtime libraries and Transformers.
- `engine_ffmpeg/` — FFmpeg and FFprobe binaries.
- `models/` — offline BLIP image-captioning and Whisper Small multilingual speech-recognition models.
- `runtime_config.json` — relative paths consumed by the launcher and application.

Large binaries and model weights are intentionally excluded from Git. Launch the
application through `run_h3_prompt_studio.bat`; it resolves everything relative to
the project folder, so no global Python or PATH installation is required.
