# SoulX-Singer 长音频修复 · 交接文档（handoff.md）

> 用途：把这份文档交给另一台电脑上的 AI（或你自己），可以**不改环境就接着往下做**。
> 记录了：原始需求 → 根因 → 已改代码（含行号）→ 验证方法与实际数据 → 还没做的事。
> 最后更新：2026-10-31（Asia/Kuala_Lumpur）

---

## 0. 一句话总结

SVC（把人声克隆到目标音频）原来只能处理 **10 分钟以内**，并且 **5 分钟之后输出是静音**；两处都是硬编码 + 一个显存/耗时随时长爆炸的实现造成的。现已全部修好，并用一条 **17 分 35 秒**的歌跑通整首（61 段，9 分 13 秒，输出全长、尾部不再静音）。

---

## 1. 原始需求（用户原话）

> 这是我的一个克隆软件，它可以把我要的人声，克隆去我要的声音内，但是现在它有两个非常严重的问题：
> 1. 处理长的音频被限制在最多 10 分钟；
> 2. 超过 5 分钟以外的音频处理得有问题。
> 现在有两个音频：要把 `prompt.mp3` 的声音克隆到 `target.mp3`。

输入文件（仓库根目录）：`prompt.mp3` = 6.84 s（音色参考），`target.mp3` = **1055.08 s（17 分 35 秒）**。

---

## 2. 本机环境（换电脑时要核对/替换的地方）

| 项 | 值 |
|---|---|
| 系统 | Windows（PowerShell 7），工程目录 `C:\Users\daniel\Downloads\SoulX-Singer-main` |
| Python 环境 | `C:\Users\daniel\miniconda3\envs\soulxsinger\python.exe`（conda env `soulxsinger`，Python 3.10.20） |
| PyTorch | `2.8.0+cu128`，`torch.cuda.is_available() == True` |
| GPU | NVIDIA RTX PRO 4500 Blackwell，32 GB；**运行时其他程序（浏览器/桌面应用）已占用约 26.5 GB，只剩 ~5.8 GB 空闲** |
| SVC 权重 | `pretrained_models/SoulX-Singer/model-svc.pt`（2.6 GB，由 [webui_svc.py:174](webui_svc.py#L174) 加载） |
| SVS 权重 | `pretrained_models/SoulX-Singer/model.pt`（只有 [webui.py](webui.py) 用，本次未涉及） |
| 预处理权重 | `rmvpe/rmvpe.pt`(173 MB)、`mel-band-roformer-karaoke/*.ckpt`(1.6 GB)、dereverb(871 MB，因 `use_der=False` 实际不加载) |
| Whisper | `openai/whisper-base`，走 HF 缓存 `~/.cache/huggingface/hub/models--openai--whisper-base` |
| ffmpeg | 仓库自带 `ffmpeg/bin/ffmpeg.exe`（我用它把成品转成 mp3） |
| 采样率约定 | SVC 输出 **24 kHz 单声道**（`soulxsinger/config/soulxsinger.yaml`：`sample_rate: 24000`, `hop_size: 480` → 50 Hz 帧网格）；人声分离在 44.1 kHz 立体声 |

**是否 git 仓库**：这份代码是 zip 下载，**没有 `.git`**，所以没有任何 diff 可看；改动范围以本文 §4 为准。`outputs/` 在 `.gitignore` 里，我的临时脚本在 `outputs/_*.py`（不会随 git 走）。

---

## 3. 症状 → 根因对照（4 处，都已修）

| # | 症状 | 根因 | 位置（修复前） |
|---|---|---|---|
| 1 | 最多 10 分钟 | `TARGET_MAX_SEC_DEFAULT = 600`，`_trim_and_save_audio` 直接把音频 `[: max_sec*sr]` 切掉 | [webui_svc.py:31](webui_svc.py#L31)（原 600） |
| 2 | **5 分钟之后静音**（核心 bug） | `F0Extractor(..., max_duration=300)` → `interpolate_f0` 里 `target_frames = min(original_frames, batch_max_length)`，F0 只到 300 s；模型 `build_vocal_segments` **只用 F0** 决定要转换哪些区间，300 s 之后没有 F0 → 没有分段 → `generated_audio = torch.zeros_like(gt_wav)` 的尾部一直是 0 | [f0_extraction.py:461](preprocess/tools/f0_extraction.py#L461) / [f0_extraction.py:531](preprocess/tools/f0_extraction.py#L531) |
| 3 | 长音频爆显存 / 卡死 | RMVPE 是**整段一次性**过 DeepUNet+BiGRU（激活随时长线性增长，17 分钟要数 GB，只剩 5.8 GB 显存时必炸）；且 `to_local_average_cents` 里 `salience[:, a:b][idx]` 每帧拷贝整块 (帧数×9) → **O(N²)**，17 分钟仅解码就 ~15 分钟 CPU | [f0_extraction.py:338](preprocess/tools/f0_extraction.py#L338) / [f0_extraction.py:419](preprocess/tools/f0_extraction.py#L419) |
| 4 | 潜在雷：>30 s 输入内容丢失 | `WhisperEncoder.encode` 把 mel 硬截到 3000 帧（=30 s），超过部分**静默丢成 0 内容特征**；另外分段之间是硬切，长歌拼接处会有割裂感 | [whisper_encoder.py:13](soulxsinger/models/modules/whisper_encoder.py#L13) |

> 关键因果：**#2 才是"超过 5 分钟处理有问题"的真凶**，跟模型长度能力无关；`generated.wav` 里 300 s 之后是纯静音。

---

## 4. 已完成的代码改动

### 4.1 [webui_svc.py](webui_svc.py)（SVC WebUI，Gradio）

| 行 | 改动 |
|---|---|
| [:31](webui_svc.py#L31) | `TARGET_MAX_SEC_DEFAULT = 600` → **`0`（0 = 不限制，整首歌直接进）**；`PROMPT_MAX_SEC_DEFAULT` 保持 30（Whisper 窗口限制，原因见 §7） |
| [:59](webui_svc.py#L59) | 新增 i18n 文案 `target_max_sec_label`（中/英） |
| [:127](webui_svc.py#L127) | `_trim_and_save_audio` 支持 `max_sec <= 0 / None` = 不裁剪，并在真的裁剪时打印一行日志 |
| [:238](webui_svc.py#L238) | `AppState.run_svc` 透传 `progress_cb` 给 `svc_process` |
| [:312](webui_svc.py#L312) | `run_svc_conversion(...)` 新增关键字参数 `target_max_sec`（在 `seed` 之后，全部调用方用关键字，向后兼容） |
| [:368](webui_svc.py#L368) | 新增 `segment_progress(done, total)`：把分段进度映射到总进度 66%→98%，长音频不再"看着卡死" |
| [:395](webui_svc.py#L395) / [:510](webui_svc.py#L510) | `_start_svc` 新增 `target_max_sec` 入参；界面加滑块「Target 时长上限（秒，0 = 不限制）」 |
| [:560-607](webui_svc.py#L560-L607) | 语言切换事件的 outputs/updates 各加一项（18 = 18，已核对） |
| 文案 | `tip_p4` 改成"长音频已自动处理"，新增 `tip_p5`（Prompt 只取前 30 秒 / Target 上限说明） |

### 4.2 [gui_svc.py](gui_svc.py)（Tkinter 桌面版，复用同一套逻辑）

- [:48](gui_svc.py#L48) `self.target_max_sec = tk.IntVar(value=TARGET_MAX_SEC_DEFAULT)`
- [:109](gui_svc.py#L109) 新增数字框 "Target seconds (0 = whole file)"（0–7200，步长 30）
- [:218](gui_svc.py#L218) 调用时传 `target_max_sec=int(self.target_max_sec.get() or 0)`
- 窗口尺寸 820×620 → 820×700（多一行控件）

### 4.3 [preprocess/tools/f0_extraction.py](preprocess/tools/f0_extraction.py)（F0 提取，改动最多）

| 行 | 改动 |
|---|---|
| [:338](preprocess/tools/f0_extraction.py#L338) | `RMVPE.infer_from_audio` 改为 **30 s 滑窗 + 2 s 重叠、只保留内部帧** 拼接（`chunk_sec=30.0, overlap_sec=2.0`，`chunk_sec=0` 可退回旧的整遍）：每窗两侧多取 `margin_frames`（≥ win/2 个样本）保证 STFT 帧与整遍**逐帧一致**；重叠区被丢弃 → 每帧都有完整上下文；显存与时长解耦 |
| [:419](preprocess/tools/f0_extraction.py#L419) | `to_local_average_cents` 向量化（一次 fancy-index 取窗口）；结果与原逐帧循环**逐点相同**（已测） |
| [:461](preprocess/tools/f0_extraction.py#L461) | `F0Extractor(max_duration=None)`：默认不再截断 F0 网格；只有显式给正数才截断（保留旧能力） |
| [:531](preprocess/tools/f0_extraction.py#L531) | `interpolate_f0`：`max_duration` 为 `None/<=0` 时 `target_frames = original_frames`（全长） |
| [:562-600](preprocess/tools/f0_extraction.py#L562-L600) | `process()` 传入 `chunk_sec/overlap_sec`，打印时长/分块参数；若仍被 `max_duration` 截断会打 warning（不再是静默静音） |

### 4.4 [soulxsinger/models/soulxsinger_svc.py](soulxsinger/models/soulxsinger_svc.py)

- [:197](soulxsinger/models/soulxsinger_svc.py#L197) `infer(..., progress_cb=None, crossfade=True, seam_fade_sec=0.2)`（都是尾部新增关键字参数，旧调用不受影响）
- [:265](soulxsinger/models/soulxsinger_svc.py#L265) 若 F0 覆盖时长 < 音频时长，打警告（这类截断以后不会再静默）
- [:314-333](soulxsinger/models/soulxsinger_svc.py#L314-L333) 分段写入时对切点做 **0.2 s 淡入淡出**（注意：只淡 0.2 s，不是淡整段 look-back 重叠区——淡整段会把两份渲染结果叠成双重音/合唱感，这个坑我自己踩过并改掉了）
- 每段结束调用 `progress_cb(idx+1, total)`

### 4.5 [soulxsinger/models/modules/whisper_encoder.py](soulxsinger/models/modules/whisper_encoder.py)

- [:26](soulxsinger/models/modules/whisper_encoder.py#L26) `encode`：>30 s 输入自动按 **30 s 切窗 + 拼接**；切点固定在 50 Hz 帧网格上（16 kHz 下 `320` 样本的整数倍，480000 = 1500×320），保证拼接后帧号与 F0 帧号仍是一一对齐
- [:61](soulxsinger/models/modules/whisper_encoder.py#L61) 原逻辑抽成 `_encode_window`，**≤30 s 的路径一字未改**（结果不变）

### 4.6 [cli/inference_svc.py](cli/inference_svc.py)

- [:65](cli/inference_svc.py#L65) `process(args, config, model, progress_cb=None)`；[:93](cli/inference_svc.py#L93) 传给 `model.infer`。CLI 本身没有裁剪逻辑，所以命令行路径天然支持长音频。

### 关键参数一览（当前生效值）

| 参数 | 位置 | 值 |
|---|---|---|
| `TARGET_MAX_SEC_DEFAULT` | webui_svc.py:31 / gui_svc.py | `0`（不限制） |
| `PROMPT_MAX_SEC_DEFAULT` | webui_svc.py:30 | `30`（Whisper 窗口） |
| RMVPE `chunk_sec` / `overlap_sec` | f0_extraction.py:342-343 | `30.0` / `2.0` |
| `F0Extractor.max_duration` | f0_extraction.py:461 | `None` |
| `seam_fade_sec` | soulxsinger_svc.py:197 | `0.2` s |
| 分段 min/max | soulxsinger_svc.py:275（**未改**，默认值定义在 [:89](soulxsinger/models/soulxsinger_svc.py#L89)） | 15 s / **30 s**（必须 ≤ Whisper 30 s，原因见 §7） |
| `WHISPER_MAX_SEC` | whisper_encoder.py:13 | `30.0` |

---

## 5. 验证方法（换机器后照抄即可）

四个脚本都在 `outputs/`（gitignored，本次保留了下来）。若新副本是从 git 克隆的，需要按 §4 重新核对代码（这些脚本不会跟着走）：

```powershell
$py = "C:\Users\daniel\miniconda3\envs\soulxsinger\python.exe"   # ← 换成你机器的 python
$env:HF_HUB_OFFLINE = "1"                                        # 避免 whisper 联网检查卡住
$env:PYTORCH_CUDA_ALLOC_CONF = "expandable_segments:True"        # 减少显存碎片
$env:PYTHONIOENCODING = "utf-8"                                  # Windows 打印中文必需

& $py -u outputs\_longfix_check.py     # 5 项自检：解码一致性 / 分块 vs 整遍 / 5 分钟截断 / 分段覆盖 / Whisper 分块
& $py -u outputs\_run_convert.py       # 端到端：prompt.mp3 → target.mp3（走的就是 WebUI/GUI 的 run_svc_conversion）
& $py outputs\_verify_output.py "outputs\gradio\svc\<时间戳>\generated\generated_mixed.wav"   # 全长 + 每分钟 RMS + 最长静音段
& $py -u outputs\_ui_check.py          # WebUI 起服务：GET / 200、事件输入/输出数量对齐、新滑块在 /config 里
```

### 5.1 命令行路径（可选，不用界面时）

`cli/inference_svc.py` **不做任何长度裁剪**，天然支持长音频；但它和界面不一样，有几个坑：

- 它要**预先算好的 F0**：`--prompt_f0_path` / `--target_f0_path`（默认指向 `example/audio/*.npy`）。用 [preprocess/tools/f0_extraction.py](preprocess/tools/f0_extraction.py) 生成即可 —— 修复后默认就是全长 F0（以前算出来的 npy 只有前 300 秒）。
- `--model_path` 默认是 **SVS** 权重 `pretrained_models/soulx-singer/model.pt`（[:118](cli/inference_svc.py#L118)），跑 SVC 要显式 `--model_path pretrained_models/SoulX-Singer/model-svc.pt`。
- `--cfg` 默认 **3.0**（界面默认 1.0），`--n_steps` 默认 32；`--auto_shift` 是开关（默认关，界面默认开）。

### 本次实测数据（都跑过，不是估计）

| 检查 | 结果 |
|---|---|
| F0 网格截断（1055.1 s 文件） | 旧 `max_duration=300` → **15000 帧 = 300.0 s**；新 `None` → **52755 帧 = 1055.1 s** |
| 分块 F0 vs 整遍 F0（40 s 片段，含 2 个窗口） | 帧数相同；浊音判定一致 **99.80%**；音高差 mean **3.06 cents** / p95 **0.49 cents**（max 2446 cents = 个别边界帧）→ 听感等价。顺带快很多：整遍 **16.4 s** → 分块 **0.7 s**（同样 4001 帧） |
| 向量化解码 vs 原循环 | `identical=True`（逐点相同） |
| Whisper 分块 | 70 s → **3500 帧**（= 1500+1500+500，精确落在 50 Hz 网格）；12 s 短路径仍是 600 帧（未变）。注意脚本最后一行 `chunked == hand-split: False (common=3500)` 是**预期**的：帧数一致，但"整段一次分窗"与"手工切三段再拼"在窗口边界因重采样/补零而有极小数值差，不是 bug |
| 分段覆盖（1055 s） | 自检脚本用**平铺的合成 F0** 得到 **66 段**（`n=66 span=0..1055.1s max_gap=0.00s max_seg=18.1s`）；真实运行用真实 F0 得到 **61 段**。两者都覆盖到文件末尾、无空隙（段数由静音切点决定，不必相等） |
| 端到端耗时 | **553 s（9 分 13 秒）**：分离 + F0 约 2 分钟，61 段转换约 7 分钟（8.2–8.8 s/段） |
| F0 阶段显存峰值 | **0.62 GiB**（旧实现随时长线性上涨，长音频必 OOM） |
| 成品 | **1055.1 s**、25,321,984 样本 @24 kHz、NaN=0、削波 6 个采样点（混音版）/69（纯人声） |
| 5 分钟以后是否静音 | 每 60 s RMS 连续（0.07–0.31），最后有声点 **1053.8 s**，最长静音段仅 **1.8 s**（正常换气） |
| WebUI | `render_interface` 通过、`GET /` 200、运行事件 13 输入、语言切换事件 18 输出、滑块标签已在 `/config` 中 |

### 本次产物

```
outputs/gradio/svc/20261031_035507_294056/generated/
├── generated.wav         # 纯人声（24 kHz 单声道，1055.1 s）48 MB
├── generated_mixed.wav   # 人声 + 自动混回伴奏（成品）48 MB
└── generated_mixed.mp3   # 同一成品 192 kbps（我用仓库内 ffmpeg 转的）20 MB
```

运行参数（等同界面默认）：Target 人声分离 ✓、Prompt 不分离、自动变调 ✓、自动混伴奏 ✓、`n_step=32`、`cfg=1.0`、`seed=42`、`device=cuda`、`fp16=True`。

---

## 6. 还没做的事（给下一台电脑 AI 的 TODO，按优先级）

1. **CFG==1.0 的快路径**（最大提速点）：[flow_matching.py:293](soulxsinger/models/modules/flow_matching.py#L293) 与 [:351](soulxsinger/models/modules/flow_matching.py#L351) 是 `if cfg > 0:`，所以界面默认的 `cfg=1.0` 仍然跑 **cond + uncond 两次前向**（32 步 × 2）。改成 `cfg == 1.0` 时只跑 cond，转换时间约可砍一半；需 A/B 听一下是否等价（数学上 cfg=1 时 `out = uncond + 1*(cond-uncond) = cond`，理论等价）。
2. **缓存 prompt 编码**：[soulxsinger_svc.py:342](soulxsinger/models/soulxsinger_svc.py#L342) 每段都对 prompt 重新跑一次 Whisper 编码（本次 61 段 = 61 次冗余），`pt_mel` 已在外面算过一次，`pt_content_feat` 也应挪到 `infer` 里算一次传进去（省 ~2 分钟，纯赚）。
3. **分离阶段整文件进内存**：[vocal_separation/model.py:83](preprocess/tools/vocal_separation/model.py#L83) 一次性 `librosa.load(sr=44100, mono=False)`，17 分钟约 0.4 GB、1 小时约 1.3 GB，再加 `mix - vocals` 等中间量。若要支持 40 分钟以上，考虑分块落盘 / 直接写 wav 再分块读。
4. **自动变调是"全曲一个偏移量"**：[soulxsinger_svc.py](soulxsinger/models/soulxsinger_svc.py) 的 `auto_shift` 用整曲 F0 中位数。音域跨度很大的歌（主歌很低、副歌高八度）可考虑按段自适应变调；同时注意 `auto_mix_acc` 会把伴奏一起变调（保持八度），目前是按全曲单一偏移。
5. **`webui.py`（SVS：歌词+MIDI 那条线）默认仍限 60 秒**（[webui.py:27](webui.py#L27)）：转录要跑 ASR + 音符识别，长音频成本与 SVC 不同，所以默认没改；桌面 GUI（§10）已经把上限做成可改字段（0 = 整首）。SVS 的合成本身没有长度问题（每个 metadata 段一次 `model.infer`），长 target 只慢不坏。它会自动吃到 §4.3 的 F0 修复与提速。
6. **输出规格**：24 kHz 单声道。想要立体声/更高采样率要在 mix 之前处理（现在 `acc` 被 `librosa.load(..., sr=24000, mono=True)` 降掉了，见 [webui_svc.py](webui_svc.py) 的 `run_svc` 混音段）。
7. **切点淡入淡出长度可调**：`seam_fade_sec=0.2` 是保守值（切点通常落在 ≥200 ms 静音里）。若发现人声被切在有声处，可加等功率(等能量)淡入淡出或调长。
8. **可配置化**：`chunk_sec/overlap_sec/max_duration`、`seam_fade_sec` 目前是代码默认值，可搬到 `soulxsinger/config/soulxsinger.yaml` 的 `infer:` 段或界面。
9. **想彻底支持 >30 s 的 Prompt**（现在只取前 30 s）：换内容编码器（Whisper 的 30 s 是模型结构决定，无法直接扩窗口；本仓库的分窗只是防丢尾）。
10. **性能小项**：RMVPE 可开 `is_half=True`（省显存、可能略快，但需重测 §5 的一致性）；人声分离的推理参数在 `pretrained_models/SoulX-Singer-Preprocess/mel-band-roformer-karaoke/config_karaoke_becruily.yaml` 的 `inference:` 段（当前 `batch_size: 8`、`dim_t: 1101`、`num_overlap: 2`，[:69-72](pretrained_models/SoulX-Singer-Preprocess/mel-band-roformer-karaoke/config_karaoke_becruily.yaml#L69-L72)），显存富余时可加大 batch/减小 overlap。
11. **GUI：转录还没有分段进度**（`_transcribe_prompt` / `_transcribe_target` 里没有 `progress_cb`，只有合成有）；要做就在 [preprocess/pipeline.py](preprocess/pipeline.py) 的 `run()` 段循环里加钩子并透传，界面已经有 `PROGRESS::` 通道，改起来很小。
12. **GUI：`n_steps` / `cfg` 是写回 `state.svs_config`（OmegaConf 进程级对象）**，WebUI / CLI 共用同一份 config；GUI 每次合成前都会写一次，若两边同时在跑要想到会被互相覆盖（要更干净就给 `run_svs` 加 `n_steps/cfg` 参数，别改 config）。
13. **GUI 可选增强**：歌词编辑器目前是"一行一词"（保住音符对齐），要做增删行就得同时改 `duration/note_pitch/note_type/f0` 并重算 phoneme；再加 MIDI 导入时把 `_edit_metadata` 的 `.mid` 直接接到编辑器（现在要先转录/导入再刷新）。

---

## 7. 踩过的坑（另一个 AI 很可能再踩）

- **改完必须重启** GUI / WebUI（`launch_gui_svc.pyw`、`launch_webui_svc.pyw`，或 `python webui_svc.py --device cuda --fp16`），否则跑的还是旧代码。
- **不要动 `build_vocal_segments` 的 `max_duration_sec=30.0`**（调用处 [soulxsinger_svc.py:275](soulxsinger/models/soulxsinger_svc.py#L275)，默认值定义 [:89](soulxsinger/models/soulxsinger_svc.py#L89)）：分段长度一旦 >30 s，Whisper 内容特征就得走分窗路径（已实现但质量未验证），而且模型的 30 s 训练分布也会被破坏。
- **帧网格三套，别混**：RMVPE mel 是 16 kHz/160 hop = **100 Hz**；模型 F0/mel 是 24 kHz/480 hop = **50 Hz**；Whisper 编码输出是 20 ms = **50 Hz**（16 kHz 下 320 样本/帧）。Whisper 切窗必须落在 320 的整数倍上，否则内容特征与 F0 逐帧错位（表现为咬字糊/跑调）。
- **不要"淡入淡出整段重叠区"**：分段有最多 30 s 的 look-back 上下文，淡整段 = 两份渲染叠加 = 双重音。只淡切点附近 ~0.2 s。
- **Windows 控制台**：脚本 `print` 中文会 `UnicodeEncodeError: 'charmap' codec...`，需要 `$env:PYTHONIOENCODING="utf-8"`。
- **PowerShell 重定向看不到 Python 进度**：用 `python -u`，并且最好像 `outputs/_*.py` 那样自己开文件 `buffering=1` 写日志（`*> file.log` 会看不到实时输出，我第一次就是这么"卡住"误判的）。
- **HF 联网检查**：`openai/whisper-base` 已在缓存里时，设 `HF_HUB_OFFLINE=1` 更稳（否则会等 Hub 超时）。
- **显存**：本机桌面程序会占掉 ~26 GB 显存，跑前先看 `nvidia-smi --query-gpu=memory.free --format=csv,noheader`；碎片多时设 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`。
- **DSH 沙箱**：在受限沙箱里 `tempfile` 写系统临时目录会被拒（Gradio 的 `get_config_file()` 会挂），把 `$env:TEMP/$env:TMP` 指到工作区内即可。
- 退出时看到 `wandb` / `tempfile ... PermissionError: [WinError 5]` 的 traceback 是**临时目录清理噪音**，不是任务失败（本次两次都是这个导致 exit code 1，但 `[result]` 行是完整的）。
- **（GUI）worker 线程里不要碰 Tk 变量**：`StringVar.get()/set()` 在非主线程、且主线程不在 `mainloop` 里时会抛 `RuntimeError: main thread is not in main loop`。写界面时看起来没事（真跑起来有 mainloop 就侥幸能过），自检脚本一跑就炸。规则：主线程快照参数 → worker 只算 + 发队列消息。（§10）
- **（GUI）`import preprocess.tools.g2p` 会把整个 preprocess 包初始化一遍**：[preprocess/tools/__init__.py](preprocess/tools/__init__.py) 里 try/except 构造 VocalSeparator / F0Extractor / LyricTranscriber / NoteTranscriber，等于顺手加载 ~10 GB 权重（我这边点了「保存 metadata」以后界面像死了一样，实际是在建模型）。只要 `g2p_transform` 就别走包导入。（§10）
- **（GUI）歌词必须一个字一行**：[preprocess/tools/g2p.py:18-26](preprocess/tools/g2p.py#L18-L26) 的 `is_chinese_char` 要求 `len(word) == 1`，多字词的 phoneme 会被写成 `<SP>`（合成时那段音符静音）。`language` 也只认 `"Cantonese"` vs 其他，ASR 存的 `"zh"/"en"` 会让粤语走成普通话分支。
- **（GUI）`run_svs_from_paths` 不转码**：[webui.py:383](webui.py#L383) 是 `shutil.copy2(prompt_wav_path, audio_dir / "prompt.wav")`，WebUI 传 mp3 时会得到"名字叫 wav 的 mp3"，靠 torchaudio 解码（需要 ffmpeg/av 后端）。喂真 wav 更稳。

---

## 8. 新机器上的 10 分钟自检清单

1. `python -c "import torch;print(torch.__version__, torch.cuda.is_available())"` → 需要 True（CPU 也能跑，但长音频很慢）。
2. 确认权重齐全：`pretrained_models/SoulX-Singer/model-svc.pt`、`.../SoulX-Singer-Preprocess/rmvpe/rmvpe.pt`、`mel-band-roformer-karaoke/*.ckpt`。
3. 确认 §4 的 6 个文件已带上新代码（对照 §4 行号 grep 这几个标记：`TARGET_MAX_SEC_DEFAULT = 0`、`max_duration: Optional[float] = None`、`WHISPER_MAX_SEC`、`seam_fade_sec`、`chunk_sec=self.chunk_sec`）。
4. 跑 `outputs/_longfix_check.py`，期望看到这几行（数字要一致）：
   - `decode() identical=True`
   - `frames equal=True  voicing agreement=0.9980` 与 `pitch vs single-pass (cents): mean=3.06 p95=0.49`
   - `interpolate max_duration= None -> frames= 52755 = 1055.1s of a 1055.1s file`
   - `whisper 70s -> frames=3500`、`whisper 12s (unchanged single-pass path) -> frames=600`
   - 两行**正常现象**别误判：`build_vocal_segments: n=66`（合成 F0，真实运行是 61）、`chunked == hand-split: False (common=3500)`（见 §5 表）
5. 跑一段 **> 5 分钟**的 target（本次是 `target.mp3`）→ 检查输出时长 == 输入时长、5 分钟后 RMS 不为 0（用 `outputs/_verify_output.py`）。
6. 界面里确认出现「Target 时长上限（秒，0 = 不限制）」滑块 / "Target seconds (0 = whole file)" 输入框。
7. （GUI，秒级、不加载模型）`python outputs/_gui_check.py`：应打印 `[editor] rows: 20`、`[save] counts text/phoneme/pitch/dur: 20 20 20 20`、`[save] backup written: True`、`[warn] multi-char phoneme: <SP>`，并以 `[cleanup] 退出清理 exit cleanup: 释放 0 个模型引用…` + exit code 0 结束。
8. （GUI，真模型）`python outputs/_gui_e2e.py`：示例 zh→zh 直接合成，打印 wav 时长/采样率/peak/rms，然后关窗卸载 —— 期望 `reserved` 掉到接近 0、`空闲 free` 明显上升；日志 `outputs/_gui_e2e.log`。（§10）

---

## 9. 一句话给下一个 AI

两个原始问题已经修完并有数据背书（§3、§5）；如果你要继续，**先做 §6 的第 1、2 条**（CFG=1 快路径 + 缓存 prompt 编码，能省接近一半时间），别去动分段长度上限和 Whisper 30 s 窗口——那是模型结构层面的约束，不是 bug。

---

## 10. 追加（2026-10-31）：SVS 桌面 GUI + 退出自动卸载模型/释放显存

需求原话：**「帮我创作一个 py gui 版本，加入 webui 的歌词和 midi，加入一个功能，退出就会自动 unload model 和自动 clear 内存和显存的占用」** —— 即把 `webui.py`（SVS：歌词 + MIDI）做成桌面版，并让"关窗 = 释放模型/内存/显存"。

### 10.1 新增 / 改动

| 文件 | 作用 |
| --- | --- |
| `gui.py`（新） | SVS 的 Tkinter 桌面版：① 参考音频（分离 + 歌词/音符转录 → `prompt metadata.json` + `vocal.mid`）② 目标旋律（A 音频转录 / **B 导入 .mid**，可选 `vocal.wav` 对齐才会写 `f0`）③ 合成（曲谱/旋律控制、自动移调、±36 半音、seed、`n_steps`、`cfg`、设备、FP16）；外加**歌词表格编辑器**（`#`/开始 ms/时长/音高/歌词）、保存与另存、`vocal.mid` 导出、示例一键载入、进度条 + 日志 |
| `resource_release.py`（新） | 通用释放逻辑：`release_singletons()` 把 `webui.APP_STATE` / `webui_svc._APP_STATES` 上的模型属性置空 → `reclaim()` = `gc.collect()` → `empty_device_cache()` → `torch.cuda.synchronize()+ipc_collect()+empty_cache()` → 打印释放前后 reserved / tensors / 显存空闲 / 进程 WorkingSet；`unload_all()` 一步做完；`force_exit()` = flush 后 `os._exit(0)` |
| `launch_gui.py` / `launch_gui.pyw`（新）+ `launch_svc_common.py:launch_gui_svs()` / `main("gui_svs")` | 双击启动桌面版（`python -u`，日志 `outputs/launcher_logs/gui.log`） |
| [gui_svc.py](gui_svc.py) | SVC 桌面版也加 `WM_DELETE_WINDOW → _on_close`（确认 → `destroy()` → 释放 `webui_svc._APP_STATES` → `force_exit(0)`）；关闭后轮询不再 `after`、不再弹 `messagebox` |
| [cli/inference.py:65](cli/inference.py#L65) `process(..., progress_cb=None)` | SVS 推理循环每段回调 `progress_cb(done, total)`（之前只有 tqdm）；[:122-123](cli/inference.py#L122-L123) |
| [webui.py:323](webui.py#L323) `run_svs` / [:362](webui.py#L362) `run_svs_from_paths` | 透传 `progress_cb`（默认 `None`，WebUI 行为不变） |
| [webui.py:309-316](webui.py#L309-L316) `run_preprocess` | **顺带修的上游 bug**：`VocalDetector.cut_wavs_output_dir` 在构造时被固定成 `_placeholder` 目录，而 `run_preprocess` 只改 `save_dir` → 所有会话的 `cut_wavs/*.wav` 和 `*_f0.npy` 都写进同一共享目录并互相覆盖。现在每次运行把它重指到 `<save_path>/cut_wavs` |

### 10.2 GUI 的关键设计（改代码前必读）

- **模型懒加载但要给足时间**：`import webui` 会在 **import 时**构造 `APP_STATE`（[webui.py:397](webui.py#L397)，≈10 GB 权重）。GUI 只在 worker 线程里 import，且**先**设 `os.environ["SOULX_DEVICE"]`、必要时临时把 `--fp16` 追加进 `sys.argv`（[:397](webui.py#L397) 就是用 `"--fp16" in sys.argv` 决定精度），设备/精度改变则重建 `AppState`。
  **实测（本机，2026-10-31）**：`import preprocess.tools`（= `preprocess/tools/__init__.py`，会连带 import NeMo / funasr / whisper 栈）是首次加载最慢的一段，机器被其他程序占满时 **10 分钟都没有一行输出**也属正常（进程 RSS <0.5 GB、显存 0 → 说明还在 import，不是卡死）；界面日志已经写了"第一次会很久"。想快速验证推理链就别走 GUI：用 `outputs/_svs_min.py`（只 `cli.inference.build_model`，跳过 preprocess 包）。
- **显存预算**：SVS 一整套（分离 1.6+0.87 GB、paraformer 0.94 GB、parakeet nemo 2.36 GB、rosvot 0.49 GB、rwbd 0.11 GB、rmvpe 0.17 GB、SVS 2.69 GB / FP16 约一半）≈ **8-10 GB**。本次测试时桌面其他程序已占 27 GB（剩 5.3 GB），所以真机跑 GUI 前先看 `nvidia-smi --query-gpu=memory.free --format=csv,noheader`，不够就关掉别的或改 `CPU`。
- **Tk 变量只能在主线程读写**：worker 里调 `StringVar.get()` 会抛 `RuntimeError: main thread is not in main loop`（只有"不跑 mainloop、自己 update 泵"的自检脚本才会暴露）。所以每个任务先 `self._settings()` 取快照，worker 只发队列消息（`LOG/PROGRESS/OUT/META/MIDI/VOCAL/STATE/PARAMS/SAVED/DONE/ERROR`），界面改动全部发生在 `_poll_queue`（主线程）。
- **歌词编辑器与 metadata 结构**：`text/duration/note_pitch/note_type/f0` 是**空格分隔的等长列表**；一行 = 一个音符，只替换文字，所以数量永不漂移（保存时仍会复核，不一致就报错拒绝写回）。保存用 `g2p_transform(tokens, language)` 重算 `phoneme`；**语言以界面选择为准**（ASR 写进 metadata 的 `"zh"/"en"` 不能用：`g2p_transform` 只区分 `"Cantonese"` 与其他，见 [preprocess/tools/g2p.py:62](preprocess/tools/g2p.py#L62)）。
- **g2p 的坑**：`import preprocess.tools.g2p` 会执行 [preprocess/tools/__init__.py](preprocess/tools/__init__.py)，顺手把分离/ASR/音符转录模型**全部构造一遍**（实测卡了 3 分钟）。GUI 改用 `importlib.util.spec_from_file_location` 单独加载 `preprocess/tools/g2p.py`（只需 ToJyutping / g2pM / g2p_en，其中 `g2p_en` 首次要 ~4 s 载 nltk 数据），并在开界面时后台预热。
- **一个字一行**：`g2p_transform` 只映射**单个**汉字（`is_chinese_char` 要求 `len==1`），`"测试"` 这类多字词会被换成 `<SP>`（合成时该音符不出声）。编辑器在「应用」时就提示，保存时统计数量并在日志里点名。
- **prompt.wav 必须是真 wav**：`run_svs_from_paths` 只 `shutil.copy2`（**不转码**；WebUI 会把 mp3 直接复制成 `prompt.wav`，靠 torchaudio 现场解码）。GUI 优先用转录生成的 `<session>/audio/prompt.wav`（44.1 kHz 单声道）；只有示例 metadata 时先 `_trim_and_save_audio` 转一份再喂。
- **`0 = 整首`**：`webui._trim_and_save_audio` 是 `audio[: max_sec*sr]`，传 0 会得到**空音频**；GUI 把 0 翻译成 `10**9`（界面字段「目标时长上限 s（0=整首）」，默认 60 与 WebUI 一致）。
- **为什么退出一定要 `os._exit(0)`**：Windows 上 `gc + empty_cache` 之后进程 RSS 不一定归还，而且 torchaudio / funasr / Nemo 的线程会让解释器继续活着 → 窗口没了但显存仍被占。所以关窗顺序固定为：确认 → `destroy()` → 释放引用 → `gc/empty_cache/ipc_collect` → 打印释放数字 → `os._exit(0)`。
- `metadata.json` 会**就地改写**并留 `.bak`（只保留第一次的原始副本）；有未保存改动时「开始合成」会被拦下（`_dirty`）。

### 10.3 自检脚本与实测状态

- `outputs/_gui_check.py`（不加载模型，秒级）：建界面 → 载示例 → 编辑器改一个音符 → worker 保存 → 校验 `text/phoneme/note_pitch/duration` 数量一致（实测 20/20/20/20）、`.bak` 生成、`dirty` 清零、多字词 phoneme 变 `<SP>` 的警告、`_on_close` 正常退出。
- `outputs/_gui_e2e.py`（真模型）：示例 zh→zh 免转录直接合成 → 打印输出 wav 的时长/采样率/peak/rms → 关窗卸载并打印显存回收数字；日志 `outputs/_gui_e2e.log`。
- `outputs/_import_probe.py`：逐段打印 `import webui` 链条耗时（自己写 `outputs/_import_probe.log`，`buffering=1`，避开 PowerShell 缓冲）。
- `outputs/_svs_min.py`：**不加载 preprocess 包**，只 `cli.inference.build_model` + `process(progress_cb=...)` 合成示例片段，再用 `resource_release.unload_all` 对**真实权重**卸载，直接看 `reserved/tensors` 掉多少 —— 想验证推理链 + 退出清理，跑这个最快。
- `outputs/_release_check.py`（秒级、已跑通）：在显存上真实分配 **3.00 GiB**，塞进假 `AppState`（`svs_model` + 嵌套 `preprocess_pipeline.model` 各引用一次），跑 `unload_all`。本机实测：

  ```text
  [release] before: allocated=3.00 GiB reserved=3.00 GiB free=23.86 GiB
  [release] 已释放模型引用 dropped_models=2
  [release] 显存 VRAM: reserved 3.00 GiB -> 0.00 GiB, tensors 0.00 GiB -> 0.00 GiB, 空闲 free 23.86 GiB -> 24.01 GiB
  [release] returned to driver: 3.00 GiB
  ```

  （注意：脚本里必须把局部变量 `weight = None`，否则引用还在手上，`reserved` 不会掉 —— 真实 GUI 没这个问题，权重只被 `APP_STATE` 持有。）

**已实跑验证（本机）**：
- `py_compile` 全通过；界面构建、示例载入、歌词编辑器（20 行 = 20 音符）、改词、worker 保存（`text/phoneme/note_pitch/duration` 都是 20）、`.bak`、`dirty` 清零、多字词 → `<SP>` 警告、`_on_close` → `resource_release` → `os._exit` 退出码 0，并打印 `显存 VRAM: reserved … / 空闲 free 28.04 GiB / 31.83 GiB`。
- 抓到并修掉一个真 bug：worker 线程读 Tk 变量抛 `RuntimeError: main thread is not in main loop` → 改成主线程 `_settings()` 快照。

**未跑完（环境受限，留给显存空闲时或下一台电脑）**：`_gui_e2e.py` / `_svs_min.py` 的**真模型合成**。本次期间其他桌面程序占了 27 GB 显存（只剩 5.3 GB，SVS 整套要 8-10 GB），且 `import preprocess.tools`（NeMo/funasr 栈）在负载下 10 分钟没走完（进程 RSS <0.5 GB、显存 0 = 还在 import，不是卡死），两次都在 import 阶段停掉。参考：同一台机器上 SVC 全流程 17 分 35 秒跑通（§5），说明这条链本身没问题。重跑：

```powershell
$env:PYTHONIOENCODING="utf-8"; $env:HF_HUB_OFFLINE="1"; $env:PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
$py = "C:\Users\daniel\miniconda3\envs\soulxsinger\python.exe"
& $py -u outputs\_svs_min.py   # 快：只建 SVS 模型，先证明合成链 + 卸载释放显存
& $py -u outputs\_gui_e2e.py   # 慢：整界面 e2e（会加载 ~10 GB 转录栈）
```
期望：`[min] progress N/N`、`[min] output: 24000 Hz / … rms>0`、`[min] unload … reserved X GiB → 接近 0`；GUI 版期望 `[e2e] wav: 24000 Hz …` + `[cleanup] 显存 VRAM: reserved … → …`。

---

## 11. 2026-11-05：这套修复已同步进 H3 工作区安装（本机 = H3 Director Cut Studio）

> 本节写在 `models\SoulX-Singer-main` 这份副本里。`C:\Users\daniel\Downloads\SoulX-Singer-main` 保持上游一致（不带下面 §11.2 的两处工作区改动）。

### 11.1 同步了什么

安装目录 `D:\minimax h3\minimax h3 reference r2v\models\SoulX-Singer-main` 之前是 **27/5 的旧码**（`TARGET_MAX_SEC_DEFAULT = 600`、F0 300 s 上限、无 `gui.py`）。两份代码是**双向分叉**：工作区这份带 H3 Studio 集成（`soulx_server.py` 的 `/_studio_start_svc`、`/_unload_svc`、懒加载、7861 Server Mode，集成代码在工作区根目录、不在本仓库内），Downloads 那份带 §3–§4 的修复和 §10 的新 GUI。因此按**文件合并**同步，没有整目录覆盖：权重 `pretrained_models\`、`.runtime\`、`ffmpeg\`、`outputs\` 原样保留。

- 覆盖的 9 个文件：`webui_svc.py`、`webui.py`、`gui_svc.py`、`launch_svc_common.py`、`cli\inference.py`、`cli\inference_svc.py`、`preprocess\tools\f0_extraction.py`、`soulxsinger\models\soulxsinger_svc.py`、`soulxsinger\models\modules\whisper_encoder.py`
- 新增 4 个：`gui.py`、`resource_release.py`、`launch_gui.py`、`launch_gui.pyw`
- 新增自检脚本：`outputs\_gui_check.py`、`_gui_e2e.py`、`_import_probe.py`、`_longfix_check.py`、`_release_check.py`、`_run_convert.py`、`_svs_min.py`、`_ui_check.py`、`_verify_output.py`
- 测试输入 `prompt.mp3`、`target.mp3` 一并复制进来（`_longfix_check.py`/`_run_convert.py` 直接用）
- 被覆盖前的 9 个文件备份在工作区 `_backup\V0.3.8-alpha.3_soulx_singer_pre_longfix_20261105\`

### 11.2 工作区专属改动（下次从上游同步时**不要**被覆盖掉）

1. `webui_svc.py:408` —— `_start_svc` 的新参数写成带默认值的尾参数 `target_max_sec=TARGET_MAX_SEC_DEFAULT`。原因：`工作区根目录\soulx_server.py::_call_upstream_start_svc` 只发布 12 个命名参数并按关键字调用；如果第 13 个参数必填，它的 `required` 判定失败会退回**按位置**传 12 个值 ⇒ `device_choice` 往后全部错位（就是以前 "Pitch 0 被送进 Device 下拉框" 那一类事故），并且缺参直接 TypeError。探针：`工作区根目录\_dsh_verify_13\verify_soulx_studio_contract.py`（用真实 `webui_svc` + 真实 `_call_upstream_start_svc`，验证走关键字路径、12 个值落点正确、Studio 路径拿 `0 = 不限制`）。
2. `launch_svc_common.py:19-66` —— 探测环境时优先 `ROOT\.runtime\<计算机名>\.venv\Scripts\`（venv 的 `pythonw.exe` 在 `Scripts\` 下，conda 环境在根目录），所以双击 `launch_gui.pyw` 用的是 Studio 装好的那套 CUDA 运行时（torch 2.7.1+cu128），不会掉进 `miniconda3\envs\soulxsinger`（torch 2.8.0）。
3. 因此本机重跑下面所有脚本的解释器是：
   `models\SoulX-Singer-main\.runtime\DESKTOP-PON9M2I\.venv\Scripts\python.exe`（不是 §2 的 conda python）。

### 11.3 本机实测（2026-11-05，RTX PRO 4500 Blackwell，跑时空闲显存 27–30 GiB）

| 脚本 | 结果 |
|---|---|
| `py_compile`（15 个文件，含 `.pyw`） | 通过 |
| `_longfix_check.py` | `decode()` 新旧一致、6000 帧 0.02 s → 0.009 s；40 s 单遍 18.0 s → 分窗 1.0 s（帧数一致、voicing 一致率 0.9978、音高 mean 3.06 cent）；对真实 `target.mp3`：旧 `max_duration=300` 只出 **300.0 s**，新逻辑出 **1055.1 s**；`build_vocal_segments` **66 段**覆盖 0–1055.1 s、max_gap 0.00 s；Whisper 70 s → 3500 帧（= 30+30+10 手工分窗之和）；CUDA 峰值 0.68 GiB |
| `_run_convert.py`（整首 17 分 35 秒，走 `run_svc_conversion` 关键字调用 = Studio 同一条路） | **61 段 / 300 s 跑完 / 输出 1055.1 s、24 kHz 单声道**，产物 `outputs\gradio\svc\20261105_162729_043984\generated\generated_mixed.wav` |
| `_verify_output.py`（上面那份） | first audio 0.0 s、**last audio 1053.8 s**、静音 50 ms 帧 1.0–2.0%、最长静音段 1.7–2.8 s ⇒ 300 s 之后全静音的旧 bug 已消失 |
| `_import_probe.py` | webui import 49.9 s、AppState 81.7 s、释放后 reserved 10.35 → 3.98 GiB、free 20.21 → 26.59 GiB |
| `_ui_check.py` | `render_interface` OK，新滑条「Target 时长上限」与新文案进入 Gradio config，页面 200 |
| `_release_check.py` | reserved 3.00 → 0.00 GiB、free 27.63 → 30.63 GiB、`APP_STATE` 置空 |
| `_gui_check.py` | 界面构建 / 示例载入 / 改音符 / 保存（text·phoneme·pitch·dur = 20·20·20·20）/ `.bak` / 多字词 `<SP>` 警告 / `_on_close` 退出码 0 |
| `_svs_min.py`（**上次因显存没跑完，本次已跑通**） | 建模型 16.4 s、reserved 2.65 GiB；合成 39.9 s；输出 24000 Hz / 6.71 s / nan=0 / peak 0.3402 / rms 0.0658；`progress_cb=[(1,1)]`；卸载 dropped=2，**reserved 2.76 → 0.02 GiB**、free 21.90 → 30.53 GiB |
| `_gui_e2e.py`（**同上，已跑通**） | 真模型合成 70.1 s、状态「完成」、wav 24000 Hz / 6.71 s / nan=0 / peak 0.2972 / rms 0.0608、进度条 100.0；关窗 dropped=5、**reserved 3.92 → 0.02 GiB**、free 30.53 / 31.83 GiB |

Studio 侧配套测试：`testing\test_soulx_runtime.py` + `testing\test_soulx_dialog.py` **20 项通过**（顺带把 `test_safe_defaults_match_official_svc_workflow` 改成注入 `SoulXRuntimeState`，本机装了 SoulX 时它以前会解析成 `127.0.0.1:7861` 而和 `DEFAULT_SOULX_SERVER` 冲突）。

### 11.4 本机两个环境坑

- **正在跑的 7861 服务不会自动吃新代码**：要么 `restart_soulx_server.bat`，要么在 Studio 里停止再启动 SOULX（健康检查要求 `/_studio_start_svc`，旧进程会被判不健康）。
- **Tk 脚本报 `Can't find a usable init.tcl … version conflict … need exactly 8.6.15`**：这是从冻结的 DeepSeek Harness Tray 继承的 `TCL_LIBRARY`/`TK_LIBRARY`（它自带 Tcl 8.6.12）污染了子进程，与 SoulX 无关；从资源管理器双击启动不受影响，在脚本前 `Remove-Item env:TCL_LIBRARY, env:TK_LIBRARY` 即可。`.runtime` 里那套 uv CPython 自带 Tcl/Tk，`import tkinter; tkinter.Tk()` 实测 OK（Tcl 8.6）。

