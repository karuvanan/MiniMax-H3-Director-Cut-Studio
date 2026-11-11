# Local Subtitle Tool

Create script-informed translated subtitles from a local video and script. The tool uses `faster-whisper` to decide which spoken lines appear and when; a locally served LM Studio model uses your script as wording and translation reference. It creates editable SRT/ASS files and a subtitled MP4 without sending media to a cloud service.

## Highlights

- Drag a video and type, paste, or drop a `.txt` / `.docx` script.
- Generate speech-timed subtitles in any selected source and target language.
- Enter any target language, or use the compact **Eng / Chi / Jp / Kor / Mel / India / Thai / 繁体** quick-select buttons.
- Query the list of models currently loaded in LM Studio.
- Position subtitles directly on the video's first-frame preview, which follows the source video's aspect ratio.
- Change font, size, text colour, outline, outline colour, and bold weight.
- Choose **automatic** MP4 rendering or **manual** SRT editing before rendering.
- Edit generated SRT or ASS files, then render the MP4 again.
- Save and reopen a subtitle-job JSON file manually.
- Optional LM Studio model unload after completion or an error to release model VRAM (system RAM is not forcibly cleared).

## Requirements

- Windows
- Python 3.11 or later
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on `PATH`
- [LM Studio](https://lmstudio.ai/) with an instruction model loaded and its local server running

Install Python packages:

```powershell
pip install -r requirements.txt
```

To keep dependencies private to this tool instead of changing a shared Python environment, install them into its `vendor` folder:

```powershell
pip install --target .\vendor -r requirements.txt
```

The selected Whisper model downloads on its first use. For NVIDIA GPU processing, select `cuda` and `float16` in the GUI. For CPU processing, use `cpu` and `int8`.

## Start

Double-click `run_subtitle_gui.bat`, or run:

```powershell
python subtitle_gui.py
```

In LM Studio, start the local server. The default address is:

```text
http://127.0.0.1:1234/v1
```

Use **Load models** in the application to select a currently loaded model.

## Workflow

1. Drag a video into the Video panel, or double-click it to browse.
2. Paste your script, or drag a `.txt` / `.docx` file into the Script panel.
3. Select your source language, target language, and LM Studio model. You may type any target language, or click a compact shortcut: **Eng**, **Chi**, **Jp**, **Kor**, **Mel**, **India**, **Thai**, or **繁体**.
4. Drag the sample subtitle over the first-frame preview and set its style.
5. Choose an output mode:
   - **Automatic:** generate SRT/ASS and immediately create the subtitled MP4.
   - **Manual:** stop after SRT creation, edit subtitle text/timecodes, then select **Save and render MP4**.
6. Use **Preview result**, **Edit SRT**, or **Edit ASS** after processing.

## Outputs

Files are written to the `output` folder beside the application. Each job uses the source video name plus a timestamp, so earlier outputs are not overwritten.

For example, a video named `demo.mp4` may create:

```text
demo_20260831_143012_input_script.txt
demo_20260831_143012_asr_raw_zh.srt
demo_20260831_143012_script_matched_zh.srt
demo_20260831_143012_translated_English.srt
demo_20260831_143012_translated_English_styled.ass
demo_20260831_143012_translated_English_subtitled.mp4
demo_20260831_143012_alignment.json
demo_20260831_143012_subtitle_job.json
```

`English` comes from the value entered in **Translate to**. All translated deliverables use the format `translated_<language>`; for example, entering `中文` creates `translated_中文.srt`, `translated_中文_styled.ass`, and `translated_中文_subtitled.mp4`. Characters that Windows cannot use in filenames are converted to `_`.

`*_subtitle_job.json` stores the job settings. Use **Open subtitle job** to restore it manually; the application does not automatically reopen a previous project on launch.

## Command line

The GUI calls `subtitle_pipeline.py`, which can also be run directly:

```powershell
python subtitle_pipeline.py `
  --video "C:\Videos\demo.mp4" `
  --script "C:\Videos\script.txt" `
  --output ".\output" `
  --model "your-lm-studio-model-id" `
  --source-language zh `
  --target-language English
```

## Notes

- Spoken audio decides which subtitles appear and supplies their timecodes. The script is optional wording and translation reference; unused script lines are not forced onto the video.
- Review names, interface labels, timing, and translation before publication.
- LM Studio unload only releases the selected model. The tool does not force a system RAM cleanup.
- For sung or music-heavy audio, uncheck **Voice filter (VAD)** in the settings panel (or pass `--no-vad`). With VAD on, Silero often cuts away most of the singing and Whisper hallucinates on whatever chunk remains — a classic example is the phantom line “优优独播剧场——YoYo Television Series Exclusive” that appears when transcribing Chinese music. You can also lower the VAD threshold (e.g. `0.35`) to keep more sung audio while staying filtered.
- Thinking models in LM Studio (for example Qwen MTP builds) spend many reasoning tokens before any visible output; the pipeline now retries with a larger token budget when the first response comes back empty or without JSON.
