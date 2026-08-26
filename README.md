# MiniMax H3 Director Cut Studio

一个以 Adobe Premiere Pro 剪辑逻辑为参考的本地 PySide6 导演工作台。它可以管理图片、视频和音频素材，在多轨 Timeline 上规划 Shot、Dialogue、Marker、Ending Hold 与 Prompt，生成 MiniMax H3 Ref2VA 提示词，并把当前有效素材及参数提交到 ComfyUI。

## 下载与快速开始

- 当前应用版本：[`v0.2.4-alpha.5`](VERSION)
- 修正与版本记录：[`CHANGELOG.md`](CHANGELOG.md)
- [MiniMax H3 Director Cut Studio 教程](https://lcz.me/topic/1317/minimax-h3-director-cut-studio-%E6%95%99%E7%A8%8B-%E6%9B%B4%E6%96%B0%E5%9C%A8%E7%AC%AC%E4%B8%80%E6%A5%BC)
- [完整 Windows runtime（Google Drive）](https://drive.google.com/file/d/1mC_GpmCuYw7zaQPfkaqtQVXTSt6DlRsM/view?usp=drive_link)
- [示范输出影片（YouTube）](https://youtu.be/hALjq11lK_s)
- 下载源码及 runtime 后，从项目根目录执行 `run_h3_prompt_studio.bat`。

源码仓库不会包含 Python runtime、FFmpeg、BLIP／Whisper 权重、ComfyUI checkpoint 或生成影片。完整 runtime 应解压到 `ai_libraries_common/`，模型则依照下方清单分别放进 Studio 与 ComfyUI 的模型目录。

版本规则：基础版本使用 `v0.2.4-alpha` 格式，三个基础数字位只使用 `0–9`。同类小优化不改变前面的基础版本，只递增 alpha 后缀，例如 `v0.2.4-alpha.1`、`v0.2.4-alpha.2`。只有进入新的功能版本时才提升基础数字；届时 `v0.2.9-alpha` 的下一基础版本为 `v0.3.0-alpha`。每次更新都会同步写入 `VERSION` 与 `CHANGELOG.md`。Project JSON 的 format version 独立管理，只有 `.h3director.json` 保存结构改变时才提升。

<img width="1280" height="769" alt="MiniMax H3 Director Cut Studio" src="https://github.com/user-attachments/assets/ed7575ea-8868-4b54-8dd1-00a1810f1fcf" />

<img width="1600" height="698" alt="Director Cut Timeline" src="https://github.com/user-attachments/assets/365a0bb0-0a7b-4f64-b323-0b71e34a1847" />

<img width="1474" height="2080" alt="Design workspace" src="https://github.com/user-attachments/assets/345e1d79-455f-4836-bffb-8e138aa20ee4" />

默认主工作流支持最多 **9 张图片、3 段参考视频和 3 段独立音频**：

```text
video_minimax_h3_r2v_9image_3audio_3video_api.json
```

Design 页面使用以下工作流生成概念参考图：

```text
Z-Image_Text2Image_for_webui_t2i_api.json
```

> 重要：模型权重没有包含在应用源代码中。请先按下方清单准备所有模型，并保持文件名完全一致。模型下载、使用许可及商用权限由使用者自行确认。

## 首次运行前必须准备的模型

### 1. MiniMax H3 Ref2VA 主工作流

以下是默认 `video_minimax_h3_r2v_9image_3audio_3video_api.json` 中所有会直接读取外部模型文件的节点，没有其他隐藏 checkpoint。

| 节点 ID | 节点类型 | 准确文件名 | 建议放置目录 | 用途 | 必需 |
|---:|---|---|---|---|:---:|
| 127 | `UNETLoader` | `minimax_h3_ref2va_int8_convrot.safetensors` | `ComfyUI/models/diffusion_models/` | H3 Ref2VA 主扩散模型 | 是 |
| 128 | `CLIPLoader` | `qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors` | `ComfyUI/models/text_encoders/` | H3/Qwen3-VL 多模态文字与参考素材编码器 | 是 |
| 119 | `VAELoader` | `minimax_h3_video_vae_fp16.safetensors` | `ComfyUI/models/vae/` | H3 视频 VAE | 是 |
| 120 | `VAELoader` | `minimax_h3_audio_vae_fp32.safetensors` | `ComfyUI/models/vae/` | H3 原生音频 VAE | 是 |
| 150 | `MiniMaxH3TurboLoRA` | `minimax_h3_turbo_v4_step600_ema.safetensors` | `ComfyUI/models/loras/` | H3 Turbo 8-step LoRA | 是 |

当前工作流的主要推理参数：

- Sampler：`res_multistep`
- Scheduler：`simple`
- Sampling steps：`8`
- Denoise：`1.0`
- 输出：`24 FPS`
- RTX Video Super Resolution：默认 `2x / ULTRA`

如果你的 ComfyUI 使用旧目录布局，`CLIPLoader` 可能从 `ComfyUI/models/clip/` 读取，`UNETLoader` 也可能从 `ComfyUI/models/unet/` 读取。应以节点下拉菜单实际扫描到的目录为准；也可以在 ComfyUI 的 `extra_model_paths.yaml` 中映射模型目录。现代 ComfyUI 通常使用 `diffusion_models`、`text_encoders`、`vae` 与 `loras`。

### 2. Z-Image Design 概念图工作流

以下是 `Z-Image_Text2Image_for_webui_t2i_api.json` 中所有会读取外部模型文件的节点：

| 节点 ID | 节点类型 | 准确文件名 | 建议放置目录 | 用途 | 必需 |
|---:|---|---|---|---|:---:|
| 16 | `UNETLoader` | `z_image_turbo_bf16.safetensors` | `ComfyUI/models/diffusion_models/` | Z-Image Turbo 图像生成模型 | 是 |
| 18 | `CLIPLoader` | `qwen_3_4b.safetensors` | `ComfyUI/models/text_encoders/` | Z-Image 的 Qwen 文字编码器，类型为 `qwen_image` | 是 |
| 17 | `VAELoader` | `ae.safetensors` | `ComfyUI/models/vae/` | Z-Image 图像 VAE | 是 |

当前 Z-Image 默认参数：

- Base resolution：`1024 × 576`
- Sampler：`euler`
- Scheduler：`simple`
- Steps：`8`
- CFG：`1.0`
- Denoise：`1.0`
- `ModelSamplingAuraFlow` shift：`3`
- RTX Video Super Resolution：当前 Z-Image API 已移除；默认输出保持 Base resolution

Design 页面可以在 `Image Generation Checkpoint` 下拉菜单选择 ComfyUI 的 `UNETLoader` 模型。当前工作流仍固定搭配 `qwen_3_4b.safetensors` 与 `ae.safetensors`；换用其他 diffusion checkpoint 时，必须确认它与这组 Z-Image text encoder/VAE 兼容，否则会在采样或解码阶段失败。

### 3. 本地 BLIP 与 Whisper 模型

这两组模型由桌面程序使用，不放入 ComfyUI：

| 功能 | 模型 | 项目内路径 | 必需情况 |
|---|---|---|---|
| 图片及视频抽帧描述 | `Salesforce/blip-image-captioning-base` | `ai_libraries_common/models/models--Salesforce--blip-image-captioning-base/` | 使用图片识别、Prompt Tool 自动 caption 或 Design 图像分析时必需 |
| VAD 后语音识别 | `openai/whisper-small` | `ai_libraries_common/models/openai--whisper-small/` | 使用音频/视频语音识别时必需 |

BLIP 当前固定读取本地 snapshot：

```text
ai_libraries_common/models/models--Salesforce--blip-image-captioning-base/snapshots/82a37760796d32b1411fe092ab5d4e227313294b
```

路径定义在 `ai_libraries_common/runtime_config.json`。BLIP 与 Whisper 均使用离线本地文件；缺少权重时不会自动从网络静默下载。

### 4. LM Studio 模型

Design 页面通过 OpenAI-compatible API 连接 LM Studio。公开配置建议先使用本机地址：

```text
Base URL:
http://127.0.0.1:1234/v1

Model ID:
hauhaucs/qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp-gguf/qwen3.8-27b-uncensored-hauhaucs-aggressive-q5_k_p.gguf

GGUF filename:
Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q5_K_P.gguf
```

若在 LM Studio 中启用该模型的视觉输入，还需要与它匹配的 projection 文件：

```text
mmproj-Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-BF16.gguf
```

当前 Design 流程会先用本地 BLIP 把生成图转成 caption，再把文字 caption 交给 LM Studio，因此 **mmproj 对现有纯文字请求不是硬性必需**；只有直接把图片提交给 LM Studio 的视觉模型模式才需要它。GGUF 由 LM Studio 管理，不要放入 ComfyUI 的模型目录。

如果 LM Studio 位于其他电脑，请在 Design 设置或 `design_ai.env` 中改成对应的局域网地址和模型 ID。

## 推荐的模型目录结构

```text
ComfyUI/
└─ models/
   ├─ diffusion_models/
   │  ├─ minimax_h3_ref2va_int8_convrot.safetensors
   │  └─ z_image_turbo_bf16.safetensors
   ├─ text_encoders/
   │  ├─ qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors
   │  └─ qwen_3_4b.safetensors
   ├─ vae/
   │  ├─ minimax_h3_video_vae_fp16.safetensors
   │  ├─ minimax_h3_audio_vae_fp32.safetensors
   │  └─ ae.safetensors
   └─ loras/
      └─ minimax_h3_turbo_v4_step600_ema.safetensors
```

模型放好后重启 ComfyUI，并逐一检查对应 Loader 节点的下拉菜单。不要只把文件复制进目录而不重启或刷新模型列表。

## 节点与自定义节点依赖

下表来自当前工作流使用的 ComfyUI 节点类型。可以通过 `http://YOUR_COMFYUI_HOST:8189/object_info` 检查自己的节点安装；`comfy_extras.*` 属于较新版本 ComfyUI 的内置扩展，`custom_nodes.*` 需要相应自定义节点包。

| 节点 | Python module | 来源/处理方式 | 额外模型文件 |
|---|---|---|---|
| `MiniMaxH3ReferenceToVideo` | `comfy_extras.nodes_minimax_h3` | 更新 ComfyUI；H3 原生节点 | 使用上方 H3 UNET、CLIP、双 VAE |
| `MiniMaxH3TurboLoRA` | `custom_nodes.comfyui_fearnworksnodes` | 安装当前服务器使用的 FearNWorks 节点包 | H3 Turbo LoRA |
| `MiniMaxH3MemoryEfficientSolAttentionPatch` | `custom_nodes.comfyui_fearnworksnodes` | 同上 | 无 |
| `VRAM_Debug` | `custom_nodes.comfyui_fearnworksnodes` | 同上 | 无 |
| `RTXVideoSuperResolution` | `custom_nodes.comfyui_nvidia_rtx_nodes` | 安装 `Nvidia_RTX_Nodes_ComfyUI`；仅支持 NVIDIA RTX GPU | 无独立 `.safetensors` checkpoint |
| `RAMCleanup` | `custom_nodes.comfyui_memory_cleanup` | 安装当前服务器使用的 Memory Cleanup 节点包 | 无 |
| `VRAMCleanup` | `custom_nodes.comfyui_memory_cleanup` | 同上 | 无 |
| `ResolutionSelector` | `comfy_extras.nodes_resolution` | ComfyUI 内置扩展 | 无 |
| `LoadVideo` / `GetVideoComponents` / `CreateVideo` / `SaveVideo` | `comfy_extras.nodes_video` | ComfyUI 内置视频节点 | 无 |
| `VAEDecodeAudio` | `comfy_extras.nodes_audio` | ComfyUI 内置音频节点 | 使用已经加载的 H3 Audio VAE |
| `ModelAttentionBackend` / `ModelSamplingAuraFlow` | `comfy_extras.nodes_model_advanced` | ComfyUI 内置高级模型节点 | 无 |
| `ComfyMathExpression` | `comfy_extras.nodes_math` | ComfyUI 内置数学节点 | 无 |
| `PrimitiveFloat` / `PrimitiveStringMultiline` | `comfy_extras.nodes_primitive` | ComfyUI 内置 primitive 节点 | 无 |
| `EmptySD3LatentImage` | `comfy_extras.nodes_sd3` | ComfyUI 内置 SD3 latent 节点 | 无 |
| `UNETLoader` / `CLIPLoader` / `VAELoader` / `KSampler` / `SaveImage` | `nodes` | ComfyUI 核心节点 | Loader 使用上方列出的模型 |

自定义节点建议通过 ComfyUI Manager 的 **Find Missing Nodes** 安装。官方说明：

- [ComfyUI：安装自定义节点](https://docs.comfy.org/installation/install_custom_node)
- [ComfyUI Manager：查找与管理节点包](https://docs.comfy.org/manager/pack-management)
- [NVIDIA RTX Video Super Resolution 节点](https://github.com/Comfy-Org/Nvidia_RTX_Nodes_ComfyUI)

### 不需要额外模型的工作流节点

为避免误以为还有遗漏，下面列出两个 API 中其余全部节点类型。这些节点只负责连接、采样、条件处理、媒体 I/O、解码、放大或内存清理，不会再读取新的 checkpoint：

```text
H3 workflow:
BasicGuider, BasicScheduler, ComfyMathExpression, CreateVideo,
GetVideoComponents, KSamplerSelect, LoadAudio, LoadImage, LoadVideo,
MiniMaxH3MemoryEfficientSolAttentionPatch, MiniMaxH3ReferenceToVideo,
ModelAttentionBackend, PrimitiveFloat, PrimitiveStringMultiline,
RAMCleanup, RandomNoise, ResolutionSelector, RTXVideoSuperResolution,
SamplerCustomAdvanced, SaveVideo, VAEDecode, VAEDecodeAudio,
VRAM_Debug, VRAMCleanup

Z-Image workflow:
CLIPTextEncode, ConditioningZeroOut, EmptySD3LatentImage, KSampler,
ModelSamplingAuraFlow, RAMCleanup, SaveImage,
VAEDecode, VRAM_Debug, VRAMCleanup
```

## 旧版 API 的兼容模型

以下文件只在手动载入旧工作流时使用，**默认 9 Image + 3 Audio + 3 Video 工作流不需要它们**：

```text
video_minimax_h3_r2v api.json
video_minimax_h3_r2v API 3IMAGE 1AUDIO 1VIDEO.json
```

| 节点类型 | 旧版文件名 | 目录 |
|---|---|---|
| `UNETLoader` | `minimax_h3_ref2va_pruned_fp8_scaled.safetensors` | `ComfyUI/models/diffusion_models/` |
| `CLIPLoader` | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `ComfyUI/models/text_encoders/` |
| `VAELoader` | `minimax_h3_video_vae_fp16.safetensors` | `ComfyUI/models/vae/` |
| `VAELoader` | `minimax_h3_audio_vae_fp32.safetensors` | `ComfyUI/models/vae/` |

旧版 workflow 使用 `20 steps`，没有当前默认工作流中的 `minimax_h3_turbo_v4_step600_ema.safetensors` 节点。

## 安装与运行

### 项目内置运行环境

程序只使用 `ai_libraries_common`，不依赖系统 Python 或系统 PATH。当前已经验证的版本：

| 组件 | 版本/路径 |
|---|---|
| Python | `3.11.15` — `ai_libraries_common/python_env/python.exe` |
| PySide6 | `6.11.2` |
| Pillow | `12.2.0` |
| Torch | `2.12.1+cu126` |
| CUDA runtime | `12.6` |
| Transformers | `5.12.1` |
| FFmpeg / FFprobe | `ai_libraries_common/engine_ffmpeg/bin/`，2026-05-25 build |

### 完整 Python library 版本清单

以下清单直接读取自当前项目的 `ai_libraries_common/python_env`，共 **44 个已安装 distribution**。这是应用实际运行环境的版本快照，不是建议版本范围：

```text
accelerate==1.14.0
annotated-doc==0.0.4
anyio==4.14.1
certifi==2026.6.17
click==8.4.2
colorama==0.4.6
filelock==3.29.0
fsspec==2026.4.0
h11==0.16.0
hf-xet==1.5.1
httpcore==1.0.9
httpx==0.28.1
huggingface_hub==1.21.0
idna==3.18
Jinja2==3.1.6
markdown-it-py==4.2.0
MarkupSafe==3.0.3
mdurl==0.1.2
mpmath==1.3.0
networkx==3.6.1
numpy==2.4.6
packaging==26.0
pillow==12.2.0
pip==26.1.2
psutil==7.2.2
Pygments==2.20.0
PySide6==6.11.2
PySide6_Addons==6.11.2
PySide6_Essentials==6.11.2
PyYAML==6.0.3
regex==2026.6.28
rich==15.0.0
safetensors==0.8.0
setuptools==70.2.0
shellingham==1.5.4
shiboken6==6.11.2
sympy==1.14.0
tokenizers==0.22.2
torch==2.12.1+cu126
tqdm==4.68.3
transformers==5.12.1
typer==0.25.1
typing_extensions==4.15.0
wheel==0.47.0
```

额外运行环境信息：

```text
Python build: 3.11.15 | packaged by Anaconda, Inc. | MSC v.1942 64 bit (AMD64)
Platform: Windows 10.0.26200
Torch CUDA runtime: 12.6
FFmpeg: 2026-05-25-git-34dfa8bf2b-full_build-www.gyan.dev
```

当前环境已经通过依赖一致性检查：

```powershell
.\ai_libraries_common\python_env\python.exe -m pip check
# No broken requirements found.
```

日后如果更新 library，可用以下命令重新取得完整清单：

```powershell
.\ai_libraries_common\python_env\python.exe -m pip freeze --all
```

> `pip freeze --all` 可能把由 Conda 打包的 `pip` 显示为本机 build URI；README 中已将它规范化为实际安装版本 `pip==26.1.2`。不要把开发机的 `file:///...` URI 复制到其他电脑的 requirements 文件。

运行：

```powershell
.\run_h3_prompt_studio.bat
```

默认启动 `director_cut_studio.py`。旧 Tkinter 程序保留在 `h3_prompt_studio.py`。

### ComfyUI 设置

主页可以选择 Aspect Ratio，并测试 ComfyUI 连接。设置保存在项目根目录 `.env`：

```dotenv
H3_COMFYUI_URL=http://127.0.0.1:8189
H3_ASPECT_RATIO=16:9
H3_MEGAPIXELS=1.0
H3_SAMPLING_STEPS=8
H3_DENOISE=1.0
H3_RTX_VIDEO_SUPER_RESOLUTION=true
H3_HISTORY_POLL_INTERVAL=1.0
H3_GENERATION_TIMEOUT=1800
H3_HTTP_REQUEST_TIMEOUT=30
```

请把 URL 改成自己的 ComfyUI 地址。Pre-run Preview 使用 `0.2 MP` 且跳过 RTX upscaling；Accept 会在正式 `1.0 MP` 生成中复用 seed，Reject 会用新 seed 重新生成低分辨率预览。

### Design AI 设置

`design_ai.env` 保存 Design 页面的服务、模型与 Z-Image 参数；API key 不写入该文件。主要配置如下：

```dotenv
H3_DESIGN_PROVIDER="lm_studio"
H3_DESIGN_LM_STUDIO_BASE_URL="http://127.0.0.1:1234/v1"
H3_DESIGN_LM_STUDIO_MODEL="hauhaucs/qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp-gguf/qwen3.8-27b-uncensored-hauhaucs-aggressive-q5_k_p.gguf"
H3_DESIGN_TIMEOUT=900
H3_DESIGN_AUTO_SEMANTIC_ENRICHMENT=false
H3_DESIGN_UNLOAD_LM_AFTER_SEMANTIC_ENRICHMENT=true
H3_DESIGN_GENERATE_COMFY_IMAGES=true
H3_DESIGN_IMAGE_CHECKPOINT="z_image_turbo_bf16.safetensors"
H3_DESIGN_IMAGE_WIDTH=1024
H3_DESIGN_IMAGE_HEIGHT=576
H3_DESIGN_IMAGE_STEPS=8
H3_DESIGN_IMAGE_CFG=1.0
```

## Design 页面执行顺序

点击 `Create Director Design JSON` 后：

1. LM Studio 根据用户构思先建立结构化计划，决定视频秒数、Shot 和需要生成多少张参考图。
2. 自动卸载 LM Studio 模型，释放显存。
3. ComfyUI 按 `media_requests` 逐张执行 Z-Image，并在小视窗显示 thumbnail。
4. 本地 BLIP 分析每张概念图，写回实际视觉 caption 与关键词。
5. Z-Image 工作流执行 `VRAM_Debug → RAMCleanup → VRAMCleanup`，程序随后请求 ComfyUI unload/free。
6. LM Studio 根据原计划与 BLIP 结果完成最终 Director Design JSON。
7. LM Studio 再次自动 unload。
8. 点击 `Apply to H3 Workspace` 后关闭 thumbnail 视窗，把素材、时间范围、Shot、主题文字和提示词带回 H3 工作台。

处理期间会显示转圈遮罩及实时阶段。默认 Design timeout 为 900 秒；H3 generation timeout 为 1800 秒。

## Director Cut 工作区

- Media Pool 会随面板宽度自动重排，素材使用 `P1 / V1 / A1` 简称。
- Recognition 检查器分为 `RAW ANALYSIS` 与 `AI SEMANTIC` 两页。后者可手动执行，也可开启 `AUTO AI SEMANTIC ENRICHMENT`，并复用 Design 当前选择的 LM Studio／Online GPT 服务与模型。
- Media Pool 或 Timeline 素材执行 AI Enrich 时，对应 Media Pool 卡片会显示半透明 processing overlay；分析在后台执行，不会冻结主界面。
- 只有拖入 Timeline 的素材才会连接并激活到 H3 workflow。
- 同一个 Media Pool Source 可以重复拖入 Timeline。每次重复使用都是独立 Clip Instance，可分别调整时间、轨道、速度、Source In/Out、淡入淡出、转场及 Clip Prompt；它们仍共享同一份识别/AI Enrich 结果，而且只占用一个实体 H3 Picture／Video／Audio reference slot。
- Studio 与 Design 内统一使用不会改变的素材编号 `@P1 / @V1 / @A1`。每个生成 Segment 提交前，编译器才按该段实际激活的素材转换成 MiniMax H3 所需的 `<Picture N> / <Video N> / <Audio N>`；旧项目中的 angle-bracket 编号会按原始 Media Pool 编号安全迁移，未激活引用不会误指向别的素材。
- Clip、Shot、Marker 与编辑范围仍以 `0.5s` 为一格执行 snap；播放头和 Program Monitor 播放滑杆不 snap，可按毫秒连续拖动。滑杆使用按下位置作为相对拖动锚点，不会在开始向左或向右时突然跳到端点；拖动期间画面 seek 会轻量 debounce，释放后精确落在所选时间。
- 支持动态增加/删除 V 与 A 轨、多层视频合成、Opacity、Blend Mode、Mute、Solo、Volume、Pan、锁定和轨道高度。
- AI Design 可按内容自动建立 V4/V5… 与 A4/A5… 编辑轨：画面／标题使用 V 轨，Dialogue、Voice-over、Lyrics 使用独立 A 轨。编辑轨最多 V16/A16；MiniMax H3 每个原生 15 秒任务仍遵守工作流的 9 Picture、3 Video、3 Audio 实体参考槽，并只选择该时间窗有关的素材。
- Clip 支持速度、源入点/出点、淡入淡出与转场。
- Selection Tool 可移动 clip 及 Program Monitor 文字；Hand Tool 用于平移 Timeline。
- Type Tool 支持 On-screen Text、Dialogue、Voice-over 与 Lyrics；文字层可以放入任意空 V Track，不需要与原素材重叠。Dialogue 另有 Speaker、Language、Delivery、Lip Sync 和所属 Shot。
- Type clip 两端使用高亮边缘进行 trimming，支持 Timeline snap、Undo 与 Redo。
- Shot Tool 在视觉轨拖出时间范围，定义 Framing、Camera angle、Camera movement、必须完成的 Core Action、必须保持的 Continuity State、Required Environment Response、可以省略的 Optional Flourish、Additional Direction 与 Shot Prompt Preset。
- Design 与 Shot Tool 共用 H3 动作预算：每 5 秒最多三个必须完成的物理动作、两个必要接触后果和两个可选装饰。超出预算时优先把次要攻击、重复反击与纯装饰降级；最终 Prompt 明确要求先省略 Optional Flourish，不能因此延迟、削弱或重播 Core Action。Design Summary 会列出 `within / optional trimmed / priority compressed` 状态及压缩说明。
- Prompt Tool 点击图片 clip 时会带入 BLIP visual caption，也可为其他元素加入专属提示词。
- Marker Tool、Creative Brief、Visual Style、Transition、Ending Hold、Constraints、Soundscape 与 Music 会共同自动生成 Director H3 Prompt。
- `AUTO SYNC FROM TIMELINE` 启用时会执行 Timeline Prompt Reconcile：以当前素材引用、Shot、Dialogue、Voice-over、Lyrics、Ending Hold 与音频 transcript 为 source of truth，自动重写 Creative Brief 与 Director H3 Prompt，并忽略已被替换的 Design placeholder，不需要重新进入 Design 页面。
- 项目保存格式为 `.h3director.json`，支持 Undo/Redo。
- Program Monitor 使用可拖动的左右分割线：左侧 `TIMELINE SOURCE` 显示当前时间轴素材与文字合成，右侧 `GENERATED OUTPUT` 显示最终 MP4。两侧采用 1px 合法最小宽度，分割线可以连续推到视觉上的最左/最右，但不会触发 Qt 自动 collapse、跳边或把手卡死；当前比例会随项目保存，并为后续 Depth / Pose 分析视图保留扩展空间。
- 播放生成视频时，右侧 MP4 作为主时钟同步 Timeline playhead、时间标签、滑杆及左侧素材画面；拖动 Timeline 或滑杆也会反向定位生成视频。
- 对大于 1080p、高码率或超过 100MB 的成片，Studio 会在后台建立缓存用的 720p Monitor Proxy，避免 Windows 播放器停在第一帧；Export 与项目归档仍使用未经修改的原始 Master。
- 生成过程中仍显示进度遮罩；完成后成片保持在右侧，直到点击 New Project，并提供 Export link。
- 每次 Preview / Run 完成后，Studio 会把成片复制为当前 `example` 工作文件夹中的 `generated_preview.mp4` 或 `generated_output.mp4`，并自动保存 `director_project.h3director.json`。使用 Open Project 打开这份项目时，会同时恢复成片、左右分割比例及对应 Timeline 起点。

## Smart Long Render（突破 15 秒）

工作区仍然显示一条完整 Timeline，不需要手动切割。生成行为由 Work Area 长度自动决定：

- `≤ 15s`：继续使用原来的单次 H3/ComfyUI 提交流程，不分段、不拼接。
- `> 15s`：自动启用 Shot-aware Smart Long Render；每个原生生成任务最长 15 秒，Studio 在后台顺序生成并重新组装为一个 Master。
- 当 Shot Blocks 覆盖至少 80% Work Area 时，Shot 起点／终点成为优先切点；少于 3 秒的微小动作（例如 1 秒 bullet-time）会向后合并，通常形成约 3–6 秒 Render Units。若项目没有完整 Shot 结构，则继续使用稳定的 `0–15 / 14–29 / 28–43…` 规划。
- Shot Render Unit 与稳定 seed 绑定。修改一秒动作时，只重新生成包含该时间的 Render Unit；continuity handle 内发生的修改不会令下一个已缓存 Shot 连锁失效。
- 每段的 Shot、Dialogue、Marker 与 Ending 指令会过滤到该段，并从全局时间自动换算成段内 `0–15s` 时间。
- 非第一段会把上一段最后 **24 帧（24 fps，正好 1 秒）**提取成无音频的隐藏 Video reference，只作为动作、人物位置、镜头方向、光线和环境的时间上下文；提示词明确禁止重播上一段动作。Hard Cut 会清空这项上下文。系统会优先使用空闲 Video slot；三个实体 Video slot 都占满时，只临时让出最低优先级的 Auto 参考，不会移除用户强制 Active 的素材。
- ComfyUI 一次只执行一段，每段后请求 unload/free VRAM；单段失败会自动重试，已成功的段会写入 manifest，避免全部重来。
- 未改变且 fingerprint 相同的段会直接复用缓存；编辑局部 Shot 或素材后，只重新生成受影响的内部段，再重新组装 Master。
- Timeline ruler 下方有一条 6px `Render Status` 状态条，并按隐藏 Segment 显示：绿色为已生成且可复用、黄色为编辑后需要重算、蓝色为正在生成、红色为生成失败、灰色为尚未生成。Hover 可查看该 Segment 的真实时间范围和状态。
- 修改 Shot、Marker、Transition、文字层、Clip Prompt、素材时间／属性时，只把与修改前后时间范围相交的 Segment 标成黄色；修改全局视觉风格、Creative Brief、声音设计或影响合成的轨道属性时，才会把所有 Segment 标成黄色。
- 生成时当前 Segment 自动变蓝；成功写入 manifest 后立即变绿，失败则保留红色。状态及黄色 dirty Segment 会跟随 Director Project 保存和恢复。
- Program Monitor 在生成期间不会再被全屏遮罩取代：旧 Master／Timeline Source 会继续显示，上方使用横跨左右两个画面的半透明 spinner 和实时阶段文字；右侧生成视频通过 `QVideoSink` 绘制，避免 Windows 原生视频表面穿透遮罩。每个 Shot Unit 下载完成后会立即在右侧循环预览，同时后台继续生成下一段与组装 Master。
- FFmpeg 会裁掉重复的重叠区，将所有段重编码为一个带音频的 `master.mp4`。Program Monitor 与 Export 始终只显示完整 Master。
- Pre-run Preview 会为所有内部段建立稳定 seed；Accept 以 1.0MP 复用同一组 seed。

Smart Long Render 的恢复资料保存在 `.director_cache/generated_outputs/`，项目文件格式为 **version 16**，并记录独立 Timeline Clip Instance、Master、各段 manifest、归档工作文件夹、生成视频时间起点、Program Monitor 分割比例、Prompt Auto Sync 状态，以及 Shot 的 Continuity State、Optional Flourish 与动作预算结果。旧版项目会把原有素材位置自动视为第一次 Timeline 使用；version 15 加入重复出现的 Clip Instance，version 16 加入可执行动作层级。每次 Preview / Run 会预先建立对应的 `example` 工作文件夹；完成后自动写入 `generated_preview.mp4` 或 `generated_output.mp4`、`director_project.h3director.json`，以及长片的 `render_manifest.json`。Design JSON 的 Timeline 长度上限为 600 秒；实际可行长度仍取决于磁盘空间、ComfyUI 稳定性和总生成时间。

Design 页的 `LOAD JSON` 可以载入人工校准或先前保存的 Director Design。若载入的 JSON 尚无预生成图片，点击 Apply 后仍会自动执行所需的 Z-Image reference generation。项目附带的 45 秒长片示范位于：

```text
example/tang_ting_ci_ying_45s_demo/design_plan.json
```

## H3 Prompt Skills

Skill 默认使用两层绑定，并支持由 Special Skill 明确声明独立模式：

```text
skill default/
└─ h3-prompt-writing/
   ├─ SKILL.md
   └─ references/

skill special/
├─ minimalist-product-ad-generator/
├─ music-video-subtitle-generator/
├─ wuxia-blade-film/
└─ ...每个含 SKILL.md 的子目录
```

- Default 固定为 `h3-prompt-writing`，负责 MiniMax H3 官方 Ref2VA 结构。
- Special 提供场景/风格规则；选择 `None` 时只应用 Default。
- 一般 Special 采用 `Default + Special`；在 `SKILL.md` 写入 `<!-- h3-studio-binding: standalone -->` 的 Special 会独立送入 Design，不会同时注入 `h3-prompt-writing`。
- `wuxia-blade-film` 使用标准 `Default + Special` 绑定：`h3-prompt-writing` 负责官方 H3 Ref2VA 结构，它负责物理连续、武器因果、每 5 秒动作预算、15 秒无重播边界、人物／武器／空间／消耗品账本、写实轻功、碎片式镜头和环境同步。英文主文件为 `SKILL.md`，中文对照版为 `SKILL.cn.md`。可直接贴入 Design 的《一叶杀》45 秒 V2 位于 `example/one_leaf_kill_45s_design_requirement.txt`。

Preset 分别保存于独立文件，均支持选择、新增、修改、删除及 `SAVE + APPLY`：

```text
preset_env/creative_brief.env
preset_env/global_visual_style.env
preset_env/transition_language.env
preset_env/constraints_and_technical_rules.env
preset_env/overall_soundscape.env
preset_env/non_diegetic_music.env
```

## 媒体分析与稳定性

- 图片使用 Pillow 与 BLIP；若边缘取样确认素材具有高度一致且与边缘连通的单色背景，会自动建立透明 PNG 衍生素材供预览、识别、Design 与 H3 引用，原图保持不变。复杂背景会安全跳过。
- 视频使用 FFprobe 获取元数据，并抽取开头 10%、中段 50%、结尾 90% 多帧进行 BLIP 分析。
- 音频按 8 秒分块流式解码，总解码长度不超过 Timeline 秒数。
- 音频先执行 VAD，再只对语音区间执行 Whisper，并以 FFT 估算节拍。
- 可选 AI Semantic Enrichment 会在所有基础分析完成后，把有界的原始证据交给 Design 当前的 Qwen/GPT，输出 Summary、Observed Facts、Subjects、Objects、Environment、Camera、Lighting、Temporal Motion、Audio/Speech、H3 Usage 与 Uncertainties。AI 推断独立保存，不会覆盖 BLIP／Whisper 原文。
- AI Enrich 会先根据素材类型和基础证据决定是否需要多区域 BLIP；需要时会补充主体、环境与细节区域 caption，再交给 Qwen/GPT，避免无条件重复分析整张图片。
- 如果被分析素材已经位于 Timeline 且存在重叠 Shot，AI 会返回对应 `shot_adaptations`，自动更新 Subject Action、Environment Response 与 Additional Direction；没有现有 Shot 时不会擅自创建新 Shot。
- Design 后替换 Timeline 素材时，旧素材的 caption、placeholder prompt 与旧 Shot 描述会失效；新素材完成分析后会融合到原有 Shot 和最终 H3 Prompt，而不是被当作额外静态照片叠加。
- 每次结果都校验素材编号、类型与 SHA-256 evidence fingerprint；换素材、修改 Recognition 或 Clip Prompt 后旧结果会标为 Stale，且不会进入 Design 的有效分析上下文。只发送文件 basename，本机绝对路径会先遮蔽。
- Online GPT 模式会把有界的 caption／transcript 证据发送至所配置的远端服务；API key 可沿用本次运行中 Design 页输入的值，或读取当前进程的 `OPENAI_API_KEY`，但不会写入 `design_ai.env` 或项目文件。
- 识别工作在后台 worker 中运行，支持取消、超时与失败回退，不阻塞主界面。
- thumbnail、抽帧、波形与分析结果缓存于 `.director_cache/`。

## 首次启动检查清单

1. 按本 README 放好 8 个 ComfyUI 模型文件：H3 5 个、Z-Image 3 个。
2. 在 LM Studio 准备并加载 Qwen GGUF，启动 Local Server。
3. 启动 ComfyUI，确认启动日志没有 `IMPORT FAILED`。
4. 在 ComfyUI 分别载入两个 API workflow，确认没有红色 missing node。
5. 检查每个 Loader 下拉菜单能找到本 README 中的准确文件名。
6. 在 H3 Studio 首页执行 `Test ComfyUI Connection`。
7. 在 Design 页面测试 LM Studio 连接，然后运行一次小型概念图计划。

也可以直接检查 ComfyUI 节点接口：

```text
http://YOUR_COMFYUI_HOST:8189/object_info/UNETLoader
http://YOUR_COMFYUI_HOST:8189/object_info/CLIPLoader
http://YOUR_COMFYUI_HOST:8189/object_info/VAELoader
http://YOUR_COMFYUI_HOST:8189/object_info/MiniMaxH3ReferenceToVideo
http://YOUR_COMFYUI_HOST:8189/object_info/RTXVideoSuperResolution
```

## 常见问题

### Loader 下拉菜单没有模型

- 检查文件名是否完全一致，包括大小写、下划线和 `.safetensors`。
- 检查模型是否放进正确目录，或是否已经通过 `extra_model_paths.yaml` 映射。
- 重启 ComfyUI；只刷新 H3 Studio 不一定会刷新 ComfyUI 的模型目录缓存。

### `Node ... does not exist`

- 先更新 ComfyUI，取得 `comfy_extras` 内置节点。
- 使用 ComfyUI Manager 的 Find Missing Nodes 安装缺少的 custom node。
- 重启后访问相应 `/object_info/节点名`，确认接口可以返回结果。

### RTX Video Super Resolution 失败

- 该节点只支持 NVIDIA RTX GPU，并需要匹配的 NVIDIA 驱动与节点依赖。
- 可在 Settings 取消 `Enable RTX Video Super Resolution`，先以基础分辨率验证完整生成流程。
- RTX 节点不需要另行下载 `.safetensors` 模型。

### Design 超时

- `H3_DESIGN_TIMEOUT` 是单次 Design 流程的总等待上限，当前默认 900 秒。
- 先检查 LM Studio 是否仍在加载 GGUF、ComfyUI queue 是否有旧任务，以及 Z-Image 是否已经输出图片。
- 可减少参考图数量、宽高或 steps 后重试。

## 测试

高风险流程的标准 Release Gate：

```powershell
.\ai_libraries_common\python_env\python.exe -m unittest -v test_standard_pipeline_regressions.py
```

这四项标准测试固定检查：

1. 稀疏 Picture / Video / Audio 素材的稳定 `P/V/A` 编号、Segment 局部编号、Prompt 标签与实际 H3 节点输入完全一致。
2. AI Design Apply 后移动、改轨、改时间或改 Clip Prompt，会立即重绑重叠 Shot、更新 Creative Brief / H3 Prompt，并在 Undo / Redo 后保持一致。
3. Picture / Video 只能落在 V Track，Audio 只能落在 A Track；错误的 Design track 请求及旧项目错误 lane 会被自动修正。
4. `0–15 / 15–30 / 30–45s` 原生边界不会重叠生成或重播前段动作；后段只使用无声 24 帧运动上下文，而且不会覆盖当前 Segment 的 Video reference slot。

当前完整验证结果：**209 tests passed**。

```powershell
.\ai_libraries_common\python_env\python.exe -m unittest discover -v
```

```text
Ran 209 tests
OK
```
