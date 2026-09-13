# Step 1：部署 Studio Runtime、Qwen3-TTS 与 VoxCPM2

这是所有主机与副机都必须完成的基础部署。完成本页后，再继续 [`Step 2：ACE-Step 1.5 主机／副机部署`](step2.md)。

## 1. 准备完整项目

下载／Clone GitHub 源码，再把 Google Drive 的完整 `ai_libraries_common` 解压到项目根目录。

只备份或下载 `ai_libraries_common` 并不足够；根目录中的 Studio 源码、BAT、requirements 和 workflow JSON 也必须保留。基本结构应类似：

```text
minimax h3 reference r2v/
├─ ai_libraries_common/
├─ models/
├─ director_cut_studio.py
├─ run_h3_prompt_studio.bat
├─ install_qwen3_tts_runtime.bat
└─ download_qwen3_tts_model.bat
```

完整 Windows runtime 下载：

- [Google Drive：ai_libraries_common](https://drive.google.com/file/d/1mC_GpmCuYw7zaQPfkaqtQVXTSt6DlRsM/view?usp=drive_link)

## 2. 安装 Qwen3-TTS runtime 与模型

在项目根目录依照以下顺序执行：

```powershell
.\install_qwen3_tts_runtime.bat
.\download_qwen3_tts_model.bat
```

第一条命令建立：

```text
ai_libraries_common/qwen_tts_runtime/
qwen_tts_support/
```

第二条命令会下载约 2.5GB 的 Qwen 模型到：

```text
models/Qwen3-TTS-12Hz-0.6B-CustomVoice/
```

## 3. 安装可选的 VoxCPM2

Qwen 下载脚本不会自动下载 VoxCPM2。需要使用 VoxCPM2 Local 时执行：

```powershell
.\ai_libraries_common\python_env\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='openbmb/VoxCPM2', local_dir=r'models\VoxCPM2')"
```

完成后模型目录应包含：

```text
models/
├─ Qwen3-TTS-12Hz-0.6B-CustomVoice/
└─ VoxCPM2/
```

不使用 VoxCPM2 时可以跳过这一步。

## 4. 验证基础 Runtime

执行：

```powershell
.\ai_libraries_common\python_env\python.exe .\qwen3_tts_setup.py verify
```

看到以下信息代表 Qwen 部署完整：

```text
Qwen3-TTS isolated runtime is ready
Qwen3-TTS model is ready
```

VoxCPM2 权重会在 Studio Settings 或点击 `Vox` 时再次检查。

## 5. 第一次启动 Studio

```powershell
.\run_h3_prompt_studio.bat
```

如果 Studio 无法打开，优先确认：

- `ai_libraries_common/python_env/python.exe` 存在；
- 项目根目录和 `ai_libraries_common` 来自同一个完整版本；
- 防毒软件没有隔离 Python、FFmpeg 或 BAT；
- 路径没有被移动到只读目录。

## 下一步

- 继续部署音乐主机／副机：[`step2.md`](step2.md)
- 返回主说明：[`README.md`](README.md)

