# 本地字幕工具

使用本地影片和剧本，建立以剧本作为参考的翻译字幕。本工具使用 `faster-whisper` 决定哪些语音需要显示字幕及其时间点，并使用本机 LM Studio 模型参考剧本的措辞与翻译。它会生成可编辑的 SRT、ASS，以及已烧录字幕的 MP4；媒体内容不会传送到云端。

## 功能重点

- 拖放影片，并可输入、粘贴或拖放 `.txt` / `.docx` 剧本。
- 为任意选定的来源语言与目标语言生成带时间码的字幕。
- 可自行输入任何目标语言，也可使用紧凑的 **Eng / Chi / Jp / Kor / Mel / India / Thai / 繁体** 快捷按钮。
- 读取 LM Studio 目前已加载的模型清单。
- 在依照原始影片长宽比例显示的首帧预览上，直接拖动字幕位置。
- 调整字体、字号、文字颜色、描边、描边颜色和粗体。
- 选择**自动**建立 MP4，或先以**手动**模式编辑 SRT 后再输出。
- 编辑已生成的 SRT 或 ASS 后，重新输出 MP4。
- 手动保存及重新开启字幕工作项目 JSON 档。
- 工作完成或发生错误后可选择卸载 LM Studio 模型以释放模型 VRAM（不会强制清除系统 RAM）。

## 系统需求

- Windows
- Python 3.11 或更高版本
- 已安装 [FFmpeg](https://ffmpeg.org/download.html)，并已加入 `PATH`
- 已安装 [LM Studio](https://lmstudio.ai/)，加载指令模型并启动本地服务器

安装 Python 套件：

```powershell
pip install -r requirements.txt
```

若要将依赖安装在本工具私有的 `vendor` 文件夹，而不影响共享 Python 环境，请使用：

```powershell
pip install --target .\vendor -r requirements.txt
```

所选 Whisper 模型会在首次使用时下载。使用 NVIDIA GPU 时，请在 GUI 选择 `cuda` 和 `float16`；使用 CPU 时请选择 `cpu` 和 `int8`。

## 启动方式

双击 `run_subtitle_gui.bat`，或执行：

```powershell
python subtitle_gui.py
```

请在 LM Studio 启动本地服务器。默认地址为：

```text
http://127.0.0.1:1234/v1
```

在应用程式中按 **Load models**，即可选择目前已加载的模型。

## 使用流程

1. 将影片拖到 Video 面板，或双击该区域浏览并选择影片。
2. 粘贴剧本，或将 `.txt` / `.docx` 文件拖到 Script 面板。
3. 选择来源语言、目标翻译语言及 LM Studio 模型。目标语言可任意输入，也可按 **Eng**、**Chi**、**Jp**、**Kor**、**Mel**、**India**、**Thai** 或 **繁体**。
4. 在首帧预览上拖动示例字幕，并设置字幕样式。
5. 选择输出模式：
   - **自动：**建立 SRT / ASS 后，立即建立已烧录字幕的 MP4。
   - **手动：**SRT 建立后暂停，编辑字幕文字或时间码，再选择 **Save and render MP4**。
6. 处理完成后可使用 **Preview result**、**Edit SRT** 或 **Edit ASS**。

## 输出文件

文件会输出到应用程式旁的 `output` 文件夹。每次工作都会使用原影片名称加上时间戳，因此不会覆盖较早的输出。

例如，名为 `demo.mp4` 的影片可能产生：

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

`English` 来自 **Translate to** 输入的目标语言。所有翻译输出均使用 `translated_<语言>` 格式；例如输入 `中文` 时，将产生 `translated_中文.srt`、`translated_中文_styled.ass` 和 `translated_中文_subtitled.mp4`。Windows 文件名不支持的字符会自动改为 `_`。

`*_subtitle_job.json` 会保存工作设定。使用 **Open subtitle job** 可手动恢复项目；应用程式启动时不会自动开启上一次项目。

## 命令列使用

GUI 会调用 `subtitle_pipeline.py`，也可直接从命令列执行：

```powershell
python subtitle_pipeline.py `
  --video "C:\Videos\demo.mp4" `
  --script "C:\Videos\script.txt" `
  --output ".\output" `
  --model "your-lm-studio-model-id" `
  --source-language zh `
  --target-language English
```

## 说明

- 影片语音决定哪些字幕出现及其时间码；剧本只用作措辞与翻译参考，未使用的剧本内容不会被强制加到影片上。
- 发布前请检查人名、界面名称、时间点和翻译内容。
- LM Studio 的卸载操作只会释放所选模型，不会强制清理系统 RAM。
