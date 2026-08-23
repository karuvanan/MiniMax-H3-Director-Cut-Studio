# MiniMax H3 Director Cut Studio

一个以 Adobe Premiere Pro 剪辑逻辑为参考的本地 PySide6 导演工作台。它可以管理图片、视频和音频素材，在多轨 Timeline 上规划 Shot、Dialogue、Marker、Ending Hold 与 Prompt，生成 MiniMax H3 Ref2VA 提示词，并把当前有效素材及参数提交到 ComfyUI。

complete library file can found at google drive:
https://drive.google.com/file/d/1mC_GpmCuYw7zaQPfkaqtQVXTSt6DlRsM/view?usp=drive_link

example output:
https://youtu.be/hALjq11lK_s

<img width="1280" height="769" alt="WhatsApp Image 2026-08-24 at 12 39 54 AM" src="https://github.com/user-attachments/assets/ed7575ea-8868-4b54-8dd1-00a1810f1fcf" />


<img width="1600" height="698" alt="WhatsApp Image 2026-08-23 at 5 08 24 PM" src="https://github.com/user-attachments/assets/365a0bb0-0a7b-4f64-b323-0b71e34a1847" />

<img width="1474" height="2080" alt="Screenshot 2026-08-23 214016111" src="https://github.com/user-attachments/assets/345e1d79-455f-4836-bffb-8e138aa20ee4" />

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
- RTX Video Super Resolution：`2x`，所以默认最终图约为 `2048 × 1152`

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

Design 页面通过 OpenAI-compatible API 连接 LM Studio。当前 `design_ai.env` 使用：

```text
Base URL:
http://192.168.0.185:1234/v1

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

`192.168.0.185` 是开发机的局域网地址。其他使用者必须在 Design 设置或 `design_ai.env` 中改成自己的 LM Studio 地址和模型 ID。

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

下表来自当前连接的 ComfyUI `http://192.168.0.185:8189/object_info`。`comfy_extras.*` 属于较新版本 ComfyUI 的内置扩展；`custom_nodes.*` 需要相应自定义节点包。

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
ModelSamplingAuraFlow, RAMCleanup, RTXVideoSuperResolution, SaveImage,
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
H3_COMFYUI_URL=http://192.168.0.185:8189
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
H3_DESIGN_LM_STUDIO_BASE_URL="http://192.168.0.185:1234/v1"
H3_DESIGN_LM_STUDIO_MODEL="hauhaucs/qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp-gguf/qwen3.8-27b-uncensored-hauhaucs-aggressive-q5_k_p.gguf"
H3_DESIGN_TIMEOUT=900
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
- 只有拖入 Timeline 的素材才会连接并激活到 H3 workflow。
- Timeline 以 `0.5s` 为一格执行 snap。
- 支持动态增加/删除 V 与 A 轨、多层视频合成、Opacity、Blend Mode、Mute、Solo、Volume、Pan、锁定和轨道高度。
- Clip 支持速度、源入点/出点、淡入淡出与转场。
- Selection Tool 可移动 clip 及 Program Monitor 文字；Hand Tool 用于平移 Timeline。
- Type Tool 支持 On-screen Text、Dialogue、Voice-over 与 Lyrics；Dialogue 另有 Speaker、Language、Delivery、Lip Sync 和所属 Shot。
- Shot Tool 在视觉轨拖出时间范围，定义 Framing、Camera angle、Camera movement、Subject action、Environment response、Additional direction 与 Shot Prompt Preset。
- Prompt Tool 点击图片 clip 时会带入 BLIP visual caption，也可为其他元素加入专属提示词。
- Marker Tool、Creative Brief、Visual Style、Transition、Ending Hold、Constraints、Soundscape 与 Music 会共同自动生成 Director H3 Prompt。
- 项目保存格式为 `.h3director.json`，支持 Undo/Redo。
- Program Monitor 在生成过程中显示进度遮罩，完成后保持最终视频，直到点击 New Project，并提供 Export link。

## H3 Prompt Skills

Skill 始终使用两层绑定：

```text
skill default/
└─ h3-prompt-writing/
   ├─ SKILL.md
   └─ references/

skill special/
├─ minimalist-product-ad-generator/
├─ music-video-subtitle-generator/
└─ ...每个含 SKILL.md 的子目录
```

- Default 固定为 `h3-prompt-writing`，负责 MiniMax H3 官方 Ref2VA 结构。
- Special 提供场景/风格规则；选择 `None` 时只应用 Default。
- 实际组合始终是 `Default + Special`，Special 不会替代官方结构。

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

- 图片使用 Pillow 与 BLIP。
- 视频使用 FFprobe 获取元数据，并抽取开头 10%、中段 50%、结尾 90% 多帧进行 BLIP 分析。
- 音频按 8 秒分块流式解码，总解码长度不超过 Timeline 秒数。
- 音频先执行 VAD，再只对语音区间执行 Whisper，并以 FFT 估算节拍。
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

```powershell
.\ai_libraries_common\python_env\python.exe -m unittest discover -v
```
