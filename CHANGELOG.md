# Changelog

Every user-visible correction receives an application version and a dated entry in this file. Application versions follow Semantic Versioning pre-release notation. The `.h3director.json` project-format version is maintained separately and changes only when the saved schema changes.

## [0.3.8-alpha.3] - 2026-10-21

### Unlock All Characters：Shot 级角色清理与合格规格矩形
- Ctrl+右键人物框：只删除该 Shot 内对应 R 角色的 Timeline clip、Shot 覆盖（identity/bbox override）及绑定条目中属于本 Shot scene 的索引；全局 all-appearance 绑定与其他 Shot 不受影响，整组操作进入同一 Undo 宏。
- Ctrl+左键点选已有人物框：自动把该角色矩形收缩为合格规格（面积 <0.82 且不再同时满足宽≥94%、高≥82%，与 Relay 引擎 _normalized_person_bbox 拒绝条件一致），围绕原框中心缩放；已经合格的框保持原有加选/取消行为。
- 打开 Shot Visual Editor 时大脸自动合格框：角色唯一证据框接近全画面或不合格格规格（近景大脸）时自动写入合格规格矩形覆盖，避免引擎再报 "no reliable box"；保存后随 source_role_bbox_overrides 持久化。
- 删除某 R 的 Shot 绑定时，若该 Shot lip-sync target 指向被删 P 图则回到 Auto；SWAP 行同步取消勾选。
- Project Format 保持 29（本版本只改 UI/覆盖写入路径，不改 Relay 编译规则）。

### Verification
- 62 项目标测试全部通过（含 1 项跳过）；director_cut_studio / character_swap_engine / smart_render_worker / source_video_analysis Python 编译检查通过。

## Unreleased - 2026-11-08

### Round 122（2026-11-11）：角色替换**推倒重来**——Studio 编译出来的图现在跟他手动那张只差输出前缀，真跑 501.7 s 与他那枪**逐帧色差 0.0**
- 根因先用他自己 ComfyUI 的 `/history` 钉死（不是推测）。三枪逐项对齐：他手动成功那枪 `107a19c7…`（46 节点、Picture 1 = 原始 P1 `z-image-upscaled_00002_.jpg`、`resolution=768`、提示词 **2 875 字、无 SILENT、无 hair**、turbo 1.0 + swap 1.0、`expansion_px=128`）；Studio 的 `h3_project_333`（`c082066c…`，同 46 节点、同 LoRA、同 128）**只有三处不同**：Picture 1 换成 preset 08 sheet、桶 `480`、提示词 **4 051 字（SILENT ✓ hair ✓）**；旧那支 35 节点成功片（`3567cbc5…`）是另一张无遮罩图、4 439 字。
- **他删掉的字被另一个文件加回来**：引擎 `character_swap_engine.py:19` 那侧（旧 `:26` 写死收割文件）从 `H3-Character-Swap-Relay-V2-api.json` 收割作者提示词（`:1674` 读文件、`:5566` 写回 conditioning），而**提交**的是 WITHMASK（`:4713`）。api.json 现值 2 876 字 + 静音改写 19 字（`visible mouth movements` 被就地换掉）＝ manifest 里的 `author_prompt_chars = 2895`，再 +1 156 字条款＝ 4 051 字。他改 WITHMASK、手跑有效，Studio 一律覆盖。
- 他 11-11 的清单式选择（我列 17 步，他勾删 7/9/10/13/16 + 桶回 768）逐条落地：
  - **第 10 步（追加条款）删**：新开关 `H3_CHARACTER_SWAP_PROMPT_APPENDIX` **默认关**（`character_swap_engine.py:4372`），路线 3 的三处例外——静音尾 `:3507`、`Authored mouth direction` `:3509`、头发归属句 `:3514`——加非人类锁 `:3523` 连同静音改写一起静默；`build_character_swap_prompt` 现在交 **2 875 字，与他模板里的原文逐字节相同**，审计新增 `prompt_appendix` / `prompt_source` 两行，免得 `append_chars: 0` 被读成"门没触发"。
  - **根因 1 修**：收割来源改为跟着 `character_swap_workflow_name`（`:4869`）走——提交 WITHMASK 就收割 WITHMASK，那张不在磁盘就退回 api.json，绝不因缺文件停 Shot；退路 `H3_CHARACTER_SWAP_PROMPT_SOURCE=api`。
  - **第 12 步（分辨率桶）改回 768**：`PREPARE_RESOLUTION_HIGH = LOW = "768"`（`:4487-4488`）。依据是他那一枪的 `prepare.resolution` 就是 `768`、Studio 是 `480` 且被他判失败，Round 53 也早量过 480 会把角色画老画糊。代价（Preview 慢一倍）他先确认。
  - **第 13 步（身份 QC）降级**：新开关 `H3_CHARACTER_SWAP_IDENTITY_QC=record`（`director_cut_studio.py:2678`，唯一收口在 `_character_swap_identity_failed:35888`）。`h3_project_333` 其实 `segment.status="complete"`、`generated_preview.mp4` 已出，只是 `similarity 0.3198 / risk 1.0597 / attempts_used 1` 被判 failed 后被 **7 处**审批/取用门拒（`:39973 / :40045 / :42120 / :42134 / :42265 / :42322 / :42387`）。`record` 只让判决不再拦路，audit 与尝试表照样落盘；默认 `gate`，写坏了退回 `gate`。
  - **第 9 步（压片）关**：`design_ai.env` 里 `H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1 → 0`。它同时也是头发那句的唯一触发者（`suppressed_plate` 才加，`:3481-3483`）。
  - **第 7 步（identity sheet）不动代码**：Studio 界面上本来就有这个总闸——Design 页「AUTO-COMPOSE WHEN PICTURE 1'S FACE IS TOO SMALL」（`:12463`，说明文字最后一句就是 "Turn this off to always send the original picture"），逐工程存 `identity_sheet_enabled`。**遗留**：`h3_project_333` 那个勾还开着，他下次 Preview 前取消，否则 Picture 1 仍会被拼成 sheet。
  - **第 16 步（VSR）**：本来就没挂（`output_upscale_skip_reason="environment_disabled"`）。
- 真枪验证（`testing/_dsh_verify_13/godzilla/parity_122.py`）：只喂编译器「他提交的模板 + 他那一枪的素材与种子」（`pass_01_R1_00003_.mp4` / 原始 P1 / seed 96928213054262 / 0.5 MP 请求），编译出的 46 节点图跟他那张成功图**逐输入比对只差 2 处**：`save.filename_prefix` 与 `video-preview` 占位；`model_identity_drift = []`；contract 写 `收割自 …WITHMASK.json，未追加条款`、`relay_prepare_resolution = "768"`、强度 1.0。提交 `24f0fe37…` → **success，501.7 s**，出片 576x864@24、188 帧（与他那支的几何、帧数完全一致）。对照表 `testing/_sheet/122/parity_frames_122.png`（四行：V1 源 / 他成功 / Studio 那枪 / 新链路）：他成功那行是新角色全程清晰；Studio 那行 t=5.0s 与 7.0s 人物**糊成一团雾**；新链路那行与他那行**同图**——逐时刻平均色差 **0.0 / 0.0 / 0.0 / 0.0**，而 Studio 那枪对他那枪是 9.8 / 14.3 / 17.3 / 13.0。
- 测试：新增 `testing/test_round122_parity_rebuild.py`（19 项）钉住"默认一个字都不加、收割跟着提交的图、桶 768、QC 只记录、他 env 现值"。另修 8 项因**他 11-11 重存模板**而失效的旧钉法（他新文件里 `expansion_px` 已是 128、两颗 LoRA 都是 1.0、Turbo 换成 768p 那颗）：`test_round112` 的"两张图模型侧完全一致"改成"只在他改过的那两处不同，底模型与 Picture 1 增强仍不许动"，漂移基准从 api.json 换成同一张 WITHMASK；`test_round117` 的强度 1.5 → 现读的 1.0、"开关只动两个节点"改成钉作用域（他这份图已写官方那个数，强度开关一处都不动）。24 套相关回归全绿（`test_round52_swap_routes` 48 项补了 `setUp` 显式钉 `gate`——`director_cut_studio` 在 import 时就把 `design_ai.env` 灌进环境，导演机器上是 `record`）。
- 顺手更正一条我早前说错的结论：`H3_IDENTITY_SHEET_CLOSEUP_PRESET` **确实在** `DESIGN_ENV_RENDER_KNOBS`（`director_cut_studio.py:457`），worker 会按 env 刷新它；但 Studio 拼 sheet 读的是 import 期的模块常量（`:2702`，默认 `"8"`；使用点 `:36700 / :36718 / :36781`），所以**Studio 里换预设仍要重开**。`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH`(`:2615`)、`H3_IDENTITY_SHEET_VIEW_SOURCES`(`:2767`)、`H3_CHARACTER_SWAP_SAM_MASK_SELECTION` 不在名单里，改了必须重开。
- 现场注意两条：代码改过 → **Studio 要重开**才吃到新的桶与收割规则；`design_ai.env` 里那两个新旋钮是热旋钮（worker 每次启动刷新）。另外这次发现 `design_ai.env` 的**注释块会被 Studio 写设置时冲掉**，只有 `KEY=VALUE` 行稳定，所以这次的依据注释也一并写进了 CHANGELOG 而不只留在 env 里。
- 导演 23:49 回报：新片**完美**，但 Final 从 ~7 min 变 ~14 min，他怀疑是"生成 motion_preview＝生成两段视频"。当场用他自己机器上的数拆干净——**两段视频的猜测不成立**：22:50 以后 ComfyUI `output/` 只落了 **1 支** mp4（23:21:16 的 `studio_character_swap/segment_001_000000000_000007850/pass_01_R1_00008_.mp4`，5 605 706 B），Final manifest 里也只有 1 条 `prompt_id`、`pass_total: 1`；他看到的第二支是 20:10 的旧 `takes/motion_preview.mp4`（Final 只写 `approved_final.mp4`，那个时间戳没被碰）。真正原因是**旧的 480 桶一直在偷压 Final 的像素**：`QUALITY_PROFILES["approved_final"]` 名义 `1.0`（`project_workspace.py:79-85`，标签 "Approved Final · 1.0MP"），可改前那支 18:06 的 Final（`a_woman_in_a_pink_dress_and_polka_dots_33`，桶 480、名义 1.0 MP）**实出 576x864 = 0.498 MP**，与 Preview 同尺寸；改后 23:21 的 333 Final（桶 768、名义 1.0 MP）**实出 800x1248 = 0.998 MP** → 像素 **2.006×**、墙钟 2×，跟他量的 7→14 min 吻合。Preview 档不受桶影响：0.5 MP 请求下 768 桶仍是 576x864（我 22:45 那枪实测 501.7 s）。再记一条依据：他判完美的手动那支 `pass_01_R1_00008_.mp4` 本身也是 **576x864**。导演看完这份数**选择保持 768**（Final 一枪定片，14 min / 0.998 MP），代码不动；退路仍是 `character_swap_engine.py:4487` 改回 `"480"` 一行。
### Round 120（2026-11-11）：按导演那条链真的造出多角度参考图并跑了真枪 —— 在这张鱼眼镜头上它**退**，原因写在他自己的条款里
- 素材侧先补齐：`testing/_dsh_verify_13/godzilla/angles_120a.py` 用他自己 ComfyUI 上的 `sd_xl_turbo_1.0_fp16` 做 i2i 转体（他机器上没有 z-image 底模，cast 那两张是别处出的），4 张角度图共 **25.5 s**；命名严格按 Studio 扫描规则（`director_cut_studio.py:2747-2760` + 36392-36504：同文件夹、同家族 `p1`/`p2`、文件名带**整词** `side`/`rear`），放进 `example/godzilla_action_figure_by_neca_6/media/imported/`。
- 挑片看帧，不猜（`testing/_sheet/120/turnaround_120a.png`、`p2_sweep_120b.png`）：godzilla 的 side 保住了深色与背鳍紫调；gundam 第一版**跑偏**（蓝胸画成红、黄色进气口没了、盾上多了星、步枪变灰），`angles_120b.py` 把配色一项一项写进正向、负面禁掉 `red chest`/`yellow star`，**side 去噪 0.55** 才配色全对；两张 rear 都没真转到背面（还是 3/4 正面），godzilla 的 rear 色调还比正面浅 —— 与正面矛盾的面板比缺面板更坏，**全部删掉**，最后两个角色各只留一张 side。
- 真枪（`selfrun_120c.py`，R2 916.9 s、R1 约 1030 s 按落盘时间 13:11→13:39 推算，两枪 success）：Picture 1 换成 preset 9 多角度 sheet，提示词用引擎 `character_swap_engine.py:3036-3052` 那段 sheet 条款**原文**（`build_character_swap_prompt` 对 manifest 那种 pass 行走"作者提示词"分支不会自带这段，探针里拼原文并带防漂移断言），强度 1.5、expansion 128、遮罩词与选择都不动。对照表 `testing/_sheet/116/round120c_multi_angle_sheet.png`：
  - **R1**：t=0.5 s 场景里长出**两只机甲**（sheet 的角度/镜像面板被读成第二个人），而 118 那版是一只完整 RX-78；
  - **R2**：godzilla 变小，t=7.0 s 近景**退回复原演员的金发脸**，而 118 那版是一整颗 godzilla 头。
- 结论不是"sheet 没用"，而是**素材类型与条款不符**：那段条款自己写着"每个面板是同一张图的**不同缩放**（different zoom）"，我给的是不同角度、不同渲染，模型就按多个人读。所以 121 接着验 Studio 本来就会拼的那种（preset 0：同图头特写 + 全身，`selfrun_121.py`，其余接线与 120c 一字不动）。
- 顺带钉住规则：`testing/test_round120_identity_sheet_views.py`（8 项绿）—— 两个角色的 side 必须在位、被判掉的 `P*_rear.png` 不许回来、preset 9 只认同家族那张 side 且返回绝对路径、preset 0-8 不标角度就一律不看、别人家族的 side 不能借、`sideburn`/`playback`/`background` 这些词不许冒充角度；另钉两件事：`IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH` 出厂为开（关它的写法仍是 `0/off/false/no`，启动时读，改完要重开 Studio），以及**近景门默认会把预设压成 8**（要 preset 9 得 `H3_IDENTITY_SHEET_CLOSEUP_PRESET=-1`）。
### Round 118（2026-11-11）：遮罩扩张 64 → 128 是这一轮唯一被帧验证过的增益；官方 api.json 与他那份图逐节点对过
- 依据落地：官方 `examples/H3-Character-Swap-Relay-V2.api.json` 已存成 `testing/fixtures/h3_relay_v2_api_official_20261111.json`。逐节点对过：导演那份 WITHMASK 的 `mask → recover → expand_mask → window → encode_source → edit_mask` 接线与官方**完全一致**，类只多一个 `SolAttnMiniMaxH3Patcher`。**官方图里没有任何压片** —— `window.0` 原片直接进 `VAEEncode`，改哪儿完全由 `H3RelayApplyEditMask` 那根遮罩限定 ⇒ 遮罩没盖住身体，模型就没有地方画身体。
- 免费量法（零扩散、只跑 SAM 链）：`testing/_dsh_verify_13/godzilla/mask_expansion_118.py`（把图剪到 `expand_mask` 的祖先、接 `MaskToImage`+`SaveImage`，再按 Studio 自己的两个角色框量覆盖率，每例 44 帧）：

  | expansion_px | R2 盖住本角色 | R2 平均 | R2 串对面 | R1 盖住本角色 | R1 平均 | R1 串对面 |
  | --- | --- | --- | --- | --- | --- | --- |
  | 64（官方值） | 31/44 | 0.5252 | 0.1995 | 22/44 | 0.4824 | 0.3590 |
  | 96 | 42/44 | 0.6315 | 0.2590 | 29/44 | 0.5505 | 0.4149 |
  | **128** | **44/44** | 0.7285 | 0.3233 | 33/44 | 0.6208 | 0.4713 |
  | 160 | 44/44 | 0.8184 | 0.3924 | 38/44 | 0.6916 | 0.5283（开始啃对面框） |

- 真跑确认（`testing/_dsh_verify_13/godzilla/selfrun_118.py`，从他提交图 `/history/<prompt_id>` 里取那 46 个节点、只动 `expansion_px`，R1 772.2 s / R2 1022.2 s，两枪都 success）：`testing/_sheet/116/round118_expansion_128.png` 上 **R2 三个时刻（t=0.5 / 3.5 / 7.0）都是完整、身份对得上的 godzilla**——官方 64 在 t=7.0 近景处留的是没画开的原演员黑发脸；**R1 第一次画出整只 RX-78（带光束步枪和盾）**，此前 11 次真跑没有一次做到。
- 于是默认改：`SAM_MASK_EXPANSION_PX_DEFAULT = 128`（注释里带上面那张表）。一行退回官方：`H3_CHARACTER_SWAP_SAM_MASK_EXPANSION_PX=64`。
- Round 117 的 2×2 也落地了（`testing/_sheet/116/round117_prompt_vs_strength.png`，R2 同一镜头）：只有**他自己的两个数**（Studio 长提示词 + 强度 1.5）画出角色；官方一句 / 强度 1.0 各自单改都退成剪影。所以提示词与强度默认退回他的数，官方两处留成开关 `H3_CHARACTER_SWAP_PROMPT_RECIPE=on`、`H3_CHARACTER_SWAP_LORA_STRENGTH=official`。
- 顺手把官方对照做完（都从他提交图与服务器 `/object_info` 实测）：`steps 8`、`normal`、`er_sde`、`CFG 1`、shift `12/3`、`window_frames 124`、`history_frames 18`、`detect 0.35`、`track 0.5`、`max_objects 1`、`detect_interval 1` 全一致；仍不一致的只剩三处 —— **turbo LoRA**（他用 `minimax_h3_turbo_v4_step600_ema`，官方 `minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16`，服务器确认这个文件**在他机器上有**）、UNET 与 video VAE 的量化变体（官方版同样都在）、分辨率桶我们 Preview 走 480 而官方写 768。

### Round 119（2026-11-11）：导演点出他的替换是「character sheet 先出多角度参考图」，查下来这一枪被单图透传绕过了
- 证据：06:32 那一枪 manifest 两行都记 `identity_sheet_single_figure_passthrough = true`、`reference_framing = illustrated_full_design`；Picture 1 原件我看过了，是 2048×2048 的**单张全身正视图**，不是 sheet。
- 门槛在 `director_cut_studio.py:36595-36609`：单图 + 头占比/占面过线 + 素材 ≥ `H3_IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS`（0.35 MP）就直接透传单图。一行关掉：`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH=0`（这两个 name 不在 `DESIGN_ENV_RENDER_KNOBS` 里，改完要重开 Studio）。
- 免费（纯 CPU）试拼了一遍：`testing/_dsh_verify_13/godzilla/sheet_reference_119.py` → `testing/_sheet/119/`。`SHEET_PRESETS` 里**只有 preset 9 带 front/side/rear 真角度面板**，preset 0 与 8 都只是「同一张图不同缩放」；而且 preset 8 拼 godzilla 那张**把头裁掉了**（上格背鳍特写、下格无头身体）⇒ 光关透传不够，反而丢脸。
- 素材事实：`example/godzilla_action_figure_by_neca_6/media/imported/` 每个角色只有 1 张（P1、P2 各一），没有 side/rear ⇒ preset 9 的 `collect_view_sources` 收不到角度图。要和导演那条链对齐，得先为每个角色生成 front/side/rear 三张 —— 这正是他代码里 character sheet 的职责，等他点头我就接上跑。
- 清账：`testing/test_round59_reference_detail.py` 那 6 个红是旧账（现在两份模板里都没有放大/增强节点，35 与 46 个节点都数过），`setUp` 现在说实话并 skip，套件回到 26 绿 6 跳。
### 10:05 回到作者公布的配方 —— Round 117（2026-11-11 上午）

**导演的话：「H3-Character-Swap-Relay-V2-API-WITHMASK.json 本来就可以一枪成功，别搞自己的实验，按照原本 h3 的提示词跑」**，并给了两份依据（模型卡 `akatz-ai/MiniMax-H3-Character-Swap-LoRA` 与 `github.com/akatz-ai/h3-relay`）。我把他那一枪**真正提交过**的图从 `/history` 读回来（R1 `89d80ec3-…`、R2 `55d2785c-…`），跟官方 `examples/H3-Character-Swap-Relay-V2.api.json` + `examples/README.md` 逐项对：**我们只偏离了两个官方数**。

| 官方 | 他那次实际提交 |
| --- | --- |
| 提示词就一句：`Replace the selected person with the reference character. Preserve source performance, scene and audio timing.` | Studio 自造的 2860 字长文（`<Subject 1>`/`<Subject 2>` + wardrobe 那套） |
| `strength_model: 1.0`（卡片："Download V1.5 — recommended, strength 1.0"；README："both LoRA strengths at 1"） | `1.5` |
| steps 8 / normal / er_sde / CFG 1 / shift 12.0+3.0 / SAM 0.35+0.5 / max_objects 1 / detect_interval 1 / expansion 64 / window 124 / history 18 | 全部一致 ✓ |

**改。** `compile_character_swap_pass` 的 v2 分支往 `MiniMaxH3ReferenceToVideo` 写的是**作者原句**（`CHARACTER_SWAP_RECIPE_PROMPT`，逐字符照抄官方 api.json）；swap 适配器强度由新的 `character_swap_lora_recipe_strength()` 决定，空值＝官方 1.0，越界仍走 `clamp_character_swap_lora_strength`（引擎自带上限 1.7）。两条各一行退回：`H3_CHARACTER_SWAP_PROMPT_RECIPE=off` 回到 Studio 那段话、`H3_CHARACTER_SWAP_LORA_STRENGTH=template`（或 `1.5`）回到图里的数。**Studio 自己那段话没有丢**，合同里 `swap_prompt_studio` 照样记着，`swap_prompt` / `swap_prompt_source` / `swap_prompt_official` / `swap_lora_strength_source` 都进 manifest——不然以后没人知道模型当时到底被喂了哪句话。

**一处特意不动：** 480/768 的分辨率桶是看「提示词里有没有 apparent-age lock」决定的，而这条判断照旧读 Studio 那段话。也就是说换措辞**不会偷偷改变这一镜的成本**，只有模型真正看到的文字变了（测试 `test_the_resolution_bucket_this_shot_earns_does_not_move_with_the_wording`）。

**守卫更新（这两条本来守的是旧行为，改成守官方事实）：** `test_compiled_pass_uses_native_relay_v2_and_resets_window_seeds` 现在断言 conditioning 收到的是官方原句、强度 1.0、并且 Studio 那段话仍在合同里；`test_the_compiled_mask_graph_changes_no_model_constant_of_the_directors`（"引擎不许重写导演的图"）以前会把 `strength_model` 也要求原样，现在明确写死：**只有这两个官方数可以动**，swap 适配器必须是 1.0，其余适配器（FL2V turbo）一个字节都不许变。

**新套件 `testing/test_round117_official_recipe.py`（12 项）** 还把那张审计表钉成代码：`test_every_other_published_number_already_matched` 逐节点断言 8 步 / normal / er_sde / CFG 1 / shift 12+3 / window 124 / history 18 / SAM 0.35+0.5 / max_objects 1 / detect_interval 1 / expansion 64 就是官方那几个数——下次再有人怀疑是不是提示词的问题，先看这张表，别靠猜。`test_only_the_two_published_numbers_move_in_his_graph` 则保证默认开与全退回之间，**图上只有 `reference_conditioning` 与 swap 适配器两个节点不同**。

**真跑（他那两台原图、只改这两处，其余一字不动）：** R1 `leftmost` 937.6 s、R2 `rightmost` 681.8 s，两遍都 `success`；提交前打印过改动：`提示词前 60 字 = Replace the person in <Video 1> with the character shown in …` → 官方那一句，`强度 1.5 → 1.0`（来源记为「官方说明与 README 的数」）。**画面结果（`testing/_sheet/116/round117_verdict.png` 第 3、6 行）：这两枪比 115 那一版更弱。** R2 的 t=0.5s 右边只剩一个黑影，115（强度 1.5）那一版同一帧是整只 godzilla；t=3.5s 也退化成剪影；R1 左边没有 gundam，仍是原人物加一层头脸。也就是说这一镜上「官方提示词 + 强度 1.0」一起上会把替换力度压下去。

**还差最后一格才能分清是谁的锅，正在跑：** 117b 把两个变量拆开各跑一遍 R2——G1 官方提示词＋强度 1.5（只改提示词）、G2 Studio 长提示词＋强度 1.0（只改强度）。加上已有的 115（长文＋1.5）与 117（一句＋1.0），这四格就是完整对照，谁该留谁该退回由帧说话，不靠猜。

**交接卡：** 本轮两枪都在 45 秒一跳的租约里跑，跑完 `claim none`。
### 08:30 这一轮把「擦哪」也交给 SAM 遮罩 —— Round 116（2026-11-11 上午）

**四枪定责。** 接着 Round 115 剩下的那条（左角色换不出来），我在他的 ComfyUI（`127.0.0.1:8189`）上把同一个镜头又跑了三遍，逐帧并排看（`testing/_sheet/115/round115_r1_four_way.png`）：

| 哪一枪 | 片源 / 遮罩 | 用时 | 画面结果 |
| --- | --- | --- | --- |
| 他的 R1 06:20 | 压片只擦头 / `person`+`largest` | — | gundam 站到画面中间，左边没换 |
| 115b R1-A 07:27 | 压片只擦头 / 词+`leftmost` | 1007.8 s | 左边只多出一小只倒在左下，审计那句「只画了一层头脸」就是这么来的 |
| 115c R1-B 07:59 | **未压片原片** / 同一遮罩 | 1118.2 s | 画面干净无糊，左边还是原人物，**一只 gundam 都没出** |
| 115d R1-D 08:20 | 整块角色框糊掉 / 同一遮罩 | 837.5 s | 那块比遮罩宽，遮罩没盖到的部分**永远灰糊着**，什么都没往里画 |

**结论不是「擦多一点」。** 没有擦除就不换（115c），擦得比遮罩小就只画头层（115b），擦得比遮罩大就留一块没人画的灰糊（115d）。三次的公分母只有一个：**遮罩才是两边唯一同意的形状**——正是导演那句「用 sam3 沟边」。

**修。** 压片改在**图内**由遮罩生成：`H3RelayWindowInputs` 第 0 脚是这一窗的画面、第 1 脚是同一窗的遮罩（`H3RelayApplyEditMask` 本来就用这一对），新接 `ImageBlur` + `ImageCompositeMasked` 拼出「遮罩内糊、遮罩外留原片」，再把 `VAEEncode.pixels` 从 `window.0` 改接到它。新增两个节点、只挪一根线，测试 `test_two_nodes_appear_and_only_one_wire_moves` 逐节点比对：除 `encode_source` 外**任何一个节点的输入都不许变**。两个新节点的 schema 是从他那台 ComfyUI 的 `/object_info` 现场抓进 `testing/fixtures/comfyui_swap_node_schemas_20261109.json`（46 类 → 48 类），不是抄的——Round 112 那条「必填输入对着服务器 schema 校验」的守卫这才继续管用。
旋钮：`H3_CHARACTER_SWAP_IN_GRAPH_PLATE`（默认开）、`…_BLUR_RADIUS`（默认 24 px，Studio 给头带来的 boxblur 半径就是这个量级）、`…_SIGMA`（默认 1.0）。`=off` 一行把压片交回 Studio 的压片带，逐字节不变。

**真跑（引擎自己的函数写在他那一枪的原图上，词/选择器/压片全走引擎代码）：** R1 973.2 s、R2 671.6 s，两遍都 `success`，引擎回报 `in_graph_plate=True`、新节点 `plate_blur`/`plate_masked`、`VAEEncode 之前接的是 {'encode_source': ['window', 0]}`（`testing/_sheet/116/round116_verdict.png` 第 3、6 行）。R2 右边仍是整只 godzilla（无回退），R1 左边**第一次出现了站着的 gundam**——但还没干净：Studio 那条糊带在遮罩外，**图内压片只能加糊、不能把 Studio 已经糊掉的带还原**，所以遮罩外的带子照旧灰糊。

**最后一半也被画面否掉了（同日 09:2x / 09:3x 两枪）。** 接着测「未压片原片 + 引擎图内压片」：R1 `leftmost` 1152.2 s、R2 `rightmost` 847.0 s，两张都 `success`（`testing/_sheet/116/round116b_verdict.png` 第 3、6 行）。**灰糊问题确实彻底消失了**——这是它对的部分；可右边又变回黑影、没有 godzilla，左边画出来的是人形不是 gundam。对照上面 116 那两枪（R1-E 左边出现 gundam、R2-E 右边整只 godzilla 但 t=3.5s 退化成金发怪物）：**九枪真跑下来，每一遍都变好的只有遮罩那一半（Round 114/115）。「遮罩内糊」治得了灰糊，治不了「画什么」。**

**所以这条默认关。** `H3_CHARACTER_SWAP_IN_GRAPH_PLATE` 留在实验位：默认 off 时 VAEEncode 仍直接吃 `window.0`，也就是他认可的那两张压片带原样进图，一个字节不多动；要试就 `=on`，半径 `…_BLUR_RADIUS`（默认 24，1-96 之外与垃圾值都退回默认）、`…_SIGMA`（默认 1.0，0.05-8.0）。这条决定由 `test_the_shipped_default_is_off_because_the_frames_said_so` 钉住，理由就是上面那几个秒数与帧。

**测试。** 新套件 `testing/test_round116_in_graph_plate.py` 12 项（只多两节点只挪一线、schema 来自他机器、关掉逐字节回去、半径/sigma 的垃圾值与越界都退回默认、撞名不压掉别人的节点、`VAEEncode` 接法不对就报告不改图、空模板照旧什么都不加、三个名字都是渲染旋钮）。当天全量扫荡 18 个套件 402 项全过：`test_character_swap_engine` 20、`…_silent_audio` 8、`…_background_extra` 9、`test_round52_swap_routes` 48、`test_round105_nonhuman_swap` 10、`…_closeup_gates` 79、`test_round110` 24、`test_round111` 22、`test_round112` 22、`test_round113` 12、`test_round114` 18、`test_round115` 14、`test_round116` 12、`test_smart_render_worker` 48、`test_smart_render_qc_advisory` 4、`test_comfy_connection_recovery` 8、`test_identity_sheet` 67、`test_smart_cut_engine` 7。

**交接卡。** 这一上午连着跑了七枪（约 100 分钟），每枪都有 45 秒一跳的租约续着，跑完全部干净交回 `claim none`。
### 07:00 这一轮把「遮罩的词」和「左右」都改成有数可依 —— Round 115（2026-11-11 早上）

**现场。** 导演 06:32 那一枪（`godzilla_action_figure_by_neca_6`，job `preview_8053966229313392623_1794348343547891800`）交出来的东西他自己判「完全失败」。App 自己的账本写得很清楚：pass R1 `target_likeness_score 0.267288`，理由 `replacement is only a head/face layer; the V1 wardrobe still fills the upper…`；pass R2 `-0.039467`，理由 `source actor silhouette remains behind the replacement`。两遍 `maximum_attempts 1`、`attempts_used 1`——审计已经喊出败因，还是一枪就交出去。合成又回退：`SAM3.1 weak association - manual box required: Current Role(s) R1 0.52 sat below 0.70`。

**证据链。** 到 ComfyUI（`127.0.0.1:8189`）把那一枪的两遍原图取出来（`/history` 里 `prompt[2]` 就是当时提交的 46 节点图）：遮罩词写的是 `subject="person"`，选择器写的是 `selection=largest`、`index=0`——**两遍遮的是同一个人**。`.director_cache/director_crash.log` 最后一行是 `=== session 2026-11-11 06:05:04 ===` 的会话起始行，说明 Studio 是在 Round 114 改完之后启动的：代码在跑，只是被两处挡住。
1. 词被 `H3_CHARACTER_SWAP_NONHUMAN_TARGET=off` 挡掉：pass 行里 `nonhuman_target_nouns = []`，而这工程 cast 认读文字里 P1→`godzilla`、P2→`gundam` 都在，只是取词那段白看了那个开关一眼。`person` 一个词在这种双角色镜头里只回 1 个 object（Round 113e 实测），于是两位角色共用同一根遮罩。
2. 左右比较读的是渲染当时那份 `self.cue.source_role_bbox_overrides`。这工程的 cue `S1`（0.000-13.980s）其实**有**框（`R1 [0.072203,0.249445,0.617203,1.0]`、`R2 [0.606356,0.264815,1.0,1.0]`），另有两个 cue 是空的——这次取到的正是空的那份，于是落回 `largest`。

**修。** 两条都不动他认可的做法（各角色分别生成、SAM3 沟边、再合成）：
- 词不再看那个开关的脸色（它只该决定压片带数、cast lock 与重试次数），直接用本镜头 cast 认读里的名词拼成 Round 113e 实测会回 3 个 object 的那串 `person, gundam, godzilla`。
- 左右改从**这一遍自己编出来的压片几何**里取：`identity_suppression_geometry` 的 `hair_extent/figure_extent` 里 `applied[*]` 的 `band/face_band/pieces` 就是本角色，`protected_boxes` 就是对面那位——逐字等于合成器打分用的那两个框。`character_swap_sam_mask_boxes_from_geometry` 顺带把 x/y/w/h 的条带换算成 xyxy（R2 的条带 `0.617203+0.382797` 正好贴右边缘，按 xyxy 读会得到 right < left）。导演的框仍是第一选择，只是不再是唯一来源。

**免费实测（零扩散，整片 345 帧、每 8 帧量一次，与 Round 113e 同一把尺）：**

| 角色 | 选择器 | 盖住本角色 | 本角色平均 | 串进对面 |
| --- | --- | --- | --- | --- |
| R1 左 | leftmost | 30/44 | 0.6235 | 0.1777 |
| R2 右 | rightmost | 31/44 | 0.5252 | 0.1995 |

Round 113e 用 `person` 时同一条是 R1+leftmost 0/21、平均 0.1274。

**真跑（用他自己提交过的原图，只改这两处，模型、LoRA、seed、窗口、像素一律不动）：**
- R2 右角色 766.8 s：t=0.5s 与 3.5s 右边出现**整只 godzilla**；他那一遍同一帧右边始终是糊着的人形。对照表 `testing/_sheet/115/round115_before_after.png` 第 3、4 行。
- R1 左角色 1007.8 s：左边仍未换成 gundam（他那遍 gundam 站到画面中间，我这遍倒在左下）。对照表 `testing/_sheet/115/round115_r1_three_way.png`。
- 追责对照 R1-B：只把片源换成**未压片原片**、遮罩不动，1118.2 s → 画面干净无糊、左边仍是原人物、一只 gundam 都没出。**压片不是拦路虎，它是「换」的驱动力：擦多大块，模型就画多大块。** 所以左角色缺的是把整块身体擦掉（`H3_CHARACTER_SWAP_NONHUMAN_TARGET=on` 那条路），本轮已在用 App 自己的 `crop→boxblur→overlay` 写法做整身压片验证（`testing/_dsh_verify_13/godzilla/selfrun_115d.py`）。

**交接卡。** 三枪连跑约 50 分钟，`comfy_claim.json` 全程被 45 秒一跳续着（两次相隔 45 秒读到 `"note":"selfrun-round115-…"`），跑完干净交回 `claim none`。

**注意。** `design_ai.env` 会被 Studio 按 allowlist 重写：旋钮行一条不少（23 行 `H3_CHARACTER_SWAP_*` 都在），但 Round 113/114 两段注释块被抹掉。往后的记录以本文件为准。

**测试。** 新套件 `testing/test_round115_mask_words_and_geometry.py` 14 项（条带 xywh→xyxy、垃圾矩形不炸、本遍几何给出本角色与对面那位、两遍分到左右、`=off` 一行退回、导演的框优先、那一枪 manifest 的空名词/两条败因/一次尝试实录、cue 框的真实分布）；`test_round114_sam_mask_role_selection` 18、`test_round112_in_graph_sam_mask` 22、`test_character_swap_engine` 20、`test_character_swap_closeup_gates` 79 全过；`py_compile` 两个文件 exit 0。

**退回。** `H3_CHARACTER_SWAP_SAM_MASK_AUTOSELECT=off` 一行把词与选择器一起退回今晚之前那张图。生效条件：完全退出 Studio 再重开。

### 00:00 这一轮让 SAM3 的遮罩跟着「该换的那一位」走 —— Round 114（2026-11-11 凌晨）

**现场。** 导演说「跑完才谈 Preview」，所以这一轮全部用零扩散的免费探针量：SAM3 检测约 2.3 秒一次、整片追踪 29 秒一卷，钱一分不花。

**先把「遮罩到底跟着谁」量出来**（`testing/_dsh_verify_13/godzilla/`，113d 与 113e 两轮，对着导演自己画的角色框 R1 `[0.072203,0.249445,0.617203,1.0]` / R2 `[0.606356,0.264815,1.0,1.0]` 打分）：

| 帧 84 的 subject 文本 | 回到几个 object | 遮罩落在哪 |
|---|---|---|
| `person`（**模板里就是这个**） | **1** | R1 被盖 0.5244、**R2 被盖 0.0000** |
| `person, gundam, godzilla`（合成器一直在用这串） | **3** | largest 仍是最左边那位 |
| `person, godzilla` / `toy action figure, person` | 2 | largest 仍是最左边那位 |
| `gundam, godzilla` / `godzilla` / `gundam` | 2 / 1 / 1 | 全是 0.03 的小团 |

同一帧换选择器：`largest` / `leftmost` / `index 0` 都拿到左边那位；**只有 `rightmost` / `index 1` 够得到右边那位**。整片追踪每 8 帧采样：

| 全片链路（subject = `person, gundam, godzilla`） | 盖住本角色的帧 | 平均盖住本角色 | 串进另一角色 | 用时 |
|---|---|---|---|---|
| R2 + `rightmost` | **21/21** | **0.3909** | 0.0772 | 46 s |
| R1 + `leftmost` | 0/21（首帧 0.5244，一路掉） | 0.1274 | 0.0 | 279 s |

Round 113d 还顺手否掉了一条看起来最像答案的路：`SAM3_Detect` 的 `positive_coords` / `bboxes` 在这个 build 里**没有作用**——16 个变体（左边点、右边点、头顶点、加角色框、加对面负点）遮罩逐位相同（覆盖率 0.2150 / 0.0743 / 0.4267 三档一模一样）；格式写对（JSON `[{"x": int, "y": int}]`）只是不再报错，不改变结果。

**结论是三条缺陷，不是一条。** ① 图内遮罩写死 `person`，两个角色的帧只回 **1 个 object**；② 引擎又把选择器硬写成 `largest + index 0`（`character_swap_engine.py:4842-4845`）——于是两个 pass 都 repaint 最大那位（左边），**右边该换的从来没被遮过**，这正是导演看到「完全没有 sam3 沟边」的成因，也是合成器 `R1 0.46 sat below 0.70` 弱关联回退的另一半原因；③ 即便文本与选择器都修对，`leftmost` 那条追踪会在片内退化，`rightmost` 稳。

**改了什么（你的做法一个字没动：各角色分别生成 → SAM3 沟边 → 合成）。**
- 遮罩的**词**由 Shot 自己决定：`character_swap_sam_mask_union_subject` 以旋钮 `H3_CHARACTER_SWAP_SAM_MASK_SUBJECT`（默认 `person`）为底，接上每个 pass 的 `nonhuman_target_nouns`，与合成器 `sam31_text_prompt` 同源、同 160 字符上限 —— 上面那张表里就是它产出 `person, gundam, godzilla`。
- 遮罩**跟谁**由你画的框决定：`character_swap_sam_mask_selection` 比较本角色框与其余角色框的中心（相差 0.05 以内算同侧），左用 `leftmost`、右用 `rightmost`；只有一个角色、没有框、框是垃圾、数字不合法一律 `largest`。Studio 读的是 `cue.source_role_bbox_overrides`（Round 113 之前从来没参与过掩码决策）。
- `apply_character_swap_sam_mask_graph` / `compile_character_swap_pass` 多了三个默认空的参数（旧调用逐字节不变），manifest 里多出 `sam_mask_selection`、`sam_mask_selection_index`、`sam_mask_subject_source`，pass 行里记 `sam_mask_recipe`，下一枪能直接看出这一遍跟的是哪一边。
- 开关 `H3_CHARACTER_SWAP_SAM_MASK_AUTOSELECT=off` **一个键同时退回**旧文本与旧选择器；已进 `DESIGN_ENV_RENDER_KNOBS`，`design_ai.env` 尾部有整段实测数字与退回写法。

**明确没修、也没拿 Preview 去赌的**：`leftmost` 追踪在片内退化（首帧 0.5244 → 全片平均 0.1274，且 `H3RelayRecoverMasks` 为补空帧逐帧重探，花掉 279 秒 vs rightmost 的 46 秒）。这条要有逐帧复检的办法才算干净，先记在 env 与这里。

**验证。** 新套件 `testing/test_round114_sam_mask_role_selection.py` 18 项全绿（名词合成去重/上限、左右判定、同侧与垃圾框回 `largest`、`=off` 一个键回旧图、真 WITHMASK 图里 `CLIPTextEncode.text == "person, gundam, godzilla"` 且选择器为 `rightmost`、普通调用仍是 `person`+`largest`、非法选择器不落进图、纯模板逐字节不动、引擎不再硬写 largest、Studio 把框与名词传下去且新开关是 render knob）；回归 `test_round112_in_graph_sam_mask` 22、`test_smart_render_worker` 48、`test_round113_gpu_claim_lease` 12 全绿；`character_swap_engine.py` / `director_cut_studio.py` `py_compile` 通过。

顺手清掉一条 **Round 111** 留下的过期断言：`test_character_swap_closeup_gates::test_hair_band_radius_shrinks_on_a_thin_crown` 还在要字面 `boxblur=18:2`，而那一轮已经把脸部那条带改成跟裁块收缩（`head_limit = int(min(w, h/2)) // 2 - 1`；120 px 的样板片上上限就是 6）。现在它断言 `boxblur=4:2` 与 `boxblur=6:2` 都在、而 18 **必须不在**（放不下，ffmpeg 会整条拒掉、那一 pass 就整块失去身份擦除），79 项全绿——比原先更严。

**要导演做的**：完全退出 Studio 再重开（名词与框都读自 Studio 进程）。之后第一枪的 manifest 里应当看到 `sam_mask_subject = "person, gundam, godzilla"` 与 `sam_mask_selection = leftmost/rightmost` 两边不同——这是他真正要的那根沟边的前提。

### 22:50 这一轮修的是「谁在占卡」—— Qwen 与 ComfyUI 的交接班 —— Round 113（2026-11-10 晚）

**现场。** 导演 18:33 升级了 `h3_status_tray.ps1`、18:35 升级了 `staged_model_driver.py`，要求按他这两条 reload / unload 交互来修 App 这边。

**先把两边的契约读准，不猜。** 托盘 `Test-ComfyClaimActive` 现在认的是**活性**而不是年龄：claim 的 `ts` 距今 <120 秒、或 ComfyUI 队列确实有活、或 `active_run.json` 报 running 且 <900 秒，否则 `Release-StaleComfyClaim` 当场删文件、按「GPU 空闲 + 队列空闲 ~20 s」把 Qwen 装回来（重载实测 45-57 秒）。driver 侧 `COMFY_CLAIM_TTL_SECONDS` 也从 5400 降到 900，注释里记着那次停放：unload 12:42:47 → reload 14:13:03。

**Studio 这一路从来没履行续租义务。** Studio 只在预生成前写一次 claim（`director_cut_studio.py:20501`），`active_run.json` 更只有 staged driver 会写。于是一枪里凡是队列暂时没活的时段——两遍之间上传 P 图、SAM3.1 aux、ffmpeg 合成——claim 过 120 秒就不算数，Qwen 被装回正在用的显存。托盘日志正是这个形状：19:35:07 `QWEN→FREE`、19:36:17 `FREE→QWEN`，21:32 / 21:37 / 21:39 / 22:09 都是 40-70 秒一对。对照组也存在：01:56 那一枪 `01:30:08 → 01:56:41` 全程没有 owner 变化，因为那 26 分钟队列一直有活——空洞只出现在「没在提交」的时段。

**托盘读卡还有两处把「不知道」当「空闲」。** 实测这台机器 `http://127.0.0.1:47831`：`/api/v1/models` → **404**、`/api/models` → 200、`/v1/models` → 200，即 Strata 方言；而 `Test-StrataHost` 的探测只有 4 秒超时，两条都超时就把缓存留空、下一次调用改走 LM Studio 分支去查那个**必定 404** 的地址，`Get-QwenLoadedInstances` 于是返回 `$null`。第 973 行 `$ownerKey = if ($null -ne $qwenInstances -and ...)` 把 `$null` 折成 **FREE**：既写了一行假的 owner 变更，又让 20 秒自动加载定时器开始倒数——这就是渲染中途多出一坨 ~20 GB Qwen 的路径；第 1102 行 `(Get-QwenLoadedInstances).Count -gt 0` 同样把 `$null` 当 0。顺带记录：`qwen_model=iq3_s` 而 `qwen_key_filter=qwen3`，实测 Strata 实例是 `id=iq3_s` / `label=Qwen3.8-Flash-Next IQ3_S`，filter 靠的是 **label** 而不是 id。

**改了什么。**
- 托盘：方言一旦证明就锁住（只有 Settings 保存 / 重启会重置，那两行本来就在），未证明时最多 30 秒重探一次并沿用上次证明的方言，探测超时 4 → 8 秒，两边都探测失败时写一行 `host dialect undecided: holding …`（120 秒节流）。`Get-QwenLoadedInstances` 返回 `$null` 一律算 UNKNOWN：`Notify-OwnerChange` 不为 UNKNOWN 写日志也不弹通知，owner 沿用上一次的确认值；自动加载闸门里 UNKNOWN 走「不算空闲」那一支（反向卸载本来就要求 `$ownerKey -eq "QWEN"`，不会误卸）。ComfyUI 不可达的 catch 分支同样不再把 `$null` 折成 FREE。
- driver：新增租约原语 `touch_comfy_claim` / `start_comfy_claim_lease` / `stop_comfy_claim_lease` / `claim_lease_state` / `comfy_claim_heartbeat_seconds`。默认 45 秒续租，硬上限 110 秒（必须小于 120 秒宽限），`H3_COMFY_CLAIM_HEARTBEAT_SECONDS=0` 恢复「只写一次」的旧行为。心跳会**重新武装**被托盘判陈旧删掉的 claim——占着卡的进程才是 GPU 归属的证人；进程一死就不续租，120 秒后自动失效，不会再出现 90 分钟停放。
- worker：`smart_render_worker.main()` 在 H3 阶段起点起租（note `worker-gpu-phase`），交还 GPU 时**先停租再 clear**（活着的心跳会把刚删掉的文件写回来，那样 Qwen 就再也回不来）；`comfy_submit_worker.py` 在等待 history 期间同样起租 / 停租。
- manifest 多一行 `gpu_claim_lease`：谁占着卡、续租间隔与次数、释放前 `at_release` 的 note 和年龄、clear 之后是否真的 `none`——下一枪能用 App 自己的数字证明卡是谁的。
- 旋钮 `H3_COMFY_CLAIM_HEARTBEAT_SECONDS` 进 `DESIGN_ENV_RENDER_KNOBS`，`design_ai.env` 尾部写了整段交接班说明与一行退回。

**这一轮不改 `render_policy_version`**：像素配方一个字没动，新行为由 manifest 里的 `gpu_claim_lease` 自证。策略 108 的图、提示词、mask 配方、`/free` 之后才交卡的顺序，以及全部既有守卫都没动。

**顺带量到、留给画面那一半的事实**（都是免费探针，没有扩散）：01:56 那枪的图内 SAM3 在 frame 84 只给出**一个** object，遮罩只盖住左边那位（IoU_R1 0.5238 / R1 被盖 0.5244，IoU_R2 0.0000）——两个 pass 共用同一根遮罩，所以 R2 那枪把哥斯拉画到了左边，右边该换的没被遮；换 selection / 阈值 / refine / 措辞、甚至把 App 自己的角色框喂进 `SAM3_Detect.bboxes` 都**没有第二个 object**，`selection=index 1` 直接执行报错；喂 raw 原始片与喂 plate 结果逐位相同（覆盖 0.2150 vs 0.2150），所以「plate 被擦糊」这个假设被证伪。`SAM3_Detect.positive_coords` 的 tooltip 给了正确格式：JSON `[{"x": int, "y": int}, ...]`（像素）——之前 12 次提交全错是因为我给的是 `"x,y"` 字符串。

**验证。** 新套件 `testing/test_round113_gpu_claim_lease.py` 12 项全绿（含「心跳必须重新武装被删的 claim」「停租后不得再写 ts」「续租间隔必须 <120 秒」「先停租再 clear」的源码顺序检查、「托盘必须沿用上次证明的方言」、UNKNOWN 不成 owner 这两条源码断言）；回归 `test_staged_model_driver` 27、`test_comfy_connection_recovery` 8、`test_round112_in_graph_sam_mask` 22、`test_smart_render_worker` 48 全绿；`staged_model_driver` / `smart_render_worker` / `comfy_submit_worker` / `director_cut_studio` 四个文件 `py_compile` 通过；`h3_status_tray.ps1` 经 `[System.Management.Automation.Language.Parser]::ParseFile` 解析 0 语法错误。

**要导演做的一件事**：PowerShell 把脚本正文读进内存就不再更新（脚本自己 335-339 行就在提醒），所以托盘那半边必须**重启托盘**才生效；worker / Studio 那半边必须**完全退出 Studio 再重开**。之后跑一枪 Preview，对着 manifest 的 `gpu_claim_lease` 和托盘日志的 owner 行看是否不再翻转。

### 01:10 这一轮不再在外面补边，把 SAM3 的遮罩交回给模型 —— Round 112 / policy 108（2026-11-10 凌晨）

**现场。** 导演跑了 23:14 那一枪（policy 107）之后话说得很重：完全没看到真正的 sam3 沟边，而且浪费太多资源重复生成没用的视频。他直接给了四条规矩：测试档案不要放主目录；失败的东西推倒重来，参照已经成功的 Director_Blueprint_Character_Remake_-_Hallway_Approach 和 godzilla_action_figure_by_neca_4；我要的做法别改（各角色分别生成 → SAM3 沟边 → 合成）；H3-Character-Swap-Relay 一次就能换完角色，没必要抽卡三次。收尾时他又补了一句：以我新存的 `H3-Character-Swap-Relay-V2-API-WITHMASK.json` 为准。

**先把「已经成功」量出来，不谈感觉。** 两个认可项目和 neca_6 的 manifest 加 resource_calibration 摆在一起：

| | Hallway（policy 96） | neca_4（97，认可） | neca_6（107，被否） |
|---|---|---|---|
| attempts_used / maximum_attempts | 1 / 1 | 1 / 1（attempt_table 空、action "accept"） | **2 / 2**（attempt_table n=2，两个 prompt_id） |
| character_swap_composite | `{}` | `{}` | **sam31_v1_plus_role_output_instance_masks_v3** |
| plate | 2 条带、wardrobe off、0.2043 | 2 条带、wardrobe off、0.4947 | **3 条带、wardrobe blur_desat、0.5642** |
| 提示词 | — | 4051 字符、append_chars 1156 ≤ 1200 | 4439 字符、append_chars 1544 **超预算**（append_over_budget true） |
| gpu_seconds_per_output_second | 45.5 | **37.8** | **139.8（3.7 倍）** |

neca_6 那一枪 R1 自己的审计理由是 "replacement is only a head/face layer; the V1 wardrobe still fills
the upper half"（wardrobe_shift −0.05753、head_layer_only true）——重 plate + 超预算提示词换来的正是「只换了一层头」。
另外那份 23:14 的 manifest 里，两卷的 `target_shape_*` 全是空串、`target_shape_samples 0`：**Round 111 的尺子在那一枪
压根没量到东西**，选卷逻辑等于没跑（job JSON 没留下，无法再往下追因；最可能是 Studio 进程还握着改动前的 env）。

**断线到底断在哪。** 节点包官方 swap 配方是 SAM3_Detect(0.35) → H3RelaySelectMask(largest) →
SAM3_VideoTrack(0.50, max_objects 1) → SAM3_TrackToMask → H3RelayRecoverMasks → H3RelayExpandMask(64px) →
H3RelayWindowInputs.mask → H3RelayApplyEditMask（把遮罩写成 `{"noise_mask": [video_mask, ones]}`），擦与画发生在
同一次扩散里。Round 98–111 没走这条路，只能在外面用 ffmpeg 的 boxblur 带 + alphamerge 贴边——那就是「没看到真正的
sam3 沟边」。仓库里那张 11-01 的 `H3-Character-Swap-Relay-V2-api-mask.json` 整条链都在、46 个类在你那台 ComfyUI 上
全有，可是 `H3RelayWindowInputs.mask` 空着：它的 `edit_mask.mask` 虽连着 `window.1`，源头永远是空，而
`H3RelayApplyEditMask.mask` 是 required，所以要到执行时才炸——从没出过画面，CHANGELOG 里也就没有它一行。

**你新存的那张图才是关键。** `H3-Character-Swap-Relay-V2-API-WITHMASK.json` 实测：46 节点、你那台机器 0 缺类、
0 个必填输入缺口，`window.mask ← expand_mask.0` 你自己已经接好。跟正在跑的图逐节点比，只多了 11 个遮罩节点，
只把 guide / sample / sampling_memory 的 latent 改走 edit_mask；底模 `minimax_h3_ref2va_int8_convrot`、
Turbo `minimax_h3_turbo_v4_step600_ema`(1.0)、swap LoRA `h3_character_swap_v1.5`(1.5)、两个 VAE、采样器、
P 图进参考槽的路径**一个字都没动**。（对照：旧 mask 图底模换成 `Minimax-h3_Singularity_x_10Eros-Max_PRISM_int8`、
turbo 换文件且 strength 0.8、P 图前多挂一层 2× RTX —— 要是直接切过去，等于一次偷改四个变量。）

**改了什么。**
1. 提交图默认换成 WITHMASK 这张。引擎只做核对与「缺才补」的接线，**不改写你画的图**；模型侧差异原样写进 manifest
   的 `model_identity_drift`（今晚实测 `[]`：这张图与正在跑的图在模型侧零漂移）。遮罩参数默认就是包里的
   0.35 / 0.50 / 64 px / max_objects 1，都能用 env 调；`sam_mask_link_source` 会写明这根线是「导演自己图里已接好」
   还是「引擎按包配方补接」。模板名找不到时会先按大小写不敏感再找一遍（这张磁盘上那张朴素图的真名其实是
    H3-Character-Swap-Relay-V2-API.json，引擎常量写的是小写 api），实在没有才退回 plain——省掉一次
    「静默换图」白烧的 Preview。
2. 不抽卡：`H3_CHARACTER_SWAP_NONHUMAN_MAX_ATTEMPTS=1`，对齐 neca_4 的 attempts_used 1 / maximum_attempts 1。
3. plate 与提示词形状退回认可那一枪：`H3_CHARACTER_SWAP_NONHUMAN_TARGET=off`（2 条带、wardrobe 不擦、
   figure 宽度 1.0 / 面积 0.56、不加那句 388 字符 cast lock）。合成器要追踪的名词是从每个 pass 的目标识别自己拼的
   （`sam31_text_prompt` 仍是 "person, gundam, godzilla"），不吃这个开关，所以关掉它不会让合成瞎掉。
4. 提示词仍取自 `H3-Character-Swap-Relay-V2-api.json` 里你手写的那段（新常量 `CHARACTER_SWAP_PROMPT_SOURCE_NAME`
   把来源钉住，测试盯着它），没跟着模板一起换——认可那一枪的 4051 字符就在里面。
5. policy 107 → 108：107 之前缓存的每一枪都是用「没有 edit mask 的图」编译的，按定义就该作废，不是 judgement call。

**不能保证的事。**「两个角色一次换完」这轮没做，也不建议赌：包里 `max_objects` 全钉 1、`ref_images.ref_image_0`
只有一个、文档没有双人同批的说法；neca_6 是 R1→P2、R2→P1 两个不同身份，按 SKILL.md 第 15 行仍要各自生成再合成。
这一轮真正改掉的是三件事：遮罩进了模型、卷数回到一卷、plate 回到认可形状。Round 104–111 那套 plate / 边缘 /
形状的机制都还在，只是这次不参与压画面。

**怎么退回（一行一条）。** `H3_CHARACTER_SWAP_WORKFLOW_NAME=plain`；`H3_CHARACTER_SWAP_SAM_MASK_SUBJECT` /
`_DETECT_THRESHOLD` / `_TRACK_THRESHOLD` / `_EXPANSION_PX`；`H3_CHARACTER_SWAP_NONHUMAN_MAX_ATTEMPTS=2`；
`H3_CHARACTER_SWAP_NONHUMAN_TARGET=on`。改完 env 必须**完全退出 Studio 再重开**——选哪张图、怎么拼提示词都发生在
Studio 进程里，Round 111 那套 worker 自愈救不了 Studio 自己那份。

**验证。** 全套 16 套件 **405 个测试、403 绿**。新增 `testing/test_round112_in_graph_sam_mask.py` 21 条：文件名拼写
（打错会静默退回无遮罩图）、按你那台服务器的 schema 0 缺口、你自己接好的线不被覆盖、与正在跑的图模型侧零漂移、
旧 mask 图必须报出漂移（证明这个审计不是摆设）、plain 图逐字节不变、遮罩参数默认值与 junk 回退、design_ai.env 里
没有偷偷激活的模板行、认可配方三项已生效、提示词来源仍是旧图。
剩 2 个红是旧账：`test_round50_qc_relaxations` 要求模板里有参考图放大节点，而正在跑的 `H3-Character-Swap-Relay-V2-api.json`
里放大类出现 0 次，认可那枪和被否那枪的 manifest 也都是 `reference_upscale_node_id: ""`——那是 11-04 模板重存时掉的，
不是这一轮碰的（WITHMASK 那张同样没有，所以两边一致）。测试档案已全部搬进 `testing/`
（`_dsh_verify_13`、`_sheet/111`、`root_stray_20261109`），主目录干净。

**待验收。** 只能靠 Preview 判定的三件事：SAM3 遮罩进图之后边缘是不是真干净、plate 回薄之后 V1 的衣服会不会又透出来、
一卷不抽卡够不够。建议还是拍 neca_6 那个 13.975 秒镜头——一枪同时回答三个问题，而且这次按 neca_4 的形状跑，
成本本该回到 37–45 GPU 秒/输出秒那一档，而不是 139.8。

### 20:33 那枪：选卷器整轮没跑，而四卷实测说"就算跑了画面也不会变" —— Round 111 / policy 107（2026-11-09 深夜）

**现场，全部来自 manifest、ComfyUI history 和在导演机器上重放的 SAM 追踪（本轮没有花一次 Preview）。** 20:33 是 neca_6 的第 10 次生成，manifest 显示 `smart_render_policy_version: 106`、合成完全忠实（`mode sam31_v1_plus_role_output_instance_masks_v3`、`fallback_reason ""`、预检 R1→object1 0.9221 / R2→object0 0.8065、take 侧 R1 0.8298、coverage 1.0），但**轮廓列全是空的、`selected_attempt: 1`、没有任何一行解释为什么没量**。成片看起来还是不行，所以先从 ComfyUI 把四卷原片取回来（334 帧、928×512，各 4.4–5.7 MB），再用**产品自己的** `measure_character_swap_attempt_target_shapes` 一卷一卷量（58 个采样/卷）：

- **R1（高达）**：留下的第一卷 p10 **0.2684**、跑形秒占 **19.0 %**、中位 0.7609；被扔的第二卷 p10 **0.3080**、跑形 **41.4 %**、中位 0.5817。第一卷的跑形秒是 0–0.25 / 8–8.25 / 12.25–14.5 s（进出画各半秒），第二卷是 2.75–4.25 / 4.75–6.5 / 8–10.5 s（**整段中段**）。画面上第一卷到 4.5 s 还是高达、6.5 s 起原人的脸被画回来、8.5 s 之后完全没有高达；第二卷 4.5 s 就只剩原人的脸。**Round 110 的"p10 先决"会翻到第二卷，也就是挑更差的那个。**
- **R2（哥斯拉）**：留下的第一卷 p10 **0.5528**、跑形 **6.9 %**（这条尺子的合格线是 p10≥0.40 且跑形≤25 %，**它是四卷里唯一合格的**）；被扔的第二卷 p10 0.1852、跑形 **84.5 %**。所以 R2 这一枪不管跑不跑选卷器都留第一卷，而成片里哥斯拉从 0 s 带到 13.5 s ✓。
- 结论：**20:33 看得过去/过不去，跟选卷没关系**——选卷器真跑了，R2 不变，R1 只会更糟。

**为什么没跑（根因，用代码证明，不是猜）。** `apply_design_ai_env_render_knobs()` 只在 `name not in os.environ` 时装旋钮，而且**只在 import 时跑一次**；Studio 是拿 `env={**os.environ, ...}` 生 worker 的（director_cut_studio 的 Popen，env 参数在 :3305 附近）。Studio 进程比这次 env 编辑更早开着 ⇒ 它自己的环境还是 `first` ⇒ 子进程**代码是 106、环境是旧的**，于是选卷分支根本没进去（既没有进度行，也只有 `selected_attempt: 1`）。manifest 里 `target_shape_*` 全空就是这个样子。

**顺手量到的第二个事实（这次没动它，但它是 R1 的病根）。** 20:33 的 R1 plate 哈希 `identity_suppressed_0b6863083c3d70478eff` **与 18:51 那枪逐字节相同**——plate 是缓存复用的，所以这个毛病会一路跟着每一枪。在角色自己的 V1 遮罩里，R1 plate 有 **25.83 %** 与 V1 逐字节相同（≥0.35 的秒：3.75 / 4.00 / 4.25 / 4.50 / 4.75 / 5.25 / 6.25 / 12.25 s，**正好是 take 把原人画回来的那几秒**，最差窗口 36.01 %）。按最差窗口的位置图：**78.2 % 的残留本来就在带内**，带外的 21.8 % 里 95.5 % 仍在角色框内；把带扩到追踪器逐帧报的包络要 **0.6629** 面积（上限 0.62）却只多盖 20.9 % 的残留——**剩的是强度，不是位置**。本地按同一把尺子重放带矩形：boxblur 18 留 0.1250、30 留 0.0985、45 留 0.0681、整块填平灰**只能到 0.0524**（天花板是带从没盖到的那部分轮廓，不是模糊不够）。那张脸以前**没有旋钮**：crown 有 `H3_CHARACTER_SWAP_HAIR_BLUR_RADIUS`、衣服有 `WARDROBE_BLUR_RADIUS`，只有脸在 director_cut_studio 写死 `boxblur=18:2`。

**改了什么（4 条）。**
1. **选卷先比"跑形秒占比"，p10 只在占比打平时用**；两个都不合格时，后来者必须比第一卷**明显好 5 个百分点**（`CHARACTER_SWAP_NONHUMAN_SHAPE_FLIP_MARGIN = 0.05`）才换卷。20:33 两卷差 22.4 个百分点、18:51 两卷差 37.9 个百分点，都远大于 5；同一卷重测量只差 1–2 个百分点，所以 5 是安全的。
2. **worker 会自愈**：job 现在带上"Studio 读过的那份 env 文件的 sha256 + 它当时装了哪几对"；worker 发现文件指纹变了，就**只刷它那几对**（启动器里手动设过的值一律不动），并在进度条上用中文说刷了哪几对；文件读不到就沿用继承的环境，**绝不因此判死 Shot**。
3. **脸的模糊第一次可调**：`H3_CHARACTER_SWAP_HEAD_BLUR_RADIUS`（默认 18，就是原来写死的值，会按 ffmpeg boxblur 的半平面合法性自动封顶）与 `H3_CHARACTER_SWAP_HEAD_EXTRA_SIGMA`（默认 0），两个都进了 `DESIGN_ENV_RENDER_KNOBS`；**plate 的缓存指纹现在包含脸的半径**（否则改了半径会被旧 plate 骗过去，就是本轮刚修过的那个坑）。design_ai.env 里两行**只注释、不启用**，不填就等于本轮之前。
4. **诊断不再哑巴**：测量失败时 `target_shape_status` 从 `error:RuntimeError` 变成 `error:RuntimeError: <前 160 字消息>`（本轮就是靠消息才发现探针把 /prompt 拼成 /prompt/prompt、以及 `KeyError: 'segment_count'`）；一段重打出多卷时，进度条**一定**说明为什么没按轮廓选卷（"这一段没有非人目标…"或"选卷模式是 first…没有按轮廓选卷"）。

**不能保证的事。** 本轮**没有**跑任何生成，所以 R1 掉高达这件事仍未经过新一枪验证；四卷的实测只证明"选卷不是 20:33 的原因"。真正该动的是 plate 把脸压住的程度，而强度这条路的天花板只到 0.0524——**本轮刻意没填 30/4**，因为一次 Preview 只该压一个变量，导演想试就在 design_ai.env 填那两行（会重建 plate，那是 relay 的时间，不是 Preview）。

**怎么退回。** `H3_CHARACTER_SWAP_NONHUMAN_RANKING=first`（Round 108 的行为）或 `=audit`（人工排法）；`H3_CHARACTER_SWAP_HEAD_BLUR_RADIUS=18`、`H3_CHARACTER_SWAP_HEAD_EXTRA_SIGMA=0` 就是本轮之前（也是现在的默认）；`H3_CHARACTER_SWAP_SAM31_TARGET_SHAPE=off` 会让选卷器整个不进分支（顺带也不再记账，别填）；`…NONHUMAN_MAX_ATTEMPTS=1` 完全不重打；`…EDGE_MODE=classic`、`…SAM31_AUTO_BOX_MAX_WIDTH_NONHUMAN=0.60` 分别退回 Round 107 / 109。

**给导演的规矩。** 改完 design_ai.env 仍然要**完全退出 Studio 再重开**——worker 这一侧现在会自愈，但 Studio 自己的界面逻辑还是 import 时读的那一份。下一枪的看点不是选卷，而是 **R1 从 5 s 起还在不在高达**；如果不在，下一步就该把 plate 的糊强度填上（先只填 `HEAD_BLUR_RADIUS=30`，sigma 留着）。

**验证。** 13 个套件、**343 个测试全绿**（新增 `test_round111_roll_ranking_and_env` 22 个：20:33 两卷留第一卷、18:51 两卷仍翻第二卷、5 点余量的两侧、合格卷优先、指纹相同不动、指纹不同只刷安装过的对、启动器覆盖不动、文件读不到不动、中文播报、**Studio 三处写 job 都必须盖章**（源码级守卫——本轮就差点只盖了 cleanup 那一处、漏了真正跑渲染的两处）、plate 旋钮默认=写死值/垃圾值回退/不启用、Studio 指纹与 job 盖章；另加真文件实测：Studio 从 design_ai.env 装了 **23 对**旋钮、指纹 `ccfa3ded…`，文件不动时刷新返回空，文件被改后**只**刷它装过的 `NONHUMAN_RANKING`，没装过的 `HEAD_BLUR_RADIUS=30` 一律不动）；round110 24、round109 18、round108 18、round107 14、round106 16、round105 10+23、round104 13、round103 19、round102 16、smart_render_worker 48、round69 102，全部逐文件跑过）。四卷原片与 plate、V1 遮罩都已落到 `_dsh_verify_13\godzilla\comfyui_files_111`，逐卷轮廓数字在 `shape_111`，两张图：`._sheet\111\rolls_2033.png`（成片 + 四卷 + R2 主遮罩 + 两张目标剪影）、`._sheet\111\plate_residual_map_R1.png`（V1 / 擦过 / 残留红块，3.75–4.25 s）。

**待验收。** 下一枪 Preview 之前请**完全退出并重开 Studio**（本轮改了 policy 到 107，缓存 Segment 会重新校验一次）。


### 18:51 那枪：合成终于忠实了，坏在"两卷里留了错的那一卷" —— Round 110 / policy 106（2026-11-09 晚上）

**现场，全部来自 manifest 与 ComfyUI 自己的 history。** 18:51 这一枪 Round 109 的修法真的生效了：`character_swap_composite.mode = sam31_v1_plus_role_output_instance_masks_v3`，`fallback_reason` 空，`sam31_prompt_ids` 三条（R1 遮罩、R2 遮罩、V1 预检），R1 匹配 0.8276 / 覆盖 1.000，R2 匹配 0.8332 / 覆盖 0.966，manifest 里也写了 `sam31_auto_box_max_width_nonhuman: 0.85`。**成片现在等于 take 本身**——所以剩下的毛病不在遮罩，在生成出来的那一卷。把九层东西摊在同一张图上（`._sheet/110/layers_1851.png`：成片 / R1 take / R2 第一卷 / R2 第二卷 / 两份擦除过的 plate / 未擦除的 plate / R2 主遮罩 / R2 碎片遮罩，列是 0.5–12.5 s，最右两张是目标 P 图）：
- **R1 那一卷从 ~4 s 起就把高达弄丢了**（4.5 s 只剩一张原人脸，6.5 s 是两个原人）；成片只是照搬。
- **R2 第一卷在 8.5–10.5 s 把哥斯拉弄丢了，第二卷从 0 s 带到 12.5 s**——可 manifest 写着 `selected_attempt: 1`。
- R2 主遮罩在 8.5–10.5 s 抓的其实是原人的头（哥斯拉不在那一卷里，SAM 只能抓最大的那团），所以成片那两秒显示原人，完全自洽。

**死因是把人类的尺子用在怪兽身上。** 审计给 R2 第一卷 `target_likeness_score` 0.6292、第二卷 0.3577（Round 108 已经证明这个数在机甲/怪兽上是反的）；`target_reference_similarity` 两卷是 0.429023 对 0.429596，在 Round 108 量出的噪声里就是平手。Round 108 因此把默认设成"留第一卷"，而这次"第一卷"恰好是差的那一卷：**first 也是猜，猜错了。**

**这次用导演自己的 ComfyUI 把它量出来了，不是拍脑袋。** 第二卷从来没跑过遮罩（只有被选中那一卷才会跑），所以把 18:50 那张 mask 图原样重放在第二卷上：先 `/upload/image` 把第二卷放进服务器 input 根目录（`LoadVideo` 只认那里的名字，带子目录的路径会被判 "Invalid video file"），再改四个 `SaveVideo` 前缀 → 队列跑完 **88 秒**，只多一个 `h3dsh110_try2_*` 输出目录，**没有新生成一帧**。然后拿 Round 108 那把尺子（take 自己的 SAM 遮罩、按自身框归一化、和目标 P 图剪影逐秒 IoU；规则 p10 ≥ 0.40 且跑形秒数占比 ≤ 0.25）量：
- 第一卷：主槽 object00 中位 0.5774 / p10 **0.3143** / **43.1 %** 跑形；合成侧实际的配对（00+02）0.5443 / 0.3714 / **51.7 %** → **不合格**。
- 第二卷：object00 0.6305 / **0.5775** / **5.2 %** 合格；object01 0.7011 / 0.6777 / 0 % 合格；全槽合并 0.6337 / 0.6096 / 0 % 合格 → **被扔掉的那一卷才是过规则的**。
- 顺手钉住一条坑：第一卷有个只覆盖 20/58 秒的碎片槽 p10 0.5807，单看它第一卷就"及格"了。**样本不足最长卷一半的槽不算数**（`CHARACTER_SWAP_NONHUMAN_SHAPE_MIN_SAMPLE_SHARE=0.5`）。

**改了什么。** 非人角色的选卷从"猜第一卷"改成"量出来留哪一卷"：只要这一卷真的重打过，就给每一卷都跑一次遮罩（实测 ~90 秒/卷），留下轮廓最像目标 P 图的那一卷；任何一卷量不出来就保留第一卷，**绝不退回那把人类尺子**；只有一卷时一分钱都不多花。`H3_CHARACTER_SWAP_NONHUMAN_RANKING` 现在是 `shape`（默认），`first` / `audit` 都留着。manifest 多记：attempt_table 每卷的 `target_shape_iou_p10` / `target_shape_weak_share` / `target_shape_samples` / `target_shape_status` / `target_shape_prompt_id`，segment 层 `identity_shape_measurements`；Studio 进度会显示"Character Swap 2 卷：先追踪每一卷的轮廓，再按与目标图的相似程度选卷"。

**顺带量出来、写下来免得下次再猜的（plate）。** 把比较范围限制在 V1 追踪器给的**源角色自己轮廓**里：擦除之后仍有 **R1 中位 25.7 %** 的像素一比特都没动（最差 3.75–6.25 s 达 35–41 %，正是 take 反水的那几秒）、**R2 中位 39.6 %**（最差 10.5–11.75 s 达 59–63 %，正是第一卷丢哥斯拉的地方）。而 R1 的 plate 已经糊掉了 57.7 % 的画面——**瓶颈不是面积上限，是糊的位置**，所以这一枪没有去调 `NONHUMAN_FIGURE_MAX_AREA` 之类赌一把。也没有在 worker 里加"顺手记一下"的指标：worker 手上只有擦**之前**的 relay（`identity_audit.source_video_path`），擦过的那份 plate 只存在于 ComfyUI 输出里，硬记只会每次都写 `missing_inputs`。测量脚本：`_dsh_verify_13/godzilla/measure_plate_residual_body_110.py`（先按 V1 遮罩与角色框的重叠自动配对 object↔R，这一步曾因为 `&` 与 `>=` 的优先级把两个角色配到同一块遮罩上）。

**诚实写下不能保证的。** `shape` 只决定"留哪一卷"，它不会让模型把高达画满 14 秒——那是 plate 与提示词的事；第二卷被选中之后成片是不是更好，只能下一枪再看；这把尺子只在 11:50（0.6393 / 0.4623 / 20.7 %）与 14:24（0.5695 / 0.3691 / 29.3 %）两枪上和导演的眼睛对过一次，样本就是这几枪；遮罩槽"哪个算角色"仍靠 Round 102–107 那一套关联，我没有改它。

**怎么退回。** `design_ai.env` 里 `H3_CHARACTER_SWAP_NONHUMAN_RANKING=first` 回到 Round 108 的"留第一卷"，填 `audit` 回到按审计分数挑。改动涉及源码与环境变量：**Studio 要完全退出再打开**才生效。

**给导演的规矩（Round 110）**：这一枪之后，判断"留了哪一卷"只看两处——attempt_table 每卷的 `target_shape_iou_p10` 与 `target_shape_weak_share`（p10 ≥ 0.40 且跑形 ≤ 25 % 是及格线），不要再听 `target_likeness_score`。若您不想为非人角色多花那 ~90 秒/卷，就填 `first`，但那等于承认"两卷都一样"。这次为了量第二卷，我在您那台 ComfyUI 上排了一个遮罩任务（当时队列是空的）；如果您不希望我再用它跑东西，请说一声，我就只能停在"量不出来"。

**验证。** 298 项测试按文件逐个跑绿：round110 新增 24（默认就是 shape、18:51 两卷的数字必须翻到第二卷、及格卷赢过 p10 更高但跑形的卷、碎片槽不算数、全都没量出来就留第一卷、audit 仍走人类尺子、真人镜头不受影响、追踪失败只记 `error:类型` 不炸 Segment、单卷不花任何任务、真人 pass 不发任务、attempt_table 记 shape 且"没量到"记 None 不是 0、TARGET_SHAPE 那个旋钮不能是 off，否则选卷会静默退回第一卷）+ round108 18（两处默认值按 Round 110 改写）+ round109 18 + round107 14 + round106 16 + round105 10 + round104 13 + round103 19 + round102 16 + smart_render_worker 48 + round69 102。两个模块 policy 106（`_dsh_verify_13/godzilla/bump_round110_policy_pins.py` 只碰含 `POLICY_VERSION` 的行，共 14 行）。

**待验收。** 下一枪 Preview（neca_6 第 10 枪）：看 manifest 里 R2 有没有 `identity_shape_measurements` 两行、被选中的是不是 p10 高的那一卷，再看成片是不是把哥斯拉从头带到尾。

### 16:52 那枪"完全错误"：不是模型画坏了，是我们自己把 SAM 路关掉了 —— Round 109 / policy 105（2026-11-09 傍晚）

**现场**：16:52 那一枪（policy 104，成片 `generated_preview.mp4` 2 160 686 B）导演的话是"完全错误"。先说好消息：**Round 108 装的两条都真的生效了**——manifest 里 `attempts_used: 2`（非人目标多打了一卷）、`selected_attempt: 1`（保留第一卷，不再让真人像度量去挑）。这一枪的 prompt 预算也和被认可的 11:50 逐字节同级：`prompt_chars` 4439、`append_chars` 1544 / `append_budget` 1200、`route: vanilla`、`megapixels` 0.5。

**死因是一条算术，不是判断**。composite 行的 `mode` 是 `sam31_v1_plus_role_output_masks_v3_fallback_delta`，`sam31_prompt_ids: []`、`sam31_role_matches: []`——**这一枪根本没用到 SAM 遮罩**。V1 侧预检本来是 trusted（R1 0.9221 / R2 0.8065）；拒绝发生在 take 侧关联：`R2 0.69 sat below 0.70`，而修框梯子的拒绝理由写着 `R2 auto-box: no candidate box fitted the size band [0.02, 0.85] within width 0.60`。用本轮从 ComfyUI 取回的该枪遮罩文件量：R2 中标槽的外接框宽 **0.7021**（按 4 fps 量是 **0.7188**），而修框梯子最紧的一档**就是这个外接框本身**——上限 0.60 之下每一档都非法，**梯子必然为空，分数必然停在 0.69**（`_dsh_verify_13/godzilla/measure_run_109_width_cap.py`）。项目自己给 R2 画的锚框宽 0.6757、身份审计的 `figure_extent.max_width` 是 0.8：三处都容得下 0.6757/0.80，只有这一道 0.60 把它们全否决了。

**画面证据**（`._sheet/109/fallback_vs_takes_1652.png`：成片 / 两卷 take / plate / 两张 P 图）：take 本身基本成立——R1 除 4 s 外都是高达，R2 在 4–7 s 回退成戴眼镜的原人（与 11:50 那枪同类局部回退）。灾难出在 fallback：差值合成拿"take 与 plate 的像素差"当遮罩、只在角色 ROI 里贴 take，而这一枪 take 把整幅都重画了，差几乎铺满 ROI，于是**没擦干净的原人 + 怪兽 + 高达同时出现在一张画上**（10 s / 13 s 最明显）。这就是"完全错误"。

**Round 108 那把尺子给这一枪的 take 打分（同 targets、同函数）**：

| 该枪某槽 | 中位 IoU | p10 | IoU<0.55 秒占比 | 判定 |
| --- | --- | --- | --- | --- |
| R1 object01 | 0.7061 | 0.6537 | **5.4 %** | 过 |
| R2 object00 | 0.6089 | 0.5702 | **10.3 %** | 过 |
| R1 四槽并集 | 0.6666 | 0.2919 | 46.6 % | 弱（0–3.25 s、4–7.75 s） |
| R2 四槽并集 | 0.4941 | 0.4084 | 55.2 % | 弱（0–3.5 s、10–14.5 s） |
| 参照：11:50 被认可（最差角色） | 0.6393 | 0.4623 | 20.7 % | 过 |

也就是说：**take 的形体与被认可的 11:50 同级，弱的是"把几块槽硬并成一块"这一步**（Round 106 的空壳污染在这里复发）。所以这一枪该修的是关联与降级，不是再打一卷。

**改了什么**：非人目标（pass 行 `nonhuman_target_nouns` 有 godzilla / gundam 这类名词，或缺该行时回退读 P 图识别文字）的修框宽度上限成为独立旋钮 **`H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH_NONHUMAN`，默认 0.85 = 面积上限**——含义很窄也很硬：**面积放行、宽度就不许再单独否决**。其余四道闸一条没动（同一 SAM 实例必须仍赢、领先 runner-up ≥0.05、自己也要过 0.70、锚框包含度 ≥0.60），真人镜头仍走 0.60（发丝 halo 那条理由仍然成立），逐字节不变。另外：composite 行现在同时记 `sam31_auto_box_max_width` 与 `sam31_auto_box_max_width_nonhuman`，拒绝理由会点名是哪个旋钮；**降级不再无声**——fallback 会 emit 一条 warning，composite 行加 `sam31_fallback_warning`（"没实例遮罩、差值合成、源角可能露在后面"）。

**诚实写下这条修改不能保证的东西**：离线重放该枪的关联判定（`_dsh_verify_13/godzilla/replay_run_109_association.py`，用产品自己的 `_sam_target_score`）显示，宽度抬到 0.72 后梯子进得来、分数能到 0.75，但**加宽后的框会把胜者挪到另一个 SAM 槽**（同体闸当场 `break`），而 R2 中标槽对锚框的包含度只有 0.5609（下限 0.60）——模型把哥斯拉从 x=0.306 挪到了 x=0。本轮因此**没有**放宽同体闸和包含度闸：宁可让这一枪仍走 SAM 合成（遮罩可能偏松，Round 108 的 `target_shape_*` 会把弱秒写进 pass 行给你看），也不要再吃一次双重曝光；真被拦下时 warning 会当场告诉你。

**顺带查明的两件事**：① 成功的枪会删本地中间文件，16:52 的 take 与全套 mask 只剩 ComfyUI history 里的副本，已全部取回 `_dsh_verify_13/godzilla/comfyui_files_109/`（16 个文件：plate、两卷 take、各 4 个 object 槽）。② manifest 写 `sam31_prompt_ids: []` 是**记账缺口**：take 侧的 mask 任务其实跑了（history 里 16:50:52 `f806a4fc…`、16:51:42 `dd6b7dd5…`），只是配对抛异常后 id 没落进 manifest——本轮记下，未改。

**怎么退回**：`H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH_NONHUMAN=0.60` 完全恢复本轮之前的行为（测试 `test_the_kill_switch_restores_the_pre_round_109_refusal` 钉着这条）。

**给导演的规矩（Round 109）**：这一枪的账在 manifest 里读三处就够——`character_swap_composite.mode`（有没有真的用遮罩）、`sam31_auto_box_max_width_nonhuman`（宽度给了多少）、以及被拒时 `box_auto_repair.refused` 里点名的那个旋钮。看到 warning 说"差值合成"就**不要**按角色替换的质量打分，那是降级品。若下一枪仍是 0.69 且被同体/包含度闸拦下，先别急着改分数下限：那说明模型把角色搬了家，该改的是这一枪的 R2 手画框（`source_role_bbox_overrides`）。

**验证**：新增 `testing/test_round109_nonhuman_auto_box.py` 18 项全绿（getter 的默认与钳位、0.7021 外接框在 0.60 下梯子为空 / 0.85 下第一档就是它本身、0.93 大块仍被面积闸拦、`_sam31_pass_is_non_human` 三种来源、真跑 `_sam31_repair_weak_association_boxes` 的真人/非人两种记录与拒绝文案、kill switch、policy 105、旋钮登记、design_ai.env 每项一次）。全套逐文件复跑 **274 项全绿**：round109 18、round108 18、round107 14、round106 16、smart_render_worker 48、round102 16、round103 19、round104 13、round105 10、round69 102；policy pin 共 10 处从 104 抬到 105（含 round108:319-320 这两处也会被漏掉的）。两份 Python 编译检查通过。改完必须**完全退出并 reopening Studio**（env 与 policy 都是编译期读的）。

**待验收**：需要导演跑一枪 Preview 才算这轮验收。


### 同一块 plate、同样的指令、只差 seed：这一枪的"替换失败"审计员排不出来，只有逐秒形体量得出来 —— Round 108 / policy 104（2026-11-09 下午）

**现场**：14:24 那一枪（policy 103，`attempts_used: 1`）导演的话是"角色替换失败"。把两枪的 manifest 摊平对比，**指令是逐字节相同的**：`prompt_chars` 4439 / 4441、`nonhuman_cast_lock_chars` 388 / 390、`append_chars` 1544 / 1546（`append_over_budget: true`、`dropped_tail_clauses: []`）、`author_prompt_chars` 2895、`char_budget` 12320、`route: vanilla`、`fallback_reason: ""`。合成那半边也没坏：成片 R1 与自己遮罩的贴合 0.8188、覆盖率 **1.0**（动用了一块碎片 obj1，覆盖 0.6552、5.0–14.5 s），R2 0.7542、覆盖 0.9138、空洞 `[[3.75, 5.0]]`。Round 106 的碎片机制这次真的救回了秒数。**所以问题只在生成那一卷本身。**

**审计员在这一对上是被证伪的**：`target_reference_similarity` 对被认可的 11:50 是 **0.3594 / 0.4229**，对被否决的 14:24 是 **0.3250 / 0.4675**——它把被否决的 R2（0.4675）排在被认可的 R2（0.4229）**之上**。而且两枪四个角色的 `blocking_cause` 都是 `head_layer_only`（"V1 服装还占着身体区域"，`minimum_wardrobe_shift` 0.12，实测 0.004 / −0.074 / −0.057 / 0.002）：这是一条**真人服装**判据，用在高达和哥斯拉身上必然永远触发。也就是说：现在的"重打一次"既不会因真失败而打，也不会因真成功而停。

**只有"最差角色 + 最差秒数"能排出导演的判定**。用 take 自己的 SAM 遮罩（96 硬阈值、并集、裁到自身外接框、归一化成方形轮廓）去比目标 P 图 cutout 的 alpha 剪影，逐秒 IoU（`_dsh_verify_13/godzilla/measure_round108_take_vs_target.py`）：

| 最差角色 | 中位 IoU | 最差十分位 p10 | IoU<0.55 的秒占比 | 导演 |
| --- | --- | --- | --- | --- |
| 11:50 R1 | 0.6378 | 0.4232 | **17.9 %** | 认可 |
| 14:24 R2 | 0.5718 | 0.3690 | **30.9 %** | 否决 |

逐秒序列顺手把病灶点了出来：**11:50 的 R1 在 5.0–6.5 s 崩到 0.19 / 0.30 / 0.31**——那就是导演上一轮已经看见、我这轮才量到的"原人的脸套着高达甲"；**14:24 的 R2 从 0.0 s 起就压在 0.37–0.41、3.5–4.25 s 只有 0.11 / 0.14**——哥斯拉根本没进场。**整枪中位数把这两件事都藏了**，所以任何按中位数的分数（包括现有审计）都排不出这两枪。

**判据**：最差角色 `p10 ≥ 0.40` 且 `IoU<0.55 的秒占比 ≤ 0.25`。两枪四个角色全部落在对的一侧，两侧都还有余量（0.4232 vs 0.3690、17.9 % vs 30.9 %）。

**本轮实现（只记账，不判死）**：产品自己的函数 `smart_render_worker._character_swap_take_target_shape`（只用 PIL，不引 numpy），写在**合成阶段**的 pass 行上——因为这条量要等 SAM 交出遮罩才算得出，而"重打一卷"那条路早在审计阶段就跑完了；诚实说明：**`block` 目前只是写进 manifest 的结论，还不会自动重打**。开关 `H3_CHARACTER_SWAP_SAM31_TARGET_SHAPE=record|block|off`（默认 record），两个刻度 `..._SHAPE_IOU_FLOOR`（0.20–0.95，默认 0.55）、`..._SHAPE_WEAK_SHARE`（0.02–0.90，默认 0.25）。
**产品函数在两枪保留文件上的复现**（`_dsh_verify_13/godzilla/verify_round108_shape_log.txt`）：11:50 = R1 0.6393 / 0.4623 / 20.7 %，R2 0.6217 / 0.5783 / 0 % → **PASS**；14:24 = R1 0.6711 / 0.6343 / 1.7 %，R2 0.5695 / 0.3691 / 29.3 % → **FAIL**；weak seconds 直接写成 `[[5.0, 7.5]]` 与 `[[0.0, 4.5]]`。与导演判定**两枪全对**（离线那版是 numpy，产品这版是 PIL，差异 ≤0.02，来自 fps 取整造成的 56→58 个采样）。

**第二件事——把"重打"的权利还回去，但不交给被证伪的分数挑**：`H3_CHARACTER_SWAP_NONHUMAN_MAX_ATTEMPTS` 从临时的 1 改回 **2**（非人目标失败就多打一卷，真人镜头仍是一卷）；新增 `H3_CHARACTER_SWAP_NONHUMAN_RANKING=first|audit`，**默认 first**：非人目标保留**第一卷**，因为"按分数挑一卷"已被上面那组数字证伪（分数会把被认可的那卷扔掉），两卷都留在 `identity_attempts/`、分数都写进 `attempt_table`，导演要换就是拷一个文件。填 `audit` 恢复真人那套挑法。

**排除项（别再投进去）**：想用"take 减 plate"的差分轮廓代替 SAM 遮罩（审计阶段唯一在手的东西）——**绝对值不成立**：差分把整幅画都算进去了（`drawn_share` 恒 0.19–0.26、IoU 恒 ~0.2、四种情形 IoU<0.55 秒占比都是 100 %），只有**时间凹陷**能用（11:50 R1 在 4–6 s 0.13/0.12/0.15、14:24 R2 在 4–5 s 0.08/0.06）。同理，`fill_delta`、`colour_distance`、`source_leakage`、`aspect_delta` 这些整枪统计在两枪上只能排对 1/2 角色（`_dsh_verify_13/godzilla/round108_metrics/round108_metric_rows.json`）。

**给导演的规矩（Round 108）**：manifest 的 pass 行现在有 `target_shape_iou_median / _iou_p10 / _weak_share / _weak_seconds_ranges_seconds / _weak`，它就是"这一角色有多少秒真的像目标 P 图"，`_weak_seconds_ranges_seconds` 直接给秒。从这一轮起**非人镜头失败会多打一卷，Preview 可能要 ≈ 40 分钟**（真人镜头仍 ≈ 20 分钟）；改 env 都要 Studio 完全退出再开。想立刻退回本轮之前：`TARGET_SHAPE=off` + `NONHUMAN_RANKING=audit` + `MAX_ATTEMPTS=1`。

**验证**：`testing/test_round108_target_shape.py` 新增 18 项（开关与钳位、空 cutout、形体对/不对、不可测量时只报告不报错、合成把 series 写进 pass 行、`off` 完全跳过解码、诊断抛异常也不能让 Segment 失败、非人保留第一卷而真人仍按相似度、env 默认值且每键只出现一次、policy 104）；回归全绿共 256 项：round108 18 / round107 14 / round106 16 / smart_render_worker 48 / round102_sam_preflight 16 / round103 19 / round104 13 / round105 10 / round69 102。policy **104**（两份），钉位同步 103→104 于 round103 / 104 / 105 / 106 / 107 / 69 六个测试文件。

**待验收**：需要打一枪 Preview（非人镜头会多打一卷，请留 ≈ 40 分钟）。这一枪要看的是 `target_shape_*` 是否如两枪复盘那样点名，以及保留第一卷是否比按分数挑更接近导演的眼睛。


### 替换终于成立了，于是"勾线"和"穿崩"被这一枪的原始文件拆成两件事 —— Round 107 / policy 103（2026-11-09 中午）

**现场**：11:50 那一枪（policy 102，`attempts_used: 1`，只打一卷）manifest 干净得第一次像话：`fallback_reason: ""`，两路 take 遮罩 **`mask_coverage_share: 1.000`、`mask_coverage_holes_seconds: []`**，`mask_fragment_object_indexes` 为空（碎片机制一次都没动用），空壳/退化槽照常点名（take R1 `[2,3]` 退化、take R2 空槽 `[3]`、V1 `[2,3,4]` 退化）。导演的话变成："替换角色效果很好，只是 sam3 的边缘勾线出现瑕疵，合成的时候出现穿崩严重"。

**先纠正一条 Round 106 记录里的说法**：per-pass 的 take / plate / mask **不是**"只保留最近三枪"——**跑成功的那一枪会在结束时自己清掉中间件**，21:17 / 23:37 / 00:11 那三个目录之所以还在，是因为它们当年是**报错中断**的枪。所以 11:50 的中间件在本地已经不存在，唯一剩下的副本是 ComfyUI 的 output：`_dsh_verify_13/godzilla/fetch_comfyui_files_107.py` 按 manifest 记录的三个 `sam31_prompt_ids` 从 `/history` + `/view` 取回了 **16 个文件**（plate 640×366/335 帧、两卷 take 928×512/334 帧、9 个 mask 960×512 与 928×512/345 帧）。这意味着：**打一枪之后想复盘，就要在 ComfyUI 被新任务挤掉 history 之前取件**。

**排除项（都是真的，但都不进画面）**：`measure_round107_registration_real_1150.py` 把成片、plate、take、mask 四件真物按产品的滤镜口径逐帧对账——成片实际被替换的区域 vs 合成器被告知的遮罩，**最优校正中位 dx ±2 px、dy 0、dt = 0 帧**（11 个时间偏移 × ±8 px 搜索）。所以这两条只是几何事实，不是缺陷：take 928×512 与它自己那套 mask 960×512 各自 fit 到 640×366 后落点差 6 px / 高度差 3.4%，以及 SAM mux 给 mask 多塞的 11 帧（345 对 334）。同理，"V1 遮罩 + take 遮罩求并集"也不是主因：R1 t=1.0 时 take 遮罩 0.2093 / 并集 0.2159，R2 的并集干脆等于 take 遮罩。

**勾线在哪里**：`rim_round107_1150.py` 只保留"遮罩外扩 6 px 减内缩 6 px"那一圈、放大 2 倍（`._sheet/107/rim_bands_1150.png`）——画面里只剩边缘本身：一侧是 plate 的地毯/墙原色、另一侧是 take，轮廓是**阶梯状硬折线 + 双线**，而 plate 的地毯色以长条形状**漏进了哥斯拉腿脚之间的身体内部**。病灶就是那行 `dilation,dilation,gblur=sigma=1.4`：先把硬阈值（`lut` ≥96）的粗糙剪影外扩 2 px，再把羽化带压在**外扩之后**的边界上，于是 1-3 px 的 plate 原色沿轮廓活下来。

**穿崩在哪里**：`sheet_round107_take_vs_composite_1150.py` 把同一秒的 composite 与 take 并排（`._sheet/107/take_vs_composite_1150.png`）：**t=4.0 s 的 take 单帧里就已经是 chibi 金发绿眼的源角脸**（高达只剩肩甲和头盔碎片围在脸外），t=7.0 s 连黑发眼镜源角都整张回来了。也就是说 4.0 / 5.5 / 7.0 / 11.5 s 这几秒的"穿崩"**发生在 take 内部**，合成只是忠实搬运——这一半属于"角色替换"，不属于 mask。

**改了什么**：`_composite_sam31_character_swap_roles` 的边缘处理改成可切换 `H3_CHARACTER_SWAP_SAM31_EDGE_MODE`，四档在同一批文件上用产品自己的合成函数重打并打分（`recomposite_round107_variants.py` + `score_round107_variants_1150.py`，6 个时刻取平均）：

| 档位 | 轮廓外 3-8 px 环里的假背景变化（勾线） | 明显被 take 画过却漏回 plate 的比例（穿崩） | 轮廓梯度（锯齿） |
| --- | --- | --- | --- |
| `classic`（旧行为） | **96.3 px/秒** | 0.75 % | 24.49 |
| `soft`（不放大只羽化） | 10.7 px/秒 | 2.04 % | 24.36 |
| **`soft_grow`（新默认：外扩 1 px 再羽化）** | **12.5 px/秒** | **1.29 %** | 24.60 |
| `soft_fill`（再加 take 亮度差补漏） | 3273 px/秒 | 7.16 % | 16.35 |

默认取 `soft_grow`：勾线按 87 % 掉下去，同时把"完全不放大"造成的漏回让回一半。`soft_fill` 已实现且可切换，但**不当默认**——它把 take 与 plate 的亮度差当补漏，这一枪上替换变半透明、plate 的源角从身体里透出来（`._sheet/107/modes_grid_107.png` 最右一列），8 px 外还多改了 11448 px/秒。

**怎么退回**：`H3_CHARACTER_SWAP_SAM31_EDGE_MODE=classic` 逐字节退回 Round 106 的滤镜图（测试逐字符钉住那行 `dilation,dilation,gblur=sigma=1.4`）；`H3_CHARACTER_SWAP_SAM31_DIFF_FLOOR`（16-200，默认 72）只在 `soft_fill` 里起作用。

**给导演的规矩（Round 107）**
1. 看到"替换对了但边缘描线"，现在先看 manifest 的 `character_swap_composite.mode` 是 `sam31_v1_plus_role_output_instance_masks_v3` 而 `fallback_reason` 为空——那就确实是合成边缘，调 `H3_CHARACTER_SWAP_SAM31_EDGE_MODE`（`classic` ↔ `soft_grow` ↔ `soft`）即可，不用再动 SAM 阈值。
2. 判断"穿崩"归属只需一帧：**把那一秒的 take 单独看一眼**。take 里就已经是原人，就是替换不稳（归 Round 105 那半边：把 `H3_CHARACTER_SWAP_NONHUMAN_MAX_ATTEMPTS` 改回 2、或换 seed）；take 是干净的而成片有原人，才是 mask。
3. **打完一枪要复盘就马上取件**：成功枪会自己删掉 per-pass 中间件，只有 ComfyUI 的 history 还留着 mask 和 take，新的任务会把它们挤掉。
4. 别再去修那 6 px 落点差和 11 帧差：已实测它们不进画面（最优校正 dx ±2 px、dy 0、dt 0 帧）。

**验证**：新增 `testing/test_round107_sam_edge.py` 14 项（默认档位、四档可选、junk 回默认、`classic` 链逐字节、`soft_grow` 只外扩 1 px、`soft_fill` 的 plate 亮度差只允许落在外扩 3 px 的环内、`DIFF_FLOOR` 进滤镜图、时间闸门仍在新边缘链之前、V1∪generated 在四档都保留、policy 103 两侧、两个新 env 在 `DESIGN_ENV_RENDER_KNOBS`）；邻居按文件跑全绿——round106 16、smart_render_worker 48、round102 16、round103 19、round104 13、round105 10、**round69 102**。两份主文件编译通过。

**待验收**：需要一枪 Preview（≈20 分钟，`attempts_used: 1`）看 soft_grow 的成品边缘；本轮**没有**动"take 画回源角"那一半。

### 导演在 ComfyUI 看到的"全黑"是真的，但不是 SAM 罢工：它把一个人切成几块，而我们只发了一块 —— Round 106 / policy 102（2026-11-09 上午）

**现场**：07:58 那一枪（policy 101，`attempts_used: 2`，20 分钟，complete 不弹窗）SAM 分数一切正常——pre-flight `trusted`（R1 **0.9221** / R2 **0.8065**），take 侧 R1 **0.8893** / R2 **0.7328**，`sam31_instance_masks_skipped: []`、`fallback_reason: ""`。导演盯着 ComfyUI 说"mask 是全黑的"。把成片按 10 个时刻摊开（`._sheet/106/shipped_preview_0758.png`）：**0–2.5 s 是完整 Gundam ✓，11 s 有完整 Godzilla ✓，3.5–9.0 s 和 13 s 全是原人**——成立的两段刚好就是被选中那个槽位有白像素的时间。

**证据怎么取的**：07:58 的 per-pass 本地缓存已被清掉（只剩 23:37 / 00:11 / 21:17），所以 13 个 mask 视频是从 ComfyUI `/history/<id>` + `/view` 原样拉回本地测的（`_dsh_verify_13/godzilla/fetch_comfyui_sam_masks_106.py`）。度量用产品自己的解码口径：按合成滤镜同一道线 `lut=y='if(gte(val,96),255,0)'` 二值化、4 fps 逐样本算 **bbox** 与 **白像素占整帧比例**（`measure_round106_coverage_metric_neca6.py`，1044 个样本）。

**测出来的事实**：
- **空壳 mask**：take R1 的中标槽 object00 在 6.25–11 s 的 bbox 仍覆盖 R1 框的 0.95（IoU 0.85+），白像素却只有 **0.0035–0.026** —— 分数照读 0.89，画面什么都没有。`_mask_frame_stats` 旧版只报 bbox，所以关联天生看不见"这帧没有遮罩"。
- **被扔掉的碎片**：take R1 object01 从 5 s 起一路带到结尾（中位白像素 0.4251），正是 object00 缺的那一段；take R2 object03 在 5.25–8 s 与主块同源（中位 IoU 0.836）。规则是"每个角色只能拿一个槽位"（`match_sam31_masks_to_passes` 的贪心 + `_sam_target_score` 只取**最好的 8 个样本**求均值，而 `_mask_frame_stats` 遇到黑帧直接 `continue`），于是洞从来不进分数。
- **"全黑"的槽位**：take R1 object02/03 峰值白像素 **0.0008 / 0.0011**，V1 object02/03/04 **0.0008 / 0.0011 / 0.0012**（bbox 面积约 0.03%）——这就是导演在播放器里看到的"全黑"；它们不会被 Round 104 的"整帧冒充"闸门拦住（那道闸门抓的是中灰 0.44–0.55 的照片帧），但也确实什么都没有。
- **阈值有实测间距**：全部 1044 个样本里，空壳聚在 **0.0000–0.0011**，最近的真实样本在 **0.0129**——中间差 12 倍，所以 0.010 这道线不是拍的。
- **别人的身体不能混进来**：take R2 object00 得 0.4594 分，但它是左边那位——对中位期望框 IoU 只有 0.318，自身框有 **0.405** 落在角色框外（真身/碎片都 ≤0.104）。溢出（spill）就是拦住它的那道线。
- **几何口径**：溢出是对"手工框 ∪ V1 anchor"量的（Round 103 已把 anchor 传进关联）：R1 的 5–14 s 碎片对手工框溢出 0.491、对并框只 0.104，而 R2 那具别人的身体两种口径都是 0.405。

**三条病根（都是写死的授权决定）**：(1) 每角色一票 + best-8 打分 + 黑帧不进样本 ⇒ 半个 clip 的遮罩被当成完整遮罩发出去；(2) 没有"覆盖率"这个概念，manifest 里没有任何一行会说"R1 的遮罩只盖了 6.7/14 秒"，于是"ComfyUI 里看着全黑"永远没有对账处；(3) 空壳槽位与全黑槽位被 `valid_masks` 静默丢掉，不进 manifest。

**修法（只动关联，不动合成）**：中标槽位与它的 `match_score` **一字不改**（Round 69–104 的配对判定原样保留），选中之后回头问其余槽位："你手里有没有中标者缺的秒数？"一个槽位只有在**逐样本**同时满足「白像素 ≥0.010」「bbox 落在角色期望框上 IoU ≥0.15 且面积达 12%」「这些样本的中位 IoU ≥0.35」「平均溢出 ≤0.35」「合格样本占比 ≥10%」时才成为该角色的碎片；若那槽位已被别的角色认领，还要本角色的中位 IoU 高出 **0.15** 才许共享（Round 69 的 margin 规矩保留）。碎片和主块一起发同一个 pass——合成器早就用 `blend=all_mode=lighten` 把同一 pass 的多张 mask 求并集（`smart_render_worker` 的 `sam{kind}Union*` / `samV1GeneratedUnion*`），mask 空白处本来就没有像素，所以**不需要逐碎片时间闸门**、也不需要改滤镜图和返回结构。同时 manifest 每个配对行新增：`mask_coverage_share` / `mask_coverage_seconds` / `mask_coverage_ranges_seconds` / `mask_coverage_holes_seconds` / `mask_clip_seconds` / `mask_primary_coverage_share` / `mask_fragments` / `mask_fragment_object_indexes` / `mask_coverage_floor` / `mask_coverage_low`，第一行加 `mask_empty_object_slots`（整槽全黑）、`mask_degenerate_object_slots`（有框没像素的"全黑"槽）、`mask_fragments_mode`、必要时 `mask_coverage_warning`。覆盖率不足**只记账不卡片**（Round 103 的"继续跑"规矩）：下限默认 0.55，`H3_CHARACTER_SWAP_SAM31_MASK_COVERAGE_FLOOR` 可调 0–1；`H3_CHARACTER_SWAP_SAM31_MASK_FRAGMENTS=off` 整体退回 Round 105 的行为。clip 长度按整套槽位的最晚样本算，不按中标槽自己算——否则"中标者提前不吭声"的最后 1.75 秒会躲过记账。

**离线复现（零渲染：`replay_round106_association_neca6.py` 用产品真函数跑 07:58 的真 mask）**：配对分数与 manifest 逐位一致（0.8893 / 0.7328 / 0.9221 / 0.8065），所以这就是那一枪做过的同一个决定：

| 哪一侧 | 07:58 实际发出 | 当时覆盖率 | Round 106 发出 | 覆盖率 | 剩余空洞 |
| --- | --- | --- | --- | --- | --- |
| take R1（Gundam） | object00 | 0.672 | object00 + **01** | **0.862** | 9.0–11.0 s |
| take R2（Godzilla） | object02 | 0.517 | object02 + **03**（与主块重叠） | 0.517 | 0–5.25 s、12.75–14.5 s → `low=true` |
| V1 pre-flight R1 | object01 | 1.000 | 不变 | 1.000 | 无 |
| V1 pre-flight R2 | object00 | 0.862 | 不变 | 0.862 | 3.0–4.75 s |

R2 那一路被标 `mask_coverage_low`，是诚实的：Godzilla 的遮罩本来只盖后半段，前 5.25 秒 SAM 就没有这具身体的像素——那一段成片必然还是原人，下一轮该由"要不要把覆盖不足的角色改走 delta-mask 合成"来决，而不是让 manifest 装看不见。**要留两句话给导演**。第一句：3.5–6.25 s 内 R1 的 mask 是满的（白像素 0.34），成片那里却仍是原人；这只能是 take 自己在那段画回了原人、或者 plate/合成把 paste 丢了，光看 V1 和成片分辨不了。第二句是把 Round 103 那条待办**改对**：per-pass take 其实是留在盘上的——`cache/generated_outputs/preview/<runhash>/segment_.../character_swap_pass_01_R1/01_save.mp4`（连同 `identity_attempts/attempt_NN__01_save.mp4`、plate `00_source.mp4` 和 `sam31_generated_role_masks/` `sam31_v1_role_masks/` 全套槽位），只是这个缓存**只留最近三枪**：我查 07:58 时它已经被轮换掉，活下来的是 21:17 / 23:37 / 00:11。所以要看某一枪的 take，就在下一枪开跑之前把它那一目录拷走。（顺带一个复现：拿今天的代码重跑 00:11 那枪自己的 9 个 mask 文件，R2 仍然是 0.40 被拒——和当年弹窗一字不差；而那两枪 23:37 / 00:11 当年是 `SAM3.1 weak association` → 整段退到 delta-mask 合成器，SAM 的遮罩**从没进过它们的画面**，所以"mask 全黑"那两枪看的是另一个问题。）

**测试**：新增 `testing/test_round106_sam_mask_fragments.py`（16 项，全部用 07:58 的实测数据做 fixture：空壳不算覆盖、碎片被收下、别人的身体不被抢、覆盖不足仍出片且记账、off 开关退回旧行为、speck/全黑槽位被点名、两个新旋钮进 Studio 白名单、junk 输入夹紧）。逐文件跑绿：`test_round106` 16/16、`test_smart_render_worker`、`test_round102_sam_preflight`、`test_round103_sam_auto_repair`、`test_round104_sam_prompt_and_frame_matte`、`test_round105_nonhuman_swap`、`test_round69_manual_parity` **102/102**。round69 的两处钉值刷新为 102，并把它那条"整字典相等"改为钉住本轮关心的键 + 一行覆盖率样例（新增的键归 Round 106 的合同管）。Studio 离线预编译再跑一遍：`policy = 102`、Round 105 的 `NONHUMAN CAST LOCK`（388 / 390 字）与 plate 参数一字未变、**工程 JSON mtime 前后一致（没写盘）**。

**已记录、本轮未修**：SAM 的 mask 视频是 960×512，take 是 928×512，V1 plate 是 640×366——`scale=...:force_original_aspect_ratio=decrease,pad=...` 之后 mask 落在 640×341/y=12、take 落在 640×353/y=6，遮罩相对它要贴的像素**低约 6 px、短 3.4%**，两种 mask 求并集时也一起错开。本轮之前就在，本轮没放大它的危害（碎片只是多了几张同样错位的遮罩，覆盖判定各自在自己的归一化坐标里做），修法是把 mask 统一到 take 几何，留给下一轮。

**给导演的规矩（Round 106）**：
1. **改了 worker 与 Studio 的代码，必须完全退出 Studio 再重开**（policy 101 → 102），否则下一枪还是旧规矩。
2. 再看到"ComfyUI 里 mask 全黑"，先读 manifest 那一段的 `sam31_role_matches`：`mask_degenerate_object_slots` / `mask_empty_object_slots` 就是那几个空槽；`mask_coverage_share` + `mask_coverage_holes_seconds` 会直接写"哪个角色只盖了几秒、缺哪几秒"。**空洞之内**是 SAM/关联的事，**空洞之外**（有 mask 却仍是原人）是 take 或 plate 的事——从此两边分得开。
3. 想让某个角色多吃几块碎片：`H3_CHARACTER_SWAP_SAM31_MASK_FRAGMENTS=off` 一键退回；嫌 0.55 太松/太紧就调 `H3_CHARACTER_SWAP_SAM31_MASK_COVERAGE_FLOOR`（0–1）。覆盖率不足**不会**弹窗、不会停枪，只进 manifest。
4. 本轮没花新枪：所有结论都来自 07:58 的真 mask 与成片。下一次按你的意思跑 Preview 时才需要那 20 分钟（Round 105 的非人重试规矩还在，最坏仍是一 pass 两 take ≈ 40 分钟）。

### mask 已经对了，坏的是"换人"本身：plate 不擦身体、提示词命令哥斯拉保留衣服、blocking 判定从不重打 —— Round 105 / policy 101（2026-11-09 凌晨）

**现场**：02:08 那枪 20 分钟跑完、不弹窗、`attempts_used: 1`、状态 complete。SAM 这一层已经完全健康——pre-flight `verdict: trusted`（R1 **0.9221** / R2 **0.8065**，`reused_by_composite: true`），take 侧 R1 **0.9189** / R2 **0.7228**（昨晚 R2 只有 0.40），`fallback_reason` 空，Round 104 的 `sam31_text_prompt = person, gundam, godzilla` 确实起了作用。**画面却是另一回事**：Gundam 只在 0–2.5 s 与 8–13.5 s 的远景成立，3.5–7.5 s 特写段两个人都退回原人，右边那位从头到尾还是黑发眼镜男，脸上身上带着一团团灰糊（4–11.5 s 最明显，`._sheet/gen_R2_right.png`、`gen_R1_left.png`、`plate.png`）。产品自己也判了：两枪 `passed: false`、`blocking: true`、`blocking_cause: target_reference_similarity`、`head_layer_only: true`、`action: retry_fresh_seed`；P1（Godzilla）`target_reference_similarity 0.404`、**`target_likeness_score 0.019`**、`retention_score 0.754`（真人还在里面），衣柜位移 **-0.0140 / -0.0376**（下限 0.12），`quality_risk_score 0.952 / 1.384`。

**读码（三条都是写死的授权决定，不是模型不努力）**：

1. **plate 根本不擦身体**（`director_cut_studio.py:37266` `WARDROBE_GATES = {"dominant","head_dominant"}`，`medium_silent` 只有在 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE != off` 时才加入，见 37307-37315 与 37538）——而本项目这个值就是 `off`，所以那两枪只糊了发冠＋头（`suppressed_frame_area 0.235`，实测 band：hair `[0.685,0.14,0.2318,0.2751]`、head `[0.466,0.4151,0.4508,0.3799]`），**下面整段衣服是干净的**（`plate.png` 里一眼可见）。QC 却按"衣柜必须变 ≥0.12"打分——**审计在考一张它自己不许改身体的 plate**。更糟的是两个旋钮互相打架：`HEAD_BAND_SHARE=0.85` 时头带止于 y 0.7951，衣柜带只剩 **0.1156** 高（下限 `MIN_WARDROBE_BAND_HEIGHT=0.10`），再推高一点身体带就无声消失。
2. **提示词命令哥斯拉当人**：`design_engine.py:3171-3178` 给每个 cast 区间写死的锁 —— "Preserve @P1's exact recognizable **face, apparent age, hair, skin tone, body proportions, complete wardrobe, footwear and accessories**. Never blend, swap, duplicate, redraw or transfer this identity."，同一份 design plan 里明明写着 "Reconstruct @P2's Gundam armor and @P1's Godzilla scales"。模型照做＝只换脸。而且这句在项目里已经被截断成 "Never blend, swap, duplicate, **r.**"。这句话像（Project JSON 的 requirement 文字 + `design/revisions/R0001/design_plan.json`），**只改代码救不了已经写完的工程**，所以改在提示词编译处。
3. **`retry_fresh_seed` 是装饰**：非 legacy 路线一律 `lean_audit`，把审计规格钉成 `maximum_attempts: 1`（38520-38529，且在 38986 最后合并覆盖 38923 的 3），worker 那侧 blocking 的提升默认也是 1（`smart_render_worker.py:551`、`character_swap_blocking_max_attempts` 841-877），而唯一的闸门是 `if attempt < identity_attempts:`（5436）⇒ 结构上永远打一卷。另外 `status: complete` + `error: ""` 与 `character_swap_identity_failed: true` 并存（7688-7706 / 7666-7673），Studio 侧只标脏不拦（"QC is intentionally non-blocking"），所以失败的画面照样发出来。

顺带把两个"看起来矛盾的数字"钉死：`target_likeness_score` 是排名不是闸门（`_candidate_target_likeness` 2792-2857：similarity + 衣柜加成×1.5（上限 0.35，**负位移没有下限**）− 静嘴惩罚 − "角色相似度 ≥0.75 时 (retention−0.75)×4+0.10" 的折扣），P1 那 0.019 = 0.404 − 0.056 − 约 0.33；blocking 用的 0.5 是 `CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR`（527）。另外**参考图没有被裁成头**：`illustrated_full_design` + `identity_sheet_single_figure_passthrough = true` 说明 Relay 收到的就是 P1 全身图，"只换头"不是参考图裁切造成的。

**修法（判据只有一个：绑定的 P 图自己的话说这不是人）**：

1. **名词表＝唯一事实源**：`character_swap_engine.py` 新增 `CHARACTER_SWAP_NONHUMAN_NOUNS`（52 个 body-kind 词，**故意不含 `figure`/`toy`/`statue`/`model`/`doll`**——P1 的文字正是 "godzilla action **figure** by neca"，这些物件词会把真人镜头也带成非人）＋ `character_swap_nonhuman_nouns()`（整词、大小写不敏感、首见顺序、最多 4、脏值→`[]`）。Studio 在编译处一次算出 `target_recognition_text` 并写成 `pass_spec["nonhuman_target_nouns"]`，**pass 行、plate、提示词、重试上限读同一个事实**。
2. **plate 连身体一起糊**（`_character_swap_identity_suppressed_source`）：非人角色的 silent 门禁破例进入 wardrobe gates（`blur_desat`，`boxblur=6:3` + `hue=s=0.25`）；身份窗口自动收到 **0.62**（不再让 0.85 把头带压到只剩 0.1156）；figure 带宽/面积下限抬到 **1.35 / 0.62**（四足怪兽比头宽）。策略名会自动带上 `_wardrobe_blur_suppressed`，引擎随即写出与 plate 相符的那句话。
3. **换锁在编译时做**（引擎内，三条返回路径全覆盖：3465-3475／3686-3693／3844-3852，都在 append 之后、长度审计之前）：删掉那句人类锁（整句、截断成 "duplicate, r."、以及断在半词的三种形状都能删，"Do not introduce this role outside its assigned event interval." 的时间句保留），换上 **NONHUMAN CAST LOCK**（388 字符 ≤420）："… the figure's own moulded material, silhouette, proportions and scale replace the source performer's face, hair, skin, wardrobe, footwear and accessories. Keep no human clothes, hair or skin and no human face where this figure's head belongs; hold that one figure for the whole clip, never flickering back to the source performer."——最后半句专门对着"3.5–7.5 s 打回真人"这个实测闪烁。审计加 `nonhuman_cast_lock_nouns` / `nonhuman_cast_lock_chars`，Studio 的 `prompt_budget` 白名单放行（**只在真的换锁时才有这两行**，真人 Job 的 manifest 一字不变）。
4. **blocking 真的重打一卷**：非人目标时 `maximum_attempts` 由 `_nonhuman_swap_max_attempts()` 给（默认 **2**，`H3_CHARACTER_SWAP_NONHUMAN_MAX_ATTEMPTS`，clamp 1-3），真人仍是 1。`H3_CHARACTER_SWAP_NONHUMAN_TARGET=off` 可整体退回 Round 104 行为。

**验证**：新增 `testing/test_round105_nonhuman_cast_lock.py` **23 项**（两条真实 BLIP 文字各得 `["godzilla"]`／`["gundam"]`、物件词不算、整词不误伤 `spirited`/`giantswarm`、四种截断形状都清除且时间句存活、同一 prompt 应用两次只加一次、真人 prompt 逐字节不变、四条路线都会带锁且 audit 行数对得上）＋ `testing/test_round105_nonhuman_swap.py` **10 项**（**两个 arm 真跑 ffmpeg 滤镜链**：同一个 neca R2 框 `[0.45,0.2,0.85,0.9]`、同一个 0.85 头带 share，真人 arm 没有 `boxblur=6:3`、非人 arm 有且策略名带 `_wardrobe`，且非人的最大 `ih*` 带高比真人小 ≥0.10；两个旋钮的脏值与上下限；Studio 真的 import 了引擎的名词扫描；pass_spec／重试上限／白名单／manifest 投影都在位；policy 101 与 0.235／0.019／retry_fresh_seed 都留在注释里）。逐文件跑 18 套：**624 项通过**（round105 23＋10、round104 13、round103 19、round102 16、round52 48、round69 102、closeup 79、worker 48、design_engine 140、character_swap_engine 20、combat 21、round54/57/65 18/18/20、storyboard 3）。三处旧 pin 随本轮改名：round104 读的是 `"sam31_target_recognition": _sam31_target_recognition_text(`（现在一次算入 `target_recognition_text` 再复用）、round52 读的是字面 `"maximum_attempts": 1`（现在是条件式）。

**一处与本轮无关的红，别误判**：`testing/test_round91_illustrated_evidence.py` 的 `test_the_two_questions_stay_on_separate_predicates` 钉的是 `bool(target_is_illustrated)\n and CHARACTER_SWAP_PLATE_SUPPRESSION` 这段源码文字，而它在 Round 94 把 plate 门换成 `character_swap_plate_suppression_gate(...)` 返回二元组时就已经不在了——这句话在 `_backup` 里 11 月 1 日（round 52／53／59／62／66／67）的 `director_cut_studio.py` 都还在，在当前文件里**一处都搜不到**（现在是 38610 行的 `plate_suppression_allowed, plate_suppression_evidence = ...`），也就是说这个 pin 从 Round 94 起就悬空，和本轮的 plate／提示词／重试改动毫无接触（该文件其余 25 项全绿）。

**下一枪会发出去什么：不花钱的实机重放（`_dsh_verify_13/godzilla/replay_round105_nonhuman_neca6.py`，日志 `replay_round105_log.txt`）**——加载 neca_6 真工程、调用 Preview 按钮用的同一个 `_compiled_character_swap_window_job(0.0, 13.975, 0.5MP)`，只编译不打枪（工程 JSON 的 mtime 前后一样：`1794161361368715500`，也就是说这次重放没写项目数据）。两枪的 pass 行实测：

| | pass 0（R1 → P2） | pass 1（R2 → P1） |
|---|---|---|
| `nonhuman_target_nouns` | `["gundam"]` | `["godzilla"]` |
| `identity_suppression_strategy` | `medium_silent_listener_identity_suppressed`**`_wardrobe_suppressed`** | 同上（02:08 那两枪都没有 `_wardrobe` 尾缀） |
| `suppressed_frame_area` | **0.5769**（02:08 同形状是 0.235） | **0.291**（原 0.235） |
| `head_band_bottom` | 0.6599 | **0.634**（原来 0.7951 —— 0.85 的 share 被 0.62 顶住，身体带才有地方） |
| `body_bboxes_normalized` | `[0.0,0.6599,0.45,1.0]` | `[0.685,0.634,0.99569,1.0]` |
| 上线 prompt 里的人类锁 | **NONE** | **NONE** |
| 上线 prompt 里的 NONHUMAN CAST LOCK | 在（`nonhuman_cast_lock_chars = 388`） | 在（**390**） |
| `append_chars` / `over_budget` | 1544（`append_over_budget: true`）／prompt 4439 vs 预算 12320 ⇒ `over_budget: false` | 1546 ／4441 ⇒ `over_budget: false` |
| `maximum_attempts` | **2**（原 1） | **2** |

两处值得单独记：① 身体带**自动停在另一位的框边**——pass 0 停在 x 0.45（R2 框左边），pass 1 从 x 0.685 起（R1 框右边），这是 `_figure_extent_band_boxes` 的 `protected_boxes` 在起作用，也正是 Round 96 那一枪学到的教训（把旁边那位也抹掉＝关掉头发作丝 halo）；② `append_over_budget` 变 `true` 是**那句换锁条款上了线**（+388／+390 字符），不是回退，也不是硬超限——`over_budget` 仍是 false， Relay 那边 12 320 的总预算还剩 7 800 字符的余量。


**给导演的规矩（Round 105）**：完全退出并重开 Studio（`design_ai.env` 与 policy 都要在新进程里才生效）。policy **100→101**，代价＝各项目缓存段重新判定一次，不是重新打枪。时间与钱：**只有 blocking 判定才会多打一卷**，而这一枪 R1、R2 两枪都是 blocking，所以这一段的 Preview 最坏是 2 pass × 2 take ≈ **40 分钟**（原来是 20 分钟但画面是错的）；第一次就打合格的，多花 0。想退回旧行为就在 `design_ai.env` 写 `H3_CHARACTER_SWAP_NONHUMAN_TARGET=off`；只想控制重试次数就改 `H3_CHARACTER_SWAP_NONHUMAN_MAX_ATTEMPTS`（1–3，默认 2，只影响非人目标）。打完读这些行：pass 行／manifest 里的 `nonhuman_target_nouns`（应为 `["gundam"]`／`["godzilla"]`）、`identity_suppression_strategy`（应带 `_wardrobe_suppressed` 尾缀）、`identity_suppression_geometry.suppressed_frame_area`（0.235 应变成 0.29／0.58）、`prompt_budget.nonhuman_cast_lock_nouns` 与 `nonhuman_cast_lock_chars`、`attempts_used`（出现 2 就说明真的重打了）。**要看的结论**：`wardrobe_shift` 从 −0.014／−0.038 变成正数、`head_layer_only` 变 false、P1 的 `target_likeness_score` 从 0.019 往上走。诚实说一句：这一轮把"产品自己不给机会"的三条决定全部改对了，模型是否真给 Godzilla 画出整身，要看下一枪这几个数字——如果 plate 已经擦到全身、锁也换成了"重建非人形体"，而 `retention_score` 还是压不下去，那才是 Relay／H3 那侧的能力边界，届时再谈加大 megapixels 或换参考图 framing。

### 「R2 0.40」根本不是框的问题：SAM3.1 被要求只找"人"，还有一个槽位存的是整帧画面 —— Round 104 / policy 100（2026-11-09 凌晨）

**现场**：Round 103 装上后，导演问的是"为什么 SAM3 会报错"。把 00:11 那一枪留下的 mask 全量了一遍（`_dsh_verify_13/godzilla/measure_neca6_pass2_masks.py`、`check_mask_vs_frame_neca6.py`、`strip_neca6_pass2_masks.py`，图 `neca6_pass2_masks_t8.png`），答案不是框，而是两条更下面的东西。

**读码 + 实测（全部用产品自己的解码器和打分器）**：

1. **提示词写死 `person`**：`build_sam31_multiplex_mask_workflow` 的 `CLIPTextEncode` 里就是 `"person"`，`detection_threshold 0.35`、`detect_interval 1`、`max_objects = 角色数+2/+3`、`resolution 480`（`smart_render_worker.py:5578-5594`）。于是第二枪里**右半边的 Godzilla 连一个实例都没有**：那一枪 5 个槽位里只有 `02_23` 是人形（白色占比 0.210、union x 0.02–0.69 = **左边那位**），`01_35` 是底部一小条（面积 0.029）、`03_31` 只有 1 帧、`04_27` 全黑——**R2 框 `[0.45,0.2,0.85,0.9]` 的主体 x 0.69–0.85 整段没有任何 mask**。对照 V1 侧：两位 chibi 都有干净 matte（白 0.159 / 0.196），所以 V1 侧一直是健康的。
2. **有一个槽位存的不是 mask，是整帧画面**：`00_1.mp4` 灰度分布 mid-gray 占比 **0.440–0.558**，真 matte 只有 **0.000–0.007**（差 60 倍），图上也能直接看出是照片。而 `_mask_frame_stats` 的规则是"灰度 ≥96 就算实心、再取 getbbox"⇒ 它进了关联，成为"bbox 占 0.91 画面、56/56 帧都在的人"，并且**真的赢了 R2**：0.4517 vs 真人 0.4033，margin 只剩 0.0484。**弹窗里的 0.40 不是"框偏了"，是被一个假人赢了**；照它合成就是把整幅抹一遍——正是 Round 69 立这道门要拦的事。
3. **词其实早就在项目里**：P1 的 `recognition` 写着 `BLIP · Overview: godzilla action figure by neca`、P2 写着 `a gundam gundam …`（P2 被 H3 画成 chibi，所以第一枪的替换体反而能被"person"检出——这也解释了为什么只有第二枪炸）。

**修法**：

1. **提示词按角色实形自动加词**：Studio 把绑定 P 图的 `recognition`/`semantic_enrichment` 写进 pass 行的 `sam31_target_recognition`（故意进内容指纹：重写识别文字＝改变 SAM 找什么，该重新判定，不能复用旧 take），worker 扫 body-kind 名词表（`godzilla/gundam/monster/…`，**故意不含 `figure`/`toy`/`statue`**，它们只描述物件、会把 SAM 从已经分对的人形上带偏）后拼成 `person, gundam, godzilla`。`H3_CHARACTER_SWAP_SAM31_TEXT_PROMPT` 手填则覆盖基底（自动名词仍追加）。
2. **`H3_CHARACTER_SWAP_SAM31_DETECTION_THRESHOLD`**（默认 0.35＝历史值，clamp [0.05,0.95]）：导演想验证"非人体能不能被检出"就调它，配套的护栏是第 3 条——不然调低只会多出一堆场景大板。
3. **整帧伪 mask 先拒**（`_sam31_mask_frame_share` + `_sam31_collect_instance_rows`，阈值 0.10，实测两边 0.007 与 0.440 之间差 60 倍，判据极稳）：这种槽位不再进关联，**且不是偷偷丢**——`reason`/`object_index`/`mid_gray_share` 挂进 `sam31_role_matches[*].instance_masks_skipped`，manifest 另加 `sam31_instance_masks_skipped`、`sam31_text_prompt`、`sam31_detection_threshold`。
4. **顺手修掉一个真 bug**：`_sam31_mask_frame_share` 起初在 `timeout=` 参数里调 `_probe_duration`，而后者读不了视频时**抛 RuntimeError**——一个下载残缺的 mask 就能把整段判死。现在先探测几何、读不了返回 None（回归测试在案）。

**用真实数据重放（`_dsh_verify_13/godzilla/replay_round104_frame_filter_neca6.py`）**：V1 槽位 0（mid-gray 0.594）被拒，R1 **0.8887**／R2 0.7796 **不变**；pass 1 槽位 0（0.596）被拒，R1 仍 **0.9124**（健康那一枪毫无变化）；pass 2 槽位 0（0.449）被拒 ⇒ R2 的对手从"照片"变回**真人**，分数如实 **0.40**，自动修框仍**诚实拒绝**（那个体要 0.666 宽的框，超过 0.60 就会关掉发丝 halo）⇒ 按 Round 103 走 delta-mask 继续合成，不赔枪。顺带复核 Round 103 的 V1 锚点：喂对 bundle 形状（每 pass **获胜**的 mask，不是全部槽位）后 anchors = R1 `[0.0205,0.0938,0.6875,1.0]`、R2 `[0.3093,0.0039,0.9828,1.0]`，正是两位真人——之前那次锚点为空/为全幅是我脚手架的形状错了。

**测试**：新增 `testing/test_round104_sam_prompt_and_frame_matte.py` 13 项——workflow 不再有写死的 `"person"`、导演可设两值、短语按 P 图实形加词（用实测的两条 BLIP 文字）、无 caption 的项目完全保持原样（`person`）、手填短语仍追加名词、两个旋钮脏值与上下限、实测两群（0.000-0.007 / 0.440-0.558）被阈值分开且留 4 倍余量、mid-gray 由**解码帧**算出而非 bbox、帧槽被拒并指名 object_index、读不了的 mask 返回 None 且不新增失败路径、Studio 交词的管道与白名单在位、policy 100 且注释里带着 0.440／0.4517／0.4033。Round 103／102／69 的 policy 断言随本轮抬到 100。五套合跑 **198 项通过**；按老规矩逐文件跑 19 套 **626 项通过**（closeup 79、round69 102、round52 48、worker 48、design_engine 140 等，全部单文件运行，避开 round52 那组改环境变量不还原的坑）。

**测试之外的现场记录**：`testing/test_director_timeline.py` 里 3 个失败与本轮无关，别误判——`test_detected_v1_person_is_saved_into_the_shot_swap_pass` 是那个测试自带的假编辑器缺 `shot_deleted_roles`（整个测试文件从没出现过这个名字，而 `director_cut_studio.py:29755` 已经要求它：Ctrl+右键删角色那版功能落地后这个 stub 没跟上）；另外两个 `_planned_render_segments` 的分段断言拿到的是 `(0.0, 12.0)`／`(0.0, 5.2)` 这种**合并成一整块**的结果，正是 `production_batch_seconds` 默认 30 秒把短片并成一个 render unit 的样子（16447 行），也就是说它们读到了本机存下来的工程设置，与 SAM、policy、pass 行新字段都无接触（policy 常量在这份文件里只做缓存有效性与盖章：23359／39327 比较、35790／39007／39652 写章）。

**给导演的规矩（Round 104）**：完全退出并重开 Studio；policy 99→**100**，代价＝各项目缓存段重新判定一次（prompts／plate／QC 结论不变）。下一枪想看 SAM 是否终于给 Godzilla 单独出 matte，就读 manifest 的 `sam31_text_prompt`（应为 `person, gundam, godzilla`）与 `sam31_instance_masks_skipped`（应列出那个整帧槽位）；还没检出的话把 `H3_CHARACTER_SWAP_SAM31_DETECTION_THRESHOLD` 降到 0.2 再试一枪。P1／P2 的 `recognition` 若在 Design 页重写，会自动触发相关段重新判定。



### SAM3.1 认人失败不再赔一整枪：自动修框 + delta-mask 继续跑 —— Round 103 / policy 99（2026-11-08 深夜～11-09 凌晨）

**现场（导演原话：「sam3 出 error，继续跑！！！」）**：Round 102 装上后同一晚 neca_6 又失败两次。23:37 弹 **R1 0.48** —— 而我按它自己留下的 mask 反解、用产品自己的打分器复算，V1 侧那次关联其实是 **R1 → object 5（左边那位）0.7726，领先次选 0.3514**，认人完全正确。把框换成实测成片包络 `[0.14, 0.105, 0.685, 1.0]` 后重跑，00:11 变成弹 **R2 0.40**：R1 这次在成片侧拿到 **0.9124**（V1 侧升到 **0.8887**），失败点整段前移到第二个角色。两次的共同点没变：**两枪都已经生成完并写盘**（23:37：`character_swap_pass_01_R1\01_save.mp4` 4,177,894 B、`pass_02_R2\01_save.mp4` 6,541,283 B；00:11：4,742,677 B / 6,224,745 B），弹窗却把整段判死。而且 manifest 里 `character_swap_composite` 依旧是**空**——数字全部丢失。

**读码定位（全部用产品自己的 `_mask_frame_stats` + `_sam_target_score` 现场量，见 `_dsh_verify_13/godzilla/measure_gate_geometry_neca6.py`）**：

1. 23:37 的 traceback 是 `main:7115 → queue_character_swap_passes:6739 → queue_sam31_role_output_masks:5893 → match_sam31_masks_to_passes:5810`，且消息里**没有** Round 102 预检的附加句 ⇒ **V1 预检已通过**，拦下的是**成片侧**那道门。
2. 成片侧 mask 的真实几何：pass 1 只有 **16 / 56 个采样帧（0–3.75 s）**属于替换后的人（`03_31.mp4`，union `[0.1396,0.1055,0.6854,1.0]`），**3.75 s 之后 SAM 把整幅图并成一个团块**（`00_1.mp4` 的 median bbox 面积 **0.9111**／p10 0.9095）⇒ 该角色的次选就是这坨全画面团块（**0.4244**），与胜出者只差 **0.0551**。也就是说：**追踪已经不再跟着人了，这种 mask 没有任何框能到 0.70** —— 门此时不是在保护画面，只是在拦产出。
3. 对照 V1 侧：`00_1.mp4` 全画面团块、`03_23.mp4`＝右半边那位（median 0.1937）、`05_27.mp4`＝左边那位（median 0.2903），关联干净且自信（0.7726／0.7796，margin 0.3514／0.3278）⇒ **成片侧的 SAM 才是不可信的那一侧**。
4. 反解可过关的框：实例包络原样 `[0.1396,0.1055,0.6854,1.0]` → **0.7397**（宽 0.5458 ≤ 0.60 ⇒ 发丝 halo 仍开）；但四边加 0.08 的框分数更高（0.8031）却**把第一名让给了全画面团块** ⇒ 高分≠认对人，这正是 Round 69 立这道门的理由。

**修法（自动修正，不再让导演重画框、也不再赔枪）**：

1. **自动修框**（`_sam31_repair_weak_association_boxes`，在 `match_sam31_masks_to_passes` 抛错之前跑一次）：候选阶梯 = 实例包络 → 加 0.06 → 加 0.12 → 放宽到 `max_width`，**只取第一个同时满足全部护栏的候选**（不做"挑分数最高的框"）：① 仍必须是**同一个 SAM 实例**获胜；② 领先次选 **≥ 0.05**；③ 自身必须 ≥ 下限，且宽度 **≤ `H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH`（默认 0.60＝Round 68 的 max_box_width，超过就关掉 halo）**；④ 必须留在人身上——有 V1 预检产物时用 `sam31_v1_role_anchor_envelopes` 算出的 V1 包络做**包含度 ≥ 0.60**（本次实测 **1.00**），没有 V1 证据时退化为与原框 **重叠 ≥ 0.30**（实测 0.329）；⑤ 有真实轨迹（`composite_track_samples`）的角色**不修**——一个静态框替代不了一条路径。
2. **修好就直接用**：把新框写回 pass 行（`composite_bboxes_normalized` + `composite_bbox_provenance = "sam31_auto_repaired"`），合成、身份审计、manifest 从此都说实测几何。
3. **修不好就继续跑**：成片侧的弱关联不再上抛判死，改为记 `fallback_reason` 并走**已有的 delta-mask 合成**（那条路靠"这一枪和它自己的源帧差了什么"定位替换区域，**根本不依赖 SAM 认人**）。`H3_CHARACTER_SWAP_SAM31_WEAK_ASSOCIATION=abort` 才恢复 Round 69 的硬失败。
4. **Round 102 的预检默认改成 `advisory`**：它该做的事（提前把分数测出来）保留，它拦人的权力默认关掉——因为成片侧已经不再拦了。
5. **失败也要留证据**：抛错消息追加 `Evidence: <角色> auto-box: <拒绝原因>`；`box_auto_repair` 记录（`attempted/accepted/applied/from/to/repaired_score/margin_over_runner_up/v1_anchor_containment/authored_box_overlap/best_candidate_score/sam_envelope_normalized/refused`）**挂在每一行 `sam31_role_matches` 上**并随 manifest 落盘；manifest 另加 `sam31_weak_association_action` / `sam31_auto_box_mode` / `sam31_v1_role_anchors_normalized`。拒绝原因取**第一个**触发护栏的理由（`_refuse`），否则"包含度不够"会被后面更宽框的"分数只有 0.60"盖掉。

**用真实数据回放（`_dsh_verify_13/godzilla/replay_round103_repair_neca6.py`，policy 98 那次跑的产物）**：V1 侧 R1 **0.8887**／R2 0.7796 ⇒ 预检不误伤；pass 1 成片 **0.9124** ⇒ 无需修；pass 2 成片 **0.45** ⇒ 自动修框**诚实拒绝**（`no candidate box fitted the size band [0.02, 0.85] within width 0.60`）⇒ 走 delta-mask 继续合成，**这一枪不再白烧**。

**测试**：新增 `testing/test_round103_sam_auto_repair.py` 19 项——三个旋钮的默认值与脏值（auto-box 默认 `on`、宽度上限默认 0.60 且 clamp 到 [0.20,1.0]、弱关联动作默认 `continue`）、阶梯不会给出会关掉 halo 的框（实测包络 0.5458 留在阶梯里、加边 0.7058 被丢掉）、修好会改写 pass 行并带 provenance、`advisory` 只记录不改框、`off` 精确恢复 Round 69 且消息写 `auto-box is off`、噪声包络（两帧相距 0.34 + 一个全画面团块）被"换了人"拒绝、V1 锚点包含度不足被拒、有轨迹的角色拒修、锚点函数遇烂 bundle 返回空、三个旋钮都在 Studio 白名单里、manifest 三个新键在位、policy 99。`testing/test_round102_sam_preflight.py` 两项默认值随本轮改写（预检默认 `advisory`），Round 69 门仍在位的断言加上了 `if sam_weak_action == "abort":`。三套合跑 **137 项通过**（round103 19 + round102 16 + round69 102）；按老规矩**逐文件**跑 18 套共 **466 项通过**（worker 48／closeup 79／engine 20／round52 48／round54 18／round57 18／round65 20／background_extra 9／design_ai_service 20／design_engine 140／combat 21+20／storyboard 3／qc_advisory 4／silent_audio 8）。**留一个已知的坑（不是本轮引入）**：`test_round52_swap_routes` 会改掉 `H3_CHARACTER_SWAP_*` 环境变量且不还原，与 `test_character_swap_closeup_gates` **同进程**跑会让后者 13 项假失败（`round52 + closeup` 复现，`round103 + closeup`、`worker + closeup` 都正常）——这两套要分开跑。

**给导演的规矩**：改完码或 env 必须**完全退出并重开 Studio**；policy 从 98 抬到 **99**，代价是各项目缓存段重新判定一次（prompts／plate／QC 结论本身不变）。之后 SAM3 认人失败不会再弹窗丢枪：能修就自动修框并认这次的人，修不了就换 delta-mask 出片，两种情况都在 manifest 里留数（`sam31_role_matches[*].box_auto_repair`、`fallback_reason`）。想要旧的硬失败行为：`H3_CHARACTER_SWAP_SAM31_WEAK_ASSOCIATION=abort`。

**留档**：neca_6 的 R1 框已换成成片包络 `[0.14,0.105,0.685,1.0]`（备份 `director_project.h3director.json.bak_pre_r1_take_box_20261108`；绑定 `R1 → P2`、`R2 → P1` 未动）；R2 的框保持 Design 给的 `[0.45,0.2,0.85,0.9]`，它 V1 侧 0.7796/margin 0.3278 是干净的，问题只在成片侧的 SAM。DETECT V1 PEOPLE 那次弹窗是本地 LM 模型回传错 `media_id`（程序只期待短代号如 `V1`，一批错就整扫中止且这一类没有重试），只影响"人物检测"这个可选步骤，没有写入任何数据。

### 把 SAM3.1 关联判分搬到生成之前：一个不合格的框不再赔 20 分钟 —— Round 102 / policy 98（2026-11-08）

**现场**：同一个 13.975 s 走廊双人 chibi（V1 `V1_afdecd120d74_…`），两个项目各赔掉一整枪。`godzilla_action_figure_by_neca_5` 在 19:00 与 19:29 两次弹「SAM3.1 weak association — manual box required」，分数 **R3 0.36**、**R3 0.31**，manifest 里 `segment_001_000000000_000013975` 状态 `failed`、`master_output: null`。`godzilla_action_figure_by_neca_6`（导演重做 Design 后的新台账：`R1 → P2`、`R2 → P1`）在 21:17 同样失败，**R1 0.52**；ComfyUI 日志把成本写得很清楚：`H3 video prepared width=960 height=512 frames=334` → SAM3.1 载入 → `tracking: 345/345` → `Prompt executed in 52.58 seconds` —— **全部跑完才判分**。

**读码定位（这次跟前一天的 neca_4 根本不是同一条路径）**：

1. 判分式与下限：`score = IoU(SAM 剪影框, 角色框) × 0.65 + 中心接近度 × 0.25 + 面积比 × 0.10`，每个采样时刻取最好的一帧，**取最好的 ≤8 帧平均**（`smart_render_worker.py:5609-5652`），下限是硬编码常量 `SAM31_MIN_MATCH_SCORE = 0.7`（`516`，Round 69 第 4 项：软关联会把新人物合成到别人身上）。低了就抛 sentinel，而调用点对它是**原样上抛、不走 delta-mask 退路**（`6554-6555`）⇒ 整段 `failed`，且是在生成已花掉之后。
2. 分数**只在角色自己的追踪区间内测**（`ranges` ±0.26 s，`5616-5620`）。neca_5 的 R3 只有三个头窄条（`[0.48,0.42,0.56,0.65]` 只有全画面 **1.8 %**；3.1667 s 的 `[0.68,0.2,0.78,0.45]` 比人实际位置**偏右约 0.10**，实测她 0–4 s 稳在 x 0.44–0.68、y 0.13–0.63）⇒ 0.31。
3. neca_6 更极端：两个 pass 的 `composite_track_samples` 都是 **0**、`composite_time_ranges_seconds` 是**空**（无轨迹的角色被标成"只有空间范围"，`director_cut_studio.py:38484-38496`）⇒ 关联退化成"一个静态框 vs 全部 345 帧"，而 Design 给的框 `[0.25,0.3,0.45,0.7]` 面积只有 0.0800，实测她在三种景别的剪影面积是 **0.106（0–3.5 s）／0.436（3.5–6.8 s）／0.220（6.8–14 s）**，三种景别对着原框算分是 0.4196／0.3591／0.3323，**全灭** ⇒ 实测 0.52 就是"最好 8 帧"的平均。
4. 为什么 neca_4 从来没遇到：它只有**一个**替换，manifest 里 `character_swap_composite = {}` ⇒ **多角色 SAM 合成这条路径（`independent_role_mode`，`6523-6540`）整条没跑**。第二个替换角色带出来的新关卡。
5. 关键发现：worker 本来就要对 V1 跑一次同样的判定 —— `queue_sam31_v1_role_masks` 内部调的就是 `match_sam31_masks_to_passes`（`5886`），只是排在生成之后。

**修法（Round 102，搬测量而不是加测量）**：

- `preflight_sam31_role_association(job, segment, passes)` 在**排第一个 take 之前**跑（插在 `independent_role_mode` 判定之后、pass 循环之前；`resume_active` 时不跑，那一枪已经在飞）。弱关联当场抛回同一句 sentinel（前缀不变，所以调用点的"不走退路"仍然命中）并加一句「Measured on the V1 plate before generation, so no H3 take was spent；重画框或降 `H3_CHARACTER_SWAP_SAM31_MIN_MATCH_SCORE`」。
- **预检不是额外开销**：它的 V1 mask bundle 交给合成阶段复用（`if sam_preflight_v1_bundle is not None` 两处：合成处与 OOM 重试处），于是比它取代的次序**少一次上传、少一次 345 帧追踪**。
- 它只是**必要条件**：H3 保持 plate 的 blocking，所以连源剪影都匹配不上的框，更不可能匹配盖在上面的替换剪影（后者只会更大更异形）；生成之后 Round 69 那道门照旧还在。
- **辅助件不得杀死渲染**：只有 sentinel 会中止；SAM 缺失／OOM／找不到实例／上传被拒都是"记录并忽略"，合成阶段照旧重新排队（等于 policy 97 的行为）。
- manifest 新增 `character_swap_composite.sam31_preflight = {mode, floor, before_generation, verdict, detail, matches, v1_prompt_id, reused_by_composite}` 与 `sam31_v1_masks_reused_from_preflight`，`verdict ∈ on/advisory/off` 对应 `trusted／weak／weak_advisory／unavailable／skipped`。
- 两个旋钮都进 `DESIGN_ENV_RENDER_KNOBS`（`director_cut_studio.py:445`）：`H3_CHARACTER_SWAP_SAM31_MIN_MATCH_SCORE`（默认 0.70，夹到 [0.05, 1.0]，junk／NaN／`7` 都有明确归宿）与 `H3_CHARACTER_SWAP_SAM31_ASSOCIATION_PREFLIGHT`（`on` 默认／`advisory` 只记录不拦／`off` 恢复 97 的次序）。Round 34／96／97／101 写过同一条笔记：**导演设不了的旋钮等于没有旋钮**。
- **policy 97 → 98**：本轮不改任何编译产物（prompt、plate、QC 措辞都没动），但"什么时候允许判失败"是渲染行为，且下限现在可读 env，所以两侧同号抬到 98。代价：各项目的段会重新判定一次（旧的 accepted take 仍按 take 状态留着，Preview 时脏段会重跑）。

**用这套东西实测出来的两个框（同一条公式反解，不是猜）**：neca_5 的 R3 用 `[0.435, 0.12, 0.705, 0.68]` —— 对四种可能剪影尺寸的**最坏**分数 0.7222（0.7222／0.8413／0.9490／0.7277），初版 `[0.43,0.11,0.72,0.70]` 的最坏只有 0.6657；框再放大一档面积 0.405 就会把中景档拉到 0.649 直接不合格，**框面积必须落在众数剪影面积的约 1.3 倍以内**。neca_6 的 R1 用 `[0.02, 0.15, 0.38, 0.95]`，对帧数最多的中景档 **0.8159**（面积 0.288 ≈ 0.220 的 1.31 倍）。两次都顺手把压制窗口抬到 0.2333／0.3826（此前 owner-shot 的追踪框只有 0.094），并让两个替换的审计框不重叠（x 0.02–0.38 vs 0.45–0.85；neca_5 是 0.28–0.42 vs 0.435–0.705）—— 就是前一天那条"混脸"经验的正面用法。

**测试**：新增 `testing\test_round102_sam_preflight.py` **16 项全绿**（夹取与 junk／NaN、`0.52/0.31/0.36` 三个真实数字都可达、下限在抛错处生效且打印自己、`on/advisory/off` 三档、只有 sentinel 会中止、bundle 原样返回、预检排在 pass 循环之前、合成与 OOM 重试都复用 bundle、Round 69 那道门仍在、policy 98 与两侧同号）。回归：`test_smart_render_worker` 48、`test_round69_manual_parity` 102（两条 wiring 断言已随新写法更新，policy 断言 97→98），其余相关套件见本轮 Verification。

**给导演的可复用规矩**：① 只需要换一个角色时，把另一位设 `KEEP_V1` ⇒ 多角色 SAM 路径整条不激活（neca_4 就是证据），这类弹窗物理上不会出现；② 手动切／改 shot 之后**每个 shot 各点一次 DETECT V1 PEOPLE**，有逐帧样本后分数只在各自时段内、用逐时刻框去比，IoU 天然高（neca_5 的 R2 那次能过就是走这条路）；③ 要换两个角色时，**框按公式反解**：面积 = 众数剪影面积的 1.0–1.3 倍、中心贴众数位置，两个角色的审计框不许重叠；先看 manifest 的 `sam31_preflight.matches` 与 `sam31_role_matches` 的真实分数，再决定要不要动 `H3_CHARACTER_SWAP_SAM31_MIN_MATCH_SCORE`。

**留档**：neca_5 备份 `project\director_project.h3director.json.bak_pre_r3_box_20261108`／`…bak_pre_r3_box_tune_20261108`，neca_6 备份 `…bak_pre_r1_box_20261108`；脚本 `_dsh_verify_13\godzilla\{author_r3_box_neca5, tune_r3_box_neca5, author_r1_box_neca6}.py`；量框格子图 `_dsh_verify_13\godzilla\{r3_gate_times, r1_all_times}.png`（0.05 网格）。


### 一个段里塞多个 shot，压制窗口与身份审计就会混脸：合并成一个 shot 才通 —— godzilla 项目实机经验（2026-11-08，**零产品码；policy 97 不变；影片已实机验证＝一次过 accepted**）

**现场**：`example\godzilla_action_figure_by_neca_4`，V1 = 13.975 s 走廊双人 chibi，P1 = NECA 哥斯拉 2014 **全身**手办。导演把原来的一整条 shot 手动切成 S1／S4／S2／S3，之后连开四枪都不干净：10:01 的 `preview_…1794102924493438800`（窗口仍等于框、`hair_halo.applied = null`）、11:42（最差样本 0.139962）、13:24（seg2 过、画面错人）、13:54（seg2 跑两次、样本 0.39–0.51 `blocking target_reference_similarity`，11.5 s 出**两只哥斯拉**，9.0／10.0／13.0 s 换了**错的人**）。

**三条根因，全部读码定位，不是框画错**：

1. **一个段只有一个压制窗口，且由 owner shot 代表整段。** `director_cut_studio.py:40137-40144` 写明"若取整后仍有多个候选，用占据本窗口最大那块的那个 shot，别让邻居的编辑漏过来"；段内其余 shot 只贡献 scene 级条目（`40198-40208`）。0–8.5 s 段里 S2 占 4.0 s > S1 的 3.0 s > S4 的 1.5 s ⇒ **owner = S2**，实测 10:01 与 11:42 两次发的都是 S2 的框，导演在 S1／S4 画的框从头到尾没参与。
2. **手动切 shot 之后，角色台账仍是整视频那一份。** "DETECT V1 PEOPLE" 按钮本身是按 shot 扫的（`26403-26404`：`start = cue.start_seconds`、`end = cue.end_seconds`），但它启动时先把 `v1.semantic_enrichment` 里全视频分析出的 `principal_roles` 当作 `known_roles` 读进来（`26413-26421`），渲染规划又从全局 `principal_roles` 出发（`40146-40151`）；shot 局部结果会被优先覆盖（`40152-40157`）。⇒ **切完 shot 必须每个 shot 各点一次 DETECT V1 PEOPLE**，否则那个 shot 身上带的还是旧的整视频轨迹。
3. **同一段里对同一个人给了打架的指令。** S3 里 R2 要被换成 P1，而 **R3 = `KEEP_V1` 的框 `[0.5347, 0.3148, 0.6847, 0.7148]` 正压在同一张脸上**（R3 与 R2 是同一位演员）；一边保护一边替换 ⇒ 特写那帧两只哥斯拉、宽景那几帧换错人。另外框宽 `1.0 > max_box_width 0.60` ⇒ halo 整条关闭，而审计框 x 0–1.0 **同时装进两张脸**，相似度必然卡在 0.4–0.5 这种混脸区间，与生成质量无关。

**终局修法（纯项目数据，零产品码）**：删掉 S4／S2／S3，把 S1 扩成 `0.0 → 13.98`；`source_role_swap_selection = ["R3"]`、`R1／R2 = KEEP_V1`、`R3 = P1`、唯一人工框 `[0.42, 0.02, 1.00, 1.00]`（宽 0.58 保持 halo 开启，上探 `min(0.5 × 0.98, 0.18) = 0.18` ⇒ 窗口上沿 0.0000 盖住 11.5 s 怼镜头那帧的 0.02 发顶；share 0.85 ⇒ 下沿 0.8530 在所有下巴之下）。同时清空所有按 shot／段 存的历史，杜绝"其实是复用旧 take"：`shot_take_states`、`segment_take_states`、`render_dirty_*`、`render_isolated_shot_ids`、`smart_render["segments"]`、`smart_render_manifests = {}`（最后这一项正是 `project_integrity.py:845` 的做法）。

**实机一枪（16:10:53，policy 97）**：`segment_001_000000000_000013975`（写入的 13.98 被吸附到整帧）、`shots ['S1']`、**attempts 1**、`passed True / blocking False`、samples **0.519434／0.513282／0.472579**、`hair_halo.applied[0].top = 0.0`、`bbox_provenance = manual_shot_override` ⇒ 用 `up_max 0.18`（`up_max_masked 0.06` 在册、只给描边框）、`head_band_bottom 0.853`、`suppressed_frame_area 0.4947`。面积比手算的 0.6014 少 0.11，是两个 `KEEP_V1` 角色的**自动轮廓把窗口左缘切掉了** —— Round 101 那条描边路径在替我们守旁白。读帧七个采样点（1.5／3.5／5.0／6.5／9.0／11.5／13.0 s）一致：右边那位每格都是哥斯拉（11.5 s 哥斯拉也正对镜头张嘴，动作连续性保住），左边金发与南瓜灯始终是原小孩。

**当轮生效旋钮**（`design_ai.env`）：`MEDIUM_SILENT_HEAD_BAND_SHARE=0.85`、`PLATE_SUPPRESSION=1`、`HAIR_BAND_MODE=blur_desat`、`MEDIUM_SILENT_WARDROBE_BAND_MODE=off`、`FIGURE_WIDTH_SHARE=1.0`、`HAIR_HALO_UP_MAX_MASKED=0.06`（出厂 `up_max 0.18`）。**0.85 是为了近景推镜**：`0.45` 在框下沿被画面边夹住时只能到 `top + 0.45 × (1 − top)`，实测 0.5641，够不到 0.68–0.78 的下巴。

**可复用的三条规矩**：① 切 shot 之后**每个 shot 都要各点一次 DETECT V1 PEOPLE**；② **同一个段里的多个 shot 不要画互不相同的框**——只有 owner shot 那条会真的发出去，其余的是装饰，非要各画就得让段边界 = shot 边界；③ 一个角色要换、另一个要留，就保证**整段指令一致**，别在同一段里出现 `KEEP_V1` 与 `P1` 指向同一张脸。

**留档**：成功配置快照 `project\director_project.h3director.json.SUCCESS_single_shot_20261108`（四级回退链 `…bak_pre_box_authoring_20261108`／`…bak_pre_restore_s3_r3_20261108`／`…bak_pre_s3_fix_20261108`／`…bak_pre_merge_into_s1_20261108`）；探针与作者化脚本 `_dsh_verify_13\godzilla\{why_no_effect, author_boxes, restore_s3_r3, fix_s3, merge_into_s1}.py`，对帧图 `_dsh_verify_13\godzilla\{ab_source_vs_output, windows_on_source, now_after_redraw, authored_boxes, shot1_check, s3_source_vs_output, success_source_vs_output}.png`。

### 让自动描边框只探到头发为止：halo 的上探量成为文件可写的旋钮，并按"谁画的框"分档 —— Round 101 / policy 97（2026-11-08）

**背景**：Round 100 之后导演问"那用自动描边的框是不是最完美"。读码答案是一半对：**左右边界和"要保住的人"上自动描边几乎一定更好，但上下边界会精确复现帽子**，因为窗口上沿 = `box_top − min(0.5 × 框高, 0.18)`，而这条公式假设框上沿已经比发顶低约 0.18；掩码框的上沿正好压在发顶上，于是又凭空多出 0.18 的空白画布。

**①（管道，零行为变化）**：`DESIGN_ENV_RENDER_KNOBS` 现在收了 7 个名字——`H3_CHARACTER_SWAP_HAIR_HALO`（总开关，真正的回滚手段）、五个出厂几何名（`UP_SHARE / UP_MAX / WIDTH_SHARE / WIDTH_MAX / MAX_BOX_WIDTH`）、以及新增的 `H3_CHARACTER_SWAP_HAIR_HALO_UP_MAX_MASKED`。这正是 Round 34／96／97 三段注释都提过的坑：不调它就得导出启动变量才能测。模块在 import 时先应用 `design_ai.env`（[director_cut_studio.py:552](#L552) 在参数表之前），所以改文件要**完全退出并重开 Studio**。

**②（分档）**：`character_swap_engine` 在角色行上写 `source_bbox_provenance = "manual_shot_override" | "auto_contour"`（判据就是已有的权威判定 `role in bbox_overrides`，[character_swap_engine.py:1884-1895](#L1884-L1895)），并把它加进分组时的键白名单（[2030-2040](#L2030-L2040)）——第一版没加，测试立刻 `KeyError` 抓到，这正是 pass 行的真实来源。studio 侧 `_hair_halo_parameters_for_provenance()` 只对 `auto_contour` 换上较短的 cap，且该 cap **只能缩短不能加长**（读值时 `min(up_max_masked, up_max)`）；缺键（本轮之前编译的所有 ledger、合并行、离线探针）一律按手画框处理。报告里每条 `hair_halo.applied` 现在写 `bbox_provenance` 与真正生效的 `up_max`，所以判过的 take 能自证走的哪条臂。

**出厂值 = 现值**：`up_max_masked` 默认 0.18 ＝ 手画框的 cap ⇒ 什么都不变。`design_ai.env` 里本轮**装上 0.06**（≈plate 在 366 px 高时 18 px boxblur 的扩散量级 0.049：够过渡、不够塞物体）。

**实测（用真实 `design_ai.env` 跑 `_dsh_verify_13/verify_round101_knob.py`）**：`up_share 0.5 | up_max 0.18 | up_max_masked 0.06 | max_box_width 0.6`；Hallway S3 那个手画框 `[0.0, 0.264815, 0.412541, 0.996296]` 的窗口上沿仍是 **0.084815**（与已判过的 take 一致），S1／S2 仍是 **0.029259** ✓；同一个框若换成自动描边来源，上沿变成 **0.204815**，正好压在实测发顶 y 0.25 上方 0.045 ⇒ 没有画布可填。（宽度这里显示 0.481435 是脚本没传 `protected_boxes` 的未截断值，实盘仍被 R1 近边截在 0.435254。）

**测试**：round69 **102**（新增 allowlist 装载＋优先级、掩码 cap 默认/夹紧、provenance 分档，并用 S3 真实框钉住 0.084815 ↔ 0.204815）；closeup gates **79**（新增一条跑真过滤镜链：同一个框，手画 ⇒ `ih*0.08000000`、自动 ⇒ `ih*0.20000000`，并断言报告里的 `bbox_provenance` 与生效 `up_max` 0.18／0.06）；engine **20**（新增来源标记两条）。worker 48／routes 48／background_extra 9／round54 18／round57 18／round65 20 全 OK。policy 96 → **97**（两边同步），plate token 只在装了旋钮的 Project 变，prompt 与策略后缀不动。

**给导演的用法**：手画框＝你要控制窗口 ⇒ 保持 0.18；自动描边框＝它已经贴着头发 ⇒ 现在只探 0.06。**要保住的角色（KEEP_V1）永远用自动描边**（截断线精确到脸边），要换的角色若不想画框，自动描边现在是安全的。一段里有多种构图仍然要切 Segment——窗口每段只有一个矩形，这是 Round 98 就写过的限制。


### 秃顶上长出一顶车长帽：halo 的 +0.18 在头顶上方留了一块空白画布 —— Round 100 / policy 96（2026-11-07）

**背景**：Round 99 的框修正后，23:24:48 的运行（policy 96，seed 7196324238162326563）导演判**完美**，数字同向：S3 采样 **0.637863 / 0.539404 / 0.503147**（上一版 −0.012201），两段都 `blocking=False`、`failure_class` 空。唯一残留缺陷：**shot 3 里 R2 的秃顶上出现一顶"黑＋红边＋白五角星徽"的车长帽**，从 8.5 s 持续到约 12.1 s，12.20 s 起自己消失（`_dsh_verify_13/hat/hat_boundary.png`）。

**机制（可复算）**：窗口上沿 = `box_top − min(0.5 × box_height, halo up_max)`，出厂 `up_max = 0.18`（`_hair_halo_parameters()`，line 1637-1638）。实测两段都精确卡在 0.18 的封顶上：S1/S2 `0.209259 − 0.18 = 0.029259` ✓、S3 `0.264815 − 0.18 = 0.084815` ✓。而 S3 里被替换角色（左边那位）的**真实头顶在 y ≈ 0.25**，且三种构图都一样（0.05 网格实测 9.12 / 11.21 / 13.10 s，`src_fine_crowns.png`）——也就是说这个框的上沿只比头顶高 0.015，halo 再加 0.18 之后，窗口上沿落到**头顶以上 0.165 的纯背景**里。H3 要把整个模糊窗口重画，于是从这块无特征带的**顶边**往下补出一个物体：帽顶与窗口上沿 y 0.0848 齐平、帽檐收在 y ≈ 0.26 ≈ 真实头顶（`ab_10.60s.png` 里黄框上沿正好压在帽顶上，就是这个签名）。
S1 / S2 从来没有帽子，因为它们的框上沿本来就画在头顶以上约 0.18（特写里秃顶顶到画面边），halo 落地时正好贴着真实头顶，没有余量。

**规则（值得记住的一般结论）**：**人工框的上沿要放在"真实头顶往下约 0.18"**，因为窗口会自动向上长 `min(0.5 × 框高, 0.18)`；框上沿贴着头顶画，就等于在头顶上方凭空造一块画布，H3 一定往上填东西（Round 96 是填头发，这次是填帽子）。

**修法（GUI，不动代码）**：S3 的 R2 框 x 不变（0–0.44），改成 **top y 0.40 / bottom y 0.85**（框高 0.45 ≥ 0.36，所以 0.18 的向上生长仍然成立）⇒ 窗口变成 **y 0.22–0.60**：头顶 0.25 上方只剩 0.03 的余量，窗口下沿 0.60 与今天一致；示意图 `_dsh_verify_13/hat/guide_s3_box_fix.png`（黄＝今天的窗口、绿＝建议窗口、青＝要画的框）。改完重跑该段角色分析（`character_swap_manual_align = false`，追踪样本只会复制手画框）。

**env 路线为什么不走**：`up_max` 有旋钮 `H3_CHARACTER_SWAP_HAIR_HALO_UP_MAX`，但它**不在 `DESIGN_ENV_RENDER_KNOBS` 名单里**（本轮 grep 确认：全文件只有参数表那 5 个名字＋开关 `H3_CHARACTER_SWAP_HAIR_HALO`），写进 `design_ai.env` 不会生效——和 Round 96 那两个失效行是同一个坑。即便加进名单再降到 0.03，实测算出来的窗口上沿是 S1 0.2269、S2 0.1684（今天 0.0769 / 0.0184），而 S1/S2 的秃顶顶到 y 0–0.05，**窗口会盖不住头顶**，Round 94 的假发就会在特写里回来。所以按框修是正解；真要全局调，得先把旋钮加进名单。

**另外**：帽子不碰 prompt 是刻意的——Round 69 的禁名词表早就证明"点名即画物"（`wig / crown / ribbon / belt…` 全是点名后长出来的），`hat / cap / badge` 同理，只能靠几何。本轮源码与 `design_ai.env` 均未改（policy 仍 96）。Project Format 仍是 29。

**导演实测后的补充（23:44:32，同 seed 7196324238162326563）**：导演把框画成 `[0.004237, 0.312963, 0.395592, 0.774074]`（比我建议的 top 0.40 高了 0.087），公式实测完全吻合：上沿 `0.312963 − min(0.5 × 0.461111, 0.18) = 0.132963`、下沿 `0.312963 + 0.45 × 0.461111 = 0.5205`（manifest 报的正是 0.5205）、面积 0.1472（旧 0.2216）。**帽子在画面上消失**，导演判成功。代价也要记下：窗口变小之后 `target_reference_audit` 采样掉到 0.451346 / 0.444486 / 0.370688、S3 变成 `blocking = True`，最可能是窗口外那缕肩旁黑发现在落进了审计框；要连应用的判定一起过，就按口诀把框下沿放到 ≈0.85（窗口下沿到 0.60）。**更正一条早期表述**：Round 98／99／100 里写过"`character_swap_manual_align = false`，所以追踪样本只会逐条复制手画框"——那句的因果记错了。读码后确认：`character_swap_manual_align` 是 **prompt 路线开关**（Route 3 vanilla ↔ Route 2 hand-built，见 [director_cut_studio.py:11934-11950](#L11934-L11950)），与框的来源无关；手画框之所以盖住 SAM 自动轮廓，是因为 `source_role_bbox_overrides` **对该 Shot 是权威的**（`position_source = "manual_shot_override"`，[26055-26075](#L26055-L26075)），证据裁剪的优先级同样是"手画框 > 证据框 > 角色框 > 全幅"（[25765-25771](#L25765-L25771)）。所以"重跑角色分析"仍然要做（它刷新审计框与保护框），但样本 bbox 全都等于手画框是 override 生效的证据，不是分析没跑。另外 S1 / S2 本轮是 `status = cached`，它们显示的 0.611845 / 0.536828 / 0.512872 是复用上一版的数，不是新渲染。


### shot 3 的两个角色对调：R1 / R2 的人工框装反了人 —— Round 99 / policy 96（2026-11-07）

**症状**：22:45:53 的运行（policy 96，seed 8673885238750441854）里 shot 3（S3，8.5–13.98 s）**两个角色位置互换了**：成片里 P1 在右、被保留角色的长相跑到左边，与源片相反。导演要求查原因。

**原因（设计文件里就能读出来）**：`director_cues[cue_id=S3]` 是唯一一个带显式选择的人工 shot——`source_role_swap_selection = ["R2"]`、`source_role_identity_overrides = {"R1": "KEEP_V1", "R2": "P1"}`，而它的两个 `source_role_bbox_overrides`（4 元组是 **[left, top, right, bottom]**，不是 width/height，两个框宽度都是 0.319）是：

| 槽 | 框（帧内归一化） | 实际套住的人（用源片 9.12 / 11.21 s 实测） |
|---|---|---|
| R2 → P1（要替换） | x 0.065–0.384 / y 0.343–0.854 | **左边的 blonde 角色**（应当保留） |
| R1 → KEEP_V1（要保留） | x 0.505–0.824 / y 0.187–0.776 | **右边戴眼镜的黑发角色**（P1 一直替的就是她） |

即应用被明确告知"替换左边、保留右边"，与整条流水线的既定目标相反，成片就是设计意图的**转置**（`_dsh_verify_13/shot3/ab_src_vs_out_11.21s.png`）。S1 / S2 不受影响，因为它们的 `source_role_swap_selection` 是**空表**，走的是全局配对——只有 S3 有人工选择＋人工框，所以只有它会被人装反。

**同一个根因解释了 Round 98 的全部遗留现象**：S3 的身份审计 `bbox_normalized` 是 `[0.141553, 0.352815, 0.3076, 0.577704]`（＝R2 那个错框的派生），本次 `correlation = -0.059248`、`similarity = -0.012201`、`mae = 0.57424`、采样 0.218416 / 0.263815 / 0.216306——应用一直在拿**左半边**（那里根本不是 P1）去和 P1 比，所以 0.346 / −0.012 这类数字以及 `target_reference_similarity` 的 blocking 全是同一错框的假信号；上一版的恒定灰雾也是这个框把窗口糊在了 blonde＋背景上。

**修法（不需要改代码）**：在 GUI 里把这两个框**互换**——R2（→P1）画到右边那位（建议 x 0.42–1.00 / y 0.10–1.00，广角与特写两种构图都罩得住，左沿不要小于 0.43 以免削到 blonde），R1（KEEP_V1）画到左边（x 0.00–0.42 / y 0.25–1.00）；标准答案图 `_dsh_verify_13/shot3/guide_s3_target_boxes.png`（绿＝R2、青＝R1，带 0.1 网格）。改完**重跑该段角色分析**：`character_swap_manual_align` 仍是 `false`，所以 `composite_track_samples` 只会逐条复制手画框（本次 S3 那 5 条样本 bbox 完全相同就是这个原因）。窗口会跟着 R2 的框走，所以身份抑制 plate 的缓存 token 会换、第一次 Preview 要多一点 plate 时间。

**记录**：`design_ai.env` 与源码本轮**未改**（policy 仍 96，头带 0.45、衣服带 off、plate 压制仍开）；本轮是把 Round 98 的"证据缺失"结论推进到"证据装反了人"。顺带修正一条读法：`source_role_bbox_overrides` / `source_bbox_normalized` 一律是 `[left, top, right, bottom]`，按 width/height 去加会得出 x>1 的假越界。Project Format 仍是 29。


### 雾化的方块：压制窗口画在一个没有追踪证据的旧框上 —— Round 98 / policy 96（2026-11-07）

**症状**：21:20:14 的运行（policy 96，seed 3744612034463707918，头带 0.65）画面左上方出现一块**恒定的灰色雾矩形**。导演判定"越来越差"。

**数字却是分裂的**：unit 1 拿下**至今最好的身份**（0.593377 / 0.544791 / 0.531572，中位 0.544791，`blocking=False`，面积 0.2618 与算好的完全一致），unit 2 掉到 0.346262 / 最坏 0.329643 且 blocking。

**根因（带名字的缺陷）**：窗口的依据本该是 pass 里的 `composite_track_samples`，而本次 manifest 里——

| | `composite_track_samples` | 合成框 |
|---|---|---|
| segment_001（0–8.5 s） | **4 条，四条 bbox 完全相同** `[0.19839, 0.209259, 0.541017, 0.898148]`，**最后一条只到 4.5 s** | 与手画框一模一样（`character_swap_manual_align = false`） |
| segment_002（8.5–13.975 s） | **空列表：0 条** | `[0.15, 0.3, 0.45, 0.75]`，凭空 |

把框画回画面就一目了然（`_dsh_verify_13/box_proof/u2_11.21s.png`、`seg2_strip.png`）：segment_002 的 8.4–11.9 s 里 **P1 一直在右半边并逐渐推近**，那个框却始终钉在左上，罩住的是**被我方保留的 blonde 角色＋背景**——雾就是那个窗口的形状（`_dsh_verify_13/box_proof/u1_7.48s.png` 里 segment_001 的框仍套在人身上，所以它 0–7.5 s 是对的）。

**两个后果，都必须记下来**：
1. 0.65 的窗口把这块**错位**的雾从 y 0.03–0.52 放大到 y 0.03–0.657 → 导演看到的是"越来越差"。所以 `H3_CHARACTER_SWAP_MEDIUM_SILENT_HEAD_BAND_SHARE` **退回 0.45**（=19:22 那张 plate，一字不差）。头带这一档本身没错（unit 1 的历史最好成绩就是它跑的），错在窗口落点。
2. **unit 2 的 blocking 是假阴性**：`target_reference_audit` 在 `bbox_index 0` 上采样，而那个框里没有人——它量的是被保留的角色，所以 0.346 / 0.287 那批数字不能当缺陷判据。画面里 segment_002 的 P1 是**合格**的（秃顶、无头发、黑背心白边、黄裤）。修好框之后这个 verdict 才有意义。

**修法排序**（都不需要改代码）：①在 GUI 里把 segment_002 的框画到右边那个秃顶角色身上（8.4–11.9 s 他大致占 x 0.42–1.0）；②这段内部还有一次构图切换（约 10.2 s 广角→特写），切成两段各自给框；③重跑该段角色分析，让 `composite_track_samples` 不再是空表——空表就等于应用在猜。可选的代码保护（未做）：让 plate 只在**有追踪样本的时间段**画窗口（ffmpeg `enable='between(t,..)'` 逐样本时间门），错框就再也糊不到无证据的帧。

**改动**：`design_ai.env` 一行（`..._HEAD_BAND_SHARE` 0.65 → 0.45，注释里记下实测与备份 `design_ai.env.bak_pre_head_band_share_20261107`）；**无源码改动**，版本号仍是 96，`test_round69_manual_parity` 100 项、`test_character_swap_closeup_gates` 78 项在退回后仍通过（这两个套件都在 import 前把该旋钮钉成 0.45，项目侧改档不会串味）。Project Format 仍是 29。


### 衣服带把头发又养回来了 —— 回退 + 只把头带下探 —— Round 97 / policy 96（2026-11-07）

**症状**：policy 95（衣服带 `blur` + `FIGURE_WIDTH_SHARE=1.0`）连跑两次——19:56:44 seed 5474034667317928853、20:14:09 seed 8564544838065224999——导演判定**素质比 19:22 那次差**。应用的数字站在导演一边：

| | 19:22（policy 94，band off） | 19:56（95） | 20:14（95） |
|---|---|---|---|
| unit 1 三个采样 | 0.646862 / 0.527920 / **0.513452** | 0.436376 / 0.377449 / 0.425890 | 0.547096 / 0.509834 / 0.485234 |
| unit 1 | **blocking=False** | blocking `target_reference_similarity` | blocking `target_reference_temporal_collapse`（attempts 2） |
| unit 2 中位／最坏 | 0.486057 / 0.473436 | 0.527253 / 0.342157 | **0.325397 / 0.287048** |
| 画面 | 只剩下颌旁一缕发、后颈几撮黑刺 | 头发大量回归 | **4.23 s 黑发披到肩、11.21 s 秃顶被刘海盖住** |

**机制**（`_dsh_verify_13/hallway_frames7/run2026_*.png`）：衣服带把 `y 0.519259–1.0`（40.48 % 画面）糊掉之后，plate 里**没有脖子也没有领口**，H3 只能按 V1 的动势在模糊上重建头发——正是 Round 46 那条"糊掉的衣服会重新播种原服装"的教训，只是搬高了一个区域。`wardrobe_audit.shift` 确实被推上去了（unit 1 的 0.037728 → 0.050275、late 0.132449），代价全落在身份相似度上。**所以衣服带回退。**

| 位置 | 内容 |
|---|---|
| `design_ai.env`（备份 `design_ai.env.bak_pre_head_band_share_20261107`） | `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off`（**回到 19:22 的 plate**，`FIGURE_WIDTH_SHARE=1.0` 留着但不生效）；新增 `H3_CHARACTER_SWAP_MEDIUM_SILENT_HEAD_BAND_SHARE=0.65` |
| 新旋钮（`director_cut_studio.py:1405` 起的读取器 + `:37150` 的 silent-listener 分档 + allowlist） | silent listener 身份窗口占作者框的高度比例，出厂 **0.45**（policy-66 的 plate），`0.05–1.0` 之外回落；只动 `medium_silent` 一档，`dominant` 0.62 / `head_dominant` 0.30 的字面量不变 |
| 版本号 | 两处 `SMART_RENDER_POLICY_VERSION = 96`——plate 窗口变了，policy 95 那两个变差的 take 不再被复用 |

**为什么这条是窄路**（按本 manifest 真实输入重建 plate，`_dsh_verify_13/band_headshare065.json`、A/B 图 `_dsh_verify_13/headshare_ab/ab_*.png`）：

| | 19:22（0.45） | 本档（0.65） | 衣服带档（已回退） |
|---|---|---|---|
| unit 1 头带下沿 | y 0.519259 | **y 0.657037** | y 0.519259 + 衣服带到 1.0 |
| unit 2 头带下沿 | y 0.5025 | **y 0.5925**（黑刺就在 0.50–0.59） | 同上 |
| 压制面积 | 0.2043 / 0.1339 | **0.2617 / 0.1654**（截到受保护近边；探针未传受保护框时 0.2869 / 0.1891） | 0.3971 / 0.2521 |
| prompt | 19:22 原样 | **一字不变**（无 clause、无后缀翻转） | 换 plate clause + 后缀 |

它的 x 列本来就被受保护角色近边截在 0.558136，所以糊不到她：重建帧里她的眼睛／眼镜／嘴都在窗外，而下颌以下的浅色发缕与头侧后颈那圈进了窗口。**顺带量到一条真实行为**：crown 切片是身份窗口的 42 %，窗口长高它跟着长——unit 1 的 crown 由 0.2058 长到 0.263667（`blur_desat` 的抽色区因此也更往下盖一层头发，这正是要的效果）。

**测试**：`test_round69_manual_parity` 100 项通过（新增读取器桩：默认 0.45、显式值生效、`""`／`0.0`／`0.04`／`1.5`／`blur`／`None` 全部回落；allowlist 名单加到 5 个名字；本模块 import 前多钉一个键）；`test_character_swap_closeup_gates` 78 项（新增 plate 桩：0.45 → 下沿 0.512、0.65 → 下沿 0.624、crown 0.22848、face 0.31552、wardrobe 从 0.624 起、ffmpeg 图里出现 `ih*0.22848000`/`ih*0.31552000`/`ih*0.37600000`；首版桩把 crown 当成定值，实测 0.22848 后按真实行为改正）；`test_smart_render_worker` 48；`test_round52_swap_routes` 48；`test_round54/57/65` 18/18/20 —— 共 **330 项通过**；五个文件 `py_compile` 通过。Project Format 仍是 29。



### 头发归属句子起效了，残余穿崩在头带下沿之下 —— Round 96 / policy 95（2026-11-07）

**验收 19:22:39 那次（policy 94，seed 1689239479428983434）**：Round 95 的词真的起了作用。

| | 18:20（policy 93） | 19:22（policy 94，只换词） |
|---|---|---|
| unit 1 三个采样 | 0.649080 / 0.538907 / **0.459285** | 0.646862 / 0.527920 / **0.513452** |
| unit 1 判定 | blocking，cause `target_reference_temporal_collapse`，attempts 2 | **blocking=False，cause=None**，attempts 1 |
| unit 2 | 中位 0.491569，最坏 0.382527 | 中位 0.486057，最坏 0.473436 @ 局部 2.708 s |
| 画面 | 黑鬃毛 + 一条辫子 + 发绳 | **鬃毛、辫子、发绳全部消失**，P1 五官/背心接近原图 |

**残余病灶（只剩一窄条）**：4.23 s 与 6.60 s 下颌旁垂下来的一缕浅色发、11.21 s 头侧与后颈的几撮黑刺——全部在 `y 0.50–0.66`，也就是头带下沿（unit 1 `0.5193` / unit 2 `0.5025`）**下方一步**。两个单元的 `wardrobe_audit` 一直在指同一处：**"the V1 wardrobe still fills the upper half of the body region"**（shift 0.037728 / −0.039443，required 0.047239 / 0.048380），而 `wardrobe_mode` 仍是 `off`。

**顺带记下一条度量口径**：unit 2 的 `wardrobe shift` 变成 −0.039443 并不是"衣服更错了"——11.21 s 时该单元的 QC 框 `[0.15, 0.3, 0.45, 0.75]` 同时罩住了 P1 小人 **和** 被保留的戴眼镜角色（她占 x 0.42–1.0），所以这个数在画框跨人时不可用作缺陷判据；画面里那件黑背心＋白边＋蓝袖是对的。要让它变成可信判据，得把 S3 的框收到只套住 P1（x ≈ 0.05–0.40）。

| 位置 | 内容 |
|---|---|
| `DESIGN_ENV_RENDER_KNOBS`（`director_cut_studio.py:445`） | **补进 4 个名字**：`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`、`H3_CHARACTER_SWAP_FIGURE_WIDTH_SHARE`、`H3_CHARACTER_SWAP_FIGURE_BOTTOM`、`H3_CHARACTER_SWAP_FIGURE_EXTENT`。这件事本身就是缺陷：这个缺陷被 Preview 了 5 次，而**没有一次能从 `design_ai.env` 配置**（先写进去试过，加载器照名单丢掉，`band mode = off` 现场复现） |
| `design_ai.env`（项目侧，备份 `design_ai.env.bak_pre_wardrobe_band_20261107`） | `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur` + `H3_CHARACTER_SWAP_FIGURE_WIDTH_SHARE=1.0` |
| 版本号 | 两处 `SMART_RENDER_POLICY_VERSION = 95`；衣服带会换掉 plate clause 与 strategy 后缀，故 94 的 prompt / take 作废。出厂默认不变（`off` / `1.75`） |

**按本 manifest 真实输入量过的三档**（`_dsh_verify_13/build_both_suppressed_plates.py` → `band_narrow.json` / `band_column.json`，A/B 图在 `_dsh_verify_13/band_ab3/abc_*.png`）：

| 档 | 衣服带几何 | 压制面积 |
|---|---|---|
| 现状（band off） | 无 | unit 1 `0.2043` / unit 2 `0.1339` |
| **本档（share 1.0）** | unit 1 `x 0.141171–0.598136 / y 0.519259–0.898148`；unit 2 `x 0.0999–0.5 / y 0.12–0.75` | **0.3971 / 0.2521** |
| 默认 growth（share 1.75） | unit 1 `x 0.049758–0.689648 / y 0.519259–1.0` | 0.5316 / 0.5015 |

默认 growth 会越过受保护角色的近边 `0.558136` 到 `0.6896`（`figure_extent_applied` 每行 `protected_boxes: []`），把本来已经完美的戴眼镜角色一起糊掉；`share=1.0` 把带子留在作者画定的框内，重建帧确认她的眼睛／眼镜／嘴都在模糊之外，面积也仍在引擎自己的 `0.56` 上限内。**`FIGURE_BOTTOM=0.66` 试过并且无效**：衣服带的基线高度＝头带高度，本来就到 `y 0.898148`，growth 代码只会伸长不会缩短——所以窄化只能靠宽度（已记入 `design_ai.env` 注释与代码注释）。

**测试**：`test_round69_manual_parity` 99 项通过（新增名单＋加载器契约桩：名单内 4 个名字、加载器只装启动器未设的键、启动器值优先、`_figure_extent_parameters` 读到 1.0/1.75 两侧；本模块 import 前钉住 band 与两个 figure 参数，避免项目渲染配置污染出厂断言）；`test_character_swap_closeup_gates` 77 项（同一泄漏面扩到 `WIDTH_SHARE` 后重钉，"出厂 figure 参数"桩先前被 `1.0` 打成红）；`test_smart_render_worker` 48；`test_round52_swap_routes` 48；`test_round54/57/65` 18/18/20 —— 共 **328 项通过**；四个文件 `py_compile` 通过。Project Format 仍是 29。



### 压制真的上船了，剩下的穿崩在淡化带下方 —— Round 95 / policy 94（2026-11-07）

**验收 18:20:49 那次（policy 93，seed 3608049340227527602）**：Round 94 的闸门第一次真的开门，而且身份真的落地。

| 指标 | 16:56（未压制） | 18:20（压制后） |
|---|---|---|
| `identity_suppression_gate` | 无此字段 | `allowed=true, evidence="cutout"`（两个单元都是） |
| `identity_suppression_strategy` | `"original"` | `medium_silent_listener_identity_suppressed` |
| 压制几何 | `{}` | unit 1 `x 0.141171–0.558136 / y 0.029259–0.5193`，area 0.2043；unit 2 `x 0.0999–0.45 / y 0.12–0.5025`，area 0.1339 |
| unit 1 三个采样 | 0.605673 / **0.428631** / 0.522097 | **0.64908 / 0.538907** / 0.459285（4.229 s 首次越过 0.5 下限） |
| unit 2 中位数 | 0.50833 | 0.491569（最坏 0.382527 @ 局部 2.708 s ⇒ 绝对 11.21 s） |

取帧核对：P1 的光头皮、大鼻、黑白背心在所有采样帧都在，头顶三根刺也对，被保留的戴眼镜角色不再被画走。**唯一还活着的源特征全部是"垂下来/荡出去"的头发**：4.23 s 两侧的长发、6.60 s 脑后那团黑、11.21 s 的黑鬃毛 + 一条辫子和发绳。对照 P1 原图（`.director_cache\image_137_b4d3e445d5182bbe_nobg.png`：全光头，只有头顶三根毛）——这些全是他没有的，就是穿崩本体。而 manifest 自己也在指同一处：两个单元的 `wardrobe_audit` 都写着 **"the V1 wardrobe still fills the upper half of the body region"**（shift 0.029945 / 0.008174 vs required 0.047239 / 0.048380），同时 `wardrobe_mode = off` ⇒ **plate 只做到 y 0.5193 / y 0.5025 就停了**。

| 位置 | 内容 |
|---|---|
| `LEAN_VANILLA_SOURCE_HAIR`（`character_swap_engine.py`） | **167 → 442 字符**：把归属从"the top of the head"扩到 `the top of the head, the temples, the ears and the nape` + `onto the shoulders and down the back`，仍是正面事实（"the same bare skin where the erased actor's hair used to fall"），不出现 `wig` / `crown` / `forehead`（Round 69 的禁用名词表点名什么就画什么）；vanilla 附录 769 → **1044 / 1200**（剩 156） |
| 版本号 | 两处 `SMART_RENDER_POLICY_VERSION = 94`（各自补 Round 95 段落）；plate 内容未变、仍命中同一 token 可复用，只有 prompt 与 take 在 94 以下作废 |

**量过之后再拒绝的更宽 plate**（备用杠杆，`design_ai.env` 保持 `off`）：`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur` 按本 manifest 的真实输入重建两个 plate（18:36）确实把鬃毛和辫子都盖进来了——wardrobe band `x 0.049758–0.689648 / y 0.519259–1.0`、`x 0.0–0.70035 / y 0.5025–1.0`——但代价是**压制面积 0.2043 → 0.5316、0.1339 → 0.5015**（policy 81 当年就是按 50.13 % vs 11.4 % 否掉这一档的，还赔上卡通手），而且 `figure_extent_applied` 每一行都是 **`protected_boxes: []`**：衣服带**不尊重受保护框**，所以本已完美的 R1 身体会跟着一起糊。A/B 帧见 `_dsh_verify_13\band_ab\ab_u1_4.23.png`、`ab_u1_6.60.png`、`ab_u2_11.21.png`（左=现plate，右=带子档）。

**顺带记录（本轮未改）**：unit 2 `blocking=True / cause target_reference_similarity / action retry_fresh_seed` 却 `attempts_used=1` —— 这是 Round 86 的设计（结构性判词不重摇），Round 92 只给 *collapse* 类升到 1 次；要恢复该类重摇用 `H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS=2`。unit 1 则按 Round 92 升到了 `attempts_used=2` 并出片，正是预期行为。

**测试**：`test_round69_manual_parity` 98 项通过（新增"量过并拒绝的宽 plate"钉桩：默认仍是窄窗；vanilla 句子新增范围短语 + 442 字符 + 附录 1044 重钉；policy 94 双端一致）；`test_character_swap_closeup_gates` 77（需按脚本方式运行，`-m unittest` 看不到它自带的 `legacy_swap_route`）；`test_round52_swap_routes` 48；`test_smart_render_worker` 48；`test_round54/57/65` 18/18/20 —— 共 327 项通过；三个模块 `py_compile` 通过。Project Format 仍是 29。



### plate 压制开关被一台死掉的 BLIP 服务挡住 —— Round 94 / policy 93（2026-11-07）

**症状**：16:56:45 的运行第一次带上了 Round 93 的两个新字段，于是答案直接写在脸上——`identity_suppression_strategy = "original"`、`identity_suppression_geometry = {}`，两个单元都是。也就是说 policy 92 的代码已经载入、`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1` 也读进来了，**压制仍然一次都没跑**。而闸门要的头框其实一直都在：审计里的 `source_bboxes_normalized = [0.19839, 0.209259, 0.541017, 0.898148]`（h 0.689、面积 0.236），远超 silent 门 `h ≥ 0.25 / area ≥ 0.05`。

**根因（用应用自己的两个谓词当场测出来的）**：`enabled = bool(target_is_illustrated) and PLATE_SUPPRESSION`，而 `target_is_illustrated` 只读 caption 文本。这台机器的 asset 137 行里 `caption = ''`，`recognition` 写着 **`BLIP ERROR · BLIP service stopped unexpectedly (exit 1)`** ⇒ caption 扫描永远命中不了 `_ILLUSTRATED_CAST_TERMS` ⇒ 这台机器上**任何**参考图的 `target_is_illustrated` 都是 False。同一个 `recognition` 又写着 `AUTO BACKGROUND REMOVAL: uniform edge-connected background removed (52 % transparent)`，这正是 Round 91 已经拿来当抠图证据的东西（本工作区每张 cast 图 46–68 % 透明、每张照片 0.0 %）。当场对账：`caption=False / cutout=True` ⇒ 旧规则 `enabled=False`，新规则 `enabled=True, evidence="cutout"`。

| 位置 | 内容 |
|---|---|
| `character_swap_plate_suppression_gate()`（`director_cut_studio.py`，plate 开关旁） | 新增纯函数：`off` / `caption` / `cutout` / `none` 四种答案，plate 闸门改读 **caption 或 抠图**，与 Round 91 给 framing 的同一套证据；*medium* 问题（live-action 改编）继续只读 caption，照片不会被文件属性误判 |
| pass 编译处 | `enabled=plate_suppression_allowed`，并把五个布尔写进 `pass_spec["identity_suppression_gate"]`；manifest 的 identity_audit 里同步落一个字段，`"original"` 从此能说出它是被关掉了、caption 没命中、还是图里没有抠图证据 |
| 版本号 | 两处 `SMART_RENDER_POLICY_VERSION = 93`（各自补 Round 94 段落）；回退：`H3_ILLUSTRATED_CAST_IMAGE_EVIDENCE=0` 把所有图像侧规则退回 caption-only，`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=0` 退回 15:21 的 plate |

**离线造 plate 的直接证据**（不碰 ComfyUI）：用 Round 49 那条链路自己的 `_character_swap_identity_suppressed_source` 对 16:56 真正上船的 clip 跑一遍，得到 `.director_cache\character_swap_identity_suppression\v1_relay_861ef5fa9f0127f74570_0.000-8.500_identity_suppressed_64667b658d55942aaa20.mp4`，strategy `medium_silent_listener_identity_suppressed`；几何 `x 0.141171–0.558136 / y 0.029259–0.5193`、发丝光晕 `y 0.029259–0.235059`、`suppressed_frame_area 0.2043`，光晕右边界正好钉在受保护 R1 的近边 0.558136；顺带记录 `silent_mouth_freeze.applied = true`（tmix 7，下半脸 `registration: lower_face`）。取帧对比确认：头顶发丝被淡化去彩，R1 一侧不被啃。

**同时暴露的第二件事**：S2 只有一张**静态**框（`composite_track_samples` 五个采样全是同一个矩形），而交叉镜头里两颗头会换位——6.63 s 时 R1 的头已经漂到自己框（x 0.558）的左边，淡化带会碰到他的左颊。尾巴单元也在门内：S3 没画框，走的是默认框 `[0.15, 0.3, 0.45, 0.75]`（h 0.45、面积 0.135）⇒ silent 门 1 行 ⇒ **8.5–13.975 s 也会被压制**，那段本来是对的，重跑后要重点看它。

**第三件事：只在 plate 上开门还不够——16:56 那次的 route 是 `vanilla`**，而 vanilla 分支（`character_swap_engine.py:3022`）**提前 return**，只上交作者模板 + 静默嘴部契约那一条例外；`source_hair_ownership_clause` 只出现在 legacy（`:3316`）、precise 用的是 `hair=LEAN_HAIR if suppressed_plate`（`:3111`）。所以只修闸门，就会变成"头顶被淡化了、却一个字没解释"——正是 policy 71 记下的 seed 923009999 那次 13/16 留假发的配置。现在 vanilla 在 `suppressed_plate` 上追加 `LEAN_VANILLA_SOURCE_HAIR`（167 字符）：沿用 Round 69 给"点名被换造型"定下的价——不出现 wig / crown / cat ear / headband 这类会被画出来的名词，只给正面事实（"the top of the head gets exactly what Picture 1 draws there: bare scalp where Picture 1 shows bare scalp"）。未压制的 plate 仍然 0 字符附录，`append_chars` 602 → 769，仍在 `CHARACTER_SWAP_VANILLA_APPEND_BUDGET` 内。

**测试卫生**：`design_ai.env` 是 Studio 在 import 时装载的，所以昨天为渲染打开的 `H3_CHARACTER_SWAP_PLATE_SUPPRESSION` / `HAIR_BAND_MODE` 会把**同一行的每个 Python 进程**都带上这两个开关——`test_character_swap_closeup_gates` 的 12 项因此在没有改一行源码的情况下变红（断言的是出厂中性 plate 的 crop / split 数 / `hue=s=`）。该套件现在在 import 之前点名这两个变量（env loader 不覆盖启动器已给的变量），从此与项目的渲染配置无关。

**测试**：`test_round69_manual_parity` 97 项通过（新增闸门真值表 + 接线 + vanilla 句子 + 版本 93）；`test_character_swap_closeup_gates` 77；`test_round52_swap_routes` 48；`test_round54/57/65` 各 18/18/20；`test_smart_render_worker` 48——共 326 项通过；三个模块 `py_compile` 通过。Project Format 仍是 29，graph json 不动。

### "plate 到底有没有被压制" 不再靠文件名反推 —— Round 93 / policy 92（2026-11-07）

**症状**：上一轮把 plate 压制开关写进 `design_ai.env` 之后，16:17:28 的运行仍然"还不行"。把 manifest 拆开看，这次跑的**根本不是改动后的 plate**：`identity_audit.plate_video_path` 仍是 `.director_cache\source_remake_relay_video\v1_relay_861ef5fa9f0127f74570_0.000-8.500.mp4`（文件 mtime 15:06:33，名字里没有 `_identity_suppressed_`），三个采样 `0.632032 (1.87 s) / 0.467966 (4.25 s) / 0.51265 (6.63 s)` 与 15:21 那次几乎重合 ⇒ 开关没进进程（这些 knob 只在 Studio 启动时由 `apply_design_ai_env_render_knobs()` 读一次）。而这一点当初只能靠人肉比对文件名得知——**manifest 里没有任何字段回答"Relay 拿到的是原图还是淡化后的头"**。

**为什么这件事必须记下来**：`character_swap_engine` 里那句"头发归属"条款是 Round 35e 用 seed 923009999 换来的——"**光晕已经盖住头顶，16 帧里仍有 13 帧留着 V1 的猫耳假发和鎏金头带**，因为没人告诉 H3 光头的 Picture 1 该怎么处理那块区域"。它只在 `if suppressed_plate` 时才上船（`character_swap_engine.py:2431`）。所以对 P1 这种光头角色，**plate 压制开关同时决定三件事**：头顶淡化窗、发丝光晕、以及那句正面陈述。manifest 藏住 strategy，就等于同时藏住三项。

| 位置 | 内容 |
|---|---|
| `director_cut_studio.py` pass 编译（identity_audit spec） | 新增 `identity_suppression_strategy`（没压制时明确写 `"original"`）与 `identity_suppression_geometry`（`bands[]` 矩形、`head_band_bottom`、`suppressed_frame_area`、crown/halo 报告）——就是 ffmpeg 裁切用的那批数，也是 prompt 编译器已经在读的那个对象 |
| 版本号 | `SMART_RENDER_POLICY_VERSION = 92`（Studio / worker 两处同步，各自补 Round 93 段落） |
| 测试卫生 | `test_round54/57/65` 里三处把版本硬钉成 `90` 的断言改为"两侧必须相等"，数字只在当轮测试里钉，避免每轮都要追改 |
| 新测试 | `PlateSuppressionEvidenceTests` 三条：manifest 字段接线、"头发归属条款必须在读到 strategy 之后编译且仍绑 `suppressed_plate`"、版本 92 且两侧一致 |

**不改行为**：进到 Relay 的东西一个字节都没动，policy-91 的 take 依然有效；只是下一次 Preview 会把"plate 是什么"记在导演本来就在读的那一栏。验证方式（下一轮 Preview 之后）：`identity_suppression_strategy` 应为 `medium_silent_listener_identity_suppressed`、`identity_suppression_geometry.bands` 应给出约 `x 0.141–0.558 / y 0.029–0.519` 的头带与头顶片，若仍是 `"original"` 就说明进程还没重启到位。

**测试**：`test_round69_manual_parity` 94 项通过（新增 3 项）；`test_round54/57/65` 版本一致性 56 项通过；`test_smart_render_worker` 48 项通过；三个模块 `py_compile` 通过。Project Format 保持 29，graph json 不动。

### 交叉镜头"五官换了、头发没换" —— 项目侧启用 plate 压制（2026-11-07，只改 `design_ai.env`）

**症状（切分之后的 15:21:44 运行，policy 91，两个 unit 都 `status=complete`）**：`segment_001_000000000_000008500` 被判通过（`head_layer_only=False`、中位数 0.51277、`minimum_similarity=0.471322 @ 4.25 s`），但抽帧看到的是 **P1 的鼻子/嘴/蓝领衣服装在一个金色 V1 头发上**（4.25 s、6.63 s 都是），8.20 s 才恢复光头。也就是说 Round 92 之后的失败形态变了：身体和五官换了、**源人物的头发留下来**。同一次运行的 `segment_002_000008500_000013975`（原本好看的尾巴）反过来被判 `blocking=True / target_reference_similarity`（中位数 0.47354、`head_layer_only=True`），而 9.7 s / 12.8 s 的画面是对的 —— 颜色直方图指标两头都不准，这次不动它。

**真因（应用自己的记录）**：该 pass 的 `source_identity_strategy = "original"`、`plate_video_path = .director_cache\source_remake_relay_video\v1_relay_861ef5fa9f0127f74570_0.000-8.500.mp4`，即 Relay 收到的是**完全未淡化的 V1**；Round 49 把手工 ComfyUI 对照图中的"关压制"设成默认后，`H3_CHARACTER_SWAP_PLATE_SUPPRESSION` 一直未设，于是这个模块里所有对付头发的工具——发丝光晕（当初的教训就是"框顶排除了头顶，所以头发从来没被问过"）和 crown split——全都空转。

| 项目 | 数值（由 `director_cut_studio` 现场算出，非估算） |
|---|---|
| S2 的 R2 框 `[0.19839, 0.209259, 0.541017, 0.898148]` | 宽 0.343、高 0.689、面积 0.236 ⇒ `_closeup_gate_for_bbox` = None（dominant 需 ≥0.72/0.80/0.82；head_dominant 需高≥0.75 且宽≤0.45），但过 silent-listener 头带门（面积≥0.050、高≥0.25） |
| 启用后的压制区 | **x 0.141–0.558、y 0.029–0.519**（`feather` 羽化 alpha，不是硬边矩形），其中头顶片 **y 0.029–0.235** 额外 `boxblur` 并把饱和度压到 0.25 |
| 受保护角色 | 光晕右边界自动停在 KEEP_V1 的 R1 近边 0.558，R1 的脸不被抹；`WARDROBE_BAND_MODE` 与 medium-silent 衣服带都是 `off` ⇒ pose、躯干、动作线索不变 |
| S3（8.5 s 之后） | 没有任何人物框 ⇒ 不达门 ⇒ **尾巴的 plate 一帧不变**（那段本来就是对的） |
| 落点 | `design_ai.env` 新增 `H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1`、`H3_CHARACTER_SWAP_HAIR_BAND_MODE=blur_desat`；`apply_design_ai_env_render_knobs()` 在 import 时读取 ⇒ **必须重启 Studio**。备份 `design_ai.env.bak_pre_plate_suppression_20261107` |
| 回滚阶梯 | `H3_CHARACTER_SWAP_HAIR_BAND_MODE=off` 只留 face band + 光晕；`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=0` 精确回到 15:21 的 plate |
| 下一轮 Preview 的核对项 | pass 行的 `identity_suppression_strategy` 不再是 `"original"`、plate 改名 `..._identity_suppressed_...`、`target_reference_audit.samples` 里 4.25 s 那一格应从 0.4713 抬到 0.5 以上 |

Project Format 保持 29，policy 保持 91（本轮没有改代码，只有一个项目侧开关）。

### 角色替换"只换到头层"不再被中位数放行 —— Round 92 / policy 91（2026-11-07）

**症状**：新项目 `Director_Blueprint_Character_Remake_-_Hallway_Approach`（13.975 s，1 个 Segment，S1/S2/S3，单趟 `R2 → P1`，`R1` 按用户设定 KEEP_V1）在 **3.5–8 s** 掉回 V1 人物：抽帧看 2 s 和 9 s 是完整 P1（光头大鼻角色），3.5 s 变成"V1 金发头 + P1 衣服"，5.5 s 几乎没换，7.5 s 是 P1 五官贴在金发头上的混合体。manifest 里 `status=complete`、`error=''`、`attempts_used=1`，QC 只留了一句 advisory。

**真因（既不是排程，也不是角色表）**：identity audit 的 target-P 相似度是 **3 个采样的中位数**，而 head-layer veto 只看这个中位数。用引擎自己的 `_extract_identity_rgb_frame` + `target_reference_frame_similarity` 对同一条 take（V1 relay plate + R2 pass 成品，manifest 里记录的 P1 图和审计框）逐帧复算：中位数**精确复现 manifest 的 0.573422（delta 0.000000）**，逐帧为 `0.635618 (3.071 s) / 0.485056 (6.979 s) / 0.573422 (10.887 s)`。最差帧已经跌破 `0.5` 门槛，中位数还在门槛之上 ⇒ `blocking=false` ⇒ lean 路径下 identity QC 只是"证人"（Round 52）⇒ 不重摇、照常交货。扫描全工作区历史 audit：`head_layer_only=True` 的判定除了这两次 Hallway 运行，其余全部落在 0.494 以下 —— 也就是说这两次正是被平均值吃掉的区间。

| 位置 | 内容 |
|---|---|
| `smart_render_worker.py` 常量区 | `CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR` 数值不动（0.5），但改为绑住**每一个采样**；新增 `CHARACTER_SWAP_HEAD_LAYER_COLLAPSE_MAX_ATTEMPTS = 2` |
| `character_swap_head_layer_blocking_cause()` | 拆出"是哪个见证触发的"：`target_reference_similarity`（Round 69 的中位数情形）与 `target_reference_temporal_collapse`（Round 92：中位数过线、但某一帧跌破）；`character_swap_head_layer_blocking()` 变成它的布尔包装，Round 69 真值表逐项不变 |
| `inspect_character_swap_identity` 采样处 | `target_reference_audit` 逐帧留表：`minimum_similarity` / `worst_timestamp_seconds` / `worst_bbox_index` / `samples[]`；中位数留在原位置，重试排名行为完全不变 |
| 判定与 reason | verdict 新增 `blocking_cause`；`reason` 追加 `target P Picture likeness collapses to 0.485 at 6.98s, below floor 0.50, while the median 0.573 clears it`，让 manifest 读起来像导演看到的画面而不是平均值 |
| 重试预算 | **只有 collapse 类**能把 lean 的单趟 spec 抬到 2 次（原始 take + 一次换 seed）—— 同一条 seed 已经在 3 s 和 11 s 都产出了目标角色，换 seed 是真有机会；结构性"衣服根本没动"仍按 Round 86 不抬预算。`H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS` 仍然双向覆盖（`1` = 绝不重摇，`3` = 恢复 Round 69 预算） |
| 版本 | `smart_render_worker.py` 与 `director_cut_studio.py` 的 `SMART_RENDER_POLICY_VERSION` **90 → 91**（QC 结论形态变了 ⇒ policy-90 的结论作废需重渲；graph json 未动） |

**验证**：对真实 take 重跑 `inspect_character_swap_identity`（manifest 里存的 spec）⇒ `passed=False / blocking=True / blocking_cause='target_reference_temporal_collapse'`、median 复现 0.573422、minimum 0.485056@6.979 s、samples 三行齐全 ⇒ attempt ceiling **1 → 2**（脚本 `_dsh_verify_13\verify_collapse_veto.py`，exit 0）。测试：`test_round69_manual_parity` **91 项通过**（新增 3 项：用本项目实测数字钉住 collapse 判定与"旧规则放行"的对照、collapse 升级预算的 env 双向覆盖、接线断言覆盖 `minimum_similarity`/`samples`/`blocking_cause`/升级调用）；`test_smart_render_worker` 48 OK、`test_silent_mouth_transient_qc` 9 OK、`test_smart_render_qc_advisory` 4 OK、`test_round52_swap_routes` 48 OK。顺带把 `test_character_swap_retry_strengthens_only_identity_lora` 里一直钉着的 1.5 改成跟随引擎常量 `CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH`（1.7）—— 上限早已上调而断言没跟上，才长期独红。

**生效方式**：重启 `director_cut_studio`（policy 版本在 GUI 进程里编译，worker 是每次新起的子进程）；Hallway 这条 segment 本来就在 `render_dirty_segment_ids` 里，直接预览即可。若重渲后 QC 仍判 collapse，会写 `attempts_used=2` 并把该段标为 QC 失败，而不是像以前一样交货。

### SoulX-Singer 运行时更新：整首歌 SVC 落进 `models\SoulX-Singer-main`（2026-11-05，**实机跑通 17 分 35 秒整首**）

**做了什么**：把修好的开发副本 `C:\Users\daniel\Downloads\SoulX-Singer-main`（改动记录见其 `handoff.md` §4/§10）同步进 Studio 安装目录 `models\SoulX-Singer-main`。两份代码是**双向分叉**的：Downloads 有长音频修复和新的桌面 SVS GUI、但没有 Studio 集成；工作区这份有 Studio 集成（`/_studio_start_svc`、`/_unload_svc`、懒加载、7861 Server Mode）但没有修复。所以按文件合并（13 个源码文件 + 9 个自检脚本），没有整目录覆盖，权重、`.runtime`、`outputs`、`ffmpeg` 原样保留；被替换的 9 个文件备份在 `_backup\V0.3.8-alpha.3_soulx_singer_pre_longfix_20261105`。

| 文件 | 内容 |
|---|---|
| `preprocess/tools/f0_extraction.py` | **5 分钟之后静音的真凶**：`F0Extractor(max_duration=300)` 取消（F0 只到 300 s，`build_vocal_segments` 之后没有分段 ⇒ 尾部一直是 0）；RMVPE 改为分窗推理（30 s + 2 s 重叠）；`to_local_average_cents` 由 O(N²) 拷贝改成量化索引 |
| `webui_svc.py` | 10 分钟硬上限 ⇒ `TARGET_MAX_SEC_DEFAULT = 0`（0 = 不限制）+ 界面「Target 时长上限」滑条；`_trim_and_save_audio` 只在 `max_sec > 0` 时裁剪；分段进度映射到 66%→98% |
| `soulxsinger/models/soulxsinger_svc.py` | 分段之间加淡入淡出接缝，拼接处不再割裂 |
| `soulxsinger/models/modules/whisper_encoder.py` | >30 s 输入不再被静默截成 30 s 内容（按 30 s 窗口分批编码） |
| `cli/inference_svc.py`、`cli/inference.py`、`webui.py`、`gui_svc.py` | `process(..., progress_cb=...)` 进度回调；SVS 侧同步 |
| `gui.py`、`resource_release.py`、`launch_gui.py`、`launch_gui.pyw`、`launch_svc_common.py` | 新增桌面 SVS GUI（歌词 + MIDI 编辑）与统一显存释放模块；launcher 加 `gui_svs` 入口 |

**两处工作区专属改动（上游没有，勿在下次同步时覆盖掉）**

| 位置 | 内容 |
|---|---|
| `models\SoulX-Singer-main\webui_svc.py:408` | 新参数 `target_max_sec` 写成**带默认值的尾参数**。`soulx_server.py::_call_upstream_start_svc` 只发布 12 个命名参数并按关键字调用；若第 13 个参数是必填，`required` 判定失败会退回按位置传 12 个值 ⇒ `device_choice` 之后全部错位（就是历史上 "Pitch 0 被送进 Device" 那一类事故），且缺参会直接 TypeError。探针 `_dsh_verify_13\verify_soulx_studio_contract.py` 实测：关键字路径可用、12 个值落点正确、Studio 路径取 `0 = 不限制` |
| `models\SoulX-Singer-main\launch_svc_common.py:19-66` | 环境探测优先 `.runtime\<计算机名>\.venv\Scripts\`（venv 的 pythonw 在 `Scripts\` 下），双击 `launch_gui.pyw` 用的是 Studio 已装好的 CUDA 运行时，不会误落进 conda 环境 |

**验证（全部用安装运行时 `models\SoulX-Singer-main\.runtime\DESKTOP-PON9M2I\.venv\Scripts\python.exe`，torch 2.7.1+cu128、RTX PRO 4500）**

- `py_compile` 15 个文件通过（含新增 `gui.py`／`resource_release.py`／`.pyw` launcher）。
- `outputs\_longfix_check.py`：`decode()` 新旧结果一致、6000 帧 0.02 s→0.009 s；40 s 音频单遍 18.0 s→分窗 1.0 s（帧数一致、voicing 一致率 0.9978、音高偏差 mean 3.06 cent）；对真实 `target.mp3`：`interpolate_f0` 旧上限只出 300.0 s，新逻辑出 **1055.1 s**；`build_vocal_segments` 66 段覆盖 0–1055.1 s、max_gap 0.00 s；Whisper 70 s → 3500 帧（= 30+30+10 手工分窗之和）；CUDA 峰值仅 0.68 GiB。
- `outputs\_run_convert.py`（真实整首 17 分 35 秒，走 `run_svc_conversion` 关键字调用 = Studio 的同一条路）：**61 段、300 s 跑完、输出 1055.1 s / 24 kHz**；`outputs\_verify_output.py`：first audio 0.0 s、last audio 1053.8 s、静音 50 ms 帧仅 1.0–2.0%、最长静音段 1.7–2.8 s（旧 bug 是 300 s 之后整段静音）。
- `outputs\_import_probe.py`：webui import 49.9 s、AppState 81.7 s，释放模型后 reserved 10.35→3.98 GiB、free 20.21→26.59 GiB。`outputs\_ui_check.py`：新滑条与文案进入 Gradio config、页面 200。`outputs\_release_check.py`：reserved 3.00→0.00 GiB、free 27.63→30.63 GiB。`outputs\_gui_check.py`：桌面 GUI 构建、示例载入、改音符、保存（20/20/20/20）、`.bak`、退出清理全部通过。
- Studio 侧 `testing\test_soulx_runtime.py` + `test_soulx_dialog.py` **20 项通过**。顺手修掉一处随主机摇摆的断言：`test_safe_defaults_match_official_svc_workflow` 改为注入 `SoulXRuntimeState(mode="client", api_url="", installed=False, …)` —— 本机装了 SoulX 时 dialog 会解析成 `127.0.0.1:7861`，与 `DEFAULT_SOULX_SERVER`（192.168.0.185）不符（本文件 :1996 早记录过同类摇摆）。

**使用条件**：正在跑的 7861 SoulX 服务仍是旧代码，必须用 `restart_soulx_server.bat`（或 Studio 的停止/启动）重启才会载入新的 `webui_svc`；WebUI 里的「Target 时长上限」滑条只影响手动 WebUI 流程，Studio 的 SOULX 工作区固定走不限制。另：在本会话这类从冻结 Tray 继承 `TCL_LIBRARY`/`TK_LIBRARY` 的 shell 里跑 Tk 脚本会因 Tcl 版本冲突失败（8.6.12 vs 需要 8.6.15），从资源管理器双击启动不受影响。



### Round 92：全透明畫布不再算摳圖證據，Identity Sheet 參考送進 ComfyUI 打第一槍（2026-11-02，**原始碼已修復；本輪 1 槍；影片已渲染但尚未由導演分級**）

**緣起**：Round 91 讓「alpha 摳圖」也能當 framing 證據之後，留下一條漏網路徑 —— 一張**幾乎全透明**的 PNG（甚至整張全透明）也會因為「透明像素 ≥ 2%」被判成摳圖證據，結果 identity sheet 的 head／outfit 框錨到空畫布上，送進 graph 的參考等於沒有角色。本輪先把這個下限補上，再把 D 方案（用 identity sheet 當外觀參考）在 ComfyUI 上打第一槍。

**源碼改動（`character_identity_sheet.py`，本輪唯一產品改動）**

| 位置 | 內容 |
|---|---|
| `:1108` | 新增 `ALPHA_CUTOUT_MIN_OPAQUE_SHARE = 0.02` —— 有被畫到的不透明像素也要佔 ≥2% |
| `:1154` | 新增 `_opaque_share()`，讀 256-bin alpha 直方圖算「真正畫到」的比例，不逐像素掃圖 |
| `:1161-1165` | `is_alpha_cutout()` 现在是**雙重下限**：透明佔比 ≥ `ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE` **且** 不透明（有畫到）佔比 ≥ `ALPHA_CUTOUT_MIN_OPAQUE_SHARE` 才算摳圖 |

`ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE = 0.02`（Round 91）保持不動，所以真正的 cast 摳圖（46–68% 透明）照樣通過。驗證：`testing\test_round91_illustrated_evidence.py` **26 項通過**（本輪回跑 0.229 s，OK），另跑既有 sheet／swap 相關 suite **211 項通過**（policy pin 仍 90）。`py_compile` 過 `character_identity_sheet.py`／`director_cut_studio.py`／`smart_render_worker.py`。

**headless 編 job（不開 GUI 也能重現這一槍）**：`.codex_tmp\r92_headless_job.py` —— `QApplication` offscreen → `load_project_path` → `quality_profile="motion_preview"` → `_reconcile_speech_timing_before_run()` → `_read_settings_ui()` → `_build_smart_render_job(request_kind="preview", megapixels=0.5, seed=…, enable_rtx_vsr=False)`，輸出 job json 後交給 `staged_model_driver.py run`。注意 headless 編出來的 job json 落在暫存目錄，專案 `render_jobs\` 只留 manifest，要重現得重跑這個腳本。

**實機這槍的技術事實（全部讀自 manifest，不是推測）**：案 `example\a_woman_in_a_pink_dress_and_polka_dots_5`，seed **592000107**、policy **90**、0.5 MP、單段 13.57 s，manifest `project\render_jobs\preview_592000107_1793589625959997100.manifest.json`。輸出 `cache\generated_outputs\preview\592000107\segment_001_000000000_000013568\character_swap_pass_01_R1\01_save.mp4`（576×864／24 fps／325 幀／11,787,718 B）。

- **D 真的有送到**：`reference_framing=illustrated_identity_sheet`、`identity_sheet_reason=composed`、preset requested **0 → forced 8**、`outfit_view=full`、sheet 頭面板 coverage **0.5251**（同場 V1 頭部 coverage 0.099588、原 P1 0.149153；原 P1 只有 0.21793 MP、頭 crop 0.0331 MP）。`medium_silent_rows=1`、`framing_threshold=0.0`、`route=vanilla`、prompt 3609 字（author 2895）。
- **Round 86 兩項止血如實生效**：`attempts_used=1`（QC 判 blocking 也沒有多花 seed）、留檔生效 `identity_attempts\attempt_01__01_save.mp4`（`attempt_table` 有這一筆，含全部數值）。
- **QC 仍未過**：`target_reference_similarity=0.277282` < floor 0.5；wardrobe `binding_region=lower`，shift **−0.04061**（late −0.045396）< floor 0.12 ⇒ **下半身穿的還是 V1 的衣服**。manifest 誠實記 `passed=false`、`blocking=true`、`action=retry_fresh_seed`、`character_swap_identity_advisory_only=false`、`character_swap_identity_failed=true`。

**量化對照（同規格才可比：手動金標 `example\a_woman_in_a_pink_dress_and_polka_dots\character-swap_00043_.mp4`，576×864／24／325 幀；基線為同專案 policy 89，seed 582453245502616783）**

| 指標 | 手動金標 | policy 89（framing=original） | policy 90（D） |
|---|---|---|---|
| 粉裙面積／金標 | 1.00 | 0.77–1.26 | 0.78–1.16（後半 0.90–0.97）⇒ 身體尺度無系統漂移 |
| 頭部區 skin 面積（loose，5 點均值） | 0.2176 | 0.2445 | **0.2736** ⇒ 對 V1 是 **3.51×**（金標 2.79×、p89 3.13×）＝ **臉比手動大約 26%** |
| 同上 strict mask（14 幀均值） | 0.1607 | 0.1814 | 0.2080 |
| 頭部區 white 像素（P1 的白色頭箍） | 0.1134 | 0.0603 | **0.0388** ⇒ 頭箍逐輪被稀釋，D 最差 |
| 1 fps 幀間差（穩定度，越小越穩） | 67.28 | 60.73 | 64.03 ⇒ **無闪烁回归** |

**14 秒 1 fps contact sheet 目視**：D 沒有 character-sheet 面板洩入畫面、無蜂窩背景、無老人化、卡通媒介保留（無真人化）；**8–13 s 的臉確實更像 P1**（圓頰、眉／瀏海筆觸）＝ D 的真實增益。另外 P1 的短 bob 在「手動」與「Studio」兩邊都變成長髮 ⇒ **髮型漂移是 H3／relay 固有，不是 Studio bug**。

**分級**：取捨權在導演，本輪不自判。助理判定供參考 —— 身份相似度↑（目視）但有代價：臉部面積比手動大 ~26%、P1 白色頭箍丢失、下半身仍未換（QC blocking 未變）。另有兩條**只記不動**的觀測缺口：（a）顏色直方圖的 `target_reference_similarity` 給 p90（0.277）比 p89（0.321）低，與目視相反 ⇒ 這個 QC 代理量的是顏色不是身分；（b）`reference_design_evidence`／`reference_alpha_flattened` 沒有寫進序列化 pass row，manifest 看不到「是哪一條證據決定的 framing」。

**界定**：`SMART_RENDER_POLICY_VERSION` 維持 **90**、`PROJECT_FORMAT_VERSION` **29**、`VERSION` 維持 `0.3.8-alpha.3`（導演指定不動）、`character_swap_engine.py:3807-3808` 的 `PREPARE_RESOLUTION_HIGH/LOW = "480"` 不動、導演的 `H3-Character-Swap-Relay-V2-api.json` 一字未改。本輪只改「空畫布不能再算證據」，framing 判定條件沒有放寬 ⇒ 既有 Job／manifest 不作廢、不需重跑。

### Round 91：Identity Sheet 的資格改讀「alpha 摳圖」證據，卡通 P 圖不再因為 caption 沒寫 cartoon 就出局（2026-11-02，**原始碼已修復；本輪 0 槍；影片未實機**）

**緣起（這是 Round 86 那三槍白燒的同一個根因）**：`a_woman_in_a_pink_dress_and_polka_dots` 的 P1 本身就是去背卡通立繪（`.director_cache\image_137_ef2009c5827da7cb_nobg.png`，RGBA 310×703），但 BLIP caption 裡沒有 cartoon／illustration 那類字，`_looks_like_illustrated_cast()` 答 No ⇒ `preserve_full_design=False` ⇒ **identity sheet 從頭到尾沒跑**，送進 graph 的只有那張頭部只佔 0.0331 MP 的立繪。結果就是下半身永遠穿 V1 的衣服，而且換 seed 修不了。

**源碼改動：把「媒介」與「framing」兩條問題永久拆開**

| 位置 | 內容 |
|---|---|
| `character_identity_sheet.py:1101,1111` | 新增 `ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE = 0.02` 與 `is_alpha_cutout()`： RGBA／PA／P／LA 且透明像素 ≥2% 才算去背摳圖 |
| `director_cut_studio.py:573-598` | `H3_ILLUSTRATED_CAST_IMAGE_EVIDENCE`（出廠 **on**，`=0` 回復「只讀 caption」）、`_illustrated_cast_image_evidence_enabled(environ=None)`、`_ILLUSTRATED_CAST_CUTOUT_CACHE`（按 (path, mtime) 記憶，上限 512 就整組清） |
| `director_cut_studio.py:600-656` | 新 predicate `_character_swap_design_reference_evidence()`：caption 命中就直接 Yes（不碰檔案系統）；沒命中才探測摳圖；**探測失敗＝沒有證據，不是「那就是照片」**；probe 一律 try/except，绝不讓 Job 編譯掛掉 |
| `director_cut_studio.py:37902-37915` | 編譯 Character Swap pass 時，`target_is_illustrated`（媒介／真人化開關與 close-up plate gate 用）與 `target_is_design_artwork`（**只有這個決定 identity sheet 分支**）分開計算，並在註解裡寫死「兩個問題、兩個 predicate」 |
| `smart_render_worker.py:324-330` | policy 註解：新證據只在**編譯時**讀，worker 本身不讀；framing 翻轉的 Shot 會重編 prompt ⇒ policy 89 的快取作廢 |
| `director_cut_studio.py:1091` | `SMART_RENDER_POLICY_VERSION` **89 → 90** |

**為什麼不會再把真人誤判成卡通**：真人化開關（`source_cast_live_action_adaptation`）與 close-up plate gate 讀的還是 caption predicate `_looks_like_illustrated_cast`，alpha 證據只准影響「要不要用整張 design／identity sheet」這一件 framing 的事。本工作區的實測分布也支持這個分界： graded cast 摳圖的透明比例 46–68%，照片全是 0.0%。

**驗證**：新增 `testing\test_round91_illustrated_evidence.py` **26 項通過**（覆蓋 env 開關的讀值、caption 短路不讀檔、探測例外一律 No、快取隨 mtime 失效、容量上限、媒介與 framing 兩條路徑互不干擾）。本輪 **0 槍**：**影片未實機**。

### Round 86：Preview 只花它編譯過的取數，而且每一取都留檔留帳（2026-11-02，**原始碼已修復；本輪 0 槍；影片未實機**）

**緣起**：導演在 Studio 點 Preview（`example\a_woman_in_a_pink_dress_and_polka_dots_4`，job `preview_1265738911004531245_1793578640785883400`，policy 89、0.5 MP、單段 13.568 s），問「為什麼會重複三次，我覺得第一次已經是最好的效果了」。查證結論先講清楚：**影片本身不是三段重複** —— `generated_preview.mp4` 是 325 幀／13.54 s／576×864，與乾淨 plate（325 幀）同長，幀自相關無週期尖峰；真正的狀況是**同一支渲染跑了三次**。

**兩段成因（都在原始碼與該 job 的 manifest 裡查證過，不是推測）**

| 環節 | 事實 | 位置 |
|---|---|---|
| Studio Preview 編譯 | `"maximum_attempts": 1` | `director_cut_studio.py:37871`（完整渲染路徑才是 `:38233` 的 3） |
| QC 否決 | `head_layer_only=True` 且 `target_reference_similarity=0.387293 < 0.5` ⇒ blocking | `smart_render_worker.py:375` |
| 抬高上限 | blocking 時 `ceiling = max(ceiling, min(job, 3))` ⇒ 編譯的 1 被抬成 3 | `smart_render_worker.py:463` |
| 選哪一取 | 依顏色直方圖「最像目標 P 圖」取最高，attempt 3 以 0.387 獲勝 | `smart_render_worker.py:2327` |
| 帳面結果 | `attempts_used=3`、`selected_attempt=3`、`action=retry_fresh_seed`、`blocking=True` | 該 manifest 232／239 行 |

三槍是**白燒**：wardrobe 審計上半身 `+0.11186` 通過、下半身 `-0.044346` 不過（門檻 0.12 絕對量或 0.042553 相對增益）⇒ 下半身一直是 V1 的衣服。這是結構性失誤，換 seed 修不了，每多一槍只是多燒 8–10 分鐘 VRAM。

**A｜止血（本輪已改）**：blocking 抬升預設值改成 **1（不抬升）**，也就是「編譯說幾種就幾種」—— Preview 編譯 1 就只渲染 1 槍，完整渲染路徑本來編譯 3，行為不變。QC 的判决與全部數值照樣進 manifest，只是不再自作主張花 GPU。代碼入口 `character_swap_blocking_max_attempts()`，函式多了一個 `blocking_max_attempts` 參數讓測試與呼叫端不用讀環境就能重現兩種行為。

**B｜留檔留帳（本輪已改）**：原本 retry 迴圈已經把落選的 take snapshot 下來，選完 winner 卻把它們 `unlink()` 掉 —— 導演想留的第一槍就這樣消失了（這次的 attempt 1 是最後從 ComfyUI 伺服器 output 裡撈回來的）。現在：

- 每一槍都複製到 `<download_dir>\identity_attempts\attempt_NN__pass_01_R1_0000K_.mp4`。檔名刻意保留 ComfyUI 原本的輸出檔名（尾段就是伺服器 output 裡那個檔案），要跨機比對或重新下載都不必重渲。
- Manifest 的 `character_swap_identity_audits[]` 每一列新增 `attempts_used` 與 `attempt_table`：逐槍記錄 `target_reference_similarity`、`wardrobe_shift`／`_late`、`silent_articulation_excess`、`target_likeness_score`、`blocking`、`head_layer_only`、`reason`、`prompt_id`、`selected`、`take_path`。以前 manifest 只留「被選中的那一筆」，所以三槍重試看起來只有一個數字，無法對帳導演看到的與指標選的為何不一致。
- 複製失敗或檔案不见只記 `take_copy_error`／空 `take_path`，**绝不拋错**：QC 這層沒權利把已經花完錢的渲染搞挂。

**新增環境變數（兩者都不必改代碼即可切換）**

| 變數 | 預設 | 作用 |
|---|---|---|
| `H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS` | 未設＝1（不抬升） | 設 `3` 回復 Round 69 的抬升行為；數值一律夾在 `[1,3]`，打錯字不會失控 |
| `H3_CHARACTER_SWAP_KEEP_ATTEMPTS` | 開啟 | `off`／`0`／`false` 回復「選完即刪」；manifest 的 `attempt_table` 照寫，只是 `take_path` 為空 |

**驗證（全部離線，本輪 0 槍）**

- `test_round69_manual_parity` ＝ **88 項 OK**（模組原本 78 項；新增 `AttemptEconomyAndEvidenceTests` 10 項：抬升常數與 env 抬升的兩張 pinned 表、env 直達 ceiling、`attempt_row` 欄位、take 檔名規則、三槍留檔位元組比對、`off` 只留帳不留檔、檔案不見不拋錯、manifest 接線）。原本钉 `(4, 1, True, 3)` 的那一列改成 `(4, 1, True, 1)` 並註明理由；Round 69 的 3 由 escape hatch 那張表繼續钉住。
- Character-Swap 分級防護網（14 個會 import `smart_render_worker` 的 suite）＝ **392 項 OK／1 skipped／51 s**。
- `py_compile`：`smart_render_worker.py`、`director_cut_studio.py`、`character_swap_engine.py` 全過。

**界定**：只改 worker 的 retry 取數與留檔，**不改 prompt、不改 workflow、不改 project schema** ⇒ `SMART_RENDER_POLICY_VERSION` 仍是 89、`PROJECT_FORMAT_VERSION` 仍是 29、`VERSION` 仍是 `0.3.8-alpha.3`，既有 Job／manifest 快取全部不作廢。Round 69 item 3 的「QC 否決權」本輪變成**預設不花錢、要花錢用 env 開**，這是導演批准的取捨（`批准 A+B`），不是把 gate 拿掉：判决與數值仍在，只是由導演用眼睛取勝，而且現在有檔案可以選。**影片未實機**：A+B 的實際省時與留檔效果都還沒跑過一槍驗證。


### Rounds 81–83：測試基準重新對齊＋登記兩項環境性測試故障；產品碼零改動（2026-11-02，**測試基準已修復並分級驗證；產品碼未動；影片未實機（本輪 0 槍）**）

**緣起**：要補登記 Round 67／69／75 之前，先讓「全套綠」這個信號可信。結果發現兩件事同時在污染信號：六處測試把**舊值**钉死（產品碼是對的，測試是錯的），以及測試結尾一個**原生崩潰**。這兩類都會讓一次真實的回歸被讀成假綠或假紅。

**六處測試重新對齊（全部只改 `testing\`，產品碼一個字未動）**

| # | 檔案 | 釘錯的地方 | 修法 |
|---|---|---|---|
| 1 | `test_fourdx_ui.py` | `payload["version"] == 25`，實際是 29 | 改成 `from version_info import PROJECT_FORMAT_VERSION` 後對常數斷言（先例：`test_director_timeline.py:5578`） |
| 2 | `test_project_workspace.py` | `motion_preview.megapixels == 0.2`，實際 0.5 | 對匯入的 `PREVIEW_MEGAPIXELS` 斷言，**另加**一個 `== 0.5` 的明文钉值＋訊息（防止兩邊一起漂移） |
| 3 | `test_music_video_engine.py:53` | `load_skill_profiles(Path(__file__).parent)` → `FileNotFoundError: skill default/h3-prompt-writing` | 改成 `parents[1]`＋註解。真正的 skill pack 在仓库根，`skill_engine.py:121-131` 不會往上找父目錄 |
| 4 | `test_design_engine.py`（兩處） | golden fixture 讀 `example\tang_ting_ci_ying_45s_demo\design_plan.json` 與 `example\Dragon_Realm_vs_Immortal_Martial\DESIGN_REQUIREMENT_WORLD_POWER_REVISION.txt`，**這兩個 example 資料夾已不存在**（完整列表核對過） | 提前 `self.skipTest(...)`，名稱＋原因都寫出來 |
| 5 | `test_design_engine.py:~2069` | `len(calls)==1`，實際 2 —— `unload_lm_studio` 現在先探主機方言（`_is_strata_host`／`_host_kind`，Strata 支援）再 GET 目錄 | 改成斷言**所有** call 都以 `/api/v1/models` 結尾（沒有 POST 過 unload）。這個 guard 本來就不計 GET，測試只是跟錯口徑 |
| 6 | `test_comfy_connection_recovery.py:287/296` | `queue.call_count==1`／`assert_not_called()`，實際 2 —— worker 現在飛完會 POST `/free`（`comfy_submit_worker.py:566`） | 只數 `full_url == "http://remote:8188/prompt"`：首跑必須是 1 且要有 `/free`；resumed 那跑必須 0 個 `/prompt` |

**登記的环境性故障 1 —— 全套結尾的原生崩潰（不是產品 defect，不修）**：崩潰身份 `0xC0000005` access violation，發生在 `testing\test_standard_pipeline_regressions.py` 跑完後、Qt `processEvents()` 與 ffmpeg `[h264_mf]`／`[hevc_mf]` 拆帳的時期；fault dump 顯示洩漏執行緒（`audio_separator_dialog.run` 卡在 `socket.create_connection`、`director_cut_studio.py:2640 _read_loop`／`:2691 _write_loop`）。bisect（日誌 `.codex_tmp\r81_bisectA..E.log`）：A／B／D（不含該模組）不崩，C 與 E 崩，**E 崩在該模組 :376（test_03）、C 崩在 :306（test_02)** ⇒ 抓到的是模組、不是某一行；是累積執行緒壓力決定崩點。**決定性證據**：單獨跑 `--only test_standard_pipeline_regressions` ＝ 15 項 OK／51 s／EXIT=0（`.codex_tmp\r82_iso_stdpipe.log`）；它早於 Round 81 就能重現（`--skip test_round69_manual_parity` 照崩），而 Round 65 的基線是绿的（`logs\r65_full_suite.log`，1 159 OK／269 s）。**實用作業方式**：要全套 tally 就用 `working\run_testing_suite_watchdog.py --stall 300 --skip test_standard_pipeline_regressions`。

**登記的環境性故障 2 —— 機器負載把單測拖到 5 分鐘 stall**：本日全套（跳過上面那模組）跑到第 526 項時，watchdog 的 `faulthandler` 5 分鐘計時在 `test_director_timeline.DirectorTimelineDragTests.test_shot_tool_drags_visual_range_and_shot_dialog_is_structured` 引爆（`.codex_tmp\r82_full_nostdpipe.log:537`，EXIT=1）。同一支測試**單獨跑 2.047 s OK**（`.codex_tmp\r83_iso_dragtest.log`）。引爆當時機器上同時常駐：ComfyUI（port 8189）、Studio 本體（06:38 啟動）＋ `media_prepare_service`／`blip_service`／`audio_service`，以及 07:50 才被拉起來的 `audio_separator_server`。結論：全套 tally 要挑空檔跑，或先關掉 Studio 那組服務；這不是測試 defect。

**驗證（本日重跑，皆離線）**

- 五個被重新對齊的模組 `--only test_comfy_connection_recovery,test_design_engine,test_fourdx_ui,test_project_workspace,test_music_video_engine` ＝ **187 項通過（0 failure／0 error，2 skipped）**，日誌 `.codex_tmp\r82_fixed_pins.log`。
- 分級 Character-Swap 網（19 個 suite，`.codex_tmp\r69_run_tests.py`）＝ **569 項通過（1 skipped，97.3 s）**，日誌 `.codex_tmp\r82_r69subset.log`。
- `test_standard_pipeline_regressions` 隔離 **15 項 OK**（51 s）。執行本身即證明可編譯，未另跑 `py_compile`。

**界定與回退**：這三輪**沒有產品碼改動** ⇒ `SMART_RENDER_POLICY_VERSION` 仍是 89、`PROJECT_FORMAT_VERSION` 仍是 29、`VERSION` 仍是 `0.3.8-alpha.3`、既有 Job／manifest 快取一律不作廢。测试端改動都可回退（它們只是把断言改對齊產品事實，沒有放松任何 gate）。**影片未實機**：本輪 0 槍，Round 69／75 的成片對帳仍欠一槍。

### Round 75：Identity Sheet 的 rear／side 畫稿要解析成絕對路徑才送到引擎（2026-11-02 約 00:50–01:47，**源碼已修復；補登記於本日，本輪 0 槍**）

**這一輪當時沒登記，而且產品碼裡沒有一個 `Round 7x` 標記**（四份產品檔 grep `[Rr]ound 7x` ＝ 0 命中），所以本條引用的是：測試 docstring（`testing\test_round69_manual_parity.py` 第 35 行附近 item 7／class G）＋ 檔實證（`character_identity_sheet.py` 00:50:57、`smart_render_worker.py` 01:06:45、`character_swap_engine.py` 01:21:27、`director_cut_studio.py` 01:47:13）。

**根因**：`_character_swap_identity_sheet_view_sources`（`director_cut_studio.py:35568`）掃 Media Pool 同目錄、按 asset family ＋ 整字 token 找到正確的 rear／side 畫稿之後，`chosen` 存的是**裸檔名**。引擎那一端 `collect_view_sources` 只保留「它打得開的圖」，裸檔名一律死在自己的 `is_file()` 檢查 ⇒ 每一張真實的 rear／side 都被丟掉，**鏡像正面的 fallback 回到線上**，整個掃描變成一個還會回報 `matched` 的 no-op。換言之 manifest 顯示「有 rear 視圖」，實際送上是正面鏡像。

**改動**：送給引擎的映射改成 `str(folder / chosen[name])`（同函數 35640-35655 的註解把理由寫死在產品碼裡），`metrics["identity_sheet_view_sources"]` 仍存檔名，讓 Job／manifest 可對帳而不把絕對路徑散佈到 contract。family 規則（正面圖的 asset id，不是整個檔名）與整字 token 規則兩者都是 load-bearing：少了 family，第二個角色的 rear 會變成第一個角色的 rear；少了整字，`background_test.png` 會搶下 rear 面板。

**驗證**：`testing\test_round69_manual_parity.py::IdentitySheetViewSourceTests::test_a_tagged_layout_finds_this_character_s_own_drawings` 直接對每個 view 來源斷言 `is_absolute()` **與** `is_file()`（第 1161 行的失敗訊息就寫著 `round 75: a bare file name fails its own is_file check`），並釘住 `identity_sheet_view_*` 五個 metrics 欄。今日重跑：class G 12 項全過，且它所在的 19-suite 分級網 **569 項通過**（見 Round 69 驗證段）。

**界定**：源碼已修復＝「後／側視圖真的以可開啟的路徑送上去」有測試钉住；**影片未實機**＝沒有一支片子證明過開著 rear／side 的 identity sheet 會把成片身分相似度拉高。

### Round 69：手動 ComfyUI 與 Studio Preview 的九項 A/B 對帳，全部落回源碼（2026-11-01，**源碼已修復；policy 88 → 89；補登記於 2026-11-02，本輪 0 槍**）

**這一輪當時也沒有登記**（`CHANGELOG.md` 上次寫入 2026-11-01 13:42）。權威條文一直在 `testing\test_round69_manual_parity.py` 的模組 docstring 裡，以下按那九項重述，並補上今天重跑的實測。

**A/B 的標的**：同一支 clip，導演手動的 `character-swap_00042_` / `character-swap_00043_`（576×864、325 幀、一條 job、plan 124/18、seed 904239、LoRA swap 1.5＋turbo 0.8、prepare `['480',0,'silence']`、RTX 節點 id 9 只掛參考圖）＝**接受**；Studio 自己編的 Preview ＝**拒絕**。計價出來的差距是：手動的圖 `appends nothing`，Studio 的同一支 append 了 **4 050 字元**，且每一張被拒絕的幀都有一個參考圖沒畫的東西（crown、cat ears、belt、honeycomb）。

**九項改動（全部只動 Studio 編譯出的東西；使用者的 `H3-Character-Swap-Relay-V2-api.json` 一個字沒改）**

1. **Prompt 去污染＋風格上限**（class A）：點名一個被禁止的物件就是把畫上它，所以附錄改說 `the top of the head` 而不是 `the crown`；路線 1 附錄可增長的那一半被 `CHARACTER_SWAP_LEAN_STYLING_BUDGET = 1200`（`character_swap_engine.py:702`）封頂，超出的部分**按證據強度丟棄**，不再只是記錄 overflow。
2. **Relay 窗口分段合併**（class B）：短於一個 124 幀 Relay 窗口的 Segment 會用自己的 seed 冷啟動自己的 H3 請求。粉紅裙那支實測 `1.589 s + 11.420 s + 0.559 s` 三段三顆 seed，只有中間那段落地。現在碎片會融合，同一個 job 的所有 Segment 共用一顆 Relay seed。
3. **QC 的頭部圖層否決權**（class C）：只重建 head/face 圖層、而且離 Picture 1 比 `CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR = 0.5`（`smart_render_worker.py:375`）更遠的 take，從 advisory 通過改成 **blocking**，換新 seed 重搖。
4. **多角色錯置保護**（class D）：SAM3.1 配對分數低於 `SAM31_MIN_MATCH_SCORE = 0.7`（`smart_render_worker.py:403`）時改用 raise 要人工框，不再拿 delta 兜底去合成一副不可信的身體；reference framing class 改成**每個 Shot 量一次**，同一 Segment 的每條 pass 講同一種相機語法。
5. **Preview 輸出增強器回滾**（class E）：見 Round 67 —— `H3_CHARACTER_SWAP_PREVIEW_VSR` 變成要指名才開。
6. **參考圖變不透明**（class F）：透明裁切圖曾被渲染成軟邊鬼影；alpha 先壓到白底，pass 列記錄有壓。
7. **Identity Sheet 視圖來源**（class G）：rear／side 畫稿只讀有標那個視圖的 layout（Round 75 修的是它必須以**可解析的路徑**送給引擎，見下一條）。
8. **畫布對齊 H3 網格**（class H）：480 bucket 的 2x 是 576×866，跟每張 H3 bucket 幀的 576×864 差兩列；Preview 組裝现在 snap 到 `PREVIEW_CANVAS_MULTIPLE = 16`（`smart_render_worker.py:3697`）。
9. **`vanilla` 成出廠預設 route**（class I）：`CHARACTER_SWAP_ROUTE_DEFAULT = CHARACTER_SWAP_ROUTE_VANILLA`（`character_swap_engine.py:481-482`）——author template 逐字原樣上線，與手動圖的文字**byte-for-byte 相同**（2 876 字元），Silent Shot 唯一允許的 append 是 silent listener 契約。

**政策版本**：`SMART_RENDER_POLICY_VERSION` 88 → **89**（`smart_render_worker.py:325` 與 `director_cut_studio.py:963` 兩側同步，註解逐項列出 (a)–(g) 的語意變化）。88 之下編出来的 prompt、分段邊界、QC 判定、畫布全部作廢；graph json 照導演要求不動。**注意**：Round 66 的快照也曾把 88→89，但那一版被 undo，所以 89 的歸屬是 Round 69。

**驗證（2026-11-02 補登記時重跑）**

- `testing\test_round69_manual_parity.py` 本身 78 項（外加從 Round 52 匯入的 48 項）；以 `.codex_tmp\r69_run_tests.py` 跑 19 個 Character-Swap 相關 suite（engine／QC advisory／routes／age lock／source-look ownership／eyewear／reference detail／closeup gates／silent audio／background extra／mouth motion／transient QC／standard pipeline／staged driver／segment engine／smart render worker／identity sheet＋Round 65）＝ **569 項通過（0 failure／0 error，1 skipped，97.3 s）**，日誌 `.codex_tmp\r82_r69subset.log`。
- **界定**：源碼已修復＝這九項都有測試钉住「源碼送出什麼」；**影片未實機**＝這九項疊起來之後的 Studio Preview 有沒有真的變得跟 `character-swap_00042_` 一樣，目前沒有一支新片子證明（本輪與 Round 75、81–83 都是 0 槍）。

### Round 67：把 RTX Video Super Resolution 接到 Preview 的「答案」上，不是參考圖上（2026-11-01 約 14:17，**源碼已修復；同日被 Round 69 關成預設 off；影片未實機（本輪 0 槍）**）

**這一輪當時沒有登記**：快照 `_backup\r67_20261101_preview_vsr_output\`（引擎檔 mtime 2026-11-01 14:17）內的 `CHANGELOG.md` 最後寫入 13:42、頭仍停在 Round 65 ⇒ 本輪的條文從未進過 CHANGELOG，只在產品碼的註解裡活著。以下依據 `character_swap_engine.py:117-135` 那段 design note 重建。

**動機**：導演的 Preview 迴路是一個成本／可讀性的取捨——`PREPARE_RESOLUTION_HIGH` 釘在 `"480"` 讓 0.5 MP 草稿便宜到能反覆試，代價是一張 576×864 的 take 用眼睛看是軟的。RTX VSR 不是第二次 diffusion，它是模板已經信任的那顆 NVFX 硬體增強器（原本只用在 Picture 1），所以在 Relay 已經-publish 幀、`CreateVideo` mux 之前跑一次，就能讓 480 bucket 的草稿在 1x 下可 grading，而不用多買一代生成。因此它只掛在 Preview 渲染上，Final Render 刻意不掛：會自己發明細節的增強器可能添加參考圖沒有的褶皺，而 Final take 必須就 H3 實際產出的東西被 grading。

**改動（只動 Studio 編譯出的 graph／pass；使用者的 `H3-Character-Swap-Relay-V2-api.json` 一個字沒改）**

- 輸出端常數組：`CHARACTER_SWAP_OUTPUT_UPSCALE_CLASS`（與參考圖那顆同 class）、node id `rtx_vsr_output`、title `RTX Video Super Resolution - Preview Output`、`CHARACTER_SWAP_OUTPUT_UPSCALE_DEFAULT_SCALE = 2`、`resize mode = "scale by multiplier"`，以及附圖 fallback 的 quality／strength／encoding 釘值（`character_swap_engine.py:140-177`）。
- pass 列自證一組 contract 欄（`CHARACTER_SWAP_OUTPUT_UPSCALE_CONTRACT_KEYS`，由 `CHARACTER_SWAP_OUTPUT_UPSCALE_ROW_DEFAULTS` 生成，:187-218），reason 取值 `not_preview_request` / `environment_disabled` / `no_image_input_to_upscale`（:182-184）。
- 開關解析 `character_swap_output_upscale_switch()`（:3432）讀 `H3_CHARACTER_SWAP_PREVIEW_VSR`：肯定型（`on`/`1`/`true`/`yes`/`enable`/`enabled`）或裸倍率（`=4` 同時表肯與要 4x）才開。
- 掛載路徑做成冪等：先找 muxer 再插，找不到 muxer 而Save 節點本身就在末端時直接接；圖裡沒有可接的影像輸入就老實回報 `no_image_input_to_upscale`。

**同日的反轉（並進 Round 69 第 5 項）**：導演分級兩支 take 的**背景**長出手動 ComfyUI 同 clip 同 seed 从未出現的蜂窩格，而輸出增強器是線上唯一能發明它的東西；它的 2x 輸出又是 576×866，跟每一張 H3 bucket 幀的 576×864 差兩列，拼出來的 Preview 跟被 grading 的那張不是同一張畫布。所以節點改成**出廠 off**，`H3_CHARACTER_SWAP_PREVIEW_VSR` 變成 opt-in；未設、空白、解析不了的輸入一律 off，絕不會把增強器偷偷放回一張正在 grading 身分的 take 上。

**今天的測試背書**：`testing\test_round69_manual_parity.py` 的 `PreviewOutputEnhancerRollbackTests`（class E，12 項：出廠常數、沒人命名時就是 off、contract 欄等於出廠預設、開啟時重接 muxer 並如實回報、掛兩次冪等、Final Render 永不買增強器、env 可否決 preview 請求、缺影像輸入的回報、非 muxer 後 Save 的直接掛載、顯式倍率記為 environment、呼叫點接線）。

**界定**：源碼層面「有這顆節點、預設 off、env 可 opt-in、Final 永不掛」已被測試钉住；**影片端**從未驗證過開起來能否讓 480 草稿變清晰而不發明星景——本輪與 Round 69 都是 0 槍。

### Round 66：Preview 不被年齡鎖抬到 768（2026-11-01，**當天曾被導演整體 undo；留下的是導演的 480 手工釘值；本輪 0 槍**）

**用戶分級**：「這一次非常完美了，只是有一個缺點就算 preview 使用 768 解像度，而不是原裝的 480，造成 preview 時間特別久，請改正這一點，完成後更新 readme、changelog、version v0.3.8-alpha.5，我就可以上載 github」。

**根因**：`_5` 那支 Preview 自己的 `render_manifest.json` 就是證據：`request_kind="preview"`、`requested_megapixels=0.5`、`effective_megapixels=1.0`、`megapixel_floor_reason="apparent_age_lock"`、`relay_prepare_resolution="768"`。Preview 與正式渲染走同一條編譯路徑，Round 53 那條「這個 pass 承諾了外觀年齡 ⇒ 地板 1.0 MP」的**自動**地板照樣落在草稿上，0.5 MP 只是請求值。

**改動（當時）**：新增 env 旋鈕 `H3_CHARACTER_SWAP_PREVIEW_MIN_MEGAPIXELS`（出廠 `0.0`＝草稿不設地板，`1.0`＝把 768 買回來，放進 `DESIGN_ENV_RENDER_KNOBS` 白名單）；`character_swap_megapixel_decision(..., preview_request=False)` 多一條優先序（通用旋鈕 ＞ 預覽分支 ＞ 外觀年齡鎖 ＞ 出廠預設）；`compile_character_swap_pass(..., preview_request=...)` 在 contract 多一列 `preview_request` 讓 Job／manifest 自證；`director_cut_studio._compiled_character_swap_window_job(..., preview=...)` 由 `_build_smart_render_job` 以 `request_kind=="preview"` 送旗。

**後續（重要）**：這套 plumbing 在導演 graded「效果完全失敗，請 undo 全部去上一次的代碼」之後**被整體回收**。今天的樹裡找不到 `H3_CHARACTER_SWAP_PREVIEW_MIN_MEGAPIXELS`、找不到 `testing\test_round66_preview_bucket.py`（29 項）、contract 也沒有 `preview_request` 欄；`VERSION` 也沒有升到 `0.3.8-alpha.5`。留下來的只有兩件事：（a）導演親手把 `character_swap_engine.py:3807-3808` 的 `PREPARE_RESOLUTION_HIGH` / `PREPARE_RESOLUTION_LOW` 都釘成 `"480"`（指令：「請不要再改這一點」），（b）`character_swap_engine.py:182` 的 `OUTPUT_UPSCALE_REASON_NOT_PREVIEW = "not_preview_request"` 這個殘留常數（Round 67 的輸出增強器後來在用它）。完整條文存檔在 `_backup\r66_20261101_preview480_pre_undo\CHANGELOG.md` 第 19–48 行，那裡曾以 `## [0.3.8-alpha.5] - 2026-11-01` 發布，全套 1 188 項綠（278.6 s）。

**今天必須知道的後果**：因為**兩個** prepare bucket 都被釘在 `"480"`，768 這個 bucket 已經不可達 ⇒ Round 53 那條「用解析度買年齡准确度」的防线現在只剩 prompt 文字在做事；`0.5 MP` 與 `1.0 MP` 的請求都會在 480 prepare。這是指導方針，不是 bug，本檔案往後每一輪都要照此前提解讀。

**界定**：源碼層面這條路已被 undo，只餘手工釘值；影片端「Preview 回到 480 之後省多少時間」由 `_5` 的實際體驗證明，本檔案不再宣稱測試背書。

### Round 65：把「必須戴眼鏡」從強制條款改成「臉上不許有任何東西」，眼镜从此不再由 V1 提供（2026-11-01，**源碼已修復＋新增 19 項測試通過，全套 1 159 項綠；影片已實機驗證（本輪 1 槍）**）

**用戶分級**：policy 87 那一槍（master seed 6401000000000000001）＝「這一次最完美，只是畫面出現眼鏡，幫我修復掉，不要在畫面強制放入眼鏡」。

**根因**：`LEAN_EYEWEAR_WORN`（`DRAWN EYEWEAR STAYS WORN`）把「P1 畫了眼鏡 ⇒ 每一幀都得戴著」寫成強制條件。P1 畫的是無框小橢圓，模型要滿足這條只能去 `<Video 1>` 撿那副粗黑方框眼鏡——0–2.5 s 沒戴，約 3 s 起變成 V1 的粗黑框，9 s 時一片鏡片掛在下顎。也就是眼鏡不是畫錯，是被條款逼出來的。

**改動（只動 Studio 編譯出的附錄，用户的 `H3-Character-Swap-Relay-V2-api.json` 一個字沒改）**

- 新增 env 旋鈕 `H3_CHARACTER_SWAP_EYEWEAR`（`uncovered` 預設／`worn` 舊行為／`neutral` 完全不提），附別名表與 `character_swap_eyewear_policy()` 解析；打錯字一律回落到 `uncovered`。
- `LEAN_SOURCE_LOOK_OWNERSHIP` 的結尾句改成模板槽 `headwear only if Picture 1 draws it{eyewear}.`，`worn` 才追加眼鏡子句。
- 新增 `LEAN_EYEWEAR_UNCOVERED`（`THE FACE STAYS UNCOVERED — MANDATORY`，430 字元，比 worn 的 448 短）：把「臉上是完整的畫」講成正面圖像，並明說被擦掉的演員的眼鏡不得殘留。
- `DETAIL_KEEP_LISTS`／`detail_keep_list()`：只有 `worn` 的保留清單裡有 "spectacle"，`uncovered`／`neutral` 用不含眼鏡字的清單。
- `build_character_swap_prompt(..., eyewear_policy=...)`；route 1 依政策插入對應子句，route 2 與 legacy 完全不動。Lean audit 新增 `eyewear_policy`、`eyewear_clause_shipped` 兩欄。
- `SMART_RENDER_POLICY_VERSION` 87 → 88（`smart_render_worker.py` 與 `director_cut_studio.py` 同步）。

**驗證**

- 離線：`test_round65_eyewear_optional`（19 項：解析器／別名／錯字／env 優先序、預設只送一次裸臉子句且位置在 `FINAL MEDIUM PRIORITY` 之前、缺席事實、keep-list 只在 worn 有 spectacle、neutral 不講話、route2／legacy／遮板／真人化閘門、子句比 worn 短、附錄 ≤4545、兩側 policy 88）＋ `test_round57_eyewear_and_age`／`test_round54_source_look_ownership` 共 **52 項 OK**；再跑 9 個相關 suite **311 項 OK**；全套 **1 159 項通過（0 failure／0 error，10 skipped，269 s）**，日誌 `logs\r65_full_suite.log`。
- 送出 prompt 的實際數字（route 1）：uncovered 附錄 4 532／prompt 7 876；worn 4 545／7 889；neutral 4 042／7 386。預設下 "glasses"、"spectacle" 在送出文字中出現 **0 次**；`dropped_tail_clauses=[]`、`over_budget=False`。
- **實機（1 槍）**：`_4` 專案，Job `preview_1482118348682408297_1793500493650525500.job.json`，policy 88，0.5 MP 請求 → 1.0 MP 生效（`apparent_age_lock` 地板），prepare 768，identity sheet preset 8 fullfig，attempts 1，跑完 driver 自帶 `/free`。0.5／1.5／3／6／9／12 s 抽幀（`working\r65_grade\`）：**6/6 全部裸臉，零眼鏡、零镜片、零眼鏡陰影**；P1 的禿頭＋三根呆毛＋額紋＋黑金背心＋青藍長袍＋黃格紋未回退，卡通媒介未漂移，背景無蜂窩。
- 已知殘留（本輪未處理，與 policy 87 相同）：虹膜偏寫實、手偏寫實、Silent Listener 的嘴部動作 advisory（`silent_mouth_audit` 相對於乾淨 plate 超限，`advisory_only`，不重試）。

**回退**：`$env:H3_CHARACTER_SWAP_EYEWEAR="worn"` 即回 policy 87 的強制戴眼鏡行為（policy 版本仍 88，audit 欄位會顯示 `eyewear_clause_shipped=True`）。

### Round 64：policy 87 的第一槍——headless 重建 Job 讓正面前綴真的送到 ComfyUI（2026-11-01，**影片已實機驗證（本輪 1 槍）**）

- Smart Render Job 把組裝好的 prompt 當**資料**存在 `segments[i].workflow.reference_conditioning.inputs.prompt`，所以「重跑舊 Job」只会重跑它出生時的文字；要測 Round 62/63 的正面前綴，必須用當前工作樹重新編譯。`working\r64_build_policy87_job.py`（351 行）就在做這件事：開真的專案、走真的 `_build_smart_render_job(request_kind="preview")`，再把寫出來的 Job 讀回並稽核**實際送出**的 prompt。
- 稽核內容：aging／texture 名詞計數（含 Studio 附錄單獨計）、必需正面子句、clause header 清單與 policy-84 分級基準逐項對比、`prompt_budget`／identity sheet／upscale／prepare／req-eff MP 全部記錄；有任何問題就不保留 Job。
- **實機（1 槍）**：seed 6401000000000000001，policy 87，0.5 MP→1.0 MP 生效，prepare 768，attempts 1。導演分級＝「這一次最完美，只是畫面出現眼鏡」→ 催生 Round 65。

### Round 63：把八處重複重申的句子砍掉，policy 86 → 87（2026-11-01，**源碼已修復；影片未實機（本輪 0 槍）**）

- Round 62 把負面清單換成正面描述之後，同一件事被講兩次的地方就變成純長度。本輪逐條比對八處子句站點，刪除重複重申：五個常數小計 **1 696 字元（−239）**，八處子句站點合計 **3 095 → 2 962**。
- `SMART_RENDER_POLICY_VERSION` 86 → 88 之前的中間值 87；全套 **1 138 項通過（0 failure／0 error，10 skipped）**，日誌 `logs\r63_full_suite2.log`。
- 工具：`working\r63_measure_pins.py`／`r63_check_pin_strings.py`（測試裡钉死的字串與產品碼逐字比對，防止「測試钉的是舊句子」）。

### Round 62：七個 aging 名詞＋七個 texture 名詞全部改寫成正面描述，policy 86（2026-11-01，**源碼已修復；影片未實機（本輪 0 槍）**）

- **根因**：Round 56–58 對齊過那支「效果很好，唯一問題＝老人化」的送件 prompt（8 204 字元）——author template（用戶的官方模板）0 個 aging 名詞、0 個 texture 名詞，7＋7 全在 Studio 附錄。模組自己的 canary 早就寫明「點名一個物件會 steer 出這個物件」，所以 `NO WRINKLES / NO STUBBLE / NO HONEYCOMB` 這種 do-not-add 清單本身就是在請模型畫出來。
- 改動：`NO INVENTED DETAILS` → `EVERY DETAIL COMES FROM PICTURE 1`、`NO INVENTED TEXTURE` → `SURFACE PROVENANCE` 等**八處**改寫，共 **+127 字元**；保留原本各自的 gate（route、遮板、真人化），不動 route 2 與 legacy。
- `working\r62_draft_clauses.py`／`r62_measure_clause_deltas.py`／`r62_clause_sizes.py`／`r62_verify_trim.py` 负责草稿、增重與尺寸稽核；送件基準存檔 `working\r62_submitted_prompt_pol84.txt`（後續各輪的對照基線）。
- 快照：`_backup\V0.3.8-alpha.3_policy86_round62_negative_clauses_pre_fix_20261101\`。

### Rounds 60–61：本輪只造工具與對帳，零產品碼（2026-11-01，**影片未實機（本輪 0 槍）**）

- Round 60：`working\r60_compare_manifests.py` 把四槍的 manifest 逐欄對帳（prompt_budget／prepare／req-eff MP／target similarity／attempts／upscale 欄），確認「老人化」的差異不在 Studio 附錄的長短上；`r60_*` 其餘腳本做行尾與文档格式核對。
- Round 61：`working\r61_submitted_graph.py`＋`r61_graph_diff.py` 發現 Relay 模板在 2026-10-29 22:26 被整組換過（PRISM merge 取代官方 ref2va checkpoint、int8 video VAE、0.8 的新 8-step turbo、Picture 1 上多了一顆 ULTRA strength 1.0 的 RTX VSR），這是 Studio 與用戶手動 ComfyUI 效果差距的唯一可單動變數；`r61_build_official_stack_job.py` 產出**只回退這四項**的候選圖 `working\r61_candidate_relay_official_stack.json`，錨定在存活的 policy-84 Job 上，prompt 不會漂移。本轮未開槍。

### Round 59：參考圖上採那顆節點的 `quality`／`strength` 變成 env 旋鈕，identity sheet 臉面板的「真實畫了多少畫素」進 manifest（2026-11-01，**源碼已修復＋新增 26 項測試通過；影片未實機（本輪 0 槍）**）

**A. 用戶訴求與本輪結論**

- 接著 Round 58 的逐幀對照，剩下的残差是「臉不像 P1」。本輪先把這筆帳算清楚，再只發布**能改變送進模型的資訊**的槓桿。
- 量測鏈（全部從 `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4` 的 media pool／sidecar／manifest 讀出，可重跑 `working\r60_compare_manifests.py`）：

| 環節 | 實測 |
| --- | --- |
| P1 原圖 | `media\imported\P1_2d515d5f365e_…_n.jpg` = 252×370 = **0.09324 MP**，13 427 B（媒體池**只有這一張** P 圖） |
| identity sheet | preset 8，800×1216 = 0.9728 MP，`head_coverage 0.5259`（sidecar `cache\identity_sheets\image_137_…_v8.png.identity_sheet.json`，cutout `.director_cache\image_137_2dac3b44b5a595d3_nobg.png`） |
| 臉面板真藝術 | sidecar `source_crop [16,1,194,153]` ⇒ **178×152 = 0.02706 MP** |
| 臉面板版面 | 774×662 = 0.51239 MP ⇒ **線性 4.35×**（面積 19.6×） |
| 衣服面板 | 250×217 = 0.05425 MP → 0.40248 MP ⇒ 線性 2.72× |
| 輸出需求 | V1 plate 頭部覆蓋 **0.214413** × 1.0 MP = **0.21441 MP** ⇒ 真藝術的 **7.9× 面積／2.81× 線性**（就算 0.5 MP 仍有 2× 線性） |
| 中繼節點 | 模板 node `reference` LoadImage → node **9 `RTXVideoSuperResolution` `scale=2, quality=ULTRA, strength=1.0`** → `ref_images.ref_image_0`，`ref_image_size="match"` |

- 機制判斷：`ULTRA` 是**生成式**增強，不是插值。餵 0.09 MP 的縮圖時它必須猜參考圖裡從不存在的臉部微細節，而卡通臉上被猜出來的微細節就讀成皺紋、胡渣、老人 —— 與 Round 57 那條年齡鎖壓的是同一個症狀，但一個在 prompt 端、一個在像素來源端。
- **同時否決兩條看起來最省事的槓桿**（避免以後被當成「還沒調的開關」）：`IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS` 出廠 0.35 已經大於 P1 的 0.09324 ⇒ 地板早就在觸發、preset 已被強制 8，所以「再調 layout／preset」對這一案是 no-op。本輪因此不發布任何不會改變數字的改動。

**B. 改碼（三個檔案；全部是「env 旋鈕＋記錄」，未設 env 時 ComfyUI workflow 與已驗證基線 byte-identical ⇒ 不影響推 GitHub）**

- `character_swap_engine.py:82-116`：新增 `CHARACTER_SWAP_REF_UPSCALE_QUALITY_ENV = "H3_CHARACTER_SWAP_REF_UPSCALE_QUALITY"` 與 `CHARACTER_SWAP_REF_UPSCALE_STRENGTH_ENV = "H3_CHARACTER_SWAP_REF_UPSCALE_STRENGTH"`。quality 的接受值就是已安裝節點公布的 `nvvfx.QualityLevel` 成員（`BICUBIC`／`LOW`／`MEDIUM`／`HIGH`／`ULTRA`／`HIGHBITRATE_*`／`STREAMING_*`），strength 上限 `1.0`。
- **`DENOISE_*`／`DEBLUR_*` 故意不提供**：那兩種模式保持**輸入尺寸**，選了就等於悄悄把讓 Picture 1 變清晰的 ×2 取消掉，一次動兩個變數。`BICUBIC` 之所以提供，是因為它是清單裡唯一「只插值、不增強」的模式 —— 那才是老實檢驗「皺紋是不是 ULTRA 畫出來的」的做法。
- 編譯段 `:3269-3364`：三個旋鈕各自解析來源（`template`／`override`），寫 **6 個 record-only contract 欄** `reference_upscale_{quality,strength}{,_source,_override}`（`:3359-3364`）；`reference_upscale_scale*` 三欄是 Round 50 舊有、本輪不動。
- `director_cut_studio.py`：旋鈕進 `DESIGN_ENV_RENDER_KNOBS`（`:465-470`），快取辨識 key（`:1886-1890`），pass row 只轉發、不自行決定（`:37749-37786`）。
- 新度量：`character_identity_sheet.py:470` dataclass 欄位＋`:485` `source_head_crop_megapixels(panels)`（讀臉面板的 `source_crop`；舊 sidecar 在 `:1957-1959` 就地重算），compose 時寫入 `:2155/2181`；Studio 對應 `identity_sheet_source_head_crop_megapixels`（`director_cut_studio.py:35661-35663`）。它與既有 `identity_sheet_source_head_coverage`（`:35467-35472`，那是 **V1 clip** 的頭部覆蓋）和 `…_reference_head_coverage`（P1 自己的覆蓋）是三個不同的東西，別再混。
- `SMART_RENDER_POLICY_VERSION` **保持 86**：record-only 的 pass row 本來就會經過 `content_fingerprint({... "passes": pass_rows ...})`，欄位新增已能被快取辨識；86→87 會把 `example\` 既有 R2V 快取一起打掉，得不償試。

**C. 界定（必須區分）**

- **源碼已修復**：兩個 env 旋鈕的解析與邊界、6 個 contract 欄、Studio 轉發與 key、臉面板真實畫素度量 —— 全部落碼且有測試覆蓋；未設 env 時模板一字不動。
- **影片未實機**：本輪 ComfyUI **零請求**；`H3_CHARACTER_SWAP_REF_UPSCALE_QUALITY=BICUBIC`、`..._STRENGTH=0.4`、`..._SCALE=3` 三個實驗**一個都沒跑過**。「皺紋因此消失」目前只有機制推論，沒有片。
- **性價比排序（要對用戶講明白）**：① 重新匯入高解析 P1（≥0.35 MP，最好 ≥1 MP）是**唯一會增加資訊**的修法，零 GPU；② `QUALITY=BICUBIC` 一槍；③ `STRENGTH=0.4-0.5` 一槍；④ `SCALE=3` 一槍；⑤ seed 抽卡（最弱，因為它不改變 4.35× 這件事實）。
- **成本**：那一鏡 12.86 s 在 1.0 MP／768 一槍約 22 分鐘；跑前照 §12 三條硬約束走 `staged_model_driver.py`，跑完自帶 `/free`。改完碼要**先重啟 Studio** 再自己按 Preview。
- **仍未表態的用戶項**（不要擅自動）：圓眼鏡形狀漂移（R57 已改措詞，待導演分級）；禁止發明的額頭皺紋／維持參考圖年齡（同上）；衣柜相對地板 0.12；silent 嘴部容差。

**D. 測試／編譯／快照**

- 新建 `testing\test_round59_reference_detail.py` **26 項全綠**：`ReferenceUpscaleKnobParsingTests` 8、`CompiledPassReferenceUpscaleTests` 6（未設 env ⇒ contract 記 `template` 且 workflow 不變；設 BICUBIC／strength 0.45 ⇒ 節點輸入真的被改寫且來源記 `override`）、`HeadCropMegapixelsTests` 5、`ComposedSheetReportsReferenceDetailTests` 2、`StudioRegistrationTests` 4（含「Studio 只轉發」）。
- 回歸（本輪實跑）：`test_identity_sheet.py` **67 OK**、`test_character_swap_engine.py` **96 OK**、`test_round54_source_look_ownership.py` **14 OK**、`test_round57_eyewear_and_age.py` **17 OK**（模組級合計 220）。**本輪未跑全套**：全套最後一次是 Round 53 的 1081；`test_director_timeline` 會打真實端點，01:47 起的那一輪卡住約 75 分鐘（見 Round 58）。
- `py_compile`：`character_swap_engine.py`／`director_cut_studio.py`／`smart_render_worker.py`／`character_identity_sheet.py`／`staged_model_driver.py` ＋ 3 支 test 全過（exit 0）。
- 快照：`_backup\V0.3.8-alpha.3_policy86_round59_reference_detail_pre_run_20261101\`（四支產品碼＋模板＋CHANGELOG＋HANDOFF＋VERSION＋三支 test＋driver）。

**E. 本輪工具**：`working\r60_compare_manifests.py`（四槍 prompt／bucket／相似度對帳）、`working\r60_append_probe.py`（policy 86 那槍的 prompt_budget 逐欄展開）、`working\r60_job_prompt_marks.py`（job 存檔 prompt 裡各條款的出現位置）、`working\r60_clause_lengths.py`（三個款式的字元數與新舊對照）。本輪 ComfyUI 端**零請求**。

### Round 58：policy 85 vs 86 逐幀 A/B 讀片 —— 眼鏡與蜂窩背景的目視證據（2026-11-01，**產品碼零改動；本輪 0 槍；讀片為助理判定，非導演分級**）

**A. 目的**

- Round 57 那兩條款式的效果不能只靠 manifest 的數字判斷，必須看幀。本輪把 policy 85（00:38 那槍）與 policy 86（01:38 那槍）各抽 0.5／3／6／9／12 s 五張幀並排，專看三件事：**眼鏡在不在、額頭皺紋深浅、蜂窩背景有沒有減少**。

**B. 工具與產出**

- `.codex_tmp\r58_montage.py`（五張幀拼臉）、`.codex_tmp\r58_sweep.py`（橫掃幀帶）；ffmpeg `C:\ffmpeg\bin\ffmpeg.exe`；輸出 `.codex_tmp\r58_frames\r58_faces.jpg`、`r58_full.jpg`、`r58_sweep_n86.jpg`、`r58_sweep_o85.jpg`。腳本要 `sys.path.insert(0, ROOT)` 才能 import 產品碼。

**C. 助理讀片結論（不是導演分級，僅供選下一槍的方向）**

| 觀察項 | policy 85（seed 8178175072880861825） | policy 86（seed 755358368423936257） |
| --- | --- | --- |
| 眼鏡出現的幀數（5 張中） | **0／5** | **3／5**（6.0／9.0／12.0 s） |
| 眼鏡形狀 | — | 圓 → 方有漂移 |
| 額頭皺紋 | 比 P1 深 | 比 P1 深（兩邊都有） |
| 蜂窩狀背景 | 明顯 | **大幅減少** |
| `target_reference_similarity` | 0.668491 | 0.686148 |

- 必須寫明的限制：兩槍 **master seed 不同** ⇒ 這是**方向性對照**，不是受控 A/B；「眼鏡回來了」要成立，得在同一 seed 上再打一槍或由導演讀片採納。評斷基準以 P1 為準：P1 本身就有三條淺額頭線＋圓框眼鏡＋黑金背心、藍褲、黃格紋襪。

**D. 全套守門的插曲（與產品碼無關，但要留帳）**

- `test_director_timeline` 那一組會打真實端點，01:47 起跑後卡住約 75 分鐘、最後寫入 01:58（`logs\r58_director_timeline_tests.err`，41 677 B）。它的殘留行程（PID 16028 ＋ `design_ai_service.py` 子行程 16748／16840／27672／16576／28336）仍在和 Strata 搶資源。**以後全套計時不把這一模組算進去**（沿用 Round 52／53 的 `--skip test_director_timeline`）；要收掉那組行程得先問用戶。

**E. 界定**

- **源碼已修復**：本輪**零產品碼改動**，只有讀片工具。
- **影片未實機（指「未經導演採納」）**：policy 86 那槍已生成但**導演尚未分級**；「眼鏡已修好」「蜂窩已消失」都還沒有被導演認可的片當後盾。
- **本輪 ComfyUI 零請求**（只讀既有 take 的幀）。

### Round 57：policy 85→86 —— 圓眼鏡條款＋年齡鎖重寫（點名禁止發明的皺紋與胡渣）（2026-11-01，**源碼已修復＋17 項測試通過；影片已實機一槍但導演尚未分級**）

**A. 用戶訴求**

- 用戶在 Round 56 那槍（分級「完美」）之後指定：「完成后繼續修『圓眼鏡』或『禁止發明的額頭皺紋／維持參考圖年齡』這類新條款」。本輪即該兩項（眼鏡**形狀**漂移尚未解決，見 E）。

**B. 改碼（`character_swap_engine.py` 兩條款式＋`smart_render_worker.py` 政策註解；policy 85→86）**

- 新增 `LEAN_EYEWEAR_WORN`（`:484`，**448 字元**）：標題 `DRAWN EYEWEAR STAYS WORN — MANDATORY`。P1 戴圓框眼鏡，但 84／85 兩槍的成片眼鏡 0／5 幀 —— 眼鏡是被「維持乾淨臉部」那類預設傾向擦掉的，不是被畫歪。
- 重寫 `LEAN_AGE_LOCK`（`:542`）：**280 字元 → 445 字元（＋165）**。舊版只講「維持參考圖年齡」，新版**點名禁止發明的東西**：疊加的額頭皺紋、眉間紋、魚尾紋、鼻唇溝、色斑、胡渣點，並要求維持參考圖的年齡與平坦卡通畫法。
- 兩條合計 **+613 字元**；與 Round 54 那條 +525 一起，正好解釋 manifest 從 `append_chars 4808` 變成 `5946`（4808＋525＋613＝5946；`prompt_chars` 8204→9342 同步 +1138）。
- `SMART_RENDER_POLICY_VERSION` **85→86**，理由寫在 `smart_render_worker.py:256-265` 的政策註解：**款式內容變了就要換政策號**，否則事後無法把「眼鏡條款有沒有在場」歸因到具體片。Project Format 保持 29、`VERSION` 保持 `0.3.8-alpha.3`。

**C. 實機一槍（本輪的片在這裡）**

| 項目 | 值 |
| --- | --- |
| manifest | `preview_755358368423936257_1793466974167283100.manifest.json`（01 01:38） |
| policy / route | **86** / `route1` |
| prompt_budget | `prompt_chars 9342`、`author_prompt_chars 3396`、`append_chars 5946`、`append_budget 4200`、`append_over_budget True`、`over_budget False`、`dropped_tail_clauses []` |
| bucket | requested 0.5 → **effective 1.0**、`relay_prepare_resolution "768"`、`megapixel_floor_reason apparent_age_lock`、`megapixel_floor_applied True` |
| 結果 | `status complete`、`attempts_used 1`、`failure_class ''`、`character_swap_identity_advisory_only true`、`target_reference_similarity 0.686148` |
| 導演分級 | **尚未分級** |

- 附带一件要記的事：`append_over_budget` 仍是 `True`（5946 > 4200），但 Round 52 之後**只記錄不裁句**，所以兩條新款式確定完整送達 —— 這正是「條款送達但模型不服從」與「條款根本沒送達」能分開的依據。

**D. 測試／快照**

- 新建 `testing\test_round57_eyewear_and_age.py` **17 項全綠**（本輪實跑複驗）：眼鏡款式的存在性與措辭黑名單、年齡鎖點名的六種發明不得被反向覆蓋、字元預算邊界、route 閘門。
- 本輪自身的狀態包含在 Round 59 的 pre-run 快照 `_backup\V0.3.8-alpha.3_policy86_round59_reference_detail_pre_run_20261101\`；本目錄非 git repo，回退靠 env 而不是 git。

**E. 界定（必須區分）**

- **源碼已修復**：兩條款式、政策號 86、contract 欄位 —— 落碼且有測試。
- **影片已實機但未經導演採納**：policy 86 已打出 1 支（01:38），助理逐幀看到眼鏡 3／5（Round 58），但**導演尚未分級** ⇒ 「老人化已被壓住」仍未成立。
- **尚未解決**：眼鏡**形狀**漂移（圓→方）；發明的額頭皺紋在 85／86 兩槍都仍然比 P1 深。
- **回退**：`H3_CHARACTER_SWAP_ROUTE=legacy` 一條回到舊胖 prompt；要回到 85 的行為請讀 manifest 政策號辨識，不要半條款式半條款式地拆。
- **下一槍怎麼跑（GPU 三條硬約束見 §12）**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4\project\render_jobs\preview_<seed>_<ns>.job.json"`。驗收順序：① manifest `render_policy_version == 86`、`relay_prepare_resolution == "768"`、`append_chars` ≈ 5 946、`attempts_used == 1`；② 才讀片評「眼鏡在不在、形狀對不對、額頭乾不乾淨、衣服像不像」。跑完 driver 自帶 `/free`。

### Round 56：Round 55 拼裝 job 的實機一槍 —— source-look ownership 條款送達後的第一支片（2026-11-01 00:39，**影片已實機＋導演分級「完美」但殘留老人化；源碼零改動**）

**A. 目的**

- 把 Round 54 那條 `LEAN_SOURCE_LOOK_OWNERSHIP` 真的送進 H3，看 V1 的假髮／cosplay 背帶會不會不再掛到 P1 身上。本輪**零產品碼**，只跑 Round 55 拼出來的 job。

**B. 這支片的帳目**

| 項目 | 值 |
| --- | --- |
| driver log | `logs\r56_source_look_driver.log`（01 00:39 收工，`/free` 已做，Qwen 由 tray 載回） |
| manifest | `preview_8178175072880861825_1793461399421021800.manifest.json`（00:38） |
| policy / route | 85 / `route1` |
| bucket | requested 0.5 → **effective 1.0**、`relay_prepare_resolution "768"`、`megapixel_floor_reason apparent_age_lock` |
| prompt_budget | `prompt_chars 8204`、`append_chars 4808`（**少記 525**，見 C） |
| 結果 | `status complete`、`attempts_used 1`、`failure_class ''`、`target_reference_similarity 0.668491` |
| 導演分級 | **「完美」**，但回報**角色仍老人化**、眼鏡不見 |

**C. 一筆必須留的帳：manifest 的 `append_chars` 不會把拼進去的條款算進去**

- 拼裝是在**編譯之後**動 prompt 的 ⇒ 該槍 manifest 記的 `append_chars 4808` 是「重新編譯時的長度」，真正送達的是 **4808＋525＝5333**。這就是為什麼 Round 59 對帳要用 5946＝4808＋525＋613 這條算式，而不是直接把兩槍的欄位相減。
- 實務結論：**凡是用 headless 拼裝打出去的槍，評斷時要手動把拼進去字元數加回 `append_chars`**；否則會誤判「條款沒送達」。

**D. 界定與下一步**

- **影片已實機且已被導演採納為「完美」**（這條路線第一次）⇒ 「路線 1 ＋ 768 bucket ＋ 乾淨 V1」的**身體、衣服、頭髮、構圖**已通過；但**老人化**與**眼鏡**兩項未過 ⇒ 直接催生 Round 57。
- 本輪 ComfyUI 請求數：**1 槍**（1.0 MP／768，約 22 分鐘）。

### Round 55：把新條款塞回「已存 Job」的 headless 拼裝工具 —— 存檔 Job 把 prompt 當資料帶著，重新編譯加不出新條款（2026-10-31 23:35，**零產品碼；本輪 0 槍**）

**A. 為什麼需要這一輪**

- Round 54 的新款式只存在於**產品碼的常數**，而 `_4` 已經存好的 Job 把 prompt 當**資料**存著（`segments[0].workflow.reference_conditioning.inputs.prompt`）⇒ 對那支 Job 重新編譯只會換 bucket，**永遠加不出那 525 字元**。要驗證 Round 54 就必須拼裝，否則測的是舊 prompt。

**B. 工具與它的自我防衛（`working\r55_build_source_look_job.py`）**

- 從產品碼讀 `LEAN_SOURCE_LOOK_OWNERSHIP`，斷言它**只有一份連續副本**（避免拼到被覆寫的第三份），再把整段字串原封不動插進存檔 prompt 的同一個位置（route-1 tail 末、`FINAL MEDIUM PRIORITY` 之前）。
- 再跑**已出貨的編譯器**重算 bucket，並斷言：graph prompt 逐字相同、bucket 不變、**只有 prepare-bucket 與那一條字串**改變、只有 master seed 變動。任何一項不符就中止，不產出 job。
- 這樣打出來的槍才是「只多一條款式」的對照組，而不是「順手換了 seed／bucket」的混合實驗。

**C. 界定**

- **源碼已修復**：不適用（零產品碼）；工具的斷言就是它的測試。
- **影片未實機**：本輪 ComfyUI **零請求**，實際的槍是 Round 56。

### Round 54：policy 84→85 —— 路線 1 補回「源片殘留造型屬於被擦掉的演員」，治 V1 假髮與 cosplay 背帶掛回 P1 頭上（2026-10-31，**源碼已修復＋14 項測試通過；影片未實機（本輪 0 槍）**）

**A. 用戶訴求與根因**

- 導讀：`_4` 那一鏡 policy 84／768 bucket（seed 5037347289670054459，31 22:41）導演分級 **「不接受」**：V1 的**紅色雙馬尾假髮＋貓耳**長在 P1 的光頭頂上、身上掛著粉色 cosplay 背帶、**眼鏡不見**；`target_reference_similarity 0.688663`（四槍裡最高）卻最差 ⇒ 相似度指標救不了「造型歸屬」這一類錯。
- 根因是 Round 52「推到重來」留下的一個**語意空洞**：路線 1 出廠 `suppressed_plate = False`（不模糊 plate），而「頭髮／服裝歸誰」那幾句原先**依賴 plate 敘述**，於是那些句子**靜默**了。結果模型看到「原片的造型還留在畫面裡」，卻沒有任何一句告訴它**那些造型屬於已被擦掉的演員，不屬於新角色**。

**B. 改碼**

- 新增 `LEAN_SOURCE_LOOK_OWNERSHIP`（`character_swap_engine.py:455`，**525 字元**）：標題 `SOURCE LOOK BELONGS TO THE ERASED ACTOR — MANDATORY`，內容點名「源片的頭髮、假髮、頭飾、戲服、配件都是被取代者的造型，一律不得轉給參考角色」，插在 route-1 附錄尾端、`FINAL MEDIUM PRIORITY` 之前；emission 掛在 `:2642-2651`（只在路線 1 且 plate 未被抑制的形狀上觸發）。
- `SMART_RENDER_POLICY_VERSION` **84→85**，理由寫進 `smart_render_worker.py:256-265`：這是一條**會改變成片行為的強制條款**，不加政策號就無法把「假髮有沒有被壓住」歸因到具體片。Project Format 保持 29、`VERSION` 保持 `0.3.8-alpha.3`。
- GPU 端照 §12 三條硬約束走 `staged_model_driver.py`；Qwen 側已是 Strata（遷移登記見 2026-10-26 那節，本輪只沿用、不重複登記）。

**C. 測試／編譯**

- 新建 `testing\test_round54_source_look_ownership.py` **14 項全綠**（本輪實跑複驗）：款式存在與位置（必須在 `FINAL MEDIUM PRIORITY` 之前）、只在 plate 未抑制的路線 1 觸發、live-action adaptation 開啟時不與之衝突、字元預算不裁掉它、舊路線不受影響。
- `py_compile` 三支產品碼全過；本輪 ComfyUI **零請求**（實際的槍在 Round 56）。

**D. 界定（必須區分）**

- **源碼已修復**：條款落碼、位置與閘門有測試釘選、政策號已換。
- **影片未實機（本輪 0 槍）**：本輪只產出代碼與測試；那 525 字元**第一次真的送進 H3** 是 Round 56 的事，而且當時是靠 Round 55 的拼裝才送進去（存檔 Job 本身不含新條款）。
- **仍未表態的用戶項**：圓眼鏡形狀漂移；禁止發明的額頭皺紋／維持參考圖年齡（下一輪做）；衣柜相對地板 0.12；silent 嘴部容差。

### Round 53：prepare bucket 改由「這一個 pass 有沒有承諾年齡」決定，根治 0.5 MP 老人化（2026-10-31，**源碼已修復＋1081 項測試通過；影片未實機（本輪 0 槍）**）

**A. 用戶诉求與結論**

- 用戶在 `a_cartoon_character_with_a_black_shirt_and_yellow_pants_4` 回報：「這一次效果完美，只會被替換的角色的還是會發生老人化的問題，只要修正這個我就可以馬上更新 github」。本輪即該一項的落地，**只動 bucket 判斷，不動 prompt 措辭、不動政策號、不動 Project Format**。
- 根因不是條款沒送達，而是** prepare 的解析度 bucket**。同一張 identity sheet、同一組框架、同一套條款下：480 bucket 那一槍老人化、768 bucket 那一槍被導演採納。

**B. 乾淨 A/B（老人化那一槍 vs 已採納那一槍）**

| 項目 | 老人化（`_4`） | 已採納（`preview_923011207`） |
| --- | --- | --- |
| `relay_prepare_resolution` | **480**（take 576×864） | **768**（take 800×1216） |
| requested / effective MP | 0.5 / 0.5 | 1.0 / 1.0 |
| identity sheet | preset 8，800×1216，`source_fingerprint a7d8b999cf3e69a3` | 同一張 |
| 框架數 / 嘗試次數 | 307 / 1 | 307 / 1 |
| `APPARENT AGE LOCK — MANDATORY` | 已送達 | 已送達 |
| `failure_class` | `''` | `''` |

兩邊條款都在 ⇒ prompt 不是變因；bucket 是唯一還活著的變因。同時也**否決了那個最誘人的條件式修法**（「只在大臉／特寫抬 bucket」）：老人化那一鏡是 **medium**（design_plan `medium`×9、`face_dominant_closeup` false），特寫導向的規則永遠不會在需要它的這一鏡上觸發。

**C. 改碼（`character_swap_engine.py`＋`director_cut_studio.py`）**

- 新增 `APPARENT_AGE_LOCK_PROMPT_MARKER`（`"APPARENT AGE LOCK"`）、`APPARENT_AGE_LOCK_MIN_MEGAPIXELS = 1.0`（不用剛好跨過的 0.75，因為 bucket 一樣、但 manifest 要讀起來像它那張對照組），以及三個理由常數 `environment`／`apparent_age_lock`／`shipped_default`（`character_swap_engine.py:2783-2818`）。
- 新增 `character_swap_megapixels_floor_override()`（`:2849`）：把「操作者沒表態」與「操作者明確說 0」分開 —— 兩者從 `floor()` 都返回 `0.0`，只有這一支分得出來。公開的 `character_swap_megapixels_floor()` 語義**一字未改**（未設 → 出廠 0.0）。
- 新增 `character_swap_apparent_age_lock_in_prompt()`（`:2875`）：偵測**編譯後**的文字而不是 Shot 的旗標 —— 要付錢的是真正送進 H3 的那個承諾。路線 1 的精簡版與 legacy 的完整版用同一個 heading，且 `apparent_age_lock` 沒有 drop rank，所以 marker 缺席就代表這一 pass 真的沒許過年齡（live-action adaptation、路線 2），而不是被長度守門裁掉。
- 新增 `character_swap_megapixel_decision()`（`:2889`）：優先序 **明確 env 覆寫（含 `0`）→ 年齡條款地板 → 出廠預設**；請求**永不降低**（2.0 MP 仍是 2.0）。回傳 `requested_megapixels`／`megapixel_floor`／`effective_megapixels`／`megapixel_floor_reason`／`megapixel_floor_applied`。非數字的請求退到地板而不是小 bucket（小 bucket 才是讓角色變老的那一個）。
- `character_swap_effective_megapixels()`（`:2942`）新增 **keyword-only** 的 `apparent_age_lock`，預設 `False` ⇒ Round 52 之前寫的所有呼叫方看到的仍是 Round 52 的世界。
- `compile_character_swap_pass`（`:3015-3019`）改用 decision；contract 多四欄 `megapixel_floor`／`megapixel_floor_reason`／`megapixel_floor_applied`／`apparent_age_lock_in_prompt`（`:3189-3196`），`requested_megapixels` 原樣保留。`director_cut_studio.py:37698-37712` 把四欄同步寫進 pass row。
- 理由要分開記是有意義的：`effective_megapixels` 單獨看無法區分「導演自己要求 1.0」與「Studio 不肯在 0.5 MP 的 bucket 上讓角色變老」，而那正是 70 分鐘那筆帳的全部問題；把 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 設成逃生口時，也必須能從 manifest 證明「旋鈕有在場，只是這次沒動數字」。

**D. 成本、快取與 ESTIMATE（要對用戶講明白的三件事）**

- **一槍變貴**：那鏡 12.86 s 原本 0.5 MP 約 9-10 分鐘，現在帶年齡條款的 pass 一律走 1.0 MP／768，約 22 分鐘。不要的時後 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 一條還原 Round 52 的定價。
- **舊 take 不會被復用**：pass row 進入 `content_fingerprint({... "passes": pass_rows ...})`（`director_cut_studio.py:37798`），欄位新增＋workflow 的 bucket 改變 ⇒ 之前 480 bucket 的已存 take 不會被當快取命中（預期行為，不是 bug）。
- **ESTIMATE 會先低估**：`project_workspace.py:494` 的 `estimate_resources` 依 profile 校準、不含 MP，所以 1.0 MP 的頭幾槍預估時間會偏低，之後由 `record_resource_sample` 自我修正。
- `SMART_RENDER_POLICY_VERSION` **保持 84**、Project Format 保持 29：事后歸因靠 contract 的 `megapixel_floor_reason` 這一欄，政策號不動可讓 `example\` 既有 manifest 繼續互相比對（沿用 Round 52 的裁量）。`smart_render_worker.py` 不重新編譯 swap workflow，因此本輪無需改動。

**E. 測試／編譯／快照**

- 新建 `testing\test_round53_age_lock_bucket.py` **30 項全綠**：`AgeLockMarkerTests` 7（含「長度守門永不裁掉 age lock」：舊路線最大形狀 13 145 字元、`over_budget=True`、裁了三條仍留 marker）、`MegapixelDecisionPrecedenceTests` 9、`MegapixelKnobParsingTests` 4、`CompiledPassBucketTests` 5（真 V2 模板：路線 1＋0.5 MP ⇒ 768／reason `apparent_age_lock`／applied True；live-action＋0.5 MP ⇒ 480／`shipped_default`；env=0 ⇒ 480 且 reason 仍是 `environment`）、`StudioContractRowTests` 2（含「Studio 只轉發、不自行決定 bucket」）、`EarlierRoundRegressionTests` 3（Round 51 的 env 地板與畸形值退回出廠值、Round 52 的 0.5 MP 定價都仍在）。
- 全套守門：`working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **RAN 1081、failures=0、errors=0、skipped=10、exit 0（253 s）**（基線 1 051＋本輪 30）。
- `py_compile`：`character_swap_engine.py`／`director_cut_studio.py`／`smart_render_worker.py`＋新 test＋probe 全過。
- 快照：`_backup\r53_20261031_age_lock_bucket\`（兩支改動產品碼＋新 test＋helper＋probe）。

**F. 界定（必須區分）**

- **源碼已修復**：bucket 由年齡條款決定、四欄 contract、env 明確值永遠贏過自動地板、非數字不退小 bucket —— 全部落碼且有測試覆蓋。
- **影片未實機**：本輪 ComfyUI **零請求**；`_4` 之後沒有任何一張在 `megapixel_floor_reason == "apparent_age_lock"` 下渲染過的影片。「老人化已消失」**尚未驗證**，必須跑一槍才算。
- **已知邊界**：路線 2（manual）的 prompt 本來就沒有年齡條款 ⇒ 它不會自動抬 bucket（已用測試釘選，避免以後被當成 bug）；要 768 就 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=1.0`。另一下一個尚未動的量測事實：identity sheet 的臉面板只有 178×152 px（來自用戶 252×370 原圖 LANCZOS 放大），但被採納那一槍用的就是同一張 sheet ⇒ sheet 不是本輪變因。
- **下一槍怎麼跑（GPU 三條硬約束見 §12）**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`。驗收順序：① manifest `prompt_budget.route == route1`、`relay_prepare_resolution == "768"`、`megapixel_floor_reason == "apparent_age_lock"`、`attempts_used == 1`；② 才讀片評「臉的年齡、衣服、頭髮、鏡位」。跑完 driver 自帶 `/free`。
- **仍未表態的用戶項**（不要擅自動）：圓眼鏡殘差；禁止發明的額頭皺紋／維持參考圖年齡的措詞；衣柜相對地板 0.12；silent 嘴部容差。

**G. 本輪工具**：`working\r53_dump_project4.py`、`r53_dump_prompt4.py`、`r53_find_prompt_key.py`、`r53_dump_job_prompt.py`、`r53_src_resolution.py`、`r53_clause_matrix.py`、`r53_compare_aged_vs_accepted.py`（A/B 對照表）、`r53_template_nodes.py`、`r53_probe_expectations.py`（本輪全部斷言的實測依據）。本輪 ComfyUI 端**零請求**。


### Round 52：角色替換模組「推到重來」——三条 prompt 路線（路線 1 出厂、路線 2 Design 開關、legacy 逃生口）、身分 QC 全轉目擊者、prepare bucket 地板退回 0（2026-10-31，**源碼已修復＋1051 項測試通過；影片未實機（0 槍）**）

**A. 範圍與決策**

- 用戶裁定：「我想把這個角色替換 skill 所有的人物優化完全推到重來，但是保留主要的多角色 sam3.1 並接、自動分切 V1 片段、自動選角色、自動多角色檢測、多人物替換」，並在選項裡選 **路線 1**，同時要求「路線 2 改成在 design 開關，default 路線 1」。本節即該決定的落地。
- `VERSION` 維持 `0.3.8-alpha.3`、Project Format 29。`SMART_RENDER_POLICY_VERSION` **保持 84**（`director_cut_studio.py:883`、`smart_render_worker.py:240`）：route 已經寫進每一個 pass 的 `prompt_budget.route` 與 manifest（`director_cut_studio.py:37648-37664`），事後歸因靠那一欄而不是靠政策號；政策號不動可讓 `example\` 裡 2 066 份既有 manifest 繼續互相比對。
- 本輪 ComfyUI **零請求**。用戶另外要求的「先補一次 `/free` 並清掉那張 70 分鐘的 stale claim」經 driver `status`（唯讀）確認**已經是乾淨狀態**：`comfy_claim: none`、`comfy_queue: free`、Qwen 已由 tray 載回，因此不需要補動作。

**B. 那 70 分鐘到底花在哪（為什麼非改不可）**

- 三處證據缺口同時存在，導致一槍 70 分鐘卻無法歸因：① Segment 死掉時 manifest 只存 `str(exc)`，policy-84 那槍留下一行 `[Errno 22] Invalid argument`，沒有 traceback、沒有 frame，分不清是 H3 拒絕、take 寫檔失敗還是 claim 過期；② `source_plate_drifted`（框外 median／MAE 粗閘門）在同一個 Segment 先重搖兩槍、每槍約 20 分鐘，第三槍才死在一個跟畫面無關的寫檔錯誤 ⇒ 70 分鐘裡約 40 分鐘是閘門自己燒掉的；③ 胖 prompt 的 12 320 字元預算把關鍵條款從尾端裁掉，而 manifest 只記裁了哪幾條、不記「如果不裁會多長」。
- 修法一（先能歸因）：`smart_render_worker.py:4276` 開始保留每一次嘗試的 traceback，失敗列（`6245-6254`）新增 `error_traceback`、`attempt_error_tracebacks`、`retry_budget`。stale claim、寫到一半的 take、真的被 H3 拒绝，過去在 manifest 裡長得一模一樣。
- 修法二（不再花錢）：lean 路線出厂 `plate_audit: False`（編譯端 `director_cut_studio.py:37417-37426` → 執行端 `smart_render_worker.py:2465-2472`）。drift **仍然量、仍然寫 manifest**，只是不再單獨判定失敗、重搖整槍。

**C. 三條 prompt 路線**

| route | 名稱 | 怎麼選到 | prompt 形狀 | 身分 QC |
|---|---|---|---|---|
| `route1` | 路線 1「精準拆」（**出厂預設**） | 什麼都不設，或 `H3_CHARACTER_SWAP_ROUTE=route1｜precise｜lean｜1` | 官方作者模板逐字 ＋ 每一句都有「被命名、被評分過的失敗」背書的條款：in-place、erasure、hair、wardrobe、no-invented、no-invented-texture、讀 sheet 一句、crop lock、age lock、silent 三句、多角色保護名單 | advisory |
| `manual` | 路線 2「手動對齊」 | Design 頁 checkbox `sourceRemakeManualAlignPrompt`（預設關，`director_cut_studio.py:11440-11474`），或 `H3_CHARACTER_SWAP_ROUTE=manual` | 用戶那張手動 ComfyUI 圖的形状：作者模板 ＋ in-place／erasure 兩條 guard ＋ 一行讀 sheet ＋ 權威 silent 塊 | advisory |
| `legacy` | 逃生口 | `H3_CHARACTER_SWAP_ROUTE=legacy` | Round 52 以前的胖 prompt，逐 clause 原樣保留，**仍受 12 320 字元預算裁句** | 舊的硬判定 |

- 解析規則（`character_swap_engine.py:316-373`）：空白值與未知值一律回 **route1**，不是回 legacy —— 因為胖 prompt 正是這次要離開的那個 regime；顯式 `route=` 參數（Studio 傳入）永遠贏過環境變數。
- 兩個環境名都進 `DESIGN_ENV_RENDER_KNOBS`（`director_cut_studio.py:469`、`474`）⇒ 寫進 `design_ai.env` 後按 Preview 立即生效並跨重啟保留，真正的啟動環境變數仍優先。
- **官方作者模板一字未動**：測試直接斷言 `prompt[:len(_relay_v2_author_prompt())] == _relay_v2_author_prompt()`，並用 `author_prompt_chars` 對帳（3 377 字元）。改動的只有模板之後的 Studio 附錄。
- 用戶清單的落地對照 —— **保留**：V1 自動分切、Qwen 多角色偵測、自動 binding、手動畫框優先＋大臉自動合格框、Identity Sheet preset 8 `fullfig`（800×1216 單人）、官方作者模板、bucket 邏輯、LoRA ≤1.5、turbo 8-step、relay 124＋18 幀接力、參考圖 RTX ×2、job compile、preflight、upload、SAM3.1 多角色並接與角色合成（僅多角色）、錯誤分類重試、組裝／tail padding、源音軌時間稽核、`/free`＋manifest。**刪除（出厂不再做）**：模糊 plate、silent-audio plate、prompt 字元預算裁句、silent megapixel 地板、`source_plate_drifted` 判定、QC 失敗→fresh-seed 自動重試、best-of 多候選。**轉 advisory**：源相關性／相似度／mae、erasure gap、strict temporal coverage、whole-character audit、silent mouth audit、wardrobe shift、目標參考相似度、reveal probe／crop lock。
- 措辭邊界由黑名單守住：路線 1／路線 2 的 prompt 永不出現 9 條 legacy 專屬措辭（含「blurred plate」「split panel」「costume」等），所以不會出現「附錄已經不寫模糊 plate、条款卻還在講模糊 plate」的自我矛盾。

**D. 實際 prompt 長度（`working\r52_route_probe.py`，可重跑；預算常數 lean 4 200／manual 2 400／char budget 12 320）**

| 場景 | 路線 1 全文／附錄 | 路線 2 全文／附錄 | legacy 全文／附錄（被裁條款） |
|---|---|---|---|
| A 靜音 Identity-Sheet 大臉特寫（含抑制 plate＋保護 R2） | **8 373／4 977**（`append_over=True`、`over=False`、dropped `[]`） | 5 670／2 274 | 13 145／9 749 ⇒ `over=True`，丟 `close_up_sheet_crop_lock`、`close_up_silent_mouth`、`wardrobe_silhouette_reinforcement` |
| B raw V1 medium 說話者 | 6 426／3 049 | 4 865／1 488 | 8 391／5 014 |
| C 雙人 sheet | 6 965／3 588 | 4 984／1 607 | 9 864／6 487 |
| D tiny-box medium（框面積 < 0.060） | 6 208／2 831（無 texture contract） | 4 865／1 488 | 7 468／4 091 |

- 這組數字就是用戶那句「同一張官方模板，手動圖兩三句就比 Studio 好」的量化：失敗那槍送達 11 941 字元，其中 **9 065 字元是 Studio 附錄**；路線 1 把同一場景壓到 8 373（附錄 4 977），路線 2 壓到 5 670（附錄 2 274）。
- **附錄預算只記錄不裁句**：場景 A 的附錄 4 977 已超過 4 200，路線 1 仍全文送達，`dropped_tail_clauses == []`，`append_over_budget=True` 進 manifest；同一形狀在 legacy 下被裁掉三條，其中一條正是 crop lock。三個 shape 上恆有 `manual < route1 < legacy`。
- crop-lock 舉旗矩陣（路線 1）：sheet＋大臉特寫 **有**、raw＋大臉特寫 **無**、sheet＋plate 底邊切人 **有**、sheet＋medium **無**。live-action 適配改寫 medium 那一句，且此時**不出現** `APPARENT AGE LOCK`（7 985 字元）。

**E. 身分 QC 從判決改成目擊者**

- lean 路線的 pass 出厂覆寫四項（`director_cut_studio.py:37417-37426`）：`advisory_only: True`、`plate_audit: False`、`maximum_attempts: 1`、`strict_temporal_coverage: False`。
- 執行端：每次 audit 打上 `advisory_only`（`smart_render_worker.py:4395`、`4406`）；只有當該 Segment 的**全部** verdict 都是 advisory 時才不放閃（`5972-5992`）；manifest 新增 `character_swap_identity_advisory_only`（`6016`）。Studio 端 `_character_swap_identity_failed` 對 advisory verdict 直接 `continue`（`34883-34884`）。
- 後果講明：lean 下**一槍就是終片**，不再用第二、第三槍去換一個閾值；best-of／多候補與 fresh-seed 機制只在 legacy 路徑與「真實錯誤」重試時仍會走到。**真實錯誤**（H3 拒絕、缺 P 圖、無檔案、寫檔失敗）仍照 `segment_attempts`（預設 3）重試，沒有被一并弱化。

**F. prepare bucket 地板退回 0（把 Round 51 的 2.4× 成本退還給導演）**

- `CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT = 0.0`（`character_swap_engine.py:2774-2782`）：0.5 MP Preview 重新走 480 bucket（576×864，一槍約 9-10 分鐘）；要回 Round 51 的 768／800×1216（約 22 分鐘）就設 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=1.0`。地板只抬不降、`0` 精確重現、`>4.0`／負值／解析失敗／**含 `nan`** 一律退回出厂值（NaN 那條守衛保留：它會偽裝成解析成功並讓地板無聲消失）。
- 取捨：`APPARENT AGE LOCK` 服從與 bucket 有關（Round 51 的實測是 768 才服從），所以地板取消把「老人化」的處方暫時換成「便宜且可重試」。`relay_prepare_resolution`／`requested_megapixels`／`effective_megapixels` 三欄仍在 manifest，地板有沒有生效一眼可查。

**G. 沒有藏起來的取捨**

- 路線 1 仍保留一句 CROP-LOCK，因為用戶最近的抱怨正是「v1 的人物是半身，但是創作出來的卻是 p1 的全身」。
- wardrobe signature 仍然計算，只是 verdict 變成 advisory —— 它是目前唯一能量化「衣服不像參考圖」的指標，降級但不丟棄。
- plate／silent-plate 的 builder 留在檔內，Round 49 的三個 parity 開關語意不變：`H3_CHARACTER_SWAP_PLATE_SUPPRESSION`、`H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP`、`H3_CHARACTER_SWAP_RELAY_WINDOW_SPLIT`，出厂全部為 off（=手動圖行為），`=1` 逐條還原。
- 單角色路徑的 plate 仍是切好的乾淨 V1（`plate_video_path = relay_source_clip`，`director_cut_studio.py:37709`），沒有模糊、沒有抽音軌。

**H. 測試／編譯／快照**

- 新建 `testing\test_round52_swap_routes.py` **47 項全綠**（`RouteResolutionTests` 6、`Route1ClauseSetTests` 9、`Route1GateTests` 10、`Route2ManualTests` 6、`ShippedMegapixelFloorTests` 5、`RouteKnobWiringTests` 5、`AdvisoryIdentityVerdictTests` 6）。
- 回歸：`test_character_swap_closeup_gates`（77）＋本輪新模組（47）= **Ran 124／OK**；用 `testing\legacy_swap_route.py` 的三個釘選 helper 釘回舊行為後，**211 項 legacy 釘選測試全過**，證明 clause 級措辭與舊 QC 判定在 legacy 下一字未變。
- 全套守門：`.\ai_libraries_common\python_env\python.exe working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **RAN 1051 項、failures=0、errors=0、skipped=10、exit 0（267 s）**（基線 1 004 ＋ 本輪 47）。
- `py_compile`：`character_swap_engine.py`／`smart_render_worker.py`／`director_cut_studio.py`／`character_identity_sheet.py`／新 test／helper／probe 全過。
- 快照：`_backup\r52_20261031_route1_policy84\`（四支產品碼＋新 test＋helper＋probe）。

**I. 界定**

- **源碼已修復**：三條 route、advisory QC、地板取消、traceback 落 manifest 都已落碼且有測試覆蓋。
- **影片未實機**：掃過 `example\` 全部 **2 066 份 manifest**，其中 80 份帶 `prompt_budget`、**0 份帶 `route` 欄** ⇒ 路線 1 與路線 2 至今 **0 槍**。用戶之前認可的「效果很好」來自 policy 82／83／84 的 legacy 形狀，不能算在路線 1 頭上。
- **回退**：`H3_CHARACTER_SWAP_ROUTE=legacy` 一條就把 prompt＋硬判定 QC 全數還原；`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=1.0` 單獨找回 1.0 MP 地板。
- **下一槍怎麼跑**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`（driver 內建 unload-qwen → wait-comfy → worker → `/free`，Segment 之間不插 `/free`，見 HANDOFF §12 三條硬約束）。**地板取消後 0.5 MP 一槍回到約 9-10 分鐘。** 驗收順序：先讀 manifest 的 `prompt_budget.route`／`append_chars`／`author_prompt_chars` 確認走的是路線 1，再讀 `character_swap_identity_advisory_only` 與 `attempts_used` 確認只花了一槍，最後讀片評分「臉、衣服、头发、鏡位、嘴」。

**J. 本節工具**：`working\r52_route_probe.py`（三路線 prompt 長度與條款矩陣）、`working\r52_lean_sizes.py`、`working\r52_measure.py`、`working\r52_clear_claim.py`（stale claim 清理與 `/free` 核對）、`working\r52_dump*.py`、`working\r52_probe_failedjob*.py`（70 分鐘那槍的事後剖析）。

### Round 51：policy 83→84 —— crop lock 的觸發條件改讀 plate 而非 box（根治「V1 半身、生出 P1 全身」）、prepare bucket 地板墊到 1.0 MP（根治人物老人化）（2026-10-30，**源碼已修復＋1004 項測試通過；影片未實機**）

**A. 範圍**：用戶回報最新一支 black-shirt 影片「效果很好，唯一的問題就是：人物變成老人化，還有 v1 的人物是半身，但是創作出來的卻是 p1 的全身，有點怪」。`VERSION` 維持 `0.3.8-alpha.3`、Project Format 29；`SMART_RENDER_POLICY_VERSION` **83 → 84**（`director_cut_studio.py:875`、`smart_render_worker.py:239`，兩處同步）。本輪 ComfyUI 端**零請求**，全部證據取自既有 manifest。

**B. 根因一 —— crop lock 只看臉的大小，不看 plate 本身（「半身 → 全身」）**

- 失敗那槍的證據鏈（manifest `preview_1116937216319510353_1793357785675188600`，`render_policy_version 83`、`megapixels 0.5`、take **576×864**、`attempts_used 3`、`failure_class silent_mouth_excessive_articulation`、`performance_mode silent_listener`）：Identity Sheet 照常出厂（`identity_sheet_preset 8`、`identity_sheet_single_figure_fullfig True`、`identity_sheet_outfit_view full`），**sheet 頭部覆蓋 0.5259**，而 **plate 頭部覆蓋只有 0.214413**。
- plate 的頭只佔畫面 21 % ⇒ `face_dominant_closeup` 不成立 ⇒ 唯一用來阻止 Relay 拉寬鏡位的 `CLOSE-UP SHEET CROP LOCK` 從頭到尾沒上桌。但 neck-down 全身衣柜視圖是 Relay 收到的最強「這整個人該在框裡」的訊號，於是它把鏡頭拉到鞋子出現為止 —— 正是用戶講的「v1 半身、做出來是 p1 全身」。該 Shot 的手動合格矩形又被 UI 刻意縮到 0.30×0.30（大臉自動框功能），所以**靠 box 尺寸永遠猜不到「plate 自己在底邊就把人切掉了」**。
- 修法：新增 `character_identity_sheet.measure_source_figure_reveal()` —— 用 ffmpeg 把 plate 整段解成 96 寬灰階、均勻抽 6 幀，在角色框的中間帶量「移動主體的最低列」，回答 `reaches_frame_bottom`（人被畫框切到 = True；框內看得到人的盡頭、底下還有背景 = False）。`director_cut_studio.py:7709 source_figure_probe_box()` 決定探測框：優先用被選中角色自己的框，退回最大角色框，**只取橫向坐标**，因此合格矩形怎麼縮都不影響讀值。engine 端（`character_swap_engine.py:1934-1940`）改成 `face_dominant_closeup` **或** `source_figure_reaches_frame_bottom` 任一成立即送上 crop lock。
- 成本與失敗模式：一次灰階解碼 + 6 幀，比既有 SAM 遮罩統計同量級。無 ffmpeg、無主體證據、框太窄、`global_motion`（整幅都在動、沒有可讀背景）一律回 `None`，呼叫端一律當 False ⇒ **每個失敗模式都等於 policy 83 的舊行為**。
- 真 plate 六組控制實測（`working\_r51f_probe.py`，檔 `.director_cache\source_remake_relay_video\v1_relay_7055bf5e541b4614b9cb_0.000-12.860.mp4`，426×642@24，就是上面那槍 manifest 裡的 plate）：

| 控制組 | 探針讀值 | 結果 |
|---|---|---|
| 真 plate 框 `[0.35,0.15,0.65,0.45]` | deepest **1.000**、median **0.9444**、證據 2 幀 | 舉旗 ✓ |
| 框縮小、下方仍是黑邊 | deepest 0.983696、證據 0 幀 | 不舉旗 ✓（實測要 ≥2 列餘裕才判 False，不是貼邊就翻） |
| 框縮小、上方加墊 | deepest 1.000、證據 2 幀 | 舉旗 ✓ |
| 整幅畫都在動 | qualifying share 0.538（未觸發 0.90 全域動態守衛） | 舉旗（已知良性，措辭本身不依賴框位置） |
| 窄框 `[0.48,…,0.52,…]` | 中央帶自動放寬到 8 px、證據 3 幀 | 舉旗 ✓ |
| 框落在主體外 `[0.02,0.62,0.20,0.95]` | deepest 0.965、證據 0 幀 | 不舉旗 ✓ |

**C. 根因二 —— prepare bucket 480 讓 `APPARENT AGE LOCK` 失效（老人化）**

- prepare 節點的 `resolution` 是 **bucket 不是尺寸**：只發布 480／768，H3 按 bucket 自己的長寬比出片 ⇒ **480→576×864、768→800×1216（像素 2.4 倍）**。最新影片每個 0.5 MP 窗口的回報都是「卡通媒介正確、頭跟參考圖不像、人變老」；而導演明確接受的那一槍（manifest `preview_923011207`，policy 82、**1.0 MP**、take **800×1216**、307 幀）prompt 形狀相同，**第一次嘗試就過、`failure_class ''`**。⇒ `APPARENT AGE LOCK — MANDATORY`（Round 50 ③ 加的條款）只在 768 服從；選了小 bucket 等於默默把那 458 字買掉，這也解釋了為何「條款送達了卻沒有效果」。**年齡漂移先是解析度問題，然後才是 prompt 問題。**
- 修法：`character_swap_engine.py:2449 character_swap_megapixels_floor()` 出厂地板 **1.0 MP**，`character_swap_effective_megapixels()` 只抬不降（0.5 MP Preview 从此走 768）。`H3_CHARACTER_SWAP_MIN_MEGAPIXELS` 覆寫：**`0` 精確重現 83**；`>4.0`、負數、解析失敗、**含 `nan`** 一律退回 1.0。NaN 這條是本轮補的洞：`float("nan")` 解析成功、活得過上下界兩道檢查，會使 `max(requested, floor)` 傳回 requested 且 `nan >= 0.75` 為 false ⇒ 操作者要的地板會無聲消失、Shot 掉回會變老的 bucket。已進 `director_cut_studio.py:466 DESIGN_ENV_RENDER_KNOBS` ⇒ 寫進 `design_ai.env` 按 Preview 即生效並跨重啟保留，真正的啟動環境變數仍優先。
- 代價講清楚不藏：800×1216 是 576×864 的 **2.4 倍像素**，Preview 每槍 GPU 時間大約按同倍增加。

**D. prompt 預算 —— 本輪新增的 crop lock 要在 12 320 字元額度內自己付帳**

| prompt 形狀 | 未預算 | 送達 | 餘裕 | 被丟條款 |
|---|---|---|---|---|
| 靜音 Identity-Sheet 大臉特寫（框 `[0.05,0.02,0.98,0.99]`） | 13 137 | 12 305 | **15** | `close_up_silent_mouth`、`wardrobe_silhouette_reinforcement` |
| 說話者大臉特寫（同框） | 10 944 | 10 944 | 1 376 | — |
| medium 框 `[0.42,0.26,0.85,0.82]`、探針不舉旗（＝83 的形狀） | — | 11 152 | 1 168 | — |
| medium 框＋探針舉旗（＝真正失敗的那種 Shot） | — | **11 961** | **359** | —（crop lock 已上桌，`MEDIUM-SHOT SILENT MOUTH REINFORCEMENT` 保留） |

- 交叉驗證：上表最後一列與上面那槍實際送達的 `prompt_chars 11 977 / 12 320、dropped []` 只差 16 字元，說明量測場景選得對。
- **關鍵界定：真正需要被救的那種 Shot 一分錢沒付**（359 字元餘裕，衣柜與 silent 條款全留）。只有「大臉特寫」形狀卡在 15 字元，而那種 Shot 在 83 就已經帶著 crop lock，本輪在它身上只多了約 40 字措辭。長度 pin 由 `12 300` 提到 **`12 320`**，並註明 36 字元的安全窗已不復返（只剩 15）；真正會擋住未來 rank-4/5 丟失的是 `test_shipped_budget_keeps_the_crop_lock_on_a_silent_sheet_closeup`，不是這條 pin。

**E. manifest 新鍵（沒有這些就無法事後歸因）**

- 探針四鍵：`source_figure_reaches_frame_bottom`／`source_figure_bottom_normalized`／`source_figure_reveal_status`／`source_figure_reveal_sample_count`（allowlist `director_cut_studio.py:1850-1858`；第一個鍵不加前綴，因為 engine 的閘門就是讀這個名字）。
- prepare 四鍵：`relay_prepare_node_id`／`relay_prepare_resolution`／`requested_megapixels`／`effective_megapixels`（contract `character_swap_engine.py:2695-2703` → manifest `director_cut_studio.py:37560-37571`）。Job 上的 `megapixels` 仍是導演的請求，所以少了這四行，「0.5 MP 卻默默渲染成 800×1216」與「真的在 576×864 變老」事後完全無法區分 —— 而那正是「人物變老」必須回答的問題。

**F. 測試／編譯**

- `testing\test_character_swap_engine.py` **96 項全綠**（85→96：新增 5 項探針觸發 crop lock、1 項「大臉即使無探針仍送 crop lock」、6 項 `CharacterSwapPrepareResolutionTests`：0.5 MP→"768" 與 contract 欄位、地板不得降低 1.0/2.0/4.0、env `0`→"480"、畸形值 `""/banana/99/-1/nan`→1.0、bucket 對照 0.5/0.74→480 與 0.75/1.0/2.0→768、NaN 端到端 canary）
- `testing\test_identity_sheet.py` **67 項全綠**（55→67，新增 `SourceFigureRevealProbeTests`；另修該檔自己的 `_frames()` helper 誤寫 `range(6)`，多幀情境根本沒被覆蓋）
- `testing\test_round50_qc_relaxations.py` **21 項全綠**（長度 pin 12 300→12 320）
- timeline 定點：`-m unittest testing.test_director_timeline -k character_swap` **6 項 OK（21.3 s）**
- 全套：`.\ai_libraries_common\python_env\python.exe working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **RAN 1004 項、failures=0、errors=0、skipped=10、exit 0（277 s）**
- `py_compile`：`director_cut_studio.py`／`character_swap_engine.py`／`smart_render_worker.py`／`character_identity_sheet.py`／`identity_sheet_page.py`／`source_video_analysis.py`／`staged_model_driver.py` 全過

**G. 界定**

- **源碼已修復**：讀 plate 決定 crop lock、prepare bucket 地板，兩者都落碼且有測試覆蓋。
- **影片未實機**：policy 84 **零槍**。① crop lock 只在「plate 於底邊切人」的 Shot 看得出差異（black-shirt 案正是；a_cartoon…shirt_9 那種全身 Shot 不會變）；② 老人化要看同一槍裡 `APPARENT AGE LOCK` 是否開始服從。**A、B 必須在同一槍評分**：靜音大臉形狀只剩 15 字元餘裕，拆兩槍看不出取捨。
- **回退**：`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 立刻回到 480 bucket；探針不舉旗（含全部失敗模式）即回到 83 的 crop lock 條件，不需要另設開關。
- **下一槍怎麼跑**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`（driver 內建 unload-qwen → wait-comfy → worker → `/free`，Segment 之間不插 `/free`，見 §12 三條硬約束）。**0.5 MP Preview 現在會出 800×1216，成本約 2.4 倍。** 驗收讀 manifest 的 `relay_prepare_resolution`／`requested_megapixels`／`effective_megapixels`／`source_figure_reaches_frame_bottom` 四項，再讀片看「腳有沒有跑出來」與「臉有沒有變老」。

**H. 本節工具**：`working\_r51f_probe.py`（六組控制組探針讀值）、`working\_r51h_headroom.py`／`working\_r51i_medium.py`（預算表兩端）、`working\_r51_delivered_prompt.txt`、`working\r51\*.png`。

### Round 50：policy 82→83 —— silent 硬閘加容差改 advisory、衣柜 floor 加「相對增益」、把 GARMENT SILHOUETTE 拆成自己付帳的可丟棄條款、參考圖上採倍率改由 env 決定（2026-10-30，**源碼已修復＋981 項測試通過；影片未實機**）

**A. 範圍**：用戶在 Round 49c §I「等用戶表態」四案中批准 1–4。`VERSION` 維持 `0.3.8-alpha.3`、Project Format 29；`SMART_RENDER_POLICY_VERSION` **82 → 83**（`director_cut_studio.py:856` 與 `smart_render_worker.py:222` 兩處同步）。bump 的理由是本輪改變了**兩個 QC 判定語意**與 **prompt 尾部結構** ⇒ 舊 Job／舊 prompt 快取必須作廢。四項全部離線完成，本輪**未向 ComfyUI 提交任何工作**（ComfyUI 端零流量、未碰 GPU）。

**B. 四項改動與 env 開關（出厂值＝鬆綁後行為；每項都能一鍵回到 82）**

| 項 | 位置 | 內容 | env（出厂） |
|---|---|---|---|
| ① silent 硬閘容差 | `smart_render_worker.py:1555`、`:2566`、`:2741-2805` | 新增 `_silent_mouth_hard_gate_tolerance()`；先按 `decision_basis` 選出 `governing_motion_limit`（plate 限／嘴腔 swing 限／pixel-motion 限），再把**絕對**超出換算成可跨 Shot 比較的 `overrun_ratio = articulation_excess / governing_limit`；`overrun_ratio ≤ 容差` **且** `not (geometry_available and geometry_violated)` ⇒ `advisory_overrun=true`、`violated=false`（不燒 fresh seed）。**只降不升**；獨立的嘴腔幾何通道仍算硬判證據 | `H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE`（**0.12**；`0`＝精確回到 82 的硬判） |
| ①b 參照系措辭 | `:1588 _silent_plate_verdict_scope()` | policy 74 起每一列都寫 `relative_to_suppressed_plate`，但 82 出厂的 plate 是**乾淨 V1** ⇒ 改按實際開檔的 plate 檔名回報 `relative_to_clean_source_plate`／`relative_to_suppressed_plate` | 無（純措辭，不改數值） |
| ② 衣柜 floor 相對化 | `:1964 _wardrobe_floor_policy_settings()`、`:2004 _wardrobe_region_passed()`；呼叫點 `:2988`（逐區）與 `:3129`（Shot 層） | 通過條件改為 **OR**：絕對 floor（原樣不動）**或**「相對源區域的增益」——`shift ≥ max(sanity_floor, source_median × 0.10)` 且 `take_median ≥ source_median × 1.10`。`policy=absolute` 精確重現 82；`floor=0` 仍是「這個 Shot 不管衣柜」。逐區與 Shot 層共用同一實作 ⇒ manifest 不可能宣稱某區用了一條聚合層沒套用的規則 | `H3_CHARACTER_SWAP_WARDROBE_FLOOR_POLICY`（**relative**）／`_RELATIVE_GAIN`（**0.10**）／`_SANITY_FLOOR`（**0.03**）；manifest 新增 `floor_policy`／`relative_gain`／`sanity_floor`／`required_relative_shift`／`absolute_floor_passed`／`relative_floor_passed`／`aggregate_rule_passed` |
| ③ prompt 條款 | `character_swap_engine.py:1891`、`:2196-2237`、`:2220`、`:213` | `APPARENT AGE LOCK — MANDATORY`（鎖參考圖年齡）與 `NO INVENTED CHARACTER DETAILS — MANDATORY`（禁 invented：面部毛／眼鏡／飾品／徽章／滾邊／金屬邊／繡花；也禁刪 P1 已有细节：鬍子、**圓眼鏡**、帽、領口點）在 49c 已用 `/history` 逐字證實送達。本輪把 `COMPLETE WARDROBE REPLACEMENT` 尾巴那句「剪裁／長度／貼身／下擺」**剪出來**做成獨立條款 `GARMENT SILHOUETTE — MANDATORY`，掛 **rank 1**（自己付帳）；其餘 wording 保持 49 原樣，因為其中沒有可協商的部分 | 無新 env |
| ④ 參考上採倍率 | `character_swap_engine.py:75-77`、`:2370`、`:2541-2566` | `RTXVideoSuperResolution` 的倍率（模板 `scale=2`、`quality=ULTRA`）可由 env 覆寫，接受 **2／3／4**；節點缺席或不認識的值 ⇒ 保留模板值，且在 contract 現形（`reference_upscale_scale_source` 寫 `template` 或 `environment`）；模板只有 mode 沒有 multiplier 時也會補上 `resize_type.scale` | `H3_CHARACTER_SWAP_REF_UPSCALE_SCALE`（出厂**不覆寫**＝沿用模板 2） |

五個開關已全部加進 `director_cut_studio.py:434 DESIGN_ENV_RENDER_KNOBS` ⇒ 可寫在 `design_ai.env`，按 Preview 即生效並跨 Studio 重啟保留；真正的啟動環境變數仍然優先。

**C. ①的容差為什麼是 12 %，以及它**故意**不救哪些槍**

`articulation_excess` 是絕對量，跨 Shot 不可比；換算成相對比例後，本專案三組既有實測落在同一軸上：

| 素材 | 判定通道 | excess／limit | overrun_ratio | 讀幀真相 | 12 % 容差後 |
|---|---|---|---|---|---|
| seed 923011107（0.5 MP／policy 82） | `pixel_motion` | 0.034924／0.225607 | **15.5 %** | 讀幀＝閉嘴笑 | **仍硬判**（>12 %） |
| seed 923011207（1.0 MP） | `plate_relative`（advisory，非決定項） | 0.053616／0.225607 | **23.8 %** | 讀幀＝閉嘴、決定項 `motion_violated=false` | 本槍原本已 pass，與容差無關 |
| 用戶否決的 S3／S5 真對嘴 | `pixel_motion` | 15 %／53 % | **15 %／53 %** | 真的對嘴 | 仍硬判（正確） |

⇒ 12 % 刻意压在「已觀察到的最窄超標 15 %」**之下**：pixel-motion 通道本身**分不出**「閉嘴但整張頭在動」與「真對嘴」——兩者落在同一個數字上——所以出厂不 retroactively 放過 923011107，只擋 micro-overrun。能分開兩者的是獨立通道（嘴腔幾何：`H3_CHARACTER_SWAP_MOUTH_GEOMETRY=on` 時它的違規永遠壓過容差）。要讓 923011107 那一類過關：`H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE=0.16`，不必改碼。

**D. ③的結構性發現：把 185 chars 加進「不可丟棄」條款，會被迫犧牲 rank 3 的已驗證閘門**

`.codex_tmp\r50_probe_drop_order.py`（零 GPU，把 prompt 從無限預算往下掃，印出守衛**真實**的丟棄順序與每筆贖回量；注意 `dropped_tail_clauses` 報的是**发射順序**而非丟棄順序）測得：

| 條款 | 新 rank | 賬回 chars | 它守住的失敗 |
|---|---|---|---|
| `wardrobe_silhouette_reinforcement`（本輪新增） | **1** | 185 | 尚未驗證的加固（剪裁／長度／下擺） |
| `close_up_silent_mouth` | 2 | 647 | close-up 對嘴 |
| `medium_shot_silent_mouth` | 3 | 660 | medium 對嘴 |
| `source_costume_leaves_plate` | 4 | 527 | **S4「源演員長袍回到 P1 身上」** |
| `close_up_sheet_crop_lock` | 5 | 768 | **S7／S9 防鏡頭位移、防 sheet 的手／袖／下擺竄入** |

Silent identity-sheet close-up 未預算 **13,096 chars**、預算 12,320 ⇒ 必須贖 **776**。rank 1（185）＋rank 2（647）＝**832**，**兩筆就夠** ⇒ rank 4 與 rank 5 **都留在頁面上**。
反之若那句話仍留在不可丟棄的 `COMPLETE WARDROBE REPLACEMENT` 內（同規格同樣 13,096，但可丟池只剩 647／527／768）：第一筆 647 蓋不掉 776 ⇒ 守衛必須再丟 `source_costume_leaves_plate`。⇒ **拿已驗證的閘門去換一句未驗證的加固是錯誤方向**，新條款必須自己付帳。

**E. 測試與編譯**
- `testing\test_character_swap_engine.py`：**85 項全綠**
- 全套：`.\ai_libraries_common\python_env\python.exe working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **981 項 OK（skipped=10）、exit 0**，log `testing\_r50_batchB.log`
- timeline 定點跑：`testing\test_director_timeline.py DirectorTimelineDragTests.test_character_swap_*` **6 項 OK（25.2 s）**
- allowlist 追加後複核：`testing\test_character_swap_closeup_gates.py` **77 項 OK**（`apply_design_ai_env_render_knobs` 的選取／優先級行為不變，launcher 變數仍贏）
- `py_compile`：`director_cut_studio.py`／`character_swap_engine.py`／`smart_render_worker.py`／`source_video_analysis.py`／`character_identity_sheet.py`／`identity_sheet_page.py`／`staged_model_driver.py` 全過
- 四項 stale 測試改成**測出來的**新順序（不是拍常數）：`test_silent_merged_clause_never_yields_and_the_mouth_reminder_does`、`test_prompt_budget_guard_drops_restatements_in_declared_order`、`test_medium_and_plate_texture_clauses_are_never_droppable`、`test_sheet_crop_lock_is_the_last_clause_the_guard_sacrifices`

**F. 界定**
- **源碼已修復**：①②③④ 全部落碼且有測試覆蓋（981 OK／engine 85／closeup gates 77／timeline 6）。
- **影片未實機（policy 83 至今零槍）**。各項要看到差異所需的條件：① 需要一支 `overrun_ratio` 落在 12–16 % 的 take；② 需要一支暗色服装、絕對 shift 低於 0.12 但相對增益 ≥10 % 的 Shot（923011207 的 0.130169 本來就過線，本輪買的是**餘裕**）；③ invented 滾邊／額紋是否消失要肉眼判——49c 已證實「送達但不服從」，本輪只是不再讓長度守衛吃掉加固句；④ 3× 上採是 GPU 成本取捨，未測。
- **回退**：五個 env 出厂＝83 行為；`H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE=0` ＋ `H3_CHARACTER_SWAP_WARDROBE_FLOOR_POLICY=absolute` 精確重現 82 的 QC 判定；prompt 側無 env（要改得動 rank 表）；上採回到模板＝不設 `H3_CHARACTER_SWAP_REF_UPSCALE_SCALE`。Round 49 的三個 off 開關（plate suppression／audio strip／window split）不受本輪影響。
- **本輪工具（零 GPU、可重用）**：`.codex_tmp\r50_probe_drop_order.py`（真實丟棄順序＋每筆賬回字符數，換 spec 即可重測）。

### Round 49：policy 81→82 —— 把 Studio 對齊到用戶認可的「手動 ComfyUI 圖」（2026-10-30，**源碼已修復＋352 項測試通過；影片實機證據見下方 Round 49b**）

**A. 用戶問題與證據（讀 ComfyUI `/history`，零 GPU）**

用戶回報：同一張 P1，手動 ComfyUI 圖的效果遠勝 Studio。`working\_r48_manual_vs_studio_probe.py` 把 Job `preview_923011007_1793291943180178000` 與手動圖逐節點比對，得到四項行爲差異：

| 軸 | Studio（policy 81） | 手動圖（用戶認可） |
|---|---|---|
| plate | `..._identity_suppressed_..._silent_....mp4`（糊臉＋糊嘴帶凍結＋抽掉音軌） | **乾淨 V1**＋原音 |
| 一段 Shot | 切成 **3 × 4.288 s** 冷啟動（每窗從第 1 幀重來） | **提交一次**，靠原生 Relay 18 幀 history 串窗 |
| swap LoRA | 1.5 → **1.75 → 2.0**（重試階梯越過官方上限） | **1.5**（官方 1.0–1.5） |
| Picture 1 | 依賴 re-export 殘留值 | `RTXVideoSuperResolution` **×2**＋`ref_image_size="match"` |

模板事實（`H3-Character-Swap-Relay-V2-api.json`）：node `9` = `RTXVideoSuperResolution`（`resize_type.scale=2`、`quality=ULTRA`）→ node 7 `ref_images.ref_image_0`；`ref_image_size="match"`；swap LoRA `h3_character_swap_v1.5.safetensors` `strength_model=1.5`；Turbo LoRA `0.8`（不同 adapter，本輪不動）。

**B. 改動（policy 81 → 82；三項行爲改為 env 開關，出厂 = 手動行爲）**

| 檔案 | 內容 |
|---|---|
| `director_cut_studio.py` | 新增 `_character_swap_parity_flag()` 與三個**出厂 off** 的開關 `CHARACTER_SWAP_PLATE_SUPPRESSION`／`CHARACTER_SWAP_SILENT_AUDIO_STRIP`／`CHARACTER_SWAP_RELAY_WINDOW_SPLIT`（已加入 `DESIGN_ENV_RENDER_KNOBS` allowlist）；swap pass 呼叫點 `enabled=bool(target_is_illustrated) and CHARACTER_SWAP_PLATE_SUPPRESSION`（off ⇒ `_character_swap_identity_suppressed_source()` 在 36038 行直接 `return source.resolve(), "original"`，糊臉／feather mask／silent 嘴帶 `tmix` 凍結全部不跑）；`_character_swap_silent_audio_source()` 開頭 `if not CHARACTER_SWAP_SILENT_AUDIO_STRIP: return source.resolve(), "original"`（不调用 ffmpeg）；`_planned_render_segments()` 的 `relay_parts` 在開關 off 時恆為 1 ⇒ 12.864 s 的 Shot 只剩**一個 segment**，交給原生 Relay loop；`SMART_RENDER_POLICY_VERSION = 82` |
| `character_swap_engine.py` | `CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH = 1.5`、`_character_swap_lora_strength_ceiling()`（env `H3_CHARACTER_SWAP_LORA_MAX_STRENGTH` **只能調低**，>1.5／≤0／垃圾值一律回落 1.5）、`clamp_character_swap_lora_strength()`（NaN／非數字 → ceiling）；`compile_character_swap_pass()` 對所有 `lora_name` 含 `character_swap` 的 `LoraLoaderModelOnly`／`LoraLoader` clamp `strength_model`，並把含 `ref_image_size` 的 inputs 寫成 env 或 `"match"`，contract **新增** `swap_lora_max_strength`／`swap_lora_ceiling`／`reference_upscale_node_id`／`reference_upscale_scale`／`reference_image_size`（上採缺席時會在 manifest 現形，不再等於「Studio 沒上採」） |
| `smart_render_worker.py` | `_workflow_for_attempt()` 階梯改成 `clamp_character_swap_lora_strength(base + 0.25*(attempt-1))` ⇒出厂 1.5 時重試**只換 seed**（等同手動重跑）；新增 `effective_generation_timeout_seconds(job)` = `generation_timeout × 該 Job 內最大 relay_window_count`（上限 86400），兩處 `wait_for_history` 改用 ⇒ 串窗三窗的 render 不會在 1800 s 被殺；`SMART_RENDER_POLICY_VERSION = 82` |

逃生門：`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1`／`H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1`／`H3_CHARACTER_SWAP_RELAY_WINDOW_SPLIT=1` 任一一鍵回到 policy 81 的對應行爲；只有肯定值（非空／非 `0/false/no/off`）才算開啟。

**B2. 同輪第二個缺陷（切段開關的必要配套）：work area 端點被 0.5 s 格線改寫**

把三段切成一段之後才發現：`_planned_render_segments()` 只登記**嚴格落在 work area 內部**的 cue 邊界（`start + 1e-6 < boundary < end - 1e-6`，`director_cut_studio.py:22188`／`22195`）。焦點專案是「單一 authored Shot 蓋滿時間軸」⇒ 邊界集合只剩 `{start, end}` ⇒ `mandatory_story_boundary_active=False`（`:22238`）⇒ 直接落入末尾通用 `plan_render_segments(..., grid_seconds=TIMELINE_SNAP_SECONDS)` ⇒ `snap_seconds` 把 **5.200 s 截成 5.000 s**（丟尾巴），把 **12.864 s 進成 13.000 s** —— 越過 `:22136` 剛 clamp 過的 V1 EOF 12.863792 s，產生幽靈尾巴與 FFmpeg seek-at-EOF。

修法（最小改動）：新增 `native_relay_exact_endpoints`（該專案走 character-swap Relay **且** `CHARACTER_SWAP_RELAY_WINDOW_SPLIT` 為 off）與 `native_relay_grid_seconds = 0.001`，套用在三處 fallback（`:22285`、`:22332`、`:22349`）。policy 維持 **82**（同一輪未發槍，不需再 bump）。

**C. 驅動器邊界查核（讀源碼，非猜測）**

`staged_model_driver.py` 的 `--wait-timeout`（默认 1500 s）只約束 `wait_comfy()` 的交棒等待；worker 子進程是 `proc.wait()` **無上限**（`staged_model_driver.py:964-983`）⇒ 串窗長 render 不需额外傳參。

**D. 驗證**
- `py_compile`：`director_cut_studio.py`／`character_swap_engine.py`／`smart_render_worker.py` 全過。
- 10 模組基線 **352 tests OK（skipped=2）**（344 → 352，本輪新增 8 項）。測試更新的是**旧已驗證行爲的期望值**，不是亂改：`test_character_swap_silent_audio` 4 項改為明確 patch 開關 on 才 strip，另**新增**出厂一致性守門（常量为 off ⇒ silent pass 拿到原 plate、完全不调 ffmpeg）；`test_director_timeline` 原「平衡切成兩半」拆成兩項（默认一段／patch 開關 on 仍是 `(0,2.6),(2.6,5.2)`）；`test_smart_render_worker` 重試強度 2.0 → 1.5，並新增「1..7 次嘗試永遠落在 1.0–1.5」與「timeout 隨窗數放大（3 窗 ⇒ 5400、上限 86400）」；`test_character_swap_engine` 新增 5 項（inflated 2.0 被 clamp 回 1.5、出廠模板本就 1.5 故 clamp 為 no-op、env 只能調低 ceiling、clamp 對 NaN/垃圾降級、`ref_image_size=="match"` 且 `ref_images.ref_image_0` 仍掛在 `RTXVideoSuperResolution`（scale 2.0）之上）。
- `test_director_timeline` 的 character-swap 分段／端點 **5 項點跑 OK（18.942 s）**：`test_character_swap_keeps_a_long_shot_in_one_native_window`、`test_character_swap_single_shot_work_area_keeps_exact_endpoints`（本輪新增，輸入 12.864042 ⇒ 斷言 `[(0.0, 12.86)]`）、`test_character_swap_balances_a_shot_that_exceeds_one_relay_window`、`test_character_swap_relay_keeps_every_source_shot_as_one_render_unit`、`test_character_swap_relay_drops_rounded_subframe_tail_past_v1_eof`。整類別 240 項每項 spawn `design_ai_service.py`，依慣例不作回歸判据。修正前該新增測試重現 `AssertionError: [(0.0, 5.0)] != [(0.0, 5.2)]`。
- 離線探針 `.codex_tmp\r49_probe_segments.py`（零 GPU，讀焦點專案）：`policy_version 82`、`scan_duration 12.863792`、`clip 0.0–12.86`、`shot S1 0.0–12.863792` ⇒ **factory 只剩 1 段 `0.000000–12.860000`**、`continuity=none`、`shots=['S1']`、`planned_total=12.860000` vs `source_limit=12.863792` ⇒ **overrun 0.000000**；把 `RELAY_WINDOW_SPLIT=1` 才回到 4.287／4.286／4.287 三段。另 `character_swap_relay_window_count(12.86)=3`、`(4.288)=1`，`effective_generation_timeout_seconds = 1800 × 3 = 5400 s`；編譯器仍寫 `prepare.duration_seconds=0`＋`schedule="adaptive"`＋`window_frames=124`／`history_frames=18` ⇒ 原生 loop 自行串 3 窗。
- 本輪**未碰 GPU**。

**E. 界定**
- **源碼已修復**：出厂不再糊 plate、不再抽音、不再切段；swap LoRA 永遠 ≤1.5；RTX ×2 上採與 `ref_image_size` 寫入 contract；native Relay 模式下 work area 端點保持毫秒級（不再被 0.5 s 格線截斷或進位越過 V1 EOF）。
- **影片已實機驗證**：**無**。五項行為全部要靠 ComfyUI 一槍取證（plate 檔名、`/history` 的 `strength_model`、segment 數、原音是否保留）。
- **本轮已知取捨**：clean plate 意味著 silent Shot 的嘴帶不再 `tmix` 凍結，且 plate 自帶會動的嘴＋原音 ⇒ 「silent listener 仍對嘴」這個老症狀有回升可能（Round 37i 的機制仍在，Round 37k 的凍結則隨 plate 開關一起 off）。若實機證實回升，只需 `H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1` 或 `H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1` 單獨回退，不需回退整輪。
- **仍未解**（未在用戶本次五項清單內，不動）：① preview 仍是 0.5 MP（bucket `megapixels>=0.75 ⇒ "768"`），用戶曾實測 1.0 MP 大增益 ⇒ 等表態 ② Round 47 三提案（衣柜門檻改相對、圓眼鏡／禁 invented 額頭皺紋、silent 微超標降 advisory）③ prompt 仍可能超預算（seed 923011007 記過 `dropped_tail_clauses=["medium_shot_silent_mouth"]`）。
- **編號說明**：`working\` 內的 `_r44_*`／`_r45_*`／`_r47_*`／`_r48_*` 是 43 之後的**離線探針輪**（從未單獨登記），本輪在源碼註解裡沿用「Round 49」一詞，對應 CHANGELOG 本條與 HANDOFF 本節。


### Round 49b：policy 82 出廠行爲的**實機一槍**（2026-10-30 08:0x–08:29，seed 923011107，0.5 MP，**影片已實機驗證＝五項全部生效＋衣柜／頭部換全身已修，唯一 red 項換成 silent 嘴**）

**A. 這一槍打了什麼**

`staged_model_driver.py run`（未經 bypass）：`unload-qwen` ⇒ `verified_clean`（VRAM **26.5 GB → 2.57 GB**）⇒ `wait-comfy ready（1600 node classes）` ⇒ `smart_render_worker` ⇒ `/free`（manifest `final_model_release = "ComfyUI models and VRAM released"`）⇒ tray 載回 Qwen。全程 ComfyUI 與 Qwen 未同時常駐。Job `preview_923011107_1793318258827680500`，總時程約 31 分鐘，`attempts_used = 3`。

**B. 用戶那五項要求的實機證據（讀 manifest／`/history`／ffprobe／讀幀）**

| 要求 | 實機證據 | 判定 |
|---|---|---|
| LoRA ≤1.5 | `/history` 本輪三發 attempt 的 `h3_character_swap_v1.5.safetensors` `strength_model` 全是 **1.5**；上一輪 policy 81 同位置是 1.5→1.75→2.0 | ✅ clamp 生效，重試只剩換 seed |
| RTX ×2 上採送 `ref_image_0` | Job／contract：node `9` `RTXVideoSuperResolution` `scale=2`、`quality=ULTRA` → `ref_images.ref_image_0`，`ref_image_size="match"`；輸出 **576×864 = 0.498 MP** | ✅ |
| 乾淨 V1 plate（不糊） | 餵給 H3 的 source 是 `h3ref_video_V1-…_v1_relay_8df6283643bf459a39b2_0.000-12.864.mp4`——檔名**不含** `identity_suppressed`、**不含** `_silent`；讀幀 row「PLATE fed to H3 (82)」是全銳利真人 coser | ✅ |
| 原音保留 | `00_source.mp4` 與 `master.mp4` 都有 `Stream #0:1 aac LC 48000 Hz stereo`；`source_audio_timing_audit = {status ok, offset 0.0, correlation 0.983089}` | ✅ 未抽音且音畫未漂移 |
| 18 幀 Relay 自動串窗 | manifest **只有 1 個 segment**（`0.0–12.864`、`continuity=none`、`relay_window_count=3`、`window_frames=124`／`history_frames=18`／`schedule=adaptive`）；`target_duration_seconds 12.863792` 完整跑完（`master.mp4` 307 幀 @24 fps、12.8 s） | ✅ 單Shot＝單 render unit，Round 49-B2 的端點缺陷在實機上也沒有復發（無 5.0 s 截斷、無越 EOF） |

**C. 與 policy 81 基準（seed 923011008）同位元組對比 —— 身份／衣柜確實變好**

| 指標 | policy 81 | **policy 82** | 方向 |
|---|---|---|---|
| `target_reference_similarity`（選中的 attempt） | 0.555226 | **0.613560** | ↑ +0.0583 |
| `retention_score` | −0.298300 | **−0.225781** | ↑ 較不負 |
| `wardrobe_shift`（脫離 V1 服装的程度） | 0.082626 | **0.136518** | ↑ 換到全身 |
| QC 失敗原因 | 「replacement is only a head/face layer; the V1 wardrobe still fills the lower half」 | 「authored Silent Listener mouth shows excessive articulation」 | 頭部貼片症狀**消失**，紅燈換成嘴 |
| `wardrobe_audit.passed` | —（被 head-only 蓋掉） | **true**（upper shift 0.1826／lower 0.1365） | ✅ |

讀幀（`_dsh_verify_9\round49\montage_82_vs_81.png`，7 個時間點 × 4 列）：82 這一槍拿回 **圓眼鏡**、光頭＋參考圖那幾根頭髮、年輕臉（基準是灰白頭髮的老人）、袍服主色是 P1 的黑＋藍；**全身都是卡通繪製**（手／袖／袍不是真人），背景為乾淨實景、**無蜂窩紋**、**無 identity sheet 下半身竄入**。

讀幀（`montage_82_seams.png`，三個 5 格帶）：Relay 窗邊界 **≈4.29 s** 與 **≈8.58 s** 前後，角色的臉、頭飾、袍服、眼镜**連續無跳變**；用戶上次抱怨的「第 4 秒出現 character sheet 下半身」在本槍 3.6–4.4 s 帶內**未出現**。⇒ 「18 幀 history 串窗 ⇒ 身份前後一致」這條在實機上成立。

**D. 唯一退步項：silent listener 的嘴（且 QC 的參照系已過時）**

`silent_mouth_audit`（同 `bbox [0.425,0.306,0.575,0.414]`、同 `band_registration head_crop`）：

| 欄位 | policy 81（糊＋凍結＋抽音 plate） | **policy 82（乾淨 plate＋原音）** |
|---|---|---|
| `plate_motion`（模型看到的 plate 嘴帶動度） | 0.071193（被 `tmix` 凍結） | **0.142404**（=V1 真人自己在動） |
| `plate_relative_motion_limit` | 0.118790 | **0.225607** |
| `result_motion` | 0.182128 | **0.260531** |
| `articulation_excess`（超出上限多少） | 0.012425（**超 53%**） | 0.034924（**超 15%**） |
| `geometry_violated`／`source_speech_conflict` | false／false | **false／false** |

判讀：`verdict_scope` 仍寫 `relative_to_suppressed_plate`，但出厂已不再有 suppressed plate ⇒ 分母從「凍結的嘴」換成「會動的 V1」，門檻其實已自動放寬 1.9×，**超標幅度反而從 53% 降到 15%**；幾何通道（嘴腔張合 0.325 vs 上限 0.52）判不违规，只有像素通道 red。同時官方 Character Swap prompt 本身就寫「match … visible mouth movements」，而 Silent Listener 是我們的覆蓋語意 —— 兩者在「保留原音」後天然衝突。⇒ 這已不是模型發明的毛病，而是**閾值参照系要重新定義**（= Round 47 提案③的範圍）。本輪**未動碼**。

**E. 界定**
- **影片已實機驗證（本槍）**：五項出厂對齊全部生效；單 Shot＝單 render unit × 3 原生窗且端點正確；原音保留且音畫對齊 0.983；身份相似度與衣柜換新度**雙雙改善**；頭部貼片／真人衣服症狀消失；跨窗身份一致；背景乾淨。
- **影片未通過的部分**：QC 仍 `character_swap_identity_failed=true`、`failure_class silent_mouth_excessive_articulation`（第 3 發被選中，`selected_attempt 3`）；影片照樣輸出，**要不要接受由用戶肉眼判**（本槍是迄今身份最接近 P1 的一支）。
- **仍未解／等表態**：① silent 微超標降 advisory（現在有硬數據：超標 15%、`geometry_violated false`、plate 自己會動、官方語意本來就要求嘴部動作）② 0.5 MP 是否改 1.0 MP（bucket `megapixels>=0.75 ⇒ "768"`）③ Round 47 另兩案（衣柜門檻改相對、禁 invented 額頭皺紋／維持參考圖年齡）④ 袍服上的紅金滾邊仍是 invented detail，P1 沒有。
- **逃生門本槍未使用**：三個 env（`H3_CHARACTER_SWAP_PLATE_SUPPRESSION`／`_SILENT_AUDIO_STRIP`／`_RELAY_WINDOW_SPLIT`）出厂 off 的假設已被實機支持；若 silent 嘴最終不可接受，只需 `H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1` 單獨回退嘴帶凍結。

**F. 本輪工具（零 GPU 重用）**：`working\_r49_montage.py`（policy 82 vs 81 四列七點，左欄掛 P1 sheet）、`working\_r49_seam_montage.py`（三個 5 格時間帶：兩處 Relay 窗邊界＋可疑洩漏帶）。輸出在 `_dsh_verify_9\round49\`。


### Round 49c：policy 82 出厂路徑的 **1.0 MP 實機一槍**（2026-10-30 12:25–12:51，seed 923011207，**影片已實機驗證＝本專案首發單發全綠 QC**）

**A. 範圍**：本輪**未動任何產品源碼** ⇒ `SMART_RENDER_POLICY_VERSION` 維持 **82**、`VERSION` 維持 `0.3.8-alpha.3`，測試沿用 Round 49 的 352 項全綠，不需重跑。唯一變因是 Job 的 `megapixels` 0.5 → **1.0**（用戶實測回報「有很大增益」後開的一槍）。

**B. 出槍前的離線 pre-flight（`working\_r49c_preflight.py`，零 GPU，七項全過）**
1. policy 82／`megapixels=1.0`／單段 `0.0–12.864`（單 Shot＝單 render unit，沒有被切段）。
2. adapter `h3_character_swap_v1.5.safetensors` `strength_model=1.5`（官方上限 1.5，不再出現 1.75／2.0）、turbo `0.8`。
3. node `9` = `RTXVideoSuperResolution scale=2 / ULTRA` → `ref_images.ref_image_0`，`ref_image_size="match"`（對齊手動工作流的 ×2 上採）。
4. plate 乾淨：檔名**無** `identity_suppressed`、**無** `_silent`，實檔帶 `aac` 音軌（沒有抽音軌）。
5. `window_frames=124`／`history_frames=18`／`schedule=adaptive`（18 幀接力）。
6. **1.0 MP 生效判據**：`H3RelayPrepareSource resolution="768"`（bucket `megapixels>=0.75 ⇒ "768"`）。
7. prompt 11,791 chars／1,802 words、`char_budget 12,320`、`dropped_tail_clauses=[]` ⇒ 尾端條款沒被截掉。

**C. QC 全部綠燈（本專案開專案以來第一次，`attempts_used=1`）**
`status=complete`、`error=""`、`failure_class=""`、`character_swap_identity_failed=false`、`selected_attempt=1`、`passed=true`；`target_reference_similarity=0.630127`（floor 0.30）；`retention_score=-0.330738`；衣柜 `shift=0.130169`／`late=0.127764`（upper 0.16266、lower 0.130169，floor 0.12 **兩半都過**、`source_wardrobe_retained=false`）；`complete_actor_erasure_audit passed`（`identity_similarity_gap=-0.121683`）；`whole_character_integration_audit passed`（`source_body_retained=false` ⇒ 不是只換頭）；`source_plate_continuity_audit passed`（左右旁角相關 0.654／0.398）；`silent_mouth_audit passed=true`（見 D）；`source_audio_timing_audit {status ok, offset 0.0, correlation 0.983089}`。
輸出 ffprobe：`master.mp4` **800×1216 = 0.973 MP**、24 fps、12.8 s、h264＋**aac**；`relay_window_count=3`；ComfyUI 原始檔 `pass_01_R1_00004_.mp4`。

**D. silent 為什麼算「過」——誠實拆開講（讀 `smart_render_worker.py` 的判定字面值）**
- `plate_relative_violated=true`：嘴部帶 `result_motion 0.279222` 確實高於 plate 上限 `0.225607`（`articulation_excess 0.053616`，超 5.4%），但 `plate_gate_mode=advisory` ⇒ **不硬判**。
- 真正的決定項是 `motion_violated=false`：參考帶改用上半臉控制帶，`upper_face_motion 0.254111` ⇒ 相對上限被放到 **0.337638** > 0.279。也就是**整張頭在動（轉頭），不是對嘴**。
- 獨立第二通道 `geometry_violated=false`：嘴腔張合 `mouth_opening_swing 0.15` vs 上限 `0.22`；`source_speech_conflict=false`；`decision_basis=pixel_motion`。
- 措辭待修（不是功能缺陷）：`verdict_scope` 仍寫 `relative_to_suppressed_plate`，但出厂已無 suppressed plate ⇒ 參照系名稱過時。

**E. 讀幀證據（`_dsh_verify_9\round49c\`）**
`detail_fullheight.png`（P1／乾淨 plate／1.0 MP／0.5 MP × t=0.5/6.0/12.3，原生解析度全身行）：卡通媒介保留、**頭/手/袍/腿全部是畫的**（非貼頭）、背景乾淨**無蜂窩紋**、**沒出現 character sheet 下半身洩漏**。`mouth_strips.png`（兩個時間窗 × 14 幀嘴部帶逐幀）：轉頭全程**閉嘴笑、無開合說話**。三個 Relay 窗邊界（≈4.29 s／≈8.58 s）臉、眼鏡、袍服**連續無跳變**。

**F. 對 0.5 MP 基準（seed 923011107／Round 49b）的量化差**

| 指標 | 0.5 MP | 1.0 MP（本槍） |
|---|---|---|
| `target_reference_similarity` | 0.613560 | **0.630127** ↑ |
| `retention_score` | −0.225781 | **−0.330738**（更遠離 V1；對 swap 是好事，但要與相似度分開講） |
| 衣柜 lower `shift` | 0.136518 | 0.130169（略降，仍過 floor 0.12） |
| silent | `failure_class=silent_mouth_excessive_articulation`（3 發用盡） | **單發通過** |
| GPU 佔用 | ≈29 分鐘（3 attempts） | **≈22.5 分鐘（1 attempt）** |

**G. 肉眼仍存的品質缺口＝模型服從度，不是缺條款**（已用 ComfyUI `/history` 逐字證實）
prompt **確實含** `APPARENT AGE LOCK — MANDATORY`、`COMPLETE WARDROBE REPLACEMENT — MANDATORY`、媒介鎖定（cartoon 保持 cartoon）、silent 的 `relaxed closed mouth with the jaw still`、旁角 `R2: KEEP V1`（x15–30%、y25–45%），且 `dropped_tail_clauses=[]`。但成片仍：服裝**輪廓**沿用 V1 cosplayer 的長袍（P1 的黑背心＋藍短褲＋黃格紋襪只還原了配色）、臉比 P1 顯老（多出額頭紋、加出鬍子）、P1 頭頂三根毛沒出現、袍上紅金滾邊屬 invented detail。
⇒ 寫死結論：**「源碼已含條款」≠「模型已服從」**。要再推這三條得換變因（抽 seed／參考圖改半身構圖／再上採），而不是再加 prompt。

**H. 界定與逃生門**
- **影片已實機驗證（本槍）**：1.0 MP 生效（`resolution="768"` ⇒ 實際輸出 0.973 MP）、LoRA 1.5、RTX ×2、乾淨 plate、原音保留且音畫對齊 0.983、18 幀接力跨窗身份一致、身份／全身／衣柜／背景／無洩漏**五項全綠且單發通過**。
- **仍待用戶肉眼判**：最終像不像 P1（尤其服裝輪廓與臉齡）由用戶決定是否接受。
- **等用戶表態（不可順手塞入）**：① silent 硬閘方案 A（bump policy 83）② 衣柜門檻相對化 ③ 禁 invented 額頭皺紋／紅金滾邊、鎖參考圖年齡 ④ 服裝輪廓要不要換變因（抽 seed／參考圖改半身構圖／再上採）。
- **逃生門本槍未使用**：`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1`／`H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1`／`H3_CHARACTER_SWAP_RELAY_WINDOW_SPLIT=1`；LoRA ceiling 只能調低 `H3_CHARACTER_SWAP_LORA_MAX_STRENGTH`。
- **GPU 交棒**（tray log，未 bypass driver）：`12:25:55 QWEN→FREE` → `smart_render_worker` → `/free` → `12:49:00 load requested` → `12:50:04 load confirmed（63 s）` → `12:51:40 auto-resume`；全程 ComfyUI 與 Qwen 未同時常駐。ComfyUI 端除 driver 這一槍外只有唯讀 `/history`。

**I. 本輪工具（零 GPU、改 seed 即可重用）**：`working\_r49c_preflight.py`（Job 七項 pre-flight，讀 `segments[i].workflow`）、`working\_r49c_montage.py`（1.0 vs 0.5 四列比較，左欄 P1）、`working\_r49c_detail.py`（原生解析度全身行）、`working\_r49c_mouthstrip.py`（嘴帶逐幀）。讀幀目錄 `_dsh_verify_9\round49c\`。


### Round 43：policy 80→81 —— medium-silent plate 出厂關掉「衣著帶」（2026-10-30，**源碼已修復＋344 項測試通過；影片證據來自 seed 923011007 的 env `off`，policy 81 出厂路徑本身未實機**）

**A. 用戶回饋與 plate 侧根因**

用戶連續多輪點名同一組症狀：「只有頭替換、衣服是發明的」「背景出現蜂窩／怪圖案」。離線把 medium-silent gate 的 plate filter graph 逐條拆開量（`working\_r45_band_ab.py`，讀 Job／manifest，零 GPU）：

| plate 臂 | bands | 抑制畫面面積 | 後果 |
|---|---|---|---|
| `blur`（policy 69–80 出厂） | head + **2 條 wardrobe（y 0.285 → 1.0）** | **0.5013** | 頭＋整個衣身糊成色斑 ⇒ H3 照 V1 cosplayer 殘留配色自行發明服裝（紅金皇袍、金色鏤空滾邊、蜂窩） |
| `off`（policy 66 舊 plate） | head 一條 | **0.114** | 軀幹保留結構，服装改由 P1 identity sheet 決定 |

對照 plate 幀：`_dsh_verify_9\round46\PLATE_seg1_{OFF,BLUR}_t2.09.png`。

**B. 實機證據（seed 923011007 ＝ policy 80 源碼 + env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off`，3 窗 ×1 發，`staged_model_driver.py run`）**

衣柜 QC 重放（`working\_r41_wardrobe_replay.py 923011007 923010907`，讀 manifest，零 GPU）：

| 量測（規則 A：`wardrobe_shift ≥ 0.12`） | `blur`（seed 923010907，policy 78） | `off`（seed 923011007，policy 80） |
|---|---|---|
| 通過列數（3 窗 × upper/lower ＝ 6 列） | 1/6 | **5/6** |
| `wardrobe_shift` 平均 | +0.0972 | **+0.1658** |
| 衣柜 `target_similarity` 平均 | 0.5359 | **0.5876** |
| manifest `suppressed_frame_area` | 0.5013（3 bands） | **0.114**（1 band） |

- manifest 另記錄 `wardrobe_mode: off`、`prompt_budget.prompt_chars` 12208／12320、`dropped_tail_clauses` 空；`master.mp4` 完成、`/free` 正常（`preview_923011007_1793291935999553700.manifest.json`）。
- 讀幀拼圖 `montage_OFF_923011007.png`／`faces_off_923011007.png`／`compare_P1_blur_OFF.png`：黑上衣＋藍下襬＋黃格襪＋黑鞋＋卡通手 ⇒ 用戶認可為 **Studio 歷來最接近 P1 全身的一支**。
- ⚠️ **配對限制**：對照臂 923010907 是 policy 78＋每窗 3 次 attempt，`off` 臂是 policy 80＋每窗 1 次 ⇒ 方向性證據而非嚴格 A/B。同 seed 同段、嚴格配對的 `blur` 對照 Job 已建好未跑：`preview_923011007_1793291943180178000.job.json`（另兩份 `..._1793290942469688300`／`..._1793288348406948300` 分别是 blur 預覽與 policy 79 殘留）。
- **註解更正**：源碼舊註宣稱「`blur` 多花 660 字 prompt，因而被預算擠掉 Silent Listener 口型條款」，與盤上證據不符 ⇒ 兩份 policy-80 `blur` Job 編譯出 11935 字，比 `off` 實際提交的 12208 字**更短**（舊 policy-78 `blur` manifest 確實被丢掉 `plate_wardrobe_silent_clause`，但那是跨政策比較）。已改成可複驗的寫法。

**C. 改動（policy 80 → 81）**

| 檔案 | 內容 |
|---|---|
| `director_cut_studio.py` | `_medium_silent_wardrobe_band_mode()` 出厂 `"blur"` → `"off"`（env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE` 仍可 `blur`／`blur_desat`  rollback）；knob 上方註解塊改寫為上述實測鏈＋配對限制＋prompt 更正；`_character_swap_identity_suppressed_source()` docstring 同步標明出厂 `off`；政策 81 註解 + `SMART_RENDER_POLICY_VERSION = 81` |
| `smart_render_worker.py` | 政策 81 註解 + `SMART_RENDER_POLICY_VERSION = 81`（與 Studio 兩處同步 ⇒ 舊 plate／Job 快取自動失效） |
| `testing\test_character_swap_closeup_gates.py` | knob 預設斷言改 `off`（空 mapping 與垃圾值兩處）；**新增** `test_default_medium_silent_plate_agrees_with_the_shipped_knob`：未經 patch 的真實呼叫必須與 import-time 常量一致（`off` ⇒ strategy 不带 `_wardrobe_blur_suppressed` 尾碼、filter graph 內不得出現 `boxblur=6:3`）；另有 **5 項**原本依賴旧出厂值的測試改為明確 pin `blur` 臂（`test_medium_silent_suppression_blurs_head_band_with_own_strategy`、`test_figure_extent_knob_rolls_the_plate_back_to_policy_68`，以及經 `_hair_band_arm()` helper 的 3 項 hair-band 測試） |

**D. 驗證**
- `py_compile`：`director_cut_studio.py`／`smart_render_worker.py`／`character_swap_engine.py`／`testing\test_character_swap_closeup_gates.py` 全過。
- `test_character_swap_closeup_gates` **77 tests OK**；`test_smart_render_worker`＋`test_character_swap_engine`＋`closeup_gates`＋`background_extra`＋`silent_audio`＋`silent_mouth_motion_gates`＋`silent_mouth_transient_qc`＋`test_identity_sheet`＋`test_smart_render_qc_advisory`＋`test_workflow_engine` 合計 **344 tests OK（skipped=2）**（基線 343 ＋ 本輪新增 1 項出厂一致性守門）。
- 本輪**未碰 GPU**：全部結論來自 manifest／Job 重放與讀幀。

**E. 界定**
- **源碼已修復**：出厂 plate 只剩 head band，衣柜不再被糊掉；`blur`／`blur_desat` 退為 env 臂；policy 81 讓舊 plate 快取失效。
- **影片已實機驗證**：`off` 這條 plate 路徑確實能把 P1 服装穿完整（seed 923011007）。⚠️ 該槍是 **policy 80 源碼 + env 覆蓋**，**policy 81 出厂路徑本身尚未實機**。
- **仍未解**（prompt／sheet 軸，與 plate 無關）：① P1 圓眼鏡每窗都丟 ② 發明的額頭皺紋 ⇒ 變老人 ③ 滾邊仍是金色鏤空而非白滾邊 ④ silent 對嘴仍被 QC 點名（三窗皆 `authored Silent Listener mouth shows excessive articulation`）⑤ 衣柜絕對地板 0.12 在 `off` regime 誤傷（W3 lower `shift 0.0906`、`target_similarity 0.4905`，規則 C／D／E 皆判過）。

### Round 42：policy 79→80 —— 衣柜線索加驗「尾端窗」，重試選片改用兩窗中較好的那個（2026-10-30 凌晨，**源碼已修復＋343 項測試通過；影片未實機**）

**A. 用戶回饋與硬證據（seed 923010907，3 窗 ×3 attempt 共 9 支候選）**

用戶看過影片後指出：「在这些影片中，我能接受的是 `pass_01_R1_00039_`」——九支候選裡唯一能接受的一支，而 worker 選的却是 `00040`。逐幀放大比對（`_dsh_verify_9\round42\` 對照幀）得到三個事實：

1. **00039 的尾段（t≈0.886）確實穿上 P1 服装**（黑背心＋白珠領＋藍袖＋黃格短褲），前段還是發明的紅金袍；00040 全程紫黑豹紋袍＋照片式陰影（真人化漂移）。⇒ 00039 是「服装來得晚」，00040 是「服装從來沒來」。
2. **九支候選全都没有 P1 的圓眼鏡**（00039／00043 放大確認）⇒ 身份訊號裡沒有眼鏡可依附，排名只能靠色彩與衣柜。
3. 排名複合分數 00039 落後 00040 達 **0.0984**，而兩者的 `wardrobe_shift` 只差 **0.005** ⇒ 勝負其實由 64×64 色彩直方圖决定，衣柜項形同啞彈。

**B. 根因：衣柜 QC 只按 `0.22 / 0.50 / 0.78` 三點取 median，而且只看「移動較少的半身」**

`inspect_character_swap_identity` 的衣柜線索綁定 upper/lower 其中一半（取移動較小者），再對三個採樣點取 **median**。服装在尾端才出現的 take，其 0.22／0.50 兩點仍是原始演員顏色 ⇒ median 被前段拖平；再加上「看較差的半身」，00039 的真實衣柜位移被系統性低估。離線重放（`working\_r43_region_timing.py`，照生產語義重算）：

| 窗 | attempt | median（0.22/0.50/0.78） | late（0.78/0.86/0.94） | 生產選片 |
|---|---|---|---|---|
| W1 | 00043 / 00044 / 00045 | +0.097 / +0.113 / +0.146 | +0.117 / +0.233 / +0.267 | 00044 |
| W2 | 00035 / 00036 / 00037 | +0.189 / +0.134 / +0.161 | +0.214 / +0.262 / +0.195 | 00037 |
| W3 | **00039** / 00040 / 00041 | +0.165 / +0.133 / +0.137 | **+0.251** / +0.167 / +0.284 | **00040** |

把排名改讀 `late`（或兩窗取優）後回放：**W3 選出 00039**（用戶唯一接受）、W1 不變、W2 從 00037 變成 00036。00036／00037 用戶都不接受，所以這不是「已認可結果的倒退」，但仍屬行為改變，須如實記錄。

⚠️ **保留意見**：探針重算的 median 系統性比 manifest 記錄高 +0.04…+0.11，且 W3 兩者順序相反（探針 00039>00040，記錄 00039<00040），推測來自實際 probed duration／seek ladder 差異 ⇒ 回放結論是**方向性證據**，不是保證。

**C. 負面結果（已排除，請勿重蹈）**

`working\_r43_selection_replay.py` 曾嘗試把「卡通媒介平塗度／飽和度」放進排名：只能把 00040 擠到最後，抓到的是 flatness 而不是身份或年齡（00041＝最卡通的老人會排第一），還會動到 W2。⇒ **平塗指標不採用**。

**D. 改動（policy 79 → 80；設計原則：QC 與 retry 觸發仍讀 median，只有排名可以看較好的窗）**

| 檔案 | 內容 |
|---|---|
| `smart_render_worker.py` | 新增政策 80 註解與 `SMART_RENDER_POLICY_VERSION = 80`；`inspect_character_swap_identity` 新增 `wardrobe_late_timestamps`（0.86／0.94，沿用 0.78 點既有解碼 ⇒ 每線索只多 2 次 decode）、region row 新增 `wardrobe_shift_late`、body row 沿用同一半身綁定改窗取樣、`wardrobe_audit` 新增 `late_shift` 與 `late_timestamps_normalized`、結果頂層新增 `wardrobe_shift_late`；`_candidate_target_likeness` 改為在 `wardrobe_shift` 與 `wardrobe_shift_late` 兩個可解析值中取 **max**，仍受 `min(0.35, …)×1.5` 上限約束；candidate assembly 與 `identity_candidate_scores` 一併帶出 `wardrobe_shift_late` |
| `director_cut_studio.py` | 政策 80 註解 + `SMART_RENDER_POLICY_VERSION = 80`（兩處同步） |
| `testing\test_smart_render_worker.py` | 新增 4 項：`test_retry_selection_reads_the_late_wardrobe_window`（用 923010907 W3 真實數字，無 late 時選 attempt2、有 late 時選 attempt1）、`test_late_wardrobe_window_ignores_an_unparseable_measurement`、`test_late_wardrobe_lead_cannot_outvote_a_surviving_v1_face`（V1 臉仍在時 0.70 罰分仍壓過尾端衣柜優勢）、`test_wardrobe_audit_records_a_costume_that_arrives_late`（`drawbox enable='gte(t,1.6)'` 造一支「尾端才換装」的影片，斷言 median 仍判 fail 但 `wardrobe_shift_late ≥ 0.12` 且 audit 記錄一致） |

**E. 驗證**
- `py_compile`：`smart_render_worker.py`／`director_cut_studio.py`／`testing\test_smart_render_worker.py` 全過。
- `test_smart_render_worker` **69 tests OK（skipped=1）**；`test_character_swap_engine`＋`test_character_swap_closeup_gates`＋`test_character_swap_background_extra`＋`test_character_swap_silent_audio`＋`test_silent_mouth_motion_gates`＋`test_silent_mouth_transient_qc`＋`test_identity_sheet`＋`test_smart_render_qc_advisory`＋`test_workflow_engine` **274 tests OK（skipped=1）**。合計 **343 項**。
- 本輪**未碰 GPU**：全部結論來自離線幀重放與合成 fixture。

**F. 界定**
- **源碼已修復**：排名現在看得見「尾端才到场的服装」，且 QC／retry 門檻刻意保持 median 语义（尾端才算數仍然是缺陷、仍然該重試）。
- **影片未實機**：下一槍 `923011007`（policy 80）能否真的選出 00039 那類 take，必須讀幀才算數。

**G. 本輪新增離線探針**：`working\_r43_media_probe.py`（平塗/飽和指標）、`_r43_selection_replay.py`（排名回放，負面結果）、`_r43_wardrobe_timing.py`（全身框 19 點時序）、`_r43_region_timing.py`（**生產語義**的 region binding 回放）。

### Round 41：policy 78→79 —— `plate_wardrobe_silent_clause` 退出 prompt 長度守衛（2026-10-29 深夜，**源碼已修復＋250 項測試通過；影片未實機**）

**A. 根因（Round 40 seed 923010907 的硬證據，探針 `working\_r41_prompt_sections.py`／`_r41_clause_lengths.py`）**

Silent Listener 的「plate 頭＋衣柜模糊」段落 `plate_wardrobe_silent_clause`（847 字元）原本是 tail 長度守衛的 **rank 0**（第一個被犧牲的條款）。三個視窗的提交 prompt 全部是 **11 746 / 12 320**，而該條 847 字元剛好就是超出額度（超出 273）⇒ `dropped_tail_clauses=["plate_wardrobe_silent_clause"]` 三窗全中。後果：模型看到的 plate 頭像裡衣柜顏色已被模糊，卻沒有任何一句話告訴它「那些顏色屬於被擦除的原始演員、不要照著重建服装」⇒ 逐窗各自發明服装（W1 黑袍紅腰帶、W2 棕色針織袍、W3 黑袍藍襬），正是用戶回報的「衣服完全不像參考圖」。

同時證明這次犧牲**沒有換到任何東西**：在保留 mouth reinforcement 的情況下 W2／W3 仍然對嘴；模組註解亦記錄 seed 97000374 失去 reinforcement 照樣對嘴、97000454 保留 reinforcement 也照樣對嘴。亦即「丟衣柜段落以保嘴部提醒」這筆交易在實機上是雙輸。

**B. 改動（policy 78 → 79；三檔）**

| 檔案 | 內容 |
|---|---|
| `character_swap_engine.py` | `CHARACTER_SWAP_TAIL_DROP_RANKS` 移除 `"plate_wardrobe_silent_clause": 0` ⇒ 該條改為 **never-droppable**（繼承它所取代的兩段 never-droppable 段落的地位）。剩餘 ranks 不變：1 `close_up_silent_mouth`／2 `medium_shot_silent_mouth`／3 `source_costume_leaves_plate`／4 `close_up_sheet_crop_lock`。兩處註解改寫並附上 923010907 實測證據 |
| `smart_render_worker.py:179`、`director_cut_studio.py:786` | `SMART_RENDER_POLICY_VERSION = 79`（兩處同步）。無任何 `policy >= N` 數值分支依賴 78 |
| `testing\test_character_swap_engine.py` | 舊測試改名 `test_silent_merged_clause_never_yields_and_the_mouth_reminder_does`：斷言 `plate_wardrobe_silent_clause` **不在** RANKS、超額時 `dropped == ["medium_shot_silent_mouth"]`、`MERGED_PLATE_HEADER` 仍在 prompt、`MEDIUM-SHOT SILENT MOUTH REINFORCEMENT` 不在 prompt |

**C. 離線驗證（改動後的同一編譯路徑）**
- 同一路徑的 prompt 落在 **11 821 ≤ 12 320**，只丟一次、丟的是 `medium_shot_silent_mouth`（重述性最強的嘴部提醒），衣柜段落存活。
- `py_compile`：`character_swap_engine.py`／`smart_render_worker.py`／`director_cut_studio.py` 全過。
- `test_character_swap_engine` **80 tests OK**；`test_smart_render_worker`＋`test_storyboard_segment_mapping`＋`test_character_swap_closeup_gates`＋`test_workflow_engine` **170 tests OK（skipped=2）**。合計 250 項。

**D. 界定**
- **源碼已修復**：衣柜段落不再被長度守衛犧牲，且測試已綁死這個行為。
- **影片未實機**：逐窗衣柜忠實度（P1＝黑色上衣＋藍下襬＋黃色格子短褲）能否真的穩定，必須等新 policy 79 的槍（下一 seed `923011007`）讀帧才算數。

**E. 本輪新增離線探針**：`working\_r41_wardrobe_replay.py`（回放 manifest 衣柜 QC、模擬 5 種判定規則）、`_r41_prompt_sections.py`（從 ComfyUI `/history` 逐段量字元並列出缺席段落）、`_r41_clause_lengths.py`（用 `ast` 從原始碼量 tail 段落長度）。

### Round 40：H3-Character-Swap-Relay-V2-api.json 換檔 —— node 7（`ImageScaleToTotalPixels` 1.0 MP）拿掉，改送 node 9 `RTXVideoSuperResolution`（ULTRA ×2）進 `ref_image_0`（2026-10-29 實機三窗 seed 923010907，**未改任何原始碼（policy 78 不變）＋影片已實機驗證＝眼鏡／臉齡與 invented 頭飾兩項已修，衣柜忠實度仍未修**）

**A. 這是 workflow JSON 的改動，不是程式碼改動**

| 項目 | 內容 |
|---|---|
| 節點级 diff（vs `H3-Character-Swap-Relay-V2-api.json 261029-1`，探針 `working\_r39_wfdiff.py`） | ①刪除 node `7` = `ImageScaleToTotalPixels`（megapixels 1.0）②新增 node `9` = `RTXVideoSuperResolution`：`images=[reference,0]`、`quality=ULTRA`、`resize_type.scale=2.0`、`strength=1.0`、8-bit RGB ③`ref_images.ref_image_0` 改接 `["9",0]`。模板 `LoadVideo` 檔名也換了，但對本專案無效（worker 逐段覆寫）。**模型檔／VAE／LoRA／取樣器全未動 ⇒ 乾淨單變量 A/B（基準 923010807）** |
| Render Policy | **78（不變）**；VERSION `0.3.8-alpha.3`、Project Format 29 不變；本輪無 `py_compile`／unittest 必要（原始碼零改動） |
| 遠端節點可用性 | `object_info/RTXVideoSuperResolution` 已確認存在且欄位吻合 |

**B. 實機證據：node 9 真的上線，不是只有離線宣稱**
- ComfyUI `/history`（prompt `a86934b3…` 與 `6bf5bd30…`，探針 `working\_r40_history_probe.py`）：36 節點、node `9` 在場且輸入為 `{ULTRA, scale 2.0, strength 1.0, images:["reference",0]}`、`ref_images.ref_image_0 = ["9",0]`、圖中已無任何 `*Scale*` 節點；`LoadImage` 仍指 `…_identitysheet08_fullfig_a0066_v8.png`。
- **幾何理由**（為何 ×2 應該有幫助）：sheet 800×1216＝0.973 MP，但**頭部面板只有 405×346**（衣柜面板 250×359）。×2 後 1600×2432＝3.89 MP、頭部約 810×692，而且是 RTX ULTRA 智能放大而非 nearest-exact ⇒ 直打 Round 38b 的「眼鏡消失／臉變老」根因。

**C. 目視讀帧結論（一定要親眼看，QC 目前不可全信）**
| 判定 | 923010807（node 7 / 1.0 MP） | 923010907（node 9 / RTX VSR ×2 ULTRA） | 界定 |
|---|---|---|---|
| **圓眼鏡＋鬍子＋臉齡**（head-crop A/B，`working\_r40_faces.py` → `_dsh_verify_9\round40\faces\faces_ab.png`） | W1 只有第一格還剩眼鏡，W2／W3 **完全沒有眼鏡**且臉明顯變老 | **W1 三格全部保留 P1 的圓眼鏡＋鬍子、臉變年輕**，最接近参考圖 | ✅ **實機驗證：38b 的兩項退步在 W1 已修** |
| **W1│W2 邊界 invented 頭飾**（`_r40_seam.py` → `round40\seam\seam.png`） | t≈4.5–5.0s 冒出**貓耳帽＋長黑髮＋真人臉** | 同一位置**完全沒有出現** | ✅ **實機驗證：invented 頭飾缺陷消失** |
| **衣柜忠實度**（P1＝黑色上衣＋藍下襬＋**黃色格子短褲**） | 三窗都是 invented 黑底金邊長袍 | W1 黑／藍袍紅腰帶、W2 棕色針織袍、W3 黑袍藍襬，**只有 W3 t≈3.8s 出現真正的黑上衣＋黃格子短褲** | ❌ **未修**：逐窗各自发明服装，已不是貼臉問題 |
| **silent 閉嘴** | W1 過、W2 超標 0.00376、W3 過 | W1 過（excess 0.0）、W2 邊緣 0.00157、**W3 超標 0.0527（嘴開合 0.275 vs 對照 0.0875）** | 未修（W3 仍在對嘴） |
- 成本／VRAM **無退步**：907 九次生成（3 窗 ×3 attempts）約 25 分鐘，807 七次約 37 分鐘；driver `/free` 實測 5.77→4.33 GB。產物 `cache\generated_outputs\preview\923010907\master.mp4`（11 041 424 bytes，3 段 complete）。

**D. 順手挖到的兩個結構性根因（本輪未修）**
1. **衣柜條款每次都被丢掉**：三窗 `dropped_tail_clauses=["plate_wardrobe_silent_clause"]`，最終 prompt 11 746／天花板 12 320（只剩 574 字元），而那條條款 ≥575 字元 ⇒ 一定塞不進去。它_rank 0_是刻意排第一个犧牲的（`character_swap_engine.py:153`、裁切迴圈 2229–2247），理由是「衣柜義務已由無條件的 COMPLETE WARDROBE REPLACEMENT 承擔」。但 Silent Listener plate 現在**連衣柜帶一起模糊**，而這條正是告訴 H3「plate 上那些糊掉的衣物色是故意的、不要照著重建一套服装」——它被丢，正好對應本輪三窗各自发明长袍的現象。
2. **衣柜 QC 的絕對地板仍然失準**：`minimum_wardrobe_shift=0.12` 是拿生成結果去比**被模糊過的 plate**，所以量到的是「離 plate 色遠不遠」而不是「像不像 P1 的衣服」。W3 的 row 同時寫著 `target_similarity 0.513 > source_similarity 0.418`（已經比源圖更接近 P1）卻被絕對地板判 fail ⇒ 對已經合格的好 take 白燒重試（本輪 3 窗全部燒滿 3 次 attempts）。
3. 另外：`enable_rtx_vsr` 對 Character Swap pass 依然無效（只有 `workflow_engine.apply_generation_parameters()` 讀它，swap 編譯路徑從不呼叫），所以新 workflow 的 node 9 **一律生效**，Studio 那個勾選框對替换 pass 是裝飾。

**E. 本輪工具與坑**
- 新增探針：`working\_r40_history_probe.py`（打 ComfyUI `/history` 讀實際提交的圖）、`_r40_faces.py`（head-crop A/B）、`_r40_prompt_probe.py`（逐窗 prompt 預算／丢条款）、`_r40_retry_scores.py`（從 driver stdout 抽每次重試的候選分數）、`_r40_montage.py`／`_r40_seam.py`。
- ⚠️ **坑**：`_r38b_montage2.py`／`_r38b_seam.py` 把抓下来的影格以**列索引**為檔名快取，換 seed 順序時會無聲地混到舊 seed 的影格 ⇒ 必須換輸出目錄（本輪已複製成 round40 版本），否則會讀到錯的圖。
- 啟動坑：`Start-Process -ArgumentList` 不會自動加引號，含空白的絕對路徑會被切爛（本輪第一次啟動因此 `unrecognized arguments`）；要寫成 `"`"$jobPath`"`"`。
- 已用 seed：**923010907**（下一槍 `923011007`）。

### Round 38–38b：policy 77→78 —— 参考圖太小就不再單圖直通，改送「單人 fullfig 全身 sheet」；換檔＋1.0 MP 後衣柜主色終於跟住 P1（2026-10-29 修碼＋測試＋實機三窗，**源碼已修復＋影片已實機驗證＝部分改進、部分退步**）

**A. 源碼改動（全部已寫入、已驗綠）**

| 項目 | 改了什麼 | 檔案／位置 |
|---|---|---|
| 低解析参考偵測 | 新增 `_identity_sheet_min_source_megapixels()`／`IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS`，地板 **0.35 MP**；`H3_IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS=0` 或負值＝關閉此路徑 | `director_cut_studio.py` 約 1531–1573 行 |
| 單人 fullfig 路由 | `_character_swap_identity_sheet_reference()` 改用 `own["canvas"]` 算實際 MP；**低於地板時不再單圖直通**，改寫 `single_figure_fullfig=True` ⇒ 強制 `IDENTITY_SHEET_CLOSEUP_PRESET`（引擎 8）＋ `outfit_view="full"`（單人全身衣柜视图） | `director_cut_studio.py` 約 35060 行起 |
| 決策欄位 | `IDENTITY_SHEET_DECISION_KEYS` 加入 `identity_sheet_source_reference_megapixels`、`identity_sheet_single_figure_fullfig`（會進 manifest／指紋，便于事後取證） | 同上 |
| Render Policy | **`SMART_RENDER_POLICY_VERSION = 78`** | `director_cut_studio.py` 786 行、`smart_render_worker.py` 179 行（兩處同步） |
| Workflow（用戶親測換檔） | node `"7"` `ImageScaleToTotalPixels.megapixels` **2.0 → 1.0**（`resolution_steps` 1、nearest-exact）。用戶實測「有很大增益和效果」後要求保留；同檔 `_OLD.json`／`-ori.json`／`.bak-*` **未動** | `H3-Character-Swap-Relay-V2-api.json` 24 行 |
| 測試 | `testing\test_identity_sheet.py` 新增 `HIGHRES_WAVING_CANVAS=(704,1034)` 與 3 項測試：低解析改走 fullfig、地板=0 還原單圖直通、預設地板確實生效 | `testing\test_identity_sheet.py` |

**B. 實機兩槍（每槍都有用戶獨立批准；GPU 全程走 `staged_model_driver.py run`）**

| seed | 配置 | 窗口 | wardrobe upper/lower（門檻 0.12） | 衣柜判定 | target_sim | attempts | silent articulation（門檻 0.055） |
|---|---|---|---|---|---|---|---|
| 923010607 | policy 77＋舊 sheet | W1 | 0.1739 / 0.1212 | 過 | 0.6321 | 3 | 0.0349 過 |
| 923010607 | 〃 | W2 | 0.1627 / 0.1341 | **全過** | 0.4706 | 1 | 0.0855 violated |
| 923010607 | 〃 | W3 | 0.2348 / 0.1574 | 過 | 0.5397 | 3 | 0.0611 violated |
| 923010707 | 換檔 A/B（僅換 workflow） | W1 | 0.1211 / **0.0710** | **FAIL（lower）** | 0.6016 | 3 | 0.0 過 |
| **923010807** | **policy 78（fullfig）＋1.0 MP** | W1 | 0.1090 / **0.0648** | **FAIL（lower）** | **0.6063** | 3 | **0.0 過** |
| **923010807** | 〃 | W2 | **0.1134** / 0.1224 | **FAIL（upper）**＋silent violated | **0.6243** | 3 | 0.0038 violated |
| **923010807** | 〃 | W3 | 0.1580 / 0.1228 | **全過** | 0.5309 | 1 | 0.0440 過 |

數值為本輪一手複驗（manifest `preview_923010807_1793277219035091900`，`attempts_used` 3/3/1，三窗 `status=complete`；`comfy-free ok`，VRAM 5.65→4.65 GB）。兩個 seed 的每一 region 都是 `target_similarity > source_similarity`（923010807：0.5405/0.4314、0.5486/0.4838、0.5484/0.4350、0.5453/0.4229、0.5761/0.4181、0.5641/0.4413），erasure／whole-body／plate 全部 passed。

**C. policy 78 路由在實機確實生效（不是只存在測試裡）**：923010807 manifest 內 `identity_sheet_source_reference_megapixels = 0.09324`（P1 上傳原圖僅 0.093 MP，低於 0.35 地板）⇒ `identity_sheet_single_figure_fullfig = True`、`identity_sheet_preset = 8`。923010607（政策 77 時建 Job）無此兩欄 ⇒ 前後對照成立。

**D. 讀圖結論（montages 親眼核對，非僅依賴 QC）**
- 923010807 的**改進**：衣柜主色轉為**黑色系**（貼近 P1 黑衫），不再出現 V1 的粉紅袍＋貓耳；silent 對嘴明顯改善（三窗 articulation 0.0／0.0038／0.0440，全部低於 923010607 同窗值）。
- 923010807 的**退步**：**P1 的大圓眼鏡在 W2／W3 消失**、臉變老（皺紋／法令紋）；W2 開頭（≈4.2–4.5 s） invented **黑色帽＋長髮＋貓耳**；衣柜細節仍是發明出來的紅金織錦滾邊，不是 P1 的剪裁。
- 對照組 923010607（用戶曾接受）：眼鏡幾乎每格都在、臉更像 P1，但粉紅袍／貓耳是源片衣柜殘留。
- ⇒ **QC 判定與肉眼排序目前是反的**：923010607 過閘但視覺更差，923010807 觸閘但衣柜更對 ⇒ `minimum_wardrobe_shift` 的絕對地板對 medium shot 已失準，下一步應改成 target-vs-source 相對偏好判定。
- 用戶上次回報的「第 4 秒出現 character sheet 下半身」殘影，本槍**未重現**（未見 sheet 分隔框／下半圖鬼影）。
- Round 38（923010707）只跑 1 窗且 lower-wardrobe 0.0710 退步，**不足以單獨歸因換檔增益**；本輪真正的變量是 38b 的「fullfig sheet × 1.0 MP」兩者綁在一起，尚未拆開。

**E. 狀態界定**
- **源碼已修復**：policy 78 低解析→fullfig 路由、決策欄位、workflow 1.0 MP、3 項新測試。
- **影片已實機驗證＝部分成功**：衣柜主色與 silent 確實變好（用戶可目視確認 `cache\generated_outputs\preview\923010807\master.mp4`）；**眼鏡遺失與臉變老尚未解決**，因此本輪**不能**寫成「角色替換已达标」。
- **尚未驗證**：1.0 MP 對身份細節的貢獻（假設：1.0 MP 讓参考 token 變少 ⇒ 身份細節先被犧牲）、第二張 close-up 頭部参考、衣柜 QC 校準。
- **測試（一手）**：`test_identity_sheet` 55 OK、`test_character_swap_closeup_gates` 76 OK、`test_character_swap_engine` 80 OK、`test_smart_render_worker` 65 OK (skipped=1)、`test_staged_model_driver` 25 OK、`test_storyboard_segment_mapping` 4 OK ⇒ **Ran 305 tests，OK (skipped=1)**；`py_compile` 四檔 rc=0。`test_director_timeline` 依慣例跳過。

### Round 37l–37p：policy 75→76→77 —— 76 是**測出來的零增益**，77 讓重試排名不再拿「最像 P1」獎勵一張張開的嘴（2026-10-28 15:30–20:20 修碼＋測試＋實機兩槍，**源碼已修復＋影片已實機驗證＝用戶接受**）

**A. 兩處政策改動（全部已寫入、已驗綠）**

| 政策 | 改了什麼 | 檔案／位置 | 結果 |
|---|---|---|---|
| **75→76** | silent 條款**去語音化措辭**：不再寫 "the speech is off screen"／"not the audible speaker"／"Every audible voice … is background sound"，改成宣告「本 Shot 人聲頻道為空」，與本專案已驗證的 speech-free 音軌通路同一说法。理由：讀取端點**真的收到**的 prompt，發現 speech／speaker／audible／voice／audio 出現 5 次且**全是正面語句** —— 用来壓嘴的句子同時也是整段 caption 裡唯一證明「這 Shot 有可聽語音」的證據 | `smart_render_worker.py` silent 條款建構處（政策註解 129–149 行） | **實機 A/B 零增益 ⇒ 已測出的 null result**（見 B） |
| **76→77** | 重試排名加入 **silent articulation 扣分**：`SILENT_ARTICULATION_PENALTY_WEIGHT = 8.0`／`_CAP = 0.35`（185–186 行）、`_silent_articulation_excess()`（1881 行，讀 `result["silent_mouth_audit"]["rows"][*]["articulation_excess"]` 取最差值；**未受審的 take 回傳 `None` 而不是 0.0**，所以 speaker Shot 與舊 Job 排名完全不變）、在 `_candidate_target_likeness()` 扣分（1865–1869 行），並在重試預算耗盡事件補印每候選的 `silent_articulation_excess` ＋ `target_likeness_score`（~4012 行） | `smart_render_worker.py`；`director_cut_studio.py` `SMART_RENDER_POLICY_VERSION = 77`（777 行） | **實機行為已被 log 直接證明**（見 C） |

政策號兩處同步：`director_cut_studio.py` 777 行、`smart_render_worker.py` 169 行（`VERSION` 維持 `0.3.8-alpha.3`，Project Format 維持 29）。

**B. 為什麼 76 只能算「測過、沒用」——p75／p76 是同 seed 923010507 的乾淨 A/B（三條 pass seed 完全相同，只差措辭）**

| seg | 嘗試數 | p75 被選 take 的 `articulation_excess` | **p76** | silent 判定 |
|---|---|---|---|---|
| 0 | 3 | 0.0477 | **0.0591** | 兩邊都 `violated=False` |
| 1 | 1 / 2 | 0.0797 | **0.0489** | 兩邊都 `violated=False` |
| 2 | 3 | 0.0589 | **0.0675** | 兩邊都 `violated=True` |

去語音化沒有讓嘴安靜下來：兩個有重試的段落反而**更動**（+24%／+15%）。三段 `decision_basis` 全是 `pixel_motion`，`maximum_motion` 仍等於 V1 自身嘴動 ×1.6（0.1756／0.1819／0.1777）。同一輪也確認了三件硬事實，全部是一手讀取：`silent_mouth_freeze.applied: true`（mode on／tmix 7／head_crop）**只作用在 plate**（plate 嘴動 0.039–0.048），而**生成結果**嘴動 0.210–0.267，已經比 V1 原片（0.110–0.113）還大 ⇒ 是 H3 自己把嘴畫動，不是複製 plate；把合格判定改成 plate 相對（上限 0.0762／0.0707／0.0834）的話 `plate_relative_violated` **三段全 true**，只是 `plate_gate_mode=advisory` 所以不生效。

**C. p77 實機（seed 923010607，0.5 MP，3 段，全 `silent_listener`，`plate=True`，`roi=[[0.3,0.285,0.78012,1.0]]`）——seg2 是關鍵證據**

`preview_923010607_1793188535321641600.job.json` → `staged_model_driver.py run`：`worker-exit code 0` → `comfy-free ok:true` → `vram-release` → `report` → `wait-qwen-reload ready:true`。成品 `cache\generated_outputs\preview\923010607\master.mp4`（12.86s，6580KB）。

seg2 三發候選（driver log 逐字，77 的扣分式已經把排序翻過來）：

| 候選 | `target_reference_similarity` | `articulation_excess` | 舊排名（sim＋衣柜加成） | **77 的 `target_likeness_score`** |
|---|---|---|---|---|
| 1 | 0.5397 | **0.0611** | 0.7758（第 2） | **0.2871 ← 被選** |
| 2 | **0.6115（最像 P1）** | 0.0846（最張嘴） | **0.8844 ← 舊排名贏家** | 0.2073 |
| 3 | 0.5400 | 0.0817 | 0.7347 | 0.0812 |

舊排名用色彩直方圖當判決，而 P1 是**露齒笑**，所以「嘴張最大的那發最像參考圖」—— seg2 兩發的相似度只差 0.004 而嘴動差了 2×，75／76 兩次都把最張嘴的選了進來。77 之後：

| seg | 嘗試數 | p75 被選 artic | p76 被選 artic | **p77 被選 artic** | 備註 |
|---|---|---|---|---|---|
| 0 | 3 | 0.0477 | 0.0591 | **0.0349** | 77 同時也是最像 P1 那發 |
| 1 | **1** | 0.0797 | 0.0489 | 0.0855 | `attempts=1`：第一發就被 QC 接受，**從頭就沒有可選**，77 無從介入 |
| 2 | 3 | 0.0589 | 0.0675 | **0.0611** | 排名翻轉（上表） |

**誠實標註**：75／76 是同 seed 的乾淨 A/B；**77 換了 seed（923010607），不是純對照**。因此「被選 take 的嘴動比較低」不能全部歸給 77，但 seg2 的**排名翻轉本身**是 log 逐字證明的機制事實，與 seed 無關。若使用者更看重「像 P1」勝過「閉嘴」，把 8.0 降成 4.0 即可（4.0 下 seg2 舊贏家重新取勝）。

**D. 尚未動用的三個槓桿（已向用戶報告，尚未實作）**
- **A** 把 silent 合格判定改成 **plate 相對**（三段都會不過 ⇒ 逼出重試，再由 77 挑最靜；`H3_CHARACTER_SWAP_SILENT_PLATE_GATE=on` 即可試，代價是可能為一支「只是道具經過嘴巴」的好 take 白花一顆 fresh seed）。
- **B** 把 mouth freeze 也套在**生成結果**上（確定性、不碰 prompt、不花 GPU 重抽）。
- **C** 做一發**閉嘴版 P1**（需用戶供圖；P1 露齒笑會讓相似度天然獎勵張嘴，這是 77 只能減緩而不能根治的部分）。

**E. 測試與編譯（一手）**
- `testing\test_smart_render_worker`：**Ran 65 tests — OK (skipped=1)**。
- `test_storyboard_segment_mapping` ＋ `test_character_swap_engine`：**Ran 84 tests — OK**。
- `py_compile director_cut_studio.py smart_render_worker.py character_swap_engine.py`：**rc=0**。
- ⚠️ **全套 `unittest discover` 本輪未採集**：5 個 `design_ai_service.py` 子進程不退出把整個 discovery 掛住（既有毛病，非本輪回歸），探測過程已被終止 ⇒ 只交上述三個目標模組的綠燈，不宣稱全套通過。

**F. 已否決清單新增（別再浪費槍）**
- 再往 silent 條款尾端加句子或換句子（76 已經把「去掉語音字眼」這條路走到底，測出零增益；37g 之前已證负面條款飽和）。
- 給 plate 加 blur（嘴帶早已不在頭部硬模糊內，見 §37k）。
- 拿 target similarity 升降去判斷「某政策好不好」（P1 露齒笑 ⇒ 張嘴天然加分，與政策無關）。
- 把 geometric mouth swing 當判决（37g 密集取樣已證讀不出嘴）。
- 「plate 凍結了就等於不會對嘴」（p77 一手數據：plate 0.039–0.048 但結果 0.210–0.267）。
- 對生成結果做 lip-sync／嘴部後製以外的 V1 參照（本專案要的恰恰是**不要**跟 V1 的嘴）。

**G. 狀態界定**
- **源碼已修復**：policy 76 措辭、policy 77 排名扣分＋候選欄印證，全部已寫入並通過目標測試與編譯。
- **影片已實機驗證＝通過（用戶接受）**：p77 seed 923010607 已跑完，用戶回報「效果我接受」，本轮不再修改生成側行為。注意本輪验的是「**選到較靜的那發**」，seg1 之類 `attempts=1` 的 Shot 依然可能第一發就張嘴，那是 A／B 兩個槓桿的範圍。
- 回滚（純環境變數／政策號，不改邏輯）：`H3_CHARACTER_SWAP_SILENT_PLATE_GATE=off`、`H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE=off`；要回到 76 排名把權重設 0 即可（`SILENT_ARTICULATION_PENALTY_WEIGHT`）。
- 探針：`working\_r37p_scan.py <SEED>`（driver log 逐 attempt ＋ 候補表）、`working\_r37p_qc3.py`（p75／p76／p77 manifest 三方表）、`working\_r37p_find.py`（找含 `silent_mouth_audit` 的 manifest）。

### Round 37k：policy 74→75 —— 把 silent plate 的嘴帶**時域凍結**，同時讓 silent QC 改讀「模型真正看到的 plate」而不是會說話的 RAW V1（2026-10-28 14:12–15:10 修碼＋測試＋**真素材離線 A/B**，**源碼已修復＋離線 A/B 通過，影片未實機**）

**A. 這輪真正落地的三處產品碼改動（全部已寫入、已驗綠）**

| 檔案 | 改動 | 開關（預設值） |
|---|---|---|
| `character_swap_engine.py` | `MOUTH_BAND_REGISTRATIONS` / `mouth_band_registration()` / `mouth_region_bbox()` 成為 **plate 與 QC 共用的同一把尺**（同一註冊規則、同一 bbox），從源頭杜絕兩邊各算各的 | 常數，無環境開關 |
| `director_cut_studio.py` | `_silent_plate_mouth_freeze_settings()`（917 行）＋ plate 組裝時把嘴帶 `tmix` 鏈放在**所有 blur 之後的最後一段**（`_mouth_freeze_chains`，36509 行）＋ 把實際 plate 路徑寫進 `identity_audit["plate_video_path"]`（~37126 行）＋ recipe 檔名加入 `mouthfreeze=…｜frames=N` 標籤 | `H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE`（預設 **on**）、`H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE_FRAMES`（預設 **7**，clamp 2–60，**import 期解析**） |
| `smart_render_worker.py` | `_silent_plate_gate_settings()`（1376 行）＋ 嘴帶審計新增 `plate_measured`／`plate_motion`／`plate_relative_limit`／`plate_relative_violated`／`source_speech_conflict`／`verdict_scope`／`decision_basis`；判定順序 plate-on → geometry-on → pixel_motion | `H3_CHARACTER_SWAP_SILENT_PLATE_GATE`（預設 **advisory**）、`H3_CHARACTER_SWAP_SILENT_PLATE_MOTION_GAIN`（1.5）、`_MOTION_FLOOR`（0.012） |
| Smart Render Policy | **74→75**（`smart_render_worker.py` 129 行、`director_cut_studio.py` 741 行，兩處都附理由註解）：plate 提交物與 QC 基準同時改變 ⇒ p74 的 manifests 視為 stale | — |

**B. 為什麼非換尺不可（p74 一手證據，誠實引用）**
- `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923010407_*.manifest.json` 三段幾何完全相同：hard head blur 只到 `y 0.285`，而 QC 註冊的嘴帶是 `[0.425, 0.306, 0.575, 0.414]` —— **嘴帶根本落在衣襬 `boxblur=6:3` 裡，不在頭部硬模糊內**。p74 的 plate 因此「臉糊了、嘴沒動」。
- 同一 manifest 三段 `silent_mouth_audit` 的 `plate_video_path` 全是 **None**： silent 閘門那時的基準是 `identity_audit.source_video_path`，也就是**會說話的 RAW V1**（`source_motion` 0.109／0.113／0.110），而 Relay 拿到的 plate 安靜得多。基準與條件不是同一支影片，契約自然對不上。
- p74 三段 `result_motion` 0.184／0.270／0.237，`maximum_motion` 上限 0.1756／0.1819／0.1777 —— 只有 seg2 因 `result > upper_relative_limit` 才被判輸；seg0 靠眼睛帶控制区（0.1399）逃過，正是 §37d 已算清的「道具經過嘴巴」而非嘴。

**C. 真素材離線 A/B（`working\_r37k_offline_proof2.py` → **VERDICT OK**，無 GPU／無 ComfyUI／無 Qwen）**
plate 由產品碼 `_character_swap_identity_suppressed_source` 在 p74 的**同一批 relay 檔**上重建（只 patch 凍結常數），嘴帶用 QC 同一個 `mouth_band_registration`，取樣器與指標就是 QC 自己的 `_extract_identity_gray_frame` + `robust_temporal_frame_motion`（7 個比例點、80px）。策略字串必須等於 p74 的 `medium_silent_listener_identity_suppressed_wardrobe_blur_suppressed`，否則直接 FAIL。

| seg | raw V1 嘴帶 | plate freeze=off | **plate freeze=ON** | p74 生成 take 嘴帶 | take 眼睛帶 | 上限(off) | **上限(ON)** |
|---|---|---|---|---|---|---|---|
| 0 | 0.1215 | 0.0578 | **0.0358** | 0.1954 | 0.1701 | 0.0987 | **0.0656** |
| 1 | 0.1084 | 0.0726 | **0.0398** | 0.2799 | 0.1187 | 0.1209 | **0.0716** |
| 2 | 0.1055 | 0.0660 | **0.0369** | 0.2369 | 0.0569 | 0.1110 | **0.0673** |
| 平均 | 0.1118 | 0.0655 | **0.0375** | 0.2374 | 0.1152 | 0.1102 | **0.0682** |

- 凍結把**被審計的那條帶**降 1.75×（0.0655→0.0375），並讓三段全部掉到 silent 契約地板 0.055 以下；相對一支真的會動的 take（0.2374）安靜 6.3×。
- 探針同時驗證：兩臂產生**兩個不同的 plate 檔**、`silent_mouth_freeze` 審計只在 on 臂記錄 band（`applied=True／mode=on／tmix_frames=7／registration=head_crop`），排除「讀到上一臂」的假象。
- 注意量測口徑：**1.75× 不是失敗**。單元測試那塊 4 幀 6 Hz 方波之所以能衰到 0.129（7.1×），是因為 `tmix=7` 在 4.3s 實片只覆蓋約 0.23s，頭部搖擺、頭髮與道具都會在 0.15×0.11 的帶內存活。目標本來就不是歸零，而是**讓 plate 安靜到足以當基準**。

**D. QC 行為的實際變化（含代價）**
- p75 的 Preview Job（探針 `_r35e_preview_rebuild_check.py 923010507` → **VERDICT OK**）三段 `identity_audit` 都帶上 `plate_video_path`（silent-audio 變體，檔名 hash 已與 p74 不同 ⇒ 凍結確實进了 recipe）⇒ 從這一槍起 silent 判決**有 plate 可讀**。
- 若把閘門切成 `on`：按上面測得的 plate 基準，p74 那三段 take 會 **3/3 被判輸**（上限 0.0682），但其中 **1/3 通過眼睛帶控制区**，也就是仍會為一支「只是道具經過嘴巴」的好 take 白花一顆 fresh seed。這就是本輪維持 **advisory**（記錄不花 seed）的理由，也是下一槍要用真 take 給 plate 相對數值驗級的原因。

**E. 測試與編譯（本輪一手結果）**
- `testing.test_character_swap_closeup_gates` + `test_character_swap_background_extra`：**85 OK**
- `testing.test_character_swap_engine` + `test_silent_mouth_motion_gates` + `test_silent_mouth_transient_qc`：**91 OK**（新增 `SilentPlateRelativeGateTests` 6 測；改寫後的凍結 A/B 測式更名為 `test_the_freeze_is_the_only_thing_stopping_the_measured_band`，並用 `patch.object(studio_module, "CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE_MODE", mode)` 才有效 —— plate 建檔讀的是 **import 期常數**，`patch.dict(os.environ,…)` 無效）
- `testing.test_smart_render_worker` + `test_storyboard_segment_mapping`：**63 OK（1 skip）**＝基準
- `py_compile director_cut_studio.py smart_render_worker.py character_swap_engine.py`：**rc=0**；`test_director_timeline` 會掛起，依慣例跳過

**F. 順便挖出來的兩個 ffmpeg 坑（測試原本燒光 180s timeout 的真因）**
1. 合成純色來源的顏色必須寫滿 `0xRRGGBB`，`0xFA` 會被拒。
2. plate 的 mask 模式用 `-loop 1` + `-shortest`：**來源若沒有音軌就永不結束**。產品來源都帶音軌所以實機正常，但這是**潛在風險**，本輪只寫進測試註解，**未改產品碼**。另 `boxblur=18` 要求 crop 後的色度面 >36px，太小的 plate 會無聲退回 raw V1（既有行為）。

**G. 狀態與回滾**
- **源碼已修復**：嘴帶共用尺、plate 嘴帶時域凍結、QC plate 參照與誠實欄位、policy 75。
- **影片已實機驗證＝尚未**：p74 仍然是「silent listener 依然對嘴」的既有證據，本輪沒有任何新影片。
- 回滾：`H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE=off`（plate 回到 p74 形狀）＋ `H3_CHARACTER_SWAP_SILENT_PLATE_GATE=off`（QC 回到只讀源片）；兩者都是環境變數，不必改碼。
- 下一槍提議 **seed 923010507／policy 75**，一條 `staged_model_driver.py run`；**尚未開槍，需使用者批准**。

### Round 37j：prompt 側徹底打光 —— 本專案還有 **577 chars 餘裕**卻仍然對嘴，所以「沒生效」不是被預算丟条款；**再加 prompt 文字已無正當性**。唯一还没試過的非 prompt 槓桿是 **plate 嘴帶時域凍結**（2026-10-28 13:41–14:10 離線＋讀圖，**診斷＋設計完成，未改碼、未開槍**）

**A. 這個專案的 prompt 側沒有死角（一手）**
- `working\_r37j_manifest_probe.py`＋`_r37j_prompt_probe.py`（headless 重組 Preview Job，從 `workflow` 抓出**實際提交**的 prompt 逐句掃嘴）。後者的重組結果與 manifest 記錄**逐字一致** ⇒ policy 74 的五句正面改寫確實到了 ComfyUI，不是本地註釋。
- `prompt_budget = {'prompt_chars': 11743, 'char_budget': 12320, 'dropped_tail_clauses': [], 'over_budget': False}`（三段同值）⇒ 還有 **577 chars 空間**，與 shirt_9 的 `SHEET_CLOSEUP` pass 只剩 2 chars 完全不同 regime。
- prompt 裡已有 **23 句**嘴相關條款，「參考圖嘴形剝離」三句早在：`Picture 1 may itself be drawn mid-laugh with an open mouth: copy that Picture's identity, not its mouth.`／`Picture 1 supplies identity but never supplies an open-mouth pose, smile, visible teeth, tongue or speaking expression.`／`Even if Picture 1 is smiling or has an open mouth, reconstruct that same identity with relaxed closed lips for the whole Shot.`
- 未處理的小項：locator 行仍帶作者原文 `R1: Juggling orange balls while smiling at camera`，本身就是「笑」的正面授權。

**B. P1 參考圖肉眼確認＝大笑張嘴**：已寫出並看過 `_dsh_verify_9\round37\p74_frames\p1_reference.png`（252×370）與 `p1_face_zoom.png` —— 禿頭＋三根毛、濃眉、圓眼鏡、**嘴大張露齒露舌**、黑藍上衣＋黃格短褲。這是模型張嘴最可能的來源（圖 conditioned），與 37i 的量化一致。

**C. 已設計好、尚未落地的三件套（policy 74→75）**
1. 共享嘴帶定義：`MOUTH_BAND_REGISTRATIONS`＋`_mouth_band_registration` 從 worker 搬到 `character_swap_engine.py`（該檔只 import stdlib），worker 保留向後別名 —— Studio 要用同一個嘴帶才算得出同一塊肉。已驗證 box `[0.35,0.15,0.65,0.45]` → `head_crop` → `[0.425,0.306,0.575,0.414]`，與 manifest 逐字相同。
2. **plate 嘴帶時域凍結**（本輪主軸）：`_character_swap_identity_suppressed_source()` 內對已 blur 的頭帶之下的嘴帶做 ffmpeg `tmix=frames=K`（預設 K=7；語嘴 2–6Hz、頭部漂移 0.5–1.5Hz ⇒ 低通殺前者留後者）。只對 silent pass 生效，寫進 plate cache token，並把 `{applied, band, registration, tmix_frames}` 寫進 `identity_suppression_geometry`。
3. **QC 誠實化**：Studio 在 `identity_audit` 補 `plate_video_path`（目前只有 RAW 的 `source_video_path`，plate 名稱只出現在 `uploaded[1].file`）；worker 加測 plate 嘴帶 ⇒ `plate_motion`／`plate_relative_*`／`source_speech_conflict`／`verdict_scope`，預設 advisory（只記錄、不增加重抽）。
- 開槍前必做的離線證明：對 p74 的 RAW relay 剪段跑新 plate 建置，用同一 `robust_temporal_frame_motion` 算術量嘴帶 motion（應從 0.056–0.073 掉到 ≈0.01–0.02）。

**狀態界定**
- **源码已修復**：本輪**無**產品碼改動（仍是 37f 的 policy 74）。
- **視頻已實機驗證**：不適用（37j 沒開槍）；p74 仍是對嘴的既有證據。

### Round 37i：推翻 37h 的 QC 判讀 —— silent 閘門的基準讀的是**會說話的 RAW V1**，不是 H3 真正看到的 plate；順帶首次取证 P1 張嘴（2026-10-28 13:35–13:40 離線，**診斷完成，未改碼**）

**一手量化**（`working\_r37i_qc_source_probe.py` → `_dsh_verify_9\round37\r37i_qc_source.txt`，嘴帶 `[0.425,0.306,0.575,0.414]`，7 點取樣）

| seg | QC 記錄 source_motion | 重算 RAW relay | 重算 `00_source.mp4`（實際 plate） | 重算 generated |
|---|---|---|---|---|
| 0 | 0.109043 | 0.121526 | **0.057028** | 0.183781 |
| 1 | 0.113240 | 0.108445 | **0.073365** | 0.269586 |
| 2 | 0.110444 | 0.105513 | **0.056258** | 0.236693 |

**結論**
- `identity_audit.source_video_path` 指向 `.director_cache\source_remake_relay_video\v1_relay_a2ab54ce555f03ec7471_0.000-4.288.mp4`（`_source_remake_relay_source_clip()`，ffmpeg 只 `fps=24,setpts`）—— 那是**會說話的 RAW V1**，不是 H3 上傳的那塊 plate。cap=`max(0.055, source*1.5+0.012)` ⇒ 這道閘門只能回答「有沒有比會說話的源片更會動」，**天生回答不了「有沒有閉嘴」**。
- 生成結果的嘴帶動得比 plate **2–4 倍**、比 RAW V1 **1.6–2.4 倍** ⇒ 37h「基準只是 plate 被 blur 的殘餘漂移」的說法不成立（否決）；同時「生成結果只是忠實轉移源片的說話表演」也否決 —— 它比源片還會動。
- plate 名稱只在 manifest `uploaded[1].file` 見得到（`v1_relay_..._identity_suppressed_<token>_silent_<token>.mp4`），`identity_audit` 裡沒有 plate 路徑 ⇒ QC 無從量到真正的輸入。這是 37j 第 3 件套的由來。

**狀態界定**：源码未改；本輪產出的是判準的定義問題，不是修復。

### Round 37h：policy 74 第一槍（seed 923010407，3 段 ×3 次生成，2026-10-28 13:05–13:30 實機＋讀帧＋離線複核）—— 五句正面改寫**確實提交到了 ComfyUI**，三段真嘴讀帧**仍然全部張開（見牙齒與舌頭）**（**視頻已實機驗證＝未通過**）

**實機**
- 一條 `staged_model_driver.py run` 跑完：manifest `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923010407_1793163682376883900.manifest.json`，日誌 `_dsh_verify_9\round37\round37h_policy74_shot.log`。三段全部 `speaker=False`、`silent_audio_strategy=audio_stripped`、`reference_framing=illustrated_full_design`、`identity_sheet_single_figure_passthrough=True`、`target_media_id=P1`（單圖直通，無 identity sheet 干擾）。
- 真嘴讀帧：`p74_s{0,1,2}_true_mouth_gen.png` 與 `true_mouth_crops\montage_true_mouth.png` —— 三個 segment 的嘴都是開的，含牙齒／舌頭；同位置的 plate crop（`*_true_mouth_plate.png`）嘴是閉的。⇒ 37f 的五句正面改寫**沒有達成「閉嘴」**。
- identity：`target_reference_similarity` = 0.607109／0.555407／0.509169，均值 **0.5572**（p73 = 0.5595）⇒ 同分布，改寫既沒把身份換壞也沒有改善。
- wardrobe：`wardrobe_shift` = 0.1539／0.1823／0.1685，全部過門檻 0.12 ⇒ 本輪不是衣柜問題；但貓耳頭箍＋黑長假髮＋鑲金清裝袍的源角色污染仍在（`p74_vs_reference.png`）。
- policy 74 的 QC 新欄位確已落地：`gate="pixel_motion_with_cavity_geometry_recorded"`、`geometry_mode="advisory"`、`decision_basis="pixel_motion"`。seg2 判違規後重抽 3 次仍失敗（`failure_class="silent_mouth_excessive_articulation"`），退回 `00_save.mp4`。

**當輪判讀（已由 37i 推翻）**：当时把 `source_motion≈0.11` 當成 plate 被 blur 後的殘餘漂移，因此以為閘門公平；37i 證明那個基準根本是 RAW V1。

**狀態界定**
- **源码已驗證正確**：37f 的改寫文本、幂等、prompt 預算（79 項測試）＋ policy 74 欄位實機落地。
- **視頻已實機驗證＝未通過**：三段仍對嘴；identity 均值未改善；貓耳／假髮／清裝袍未解。

### Round 37g：密集取樣復跑（2026-10-28 12:55–13:05 離線，**無產品碼改動**）—— 37f 否決「口腔形狀 swing 當判決」不是取樣運氣：同一支探針、同一批 p73 素材復跑，輸出與 37f 逐字不差

- 探針 `working\_r37f_dense_probe.py` 復跑 → `_dsh_verify_9\round37\r37g_dense_rerun.txt`，以 `fc /B` 與 37f 的 `r37f_dense.txt` 比對：**逐字不差**（可確定性重現，非单次取樣）。
- 內容要點：生成側（p73 的 `00_save`／`01_save`，101–102 帧 @24fps、5 帧平滑）每一行 band 的 cavity 值都在 0.10–0.60，**最噪的非嘴行與真嘴行只差 ≤0.05**（例：seg0 `00_save` 真嘴行 0.615、非嘴峰 0.557/0.523）；同一算法在 plate 側只有 0.000–0.100，且 plate 的 dark-row 剖面有清晰的「臉下暗帶」結構。⇒ 算法對 plate 誠實、對 Relay 重畫過的頭不可讀，這條否決維持；`H3_CHARACTER_SWAP_MOUTH_GEOMETRY` 停在 `advisory` 是對的。
- 本輪存在的理由：37h 要拿 policy 74 實機開槍，判據的可靠性必須先能自證。

### Round 37f：policy 73→74 —— silent 的**负面条款已经饱和**，本轮改官方模板里那五句**正面**许可（`body performance` / 删 `every expression` / `the speech is off screen`）；同一轮把 37e 的嘴形 QC 从 `on` 退回 `advisory`，因为密集采样证明生成侧口腔形状读不出嘴（2026-10-28 12:25–12:56 离线＋修码＋测试，**源码已修复，实机未跑**）

**根因（一手，离线）**
- 负面侧已无牌可打：p71／p72／p73 三枪（seed 923010107／923010207／923010307，共 27 次生成）每段都带完整 SILENT LISTENER 合约＋medium 强化＋37c 改写后的嘴句＋plate silent clause，p73 的 `prompt_budget = 11731/12320、dropped_tail_clauses=[]、over_budget=false` ⇒ 句子没被预算丢掉，却仍然对嘴。剩下能动的只有官方模板的**正面**许可。
- 官方模板里仍在授权对嘴的五句：`whose performance comes from the person being replaced`、`transferring their complete visible performance`、`identity through every expression`、`Hair and clothing move naturally with the transferred performance`、`Retain the source clip's existing sound`。

**改法（`character_swap_engine.py`）**
- 新增 `AUTHOR_PROMPT_SILENT_PERFORMANCE_REWRITES`（五组 `anchor → replacement`＋各自 marker），`_author_prompt_with_silent_mouth()` 先套 37b 的嘴句替换、再逐条就地改写：**只追加词内改写、不新增段落**，marker 已在就跳过 ⇒ 重编译／重放 Job 都不会叠句；作者 prompt 被剪掉某句时原样返回，不抛错。只在 `silent_mouth=True` 生效，说话镜头保留原句。
- 五句改写：`whose body performance comes from…`（＋5）／`transferring their visible body performance`（−4）／`through every viewing angle`（删 `expression`，−15）／`with the transferred body motion`（0）／`…sound effects; the speech is off screen.`（＋26）⇒ 表成本净 **+12**。
- `retention_analysis` 的 `…as the character performs the source person's movements.` **故意不动**：`AUTHOR_PROMPT_WARDROBE_LOCK` 就插在这句之后，改它会静默丢掉衣柜锁。
- 长度纪律实测（探针 `working\_r37f_len_probe2.py`）：最重的 silent pass（`SHEET_CLOSEUP_SPEC`，S8/S9 型 sheet 近景）unbudgeted **12 956**，预算 **12 320** ⇒ 必须丢 636，而 guard 的 rank-1 条款只能买到 **638** ⇒ 改写前只剩 14 chars 余裕、改写后只剩 **2**。再多 3 个字的 silent 条款就会连 rank-3 `source_costume_leaves_plate`（S4 衣服复辟那句）一起丢。drop 概况实测不变：仍只 `['close_up_silent_mouth']`，`SOURCE COSTUME BELONGS TO THE ERASED ACTOR` 两句都在。

**QC 退回（`smart_render_worker.py`）**
- 37e 的口腔形状闸门默认 `on` 已用密集采样否掉（数据见 Round 37e 条），默认改回 `advisory`：形状数字继续写进 manifest，判决仍由 pixel-motion 出；`gate` 字串诚实化为三态 `mouth_cavity_geometry_with_pixel_motion_fallback` / `pixel_motion_with_cavity_geometry_recorded` / `pixel_motion`。同时修掉两处残留：空 env 与非法 env 仍会落回 `on`（应落 `advisory`）。
- 密集采样 9 格（3 个 policy × 3 段，`working\_r37f_dense_probe.py` ⇒ `_dsh_verify_9\round37\r37f_dense.txt`，24 fps＋5 帧平滑，探针与结论本轮 12:55 复跑复核 `_r37g_dense_rerun.txt`，`fc /B` 逐字不差）：生成侧真嘴行 swing 与**最吵的非嘴行**只差 1.26–1.80×（p71 1.73／2.53／1.26，p72 2.08／1.98／5.39，p73 1.41／1.53／1.80），margin 1.60 会把 9 段里**至少 3 段真在说话**的判成合格；而**静音源片**同一算法下 mouth 0.0462／0.0769／0.1000、noise 0.0000，全部越过 0.020 floor ⇒ 会把不说嘴的 plate 判成违规。两个方向都错，所以 `on` 不能用。

**Verification**
- `test_character_swap_engine` **79 OK**（新增 3 项：`test_silent_pass_carries_no_affirmative_performance_or_sound_claim`、`test_author_prompt_silent_performance_rewrites_are_idempotent`、`test_silent_performance_rewrites_stay_inside_the_measured_length_slack`；最后一项不再 pin 死数字，而是把改写表关掉重建同一条 pass 实测余裕再断言 `cost ≤ 余裕`）；`test_silent_mouth_motion_gates` 9 OK；`test_silent_mouth_transient_qc` **3 OK**（37e 遗留的 `test_persistent_lip_motion_still_fails_the_take` 因默认退回 advisory 自动恢复，未改 fixture）；`test_character_swap_closeup_gates`＋`test_character_swap_background_extra` 合计 171 OK（第一批）；`test_smart_render_worker`＋`test_storyboard_segment_mapping` **63 OK／1 skip**；`character_swap_engine.py`／`smart_render_worker.py`／`director_cut_studio.py` `py_compile` 通过。
- Smart Render Policy **73 → 74**（`director_cut_studio.py`、`smart_render_worker.py` 两处同步）：提交给 H3 的 prompt 文字变了 ⇒ policy-73 manifest 作废，Preview 会重算。
- 备份 `_backup\r37f_20261028_pre_silent_performance_rewrite\`（engine／worker／studio／CHANGELOG／HANDOFF／两个测试档）。VERSION 维持 `0.3.8-alpha.3`，Project Format 29，Policy 74，sheet engine 8。
- **状态界定**：源码已修复＝上述五句改写＋advisory 退回。**视频已实机验证＝未通过**：p71/p72/p73 三段仍对嘴，policy 74 **还没跑过一枪**，「不再对嘴」目前是假设。

### Round 37e：silent-mouth QC 换成「口腔开合形状」判据（`H3_CHARACTER_SWAP_MOUTH_GEOMETRY`，默认 `on`）——manifest 从此带得走形状证据，但生成侧形状本身被 boil 污染，37f 已退回 `advisory`（2026-10-28 12:10–12:30 离线＋修码，**源码已修复，当轮未登记**）

**做了什么**
- `smart_render_worker.py` 新增 `_cavity_opening_profile()`：把已登记的嘴带按行求「暗腔开启度」的时间序列，取 swing（最大−最小）而非相邻帧差；同一算法跑在额头控制带与源 plate 上，`violated = mouth_swing > max(control_swing × margin, floor)`，margin 1.60／floor 0.020。动机是 §37d 的定案：两条阈值都不含嘴唇，判的其实是额头 vs 头顶。
- `_silent_mouth_geometry_settings()` 暴露三个 process env：`H3_CHARACTER_SWAP_MOUTH_GEOMETRY=on|advisory|off`、`…_MARGIN`、`…_FLOOR`（只读进程 env，不读 `design_ai.env`）。
- manifest 新增：audit 层 `gate`／`geometry_mode`／`geometry_margin`／`geometry_floor`，row 层 `mouth_opening_median|swing`、`control_opening_median|swing`、`source_mouth_opening_median|swing`、`geometry_available`、`geometry_swing_limit`、`geometry_violated`、`decision_basis`、`articulation_excess`。复用 37b 已抽的帧，**不增加 ffmpeg 抽取**，只多 numpy 算术。
- 当时无专属测试，直接改默认 ⇒ 打破 `testing/test_silent_mouth_transient_qc.py::test_persistent_lip_motion_still_fails_the_take`（37e 基线 2 OK／1 FAIL），该失败由 37f 的 advisory 退回消掉。
- 事后核对：p73 manifest 的 `silent_mouth_audit` 只有 `checked/passed/rows`（`working\_r37f_regscan_probe2.py` 口径），**没有 geometry 栏位** ⇒ 那些栏位要到 policy 74 的第一枪才会出现在 manifest 里，不能用 p71–p73 的 manifest 验证 37e。

**已否决（37f 一手数据，见 Round 37f 条）**：Relay 重画过头之后，生成侧每一行带（含头发、帽带）的 cavity swing 都在 0.10–0.60，最吵的非嘴行与真嘴行常差不到 0.05 ⇒ `on` 等于让所有会动的 take 都过关，静默关掉审计。形状判据在 plate 侧诚实（0.000–0.100），在 result 侧不可分。**保留**：数字继续入 manifest 供离线 A/B，`on` 留给一次受控对照。

**Verification**：当轮只跑 `py_compile` 与既有测试（遗留 1 FAIL）；37f 已补回全绿。**源码已修复（判据本身），实机增益＝零**（p73 那三段的判决本来就是 pixel-motion 出的）。

### Round 37d：policy 73 实机首枪（seed 923010307，9 次生成）—— 真嘴读帧判定**闭嘴仍未达成**；并把 silent QC 的 `violated` 为何在 seg0 判 False 定量算清（2026-10-28 11:05–11:55 实机＋读帧＋离线复核，**视频已实机验证＝未通过**）

**跑法与产物（GPU，按三条硬约束走 driver）**
- job 重建：`working\_r35e_preview_rebuild_check.py 923010307` ⇒ `preview_923010307_1793157449016312100.job.json`，`VERDICT OK`；knobs `passthrough=True / wardrobe_audit=on / hair_band=off / policy=73`；3 段、audit ROI `[[0.3, 0.285, 0.78012, 1.0]]`、ref＝P1 原图直通（`image_137_4bd41c9e363a8278_nobg.png`）、budget 11731/12320、`dropped_tail_clauses=[]`。日志 `_dsh_verify_9\round37\rebuild_923010307.log`。
- 这一枪确实是 policy 73（`working\_r37c_prompt_check.py` 口径数过）：新串 `copy that Picture`／`relaxed closed mouth`／`blinking, brow and eye expression only` 各 **6 次**，旧串 `one static expression`／`facial expressions, and visible mouth movements` 各 **0 次**。
- driver：`Start-Process … staged_model_driver.py run <job>` ⇒ `worker-exit 0` → `comfy-free ok` → `vram-release 3.14→2.87 GB` → `wait-qwen-reload ready=true`（Qwen 已回、ComfyUI 已空）。master `7,981,117 B`。日志 `_dsh_verify_9\round37\round37c_policy73_first_shot.log`，manifest `project\render_jobs\preview_923010307_1793157449016312100.manifest.json`。

**实机数字（一手，探针 `working\_r37c_manifest_summary.py`）**

| 段 | 窗口 | attempts/选中 | 重抽 class | target sim | 衣柜 pass / binding | upper／lower shift | upper_face／相对线 | 嘴 violated |
|---|---|---|---|---|---|---|---|---|
| 0 | 0–4.288 | 3 / 2 | —（accept） | 0.571400 | **False** / lower | 0.127625 / **0.101278** | 0.198382 < 0.267978 | **False**（0.267488 > 0.106289） |
| 1 | 4.288–8.576 | 3 / 1 | silent_mouth | 0.525428 | True / lower | 0.213489 / 0.181294 | 0.178909 < 0.243636 | True（0.270166 > 0.086737） |
| 2 | 8.576–12.864 | 3 / 2 | silent_mouth | 0.581529 | True / upper | 0.157855 / 0.196693 | 0.135269 < 0.189087 | True（0.254121 > 0.129921） |

三段 `complete_actor_erasure`／`whole_character_integration`／`source_plate_continuity` 全 passed=True ⇒ **总生成 9 次**（与 p72 同量）。MEAN target sim **0.55945**，落在同-policy 的 seed 变异区间（p71 0.5513／p72 0.5685）之内 ⇒ 不得据 sim 宣称增益。seg0 `wardrobe pass=False binding=lower`（lower_shift 0.101278 < floor 0.12）＝ policy 72 的闸门又抓到一次**「只换上身的反面」**，但预算耗尽后仍以 target-best accept。

**读帧判定（唯一真判据，数字在此案不可信）**
- 产物：16 格网格 `_dsh_verify_9\round37\p73_frames\montage_policy73.png`（生成器 `working\_r37d_extract.py`）；真嘴 crops `…\p73_frames\true_mouth_crops\montage_true_mouth_p73.png`（`working\_r37d_true_mouth.py`，带与 p72 完全同一路：seg0 0.315–0.385／seg1 0.340–0.410／seg2 0.355–0.425）。
- **三段都还在对嘴**：seg0 t=0.50／2.70／3.20／3.70 是露齿露舌的大张嘴、t=1.50／2.10 是抿嘴 ⇒ 明显一张一合；seg1 七个采样点有 **5 个张嘴**；seg2 t=0.50／1.00 大张嘴。与 p72 的 `…\true_mouth_crops\montage_true_mouth.png` 并排看，两边都是「会说话」，差异属 seed 变异 ⇒ **policy 73 不得宣称已让角色闭嘴**。
- 顺带读头饰／衣柜：猫耳 **16/16** 仍在；镶金头带＋长假发 **9/16**（seg0 4/5、seg1 5/6、**seg2 0/5**）。seg2 那几格反而最像 P1（秃顶＋黑 mesh 坎肩＋蓝短裤＋黄格纹裤），但 policy 73 只动嘴部措辞 ⇒ 这是 **seed 变异**，不能记在改动名下。

**把 `violated` 的判定彻底算清（回答 §Round 37c 留的矛盾）**
- 规则（`smart_render_worker.py:2105-2125`）：`violated = (result_motion > maximum_motion) AND (result_motion > upper_relative_limit)`，其中 `maximum_motion = max(0.055, source_motion*1.5+0.012)`（阈值，非测量）、`upper_relative_limit = upper_face_motion*1.25+0.02`。⇒ seg0 的 0.267488 虽远超 0.106289，却比自己的相对线 0.267978 **只差 0.00049（0.18%）**，AND 失败 ⇒ `violated=False`；seg1／seg2 越线 ⇒ True。**seg0「通过」是掷硬币，不是它真的闭嘴。**
- 两条线为什么都不成立（本轮离线复核 `working\_r37d_roi_audit2.py`，用 manifest 写死的审计带 `[0.434, 0.225, 0.566, 0.291]`＝**额头／眼镜／头带**，与由同一硬编码 box `[0.35,0.15,0.65,0.45]` 导出的对照带 y 0.156–0.222＝**头顶／猫耳**，对 p72／p73 逐段算 median 相邻帧差）：

| seed／段 | 审计带(额头) | 对照带(头顶) | 相对线 | **真嘴带**实测 | 真嘴是否越自己的线 |
|---|---|---|---|---|---|
| p72 seg0 | 0.2837 | 0.2806 | 0.3708 | 0.2553 | under |
| p72 seg1 | 0.2943 | 0.2075 | 0.2794 | 0.2236 | under |
| p72 seg2 | 0.2516 | 0.1389 | 0.1936 | 0.2709 | **ABOVE** |
| p73 seg0 | 0.2629 | 0.1856 | 0.2520 | 0.2614 | **ABOVE** |
| p73 seg1 | 0.2585 | 0.2069 | 0.2786 | 0.3152 | **ABOVE** |
| p73 seg2 | 0.2699 | 0.1294 | 0.1818 | 0.2235 | **ABOVE** |

- ⇒ 审计带与对照带**都不含嘴唇**，而「额头带」的沸腾还常常**高于**真嘴带 ⇒ 这条规则在本专案实际比的是「额头 vs 头顶」，与口型有没有动近乎无关。§37b 根因①因此升级：不只是「带压错位置」，而是**两条阈值都建立在非嘴部沸腾上**，所以 `violated=True/False` 都不能当闭嘴判据（本轮 p73 就是「violated 的两段里 seg2 前半有张嘴、没 violated 的 seg0 一样在大笑」）。

**Verification**：本轮无源码改动（纯实机＋读帧＋离线复核），故无需跑测试；`test_director_timeline` 238 项于 10:21:36 起跑，至 11:55 仍未见 `Ran N tests`（进度停在 200/238 ⇒ 173 ok／5 error／6 failure／16 skip，CPU 仍在递增，卡在会 spawn 服务的单项）⇒ 仍**不作** policy 73 的回归判据。VERSION 维持 `0.3.8-alpha.3`，Project Format 29，Policy 73，sheet engine 8。

**状态界定**
- **源码已修复**：policy 73 措辞（§37c，测试证明文本正确）。
- **视频已实机验证＝未通过**：seed 923010307 三段仍对嘴；主缺陷仍是 V1 的猫耳假发＋镶金头带与上身衣柜（seg2 是三轮里最接近 P1 的一格，但属 seed 变异，不能宣称改善）。
- 下一枪候选（每枪都要新的「批准」）：① silent QC 的 **ROI 配准／boil-relative 审计**（先离线合成 fixtures：articulating 必 fail、transient 必 pass，再单独一枪）；② 头饰／衣柜的**非 prompt 抹除机制**。**已否决**：往头发条款堆句子（§36）、`blur`（§32）与 `blur_desat`（§33）去色抑制。

### Round 37c：policy 72→73 —— silent 條款不再「請模型複製 P1 張开的嘴」，作者 prompt 也不再要 facial expressions（2026-10-28 10:10–10:30 修碼＋測試，**源码已修复，实机未跑**）

**为什么要改（Round 37b 的两条一手证据，详见 §Round 37b）**：① `close_up_silent_mouth` / `medium_shot_silent_mouth` 两条加固条款的末句写的是「Picture 1's own open smiling mouth is **one static expression to copy**…」——这是叫模型去复制一张**张开的嘴**，和权威 SILENT LISTENER 契约（`character_swap_engine.py:1781-1794`：「no open-mouth smile, laugh or jaw drop」「Picture 1 supplies identity but never supplies an open-mouth pose, smile, visible teeth, tongue or speaking expression」）直接对打；② silent 改写（`AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT`）只把「visible mouth movements」换掉，**保留了「facial expressions」**，而这块 plate 的表演本身就是一阵大笑 ⇒ 「match facial expressions」照样要求张嘴。真嘴 crops（`_dsh_verify_9\round37\true_mouth_crops\montage_true_mouth.png`）证实嘴是真的在一张一合，不是量测假象。

**改了什么（三处，全是 CPU）**
1. `character_swap_engine.py:546-549`：`AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT` 改成 `blinking, brow and eye expression only, and a relaxed closed mouth with the jaw still.`（把可匹配的表演限制在**上半脸**）。组串后的实文已打印复核：`…head turns, gaze, blinking, brow and eye expression only, and a relaxed closed mouth with the jaw still.`
2. `character_swap_engine.py:555-567`：新增共用常量 `SILENT_MOUTH_REFERENCE_PORTRAIT_CLAUSE`（「Picture 1 may itself be drawn mid-laugh with an open mouth: copy that Picture's identity, not its mouth. Draw the same face with the lips gently together in every frame, and never let the lips open or change shape from frame to frame.」），两条 scale 条款改为拼接该常量 ⇒ **两条永远不会再各写各的**。旧句「one static expression to copy」在樹内只剩註解。
3. `smart_render_worker.py:115` / `director_cut_studio.py:727`：`SMART_RENDER_POLICY_VERSION` **72 → 73**（提交的 prompt 变了 ⇒ policy-72 manifest 过期）。逐 byte 比对备份：两檔各只有 **1 個 byte** 变化，無 encoding/BOM 走樣。

**测试跟着改**：`testing\test_character_swap_engine.py:760-770` 改断新串并新增「旧串不得出现」；`testing\test_silent_mouth_motion_gates.py:115-128` 改名 `test_both_clauses_forbid_copying_the_reference_open_mouth`，断言 `copy that Picture's identity, not its mouth` 存在且旧句不存在。policy 常数是符号引用，升版自动跟随。

**Verification（本轮第一手）**
- `test_character_swap_engine` + `test_silent_mouth_motion_gates` + `test_silent_mouth_transient_qc` ⇒ **88 OK**（4.8 s）
- `test_smart_render_worker` ⇒ **59 OK（1 skip）**（23.0 s）
- `py_compile`：engine／worker／studio + 两个测试档 ⇒ exit=0
- `test_director_timeline`（238 项，`-m unittest testing.test_director_timeline` ＋ `PYTHONPATH` 含 `testing\`）：10:21:36 启动，10:40 仍在跑（中途快照 **200/238 ⇒ 173 ok／5 error／6 failure／16 skip**；卡住的那项会拉起 `audio_separator_service.py`，单项就要数分钟）。**这条不能作为 policy 73 的回归判据**：本机对这个模块**没有近期 green 基线**——日常全量基线一直是 `run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline`（`Ran 734/739/744/750/752 … OK (skipped=10)`），跳过理由见 HANDOFF §「慢模块」条目（每项 spawn `design_ai_service.py`，单模块 2 小时以上）；本轮改用 `-m unittest` 直跑，正是 HANDOFF 记过会产生 invocation-artifact error 的跑法。跑完后按**失败测试点名**逐条判定是否与 prompt 措辞／policy 版本相关，再回来补这条。日志 `_dsh_verify_9\round37\policy73_timeline_only.err`，进度探针 `working\_r37c_progress.py`。
- 备份：`_backup\r37b_20261028_pre_policy73\`（三个源檔 + 两个测试档）。VERSION 维持 `0.3.8-alpha.3`，Project Format 29，sheet engine 8。

**状态界定**：**源码已修复**（prompt 文本层，测试证明文本正确）；**「卡通角色闭嘴」这件事仍未实机验证**——下一枪 seed 923010307 之前不得宣称已修好。已设计但**没实现**的另一半：QC 嘴部 ROI 的配准修正（见 §Round 37b 根因①），它需要单独一枪与自己的合成 fixtures 验证。

### Round 37b：silent-mouth QC 的 ROI 根本没对在路上＋P1 大笑让模型真的对嘴 —— 两个独立根因定案（2026-10-28 09:30–10:05 離線＋讀幀，**诊断完成，未改码**）

**根因①｜QC 量的是「 redraw 沸腾＋头晃动」，不是口型**。silent 审计用的 actor box 是硬编码默认 `[0.35, 0.15, 0.65, 0.45]`（`identity_audit.source_bboxes_normalized`），**不是检测到的人脸**；`_mouth_region_bbox()`（`smart_render_worker.py:1234`）在里面再切出 `[0.434, 0.225, 0.566, 0.291]`，对照组 `[0.4657, 0.1586, 0.5343, 0.1877]`。带网格的标注帧（`_dsh_verify_9\round37\roi_check\f01_t001.00_roi.png`／`f05_t004.35_roi.png`／`f11_t008.70_roi.png`，生成器 `working\_r37b_roi_annot.py`）显示：「嘴带」压在**额头／眼睛／眼镜／头带**上，「对照带」压在**猫耳＋背景**上，而真嘴在 y≈0.33–0.40（seg0 0.315–0.385、seg1 0.340–0.410、seg2 0.355–0.425）。整条 box 高度的运动剖面（`working\_r37b_profile.py` → `_dsh_verify_9\round37\round37b_motion_profile.json`）：result 侧每条带都是 **0.15–0.33 一律平坦**（没有嘴部峰值），plate 侧 0.01–0.09 ⇒ 绝对 floor 0.055 在这种画风下**永远达不到**，因为量到的根本不是口型。另注：`maximum_motion` 是**阈值** `max(0.055, source_motion*1.5+0.012)`（`smart_render_worker.py:2105`），从来不是测量值。

**根因②｜嘴真的在动，因为 prompt 让模型复制 P1 张嘴**。P1 参考图（`.director_cache\image_137_4bd41c9e363a8278_nobg.png`）是一个**张嘴大笑（露齿露舌）**的卡通秃顶男；三条真嘴 crops 显示 seg0 大笑与闭嘴交替、seg1 从抿嘴变到大张嘴、seg2 也有张嘴帧 ⇒ 用户的「对嘴」抱怨是真的。两处自相矛盾的原文位置见 §Round 37c。

**顺带查实**：喂给 H3 的 silent plate 整个头部是**糊掉的**（`.director_cache\character_swap_silent_audio\v1_relay_6a51a424164732e57f91_0.000-4.287_..._silent_3dcc95030363c88b6c8b.mp4`， crops 见 `_dsh_verify_9\round37\plate_silent_crops\montage_silent_plate_head.png`）⇒ plate 根本没出口型线索，模型画出来的嘴只能来自 prompt／P1。

**探针（本轮新增，可复用）**：`working\_r37b_roi_annot.py`、`_r37b_profile.py`、`_r37b_true_mouth.py`、`_r37b_plate_crops.py`、`_r37b_prompt_mouth.py`。

### Round 37：policy 71→72 —— 衣柜闸门改成「上半身／下半身各自要动」，判定与重抽都跟最差半边；首枪实机（seed 923010207）证明**闸门抓得住、但全身替换仍没达成**（2026-10-28 09:18–09:30 修码＋实机）

**为什么**：policy 71 那枪（seed 923010107）三段衣柜位移 **0.121004／0.154807／0.123736** 全过 floor 0.12，读帧却是「腿已是 P1 黄格纹腿套、上身仍是 V1 粉袖＋金边黑背心」⇒ **整带中位数分不出「换装」与「只换裤」**，这正是导演一路在批的「只有头被换」。

**改了什么（`smart_render_worker.py`，+4.7 KB）**：新增 `_wardrobe_region_boxes()`——把被审计的服装矩形在中线切成 `upper`／`lower` 两半（仅当高度 ≥0.36 且每半 ≥0.18，否则保持 `whole`，避免细矩形被切出背景当衣服）；每半分别跑 `target_reference_frame_similarity` 取中位数，产出 `regions[]`；**binding 取位移最小的半边**，判定、manifest 顶层 `wardrobe_shift`、重抽排序全部跟最差半边，并写 `binding_region` + `region_policy="each_half_must_move"`；失败原因与重抽 prompt 会点名「the <upper|lower> half of the body region」。`director_cut_studio.py` 只动 policy 註解与常数。

**实机（seed 923010207，0.5 MP，3 段）**：manifest `preview_923010207_1793150597426430600.manifest.json`；日志 `_dsh_verify_9\round37\round37_policy72_first_shot.log`；抽帧 `_dsh_verify_9\round37\p72_frames\`。

| 段 | 窗口 | 尝试数 | failure_class | target sim | 衣柜位移(binding) | ward pass | binding | 嘴 violated |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.0–4.288 | 3 | — | 0.612033 | **0.079174**（upper 0.145896／lower 0.079174） | **False** | **lower** | False |
| 1 | 4.288–8.576 | 3 | silent_mouth_excessive_articulation | 0.561566 | 0.162069（upper 0.16968／lower 0.162069） | True | passed | **True**（0.301936 > 0.280528） |
| 2 | 8.576–12.864 | 3 | silent_mouth_excessive_articulation | 0.531974 | 0.183196（upper 0.188221／lower 0.183196） | True | passed | **True**（0.236705 > 0.183148） |

- **闸门确实抓到了用户的抱怨**：seg0 上半身 0.145896 vs 下半身 0.079174 ⇒ 绑在 `lower` 并判 fail。三次候选（0.088685／0.055641／0.079174）全数低于 floor，预算耗尽「keeping target-best take」。
- **相似度没有可宣称的提升**：MEAN **0.5685**（p72）vs **0.5513**（p71，0.617651／0.439179／0.597070）——落在同 policy 的 seed 变异内（历史 spread ≈0.067），**不得宣称 policy 72 带来增益**；代价是多烧 2 次生成（9 次 vs 7 次）。
- **读帧定案（16 格，`montage_policy72.png`）**：猫耳＋镶金头带几乎每格都在；上身仍是 V1 的粉袖＋金边背心（部分格出现 P1 蓝袖＋红蓝裙）；头/脸 OK ⇒ **「整个角色替换」仍未达成**。

**状态界定**：`policy 72 = 源码已修复＋实机验证闸门有效`（不误杀 seg1/seg2，且确实拦下 seg0 的只换腿）；**视频实机结果仍不合格**——头饰未抹除、上身衣柜未换、silent 对嘴（seg1/seg2）。

### Round 36：policy 70→71 —— 头发条款补上「正面事实」（bald crown／headwear only where Picture 1 draws it）；首枪实机（seed 923010107）**猫耳＋头带仍在 15/16 格** ⇒ 只加句子这条路已否（2026-10-28 08:48–09:15 修码＋实机）

**改了什么**：`character_swap_engine.py:1395-1412` 的 `source_hair_ownership_clause` 过去只宣布「谁拥有这块区域」（policy 68 措辞：假发「leaves the frame」、Picture 1「decides that region」），没有可画的事实；policy 71 补上正面事实——**该区域就是 P1 显示的头顶：P1 秃顶或只有几根发丝处即为裸头皮，不得残留假发体积、兽耳轮廓、头带、发绳或接发；头饰只在 P1 自己画了才出现**。只在 suppressed plate 上发言。policy 理由见 `smart_render_worker.py:103-108`、`director_cut_studio.py:715-720`。

**实机（seed 923010107，0.5 MP，3 段）**：manifest `preview_923010107_1793148508260025000.manifest.json`；日志 `_dsh_verify_9\round36\round36_policy71_first_shot.log`；抽帧 `_dsh_verify_9\round36\p71_frames\montage_policy71.png`。尝试数 2／2／3＝**7 次生成**；target sim 0.617651／0.439179／0.597070，MEAN **0.5513**；衣柜中位数三段全过（0.121004／0.154807／0.123736）；seg2 `silent_mouth_excessive_articulation`（result 0.283551 > limit）。
- **头发结论（本轮读帧）**：15/16 格仍有**猫耳**，row1/row2 仍有**镶金头带**，只有 row4 的 2–3 格出现裸头顶（仍带兽耳）；另外新出现**发色漂移成桃红／ magenta**（row3–row4）。⇒ 「只往 prompt 加正面事实」这条路**已试过、已否**，别再往同一方向加句子。
- **顺带定位 policy 72 的动机**：三段衣柜中位数虽 pass，读帧却是腿换上身没换 ⇒ 见 Round 37。

**状态界定**：**源码已修复**（policy 71 条款已在树内并进入提交 prompt）、**实机验证＝失败**（头饰未抹除）；同 shot 的衣柜「只换一半」缺陷由 policy 72 接手。VERSION 维持 `0.3.8-alpha.3`。

### Round 35e：policy 70 首枪实机跑完（0.5 MP、seed 923009999、三段）——sheet 渗出已消除、衣柜闸门既不误杀也确实会重抽；新暴露的主缺陷是 V1 的猫耳假发＋镶金头带仍在（2026-10-28 07:54–08:13 实机，**视频已实机验证**）

**跑法**（用户「批准」后上卡）：`staged_model_driver.py run "...render_jobs\preview_923009999_1793143069391241000.job.json"`。driver 逐段留痕：`unload-qwen verified_clean=true`（VRAM 25.69 → 2.77 GB）→ `wait-comfy ready node_classes=1600` → `worker-exit code=0` → `comfy-free ok` → Qwen 由 tray 载回。日志 `_dsh_verify_9\round35\round35d_policy70_first_shot.out.log`、`logs\staged_model_driver\preview_923009999_..._20261028_075444.log`。产物 `cache\generated_outputs\preview\923009999\master.mp4`（7,640,843 B、576×864、12.864 s）、manifest `render_jobs\preview_923009999_1793143069391241000.manifest.json`（54,836 B）。跑前备份在 `_backup\r35d_20261028_pre_policy70\`。⚠ **`.job.json` 跑完即被消耗**，只剩 manifest 与同 seed 的另一份 scratch job `preview_923009999_1793142990323537600.job.json`；要再跑得重新编译 job。抽帧档 `_dsh_verify_9\round35\p70_frames\`（16 格 + 4 张段边界 full + `montage_policy70.png`，row-major = t 0.2/1.0/2.0/3.0 | 4.0/4.35/4.70/5.50 | 6.5/7.5/8.45/8.70 | 9.5/10.5/11.5/12.6）。

**§34/§35 预告的三判据，逐条给结论**

| 判据 | 结果 | 一手证据 |
|---|---|---|
| ① sheet 边框／无头面板渗出 | **已消除 ⇒ Round 35 根因① 修实验证通过** | 16 格无白垫板、无边框；三段 `uploaded` 参考全是 **P1 原图** `image_137_4bd41c9e363a8278_nobg.png`，不是 sheet；`identity_sheet_single_figure_passthrough=true` 出现在真 render 的 pass 行 |
| ② 衣柜闸门会不会误杀 | **没有误杀，也不浪费重抽** | 三段 shift **0.160258／0.129918／0.159559** 全 ≥ floor 0.12、`passed=true`、reason「body region moved towards Picture 1's wardrobe」；seg2 **第一次尝试就 accept**（attempts_used=1） |
| ③ 年龄漂移（head share 0.5259→0.2144 的代价） | **局部复现一处** | t≈4.0 s（seg0 尾）灰白头发＋明显显老；其余取样帧未见 |

**闸门与选择逻辑在真卡上的行为（这是 §35b／Round 35c 只能离线推的东西）**：seg0 attempt 1 被衣柜闸门拒掉——shift **0.058691 < 0.12**、reason「replacement is only a head/face layer; the V1 wardrobe still fills the body region」、`action=retry_fresh_seed` ⇒ **闸门确实在拦「只换头」**。三次候选 `identity_candidate_scores`：#1 target 0.582741／shift 0.058691（被衣柜拒）、#2 target 0.503245／shift 0.160258、#3 target 0.394576／shift 0.082143 ⇒ 预算耗尽时选的是 **target 相似度最高的 #2**（`selected_identity_attempt=2`，log 明写「keeping target-best take 2」），不是盲取最后一条。

**主缺陷（新暴露，读帧 13/16 帧命中）**：V1 的**猫耳假发＋镶金头带仍在**，P1 是秃顶＋几根发丝，画面却是长棕发＋兽耳＋头带 ⇒ 身份相似度卡在 **0.503245／0.520336／0.531581**，MEAN **0.5184**。对照 policy 69 三个 seed 的 MEAN 0.5521／0.5753／0.6187（均值 0.582）：低约 0.06，但同 policy 的 seed 方差本身就有 0.067，**单 seed 不能判定 policy 70 造成回归**，只能说相似度天花板由头饰决定。prompt 里 `COMPLETE SOURCE-ACTOR ERASURE` 已点名「wig、hair extensions、hairpiece、**animal ears**、headgear 属被抹除身份」，实测仍拦不住。

**衣柜只换到一半（重要，别让「gate passed」骗人）**：读帧确认腿部已是 P1（黄格纹腿套＋黑黄球鞋＋蓝短裤），**上身仍是 V1 的粉袖＋金边黑背心**。衣柜 audit 的 ROI 是带 `[0.3, 0.285, 0.78012, 1.0]` 的 3 点均值，腿部变化就足以越过 floor 0.12 ⇒ **`wardrobe_audit.passed=true` 不等于整身换装**。

**silent listener 仍未结**：seg0／seg1 `failure_class=silent_mouth_excessive_articulation`，三次 fresh seed 压不住（`result_motion_mean` 0.274679／0.248828 vs source 0.062185／0.070963；`maximum_motion` 0.106289／0.086737 > `maximum_silent_mouth_motion` 0.055，`violated=true`）；seg2 通过（mean 0.217998 vs source 0.120635，max 0.129921 `violated=false`）。卡通媒介保留 OK：`live_action_adaptation=false`，16 格无真人化。

**状态界定**
- **源码已修复＋实机验证通过**：Identity Sheet 单图直通（判据①）、衣柜位移闸门 floor 0.12（判据②＋真卡上的重抽与 target-best 选择）、Round 35d 的 arity hotfix（这次一路跑到 GPU，`identity_audit.body_bboxes_normalized=[[0.3,0.285,0.78012,1.0]]` 是它第一次在真 render 里出现）、卡通媒介保留。
- **实机验证仍失败**：V1 头饰（假发／猫耳／头带）没被抹除 ⇒ 身份相似度天花板；silent listener 对嘴（seg0／seg1 三次都失败）。
- **本轮没有新写源码**，只有本轮的证据与文档；GPU 跑完已 `/free`（`comfy-free ok`），Qwen 已由 tray 载回。

**下一枪（必须先取得用户批准）**：单一变量＝把 P1 的发型写成**具体正向事实**（bald pate / no animal ears / no headband），挂在既有 hair 条款而不是新增 clause 家族；prompt 预算只剩 `12320-11324 = 996` 字元，`dropped_tail_clauses=[]`。头发之外另开一枪打 silent mouth。已否决、别再重跑：加大抑制面积／去色（§32 blur、§33 blur_desat）。
### Round 35d：hotfix——`_character_swap_body_audit_box()` 的 `list.append()` arity 错让**每一次带抑制几何的 Character Swap Preview 在碰 ComfyUI 之前就崩**（2026-10-28 07:00–07:20 修码＋离线复跑，**源码已修复，实机未跑**）

**症状**：用户在 Studio 按 Preview（0.5 MP）弹出 Queue error。traceback 末三段：`_start_generation` → `_build_smart_render_job` → `_compiled_character_swap_window_job` → `_character_swap_body_audit_box`，错误 `TypeError: list.append() takes exactly one argument (2 given)`。

**根因**：Round 35 新增 helper 时写成 `candidates.append((area), [box])`——把一对 `(面积, 框)` 当两个实参塞给 `append`。衣柜 audit 默认 `on`，任何有 wardrobe bands 的 Shot 一进 Job 编译就抛异常 ⇒ **policy 70 的 GUI 路径整条不可用**，不是偶发、不是项目资料问题。

**修法**（`director_cut_studio.py:35105-35127`）：先算出 `band_box`，再 `candidates.append(((right - left) * (bottom - top), band_box))`，并留一行注释说明 `append` 只收一个实参。逻辑不变（取面积最大的衣柜带）。

**防再犯**：`testing\test_character_swap_closeup_gates.py` 新增 `WardrobeAuditBoxTests`（4 项，geometry 直接抄 black-shirt 已 accept manifest 的真 bands）——① 最大衣柜带 → `[[0.3, 0.285, 0.78012, 1.0]]` 且 float 可 JSON 序列化；② 细手臂 sliver（宽 0.08002）被跳过 → 退回 role box；③ 只有 head 带 → 退回 role box（`top + 0.45 * height`、`bottom ≥ 0.999`）；④ 无 geometry／无 role 时回 `[]`，bands 里塞 `None, 7` 也不炸。另写 AST 扫描 `working\_r35e_scan_append_args.py`：四模組（studio／worker／engine／identity sheet）再无同型 arity 错的 `append/extend/update/add`（只剩 `dict.update(**kwargs)` 假阳性）。

**必须澄清的一处过度声称**：`working\_round35c_offline_verify.py` 第 67 行是**手喂** `"body_bboxes_normalized": [BAND]` 给 worker，从未执行过 studio 侧的 `_character_swap_body_audit_box()`。所以 §35／Round 35b 写的「用 shipped 路径复核（不是手搓等价逻辑）」对那个 helper 而言**不成立**——它当时根本没被跑过，这也是这个崩漏到 GUI 才被发现的原因。本轮补上真正走 shipped 路径的探针：`working\_r35e_preview_rebuild_check.py`（headless 调 `DirectorCutStudio()._build_smart_render_job(request_kind="preview", megapixels=0.5, seed=923009999)`），**VERDICT OK**，三段一致：`policy=70`、`segments=3`、`framing=illustrated_full_design`、`passthrough=True`、上传参考＝**P1 原图** `image_137_4bd41c9e363a8278_nobg.png`（不是 sheet）、衣柜签名 `image_137_..._nobg_wardrobe_db6fde105445_v1.png`、`identity_sheet_reference_head_coverage=0.220077`／`source=0.214413`／`fill=0.96257`、`identity_audit.body_bboxes_normalized=[[0.3, 0.285, 0.78012, 1.0]]`＋`wardrobe_audit_mode="on"`＋`minimum_wardrobe_shift=0.12`＋`whole_character_audit=true`、prompt `11324/12320` 字元、`dropped_tail_clauses=[]`、`over_budget=false`。注：这些 key 在 **`identity_audit` 里面**，不在 pass row 顶层（顶层是 `identity_sheet_reference_head_coverage`／`…_source_head_coverage`／`…_subject_fill`／`…_single_figure_passthrough`）。

**Verification（本轮第一手复跑）**
- `test_character_swap_engine`＋`test_character_swap_closeup_gates`＋`test_character_swap_silent_audio`＋`test_character_swap_background_extra` ⇒ **162 OK**（7.0 s，含新增 4 项）
- `testing.test_identity_sheet`＋closeup_gates ⇒ **123 OK**（7.8 s）
- `py_compile`：studio／worker／engine／identity sheet＋新测试档 ⇒ exit=0
- 未结项照旧：silent listener 对嘴（seg1 三次 fresh seed 压不住）

**状态界定**
- **源码已修复**：Preview 崩（arity）＋回归测试＋AST 扫描＋shipped 路径 Job 编译取证。GPU 这轮**没碰**——那次 Preview 死在 Job 编译之前，ComfyUI 全程空闲。
- **视频已实机验证**：**无**。policy 70 至今零枪；可跑 job 已备好（`render_jobs\preview_923009999_1793143069391241000.job.json`，本轮重建），等用户批准才上卡。 > 已由 Round 35e（2026-10-28 07:54）实机跑完并读帧，见本节上方 Round 35e。

### Round 35b：衣柜位移闸门的 floor 定在 0.12 —— 用 9 点/段实测定标，并用 shipped 路径逐段复核：三段已 accept 的 take 位移只有 0.062／0.078／0.102，全部不及格 ⇒ 会被闸门拒掉并重抽 fresh seed（2026-10-28 01:50–03:00 离线，**源码已修复＋离线全绿，实机未跑**）

**为什么要定这个数**：Round 35 的衣柜 audit 需要一个「什么叫做完整个身体替换」的量化界线。`working\_round35b_wardrobe_shift_calibration_20261028.py`（只读 CPU，不碰 GPU）对 Round 34 那支新片的三段各取 9 个取样点量 V1↔take 衣柜色位移：

| 段 | 9 点位移范围 | 与 floor 0.12 |
|---|---|---|
| seg0 0–4.288 s | 0.036 – 0.076 | 全部不及格 |
| seg1 4.288–8.576 s | 0.031 – 0.150 | 多数不及格，1 点勉强过 |
| seg2 8.576–12.864 s | 0.082 – 0.270 | 9 点均值 0.134 > 0.12，边界段 |

对照参照值（写进 `character_swap_engine.py:233` 注释）：三段中位数 0.053／0.089／0.114、整片最好单帧 0.177、真正整片换装的参照样本 ≥0.20。positive control 图 `_dsh_verify_9\round35\positive\`（标 0.152／0.177）读帧仍是「P1 的头＋V1 猫耳假发＋粉黑 cosplay 身体」⇒ **0.15–0.18 还不能叫整身替换**，所以 floor 落在 0.12 而不是 0.15：宁可让边界段重抽，也不要把「只换头」放过去。已知代价：seg2 这种均值贴着 floor 的段，判定会随取样点数摆动（3 点 vs 9 点结论可能不同）。

**离线取证（shipped 路径，`working\_round35c_offline_verify.py`）**：载入即 `passthrough=True`／`wardrobe_audit_mode=on`／`minimum_shift=0.12`。P1 原图 `image_137_4bd41c9e363a8278_nobg.png` 自量 head coverage **0.220077**（≥0.22 门槛，勉强过）、subject fill **0.96257**、head box `[37,1,172,153]`、subject box `[0,11,250,370]` ⇒ 编译路径决策 `FULL_DESIGN_FRAMING="illustrated_full_design"`＋passthrough `true`，**上传的就是 Media Pool 原图**，不再经 sheet。衣柜签名档 `image_137_4bd41c9e363a8278_nobg_wardrobe_db6fde105445_v1.png`，签名 bbox `[0, 0.418919, 0.992063, 1]`（只裁衣服，不含脸），第二次调用返回 `cached`。三段 accepted take 全部被拒：shift **0.062375／0.078099／0.102392**（ROI 取 manifest 里的衣柜带 `[0.30, 0.285, 0.78012, 1.0]`，每段 3 取样点），`passed=false`、`action=retry_fresh_seed`，reason「replacement is only a head/face layer; the V1 wardrobe still fills the body region」。

**状态界定**
- **源码已修复**：衣柜位移闸门（`CHARACTER_SWAP_MINIMUM_WARDROBE_SHIFT=0.12`）＋标定依据已在树内。测试：`test_character_swap_engine`＋closeup_gates＋silent_audio＋background_extra **158 OK**、`testing.test_identity_sheet` **52 OK**、`testing.test_smart_render_worker` **57 OK（skipped 1）**；另有 storyboard_segment_mapping **7 OK**、smart_render_qc_advisory **5 OK**、project_workspace **19 OK**（后三组沿用本轮较早的重跑）。四模組 `py_compile` 全绿。
- **视频已实机验证**：**无**。policy 70 至今没跑过一枪，上面三段 0.062／0.078／0.102 是拿 policy 69 已 accept 的 take 反向套新闸门算出来的，只能证明「闸门会拒这一支的只换头」，不能证明重抽后能过。 > 已由 Round 35e 实机跑完：闸门没误杀、也确实重抽过只换头的 take，见 Round 35e。

### Round 35：读帧定位两个根因——参考图 55% 是空白垫板（sheet 下半身在 4.287 s 段边界漏进画面）＋27–29% 的 V1 衣柜落在抑制带外 ⇒ 新增「单图直通」与「衣柜 audit」，policy 69→70（2026-10-28 01:23–02:30 离线＋修码，**源码已修复，实机未跑**）

**症状**（用户自己在 Studio 按 Preview/Accept 出的新片，0.5 MP 与 1.0 MP 都比开始好很多）：① `generated_output.mp4` 第 4 秒出现 identity sheet 的下半身面板；② 这一段其实只换了头，身体仍是 V1。

**根因①｜参考图本身大片是空白**（`working\_round35_sheet_bleed_and_body_probe_20261028.py`，CPU 只读）：被上传的 sheet `image_137_4bd41c9e363a8278_nobg_identitysheet08_fullfig_a0066_v8.png`（800×1216）**近白像素占 55.0%**；head 面板占 54.6% 画布、面板内部空白 50.6%；outfit 面板占 97.3%、内部空白 57.8%；head／outfit 面积比只有 0.56×。量化到身份门槛：sheet 的 head coverage **0.5259**，而 V1 源人物只有 **0.2144** ⇒ 2.45 倍的头身配重差，模型会把 sheet 的面板边框与无头躯干当成「要画进画面的东西」，在段边界（4.287 s）就渗出来。

**根因②｜抑制带没盖到衣柜**：R1 手动画框 `[0.35, 0.15, 0.65, 0.45]`＝29.2% 画面，plate 实际被抑制的面积 **61.0%**（manifest `suppressed_frame_area=0.5013`）。带框之外仍留着 V1 的衣服：三段带外 V1 衣柜像素 **27.8／27.1／29.2%**，V1 粉腰带带外 **20.6／23.2／27.4%**。叠加图 `_dsh_verify_9\round35\seg{0,1,2}_bands_vs_costume.png`。⇒ prompt 写了 `crown to feet`，plate 却只削掉身上 6 成里的一部分，模型读到的还是 V1 的黑金 cosplay。

**修码清单**（全部在树，已复核）
- `character_identity_sheet.py`：新增 `measure_reference_head_metrics()`（883）与 `compose_wardrobe_signature()`（931）——后者只裁衣服区做衣柜签名，不混脸。
- `director_cut_studio.py`：单图直通分支（34919–34936，决策回传 `FULL_DESIGN_FRAMING="illustrated_full_design"`，engine 237）；`_character_swap_wardrobe_signature()`（35039）、`_character_swap_body_audit_box()`（35079）；knob `IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH`（1410，env `H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH`）、`CHARACTER_SWAP_WARDROBE_AUDIT_MODE`（1421，env `H3_CHARACTER_SWAP_WARDROBE_AUDIT`＝`on|advisory|off`，默认 `on`）；pass rows 记 5 个 identity_audit keys（36843–36850、36960–36966）。
- `smart_render_worker.py`：`_wardrobe_audit_bboxes()`（1567）、衣柜 audit 主体（2157–2262，回传 `checked/passed/mode/shift/rows/minimum_shift/reason`）、衣柜相似度加成 `min(0.35, shift) * 1.5`（1613）、`whole_character_audit` 走 strict temporal coverage（1981）。
- 阈值（`character_swap_engine.py`）：`IDENTITY_SHEET_MIN_HEAD_COVERAGE=0.22`（205）、`IDENTITY_SHEET_MIN_SOURCE_CANVAS_HEAD_COVERAGE=0.18`／`IDENTITY_SHEET_MIN_SOURCE_SUBJECT_FILL=0.55`（221–222，注释写明 black-shirt 证据）、`CHARACTER_SWAP_MINIMUM_WARDROBE_SHIFT=0.12`（233）。
- `SMART_RENDER_POLICY_VERSION` **69→70**，`director_cut_studio.py:715` 与 `smart_render_worker.py:103` 同步。

**回滚**：`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH=0` 退回 sheet 路径；`H3_CHARACTER_SWAP_WARDROBE_AUDIT=off`（完全不量）／`=advisory`（只量不拦）。

**状态界定**
- **源码已修复**：上述全部改动＋policy 70＋测试与 `py_compile` 全绿（158／52／57(+1 skip)，另 7／5／19 沿用本轮较早重跑）。

**别再重跑的死角**：round 32 的 `blur`（policy 69，§32）与 round 33 的 `blur_desat`（§33）已证明「加大抑制／去色」到顶——MEAN similarity 卡在 0.552–0.587，且 desat 会让模型把灰模板还原成 V1 cosplay。本轮改的是**喂给模型的参考图本体**与**验收条件**，不是抑制强度。

### Round 34：crown／face 分带（`_hair_band_*`，默认 `off`）＋knob 进 `design_ai.env` 白名单；用户 GUI 跑出的新片（0.5 MP／1.0 MP）读帧仍有「sheet 下半身渗出」与「只换头」两缺陷 ⇒ **这支新片是 policy 69 旧 plate 的产物，分带与 policy 70 都还没实机跑过**（2026-10-28 00:11–01:10 实机 seed 2027186731173264249，**视频已实机验证＝两缺陷仍在**）

**跑法**（Director 自己在 Studio GUI 按 Preview／Accept，不是 staged driver）：motion_preview 00:21 → `generated_preview.mp4` 7.13 MB@00:32（0.5 MP）→ `generated_output.mp4` 10.63 MB@01:10（1.0 MP）。manifest `accepted_2027186731173264249_1793118846499730000.manifest.json`：`megapixels=1.0`、`master_seed=2027186731173264249`、**`render_policy_version=69`**。

**QC（纯读 manifest，`working\_r35d_manifest_read{,2,3}.py`、`_r35d_manifest_keys.py`、`_r35d_hair_modes.py`）**

| 段 | seed | attempts | similarity | silent |
|---|---|---|---|---|
| seg0 0–4.288 s | 6533122960410627603 | 1 | 0.608703 | pass |
| seg1 4.288–8.576 s | 7217704202240956819 | 3 | 0.573653 | **fail**（`authored Silent Listener mouth shows excessive articulation`、`character_swap_identity_failed=true`）|
| seg2 8.576–12.864 s | 3524457325454587044 | 1 | 0.506030 | pass |

MEAN **0.5628**（与 round 32 blur 0.5521／round 33 desat 0.5753 同档）。pass rows 三段都是 `reference_framing=illustrated_identity_sheet`、`identity_sheet_head_coverage 0.5259`／`source 0.214413`、preset forced 8、`outfit_view=full`、`identity_sheet_reason=cached`。

**plate 实况（决定性）**：`identity_suppression_geometry` 记 `wardrobe_mode="blur"`、**`hair_band_mode="off"`**、`hair_extent.enabled=0.0`（params `vertical_share 0.42`／`saturation 0.25`／`blur_radius 18.0`／`extra_sigma 0.0`／`min_band_height 0.05`）、`mask_mode="feather"`、`suppressed_frame_area 0.5013`、bands 3（head 带 `[0.3, 0, 0.4001, 0.285]`＋两条衣柜带）⇒ 本轮新增的头饰分带**没有参与这支新片**，Round 35 的 policy 70 也没有。

**本轮源码**（未参与上述新片）
- `_hair_band_mode()`（1029，`off` 默认／`blur_desat`）与 `_hair_band_parameters()`（1044）：把 head 带拆成 face ROI（锐利、保护身份）＋hair／accessory ROI（blur＋desat），目标是打掉 V1 猫耳假发、镶金宝石头带。
- geometry 自记录 `hair_band_mode`（36133）：**只在实际套用时报真值**，没套用就写 `off`，避免以后误读。
- `H3_CHARACTER_SWAP_HAIR_BAND_MODE` 已加入 `DESIGN_ENV_RENDER_KNOBS` 白名单（433–444），让 GUI 按 Preview 时 knob 能靠 `design_ai.env` 跨重启携带（真 env 优先）。

**备份纪律**：同 seed 会覆盖输出目录，跑前已把上一版 desat take 备份到 `_dsh_verify_9\round34\prev_desat_take_backup\`（三段 `character_swap_pass_01_R1\00_save.mp4`／`01_source.mp4`＋`master.mp4` 8,747,247 B）。

**状态界定**
- **视频已实机验证**：0.5 MP／1.0 MP 两支都已读帧，用户口径与读帧一致——**sheet 下半身渗出（4.287 s 段边界）与「只换头没换身」两个缺陷仍在**；silent listener 仍未结（seg1 用满 3 次 seed 仍压不住对嘴）。
- **源码已修复**：hair／face 分带＋knob 白名单＋geometry 自记录，shipped default 仍 `off`，本轮未跑。
- program monitor 的 preview 无声：`_apply_monitor_audio_routing` 与 10-26 备份逐字相同（matches 21=21）⇒ **本轮没有新增源码**，不能写成已修好。

### Round 33：单一变量 `blur_desat`（衣柜灰模板 s=0.25）实机——数值上粉被去掉、黄回来了，但读帧证明模型把灰轮廓**还原成 V1 的黑金 cosplay**，猫耳冠照旧、眼镜还丢了 ⇒ desat 记为已否决分支（2026-10-27 21:43 实机 seed 923001027，**视频已实机验证＝结论为负**）

**跑法**：`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur_desat` + `staged_model_driver.py run example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923001027_1793108487623275800.job.json`（背景 Start-Process，pid 13472）。driver 收尾 `comfy-free ok=true`、`vram-release freed_gb=0.0`、`report` manifest `render_policy_version=69` 且 geometry 新增自记录 `wardrobe_mode="blur_desat"`、`wait-qwen-reload ready=true`（Tray 已载回 Qwen）。blur 版 p69 输出 13 档／35,596,819 B 已先备份到 `_dsh_verify_9\round33\p69_master_backup\`（同 seed 会被覆盖）。

**离线取证（不碰 GPU，`working\_round33_desat_plate_check_20261027.py`，verdict OK）**：同一 timeline 建 blur／desat 两份 job，几何与预算**完全一致**（`suppressed_frame_area=0.5013`、bands 同、`wardrobe_reaches_bottom=True`、clause `crown to feet`、`dropped=[]`），prompt 只差 strategy 名 15 字符（12210→12195，仍在 12320 内）。desat 真的只在带内生效：衣柜区 mean saturation 114→46、六个采样点 ratio 稳定 **0.386–0.413**（名义 `hue=s=0.25`、实测 ~0.40），head 区 103.5→103.4、背景控制区 x<0.20 是 105.3→105.4 ⇒ 无 round-14「糊整面墙→背景蜂窝」的风险来源。plate A/B：`_dsh_verify_9\round33\r33_desat_plate_ab.png`。

**同 seed 三次 QC 对照（`working\_round33_qc_table_20261027.py`）**

| 段 | blur（p69）| similarity | silent | desat（p69+blur_desat）| similarity | silent |
|---|---|---|---|---|---|---|
| seg0 0–4.288 s | 2/3 | 0.6081 | pass | 3/3 | 0.6005 | pass |
| seg1 4.288–8.576 s | 3/3 | 0.5163 | pass | 3/3 | **0.5930** | **fail**（`silent_mouth_excessive_articulation`、`identity_failed=true`）|
| seg2 8.576–12.864 s | 2/3 | 0.5319 | pass | **1/1** | 0.5326 | pass |
| MEAN | | **0.5521** | 3/3 | | **0.5753** | 2/3 |

`source_plate_continuity_audit` 虽 passed，但相关性明显低于 blur 版：seg0 r0 0.709（blur 0.922）／r1 0.538（0.880）／r3 **0.058**（0.741）、seg1 r2 **−0.243**（0.658）⇒ 带内被改写更多、背景锚点更弱（seg1 用满 3 次重试）。

**数值评级（`working\_round33_desat_grade_20261027.py`，lower crop x0.25–0.78／y0.52–1.0，9 个取样点）**：desat 的 yellow share 在 seg0／seg2 明显上升（t0.6 0.031→0.100、t3.4 0.000→0.102、t9.6 0.041→0.056），magenta share 全线下降（t3.4 0.677→0.033、t2.0 0.662→0.163），lower 区 mean saturation 下降 ⇒ 粉色丝带与粉黑条纹袖确实被压掉。**但**这些数字来自「粉被去掉」＋底缘几块黄格纹，不等于 P1 衣柜整件回归。

**读帧四判据（`_dsh_verify_9\round33\frames_p69desat\`：`r33_desat_vs_blur_bottom.png`／`r33_desat_vs_blur_head.png`／`r33_master_grid.png`＝desat／`p69_master_grid.png`＝blur／`r33_desat_vs_reference.png`）**
- ① 髋以下是 P1 黄格纹长裤＋黑球鞋：**不通过**。desat 下半身主体是 V1 的黑底镶金 cosplay 长袍（深色蜂巢 mesh＋红／粉腰带＋粉或蓝袖），黄格纹只剩画面底缘小块（t0.6／2.0／3.4／9.6）⇒ 与 `r33_desat_vs_reference.png` 里 P1 identity sheet 的「黑上衣＋蓝短裤＋黄格纹」完全不同一件。
- ② 黑猫耳冠＋镶金宝石头带：**没改善**，desat 9/9 帧仍在（blur 6/9），seg0 反而更常出现完整头带。
- ③ 头部仍是 P1 卡通（圆眼镜＋胡子＋秃顶灰边发）：**退步**。desat 的 t0.6／2.0／3.4／5.0／6.6／8.0 **圆眼镜消失**，且头发变成 V1 的整头灰色长假发（P1 是秃顶）；seg2 的 t9.6／11.0／12.3 眼镜回来了但换成大眼另张脸 ⇒ 与 QC seg1 `identity_failed=true` 一致。
- ④ 第二小人／蜂窝背景：未见新蜂窝；R2 绿衣戴帽摄影师保持锐利。

**判读（根因）**：把 cosplay 压成灰模板后，模型没有改读 P1 的衣服，而是**照 plate 的灰轮廓＋V1 先验自行重建原来的黑金 cosplay**（round-13 S4 两次灰洗 take 就是同一现象，当时 ratio 0.64；本轮 ratio ~0.40 更激进 ⇒「灰模板→模型自创／自恢复衣物」这条历史警告成立）。同时 head 带按设计保留 chroma，猫耳冠与宝石头带从未被抑制，P1 秃顶被 V1 假发顶掉、圆眼镜也跟着丢。**结论：瓶颈不在「抑制强度」，而在（A）抑制带没盖住头上配件与假发、（B）P1 衣柜没有任何 plate 之外的强制证据。** 三轮（policy 68 blur／policy 69 blur／policy 69 blur_desat）MEAN similarity 一直卡在 0.552–0.587，这条「加大抑制」曲线已经到顶。

**处置**：`blur_desat` 登记为**已否决分支**，shipped default 保持 `blur`；本轮**未改任何核心源码**（回滚开关与默认值原样）。下一枪方向（待批准，仍单一变量）：把 head 带拆成 face ROI（保护身份，不动）＋hair／accessory ROI（blur+desat），专攻猫耳冠、宝石头带、V1 假发；衣柜那条再谈。

**状态界定**：源码状态＝Round 31／32 已登记内容，未新增修复；`blur_desat` ＝ **源码已在 + 已实机验证，结论为负（不采用）**。identity sheet 头部面板张嘴（silent listener 独立嫌疑线）仍未结。

### Round 32：policy 69 实机——抑制面积 0.18→0.5013 确实把衣柜抢回来，但 blur 保留轮廓与色相 ⇒ 猫耳冠＋镶金头带照抄；seg1 身份跑飞（2026-10-27 21:03 实机 seed 923001027，**视频已实机验证＝部分有效**）

**跑法**：`staged_model_driver.py run example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923001027_1793100745085992400.job.json`。三格 20:46–21:03 全新重生成（`comfy-free ok`、VRAM 释放 1.5 GB、Qwen 由 Tray 载回）。三段几何与离线取证一致：`suppressed_frame_area=0.5013`、`wardrobe_reaches_bottom=True`、bands=3、预算 12210/12320、`dropped=[]`、strategy 名称不变。

| 段 | QC | 选中 attempt | `target_reference_similarity` | silent mouth | plate 连续度（四区） |
|---|---|---|---|---|---|
| seg0 0–4.288 s | passed | 2/3 | 0.6081 | 0.239 pass | 0.919 / 0.881 / 0.451 / 0.741 |
| seg1 4.288–8.576 s | passed | 3/3 | 0.5163 | 0.165 pass | 0.757 / 0.520 / 0.658 / 0.276 |
| seg2 8.576–12.864 s | passed | 2/3 | 0.5319 | 0.290 pass | 0.841 / 0.693 / 0.766 / 0.217 |

三段 QC 全过（policy 68 是 2/3），MEAN similarity **0.5521**（policy 68 = 0.5873；policy 67 = 0.5664 / 0.6045 / 0.5722 ⇒ 仍在同一区间，没有进步）。

**读帧（9 帧，`_dsh_verify_9\round31\frames_p69fig\`：`p69fig_master_grid.png`／`p69fig_bottom_grid.png`／`p69fig_head_grid.png`／`p69fig_vs_reference.png`，脚本 `working\_round31_p69fig_grade_20261027.py`）**
- ① 髋以下换 P1：**7/9 帧**看得到 P1 的黄格纹＋黑球鞋（seg0 底部黄格纹、seg2 黑球鞋＋格纹短裤），policy 68 同 Shot 只有 seg0 做得到。混入项：V1 的粉黑条纹袖仍在；seg2 短裤变成自创青绿微格纹；t12.3 退回黑色蜂巢 mesh。
- ② 黑猫耳冠／镶金宝石头带：**6/9 帧仍在**（t0.6／2.0／3.4／9.6／11.0／12.3），只有 t5.0／6.6／8.0 消失 ⇒ 与 policy 68 相比**没有改善**。
- ③ 头部仍是 P1 卡通（圆眼镜＋胡子＋灰白头顶）：6/9。seg1 的 t5.0／6.6 整段跑飞成「棕发、无眼镜的另一个卡通男」，t8.0 又变灰发老人 ⇒ **同一段内身份漂移**，这是本轮新增的缺点。
- ④ 无第二小人、无蜂窝背景；R2 绿衣戴帽摄影师保持锐利（round31 plate A/B 已验：diff 亮区只在 x0.22–0.78／y0.45–1.0，mask 边缘是 feather 软边）。

**判读**：blur 削弱的是**细节**，几乎完整保留**轮廓与色相**。猫耳冠与宝石头带是大尺寸高对比物件（黑＋金＋粉），plate 里那团模糊足够模型重建出同样的形状与配色 —— 所以「扩带」买到了衣服色块（P1 黄格纹确实出现），买不到头上配件。另外抑制带扩到 0.50 之后，plate 剩下的人物锚点变少，身份重建方差上升：seg1 用满 3 次重试、下半身连续度只剩 0.276。

**处置（下一枪单一变量）**：几何与 prompt 一律不动，只把 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE` 从默认 `blur` 换成 **`blur_desat`**（`WARDROBE_SATURATION=0.25` 灰模板，S4 seeds 97000324／97000334 实测过的配方，源码一直保留但从未启用）。目标：让 plate 里的 cosplay 只剩姿态与明暗，读不出粉黑配色与头饰轮廓。

**状态界定**：policy 69 = **源码已修复 + 视频已实机验证**，但实机结论是「部分有效」（衣柜↑、头饰＝、seg1 身份新缺点）；`blur_desat` 变体是**源码已在、未实机**。

### Round 31：糊布帶只蓋到普查框＝衣服還是 V1 的——衣著帶長到「看得見的身體」，旁觀者用矩形相減摳掉（2026-10-27 19:44 修碼＋離線取證，policy 68→69，**源碼已修復，實機未跑**）

**為什麼要動**：seed 923001027（policy 68）實機三段都已把頭換成 P1 卡通、torso 也明顯改善，但三段仍保留 V1 的黑貓耳冠＋假發與粉黑條紋袖。讀 `identity_suppression_geometry` 找到根因：head 帶與 wardrobe 帶都由 AI 角色普查的 thumbnail box `[0.35,0.15,0.3,0.3]` 推出來，只糊 18 % 畫面；而 V1 的假發＋貓耳＋條紋袖實佔 x0.10–0.90 / y0.03–1.0（≈60 %）。框外的袖、裙、腿一律銳利 ⇒ 模型照抄源服装。

**改了什麼（源碼）**
- `director_cut_studio.py`：`SMART_RENDER_POLICY_VERSION` 68→69。新增 `_figure_extent_parameters()`（env `H3_CHARACTER_SWAP_FIGURE_EXTENT`=0 回滾、`_WIDTH_SHARE`=1.75、`_MAX_WIDTH`=0.80、`_BOTTOM`=1.0、`_MAX_AREA`=0.56、`_MIN_PIECE_WIDTH/HEIGHT`=0.06）、`_subtract_protected_boxes()`（精確矩形相減，碎片互不重疊）、`_figure_extent_band_boxes()`（候選寬度依 1.0 / 0.8 / baseline 遞減，先扣掉 protected box，丟棄小於 0.06 的碎片，含 head 帶的總面積超過 cap 就整套退回 policy-68 baseline）。
- 衣著帶從單矩形改成多矩形，但 `kind` 仍是 `wardrobe` ⇒ strategy 名稱與 prompt 條款選擇完全不動，**prompt 零增量**。`identity_suppression_geometry` 新增 `figure_extent{parameters, applied}` 與 `wardrobe_reaches_bottom`。
- `smart_render_worker.py`：`SMART_RENDER_POLICY_VERSION` = 69。
- `character_swap_engine.py`：merged silent plate 條款依 `wardrobe_reaches_bottom` 選 `crown to feet` / `crown to hips`（兩串都是 4 字元 ⇒ 12 288/12 320 預算不動）；沒有該 key 的舊 geometry 仍寫 `hips`。

**離線幾何取證（不碰 GPU，`working\_round31_figure_extent_geometry_20261027.py 923001027`）**：三段都是 budget 12210/12320、`dropped=[]`、strategy 名稱不變。bands 由 policy-68 的 0.18 變成 head (0.30, 0, 0.4001, 0.285) 0.114 ＋ wardrobe (0.30, 0.285, 0.48012, 0.715) 0.3433 ＋ wardrobe (0.21998, 0.45, 0.08002, 0.55) 0.044 ⇒ `suppressed_frame_area=0.5013`、`wardrobe_reaches_bottom=true`、prompt 出現 `crown to feet`。ffmpeg A/B 圖 `_dsh_verify_9\round31\plate_ab_t2.png` 與差異圖 `plate_diff_t2.png` 證明：差異只落在新帶（x0.22–0.78、y0.45–1.0），右側背景 x>0.78 與綠衣攝影師 R2（protected box [0.15,0.25,0.3,0.45]）仍然銳利，feather mask `plate_mask_p69.png` 邊緣是軟的（round-14「糊整面牆→背景長蜂窩」的教訓）。

**驗證**：`test_character_swap_*` **141/141 通過**（本輪新增 9 項：`_figure_extent_parameters` 預設值／env 回滾／junk 退回預設、矩形相減逐格鋪滿且碎片零重疊、protected box 完整摳除、area cap 退回 policy-68 baseline、engine `crown to feet`/`hips` 與 `wardrobe_reaches_bottom` 一致且字串等長）；`director_cut_studio.py`／`smart_render_worker.py`／`character_swap_engine.py`／`character_identity_sheet.py`／`staged_model_driver.py` py_compile 通過。**實機尚未跑**；回滾開關 `H3_CHARACTER_SWAP_FIGURE_EXTENT=0`。

### Round 30：policy 68 实机——head 带长过假发后三段头**全是 P1**，但衣著带只到普查框，V1 猫耳冠＋镶金头带三段都留（2026-10-27 19:12 实机 seed 923001027，policy 68，**实机＝部分有效**）

**送达证据**：manifest `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923001027_1793097354479742600.manifest.json`（`render_policy_version=68`）。`uploaded` 只有两件：**Picture 1 = `image_137_..._nobg_identitysheet08_fullfig_a0066_v8.png`（full-figure sheet）** ＋ **Video 1 = 抑制后的 plate mp4** ⇒ Round 28 重建的全身身份面板与 plate 抑制都真的进了模型输入。`identity_suppression_geometry.suppressed_frame_area = 0.18`。driver log `_dsh_verify_9\round30\driver_923001027_run.{out,err}.log`。

**机械指标**：seg0 `target_reference_similarity` 0.6187 **通过**、seg1 0.5529 **通过**、seg2 三次重试后 `silent_mouth_excessive_articulation` **失败**（取最佳 0.5904）⇒ MEAN **0.5873**（policy 67 同结构 0.5407、policy 66 是 0.5955）。

**读帧四指标**（探针 `working\_round30_policy68_halo_budget_20261027.py`＋人工读帧；A/B 图 `_dsh_verify_9\round30\r30_sheet_v7_uhip_vs_v8_fullfig.png`）
- **头部：3/3 段都是 P1**（光头＋眼镜＋胡子的卡通脸），不再跑成灰发老人、也不真人化 ⇒ Round 29 的 `source_hair_ownership_clause` ＋ head 扩带有效。
- **衣著：明显改善但不完整**——seg0 蓝袍下摆＋黄格纹大腿＋黑球鞋、seg1 黑白滚边背心、seg2 蓝袖＋黑背心都在（policy 67 同 Shot 全是 V1 粉黑条纹袖）。
- **头发／头饰：仍失败**——V1 黑猫耳冠＋镶金／宝石头带**三段都在**，直接压在 P1 光头上；假发残留且跨段变色（粉／黑／粉）。
- **背景／路人**：无蜂窝状图案；R2 绿衣戴帽摄影师保留（seg2 t≈10 s 有一个灰色糊人物）。

**遗留根因（这一轮的真正结论）**：head 带与 wardrobe 带**都由 AI 角色普查的 thumbnail box `[0.35, 0.15, 0.3, 0.3]` 推出来** ⇒ 只糊 18 % 画面，而 V1 的假发＋猫耳＋粉黑条纹袖＋长裙实佔 x0.10–0.90 / y0.03–1.0（≈60 %）。**框外的袖、裙、腿在 plate 里依旧锐利** ⇒ 模型照抄源服装与头饰，直接催生 Round 31。

**状态界定**：**源码已修复＋视频已实机验证**，但实机结论是「部分有效」（头 ✅、衣 ↑、头饰 ❌）。回滚快照 `_backup\V0.3.8-alpha.3_policy68_fullfigure_hairhalo_pre_run_20261027\ROLLBACK.md`。

### Round 29：policy 68 源码——engine 加 `source_hair_ownership_clause` 与 `pass_index/pass_total` stamp，identity sheet 引擎 7→8 支持 `full` 衣柜视图，head 带扩过假发（2026-10-27 修码，**源码已修复**）

**改了什麼（源碼）**
- `character_swap_engine.py`：新增 `source_hair_ownership_clause`——把头发的归属写进 prompt（源片的头发／头饰属于 `<Subject 2>`，不得移植到 `<Subject 1>` 头上）；每条 pass 另記 `pass_index` / `pass_total` stamp，便于事後逐 pass 判讀。
- `character_identity_sheet.py`：sheet 引擎 **7 → 8**，`OUTFIT_VIEW_*` 新增 `"full"`（全身衣柜视图），让 sheet 也能供给髋以下的服装权威。
- head 抑制带由 `H3_CHARACTER_SWAP_HAIR_HALO_UP_SHARE`（0.5）、`_UP_MAX`（0.18）、`_WIDTH_SHARE`（1.45）、`_MAX_BOX_WIDTH`（0.6）向上扩过假发／头冠。

**政策號記帳不一致（點名，勿再混淆）**：本輪備份快照 `_backup\V0.3.8-alpha.3_policy68_fullfigure_hairhalo_pre_run_20261027\ROLLBACK.md` 記「改碼前＝policy 67、engine 7」，而 Round 26 結尾已記 `67 → 68` ⇒ 同一個 68 被兩處提到。**已用 manifest 核實**：round 30 實機 `render_policy_version=68` 且帶 fullfig sheet＋head 擴帶（＝本輪源碼內容），round 32 實機是 69 ⇒ 68 這個號在實機上生效過一次，行為與本輪源碼一致；只是 `SMART_RENDER_POLICY_VERSION` 常數在 Round 26 回滾時已先 bump，本輪未再 bump。不影響任何回滾開關。

**驗證**：`test_character_swap_*` 全綠＋四模組 `py_compile` 通過。本輪只算**源碼已修復**，影片判讀見 Round 30。

### Round 28：衣柜權威來自哪裡——半身（uhip）identity sheet 面板根本不含髋以下（2026-10-27 17:46–17:55 離線取證，不跑 GPU）

- 對照圖 `_dsh_verify_9\round28\frames\r28_p1_panel_full.png` 與 `r28_p1_panel_uhip_current.png`（另有 `r28_p1_source_full.png`）：當時上線的 `*_uhip` 面板只有**上半身**，不含 P1 的黃格紋短褲＋黑球鞋 ⇒ 衣柜的視覺權威只能從 plate 殘影猜，而 plate 正在被抑制 ⇒ **兩邊都沒有權威**，模型退回去抄 V1 的 cosplay。
- 據此重建全身版 sheet：`image_137_..._nobg_identitysheet08_fullfig_a0066_v7.png` / `_v8.png` ＋ `.identity_sheet.json`（v8 落在 `_dsh_verify_9\round30\sheets\`，另有 `_head_v8.png` / `_body_v8.png` 變體）——這正是 Round 29 在 `character_identity_sheet.py` 加 `"full"` 視圖的直接原因。
- 本輪**純離線**：沒碰 ComfyUI，也沒碰 Qwen。

### Round 27：round 26「擴帶反而更差」是條款被擠掉還是 blur 本身壞事——同一 timeline 編 off／blur 兩版 prompt 對照（2026-10-27 17:40 離線，seed 923000999、tail-drop 關閉）

- 把同一條 timeline 分別以 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off` 與 `=blur` 各編一份 prompt，並把 budget 覆寫成 99999（**關掉尾部丟棄**），於是兩版都保留全部條款，差異只剩 blur 機制本身。輸出：`_dsh_verify_9\round27\prompt_build_log.txt`（`built mode=off policy=67 segments=3 passes=1` / `built mode=blur ...`，合併條款普查計 847 chars）與 `_dsh_verify_9\round27\prompt\S1_p0_R1_P1_{off,blur}.txt`。
- **結論**：Round 26 那次退步**不是**「silent 條款被擠掉」——兩條 silent 都在。真正原因是 **blur 只削細節、保留輪廓與色相**，模型轉而從未被抑制的 V1 區域取衣與取頭飾 ⇒ 於是要嘛把衣柜權威搬到 full-figure sheet（Round 28/29）、要嘛擴大抑制面積（Round 31）、要嘛改用 `blur_desat`。
- 本輪**純離線**：只編 prompt，沒碰 GPU。

### Round 26：medium-silent 只糊头部不够——扩到「头冠到臀部」整条人物带，并把两条条款合并成一条才塞得进预算（2026-10-27 15:40 修码，16:00 实机 seed 923000327，policy 66→67→68，**实机＝退步，默认值已回滚**）



**为什么要动**：round 24/25 的实机（seed 923000227，policy 66）已经量化了「只糊头部」的效果——头套／假发 8/12 帧被 P1 取代、三段 `target_reference_similarity` 单调上升（0.5685→0.5955），但**衣柜只有 4/12 帧换上 P1**（只有最干净的 seg2 整套跟过来），seg0／seg1 的躯干仍被源片那套粉黑条纹 cosplay 压住。也就是说 plate 抑制的方向被证明有效，只是**作用范围只到肩膀**。

**改了什么（源码）**
- `director_cut_studio.py`：新增 `CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE` 与 `_medium_silent_wardrobe_band_mode()`（env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`，`off|blur|blur_desat`，默认 **`blur`**）。当一条 pass 的**全部** gate row 都是 `medium_silent` 时，plate 抑制从「只糊头部」扩成「头部＋衣著带」，策略尾码 `_wardrobe_blur_suppressed`，plate cache token 升到 v7。
- **默认不用 `blur_desat`**：round-14 的 S4（seeds 97000324 / 97000334）已经证明去饱和会把衣服变成灰模板，模型接着自己发明不存在衣物。所以 medium 用的是**保色模糊**——留下色块与placement，抹掉领口、接缝、布纹这些「能认出是 cosplay」的结构。
- `character_swap_engine.py`：新增 `plate_wardrobe_silent_clause`，header `SOURCE PLATE HEAD AND WARDROBE BLURRED — AUTHORITATIVE:`。触发条件是「已有衣著带 且 策略含 `medium_silent` 且 不含 `dominant`」，也就是**只管中景静音角色**，近景大脸那套（`dominant`）一个字都不改。命中时把原来的 head 带与衣著带**合并成一条**并把两者清空，保证 plate 在 prompt 里仍然只被描述一次。措辞随 plate 模式切换：`blur` ⇒ `its colours survive while no collar line, seam or drape resolves`；`blur_desat` ⇒ `below the shoulders it is a neutral grey template`。
- `CHARACTER_SWAP_TAIL_DROP_RANKS`：改成单一 `"plate_wardrobe_silent_clause": 0`（最先被牺牲，排在 `close_up_silent_mouth`=1、`medium_shot_silent_mouth`=2、`source_costume_leaves_plate`=3、`close_up_sheet_crop_lock`=4 之前）。理由：衣著义务已经由无条件的 `COMPLETE WARDROBE REPLACEMENT` 承担，而静音口型条款别无替补 ⇒ 预算不够时宁可退这条，也不能退静音。

**为什么必须合并（这一轮真正的坑）**：初版把 head 带与衣著带**分开写两条**，实测真实 budget 12320 的专案编译出 **12758 chars** ⇒ 长度守卫反手丢掉 525 chars 的 `MEDIUM-SHOT SILENT MOUTH REINFORCEMENT`（编译后 12231）。换句话说「加衣著条款」的实价是 +857 chars，直接**把静音对嘴的修法挤掉**，两件事互相抵消。第一版合并（978 chars）仍超 99 chars，压缩到 **847 chars** 后落在 **12288 ≤ 12320**，两条 silent 口型条款都保住了。

**离线实测矩阵（专案 `a_cartoon_character_with_a_black_shirt_and_yellow_pants`，1 shot→3 segments，单 pass `S1_p0_R1_P1`，budget 12320）**

| 配置 | 编译后 chars | dropped tail clauses |
| --- | --- | --- |
| `off`（＝policy 66 行为） | 11901 | 无 |
| `blur` 两条分开写（初版） | 12758 | **丢 `MEDIUM-SHOT SILENT MOUTH`** |
| `blur` 合并 978 chars | 12419 | 仍超限 |
| **`blur` 合并 847 chars（现况）** | **12288** | **无 ⇒ 静音条款保住** |

探针 `working\_round26_policy67_wardrobe_band_budget_20261027.py`（`H3_PRECHECK_BUDGET` / `H3_PRECHECK_OUT` 可覆盖）；log `_dsh_verify_9\round26\logs\policy67_merged_clause_compressed_budget_probe.log`（verdict **OK**，并附带断言「合并条款必须存在且旧两条不得并存」）；dumped prompts `_dsh_verify_9\round26\prompts_merged2\`。

**测试**：`testing\test_character_swap_engine.py` 新增 5 项（合并条款唯一且 <900 chars、face／wardrobe 两条旧条款必须消失、两条 silent 口型条款共存且排在合并条款之前、blur 与 desat 措辞不互串、close-up 的 `dominant` 不触发合并；以及**用实测字数字节-1 作 budget 时唯一被丢的就是 `plate_wardrobe_silent_clause`**）⇒ 该文件 **Ran 74 tests OK**。`testing\test_character_swap_closeup_gates.py` 新增 5 项 knob／回滚／优先级测试 ⇒ **Ran 42 tests OK**（教训：同一个 test 内不能建第二个 `DirectorCutStudio()`，因为 `subprocess.run` 已被 fake，`detect_ace_step_runtime` 会炸）。目标六档组合 **Ran 180 tests OK**；三个源档＋两个测试档＋探针 `py_compile` 全过。全量套件跑到本条目登记时仍在进行（`_dsh_verify_9\round26\logs\suite_policy67_merged_silent_band.log`，基线 policy 66 是 `Ran 866 tests OK (skipped=10)`，本轮新增 5 项 ⇒ 预期 ~871）。

**版本**：`SMART_RENDER_POLICY_VERSION` **66 → 67**（`director_cut_studio.py`、`smart_render_worker.py` 同步）。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。回滚快照 `_backup\V0.3.8-alpha.3_policy67_silent_merged_band_pre_run_20261027\`（四模块＋`ROLLBACK.md`）；运行时回滚只需 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off`。

**状态**：**源码已修复＋离线全绿；视频未实机验证**。要验证的是两件事——（a）衣著是否在**全部三段**都换成 P1（policy 66 是 4/12）；（b）silent 对嘴是否回到阈值以下（policy 66 三段全败 0.287／0.229／0.213，源 0.063／0.071／0.080）。注意 silent 已排除音频因素（silent plate `audio_stripped`）与措辞因素，另有新线索：identity sheet preset 8 的头部面板本身就大笑张嘴，头部一带糊掉就由「张嘴的 sheet」主导 mouth——那是**另一个变量**，不在本轮混入。提议下一枪 seed 923000327 一族，仍需用户批准才开跑。

**实机结论（round 26b，seed 923000327 一族，2026-10-27 16:00，policy 67）＝退步 ⇒ 默认回滚 `off`、policy 67→68**

送达证据（证明这一枪真的是 policy 67，不是「只写进 prompt」）：manifest `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923000327_1793087088562593800.manifest.json`，三段 pass 行都是 `strategy=medium_silent_listener_identity_suppressed_wardrobe_blur_suppressed`，`identity_suppression_geometry` = head(0.15, 0.135) + **wardrobe(0.285, 0.165)**、`wardrobe_mode=blur`、`suppressed_frame_area 0.0828`（policy 66 是单 head band／mode `off`／0.0373）；`prompt_budget 12288/12320`、`dropped=[]` ⇒ **本轮的预算修复实机成立**，两条 silent 口型条款都在场；参考图 bytes 不变（`identitysheet08_…_v7.png`，`reason "cached"`）⇒ 与 923000227 是干净单变量。Driver 收尾 `worker-exit 0` → `comfy-free ok` → `wait-qwen-reload ready`。

机械指标（探针 `working\_round26_blackshirt_grade_20261027.py`，log `_dsh_verify_9\round26\logs\grade_round26_policy67.log`）：

| 段 | policy 66（923000227）sim / silent | policy 67（923000327）sim / silent |
| --- | --- | --- |
| seg0 0–4.288 s | 0.5967 / 不过 0.287←0.063 | 0.5708 / 不过 0.253←0.063 |
| seg1 4.288–8.576 s | 0.6211 / 不过 0.229←0.071 | 0.5147 / **通过** 0.233←0.071（attempt 3 `accept`） |
| seg2 8.576–12.864 s | 0.5686 / 不过 0.213←0.080 | 0.5367 / 不过 0.260←0.080 |
| 平均 `target_reference_similarity` | **0.5955** | **0.5407（三段全降）** |

读帧（12 帧 × wardrobe／head／bottom-left／master，`_dsh_verify_9\round26\frames\r26_p67_*` 对同目录 `r26_p66_*`，基准 `r26_p1_reference.png`）：

- **衣著：policy 66 有 3/12 帧整套换成 P1（seg2 10.0s／11.2s／12.4s——黑背心白滚边＋蓝长袖＋蓝短裤＋黄格纹袜＋黑鞋都在），policy 67 是 0/12**，三段自始至终都是源片那套粉黑条纹＋粉缎带 cosplay。
- **头部：policy 66 有 9/12 帧恢复 P1 光头，policy 67 是 0/12** —— 12 帧全部挂着粉红双马尾＋猫耳；seg1（4.3–8.6 s）整段跑飞成「中国官帽＋灰发老人脸」，6.9s／8.2s 那张根本不是 P1，却在 attempt 3 被 QC 接受。
- 模糊带**没有**污染画面（无用户投诉的蜂窝状图案），左下幻影 chibi 仍 0/12 ⇒ 这两项不是本轮造成的。
- silent 对嘴只是「跨过一次阈值」：seg1 0.287→0.253（仍不过）、seg2 0.229→0.233（反而略差）、seg3 0.213→0.260（明显变差）⇒ 噪声级，**不算改善**。

**判读（为什么反而更差）**：「plate 抑制范围越广越好」被实机否定。躯干一糊，plate 只剩姿态、手和一点背景色，H3 失去「这个位置的人穿什么颜色／廓形」的唯一锚点，于是服装与头发改由 **V1 原片**（粉黑 cosplay 演员）继承；head-only（policy 66）保留躯干色块，反而让最干净的 seg2 把 P1 整套衣柜带进来。**衣柜的主战场不在 plate 抑制**，而在（i）identity sheet 衣柜面板本身够不够大（`character_identity_sheet.py` `OUTFIT_VIEW_SHARES["medium"]` 现 0.62）、（ii）三个 attempt 全不过时 QC 按什么排序取件——现在按 silent risk 挑「最不急」，不是按 `target_reference_similarity` 挑「最像 P1」，那个官帽老人就是这样被选中的。

**处置**：`CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE` 默认 `blur` → **`off`**（机制、合并条款与全部测试保留，实验时用 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur` 手动开），`SMART_RENDER_POLICY_VERSION` **67 → 68**。

### Round 25：policy 66 读帧量化——头套／假发 8–9/12 帧已被 P1 取代，但衣柜只有 3–4/12 ⇒ 方向正确、范围只到肩膀（2026-10-27 08:08 读帧，seeds 923000127＝policy 65／923000227＝policy 66，**不改源码**）

**做了什么**：对两条已送达的 master 各抽 12 帧，每个 seed 出四张对照 grid（`master`／`wardrobe`／`head`／`bottom-left` 四个观察窗），另存基准 `r25_p1_reference.png` 与源片对照 `r25_v1_source_grid.png`。全部落在 `_dsh_verify_9\round25\frames\`，评级 log `_dsh_verify_9\round25\logs\grade_round25_policy66.log`。**纯读帧，没碰 ComfyUI、也没碰 Qwen。**

**量化结果（policy 66 三段 QC，取自同一 log）**

| 段 | `target_reference_similarity` | silent 口型 result/source | 判定 |
| --- | --- | --- | --- |
| seg0 0–4.288 s | 0.5967 | 0.287 / 0.063 | 失败（attempt 2 `retry_fresh_seed`） |
| seg1 4.288–8.576 s | 0.6211 | 0.229 / 0.071 | 失败（attempt 3） |
| seg2 8.576–12.864 s | 0.5686 | 0.213 / 0.080 | 失败（attempt 1） |
| MEAN | **0.5955** | — | 三段都被 QC 拒但都 `complete` |

- **头部**：policy 66 有 **8–9/12 帧**源片头套／假发被 P1 的卡通光头取代（policy 65 只有 7/12），且三段 similarity 相对 policy 65 **单调上升**（0.5685 → 0.5955）。
- **衣柜**：只有 **3–4/12 帧**整套换成 P1（两版评级脚本对 seg2 其中一帧判定不同，故给区间）——只有最干净的 seg2 把整套衣柜带过来。
- **背景**：左下幻影 chibi **0/12**、无用户投诉的蜂窝状图案 ⇒ 这两项不是 policy 65/66 造成的。

**判读**：plate 抑制（只糊头部）**方向已被证明有效**，但作用范围**只到肩膀** ⇒ 直接催生 Round 26 的「头冠到臀部」衣著带。

**状态界定**：本轮**不改源码**，属判读轮；结论是 policy 66「视频已实机验证＝部分有效」（头 ✅、衣柜 ✗、silent ✗）。

### Round 24：prompt 说「plate 已削弱」但 plate 其实是原图——两道闸门对齐（2026-10-27 03:55 修码，07:38 实机 seed 923000227，policy 65→66，**实机＝方向正确、只修好一部分**）

**根因（读 round 23 真实 worker log 得证，不是猜）**：`logs\staged_model_driver\preview_923000127_1793041137147319300.jo_20261027_030359.log` 里 `MEDIUM-SHOT SILENT MOUTH REINFORCEMENT` ×19、`COMPLETE WARDROBE REPLACEMENT` ×19，但 `SOURCE PLATE FACE BLURRED` ×0、`identity_suppressed` ×0，三段上传的 plate 档名都**没有** `identity_suppressed` token。也就是说 prompt 宣称拿到一张削弱过的源片，实际送进 Relay 的是**一帧原封不动的 V1**。原因是两侧阈值脱节：Relay 引擎早已把中景静音放宽成 `SILENT_REINFORCEMENT_MIN_BOX_AREA = 0.050` / `SILENT_REINFORCEMENT_MIN_BOX_HEIGHT = 0.25`（`character_swap_engine.py:179-180`），而 Studio 侧的**plate 抑制闸门**还写死 `0.12 / 0.35`。本项目 R1 框 `[0.35,0.15,0.65,0.45]`（面积 0.09／高 0.30）正好落在中间 ⇒ 只发文字、不改图。

**改了什么（源码）**
- `director_cut_studio.py`：`character_swap_engine` 导入块补上 `SILENT_REINFORCEMENT_MIN_BOX_AREA` / `SILENT_REINFORCEMENT_MIN_BOX_HEIGHT`；新增 `_medium_silent_blur_min_framing(environ=None) -> (area, height)` 与快照常数 `CHARACTER_SWAP_MEDIUM_SILENT_BLUR_MIN_AREA` / `_HEIGHT`（紧跟 `CHARACTER_SWAP_IDENTITY_MASK_MODE` 块）。`_pass_spec_medium_silent_blur_rows()` 的判定改读该常数，不再写死 0.12／0.35。
- 可调／可回滚：`H3_CHARACTER_SWAP_MEDIUM_SILENT_MIN_AREA`、`H3_CHARACTER_SWAP_MEDIUM_SILENT_MIN_HEIGHT`。**逐项**容错——单个值不可解析或越界时只回退该组件到引擎档位；成对设 `0.12 / 0.35` 即完全恢复修复前行为。
- **版本**：`SMART_RENDER_POLICY_VERSION` **65 → 66**（`director_cut_studio.py:656`、`smart_render_worker.py:86` 同步）。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。

**测试**：`testing\test_character_swap_closeup_gates.py` 新增 4 项（默认值＝引擎档位、knob 可回滚、round-23 那个 0.09 框现在会拿到头部模糊带、同一框同时命中身份抑制闸门），并把旧断言 `…framing_rows_but_no_silent_rows` 改写为「发言者 spec ⇒ 有 framing 行、无 silent 行」。`test_character_swap_closeup_gates`＋`test_identity_sheet` **Ran 82 tests OK**；`test_character_swap_engine` **Ran 69 tests OK**；全量套件 **Ran 866 tests OK (skipped=10)**（`_dsh_verify_9\round24\logs\suite_policy66_medium_silent_gate.log`）；改动文件 `py_compile` 全过。

**离线 A/B 证据（`working\_round24_policy66_plate_diff_20261027.py` → `_dsh_verify_9\round24\logs\policy66_plate_diff.log`）**：新 Job `preview_923000227_1793043950705503000.job.json`（policy 66）三段 plate 全部变成 `…_v1_relay_…_identity_suppressed_…_silent_*.mp4`，每条 pass 行 `strategy=medium_silent_listener_identity_suppressed`、`identity_sheet_medium_silent_rows 1`，prompt 里出现 `SOURCE PLATE FACE BLURRED — AUTHORITATIVE`；而**参考图 bytes 不变**（同一片 `…_identitysheet08_uhip_a0066_v7.png`，coverage 0.5259，`reason "cached"`），prompt_chars 只从 11966 变成 11901 ⇒ 这是只换 plate 的单变量实验。

**实机结果（seed 923000227，policy 66，2026-10-27 07:38，manifest `…1793043950705503000.manifest.json`）**

plate 真的换掉了（不是只写 prompt）：manifest `identity_suppressed` 出现 18 次、每段正好 1 个 suppressed plate 上传；新 worker log `preview_923000227_…_073804.log` 里 `SOURCE PLATE FACE BLURRED` ×11、`identity_suppressed` ×25，而对照 log（923000127）两个都是 **0**。三段 `attempts_used=3` 全部 `complete`。

读帧（探针 `working\_round25_blackshirt_grade_20261027.py`，输出 `_dsh_verify_9\round25\frames\`，log `…\round25\logs\grade_round25_policy66.log`；每段 4 帧＝12 帧，另存 wardrobe／head／bottom-left 三种裁切与 V1 对照）：

| 项目 | policy 65（923000127） | policy 66（923000227） |
| --- | --- | --- |
| 脸的归属／媒介 | 12/12 是 P1 卡通脸 | 12/12 仍是 P1 卡通脸，没真人化、没变老人 ⇒ **没退步** |
| 左下第二个小人 | 0/12 | **0/12 ⇒ 视频已实机验证仍保持消失** |
| 粉红双马尾假发＋猫耳 | 12/12 仍在 | seg0 4/4 消失、seg2 4/4 消失、seg1 4/4 仍在 ⇒ **8/12 已实机消失** |
| 衣柜＝P1 | 0/12（全片 cosplay） | seg2 4/4 出现 P1 的黑背心白滚边＋蓝衣＋**黄格纹袜＋黑鞋**；seg0／seg1 仍 cosplay（袖子还留粉红条纹）⇒ **4/12 已实机换上** |
| `target_reference_similarity` 平均 | 0.5685（0.584／0.601／0.560） | **0.5955（0.597／0.621／0.569）＝三段全部上升** |
| silent listener QC | seg2 通过，seg1／seg3 `silent_mouth_excessive_articulation` | **三段都未过**（0.287／0.229／0.213 vs 源 0.063／0.071／0.080）⇒ 中间段由通过变不通过，**这项实机变差** |

**结论**：闸门对齐是**有效方向**——头髮／头套这种「头部像素权威」8/12 直接被 P1 取代，最干净的 seg2 甚至整套衣柜＋袜子＋鞋子都跟着换成 P1，三段相似度单调上升；但 seg0／seg1 的**躯干 cosplay**（粉黑条纹＋网眼＋飘带）仍压过 prompt，且 silent 对嘴反而三段都超标。衣柜问题**部分修复**，尚未全绿。

**状态**：衣柜／假发是否跟过来＝**已实机验证：部分修复**（头套 8/12 消失、衣柜 4/12 换上、相似度三段都涨）；躯干 cosplay（seg0／seg1）与 silent 对嘴＝**已实机确认仍存在**。下一个单一变量：把 `WARDROBE_GATES` 扩到 `medium_silent` 并对 cartoon P 启用 `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE=blur`（只软化衣物带、保留色度，绝不 `blur_desat`）。

### Round 23 实机跑成功一张：第二个小人消失＝medium 单脸 sheet 有效；衣柜仍来自源 plate＝下一个变量（2026-10-27 03:26，policy 64→65）

**实机状态（这是 round 23 第一次真正跑成的 take）**：seed **923000127**、manifest `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923000127_1793041137147319300.manifest.json`、`render_policy_version 65`。三条验收口径全部命中：`identity_sheet_preset: 8`、`identity_sheet_framing_threshold: 0.18`、`identity_sheet_framing_medium_rows: 1`，三段上传的都是 `image_137_4bd41c9e363a8278_nobg_identitysheet08_uhip_a0066_v7.png`，`identity_sheet_head_coverage 0.5259`（源图 0.214413）、`reason "cached"`。驱动走 `staged_model_driver.py run`：unload-qwen `verified_clean`（24.7→2.56 GB）→ wait-comfy → 三段渲染 → `comfy-free ok` → Qwen 由 tray 载回。

**逐帧 grading（`working\_round23_blackshirt_frames_20261027.py`，帧图 `_dsh_verify_9\round23\frames\`，每段 4 帧＝12 帧）**

- ✅ **round 22 缺陷②「画面左下角多出一个 chibi 小人」已实机消失**：12/12 帧的下半左区都没有第二个角色（round 22 是 4/12）。单脸 sheet 把第二张脸从参考图里删掉之后，模型不再画第二个小人 ⇒ **「medium 单脸 sheet 修掉二次小人」＝视频已实机验证成功**。
- ✅ 脸的归属没退步：12/12 帧都是 P1 的卡通脸（秃头＋三根头发＋圆眼镜＋翘胡子＋大圆鼻），媒介仍是卡通，没有真人化，也没有变老人。
- ❌ **round 22 缺陷①「衣柜来自源 plate」仍在，12/12 帧**：身体仍是源片那套粉黑条纹＋网眼＋飘带的 cosplay，不是 P1 的黑背心＋蓝短裤＋黄格纹袜。`target_reference_similarity` 只有 0.560–0.601（QC 三段只 seg2 `passed=true`）。
- ❌ **粉红双马尾假发＋猫耳也保留**：P1 是秃头，头套属于源演员，和衣柜是同一个根因。
- ⚠️ silent listener：seg1／seg3 QC 判 `silent_mouth_excessive_articulation`（similarity 0.584／0.560），seg2 QC 通过（0.601）。

**根因（读源码＋manifest＋worker log 得出，不是猜）**：这条 Shot 的 R1 框 `[0.35,0.15,0.65,0.45]`（高 0.30／面积 0.09）**低于所有身份抑制闸门** ⇒ 整轮 worker log 里没有任何 suppression 记录，送进 Relay 的是**一帧原封不动的 V1 plate**。H3 在 plate 未被削弱时只会换脸：头发和衣服的形状＋色度是它最强的条件来源。`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` 这个"把衣服那条带软化"的开关**已经实现但默认 `off`，而且只在 `dominant`／`head_dominant` 闸门内生效**，对 0.09 的小框永远不会触发。prompt 侧没问题：`prompt_chars 11966 / char_budget 12320`、`dropped_tail_clauses []`，`COMPLETE WARDROBE REPLACEMENT — MANDATORY` 与 `WARDROBE…AUTHORITATIVE` 两条都在送出去的 prompt 里 —— 文字条款在 plate 完整时压不过像素。

**改了什么（源码，policy 64→65）**

- `director_cut_studio.py` 的 `_compiled_character_swap_window_job()` 过去只把两个 coverage 键白名单进 Character Swap pass 记录 ⇒ **布局决定永远进不了 Job／manifest，round 23 根本无法验收**。新增模块常数 `IDENTITY_SHEET_DECISION_KEYS`（11 个决定字段）与静态方法 `_identity_sheet_decision_rows(pass_spec)`（只跳过 `None`，preset 0／outfit_view `""` 都要留），pass 行改成整体转发；决策循环也改成读同一常数，不会再和序列化脱节。
- **版本**：`SMART_RENDER_POLICY_VERSION` **64 → 65**（`director_cut_studio.py:639`、`smart_render_worker.py:77` 同步）。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。
- **测试**：`test_identity_sheet` 新增「决定行序列化后仍在」「窗口 Job 转发整行」；`test_identity_sheet`＋`test_character_swap_closeup_gates`＋`test_smart_render_worker` `Ran 130 tests … OK (skipped=1)`；全量套件 `Ran 862 tests … OK (skipped=10)`（`_dsh_verify_9\round23\logs\suite_policy65_decision_row.log`）；`py_compile` 全过。
- **新的离线 Job 构建器**（用户选的路径 b）：`working\_build_blackshirt_preview_20261027.py <SEED> [PRESET] [MEGAPIXELS]` 直接在进程内载入项目、设 `identity_sheet_enabled/preset`、用 `window._build_smart_render_job(request_kind="preview")` 编出真 Job，逐条打印 `identity_sheet_*` 并强制验收（preset 8／阈值 0.18／`framing_medium_rows ≥1`／sheet 名含 `identitysheet08`），不合格 exit 1。

**下一个单一变量（待用户批准实机）**：衣柜／假发的共同根因是 plate 未被削弱。最小改动＝让 wardrobe band 不再只服务近景闸门：cartoon P（`live_action_adaptation=false`）＋框面积 ≥0.06 时也启用 `blur`（保色不灰化；round 17 的 S4 四个 take 已实测 `blur_desat` 会灰化出一个灰色衣服）。对照组仍是 seed 923000127，除 band 以外全部不变。

### Round 23 卡在同一个陷阱两次：找到真元凶＝Studio 存盘会吃掉 `design_ai.env` 旋钮；布局授权改放进 Identity Sheet 页面（2026-10-27 03:05）

**实机状态：round 23 的单一变量实验至今一次都没跑过（不是失败，是没跑）**。用户回报「跑完了」，磁盘上确实多了 02:27:00 的新 take（`preview_197804093403812434_1793037707269261700.manifest.json`，policy 标 64、0.5 MP、12.86 s、3 段、每段 3 次尝试），但它上传的 sheet 仍是 `image_137_4bd41c9e363a8278_nobg_identitysheet00_a0066_v7`、`identity_sheet_head_coverage 0.3907` —— 与 round 22 **同一个布局（preset 0＝两张脸）**。查到的原因有两条，第一条是这轮才现形的**真元凶**：`design_settings.save_design_settings()` 用 `KEYS` 重新生成整个 `design_ai.env`，凡是自己不认识的行**整行删除**。磁盘上该文件 mtime 01:39:47、内容里已经没有 `H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT` —— 任何一个 settings 对话框点保存都会把实验开关吃掉，重启多少次都不会生效（这也解释了它为什么"写过又消失"）。第二条才是上一轮怀疑的老问题：Studio 进程 00:24:33 启动，早于旋钮写入，import 时常量仍是 0.0。顺带纠正上一轮的推断错误：manifest 缺 `identity_sheet_preset*` 字段**不能**证明进程是旧的，因为 pass 记录的过滤器 `value in ("", 0)` 会把 preset 0（出厂布局）当成"没有值"丢掉 —— round 23 之所以无法验收，正是这个过滤器造成的。

**改了什么（源码）**

- **`design_settings.py`：advanced 键不再被吃掉。** 新增 `_advanced_design_env_lines()`，`save_design_settings()` 先读出页面不认识的赋值行（保持原顺序、同键取最后一次），再原样附在页面键之后；页面自己拥有的键仍由页面决定，残留的同名重复行不会反过来遮蔽它。
- **`director_cut_studio.py`：把授权搬进 GUI。** 在 Identity Sheet 页面选 **"Head + neck-down figure (single face)"**（preset 8）时，framing 闸自动以新常数 `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_HEIGHT_WHEN_CHOSEN = 0.18` 生效：框高 ≥0.18 且面积 ≥0.04 的 medium Shot 拿到**单脸＋齐胯衣柜面板**，更矮的宽景仍保留整身面板（鞋子上过镜就该留在参考图里）。preset 是实例状态、按 Preview 时现读 ⇒ **既不需要 `design_ai.env`，也不需要重启 Studio**，"没重启＝白跑一轮"这个陷阱从根上拆掉。回滚＝把该常数改 0.0。
- **manifest 会自己交代布局。** pass 记录过滤器改成只跳过 `None`（`identity_sheet_preset = 0`、`identity_sheet_outfit_view = ""` 都是有意义的值），并新增 `identity_sheet_framing_threshold`。以后判断一次 take 用了哪个布局，读 manifest 就行，不必再从上传文件名反推。
- **测试**：`test_design_engine` 新增「存盘保留 advanced 键、重复行不遮蔽页面键」；`test_character_swap_closeup_gates` 新增「选 preset 8 就给 hip 裁切」「宽景选 preset 8 仍保留整身面板」；`test_identity_sheet` 新增「preset 0 也必须进 pass 记录」。三模块 `Ran 216 tests … OK (skipped=2)`；全量套件 `Ran 860 tests … OK (skipped=10)`（见 `_dsh_verify_9\round23\logs\suite_policy64_advanced_keys.log`）；`py_compile` 通过。当时 ComfyUI 只读检查 `/queue` running 0／pending 0，GPU 空闲，未提交任何渲染。

**验收口径（下一轮，缺一律算无效 A/B、不计入 grading）**：manifest 必须出现 `identity_sheet_preset: 8`、`identity_sheet_framing_threshold: 0.18`、`identity_sheet_framing_medium_rows ≥ 1`，且上传的 sheet 文件名带 `identitysheet08…_uhip`（离线 coverage ≈0.526）。操作只要两步：Identity Sheet 页面选那个单脸布局 → Save → Preview 0.5 MP。

### Round 22 实机：脸已修好，衣柜／二次小人仍在 → round 23 单一变量实验：medium 构图改用单脸 sheet（2026-10-27，policy 63→64）

**01:35 增补（旋钮已装上 + 拆掉两处测试耦合）**：用户回报「已按 Preview」，但 black-shirt 磁盘上最新 take 仍是 01:02:50 的 **policy 63** manifest（policy 64 代码 01:17 才落地），ComfyUI 只读检查 `/queue` 全空、`vram_free 26.07 GB` ⇒ **policy 64 零实机 take**。旋钮已写进 `design_ai.env`（`H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT="0.18"`，带注释，删行即回滚）；knob 在 import 时读取，所以**必须完全关闭并重启 Studio** 才生效（00:2x 启动的旧进程读不到）。顺带修掉两处「单元测试其实依赖这台机器的 `design_ai.env`」的耦合：threshold 解析抽成 `_identity_sheet_framing_medium_min_height(environ)`（空 mapping ⇒ 出厂 0.0，import 快照 ⇒ 常量确实跟随 knob），`test_identity_sheet._fake_studio()` 补上真实的 `_pass_spec_framing_medium_rows`（门槛为 0 时调用点被短路，所以 policy 64 当天全绿也没暴露这个 stub 缺口）。`test_character_swap_closeup_gates` **30 → 31**；带 knob 的 7 模块 `Ran 214 tests … OK (skipped=1)`；全量套件带 knob `Ran 856 tests … OK (skipped=10)`（log `_dsh_verify_9\round23\logs\env_knob_0p18_regress3.log`、`suite_policy64_knob_on.log`）；`py_compile` 5 个源码模块＋2 个测试模块全过。**状态不变：单脸 medium sheet 仍是源码已修复＋离线绿＋落板图人眼确认，尚未实机验证。**

**实机确认（round 22，policy 63／engine v7，用户按 Preview，0.5 MP／576×864／12.86 s／3 段）**：manifest `preview_5946797166534131206_1793032633899288000.manifest.json` 记录实际上传的 sheet 是 `image_137_4bd41c9e363a8278_nobg_identitysheet00_a0066_v7.png`，`identity_sheet_head_coverage 0.3907`（源图 0.214413），三段各 3 次尝试，`prompt_chars 11966 / char_budget 12320`、`dropped_tail_clauses []`（衣柜条款与单实例条款**都进了 prompt**）。逐段读帧（探针 `working\_round22_newvideo_frames_20261027.py`，帧图 `_dsh_verify_9\round22\round22_policy63_v7_master_grid.png`）：

1. ✅ **脸整张复制成功 —— 根因 O 已在实机关闭**：三段都画出完整五官（秃顶＋三根头发、额头纹、圆框眼镜、大鼻、八字胡、张嘴、下巴），没有「变老人」，卡通媒介保留，身份＝P1。
2. ❌ **衣柜仍来自源 plate**（粉红黑条纹袍＋缎带，而不是 P1 的黑背心＋蓝短裤＋黄格纹袜＋球鞋）。prompt 一个字都没丢 ⇒ **文本已饱和，杠杆只能在视觉上**。
3. ❌ **新缺陷⑧ —— 画面长出第二个小人**：12 帧里 4 帧（t≈0.4／4.6／8.9／10.1，正好每段第一帧）左下角出现一个穿 **P1 真衣柜**的 chibi 小人。也就是说模型把 body 面板读对了，却把它当成**第二个实例**放进场景（`identity_sheet_contract` 早就禁止「second, smaller or partial copy」）。
4. ❌ 源片粉红假发在 seg0／seg2 保留（头发／头饰归属条款缺口）。
5. ❌ **Silent Listener 仍对嘴**：三段 `failure_class: silent_mouth_excessive_articulation`（result_motion 0.196／0.218／0.262 vs 上限 0.055）。
6. ⚠️ QC 的 `target_reference_similarity`（0.588／0.614／0.554）与用户 grading 不相关 ⇒ 评分要看「脸有没有整张复制」「衣服是不是 P1 的」，不要看这个数。

**离线定位缺陷⑧／②的开关**：round 22 的 R1 框是 `[0.35, 0.15, 0.65, 0.45]`（h 0.30／area 0.09）。它既过不了 close-up 闸（要 area ≥0.72 或 h ≥0.75），也过不了 medium-silent 闸（要 h ≥0.35 且 area ≥0.12）⇒ **这个 Shot 从来没拿到「改成单脸布局」的授权**，于是提交 preset 0＝两张脸＋全身。离线把同一条 Shot 的三种布局全部重排（探针 `working\_round23_preset8_medium_sheet_20261027.py`，落板图 `_dsh_verify_9\round23\sheets\`）：preset 0 有**两张脸**（coverage 0.3907，衣柜只占下半一小块）；preset 8＋hip 裁切只有**一张脸**，下半格是齐胯的衣柜（coverage 0.5259）；preset 8＋chest 裁切衣柜断在白腰带**上方**（0.6023，正好缺掉蓝短裤＋黄格纹那些可辨认的行，与 round 17 结论一致）。

**改了什么（源码）**

- **布局跟着构图走**：新增 `_pass_spec_framing_medium_rows()` —— 框高 ≥ 门槛且面积 ≥ `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_AREA = 0.04`、且没被 close-up 闸接管时，该 Shot 也用 preset 8＋hip 衣柜面板。**刻意不看 `performance_mode`**：medium-silent 闸要静音是因为它在保护嘴巴，而这里保护的是「画面容不容得下第二个人」。
- **旋钮** `H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT`（**默认 0.0＝关闭**，0–1 夹取）：默认行为与 policy 63 完全相同，0.18 是本轮要试的单一变量。
- **`design_ai.env` 现在能驱动 GUI Preview**：`DESIGN_ENV_RENDER_KNOBS` allowlist（wardrobe band、identity mask、sheet outfit view、closeup preset、medium framing 高度）＋ `apply_design_ai_env_render_knobs()` import 时安装；真实环境变量优先、注释与非 `=` 行跳过、非 allowlist 的键忽略 —— 否则按 Preview 的导演永远看不到这些开关。
- **把布局决定写进 manifest**：pass 记录新增 `identity_sheet_preset`／`_preset_requested`／`_preset_forced`／`identity_sheet_outfit_view`／`_outfit_view_override`／`identity_sheet_closeup_gate_rows`／`identity_sheet_medium_silent_rows`／`identity_sheet_framing_medium_rows`。round 22 只能从上传文件名反推布局，下一轮直接读 manifest。
- **版本**：`SMART_RENDER_POLICY_VERSION` **63 → 64**（`director_cut_studio.py`／`smart_render_worker.py` 同步）—— 旋钮开启时提交的参考图会变，policy 63 的 sheet／manifest 不能再复用。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。

**测试**：`test_character_swap_closeup_gates` **20 → 30**（新增 `DesignEnvRenderKnobTests` 3 项：allowlist 安装／真实 env 优先／缺档空装；`IdentitySheetFramingLayoutTests` 6 项：round-22 框逐字回放证明旧闸全部漏判而 framing 闸命中、sliver／远景／close-up／畸形输入不误触发、门槛非法不炸、默认 0.0 保持 preset 0 两张脸、门槛 0.18 时换成 preset 8＋medium、close-up 旧行为不变）。同批相关模块 `test_identity_sheet`／`test_character_swap_engine`／`test_character_swap_background_extra`／`test_character_swap_silent_audio`／`test_smart_render_worker`／`test_smart_render_qc_advisory` **183 全绿（skipped=1）**；`director_cut_studio`／`smart_render_worker`／`character_identity_sheet`／`character_swap_engine`／`identity_sheet_page`／测试模块 `py_compile` 全过。全量套件 `Ran 855 tests … OK (skipped=10)`（上一基线 845 → +10，log `_dsh_verify_9\round23\logs\suite_policy64_framing_sheet.log`）。

**状态界定**：round 22 的**脸部整张复制＝已实机验证成功**；medium 构图改用单脸 sheet ＝ **源码已修复＋离线测试绿＋三张落板 sheet 人眼确认**，**尚未实机验证**；衣柜漂移、二次小人、粉红假发、silent 对嘴 **仍未修复**。下一轮单一变量：`design_ai.env` 写 `H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT=0.18` ＋ 重启 Studio ＋ Preview，其余条件（`source_identity_strategy: original`、同一条 timeline）不动。

### Round 21 后续：Identity Sheet 的脸面板被切在眼睛 —— head-run 引擎 v7 ＋ 脸面板填满格子 → 源码已修复＋离线绿＋落板图已看过，实机未跑（2026-10-27）

用户对 `a_cartoon_character_with_a_black_shirt_and_yellow_pants` 单角色片逐镜 grading：S1／S4／S6／S8「衣服完全不像参考图」、S3／S7／S10／S11「角色变成老人」（自评相似度 20 %–60 %），只有 S5（80 %）勉强可接受。离线读 frame 后定位到问题不在 prompt，而在**送进 H3 的那张 Identity Sheet 本身**：脸面板是从眼睛以下才开始画的。

- **根因 O —— 举手把「最宽行」当成肩线，脸面板被切成一条横带**：`estimate_head_box` 量的是整行不透明范围。black-shirt P1 右手举在头侧（`x 204-250`、自 `y 76` 起），所以肩线落在 armpit，v6 的 head box = `(32, 5, 252, 92)`（220×87，宽高比 2.53，`MAX_HEAD_BOX_ASPECT = 2.6` 挡不住）。后果有两层：① 脸面板里没有眉眼／眼镜／鼻子／胡子／下巴，H3 只能自己发明五官 ⇒ 「变老人」；② 衣柜面板的起点就是 `head_bottom`，误差直接继承 ⇒ 「衣服完全不像」。
- **修法：head-run 引擎 v7（`IDENTITY_SHEET_ENGINE_VERSION` 6 → 7）**：头改成「与颅骨轴**相连**的那一段不透明行程」，由 `_head_run_walk()`（回传 `(seed_row, walked)`）与 `_head_run_landmarks()`（`skull_locked`）量出来，永不等于最宽行；参数 `CROWN_SEED_SHARE = 0.10`、`HEAD_RUN_BRIDGE_SHARE = 0.12`、`HEAD_RUN_MAX_AXIS_SHIFT = 1.10`、`HEAD_SEARCH_SHARE = 0.62`、`HEAD_RUN_SHOULDER_VS_SKULL = 1.05`、`HEAD_RUN_SHOULDER_VS_NECK = 1.35`、`HEAD_HEIGHT_MIN_SKULL_SHARE = 1.10`。完全没有 silhouette（不透明满幅背景）时退回**比例 fallback**：peak row 已经是最宽行且找不到肩线 ⇒ 取 0.34×主体高、宽 ≤ 1.15×H、居中，不再吐一条扁带。black-shirt P1 实测 `(37, 1, 172, 153)`（135×152，宽高比 0.89）：下巴进框、袖管出框；P4／P5／P6 与 v6 判定一致，没有回归。
- **v7 的副作用 —— 正确的 skull 框在自己格子里被 letterbox**：真实 skull 是「高 > 宽」，head 格通常是「宽 > 高」，而 `_fit_into_cell` 一律 contain-fit 不拉伸 ⇒ 脸在格子内又缩一次，`head_coverage` 从 0.304 掉到 **0.194**，低于 `character_swap_engine.IDENTITY_SHEET_MIN_HEAD_COVERAGE = 0.22`，两条既有测试当场变红。新增 `_grow_head_crop_to_cell()`：用 skull 周围**真实像素**把 crop 长到能填满格子 —— 向下占 `HEAD_PANEL_DOWNWARD_GROW_SHARE = 0.75`（多出的是脖子／肩／领口，正是 Relay 必须重画的部分，且下巴不动）、向上 25 %、横向以 `HEAD_PANEL_MAX_GROW = 1.45` 封顶，绝不 upscale、绝不越过 silhouette。
- **脸必须留在面板正中**：`_balanced_growth_split()` 把横向多出来的列**平分**，只在某一侧真的顶到画框时才偏向另一侧；剩下那一列的奇偶由 `_column_artwork_scores()` 的逐列覆盖率决定（哪边带角色像素就往哪边长）。
- **顺手修掉本轮刚写出来的一个 bug**：`_balanced_growth_split()` 把传入的 `(left, top, right, bottom)` 当 `(left, right)` 读，`span[1]` 是 top 而不是右边界 ⇒ 右侧永远算出「没有空间」，脸被整块推到画框最左。waving fixture 实测 `(0, 1, 197, 155)`（脸贴左边），改读 `span[2]` 之后是 `(7, 1, 204, 155)`，脸中心 105.5 对 skull 中心 105。
- **真材实料 9 张 cast 全部变好**（探针 `working/_headpanel_fill_probe_20261027.py`，log `_dsh_verify_9/round21/logs/headpanel_fill_v71_probe_20261027.log`，落板图 `_dsh_verify_9/round21/sheets_v71/`）：black-shirt P1 `coverage 0.2435 → 0.3907`、脸面板 crop `(32, 5, 252, 92) → (7, 1, 203, 153)`，右边界 203 仍在袖管 204 之外；`..._yellow_shirt_9` P4 0.5895→0.8544、P5 0.3153→0.4314、P6 0.1413→0.4297，其余 5 张同样上升。人眼已读过 black-shirt v7 落板图：脸面板完整含 crown → 眉毛 → 圆框眼镜 → 眼睛 → 鼻子 → 胡子 → 张嘴 → 下巴，右下角只有一小条蓝袖。
- **版本**：`SMART_RENDER_POLICY_VERSION` **62 → 63**（`director_cut_studio.py`／`smart_render_worker.py` 同步）—— 提交的**参考图本身**变了，policy 62 的 sheet、manifest 与候选一律作废。VERSION 维持 `0.3.8-alpha.3`，Project Format 维持 29。
- **测试**：`test_identity_sheet` **39 → 42**（新增 waving-arm 三项：head box 必须排除袖管且含下巴、宽高比落在 0.5–1.35；脸面板必须长大但不超 1.45×、脸居中误差 ≤ 15 % 面板宽、`head_coverage ≥ 0.22`、右边界不吞袖管；无平坦背景时比例 fallback 落在 0.28–0.40 主体高且宽高比 ≤ 1.2）。`test_character_swap_engine`／`test_character_swap_closeup_gates`／`test_character_swap_background_extra`／`test_character_swap_silent_audio` 合计 **105 全绿**；引用 policy 版本符号的 `test_storyboard_segment_mapping` 绿；全量套件 `Ran 845 tests … OK (skipped=10)`（log `_dsh_verify_9/round21/logs/suite_policy63_headpanel_v7.log`）。`character_identity_sheet`／`character_swap_engine`／`smart_render_worker`／`director_cut_studio` `py_compile` 通过。
- **状态界定**：head-run 引擎 v7、脸面板填满、`span[2]` 修正 ＝ **源码已修复＋离线测试绿＋落板 PNG 人眼确认**。**尚未实机验证** —— black-shirt 三段 Character Swap 在 policy 63／engine v7 下一条都还没提交，「变老人是否消失」「衣服是否真的换成参考图衣柜」仍未人眼读过新帧。
- 新增离线工具（`working/`）：`_wavetest_probe_20261027.py`（waving-arm 合成 fixture，逐项打印 head box／面板 crop／coverage）、`_headpanel_fill_probe_20261027.py`（9 张真 cast 的 v6→v7 coverage 对照与落板图）。

### Round 20–21 实机：背景蜂窝、silent listener 对嘴、衣柜／年龄漂移、尾条款预算重排 → 源码已修复＋离线绿，实机部分通过（2026-10-26）

用户新片（`a_cartoon_character_with_a_black_shirt_and_yellow_pants` 单角色片＋`..._yellow_shirt_9` 十分镜片）回报 4 类缺陷，逐条定位到源码并修复；VERSION 维持 `0.3.8-alpha.3`，Project Format 维持 29，Smart Render Policy **61 → 62**、Identity Sheet 引擎维持 v6。

- **修因 L —— 背景长出蜂窝／龟裂状图案**（S2／S4／S6／S8 同一次回报）：源 plate 上细小高对比颗粒在 Relay 缩放时被丢弃，模型自行补「装饰纹理」，且只在人物框之外的背景区域出现。新增人物框面积闸门 `BACKGROUND_EXTRA_MAX_BOX_AREA = 0.045`＋`BACKGROUND_EXTRA_PROMINENCE_RATIO = 2.0`（框越小 ⇒ 背景越可能是模型自造，越必须下禁令），并在框面积 ≥ `PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA = 0.060` 时发射 `NO INVENTED TEXTURE OR PATTERN — MANDATORY`；该条款与 `close_up_medium_reinforcement` 一起被列入**永不丢弃**白名单，长度守卫不能再牺牲它。
- **修因 M —— Silent Listener 明明设了却还对嘴／以及反过来误判**：旧 QC 用人物框的**均值**逐帧差，一次眨眼或一次身体晃动就能把 7 个嘴部取样点（`0.12…0.88`）的中位数淹没；同时旁观者（`source_identity_retained=true`）也被当作判定对象。改为：① 改用 `robust_temporal_frame_motion` 的**中位数**；② 双重阈值 —— 必须同时超过绝对上限 `max(0.055, source×1.5+0.012)` **和**上半脸参照上限 `upper_face_motion×1.25+0.02`，即「只有嘴比眉眼动得多才算说话」；③ 左右 plate 条几乎不动（`plate_motion < 0.010`）时该行改判 `audit_region_ambiguous`，全行模糊 ⇒ 不再记 failed 并回报 `plate_strip_ambiguous`；④ 目标相似度失败同样降级为 `target_similarity_ambiguous`；⑤ 旁观者行改 `advisory` 且不再进入 `retention_score`。审计行新增 `source_motion_mean`／`result_motion_mean`／`upper_face_motion`／`upper_relative_motion_limit` 便于事后复核。
- **修因 N —— 衣服完全不像参考图／角色变成老人**（S3／S5／S7／S10／S11）：衣服条款原先躲在 close-up 分支里，medium／raw framing 一条都不发。新增无条件 `COMPLETE WARDROBE REPLACEMENT — MANDATORY`，以及 `SOURCE COSTUME BELONGS TO THE ERASED ACTOR — AUTHORITATIVE`（明说旧戏服属于被擦掉的演员，不能留在新角色身上）；新增 `APPARENT AGE LOCK — MANDATORY`（禁止「漂成更老的人」）；close-up 另补 `CLOSE-UP FACE ANCHORING` 与 `CLOSE-UP MEDIUM REINFORCEMENT`。
- **缺陷⑦ —— 12 320 字预算又被尾条款挤爆**：新条款使 sheet＋近景 silent 组合达到 13 072 字，守卫只能丢条款，于是刚写好的 silent 条款年年被丢。把尾部可丢条款改为显式优先级 `CHARACTER_SWAP_TAIL_DROP_RANKS`（`close_up_silent_mouth 1` → `medium_shot_silent_mouth 2` → `source_costume_leaves_plate 3` → `close_up_sheet_crop_lock 4`），并把重复表述压缩，尾部实测 −301 字（13 072 → 12 771）。实测发出的 sheet＋近景 silent = **12 245 字**，只丢 `close_up_silent_mouth`，crop lock 保留。
- **ComfyUI 环境阻断（新视频 R2V 必崩，非本项目代码）**：`prompt id cd1a505b-…` 在 `SamplerCustomAdvanced` 报 `The size of tensor a (3) must match the size of tensor b (2)`，抛点在 `custom_nodes\comfyui-minimax-h3-turbo\__init__.py:235`。离线复现（`working/_h3turbo_rowcount_sim_20261026.py`）证明：节点 `_unique_t()` 只补视觉 cond 行、漏补 audio cond 行，而基座 `seg_t` 在带 ref audio 时会多要一行 ⇒ 只要「参考音频＋Turbo LoRA」同时出现就错行；Character Swap／Relay 不带参考音频，所以从来没撞上。上游 `Larryvrh/ComfyUI-MiniMax-H3-Turbo` issue #29 已修，本机尚未更新。**待批准后才动 `C:\ai program\` 下的 ComfyUI。**
- **该阻断已按方案 B 修补（源码已修复，实机待重跑）**：先备份原节点（`_backup\comfyui-minimax-h3-turbo___init__.py.20261026.bak`，SHA256 `65AE7F4B…27863`，与原文件同哈希），只改两处：新增 `_cond_rows(payload)` 按 `kind in ("audio","video_audio") and ref_audio_t > 0` ＋ keyframes 的 `audio_latent` 判断基座会打包哪几类 cond 行；`_unique_t()` 收 payload dict（仍兼容 bool）并补上音频钉行 `max(t_a, audio_cond_noise_aug 默认 1.0)`，视觉钉行改读 `visual_cond_noise_aug`（默认仍 0.999）；`_make_adaln_forward.forward` 加 `st.shape[0] == x.shape[0]` 闸门，行数和不上时跳过 delta 而不是抛错。没有采用上游的 `adaln_t_table` 最近行改写，避免 look 偏移既有基线。
  - 离线证明（用 ComfyUI 自带解释器 `venv\Scripts\python.exe`，真实 `PackedLayout`／`time_shift_sigma` 当基准）：`working/_h3turbo_rowcount_after_20261026.py`，log `_dsh_verify_9\round21\logs\h3turbo_rowcount_after_20261026.log` ⇒ 9 个场景 × 8 个 σ 共 72 组，**旧规则 24 组行数不符、补丁后 0 组**；在失败形状上用真 torch 复现出逐字相同的 `The size of tensor a (3) must match the size of tensor b (2) at non-singleton dimension 0`，补丁后 `ok, out (3, 3)`。Character Swap／Relay（只有 picture ref）两规则都是 2／3 行 ⇒ 既有成功基线零行为变化。
  - 节点级导入探针：`working/_h3turbo_import_probe_20261026.py`（log 同名 `.log`）在真实 ComfyUI 模块环境导入编辑后的文件，`NODE_CLASS_MAPPINGS` 两个节点齐全，`_unique_t` 对新视频图返回 3 行。已重启 ComfyUI（StabilityMatrix 监管，命令行逐字保留）：启动日志无 `IMPORT FAILED`／Traceback，`/object_info/MiniMaxH3TurboLoRA` 正常注册，`/system_stats` 显示 `cuda:0 NVIDIA RTX PRO 4500 Blackwell`、VRAM free 30.55 GB。**新视频尚未实机重跑。**

#### 实机证据（round 20 与 black-shirt 两次 preview，均 0.5 MP，走 `staged_model_driver.py`）
- `..._yellow_shirt_9` S1／R1→P5／seed 97000904（policy 61＋engine v6）：`prompt_chars 11 421`、`dropped_tail_clauses []`，去污染后不再长出帽子／山羊胡；三次尝试 similarity 0.538173／0.602773／0.597043，选 attempt 2，最终 `passed=false`，理由 `output drifted away from the selected V1 Shot/plate`（左右 plate 条 continuity 失败）。
- `..._yellow_shirt_9` S7／R1→P1／seed 97000914：**`passed=true`／`accept`**，similarity 0.493088，`attempts_used 1`，提交 prompt 含 `CLOSE-UP SHEET CROP LOCK`、`APPARENT AGE LOCK`、`NO INVENTED TEXTURE OR PATTERN`。
- black-shirt `preview_1516417359058198094`（policy 61）：三段全 `passed=false`，每段两条 silent 审计行 —— 目标 R1 超标（0.2531／0.2003／0.2494 vs 0.1206／0.0801／0.2150），旁观者从不超标 ⇒ 正是修因 M 要拆掉的误判来源。
- black-shirt `preview_2448458047138852523`（policy 62，同一条 timeline）：审计行只剩 R1（`advisory=false`）、`selected_attempt` 由全 1 变成 2／3／2、similarity 三段全部上升（0.501021→0.560221、0.51596→0.53726、0.52525→0.557678）；seg1 **`passed=true`**（result 0.164414 > 绝对上限 0.078027，但 < 上半脸参照上限 0.178414 ⇒ 判为整脸运动而非说话），seg0／seg2 仍超标。**人眼尚未 grading**，故只能写「QC 判定已按新规则改变」，不能写「对嘴已实机修复」。

#### Verification（源码 vs 视频，务必分清）
- 离线：`testing/` 全量套件 `Ran 842 tests … OK (skipped=10)`（log `_dsh_verify_9/round21/logs/suite_policy62_registration.log`，上一基线 801 → +41）；新模块 `test_character_swap_background_extra.py` 9、`test_silent_mouth_transient_qc.py` 3、`test_smart_render_qc_advisory.py` 4；`test_character_swap_engine.py` 69、`test_identity_sheet.py` 39、`test_smart_render_worker.py` 52、`test_staged_model_driver.py` 25；`director_cut_studio / smart_render_worker / character_swap_engine / character_identity_sheet / staged_model_driver / source_video_analysis` py_compile 全过。
- 视频：S7／97000914 已 `accept`，black-shirt seg1 已被新 QC 放行，但「蜂窝是否真的不再出现」「衣服是否真的换成参考图衣柜」「是否真的不再变老」仍未人眼读帧 ⇒ **未实机验证**。
- 新增离线工具（`working/`）：`_h3turbo_graph_dump_20261026.py`、`_h3turbo_history_probe_20261026.py`、`_h3turbo_rowcount_sim_20261026.py`、`_h3turbo_rowcount_after_20261026.py`、`_h3turbo_import_probe_20261026.py`、`_manifest_keypaths_20261026.py`、`_analyze_blackshirt_20261026.py`、`_tail_clause_lengths_20261026.py`、`_prompt_budget_headroom_20261026.py`、`_prompt_length_delta_20261026.py`、`_probe_silent_mouth_fixture_20261026.py`。

### Round 19 实机：修因 I／J 第一次走完 ComfyUI ＋ 两处新修（去污染 / 近景裁切锁定）→ 源码已修复＋离线绿，实机待 round 20（2026-10-26）

- **round 19 实机（policy 60，0.5 MP，链 `working/_chain_round19_20261026.ps1`，日志 `_dsh_verify_9/round19/logs/`，两条都 `exit=0`）**：
  - **S10／R1→P1／97000884（similarity 0.5081）**：至今最像 P1 的一次 —— 圆框金属眼镜、细胡子、大眼大笑、黑帽红顶＋金带全部到位，**没有变老人**。遗留缺陷仍是根因 H：衣服＝源演员的金色团花袍。`close_up_silent_mouth` 被长度守卫丢弃（12 178／12 320），`silent_mouth_audit passed=false`。
  - **S1／R1→P5／97000894（similarity 0.615，四条最高）**：卡通媒介保住、medium 构图正常，但脸出来是「戴帽皱眉＋山羊胡」的真人味男人 —— 与 P5 参考图本身**完全一致**：P5 是一张带标题「剧名：毒舌大壯」＋字幕＋👍901 点赞 UI 的截图。模型把截图上的烧录文字/图标当成角色设计的一部分 ⇒ 直接催生修因 K。
- **修因 I 实机证明**：`unload-qwen` attempt 1 撞 `HTTP 409`，`cancel_requests=["req_89da1635"]`，attempt 25 `verified_clean=true`，VRAM **26.55 GB → 3.81 GB** ⇒ 补 `generating` 白名单后的 cancel sweep 在真机上确实能清掉 tray 预热请求。
- **修因 J 实机证明**：S1 的 4 帧 clip 这次正常产出 QC 判定（不再 `Could not sample Character Swap identity region`），clamp 后的 stamp 在实机可解码。
- **修因 K（新，源码已修复）：参考图上的烧录字幕/标题/点赞 UI 被当成角色设计**。`character_identity_sheet.py::suppress_burned_in_overlays` 在 `compose_identity_sheet` 尺寸检查之后、`_segment_mask` 之前对**不透明**输入做一次去污染：上下条带（top 20 %／bottom 13 %）与左右条带（left 10 %／right 16 %）里，近白（≥240）连续行程 ≥2 px 且 ≤30 % 行宽者判定为烧录字形，连同 9→5 px 光晕一起删除，两轮后 3.0 半径羽化融合；总删除量 >8 % 时判定「图本身就是白的」并整体放弃（回报 `overlay hypothesis rejected`）。透明 cut-out 直接跳过。真实素材实测：P5 删掉 **1.306 %**、P6 **0.119 %**，P1／P3 跳过。结果写进 sheet `notes`。
- **缺陷⑥（新，源码已修复）：close-up 把 identity sheet 的衣柜面板整段搬进画面**。`character_swap_engine.py` 新增 `CLOSE-UP SHEET CROP LOCK — MANDATORY` 条款，闸门＝`face_dominant_closeup and reference_framing == IDENTITY_SHEET_FRAMING`（raw framing／medium 框一律不触发），插在 `identity_sheet_contract` 与 `apparent_age_lock` 之间，`CHARACTER_SWAP_TAIL_DROP_RANKS` 排名 3（在两条 silent 条款之后）。实测：sheet＋近景 silent = **12 258 字**（仍在 12 320 预算内 ⇒ 条款与 silent 条款可共存）；sheet＋近景说话人 = 10 272 字。
- **顺带修掉一个真 bug：默认 preset 永不命中缓存**。`_cached()` 用 `int(payload.get("preset") or -1) != preset_index`，而 **preset 0 就是 `DEFAULT_SHEET_PRESET`、`or` 把它当缺失** ⇒ 每一张默认布局 sheet 每次 Job 都被重画一遍。改成 `isinstance(payload.get("preset"), int)` 的 fail-closed 守卫；回归测试先断言 `reason == "cached"`，再把 sidecar 的 `engine_version` 改旧断言 `reason == "composed"`。此项只改校验路径，sheet 画面内容不变 ⇒ 不需要 bump 版本号。
- `SMART_RENDER_POLICY_VERSION` **60 → 61**（`director_cut_studio.py`／`smart_render_worker.py` 同步）：close-up sheet 裁切锁进指纹；`IDENTITY_SHEET_ENGINE_VERSION` **5 → 6**：去污染改变面板内容，旧 v5 sidecar 全部作废。
- **测试**：`test_character_swap_engine` **68**（新增 6 项 crop-lock：触发与措辞、无 sheet 静默、`FULL_DESIGN_FRAMING` 静默、medium 框静默并断言 `MEDIUM-SHOT SILENT MOUTH REINFORCEMENT`、`len-1`／`len-1500` 的 rank-3 丢弃行为、speaker pass 天花板）＋ `test_identity_sheet` **39**（新增 9 项去污染：字形清除且 <8 %、角色像素不动、bottom band、透明跳过、合法白区跳过、>8 % 弃用、干净图原样返回、sheet notes 记录、cut-out notes 记录、默认 preset 缓存命中与 engine bump 失效）；`test_smart_render_worker`／`test_staged_model_driver` 维持绿；`character_identity_sheet`／`character_swap_engine`／`smart_render_worker`／`director_cut_studio` `py_compile` 通过。
- **状态界定**：修因 K、缺陷⑥ 锁、preset-0 缓存修复 ＝ **源码已修复＋离线测试绿，尚未实机验证**；round 19 的 S10／S1 两条是 policy 60 + engine **v5**（未去污染、无 crop lock）的产物 ⇒ 「去污染能否让 P5 不再长出真人味」「crop lock 能否消除 97000854 的衣柜入侵」要等 round 20（S1／R1→P5 与 S7／R1→P1，seed 从 97000904 起）。**视频已实机验证**的仍然只有：close-up `uhip` 让 S7／S3 拿回 P1 五官与衣柜（97000824／97000854）、driver unload 409 自愈、QC clamp。
- 新增离线工具（`working/`）：`_croplock_probe_20261026.py`、`_decontam_fixture_probe_20261026.py`、`_decontam_bail_probe_20261026.py`、`_cachereason_probe_20261026.py`、`_cachekey_probe_20261026.py`、`_decontam_land_check_20261026.py`（真 P1/P3/P5/P6 落板图 `_dsh_verify_9/round20/*_decontam_land_check.png`）。

### Round 18 实机基线 + 两处新根因（修因 I／J）→ 源码已修复＋离线测试绿，S10 复测待跑（2026-10-26）

- **round 18 实机基线（policy 60＝新默认，四条 Job，0.5 MP）**：
  - **S7／R1→P1／97000854 `exit=0`，sim 0.515343 accept** —— 五官回到卡通 P1，衣服＝黄长衫＋黑马甲三白点＋蓝格裤，媒介保持卡通。**这是 close-up 默认改 `uhip` 之后第一次实机成功**，用户 grading 从 40 % 拉到可接受。新缺陷⑥：identity sheet 的衣柜面板整段被搬进画面（桌子被抬高、画面里多出垂手拳头与袍摆），违反 `do not widen the shot to reproduce the full-body reference`。
  - **S11／R2→P1／97000874 `exit=0`，sim 0.467493 accept** —— 仍不合格：脸变老人（银灰鬓、皱纹、长八字胡），衣服＝源演员的金色团花袍。
  - **S1／R1→P5／97000864 `exit=1`** —— 见修因 J，片段早已渲染完成却被 QC 异常判 failed。
  - **S10／97000844 `exit=2`** —— `run-aborted reason=qwen-not-clean`，见修因 I；ComfyUI 从未收到任务，是唯一没有产物的 seed。
- **修因 I：driver 的 unload cancel 白名单缺 state**。实测（`working/_strata_states_live_probe_20261026.py`）Strata `/api/serving` 只有 `queued/True`、`generating/True`、`done/False` 三种 `(state, cancellable)`，而且 finished row 会永久留在 ledger。旧白名单没有 `generating` ⇒ cancel sweep 命中 0 条 ⇒ 每轮 `HTTP 409 … Finish or cancel this model's requests first` 直到 90 s 超时。`staged_model_driver.py`：白名单补 `generating/streaming/processing`，新增 `TERMINAL_REQUEST_STATES`、`_request_state()`、`_request_is_live()`（规则＝`cancellable` 且 state 非 terminal，未知 state 一律视为 live）、`_inflight_request_ids(rows)`（复用 rows 不再二次 GET）；`_cancel_inflight_requests()` 回报 `observed`／`recognised`；sweep 空但 ledger 非空时 emit `cancel_sweep_empty` 诊断（attempt 1／7／最后一次）。`H3_STAGE_QWEN_FORCE_CANCEL=0` 行为不变。
- **修因 J：短片 QC 采样点越界**。4 帧 clip（duration 0.166667 s、interval 0.041667 s）里 strict coverage 的 `0.82 × duration = 0.1367 s` 落在最后一帧之后，ffmpeg input seek 回 `rc=0` 且 0 bytes，`_extract_identity_gray_frame` 抛 `Could not sample Character Swap identity region:`，已渲染好的 take 直接被判 failed。`smart_render_worker.py` 新增 `_probe_frame_interval()`（avg_frame_rate，失败返回 0.0）、`_clamped_timestamps()`（ceiling＝`duration − 2 × frame_interval`；interval 未知时退回原比例）、`_identity_sample_ladder()`、`_decode_probe_frame()`（5 个 stamp × 2 种 seek 变体，input-seek 优先），`_extract_identity_gray_frame`／`_extract_identity_rgb_frame` 改为委派且错误讯息字串不变；identity 审计四处时间戳（常规三点、strict 五点、mouth、ambiguous）全部走 clamp，`frame_interval = max(plate, take)` 保证 source 与 result 用同一组 stamp。
- **离线收口**：`working/_s1_audit_replay_20261026.py` 对 round 18 **真实产物**跑真 `inspect_character_swap_identity`，逐 attempt 配对 `NN_source.mp4 → NN_save.mp4`：97000854 sim **0.515343 accept**、97000874 sim **0.467493 accept**，与实机 manifest 逐位一致 ⇒ 修因 J 没有改变任何评分行为；97000864 不再抛异常，两个 attempt 都返回 `action=retry_fresh_seed`（`source_plate_continuity_audit passed=False`，reason「output drifted away from the selected V1 Shot/plate」）。
- **测试**：`test_staged_model_driver` **24**（新增 `test_generating_and_unlisted_states_are_still_cancelable`、`test_strata_unload_cancels_a_generating_tray_request`）＋ `test_smart_render_worker` **52**（新增 `test_probe_helpers_keep_every_sample_decodable`、`test_identity_audit_survives_a_four_frame_character_swap_take`）＋ `test_character_swap_engine`／`test_character_swap_closeup_gates`／`test_character_swap_silent_audio` **89** ＝ **165 项全绿（1 项跳过）**。
- **状态界定**：修因 I／J 目前是「源码已修复＋离线可复现」，还没拿到一条走完 ComfyUI 的新片；**round 18 唯一没出产的 S10／policy 60 待用 seed 97000884 实机补跑**。「close-up 用 `uhip` 能拿回 P1 五官」在 S7 已是**视频级验证**，S1／S10／S11 是否同样受益仍未验证。
- 新增离线工具（`working\`）：`_strata_states_live_probe_20261026.py`（记录 host 真实 state 词汇，log 同名 `.log`）、`_s1_audit_replay_20261026.py`（真实产物 QC 回放）。

### Round 17 干净单变量判定：close-up Shot 改用「臀部高」衣柜面板（policy 59→60）→ 源码已修复，round 18 实机进行中（2026-10-26，单元测试 118/118 + 50/50 绿）

- **驱动层修复第一次拿到实机证明**：tray 会把 Qwen 载回并立刻预热，所以 `run` 的 `unload-qwen` 经常撞在一条还开着的 warm completion 上，host 回 `HTTP 409 … Finish or cancel this model's requests first`。`staged_model_driver.py` 现在识别这个 busy 错误（`_unload_busy_error`），在每一轮重试前扫描 host 的 serving request 列表并逐个 `POST /api/serving/requests/{id}/cancel`（`H3_STAGE_QWEN_FORCE_CANCEL=0` 可关），同时把轮询窗口从 30 s 提到 `UNLOAD_POLL_SECONDS = 90`。round 17 两条 Job 的 `unload-qwen` 都在 **attempt 2** 成功，VRAM **26.69 GB → 4.05 GB**，两条 `exit=0`；此前 2026-10-25 每一个 `preview_*.job.json` 都在 ComfyUI 收到任务之前就崩在这一步。
- **round 17 是 policy 59 之后唯一干净的单变量实验**：S3／97000804（`uchest`）与 S3／97000824（`uhip`）同 policy、同 engine v5、同 plate、同 12 132 字提示词，只差衣柜面板的裁切线；S10／97000834 同理对照旧 `uchest` 组。
  - **S3 uchest（97000804，`head_coverage` 0.4473，similarity 0.5373）**：无眼镜、无帽，仍是源演员的金色团花补服 ⇒ 判定 `uchest` 失败。
  - **S3 uhip（97000824，`head_coverage` 0.3421，similarity 0.5550）**：P1 的圆框眼镜、黑帽＋金带＋红顶白牌、胸前深色面板与三白点**同时出现** ⇒ 同一 plate、同一提示词下只换裁切线就翻转结果。
  - **S10 uhip（97000834，similarity 0.5088，attempt 1 被选）**：至今最接近 P1 的一次（大卡通眼、P1 眼镜、张嘴大笑、P1 帽），但**凭空长出黑色山羊胡**、鬓角仍是源演员深色头发、袍仍是金色团花。对照 97000784 / 97000724 / 97000564 全是 **engine v4** 的 sheet，不构成干净对照。
  - 两条 Job 都因 `failure_class=silent_mouth_excessive_articulation` 被判 identity failed（S10 `result_motion` 0.131 ≫ 阈值 0.055），根因见下方「round 16 暴露的结构性矛盾」：S3/S6/S10 的 `close_up_silent_mouth` 一定被长度守卫丢掉。
- **产品默认改动**（`director_cut_studio.py::_character_swap_identity_sheet_reference`）：close-up Shot 的衣柜面板裁切线由 `close_up`（胸部 0.34 → 档名 `uchest`）改成 `medium`（臀部 0.62 → 档名 `uhip`），判定条件写作 `if medium_rows: "medium" elif closeup_rows: "medium"`，并在源码注释里钉住 round 17 证据。`uchest` 仍可用 `H3_IDENTITY_SHEET_OUTFIT_VIEW=close_up` 回滚，不需要改码。
- `SMART_RENDER_POLICY_VERSION` **59 → 60**（`director_cut_studio.py` / `smart_render_worker.py` 两处同步）：默认裁切线进入 Smart Render 指纹，close-up Shot 的旧 Segment 缓存全部作废，避免「新代码 + 旧 sheet」混片。
- 新增回归测试 `testing/test_identity_sheet.py::test_closeup_shot_gets_the_hip_height_wardrobe_panel`：断言 metrics `identity_sheet_outfit_view == "medium"`、档名含 `_uhip_`；override 路径必须返回 `_uchest_`。
- **状态界定**：以上全部「源码已修复 + 单元测试绿」（`test_identity_sheet`／`test_character_swap_engine`／`test_character_swap_closeup_gates`／`test_character_swap_silent_audio` 共 **118/118**；`test_smart_render_worker` **50 OK, skipped=1**；六个核心文件 `py_compile` 通过）。
- **round 18 实机进行中**（policy 60、无 env override = 新默认，链 `working/_chain_round18_20261026.ps1`，日志 `_dsh_verify_9/round18/logs/`）：S10／97000844（对照 97000834）、S7／97000854（用户 grading 40 %）、S1／97000864（R1→**P5**，P5 sheet 第一次走 `uhip`）、S11／97000874（**R2**→P1，60 %）。离线 pre-flight 记录在 `_dsh_verify_9/round18/precheck_policy60.txt`：四条 pass 长度 10 534–12 178，S10 仍 `dropped_tail_clauses=['close_up_silent_mouth']`。读帧前，「close-up 用 uhip 就能稳定拿到 P1 五官」只能算**待验证假设**。
- **仍未解的五项画面问题**（本轮无源码改动）：① 年龄漂移（变老人）② 服装被源 plate 压过 ③ 凭空长出面部毛发/细节 ④ 背景蜂窝 ⑤ silent listener 对嘴。⑤ 的两条候选修法都还没做：(a) 再压缩约 200 字让 `close_up_silent_mouth` 活下来（headroom 只有 188 字；`close_up_medium_reinforcement` 与 `plate_texture_contract` 已被测试锁死、不可丢）；(b) 当所有 attempt 都违反 silent 时改选 mouth motion 最小的那条（现在已经会选，但仍标 failed，白白烧重试）。
- **已否决、不要再试的方向**：source plate 躯干「服装带」——round 9 终局判定「只要动躯干带就变差」，`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` 出厂默认 `off`。

### Identity Sheet 脸部优先配重 + 衣柜面板按景别裁切（policy 58→59 / engine v5）→ 源码已修复，round 15/16 实机均未通过（2026-10-26，单元测试 110/110 绿）
- 根因 F（脸太小）：`character_identity_sheet.py` 旧配重把 body/outfit 当等权主面板，P1（209×600）的五官在 sheet 上只占 **15.3 %** 画布，H3 没有足够头部证据，只能从 plate 的颜色分布猜年龄与服装 —— 用户 grading 里 S3/S5/S7/S10/S11 全部「变成老人」，相似度 20 %–80 %。
- 根因 G（衣柜面板画出第二个人）：衣柜面板一律裁到全身，近景 Shot 画不到的腿与鞋仍占掉一半画布，H3 把它读成「站立的另一个人」（round 15 S2 帧内出现小型 P1 分身）。
- `IDENTITY_SHEET_ENGINE_VERSION` **4 → 5**：(1) 面板配重改为脸部优先（`ORIENT_SECONDARY_PANEL_WEIGHT = 0.05`，已钉进测试）；(2) 衣柜面板按 Shot 景别裁切 —— `OUTFIT_VIEW_SHARES`（`close_up` 0.34 → 档名 `uchest`、`medium` 0.62 → `uhip`）与 `OUTFIT_VIEW_OUTFIT_AREA`（0.36 / 0.44），preset 8 仍是「头 + 颈部以下」单脸布局。P1 脸部画布面积 **15.3 % → 44.7 %（uchest）/ 34.2 %（uhip）**；面板几何变了，旧 v4 缓存必须失效，所以版本号继续写进档名。
- policy **58**：identity-suppression 遮罩板从硬边矩形改成圆角羽化 alpha 窗口（根因 E：S6 的人物框把 44 % 画幅的墙面一起糊掉，H3 把糊掉的重画成蜂窝），`H3_CHARACTER_SWAP_IDENTITY_MASK_MODE=rect` 可回滚。policy **59**：把 plate 遮罩模式与 sheet 配重写进 Smart Render 指纹（`director_cut_studio.py` / `smart_render_worker.py` 同步）。
- **round 16 实机**（policy 59，链 `working/_chain_round16_20261026.ps1`，日志 `_dsh_verify_9/round16/logs/`，两条都没过）：
  - S3 / seed 97000804（uchest，`head_coverage` 0.4473，`target_reference_similarity` 0.5373，round 15 同段 0.530 ⇒ 实质持平）：QC `passed=false`，reason `authored Silent Listener mouth shows excessive articulation`，`action=retry_fresh_seed`。读帧：仍是灰白短发＋浓黑八字胡＋额头皱纹的老人，衣服是金色团花补服；**P1 的瓜皮帽（红顶）、圆眼镜、白眼圈、细胡子、黄衫＋三白点黑马甲一个都没有**。plate 本身脸已羽化模糊 ⇒ 老人是新造的，不是把 V1 的脸贴回来。
  - S2 / seed 97000814（uhip，`head_coverage` 0.3421，similarity 0.5514）：主体五官已回到卡通 P1（圆眼镜、白眼圈、细胡子、卡通线条）⇒ **medium 档的媒介与五官绑定成功**。但仍有四个缺陷：(a) 主体前多出一个完整的小型 P1 站立小人；(b) 右侧一个 live-action 真人；(c) 背景蜂窝格；(d) 与 plate 景别/构图漂移（`source_plate_continuity_audit.passed=false`，`retention_score=-0.4074`）。plate 里没有蜂窝也没有小人 ⇒ 两者都是生成期幻觉。
- **round 16 暴露的结构性矛盾**：三个 silent Shot 一定被长度守卫裁掉 `close_up_silent_mouth`（S3 编译 12 132，预算 12 320 只剩 188 字空间），而 QC 仍按 silent 门禁硬判失败 ⇒ 白白烧掉 fresh-seed 重试。提示词侧已饱和：禁止第二个分身（`identity_sheet_contract`）、禁止加年龄（`apparent_age_lock`）、禁止从糊掉的颜色猜服装（`plate_torso_blurred_clause`）三条都在提示词里，实机照样违反 ⇒ 加条款无效。
- **round 17 假设（实机进行中）**：round 16 只剩一个干净变量 —— S2（uhip，五官成功）对 S3（uchest，五官失败）。新增实验开关 `H3_IDENTITY_SHEET_OUTFIT_VIEW=close_up|medium|none`（默认空值＝保持逐 Shot 自动判定，因此默认行为与 policy 不变）。S3 / 97000824、S10 / 97000834 两条 Job 全部强制改用 uhip 重跑，链 `working/_chain_round17_20261026.ps1`。
- Verification（源码层）：`testing/test_identity_sheet.py`、`testing/test_character_swap_engine.py`、`testing/test_character_swap_closeup_gates.py` ⇒ **110 项全绿**；`director_cut_studio.py`、`smart_render_worker.py`、`character_swap_engine.py`、`character_identity_sheet.py`、`identity_sheet_page.py` `py_compile` 全通过。实机结论一律单独标注，未标注即「尚未实机验证」。
- 本轮新增离线取证工具（`working/`）：`_manifest_index_20261026.py`、`_attempts_dump_20261026.py`、`_manifest_tree_20261026.py`、`_audit_dump_20261026.py`（直接打印 `character_swap_identity_audits`）。

### Plate 语义 + sheet 单实例 + 尾部条款压缩（policy 55→57）→ 源码已修复，round 14 实机进行中（2026-10-26，单元测试 83/83 绿）

- round 13（policy 55：seeds 97000554 S3 / 97000564 S10 / 97000574 S6 / 97000584 S2，日志 `_dsh_verify_9/round13/logs/`）读完帧后给出两条新根因，两条都不是长度问题：
  - **根因 C — plate 与 prompt 不一致**：`dominant_closeup_identity_suppressed` 会把近全屏框约 **62 % 画面高度**（头＋肩＋胸）糊成硬边矩形，而提示词只说「头部区域被模糊」。模型于是从糊块的平均色里幻想年龄与服装——这正是 S3/S6/S10「卡通角色变成灰发老人＋凭空长出道袍/腰带」的直接来源。四个 take 里只有 S2（`medium_silent_listener_identity_suppressed`，plate 只糊头）带着与之相符的 plate 条款，也是唯一被评 ok 的一组。
  - **根因 D — Identity Sheet 分格漏进画面**：Relay 只有一个图片槽，sheet 的多面板被 H3 当成「场景里的人数」。round 13 背景里被复制出的人头数正好等于面板数，而且复制人穿着 P 图正装——这解释了 S4/S6/S8「角色对但衣服完全不像」：观众看到的“衣服”其实是背景里那个穿 P 图的小人，主角身上仍是 V1 服装。
- **policy 56**：
  - 新增 `plate_torso_blurred_clause`（`SOURCE PLATE HEAD AND TORSO BLURRED — AUTHORITATIVE`）。Studio/Worker 通过 `pass_spec["identity_suppression_geometry"]` 上报真实模糊带几何，引擎按几何选择措辞：只糊头 → 旧的 `SOURCE PLATE FACE BLURRED`；糊到头＋胸 → 新条款，明确「硬矩形边缘是工具伪影、糊块颜色是被抹掉演员的衣服而非需保留的事实、never infer apparent age／face／skin texture／hair colour、soft 区域由 Picture 1 决定整套服装」。`wardrobe` 类抑制策略仍走各自的 wardrobe 条款，不会重复。
  - `identity_sheet_contract` 加入 `Render exactly one instance of that character inside <Video 1>'s ... the scene must not gain a second, smaller or partial copy of Picture 1.`，直接针对根因 D。
  - `SMART_RENDER_POLICY_VERSION` 55 → **56**。
- **policy 57**（同轮）：把六条尾部条款压缩约 **410 字/Shot**，让四个重 Shot 回到已验证天花板之内，而不是悬在天花板上方 190–360 字：`CLOSE-UP MEDIUM REINFORCEMENT`（删去与 FINAL MEDIUM PRIORITY 重复的「照片参考保持照片」尾句）、`NO INVENTED TEXTURE OR PATTERN`、`SOURCE PLATE HEAD AND TORSO BLURRED`、`PICTURE 1 IS ONE IDENTITY SHEET`、`APPARENT AGE LOCK`（删去结论句）、`COMPLETE WARDROBE REPLACEMENT`。所有 rank-0 语义仍在场，未丢弃任何无 rank 条款。
  - `CHARACTER_SWAP_PROMPT_CHAR_BUDGET` **12600 → 12320**：12 326 是被证实可完整提交并渲染的最长提示词（seed 97000584，policy 55，`/history` 回读长度一致），预算取略低于它。压缩后最长 pass 为 S6 的 12 304，已落在天花板下方；S3/S6/S10 仍要让出 ≈400 字 close-up 口型强化（完整长度 12 537–12 734，任何 ≤12 326 的预算都留不住它），而 round 10/11 已证明该强化不是决定性因素。
  - policy 57 编译结果（0.5 MP，`working/_precheck_policy57b_20261026.log`；Job 内条款实测 `working/_job_prompt_census_20261026.py`）：
    | pass | 最终长度 | dropped |
    |---|---|---|
    | S1 `R1→P5` | 10655 | — |
    | S2 `R1→P1` | 12309 | — |
    | S3 `R1→P1` | 12134 | `close_up_silent_mouth` |
    | S4 `R2→P6` | 10641 | — |
    | S5 `R1→P1` | 9804 | — |
    | S6 `R2→P3` | 12304 | `close_up_silent_mouth` |
    | S7 `R1→P1` | 10597 | — |
    | S8 `R1+R2→P3` | 11569 | — |
    | S9 `R1→P1` | 10384 | — |
    | S10 `R1→P1` | 12180 | `close_up_silent_mouth` |
    | S11 `R2→P1` | 10536 | — |
    全部 11 pass `over_budget=False`（此前 S2/S3/S6/S10 为 12 518–12 688）。
  - `SMART_RENDER_POLICY_VERSION` 56 → **57**（两处同步）；`testing/test_character_swap_engine.py` 61/61、`testing/test_identity_sheet.py` 22/22 全绿，三个核心文件 `py_compile` 通过。
- **round 14 GPU**（policy 57，链脚本 `working/_chain_round14_20261026.ps1`，日志 `_dsh_verify_9/round14/logs/`）：S3／97000714／preset 0、S10／97000724／preset 0、S6／97000734／preset 2、S2／97000744／preset 0；对照 round 13 同 Shot 的 97000554／97000564／97000574／97000584。验收点：老人消失、服装按 P 图、背景无复制人。
- **状态界定**：本轮仍是「源码已修复 + 单元测试绿」。**根因 C／D 的视频尚未实机验证**——年龄漂移、蜂窝背景、衣服不像三项在 round 14 出片读帧前不得声称已解决。

### 尾部条款冻结 + 预算重校准 + silent 条款瘦身（policy 52→55）→ 源码已修复，round 13 实机进行中（2026-10-26，单元测试 57/57 绿）

- 用户整片分级（最新一版 `a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9`）：S1 完全不像参考图、S3 角色变老人＋衣服不像、S4/S6/S8 角色对但「衣服完全不像」、S7 40 %、S10 20 %、S11 60 %、S5 80 % 可接受；S2/S9 角色 ok，但背景出现蜂窝状图案。要求：完全根据参考图替换角色（以官方 H3 character-swap prompt 为规格）。
- **根因 A（已从 ComfyUI `/history` 回读证实）**：把 seed 97000374–97000544 的**实际提交提示词**（存档 `working/submitted_prompts_20261025/`）与 manifest 的 prompt 预算对照，分界线就是长度守卫丢掉的尾部条款——每一个被评 ok 或 80 % 的 take 都保留了 `CLOSE-UP MEDIUM REINFORCEMENT` 与 `NO INVENTED TEXTURE OR PATTERN`；每一个被评 20 %–60 % 的 take，以及 S3/S6/S10「老人＋凭空背景图案」那一组，恰好都被丢掉这两条。蜂窝背景 = `NO INVENTED TEXTURE OR PATTERN` 被丢的直接后果。
- **根因 B（像素天花板）**：P1 原图只有 209×600，头部裁切 136×163 px 被 LANCZOS 放大进 sheet 面板；对照 P5 head 面板原生 1734×1509（历史最高相似度 0.689、也是用户评级最好的一组）。提示词补不回像素 ⇒ 建议把 P 图先超分再进 Media Pool（尚未实施，需用户决定）。
- **policy 52 / 53**（上一轮已落地）：合并描述同一个身体的重复角色轨（S10/S11/S7 曾给一个人发双人 subject definition，导致所有条款翻倍）、拒绝冒充人框的背景柱、silent 口型带在选框填满画面时移到下半脸；并删掉 silent pass 里仍在正向要求动嘴的两句——官方作者模板的 "and visible mouth movements" 与 Studio 自己的 "Preserve Video 1 visible mouth timing"。
- **policy 54**：`CHARACTER_SWAP_TAIL_DROP_RANKS` 冻结——上述两条 load-bearing 条款不再有 rank，**永不丢弃**；改为压缩真正的重复表述：sheet framing 下 `FULL DESIGN-SHEET INTERPRETATION` 改用 lean 版（每条 silent pass 省 250 字），`multi_person_subject_definitions` 1047 → ≈560 字。S8 `R1+R2 → P3` 从 11589 降到 11170，`dropped=[]`。
- **policy 55**：`CHARACTER_SWAP_PROMPT_CHAR_BUDGET` **11400 → 11900**。11400 是在「守卫还能牺牲那两条 load-bearing 条款」的旧前提下校准的；冻结后该前提失效，于是 S2/S3/S6/S10（编译 12115–12706）只能牺牲 380–720 字的 silent 口型强化。11911 是被证实可完整提交并渲染的最长提示词（seed 97000374；回读档 `working/submitted_prompts_20261025/97000374_S10_overbudget_cartoon.txt` = 11911 字符／12013 位元组，端到端完整 ⇒ 该长度没有服务端截断），预算取略低于它。
- 同时把 **voice-ownership** 规则（画面里每一条可听声音——别的在镜角色、画外音、被替换者原本的 V1 声音——都只是背景声，绝不能驱动被替换角色的嘴）搬进**永不丢弃**的权威 `SILENT LISTENER PERFORMANCE — AUTHORITATIVE` 合同；两条 shot-scale 强化条款因此从 720 字各缩到 ≈380 字。依据：seed 97000374 丢掉强化仍对嘴，seed 97000454 带着完整 720 字强化也照样对嘴——真正压住嘴的是 plate 头部模糊＋官方作者提示词的闭嘴替换，两者都不在可丢清单里。
- policy 55 编译结果（0.5 MP，precheck 走 Studio 真编译路径，`working/_precheck_policy55_final_20261026.log`）：
  | pass | 最终长度 | dropped |
  |---|---|---|
  | S1 `R1→P5` | 10256 | — |
  | S2 `R1→P1` | 12326（over_budget） | `close_up_silent_mouth` |
  | S3 `R1→P1` | 11735 | `close_up_silent_mouth` |
  | S4 `R2→P6` | 10242 | — |
  | S5 `R1→P1` | 10224 | — |
  | S6 `R2→P3` | 11905（over_budget） | `close_up_silent_mouth` |
  | S7 `R1→P1` | 10198 | — |
  | S8 `R1+R2→P3` | 11170 | — |
  | S9 `R1→P1` | 10342 | — |
  | S10 `R1→P1` | 11781 | `close_up_silent_mouth` |
  | S11 `R2→P1` | 10137 | — |
  即：**load-bearing 条款（medium／texture／age／wardrobe／sheet／erasure）在每一 pass 都在场**，唯一仍被牺牲的是那条 380 字口型强化；S2 因自带 460 字 `SOURCE PLATE FACE BLURRED` 仍超 11911，作为「更长提示词能否被完整接受」的实测样本。
- `SMART_RENDER_POLICY_VERSION` 54 → **55**（`director_cut_studio.py` 与 `smart_render_worker.py` fallback 同步）；`testing/test_character_swap_engine.py` 新增/改写 4 项守卫测试，`Ran 57 tests ... OK`，四个核心文件 `py_compile` 通过。
- **round 13 GPU**：S3／97000554／preset 0、S10／97000564／preset 0、S6／97000574／**preset 2**（sheet 附 body＋outfit 面板，专治「衣服不像」）、S2／97000584／preset 0，链脚本 `working/_chain_round13_20261026.ps1`，日志 `_dsh_verify_9/round13/logs/`。
- **状态界定**：本轮只有「源码已修复 + 单元测试绿」。**round 13 的视频尚未生成**，年龄漂移、蜂窝背景、衣服不像、silent 对嘴四项仍未实机验证。

### Identity Sheet 头部面板改为「真 skull」而非半身像（engine v4 / policy 51）→ 源码已修复，等待实机（2026-10-25，单元测试全绿）

- 起因：policy 50 的 S10 实机复核显示渲染身份仍偏离 P1——太阳穴与鬓角长出灰白发、额头深纹、眼睛塌成写实半闭，即**年龄漂移**没有因为提示词缩短而消失。逐帧比对 P1 原画与当时喂给 Relay 的 identity sheet 头部面板，发现面板装的是**整个半身**（帽子＋脸＋背心三颗点＋格纹裤都在里面），不是头部。原因是 `estimate_head_box` 用「肩部行」当头部下界，而 P1 的帽子是平黑色、背心是平淡黄色，行覆盖率几乎不变，肩行判定被推迟到胸腔以下 → 头部框一直扩到胸口，与身体面板同倍率放大，脸部实际只有 96→212 px。H3 读不到脸，只能自己发明五官与年龄。
- `character_identity_sheet.py`：
  - 新增 `MAX_HEAD_HEIGHT_TO_SKULL_WIDTH = 1.45` 与 `SKULL_WIDTH_SAMPLE_SHARE = 0.55`。测量依据：P1 头骨最宽行 99 px、下巴线 145 px = **1.46×**；P3 98 px → 134 px = **1.37×**。卡通正脸「高度 ≤ 1.45× 头骨宽」是稳定几何关系，而 bust（头＋颈＋肩）必然超过它。
  - 新增 `_widest_row(mask, first_row, last_row)`：只在候选带顶部 55 % 取样最宽行，避免把帽檐外的装饰、飘带计进头骨宽度。
  - `estimate_head_box` **仅在 `shoulder_row >= 0` 时**夹紧 `head_bottom ≤ top + skull_width × 1.45`（下限 `top + 0.10 × 主体高度`），保留「只有头发露出、无肩可测」的 fallback 路径不变。
  - `IDENTITY_SHEET_ENGINE_VERSION` **3 → 4**：该常量直接进入所有 sheet 档名，因此 v3 缓存自动失效、重建；程式码内没有任何地方硬写 `_v3`。
- `director_cut_studio.py`：`SMART_RENDER_POLICY_VERSION` **50 → 51**——v4 sheet 是不同的参考图位元组，policy 50 的旧 Job 仍指向 v3 半身面板，必须作废重编译。
- 实测放大率（preset 0，target_aspect = V1 clip 460×642，canvas 832×1152）：
  | cast | 头部面板倍率 v3 → v4 | 身体倍率 | sheet 头面板占比 | 闸门指标（原图头 / V1 帧） |
  |---|---|---|---|---|
  | P1（209×600） | 2.15× → **2.69×**（+25 %） | 1.94× | 0.168 | 0.086 ⇒ 一定做 sheet |
  | P2（342×584） | –（原本就 ≥0.22） | – | 0.259 | 0.259 ⇒ **passthrough，不做 sheet** |
  | P3（307×651） | 2.66× → **2.91×** | 0.96× | 0.300 | 0.111 |
  | P4（1069×1471） | – | – | 0.316 | 0.180 |
  | P5（1062×1482） | – | – | 0.315 | 0.185 |
  | P6（302×246） | – | – | 0.313 | 0.055 |
  目视确认看板 `_dsh_verify_9\round9_frames\sheet_v3_vs_v4_20261025.png`：v4 的 P1 头面板是真正的 skull（帽子、眼睛、胡子、嘴填满面板，裁切停在领口），v3 则是整个半身（连同背心三颗点）。
- preset 扫描（P1，头部面板倍率／渲染高度／占比）：p0 2.69×/439 px/0.17 · p1 2.45×/0.14 · **p2（头＋身＋服装）3.01×/491 px/0.21** · **p3（头／镜像头／身）3.99×/651 px/0.37** · p4（只有头）5.93×/966 px/0.81（无身体面板）· p5 0 · p6 3.40×/555 px/0.27 · p7 2.33×/0.13。渲染路径本来就尊重用户在 Identity Sheet 页面的选择（`director_cut_studio.py` 传入 `preset=int(self.identity_sheet_preset)`），**默认仍保持 0**，是否改用 preset 2／3 由导演决定。
- project cache 已按 v4 重建目前 Project 实际引用的三张图（P1 `image_137_fabf0dbd875434cd_nobg.png`、P2 `image_139_c8f4fe050a17a4aa_nobg.png`、P3 `image_141_d3bf62d5fc9dfa30_nobg.png`；这三档实际位于工作区根 `.director_cache\`，不是 project\media\imported）。
- 测试：`testing\test_identity_sheet.py` 新增 2 项——`test_head_box_is_a_skull_when_the_shoulders_read_late`（平色帽子＋平色躯干的合成图，肩行读晚时头部框必须停在领口之上）与 `test_sheet_magnifies_the_face_beyond_the_body_panel`（头面板倍率必须高于身体面板）。反证成立：关掉夹紧时头部框一路扩到胸腔。该模块 **Ran 22 tests OK**。整轮 `QT_QPA_PLATFORM=offscreen` + `working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` → **`Ran 752 tests`，failures=0 errors=0 skipped=10**（基线 750；日志 `_dsh_verify_9\round9\logs\full_suite_policy51_sheetv4.log`）。`director_cut_studio.py` / `character_identity_sheet.py` / `character_swap_engine.py` / `smart_render_worker.py` py_compile 通过。
- **状态界定**：本轮只有「源码已修复 + 单元测试绿」。**尚无任何一张新视频是在 v4 sheet + policy 51 下生成的**，年龄漂移、蜂窝纹理、silent 口型三项仍未实机验证。下一轮 GPU 顺序建议：S10（有量化基线可比）→ S3 → S5/S7/S11 → S1 → 整片。
- VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，**Smart Render Policy `51`**，Identity Sheet engine `4`。

### S10 提示词长度去重＋预算守卫（policy 50）→ 实机已渲染，判定「长度不是相似度主因」（2026-10-25，源码已修复 + 单元测试全绿；policy 50 默认路径已实机）

- 起因：导演对整片目视复核给出相似度分数（S10 20 %、S7 40 %、S11 60 % 不及格；S5 80 % 可接受）。量化编译后的提示词发现一个相关性——**分数最差的 Shot 提示词最长**，而最新写入的身份条款（年龄锁、sheet 解读、silent 契约）恰好全部排在末尾，正是稀释最严重的位置。S10 编译出 14 385 字符，是从未被提交过的长度。
- `character_swap_engine.py`：
  - **Silent 契约去重**：正文改为一行 `SILENT LISTENER — SUMMARY`，完整版 `SILENT LISTENER PERFORMANCE — AUTHORITATIVE` 只在最后出现一次（每个 silent Shot 省约 1 230 字符，此前同一契约在一条提示词里出现两遍）。
  - 尾部条款重构为有序 `tail_clauses` + 丢弃循环，新增 `CHARACTER_SWAP_PROMPT_CHAR_BUDGET = 11400` 与 `CHARACTER_SWAP_TAIL_DROP_RANKS`（1 close-up medium 强化 → 2 plate 纹理契约 → 3 plate 服装带 → 4/5 close-up/medium silent 强化）。`plate_face_blurred_clause` 刻意**不排队**：它是唯一告诉 H3「plate 头部模糊是有意的」那句话，删掉它就复现 S7/S9 的「还是 V1 那张脸」。超预算时只做**标记**，绝不砍掉无 rank 的保护条款。
  - 新增可选 `prompt_audit` 参数记录 `prompt_chars` / `char_budget` / `dropped_tail_clauses` / `over_budget`。
- `director_cut_studio.py`：`SMART_RENDER_POLICY_VERSION` **49 → 50**（与 worker 同步），build 调用传入 `prompt_audit`，pass row 落盘 `prompt_budget`，因此 manifest 直接能看出该 take 丢了哪几条尾部条款。
- 编译结果（0.5 MP，未上 GPU）：S10 14 385 → **11 911**（仍超预算，丢 3 条）、S3 11 391、S5 11 305、S11 11 239、S2 11 229、S7 11 130、S8 10 990、S6 10 839、S9 10 655、S4 10 597、S1 10 551。审计脚本 `working\_prompt_clause_audit_20261025.py`（本轮修好单行条款标题的正则，并新增 `drop` 栏与 `DROPPED FOR BUDGET` / `DUPLICATE CLAUSES` 输出）。
- **实机验证（policy 50 默认路径）：S10 / seed 97000374 / 0.5 MP / 单 Segment 21.5–22.5 s / `R1+R2 → P1`**：driver 全程 `unload-qwen → wait-comfy → worker → /free` 正常收工，`/free` 后 VRAM 2.38 GB。三次尝试后按「最像目标 P 图」选中 attempt 2：target similarity **0.534885**、`source_identity_retained=false`（V1 身份已抹除）、`complete_actor_erasure` 通过、`whole_character_integration` 通过；`silent_mouth_audit` 违规（result_motion 0.1174/0.1197 > 上限 0.0620/0.0655）⇒ `failure_class=silent_mouth_excessive_articulation`。**同时证明 11 911 字符可被 H3 接受并渲染**，已提交上限从 11 454 抬到 **11 911**（引擎注释已同步）。
- **判定（关键负面结论）**：缩短提示词**没有**救回相似度也没有闭上嘴。逐帧目视 vs P1 原画：渲染是 P1 的卡通媒介（真人化未复发 ✅），但①太阳穴与鬓角长出**灰白头发**、额头三道深纹、眼角鱼尾纹、眼睛塌成写实半闭 ⇒ 年龄漂移仍在；②P1 的**黑色平顶帽是纯平色**，渲染成**蜂窝状格子织纹**，背心三颗白点被平铺成满地大圆点；③帽子红球变成红线穗。结论：**提示词长度是提交风险，不是相似度与口型的病因**，长度守卫保留但不该继续加码。三条真正的病因另有其因（参考图只有 209×600、QC floor 0.30 太松、silent plate 仍保留张开嘴的嘴部），见下一轮条目。
- 测试：`testing\test_character_swap_engine.py` 新增 6 项（silent 契约恰好出现一次；契约仍是最后一段话；speaker pass 两者都不出现；预算内不丢弃；按声明顺序丢弃且保护条款存活并 `over_budget=true`；`plate_face_blurred_clause` 永不可丢）。engine 模块 **49 项 OK**；gates + identity-sheet + silent-audio **45 项 OK**；`test_smart_render_worker` **49 项 OK（skipped=1）**；整轮 `QT_QPA_PLATFORM=offscreen` + `working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` → **`Ran 750 tests`，failures=0 errors=0 skipped=10**（基线 744；日志 `_dsh_verify_9\round9\logs\full_suite_policy50_20261025.log`）。
- 取证：看板 `_dsh_verify_9\round9_frames\S10_97000374_board.png`（P1 原画 + v3 sheet ＋ silent plate 四帧 ＋ 渲染四帧）与 `_dsh_verify_9\round9_frames\S10_97000374_faces.png`（头部特写逐帧对照）；P1 纹理探针 `_dsh_verify_9\round9_frames\P1_texture_zoom.png`；驱动日志 `_dsh_verify_9\round9\logs\S10_97000374_driver.log`、提示词全文 `S10_97000374_prompt.txt`；成品 `...\cache\generated_outputs\preview\97000374\master.mp4`。
- VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，**Smart Render Policy `50`**。

### S4 躯干带第四／五轮实机 → 终局判定「任何躯干带都是净损失」，`off` 维持出厂默认（2026-10-25，源码已修复 + 单元测试全绿；两档均已实机验证）

- 接着上一节的三档 A/B，补跑剩下两个决定性对照（同一个 Shot S4、R2→P6、同一张 v3 identity sheet、policy 49、0.5 MP、单 Segment、fresh seed，只换躯干处理方式）：
  | take | 躯干处理 | QC | target similarity | 躯干 vs P6 直方图相关性 | 格纹梯度能量 | 导演目视 |
  |---|---|---|---|---|---|---|
  | `97000314` | 只有头部带（policy 47） | 通过 | 0.419648 | +0.690 | 15.30 | 衬衫格纹＋领口正确，多一条斜披带 |
  | `97000324` | blur40＋去饱和（policy 48） | 通过 | 0.401769 | +0.778 | 14.17 | 发明和服式长袍＋宽腰带 |
  | `97000334` | blur6＋去饱和（policy 48） | 通过 | 0.398574 | +0.364 | 15.62 | 凭空长出灰色无袖背心＋马尾 |
  | **`97000344`** | **band 关闭＝默认（policy 49）** | **通过** | **0.443384** | **+0.768** | **16.17** | 色彩与织纹同时最接近 P6（基准梯度 14.85、饱和 160±76），斜披带仍在 |
  | `97000354` | blur6 保色（policy 49，`blur` 模式） | 通过 | 0.421568 | +0.347 | 12.30 | 色彩保住（饱和 188±27）但格纹塌成扁平等边点阵背心，格纹只剩袖子 |
  全部 `attempts_used=1`。
- 因果修正（推翻上一节写下的假设）：先前结论是「把服装变灰的是去饱和，不是模糊」。`97000334`（blur6＋desat）与 `97000354`（blur6 保色）躯干相关性一起掉到 ~0.35，两档唯一的共同处理就是模糊 ⇒ **模糊本身**就会摧毁 Relay 需要的衬衫几何（失去摆放 P6 图案的地图），去饱和只是再叠一层色彩损失。因此判定收敛为：**S4 只要动躯干带就变差**，`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` 出厂值保持 `off`，`blur`／`blur_desat` 只保留为实验开关，本轮无需改代码去翻默认值。S4 剩余故障（源演员的交领斜披带＋长袖 vs P6 短袖翻领格子衬衫）是语义问题，只能从 prompt／identity sheet 攻，靠 plate 处理无解。
- **`97000344` = band 关闭这条默认路径「新视频已实机验证成功」**：它是目前 S4 全部六次生成里 target similarity 与躯干量化同时最好的一档（两项都是第一名，不是只赢一项）。`97000354` 则是「blur 模式已实机验证、判定为负」：QC 与 target similarity 都过关，但目视与躯干几何都不如 344，说明 QC 指标看不出织纹被摧毁。
- `director_cut_studio.py`：躯干带从 bool 升级为三档模式 `off | blur | blur_desat`（env `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE`，非法值回落 `off`）；`_character_swap_identity_suppressed_source()` 的 `wardrobe_band` 参数同时接受 bool 与字符串（bool→`blur_desat`/`off`，兼容旧测试），非法字符串抛 `ValueError`。plate 缓存 salt 的 `band_tag` 现在把模式名折进去，所以 `blur` 与 `blur_desat` 互不污染，且永不作废既有 head-only 缓存。
- `character_swap_engine.py`：拆成两条独立条款——`blur` 模式说「躯干已被模糊但色彩保留，只读成布料摆放模板」，灰色模板措辞只在 `blur_desat` 出现；`blur` 条款另外缩短约 147 字符，使 blur 档提示词留在已验证可提交的长度级。顺带把「已提交且渲染成功」的提示词长度上限从 11089 抬到 **11454**（`97000354` 实测提交并渲染通过），接手文件里 `<10800` 的保守天花板从此作废（仍无代码级长度守卫，不要主动写超）。
- 顺带澄清一项长期误判：S4 画面右侧的缩略图栏、图标堆叠、底部字幕条都是 **V1 plate 本来就有的内容**（未加任何处理的原始切片 `.director_cache\source_remake_relay_video\` 里同样存在），不是 identity sheet 泄漏；sheet 只当 Picture 参考，从不进 plate。
- 测试：`testing\test_character_swap_closeup_gates.py` 新增 4 项（`blur` 保留色彩且几何不变、`blur_desat` 与旧 bool `True` 产物完全等价、`"off"` 与 bool `False` 完全等价、非法模式字符串抛 `ValueError`）；`testing\test_character_swap_engine.py` 新增 1 项锁死两条条款措辞不可混用。目标两模块 **61 项 OK**（原 56）；`testing\test_smart_render_worker.py` **49 项 OK（skipped=1）**；整轮 `QT_QPA_PLATFORM=offscreen` + `working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` → **`Ran 744 tests`，failures=0 errors=0 skipped=10**（日志 `_dsh_verify_9\round9\logs\full_suite_band_mode_20261025.log`，基线 739）。`director_cut_studio.py` / `smart_render_worker.py` / `character_swap_engine.py` / `identity_sheet_page.py` / `staged_model_driver.py` py_compile 全通过。
- 取证与看板：五档对照拼图 `_dsh_verify_9\round9_frames\S4_five_way_blur_only_97000314_334_344_354.png`（旁边放 P6 torso 基准）；量化脚本 `working\_s4_v7_five_way_ab_20261025.py`（v6 四档脚本加进 354 行）；驱动日志 `_dsh_verify_9\round9\logs\S4_97000344_bandoff_default_driver.log`、`S4_97000354_bluronly_driver.log`；成品 `...\cache\generated_outputs\preview\97000344\master.mp4`、`...\preview\97000354\master.mp4`（blur pass 输出 `...\preview\97000354\segment_001_000003650_000005606\character_swap_pass_01_R2\01_save.mp4`）。
- 实机顺序更新（S4 已判定收案）：**S10（曾报 no reliable box）→ S3／S5／S7／S11（年龄漂移）→ S1（完全不像参考图）→ S6／S7／S8（背景蜂窝）→ 整片**。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，Smart Render Policy 保持 `49`。

### Source plate 躯干「服装带」前三轮实机 A/B → 判定负收益、默认关闭（2026-10-25，源码已修复 + 单元测试全绿；band 两种强度已实机，关闭后的默认路径已实机，见上一节终局判定）

- 要回答的问题：把 V1 plate 的躯干区域「模糊 + 去饱和」能不能修掉导演报的两类服装故障（S4「头发穿崩／衣服不像参考图」、S6/S8「衣服完全不像参考图」）。做法是把变量收到最小：同一个 Shot（S4，R2→P6）、同一张 v3 identity sheet（head coverage 0.3131）、同一 policy、0.5 MP、fresh seed、单 Segment，只换躯干处理方式。
- 三轮实测（全部 `attempts_used=1`、`passed=true`，即 QC 绿灯但导演目视不合格——再次证明颜色指标看不出服装语义）：
  | take | plate 躯干处理 | 目视 | 躯干 vs P6 直方图相关性 | 格纹梯度能量 |
  |---|---|---|---|---|
  | `97000314` | 只有头部带（无服装带） | 格子衬衫 + 领口正确，只多一条斜披带 | **+0.690** | 15.30 |
  | `97000324` | `boxblur=40:3,hue=s=0.25` | 格纹被打散 → Relay 自行发明带圆花图案的和服式长袍 + 宽腰带 + 格子背景 | +0.778 | 14.17 |
  | `97000334` | `boxblur=6:3,hue=s=0.25` | 格纹保留，但 plate 自己的灰色上衣被画成多出来的无袖背心，另外长出马尾 | +0.364 | 15.62 |
  三档只是把一种故障换成另一种：重模糊会摧毁 plate 的织纹／接缝几何（Relay 失去摆放 P6 图案的地图，于是凭空发明服装）；轻模糊保住了几何，却保不住 plate 自身服装的形状语义。**没有任何一档是净收益**，因此按测量结果回退：服装带默认关闭，plate 只做头部带。
- `director_cut_studio.py`：新增模块常量 `CHARACTER_SWAP_WARDROBE_BAND_ENABLED`（env `H3_CHARACTER_SWAP_WARDROBE_BAND`，默认关，注释里保留三档 seed 证据）；`_character_swap_identity_suppressed_source()` 新增 `wardrobe_band: bool | None` 参数（`None` 跟随 env），躯干区域只在 `band_enabled and row["gate"] in WARDROBE_GATES` 时产出；`WARDROBE_BLUR_RADIUS` 40 → 6（97000324 的重模糊直接导致发明服装，97000334 证明轻档能保住格纹）。plate 缓存 salt `v4 → v5 → v6`，token 现在含 `band={0,1}`，且 `{radius}:{saturation}` 只在带开着时才折进去——此前只要有人调一个从未启用的半径，就会把全部 head-only plate 缓存白白作废。
- `character_swap_engine.plate_wardrobe_blurred_clause` 改写：躯干读成「中性灰布料模板」，织纹／接缝／轮廓只是摆放参考，服装类型、颜色、图案、滚边一律来自 Picture 1；明令禁止发明带饰纹的长袍、圆花图案、格子刺绣、斜披带、宽腰带。标题串 `SOURCE PLATE WARDROBE SUPPRESSED — AUTHORITATIVE` 保留，条款只在 strategy 以 `_wardrobe_suppressed` 结尾时触发 ⇒ 默认关闭时提示词里根本不出现该条款。
- **Smart Render Policy 47 → 48 → 49**（studio 与 worker 同步，`smart_render_worker.py` 此前停在 47 已对齐）：48 是加入躯干带（`97000324`／`97000334` 两份 manifest 即 48）；49 是关闭为默认 + plate salt 升到 v6。48 时代缓存的 band plate 与 Segment 全部失效，不会静默复用。
- 测试：`testing\test_character_swap_closeup_gates.py` 4 处「带必须存在」的期望改为显式 opt-in（`wardrobe_band=True`），并新增 2 项锁死默认关闭——单 dominant 角色策略名必须恰好是 `dominant_closeup_identity_suppressed`、filter graph 不含 `hue=s=`、`split` 计数 1；双角色多 gate 时策略名无 `_wardrobe_suppressed`、无 `hue=s=`、`split` 计数 2。`testing\test_character_swap_engine.py::test_wardrobe_suppression_clause_fires_only_for_wardrobe_bands` 改断言新措辞（`neutral grey fabric template` 与禁发明清单）。实测：目标两模块 **56 项 OK**（closeup gates 15 + engine 41）、`testing\test_smart_render_worker.py` **49 项 OK（skipped=1）**；整轮 `QT_QPA_PLATFORM=offscreen` + `working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` → **`Ran 739 tests in 328.239s`，failures=0 errors=0 skipped=10**（日志 `_dsh_verify_9\round9\logs\suite_full_v6_bandoff_default.log`）；`director_cut_studio.py` / `smart_render_worker.py` / `character_swap_engine.py` / `character_identity_sheet.py` py_compile 全通过。
- 取证与看板：三档 A/B 拼图 `_dsh_verify_9\round9_frames\S4_torso_three_way_97000314_324_334.png`；相似度量化脚本 `working\_s4_torso_similarity_ab_20261025.py`（person box `[0.08,0.04,0.9488,0.96]`，躯干带取框内 x 0.14–0.90 / y 0.62–0.95，HSV 96-bin 相关性 + 灰度梯度能量），三档渲染脚本 `working\_s4_v5_three_way_ab_20261025.py`；驱动日志 `_dsh_verify_9\round9\logs\S4_97000324_v4wardrobe_driver.log`、`S4_97000334_v5wardrobe_blur6_driver.log`。plate 留在 `.director_cache\character_swap_identity_suppression\`，未加任何处理的原始切片仍在 `.director_cache\source_remake_relay_video\`。
- 状态区分（本条已被上一节「第四／五轮」条目取代，保留只为留痕）：`97000324`（blur40）与 `97000334`（blur6）= 已实机、结论为负；`97000314`（无 band）= 已实机、当时服装最接近 P6 的一档（target similarity 0.419648，仍有一条斜披带）。**`97000344`（band 关闭的默认路径，policy 49、strategy `dominant_closeup_identity_suppressed`、plate token `adca9488635ed124c70e`）已实机跑完并通过：`attempts_used=1`、`passed=true`、target similarity 0.443384、躯干量化 +0.768／梯度 16.17 双第一 ⇒ 默认路径已「视频实机验证成功」**；`97000354`（`blur` 模式、plate token `..._identity_suppressed_5c5c47f33a2b078450a2`）亦已实机、判定为负。后续实机顺序见上一节末尾。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，Smart Render Policy `49`。

### 测试契约与本机实况对齐 · 8 项既存红项清零（2026-10-25，源码已修复 + 单元测试全绿）

- 本轮不改产品语义，只把单元测试里**过期的期望值**与**依赖本机状态的断言**改成能长期稳定的契约；每一项都是先前改动落地后测试没跟上，不是新 bug。逐条根因与修法：
  - `testing\test_project_workspace.py:250`：`motion_preview` 仍按 `0.2` 断言，而 `project_workspace.PREVIEW_MEGAPIXELS` 本轮有意升到 `0.5`。期望值改为 0.5 并注明来源。
  - `testing\test_fourdx_ui.py:95`：4DX payload 仍按 Project Format 25 断言 `payload["version"]`，当前格式已是 29。改为 29。
  - `testing\test_soulx_dialog.py:112`：本机装有本地 SoulX，`detect_soulx_runtime()` 回 `127.0.0.1` 覆盖 `DEFAULT_SOULX_SERVER`（192.168.0.185），测试因此随主机安装状态摇摆。改为注入确定性 `SoulXRuntimeState(mode="client", api_url="", installed=False, ...)` 专测 fallback 路径。
  - `testing\test_staged_model_driver.py:314 / :335`：`run_job` 的 crash/auto-resume 包装会额外 `subprocess.Popen` 一个 detached `resume-wait`（`_spawn_resume_watcher`，`staged_model_driver.py:764`，2026-10-22 S7 事故后加的），`popen.call_count` 把渲染 worker 与看门狗混在一起。两个测试改为 patch `_spawn_resume_watcher`，保留原有 Popen 期望，另加断言「看门狗确实被唤醒」——Qwen 未在窗口内回来／退出码非 0 都必须唤醒 agent。该模块单跑 16 项 OK 但要 180.7s：mock 之下 `wait_qwen_reloaded` 仍会跑满 180s 真实超时。
  - `testing\test_skill_engine.py:829`（wuxia）：测试要求 wuxia 技能有「先修输入再规划」章节，但本地 `skill special\wuxia-blade-film\SKILL.md` / `SKILL.cn.md` 里根本没有该章节（全工作区只有测试文件提到相关短语，`_backup` 亦然）。补上英文 `## Repair Unsuitable Input Before Planning` 与中文 `## 规划前自动修正不合适的输入`，包含全部必需契约：input-repair pass、不得保留原始 Shot 数、三个 15 秒 Segment／九个五秒 Shot、单 Shot 约 60–120 度连续移动、每 Shot 一条主镜头运动、零预算警告。
  - `testing\test_comfy_connection_recovery.py:293 / :302`：`comfy_submit_worker.main()` 的 `finally`（`comfy_submit_worker.py:555-574`）现在**无条件** POST `/free`（每次测完必 free 的硬约束），且复用同一个 `_request_json`，于是「prompt 只排队一次」的 `call_count` 变成 2、`assert_not_called()` 也被 cleanup 触发。新增模块内 `_queue_posts()` helper 只数 URL 以 `/prompt` 结尾的调用，checkpoint/resume 契约（不得二次排队）保持原语义。
  - `testing\test_design_engine.py:2056`（cleanup 不猜 instance id）：`unload_lm_studio` 先做宿主方言探针（Strata vs LM Studio，`design_cleanup_service.py:82 → _host_kind:141`，GET `/api/v1/models`，进程级 `_HOST_KINDS:138` 按 origin 缓存）再读 catalog ⇒ 2 次 GET，`assertEqual(len(calls), 1)` 失败且随测试顺序摇摆。改为先 pop 该 origin 的缓存去顺序依赖，再把断言换成真正要守的契约：**不得出现任何 unload POST**（reads 允许，猜测式 unload 禁止）。
  - `testing\test_design_engine.py:3162 / :3840`：两项直接读 `example\tang_ting_ci_ying_45s_demo\design_plan.json` 与 `example\Dragon_Realm_vs_Immortal_Martial\DESIGN_REQUIREMENT_WORLD_POWER_REVISION.txt`，本机 `example\` 没有这两个用户项目 ⇒ 纯环境问题报 ERROR。改为缺文件即 `skipTest`，换机器不再假红，素材在时仍照常校验。
- 实测（2026-10-25 本机）：`testing\test_comfy_connection_recovery.py` 8 项 OK、`testing\test_design_engine.py` 139 项 OK（skipped=2）。Batch A 16 模块先前 `Ran 304: failures=2 errors=2` ⇒ 现在 0 失败 0 错误；Batch B 26 模块先前 `Ran 354: failures=6` ⇒ 现在全绿；尾段 7 模块 76 项先前已全绿。整轮一次跑完（`QT_QPA_PLATFORM=offscreen` + `run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline`）：**`Ran 734 tests in 382.849s`，failures=0 errors=0 skipped=10，退出码 0**；完整日志 `.director_cache\suite_full_20261025.log`。跳过 10 项 = 2 项本机缺 example 素材 + 7 项需可选运行时 + 1 项既有跳过。
- 慢模块与跑法修正：`testing\test_director_timeline.py`（238 项）每项拉起一个 `design_ai_service.py` 子进程，本机 2 小时以上，整轮请用 `--skip` 排除、需要时单独 `--only test_director_timeline`。先前「整轮 discovery 会莫名吞掉后续模块」是因为没设 `QT_QPA_PLATFORM=offscreen`：Qt 测试在真实桌面上建窗口时 `test_standard_pipeline_regressions` 会以 `0xC0000409` 原生 fail-fast 终止整个进程（该模块本身 15/15 绿）。本轮设了 offscreen 之后整轮 6.4 分钟干净跑完，不再需要分模块分批。
- 副作用提醒：`testing\test_staged_model_driver.py`（16 项）会对**真实** LM Studio / ComfyUI 端点发控制请求（`unload-qwen`、`/free`、VRAM 读数），单模块约 3 分钟，而且会让状态托盘弹「Qwen loaded / Qwen unloaded」气球并触发 auto-resume 通知。它不提交任何生成任务、不占显存跑模型，看到托盘跳动不代表做过实机渲染；实机验证仍以 Smart Render Job manifest + 输出视频为准。
- `director_cut_studio.py`（37492 行）py_compile 通过；本轮未改任何 Relay 编译规则、QC 语义或持久化 schema。
- 状态：**源码已修复 + 单元测试全绿**；Identity Sheet、0.5MP preview、Age Lock、Scene／Wardrobe Lock、0.200 背景纹理门槛、target-similarity 硬门槛、policy 47 全部**仍待实机验证**，尚未产生任何「新视频已实机验证成功」的结论。GPU 验证顺序不变：S4（衣服+背景）→ S10（曾报 no reliable box）→ S3／S5／S7／S11（年龄漂移）→ S1（先换干净 P5）→ 整片。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，Smart Render Policy 保持 `47`。

### 背景纹理门槛 0.200 + 官方字段内 Scene/Wardrobe Lock + 静止条带不再硬拒（2026-10-25，源码已修复，待实机验证）

- `character_swap_engine.PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA` **0.10 → 0.200**（取代上一节写的 0.10）：逐 Shot 实测证明尾巴条款在 0.729-0.960 的角色框面积上早就触发过，S3/S4/S6/S8/S10/S11 的背景仍然长出蜂窝/格纹，所以「有没有挂尾巴条款」不是这些 Shot 的根因；门槛改为保留全部坏背景 Shot（S4 0.800、S6 0.768、S8 0.729、S3 0.856、S10 0.950、S11 0.960、S2 类手动覆盖框 0.241），同时让 S5（0.152/0.177）与远处第二身体（0.047）保持精简提示词。
- 新增 `_author_prompt_with_locks()`：把禁令写进 H3 真正读取的官方模板字段，而不是挂在模板尾部。Scene lock 注入 `<Subject 2>` 的 retention 行（`plain surfaces stay plain`，禁止 lattice/honeycomb/grid/wallpaper motif/dotted texture/embroidery 等 `<Video 1>` 同位置不存在的图案）；Wardrobe lock 注入 `<Subject 1>` 的 retention 行（服装 = `<Picture 1>` 的完整剪裁/层数/配色/滚边/鞋履/手持道具，原服装随身体离开画面，`no substitute outfit may be invented`）。两条都用 marker 幂等插入，anchor 找不到就跳过，绝不抛异常。官方 `H3-Character-Swap-Relay-V2-api.json` 提示词 2873 → 3430 字符（两条 lock 共 +557）。
- `smart_render_worker.inspect_character_swap_identity`：target-similarity 硬门槛在**审核框是近似静止的画面条带**时降级为 review flag。理由是同一条近静止背景条带既会让身份线索误报「V1 演员还在」，也会让 target 相似度量到壁纸而不是演员——S2 的手动覆盖框正是这种墙条。新增 `plate_strip_ambiguous` / `target_similarity_ambiguous` 两个输出字段并在 reason 追加 "target P Picture floor downgraded"；S8 那种身份确实换掉（不产生 ambiguity）的 take 依然 `retry_fresh_seed` 硬拒，S1/S4/S8 类不会被顺手放行。
- 提示词长度实证（`working\measure_manifest_prompt_len.py`，42 份 manifest / 73 条 pass-prompt）：真正送进 H3 并产出画面的最长提示词是 **10275 字符**（S2，policy 46，0.2MP），并非 job 文件里看到的 9551——job 记录永远停在 `pending`， outcome 只在 manifest。加上两条 lock 后最长真实 Shot 预计 ~10830 字符，仍贴近已被实机接受过的上限；合成最坏情境 14725 字符仍属未验证。GPU 首轮若 H3 回 4xx，优先削减 Sheet+近景双条款 Shot。
- 测试：`testing\test_character_swap_engine.py` +2（`test_author_prompt_locks_scene_and_wardrobe_in_official_fields` 断言两条 lock 落在 `detailed_description:` 之前且幂等、`test_identity_sheet_closeup_prompt_stays_within_submitted_ceiling` 断言 Sheet+近景路径 <10800），bloat guard 6000 → 7600；`testing\test_identity_sheet.py` 纹理门槛测试改为 0.200 实测区域带（0.150/0.177 不挂条款，0.241/0.731 挂条款）；`testing\test_smart_render_worker.py::test_identity_audit_treats_static_wall_strip_as_ambiguous_not_failed` 补断言（floor 降级后 `target_similarity_failed=false`、`target_similarity_review=true`、reason 含 "floor downgraded"）。目标模块 **127 项全绿**（41 engine + 18 identity sheet + 12 closeup gates + 7 silent audio + 49 smart render worker，含 1 项既有 skip）；`smart_render_worker.py` / `character_swap_engine.py` py_compile 通过。
- 修正上一节「两文件单独运行通过」的说法：当时 `test_character_swap_engine.py` 里有 **2 项失败**（bloat guard 6000 挡住加长后的提示词、纹理门槛测试仍按 0.10 假设区域带），本轮才修好。
- 测试工具：新增 `working\measure_manifest_prompt_len.py`（按 manifest 结果统计真实提交长度）、`working\run_testing_suite_watchdog.py`（每个测试重置的 `faulthandler` 看门狗，`--skip`/`--only` 可挑选模块，把「整轮 discovery 无限卡住」变成点名卡住的模块）、`working\run_testing_modules_timed.ps1`。实测记录：本机 `test_director_timeline.py`（238 项）每项都会拉起一个 `design_ai_service.py` 子进程，单模块要跑 2 小时以上，是整轮 discovery 看起来「挂死」的真正原因；其余 48 个模块合计 733 项可在十分钟内跑完。
- 状态：**源码已修复 + 目标单元测试全绿**；0.200 门槛、两条官方字段内 lock、target floor 降级、0.5MP preview、Identity Sheet 合成、Age Lock、policy 47 全部仍**待实机验证**。GPU 验证顺序不变：S4（衣服+背景）→ S10（曾报 no reliable box）→ S3/S5/S7/S11（年龄漂移）→ S1（先换干净 P5）→ 整片。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，Smart Render Policy 保持 `47`（本轮只放宽 QC 与加长提示词，不新增强制失效的语义变更，policy 46 的旧 take 早已被上一轮 47 全部作废）。

### Identity Sheet v2 · 小头参考图局部重绘 + 硬 target-similarity 门槛（2026-10-25，源码已修复，待实机验证）

- 逐段取证（policy 46 / 0.2MP 全片 11 段，每段对自身目标 P 图的 colour-histogram 中位相似度）：S1 R1→P5 0.728、S2 0.578、S3 0.554、S4 R2→P6 0.370、S5 0.343、S11 0.463、S6 R2→P3 0.523、S7 0.513、S8 R1+R2→P3 **0.273**、S9 0.310、S10 0.587；导演目视不及格的是「衣服完全不像参考图」S1/S3/S4/S6/S8 与「角色变成老人」S3/S5/S7（40%）/S10（20%）/S11（60%）。S7 0.513、S10 0.587 都远高于旧的非阻断 review floor 0.30，说明颜色线索看得见配色、看不见年龄与脸部漂移；只有 S8（0.273、首次 attempt 就直接通过并拼进 master）属于颜色线索可靠能判的类别。
- 生成端根因：Media Pool 的全身卡通图在 460x642 的 V1 帧里只贡献约十分之一帧高的头部（实测原始 head coverage：P1 0.1097、P2 0.1749、P3 0.1746、P6 0.0644；P4/P5 近景照片 1.377）。头像素不足时 Relay 保住配色却自行发明年龄、脸型与服装——这正是 S3/S5/S7/S10/S11 年龄漂移与 S4/S6/S8 服装漂移的同一根因。
- `project_workspace.PREVIEW_MEGAPIXELS` **0.2 → 0.5**：按钮、菜单、preflight 文案、job 编译与 manifest 全部由常量跟随，无需改调用点。
- `character_identity_sheet.py` 引擎 **v2**：新增公开 `measure_head_coverage()`（把 P 图头部量成相对 V1 帧面积的覆盖率，失败回 `None`，永不抛异常）；compose 会把头部面板放大进格子（preset 0 实测覆盖率提升：P1 0.1097→0.3704、P2 0.1749→0.2994、P3 0.1746→0.3708、P6 0.0644→0.1413、P4 1.377→0.241、P5 1.377→0.245），同一 artwork 的多面板合成、按源图指纹缓存复用。
- 新增 `identity_sheet_page.py`：**Identity Sheet 页面**（左侧 cast 列表 + 缩略图、layout preset 下拉、panel role 说明、覆盖率读数 + 阈值判定、预览、Measure / Compose / Compose all that need it / Export… / Open folder）。纯本地 PIL，不占 GPU、不连 ComfyUI；`set_settings()` 带回声抑制，`closeEvent` 通知宿主；任何异常都降级为提示，不影响主流程。参考 https://github.com/Jalen-Brunson/ComfyUI-H3-Character-Sheets ——上游是尚未安装的 H3 still-model 生成器，本页改为本地合成同等多面板表义。
- `director_cut_studio.py` 集成：Design 页 Identity Sheet 组（开关 + preset，随 binding 表刷新显隐）、`set_identity_sheet_settings()`（preset 以 `SHEET_PRESET_KEYS` 白名单校验、无变化时不标脏）、`open_identity_sheet_page()`（惰性 import、单例缓存、`cast_provider` / `frame_size` / `output_dir=<project>\cache\identity_sheets` 注入）、`note_identity_sheet_page_closed()`；`identity_sheet_enabled` / `identity_sheet_preset` 进入 workspace 保存与载入，restore 与 new/load project 时同样白名单校验并关闭旧页。
- 渲染路径接线：`_character_swap_identity_sheet_reference()` 以该 Shot 的 V1 clip 实际分辨率量头部覆盖率，`coverage < IDENTITY_SHEET_MIN_HEAD_COVERAGE`（0.22）才本地合成 sheet 并把 framing 改为 `illustrated_identity_sheet`；覆盖率 ≥0.22 或任何量测/合成失败一律原图透传（`illustrated_full_design`）。pass spec 同时带 `reference_framing`、`target_reference_path`（H3 实收的 sheet）与 `target_reference_qc_path`（QC 比对的原始 Media Pool 图）。
- `character_swap_engine.build_character_swap_prompt` 新条款：`PICTURE 1 IS ONE IDENTITY SHEET — AUTHORITATIVE`（仅 framing == `illustrated_identity_sheet` 触发：一张图是同一个人不同倍率的多个面板而非多人或房间照片；放大头部面板是脸/眼/眉/鼻/嘴/胡须/肤色/发型/发色/表观年龄的唯一权威，身体与服装面板是比例、整套服装、配色、鞋与手持道具的唯一权威；不得把两个面板读成两个人、不得 A 头 B 身、不得与 V1 演员平均；面板边框/间隔/底板属于包装不得进入画面）；`APPARENT AGE LOCK — MANDATORY`（`not live_action_adaptation` 即卡通媒介时恒定触发：锁死年龄类别、脸部饱满度、皮肤质感、下颌、发际线与体型，禁止加皱纹/垮脸/凹眼/白发/秃顶/更壮框架，也不得借用 V1 演员年龄；年龄漂移即算替换失败，即使配色与轮廓正确）。
- `character_swap_engine` 背景纹理合约门槛改为常量 `PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA = 0.10`：任一角色框面积 ≥0.10 即挂 `NO INVENTED TEXTURE OR PATTERN — MANDATORY`（S2/S4/S6/S8 背景曾出现蜂窝/格纹等 invented pattern）。
- `smart_render_worker.inspect_character_swap_identity`：QC 参考图优先取 `target_reference_qc_path`（原始 P 图）而不是 H3 实收的 sheet；把 target-similarity 从**非阻断 review flag** 升级为**硬门槛** `target_similarity_floor`（默认 0.30，`minimum_target_reference_similarity` 可覆盖，0 关闭）→ 低于 floor 即 `target_similarity_failed=true`、`action=retry_fresh_seed`、reason "output palette never matches the target P Picture"；已通过硬门槛但落在 `TARGET_SIMILARITY_WARNING_BAND = 0.06` 警告带内仍拼装，只标 `target_similarity_review` 并在 reason 追加提醒。
- **Smart Render Policy 46 → 47**（studio 与 worker 同步）：所有已缓存 Segment 失效，下次 Preview/Render 会全部重算——这是条款与 QC 语义变更的必要代价，旧 take 不再被静默复用。
- 测试：新建 `testing\test_identity_sheet.py` 18 项（引擎覆盖率量测与 None 降级、never-throw、sheet 放大头部 + 缓存复用、preset 标签/panel roles、prompt 条款门控、Studio 集成用 `SimpleNamespace` + `probe_media` patch、离屏页面）；重写 `testing\test_smart_render_worker.py::test_identity_audit_hard_rejects_take_that_never_matches_target`（默认 floor 硬拒 + `retry_fresh_seed`、floor 0 关闭、floor 在 sim−0.03 时进警告带、floor 在 sim−0.20 时干净通过）。两文件单独运行通过；`director_cut_studio.py` / `identity_sheet_page.py` / `character_identity_sheet.py` / `character_swap_engine.py` / `smart_render_worker.py` py_compile 通过。
- 备份：`_backup\V0.3.8-alpha.3_identity_sheet_pre_fix_20261024\`。
- 状态：**源码已修复 + 单元测试通过**；0.5MP preview、Identity Sheet 合成、两条新条款、硬 target 门槛、policy 47 全部**待实机验证**。建议顺序：先单 Shot 抽卡验 S4（衣服 + 背景图案）与 S10（曾报 no reliable box），再验 S3/S5/S7/S11 年龄漂移，最后整片。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，Smart Render Policy `47`。

### Workspace Layout · working/ & testing/（2026-10-24，源码已修复）

- 全部临时脚本（`_*.py`、`*_patch*` 等约 130 个）移入 `working\`；49 个测试文件移入 `testing\`。studio 源码无路径引用改动，无需改代码。
- 每个 `testing\test_*.py` 顶部加入 sys.path bootstrap（项目根自动入 path），从任意 CWD 直接运行单个文件或 `-m unittest discover -s testing` 均可；README「## 测试」与交接文档 §8 的运行命令同步改为 discovery 形式。

### Reference-Fidelity Character Swap · 完全按参考图替换 + 多角色 head-band 模糊 + target-likeness review（源码已修复，待实机验证）

- 实机取证（a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9 重渲逐帧分析）：S5 单角色 head_dominant pass（仅 R2 顶部 30% band 模糊、R1 脸可见）= 用户确认完美；S7/S10/S11 multi_role_dominant_closeup_identity_suppressed（两张 plate 脸全部 62% 全脸模糊）全部失败「老人 20-60%」+ photorealistic drift——两张 plate 脸都被抹掉后 H3 失去 pose/identity 锚点，渲染出松散的 P1 真人化「概念」。S4/S6/S8 衣服完全不像参考图（H3 只接受「相似概念」服装）；S7 添加参考图不存在的山羊胡/徽章/花纹；S9 前半段失败后半段成功。
- 根因①多角色 prompt 结构失配：官方 subject_definitions 是单数（"the person being replaced"），grouped pass 只在模板后追加 "Replace each of these N..."，H3 调和差（S7/S10/S11）。
- 根因②无显式整套服装替换条款：base template 只提一次 clothing，既有附加条款全部聚焦头/脸 → S4/S6/S8 服装漂移。
- 根因③medium reinforcement 只覆盖头部（"Rebuild the head..."），而 drift 波及全身/手（S7/S8 photorealistic skin）。
- 根因④无「不得发明细节」绑定：H3 添加 P 参考图不存在的山羊胡/徽章/刺绣；既有 NO INVENTED TEXTURE 条款只针对背景。
- 根因⑤QC 缺口：inspect_character_swap_identity 无最低 target-similarity 门槛——弱 take 照样 passed=True 被静默拼进 master（S1/S4/S8/S11 全部通过）。
- character_swap_engine.build_character_swap_prompt：CLOSE-UP MEDIUM REINFORCEMENT 条款从仅头部扩展到整个可见角色（head, neck, torso, arms and hands），gate 不变（face_dominant_closeup 且非 live-action）；新增 MULTI-PERSON SUBJECT DEFINITIONS — AUTHORITATIVE 条款（仅 len(source_roles)>1 触发：把单数 "person being replaced" 重定义为全部选中 performer，Subject 1 = 单一替换角色逐个替换每个身体、各身体保留自己的位置/pose clock/遮挡顺序、绝不合并换脸）；新增 COMPLETE WARDROBE REPLACEMENT — MANDATORY 条款（每一层服装/图案/滚边/领口/扣件/配饰/色块都来自 Picture 1 design sheet，原 V1 服装不得残留于其下或其上，参考图未画全的服装按同一设计连贯补全、绝不从 Video 1 借用）；新增 NO INVENTED CHARACTER DETAILS — MANDATORY 条款（每个可见细节必须已存在于 Picture 1 design sheet：不加它没有的面部毛发/眼镜/首饰/徽章/刺绣/图案，不删它有显示的细节）。
- director_cut_studio._character_swap_identity_suppressed_source：多角色全 dominant pass（所有 gate row 均为 "dominant"）改用 head-band 模糊（每个框顶部 30%）替代全脸 62%，肩部/躯干/手保留 pose 线索；新策略名 multi_role_head_band_dominant_closeup_identity_suppressed；cache token character-swap-identity-suppression-v2 → v3（旧全脸多角色 plate 自动重生成）。单角色 dominant / head_dominant / medium_silent 行为不变。
- smart_render_worker.inspect_character_swap_identity：新增保守 target-likeness review flag——passed take 的中位 target_reference_similarity 低于 floor（默认 0.30，spec 可用 minimum_target_reference_similarity 覆盖）时标记 target_similarity_review=true 并在 reason 追加 "(low target P Picture similarity; kept for review)"，不再静默拼装；非阻断（S5 用户确认完美于 0.378 → floor 保持远低于它）。
- 测试：testing\test_character_swap_engine.py +5（多角色 subject 重定义触发/单角色缺席、wardrobe contract、no-invented-details contract、whole-character medium reinforcement）、testing\test_character_swap_closeup_gates.py +1（双 dominant 多角色 → head-band 策略名 + ih*0.2766/ih*0.2700 filter 几何、legacy 62% band 缺席）、testing\test_smart_render_worker.py +1（passed take 低 target similarity 被标记 review；spec floor 覆盖后不标记）。三文件共 39+12+49=100 项测试通过（含 1 项既有跳过）；三个源文件 py_compile 通过。
- S1 confounder：P5 参考图自带烧录 UI overlay 文字/图标/字幕（用户侧素材问题），建议重渲 S1 前先换干净 P5。
- 备份：_backup\V0.3.8-alpha.3_reference_fidelity_pre_fix_20261023\（六个文件修复前副本）。
- 状态：源码已修复 + 单元测试通过；全部条款/模糊/QC 改动待实机验证。建议顺序：先 S7/S10 多角色 head-band，再 S4/S6/S8 wardrobe，最后 S1（带 P5 说明）。VERSION 保持 0.3.8-alpha.3，Project Format 保持 29，Smart Render Policy 保持 46。

### S2 Medium-Silent Plate Face Blur · 近景身份抑制扩展到 medium-shot silent pass（源码已修复；条款与模糊已实机生效，指标仍未过）

- 实机取证（preview_995000001，2026-10-23，staged_model_driver）：收紧后的闭唇条款在 prompt 中部与尾部各出现一次并全部生效，但三次 attempt silent_mouth_audit 仍全部 violated（result_motion 0.1985 > max 0.1403），逐帧对比显示 H3 复刻了 P1 design sheet 本身的张嘴大笑表情——身份换对了（target P1 相似度 0.417、source_identity_retained=false、erasure 与 plate continuity 通过），嘴部仍被未模糊的 V1 脸部动态驱动。
- 根因：既有近景身份抑制（plate 脸部模糊）只对已验证 close-up 门生效（dominant / head_dominant）；S2 override 框 [0.42, 0.26, 0.85, 0.82]（w=0.43、h=0.56）两个门都不满足，H3 因此拿到未模糊的 V1 嘴部动态。
- `character_swap_engine.build_character_swap_prompt` 新增 SOURCE PLATE FACE BLURRED — AUTHORITATIVE 条款：identity_suppression_strategy 含 medium_silent_listener 时触发（与 close-up 策略互斥、不会同 pass 双发），明确头部区域是有意模糊、不得从记忆恢复/锐化，只取轮廓供位置/姿态/运动，整张脸按 Picture 1 design sheet 重建；插入 prompt 尾部、最终 SILENT LISTENER contract 重追加之前。
- `director_cut_studio` 新增 `_pass_spec_medium_silent_blur_rows`：silent_listener / no_human_voice pass 中角色框面积 ≥0.12 且高 ≥0.35（与引擎 medium-shot silent 条款同一门）且未命中 close-up 门时，贡献一个 head-and-neck 模糊区域（框顶部 45% 高度、左右各留边距），躯干/手/桌面几何保留姿态线索；`_character_swap_identity_suppressed_source` 在无 close-up 行时回退到该 medium-silent 行，策略名 `medium_silent_listener_identity_suppressed`。
- 调用点重排：身份抑制现在先于 prompt 编译执行，并把 strategy 写回 pass_spec 后再 build_character_swap_prompt——条款与 plate 变体永远同步。
- 测试：testing\test_character_swap_engine.py +3、testing\test_character_swap_closeup_gates.py +4；两文件共 45/45 通过，py_compile 通过。备份：`_backup\V0.3.8-alpha.3_medium_silent_plate_blur_pre_fix_20261023\`（四个源文件修复前副本）。
- 实机重渲（preview_996000001，2026-10-23）：medium-silent gate 触发、模糊 plate 实际上传（head-and-neck 区域可见模糊）、SOURCE PLATE FACE BLURRED 条款嵌入 prompt 一次；target-likeness 排序选中 attempt 3（target P1 相似度 0.546，历次最高；source_identity_retained=false、erasure 与 plate continuity 通过）。但 silent_mouth_audit 仍 violated：result_motion 0.229 > max 0.140——逐帧对比显示 H3 在模糊 plate 上依然画出大幅张嘴大笑（t≈0.3–0.8s 可见牙齿/舌头）：V1 嘴部动态已被模糊消除，剩余根因是 P1 design sheet 本身就是张嘴大笑表情，H3「按 Picture 1 重建整张脸」时把该表情一并复刻并动画化。
- 状态（2026-10-23 更新）：medium-silent plate blur = 源码已修复 + 实机生效（模糊与条款均确认）；S2 silent mouth 指标仍未过，剩余根因指向 P1 参考图自身表情。后备方案：为 silent pass 生成 P1 neutral-mouth 变体参考图（把 design sheet 嘴部修成闭唇中性），或接受该 take 由用户目视裁决。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，Smart Render Policy 保持 `46`。

### S3 Silent Listener Lip-Sync · 根因修复（源码已修复，待实机验证）

- 根因定位（preview_8120188561332373323 渲染取证）：S3 R1→P4 pass 框为全屏 [0.0, 0.003, 1.0, 1.0]，触发 face_dominant_closeup；EXTREME CLOSE-UP SILENT MOUTH 与尾部 SILENT LISTENER PERFORMANCE 条款均在 prompt 中，但三次 attempt 的嘴部运动（result_motion≈0.086）全部超过阈值（max 0.055），best-of-N「retry budget exhausted; keeping target-best take」后仍以 status=complete + character_swap_identity_failed=true 被拼进 master。
- 生成端根因：S3 plate（v1_relay_23627fdd9efc7f006563_1.809-3.650.mp4）带 AAC 原声音轨（mean -19.8 dB），H3 收到的是 R1 自己的原声；旧条款只说「that voice belongs to another character or an off-screen speaker」，对 S3 不成立（可听见的声音正是被替换者本人），H3 因此让新脸跟着自己的原声对嘴。
- `build_character_swap_prompt` EXTREME CLOSE-UP SILENT MOUTH 条款文本修正：明确加入「or the replaced performer's own original Video 1 voice」，并要求把本 Shot 一切可听见的声音当作背景音、不得驱动被替换的嘴（marker 不变）。
- `smart_render_worker` segment 结果新增 `failure_class="silent_mouth_excessive_articulation"`：任一 attempt 的 silent_mouth_audit row violated（该 row 只在 silent_listener/no_human_voice 下产生）时不再留空，Studio 可区分「QC 已知不合格仍被接受」与干净 take；segment status 保持 complete（视频仍可审查）。
- 备份：`_backup\\V0.3.8-alpha.3_s3_silent_mouth_pre_fixes_20261022\\`（两个源文件修复前副本）。
- 测试：testing\test_character_swap_closeup_gates.py 7/7、testing\test_character_swap_engine.py 27/27、testing\test_smart_render_worker.py 46 OK (skipped=1)；py_compile 通过。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`。

### S2 Silent Listener · Plate 原声剥离 + Identity Audit 歧义保护（源码已修复；plate-audio 已过指标级实机验证，ambiguity guard 待实机）

- 根因定位（preview_960000001 渲染取证）：S2 plate 自带的 AAC 原声音轨在 silent pass 下也一直被作为 `ref_audio_0` 喂给 H3，嘴部因此跟随画外对白开合——文本条款只说「never follow the V1 voice」，但可听见的声音正是被替换者本人的原声。S5 正常是因为它是 on_screen_speaker（跟音正确）且带宽 R1 override 框。
- `director_cut_studio._character_swap_silent_audio_source`：silent_listener / no_human_voice pass 上传前剥离 plate 自身音轨，pass_rows 记录 `silent_audio_strategy="audio_stripped"`；A999 在最终装配时恢复 V1 原声轨，静音不损失信息。
- 实机验证（preview_960000001）：上传源确认为 silent 变体 `_silent_a8b7987b…mp4`；3/3 attempts 通过 silent_mouth_audit（result_motion≈0.0016 vs max 0.055，source_motion≈0.0009）；逐帧对比显示新 take 嘴部开合明显小于旧 take（支持性证据，非 100% 定论），待用户目视确认。
- `smart_render_worker.inspect_character_swap_identity` 新增 identity-audit ambiguity guard：retained row 中位 similarity ≥0.95 且 target-likeness <0.25 时，追加测量该区域 plate 自身运动（7 timestamps、size=80）；<0.010 标记 `audit_region_ambiguous`——未变化的背景条带不再单独触发 fresh-seed retry；全部 retained rows 均 ambiguous 时 accept 并留待人工复核（返回 `identity_audit_ambiguity.checked/rows`）。根因：S2 保存的 R1 框 [0.083–0.179, 0.041–0.625] 锚定在画面左缘未变化的墙条/匿名前景人物上（真正的 witness-bench 角色位于 x≈0.42–0.78），identity QC 量到「墙 vs 墙」（similarity 0.98）误报 still matches V1 actor，浪费 2 次 fresh-seed retry。
- 项目数据修复：S2 cue 增加 `source_role_bbox_overrides` R1 [0.42, 0.26, 0.85, 0.82]（镜像用户自绘 S3/S5 宽框做法；identity window 落于脸部区域、mouth window 落于下脸带），`render_cache_revision` 0→1 强制重渲。备份：`_backup\V0.3.8-alpha.3_s2_bbox_override_pre_fix_20261023\`（JSON 修复前副本，语义 diff 已验证仅这两处变化）。
- 测试：testing\test_smart_render_worker.py 新增 2 项 identity-audit ambiguity 测试（静态墙条 → accept + ambiguous row；retained 区域 plate 运动 → 仍 retry_fresh_seed）；89 项目标测试全部通过（含 1 跳过）；director_cut_studio / character_swap_engine / smart_render_worker py_compile 通过。
- 实机重渲（preview_980000001，2026-10-23，staged_model_driver）：job identity_audit 已改用 S2 R1 override 框 [0.42, 0.26, 0.85, 0.82]（identity window 落于脸部区域），source_identity_retained=false（correlation −0.12 / similarity −0.09）——QC 现在量到的是真实角色而非墙条；target P1 相似度 0.403，重试候选按 target-likeness 排序（新排序逻辑实机生效）；complete_actor_erasure 与 plate continuity 均通过（左墙条 similarity 0.935）。ambiguity guard 本次未触发（checked=false），仍待专门实机验证。剩余门槛：silent_mouth_audit 三次 attempt 全部 violated（result_motion 0.191 > max 0.140，source 0.086）→ failure_class=silent_mouth_excessive_articulation；逐帧对比显示新 take t≈0.5–1.0s 出现张嘴帧——可能是真实对嘴也可能是卡通重绘抖动（指标无法区分），待用户目视确认。另注：960000001 的 silent_mouth「通过」（result_motion≈0.0016）量在旧墙条 mouth box 上，部分属于错框假象。
- 状态（2026-10-23 更新）：plate-audio strip = 源码已修复 + 指标级实机验证通过、视觉待用户确认；S2 R1 override 框 = 重渲后指标级实机验证通过（identity QC 量到真实角色，target-likeness 排序生效）；ambiguity guard = 源码已修复 + 单元测试通过、本次未触发、待专门实机验证；silent mouth = 新 take 仍被指标标记（result_motion 0.191 > max），视觉确认中。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`。

### S2 Medium-Shot Silent Mouth · 条款强化（源码已修复，待实机验证）

- 根因定位（preview_980000001 重渲取证）：S2 是 medium shot——R1 override 框 [0.42, 0.26, 0.85, 0.82] 脸部与嘴部清晰可见，但非脸占满画面近景（w=0.43 < 0.55），拿不到 EXTREME CLOSE-UP SILENT MOUTH 条款，只有通用 SILENT LISTENER contract ×2；三次 attempt silent_mouth_audit 全部 violated（result_motion 0.191 > max 0.140，source 0.086），逐帧对比 t≈0.5–1.0s 出现张嘴帧——plate 原声剥离 + 通用条款之后 H3 仍跟随 Video 1 可听对白开嘴。
- `build_character_swap_prompt` 新增 MEDIUM-SHOT SILENT MOUTH REINFORCEMENT 条款：silent_listener / no_human_voice pass、任一角色框面积 ≥0.12 且高 ≥0.35（脸/嘴清晰可见）且非脸占满近景时触发（该情形已由 EXTREME CLOSE-UP SILENT MOUTH 覆盖，两条款不会同 pass 双发）。内容：本 Shot 一切可听声音（含被替换者本人原声）一律当背景音、不得驱动被替换的嘴；全程闭唇、不见牙齿/舌头/下颌，只允许眨眼、呼吸、转头与视线移动。插入位置在 prompt 尾部、最终 SILENT LISTENER contract 重追加之前（与 EXTREME 条款同一机制）。
- 测试：testing\test_character_swap_engine.py 新增 3 项（S2 型 medium 框触发 + 尾部排序；小框 [0.45, 0.62, 0.58, 0.92] 负例只保留通用 contract；speaker pass 不触发），替换旧「medium shot 只有通用条款」断言；该文件 29/29 通过，py_compile 通过。
- 备份：`_backup\V0.3.8-alpha.3_medium_shot_silent_mouth_pre_fix_20261023\`（两个源文件修复前副本）。
- 实机重渲（preview_990000001，2026-10-23）：新条款确认嵌入 prompt 恰好一次并实机生效；但三次 attempt silent_mouth_audit 仍全部 violated（result_motion 0.189 > max 0.140），逐帧对比显示 H3 给卡通角色画了大幅张嘴大笑（t≈0.5–1.1s）。双重根因：① P1 design sheet 本身就是张嘴大笑表情，H3 按参考图重建身份时复刻了该表情；② 通用 SILENT LISTENER contract 的「silent listening reactions」措辞未限定闭唇，且该 contract 在 prompt 尾部重追加、位置晚于新条款，给 H3 留下把反应画成张嘴笑的解释空间。
- 跟进修复：`build_character_swap_prompt` speech_contract 措辞收紧——「allow only blinking, breathing, gaze and silent listening reactions」→「allow only blinking, breathing, head turns and gaze shifts; every silent listening reaction must keep the lips closed — no open-mouth smile, laugh or jaw drop」（该字符串在 prompt 中部与尾部各出现一次，收紧一处两处同时生效）。新增 2 项测试（silent pass 含闭唇反应规则且尾部重追加保留；speaker pass 不含）；testing\test_character_swap_engine.py 31/31 通过，py_compile 通过。
- 备份：`_backup\V0.3.8-alpha.3_silent_contract_tightening_pre_fix_20261023\`（两个源文件修复前副本）。
- 状态（2026-10-23 更新）：medium-shot 条款 = 源码已修复 + 实机生效但指标/视觉仍未过；speech_contract 收紧 = 源码已修复 + 单元测试通过，待重渲 S2 实机验证。若仍失败，后备方案为把近景身份抑制（plate 脸部模糊）扩展到 medium-shot silent pass。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`。

### Round-8 Per-Shot Fixes · S3/S4/S5/S6/S7/S8/S10/S11（源码已修复，待实机验证）

- `build_character_swap_prompt` 新增三条条款（全部只在已验证的近景/plate 几何下触发）：
  - CLOSE-UP MEDIUM REINFORCEMENT：非 live-action pass 且角色框为脸占满画面近景时，禁止向照片/真人渲染漂移；头部必须按 Picture 1 自身媒介重建（线条、阴影风格、色块），不得新增真实皮肤毛孔、次表面光、单根发丝、镜头柔化或胶片颗粒。针对 S5/S10/S11「卡通化 OK 但脸与 P4 不一致」。
  - NO INVENTED TEXTURE OR PATTERN：plate 框面积 ≥0.45 被重绘时，禁止发明重复装饰纹理（格纹/壁纸图案/蜂窝/点阵网格/徽章/刺绣）；Video 1 中素净的墙面与布料必须保持素净。针对 S3 长袍徽章图案 + S4/S6/S8 背景奇怪图案。
  - EXTREME CLOSE-UP SILENT MOUTH：silent_listener pass 且脸占满画面近景时，在 prompt 尾部（最终 Silent Listener contract 重追加之前）强化闭唇指令：全程不张嘴、不见牙齿/舌头/下颌；只允许眨眼、呼吸、转头与视线移动。针对 S3/S6「设定 silent listener 仍对嘴」。
- `_character_swap_identity_suppressed_source` 现对 pass 内每个选中角色独立评估已验证近景门（旧逻辑要求恰好一个角色，导致多人组合 pass 整体跳过抑制）：每个合格角色贡献一个去重后的模糊区域；多区域串联为单一 split/crop/boxblur=18:2/overlay ffmpeg 图，共享同一 plate。单角色 Shot 保留旧策略名（`dominant_closeup_identity_suppressed` / `head_dominant_closeup_identity_suppressed`）；多区域 pass 报告 `multi_role_{gates}_identity_suppressed`。缓存 token 升级为 `character-swap-identity-suppression-v2`。针对 S7/S10/S11 组合 R1+R2→P4/P5 pass「V1 头部残留」。
- 新增共享助手 `_closeup_gate_for_bbox` / `_pass_spec_closeup_gate_rows`：已验证门（dominant：面积≥0.72 且宽≥0.80 且高≥0.82；head_dominant：高≥0.75 且宽≤0.45）的唯一来源，同时供身份抑制模糊与 `strict_temporal_coverage` 使用——组合/近景 Shot 即使事件文本没有 "close-up" 字样也获得严格时间采样。
- `choose_character_swap_identity_candidate` 现按 `_candidate_target_likeness` 排序重试候选：目标 P 图颜色直方图相似度扣除 V1 身份残留折扣（per-role source similarity ≥0.75 时减去 `(retention−0.75)×4 + 0.10`），脸部仍与原演员高度一致的 take 不能再仅凭服装颜色胜出；无 role 数据的候选保持原始分（旧行为保留）。针对 S7「target 相似度最高却仍是 V1 头」。
- 备份：`_backup\V0.3.8-alpha.3_round8_pre_fixes_20261022\`（三个源文件修复前副本）。
- 测试：testing\test_character_swap_engine.py 新增 7 项条款测试；testing\test_smart_render_worker.py 新增 3 项重试选择测试；新增 testing\test_character_swap_closeup_gates.py 覆盖门分类、组合 pass 行、早退路径与多区域 filter 图。VERSION 保持 `0.3.8-alpha.3`，Project Format 保持 `29`，待实机验证通过并经用户接受后再升版。

### Close-up Face Anchoring · 近景脸部身份锚定（S9回归基准已实机验证 · 残留问题已记录）

- `build_character_swap_prompt` 新增 CLOSE-UP FACE ANCHORING 条款：当选中角色框为脸占满画面的近景（宽≥0.55 且高≥0.65）、或高瘦全身站立框（高≥0.75 且宽≤0.45，S9 型）时，强制脸部与头发完全按 P 参考图设计重建；源画面只供给头部位置、姿态、运动、构图与光线方向，禁止两张脸混合成第三张脸、禁止保留原演员头发、禁止从记忆恢复被模糊的源脸。
- `_character_swap_identity_suppressed_source` 新增第二道门：高瘦站立框（高≥0.75 且宽≤0.45）只对框顶部头部区域（30% 高度）做身份模糊；已验证的宽框近景门（面积≥0.72、宽≥0.80、高≥0.82，62% 高度）保持不变。缓存 token 增加 variant 标记避免新旧条目冲突。
- 目标：解决 S6/S7/S8/S9/S10 共同根因——服装换上了但脸/头发向 V1 演员身份回漂。
- S9 回归基准实机验证（2026-10-22，192.168.0.185，staged_model_driver 两次对照运行）：Run-1 仅 prompt 条款 vs Run-2 条款 + head_dominant 部位区域模糊，同 seed A/B。两次均首次尝试通过全部 identity audit；target P1 相似度 0.459 / 0.419（Round-6 基线 ~0.179）；完整卡通转换从 ~3.5–4.0s 提前到 ~2.0–2.5s，服装替换自首帧生效。
- 残留问题（已记录，待用户接受后决定升版）：该 Shot 前 ~2s 仍出现 V1 演员脸（H3 单 window 内时间漂移）；head_dominant 静态盒域模糊在部分帧头部留下矩形 smudge 痕（头部在高窄盒内移动时盒域覆盖不足）。

### Staged Model Driver · Qwen3.8与ComfyUI串行化＋Tray仲裁

- 新增`staged_model_driver.py`，Python分阶段驱动H3任务：子命令`status`／`unload-qwen`／`load-qwen`／`wait-comfy`／`free`／`run JOB.json`／`report`；`run`按固定管线执行`unload-qwen → wait-comfy → worker → /free → report`，Qwen未干净即提前中止，保证ComfyUI与Qwen3.8不同步加载，每次测完以`/free`收尾。
- 定位“unload后load不了Qwen”的根因：LM Studio聊天页会在API卸载数秒后自动重载模型（竞态），叠加ComfyUI占用显存造成共驻死锁；卸载本身没有问题。`load-qwen`现由agent侧显式自载：先查`/api/v1/models`，未加载则发一次最小`chat/completions`探针触发LM Studio自动载入，再轮询目录直到实例出现并报告前后VRAM（不阻断）。
- `load-qwen`模型名依次取自环境变量`H3_STAGE_QWEN_LOAD_MODEL`、`design_ai.env`的`H3_DESIGN_LM_STUDIO_MODEL`或默认`qwen3.8-uncensored-mtp`。
- `h3_status_tray.ps1`升级为双源仲裁：Tray同时监控Qwen（LM Studio目录）与ComfyUI，tooltip／菜单显示“QWEN loaded (agent owns GPU)”或“GPU free for H3”；Qwen已加载且VRAM≥80%时优先警告。
- Tray菜单新增三个手动动作：`Unload Qwen`（逐实例`/api/v1/models/unload`）、`Load Qwen`（chat探针，90秒超时）、`Free ComfyUI (/free)`（`unload_models + free_memory`）；agent与ComfyUI两侧各自自载／自卸，Tray作为中央仲裁。
- 设置对话框新增LM Studio URL（留空时按ComfyUI主机＋端口1234自动推导）与Qwen模型名过滤两个字段，持久化到`tray-settings.json`；LM Studio与ComfyUI不在同一台机器时必须显式填写。
- `192.168.0.185`实测：卸载后VRAM 29.8→2.7GB（约3秒、目录干净）；重载约10秒回到~29.8GB且verified_loaded；驱动单元测试16项全部通过（约0.08秒）。

### Updated 9-Image / 3-Audio / 3-Video H3 API

- Studio主工作流已同步用户更新的`video_minimax_h3_r2v_9image_3audio_3video_api.json`：主UNet切换为`minimax_h3_ref2va_pruned_int8_convrot.safetensors`，旧`MiniMaxH3MemoryEfficientSolAttentionPatch`替换为`SolAttnMiniMaxH3Patcher`。
- 新Sol-Attention图通过`ModelAttentionBackend`继续连接H3 Turbo LoRA；保留9 Picture、3 Video＋配套音轨及3独立Audio的素材容量。
- `CreateVideo`／`SaveVideo`及RTX VSR的新字段保持原API设置；Studio仍会在Preview关闭RTX VSR，并在每个Segment编译时覆盖精确时长、分辨率、steps、denoise及seed。
- API导出时的3秒示例Duration恢复为Studio新项目合同的12秒；实际生成仍按Timeline Segment精确覆盖，不会强制输出12秒。
- 已向`192.168.0.185:8189`确认新Patcher节点、Pruned UNet、Qwen encoder及双VAE全部可用。
- Smart Render Policy升级至`44`，避免误复用旧主H3 API产生的Segment缓存。
- 主Workflow、标准管线、长片可靠性、Character Swap及Smart Render共95项相关测试通过；Python编译检查通过。

### H3 Character Swap Relay V2 API

- Studio默认Character Swap workflow由`akatz-labs-character-swap-turbo8-adaptive-window-api.json`切换为`H3-Character-Swap-Relay-V2-api.json`；V2直接取代旧API，新任务不再编译旧的一体式`H3RelayWindowedEdit`节点。
- Character Swap编译器现会识别并填写V2原生Relay图：`H3RelayPrepareSource`、`H3RelayWindowPlan`、`StartLoop/EndLoop`、`MiniMaxH3ReferenceToVideo`、`BasicScheduler`、`CFGGuider`及`H3RelayFinishWindows`。
- V2会把Studio生成的角色Prompt写入`MiniMaxH3ReferenceToVideo.prompt`，把24fps窗口、history、固定seed及空`seed_overrides`写入`H3RelayWindowPlan`，并按Preview/正式输出选择480/768分辨率。
- Program Monitor改以每次`H3RelayAppendWindow`的原生Loop执行事件推进`Window x/y`，V2不再依赖已经移除的`H3RelayWindowedEdit`进度事件。
- Smart Render Policy升级至`43`，使旧Relay API生成的Character Swap缓存自动失效；重新打开项目后会使用V2重生受影响Segment，而不会误复用V1 workflow输出。
- 旧API仍可读取和编译，仅用于旧保存任务兼容；应用默认路径、部署模型名及节点清单已经更新为V2。
- Character Swap／Smart Render目标测试共53项通过；Python编译检查通过。版本号暂时保持`0.3.8-alpha.2`，Project Format保持`29`，Render Policy为`43`。

## [0.3.8-alpha.2] - 2026-10-19

### SAM3.1 V1 + Generated Character Union Masks

- 修复只使用V1人物Mask时，新角色发型、服装、手臂或身形超出旧轮廓而被裁切的问题；同时修复只使用换角后人物Mask时，V1原人物较大的头发、衣服和身体轮廓残留在背景中的问题。
- 多角色Character Swap现在建立双来源角色遮罩：共享扫描一次干净V1得到原人物Mask，再分别扫描每个H3角色输出得到换角后人物Mask，最终以`V1 Mask ∪ Generated Mask`作为该角色可见合成范围。
- V1 Mask负责完整移除原演员，新人物Mask负责容纳换角后不同的身体比例、发型、服装和动作；联合结果只做轻微边缘扩张及羽化，不再使用整块矩形人物框。
- V1角色框、24fps轨迹和出现时间继续用于SAM对象身份匹配、时间门控及前后景排序；`KEEP V1`与邻近非目标人物不会加入替换角色的联合Mask。
- 每个角色仍从同一份干净V1独立执行H3 Relay，避免后续角色Pass恢复或覆盖前一个替换角色；双角色Layer按V1深度顺序合成，降低同画面角色互盖。
- 新增合成模式`sam31_v1_plus_role_output_instance_masks_v3`。旧固定矩形、V1-only及Generated-only多角色缓存会自动标记Dirty；单角色Shot与无关Segment继续复用。
- Character Swap部署清单新增`sam3.1_multiplex_fp16.safetensors`及`SAM3_VideoTrack`／`SAM3_TrackToMask`节点检查。

### Verification

- 在`192.168.0.185:8189`以双角色V1 Shot完成实际SAM3.1共享V1扫描、两个角色绑定及联合遮罩合成；完成后执行`/free`释放模型与VRAM。
- 51项Smart Render、Character Swap、Shot角色绑定及Relay回归测试通过；Python编译通过。
- App版本升级至`0.3.8-alpha.2`；Project Format保持`29`，Render Policy保持`41`。

## [0.3.8-alpha.1] - 2026-10-19

### Free Remake Engine Selection

- 顶部`Remake Engine`解除只读锁定，用户可以自由选择`Create H3 Remake`、`LoRA Preserve V1`及`LoRA + Reshape Environment`。
- Special Skill仍会提供安全的推荐默认值：`Source Video Cast Remake H3`推荐`LoRA Preserve V1`，其他Skill推荐`Create H3 Remake`；推荐不再是强制路由，选择Skill后仍可手动覆盖。
- 手动Remake Engine选择写入Project、Design Undo/Redo状态及生成fingerprint；重新打开Project、恢复Design或开始Compile时不会再被Skill静默改回。
- Character Swap Relay的实际编译依据当前选择，而不是重新从Skill推导。选择任一LoRA模式都会建立24fps V1 Relay Shot；选择`Create H3 Remake`则走标准H3重制流程。

### Design Reshape Environment

- `RESHAPE ENVIRONMENT / BACKGROUND · KEEP MAPPED CHARACTERS`由禁用说明改为可勾选控制。
- 勾选后，Qwen Design会保留映射P角色、V1动作／表演／时间及同步声音，但根据当前Design Requirement重新设计场景、灯光、背景与环境关系。
- 当前引擎为`LoRA Preserve V1`时，勾选会在Apply后自动切换为`LoRA + Reshape Environment`；取消勾选会安全返回`LoRA Preserve V1`。`Create H3 Remake`保持完整二创路径。
- 修复`a_cartoon_character_with_a_mustache_and_a_yellow_shirt_7`暴露的多人物穿帮：不再把固定矩形人物框直接羽化贴回画面，而是比较干净V1与每个独立角色Pass，建立逐帧人物变化轮廓遮罩；人物框只作为扩大的搜索区域，因此伸出框外的手臂、袖子、头发仍可完整替换，未变化的背景及相邻演员不会被整块覆盖。
- 角色轨迹现在保留`first_frame_index / last_frame_index`。一个Relay Segment内部发生硬切、两个角色先后出现时，每个角色遮罩只在自己的真实出现帧启用，不会再把前后镜头的角色输出同时合成。
- 修复编译器误读`track_samples`而遗漏实际`source_track_samples`的问题；人工调整人物框后也只覆盖空间范围，不再丢掉Qwen逐帧时间证据。
- 旧版`independent_role_boxes`固定矩形缓存会在载入Project时自动标记Dirty，只重做受影响的多角色Shot；其余单角色缓存继续复用。

### Verification

- Remake Engine三模式切换、Skill推荐、Design环境勾选、Project持久化、Character Swap及Smart Render回归测试通过。
- App版本升级至`0.3.8-alpha.1`；Project Format保持`29`，Render Policy保持`41`；本次以合成模式迁移精准失效旧双角色缓存。

## [0.3.7-alpha.20] - 2026-10-18

### KEEP V1 and Character Swap Pass Control

- `KEEP V1`成为明确的零Pass状态：选择后自动取消同排`SWAP`，不向Character Swap Relay提交该人物，只把它加入其他替换Pass的非目标人物保护名单。
- `KEEP V1`不再永久锁死SWAP。用户手动重新勾选时，Studio会恢复该行最近使用的P Picture；没有历史时采用第一个可用P Picture。若Media Pool没有任何P Picture，则保持关闭并显示说明，避免勾选无目标的假Pass。
- 相同P Picture的多个目标角色继续合并为一个Pass；不同P Picture维持模型所需的串行Pass；所有`KEEP V1／无需替换`角色均跳过。
- Character Swap进度明确显示`Segment · Role · Pass · Window`，区分一次Job内部的Relay window，避免把同一Pass的窗口误认成重复生成。
- Shot角色窗口保存后，再点击Shot Visual Editor的`SAVE SHOT`，`REGENERATE DIRTY`及`RUN + QUEUE`都会从最新Shot状态重新编译P Picture、SWAP选择、手动人物框及KEEP设置；只有受影响的Dirty Segment重生。
- 修复Shot Visual Editor保存`Silent listener`后，Source Video Cast Remake自动对嘴路由立即按照旧Qwen speaker ledger恢复成`On-screen speaker`／默认值的问题。
- 新增持久化的Shot人工发声控制所有权：只要用户修改并保存发声状态、嘴形、声音位置、Lip Sync开关、目标角色或时间声源，重新打开Project、`REGENERATE DIRTY`、`RUN + QUEUE`及生成前标准化都必须保留该决定；未手动编辑的Shot仍继续自动路由。
- Timeline Ask Qwen若修改同一组发声字段，也会自动建立人工覆盖，避免生成时被旧分析覆盖。
- App版本保持`0.3.7-alpha.20`；Project Format升级至`29`，Render Policy保持`38`。旧Project缺少新标记时安全默认为自动路由，不需手工迁移。

### Verification

- Shot Visual Editor自动关闭／手动恢复SWAP交互测试、Silent listener保存／序列化／重开／自动路由保护测试、10项Character Swap Engine测试及Python编译通过。

## [0.3.7-alpha.19] - 2026-10-18

### Multi-Person V1 Box Layering and Swap Isolation

- 点击`CURRENT ROLE`会立即将对应V1人物框设为focused并最后绘制，相当于提升至最高z-level；重叠框的边界、控制点及角色标签不再被后续角色遮住。
- 修复角色框绘制控制点后没有重置`QPainter` brush，导致下一人物框以不透明黑色填满并盖住V1画面的问题；focused、selected及普通框现在均使用不同强度的半透明填充。
- 修复多人画面只勾选一位角色时，被错误标记为`the only existing foreground person`的问题；唯一人物判断现在依据画面完整可见角色，而不是本轮SWAP子集。
- 每个Character Swap pass新增其他可见人物的保护身份及位置框，明确禁止修改非目标人物、串脸、身体合并、身份互换或覆盖上一Pass已经完成的替换。
- 增加实际`SAVE SHOT`链路测试：Shot局部P Picture绑定及手动画框会在`REGENERATE DIRTY`时优先覆盖旧Design ledger，同时保持全局ledger及相邻Shot不变。
- App版本升级至`0.3.7-alpha.19`；Project Format保持`28`，Render Policy保持`38`，旧Project无需迁移。

### Verification

- 19项Character Swap、多人保护、V1框层级、半透明绘制、逐帧Detect、Save Shot覆盖及旧ledger回归测试通过；Python编译通过。

## [0.3.7-alpha.18] - 2026-10-18

### Detect V1 People Now Drives Regenerate Dirty

- 修复`DETECT V1 PEOPLE`新增的V1人物只更新Shot Visual Editor／局部框，但Character Swap生成仍依赖旧Design角色ledger，导致`REGENERATE DIRTY`找不到新source role并继续替换旧人物的问题。
- Shot局部`source_role_identity_overrides`及`source_role_bbox_overrides`现在会在每次生成前建立私有analysis overlay：把新R角色加入当前Shot覆盖的scene、补齐Shot专属P Picture binding，并让手动画框覆盖旧Qwen轨迹。
- 局部overlay只存在于当前Relay生成窗口，不会写坏原始V1语义分析，也不会把新角色或框泄漏到相邻Shot。
- 当Shot原本只启用部分角色时，Detect新发现的人物会自动加入SWAP选择；重新打开角色视窗后仍可手动取消。
- App版本升级至`0.3.7-alpha.18`；Project Format保持`28`，Render Policy保持`38`，旧Project无需迁移。

### Verification

- 16项Character Swap、Shot局部角色、逐帧Detect、角色选择、手动框及旧ledger回归测试通过；Python编译通过。

## [0.3.7-alpha.17] - 2026-10-18

### Qwen Role Discovery v2 · 96-Frame V1 Storyboard

- 确认旧Source Video Cast Remake分析最多48帧：场景数不超过24时每场抽取约34% Early及68% Late；超过24场后会突然退化为每场单一Midpoint，超过48场还会均匀删除部分场景，容易遗漏只在场景开头／结尾短暂出现的关键角色。
- 新`Role Discovery v2`将完整V1分析上限提高至96帧，并允许Source分析专用请求向Qwen发送最多6张清晰4×4 Storyboard；普通Design仍保持原来的三图上限。
- 场景数量允许时每场抽取15% Early、50% Midpoint及85% Late三帧，扩大角色进入／离开画面的覆盖范围。
- 中长影片采用渐进式预算：优先保留每个场景，再按全片时间均匀增加Early／Late证据；不再出现超过24场后全部只剩Midpoint的质量断崖。
- 极端超过96个检测场景的素材才会均匀缩减场景，但保留帧会轮换Early／Midpoint／Late，不会全片固定在同一相位。
- Qwen指令明确要求读取sheet 1至sheet 6全部面板，并把只出现于单一时间面板的人物视为有效principal-role候选。
- 新分析使用`role_discovery_v2`版本标记及V4 frame cache；旧48帧Project下次点击Design时会自动重新抽帧及重新运行Qwen，不需重新导入V1。
- App版本升级至`0.3.7-alpha.17`；Project Format保持`28`，Render Policy保持`38`。

### Verification

- 36项媒体抽帧、96帧预算、六图Qwen请求、V1结构化分析、旧取样自动失效及Current Role回归测试通过；Python编译通过。

## [0.3.7-alpha.16] - 2026-10-18

### Detect V1 People Now Creates Visible Current Roles

- 修复`DETECT V1 PEOPLE`已经识别并保存新人物及位置框，但`Character → Unlock All Characters`仍只从旧的全局V1角色ledger建立列表，导致新人物没有出现在`CURRENT ROLE`的问题。
- 新识别的`R`角色现在会立即加入当前Shot的角色绑定列表；即使尚未手动选择P Picture，也会先用可用P Picture作为可编辑建议，不再静默隐藏。
- Shot本地保存的`source_role_bbox_overrides`现在也是持久角色证据；关闭视窗、储存Project或重新打开后，新角色仍会恢复为独立Current Role行。
- Current Role头像优先使用该Shot实际角色框裁切V1画面，不再把旧全局ledger缺少的新角色错误显示成整幅画面。
- 收紧Qwen逐帧角色合并：同一批／同画面的两个人不会只因感知哈希接近而合并；跨帧的同一人物仍可凭脸部、服装与身份描述的组合证据延续同一R编号。
- App版本升级至`0.3.7-alpha.16`；Project Format保持`28`，Render Policy保持`38`。

### Verification

- 18项Current Role、Qwen逐帧检测、多人角色、角色框、重复P绑定及Source Video Cast Remake相关测试通过；Python编译通过。

## [0.3.7-alpha.15] - 2026-10-18

### Reviewed Dirty Preview Is Now the Accepted Take

- 修复在Shot执行`DETECT V1 PEOPLE`并更新角色后，`REGENERATE DIRTY` Preview正确，但`ACCEPT 1.0`再次从原始V1运行Character Swap，导致同一Prompt／P Picture／角色框／seed在不同解析度下重新选错人物、视觉上像退回原装设定的问题。
- Dirty Segment的成功Preview现在是用户已经审核的权威画面；Accept会直接提升该Preview为正式Take，不再向H3重新提交原始V1。
- 若Project已有旧1.0MP Segment，Studio会读取其最终画布，以Lanczos及中心裁切确定性适配审核过的Preview；只改变编码画布，不重新解释人物、角色框或身份。
- Clean Segment继续复用既有1.0MP Take；只有已审核的Dirty Segment使用锁定Preview，因此不会重新生成全片，也不会污染邻近Shot。
- 锁定来源、Preview路径及`reviewed_preview_locked_accept`原因会写入Smart Render Manifest，方便恢复Project及诊断。
- App版本升级至`0.3.7-alpha.15`；Project Format保持`28`，Render Policy保持`38`。

### Verification

- 使用实际失败Project `a_cartoon_character_with_a_suit_and_tie`核对：Preview与Accept的角色Prompt、P3、R4/R5框及seed完全相同，但旧1.0MP重跑把正确替换移到原人物背后；新锁定Take成功由704×704确定性适配为1024×960、24fps。
- Dirty Preview复用／Accept回归测试及Python编译通过。

## [0.3.7-alpha.14] - 2026-10-18

### Completed-Prompt Output Download Recovery

- 修复ComfyUI已经完成H3／Character Swap，但Studio在`ComfyUI connection lost while downloading output`阶段持续重试旧`/view`请求、画面长期停在`0/N completed`的问题。
- 每次下载重试都会建立新HTTP请求；每5秒读取同一`prompt_id`的ComfyUI history并刷新实际filename／subfolder，不会重新Queue或重新生成H3。
- MP4改为1MB分块写入`.part`，验证非零长度及`Content-Length`完整性后才原子替换正式文件，断线或截断文件不会被误当成成功Segment。
- 输出下载恢复独立限制为120秒；超过时间会退出Generating并保留accepted Prompt checkpoint。再次点击`REGENERATE DIRTY`会继续监控并下载原Prompt，不会等待原有3600秒连接恢复上限。
- 修复Dirty Segment被accepted Prompt checkpoint排除的问题；即使该Segment仍标示Dirty，只要fingerprint一致便优先恢复原Prompt。
- Character Swap现在记录进行中的pass及已完成pass输出；下载中断后恢复同一Relay pass，不会重新执行角色替换或重复累积Server Cache。
- App版本升级至`0.3.7-alpha.14`；Project Format保持`28`，Render Policy保持`38`，当前失败Job及既有Segment无需重生。

### Verification

- 34项连接恢复与Smart Render测试通过，另通过Studio Job Builder测试验证Dirty accepted Prompt可恢复；真实ComfyUI Prompt `540dbf57…`的1.27MB Character Swap输出已由新下载器成功读取，未触发新Prompt。

## [0.3.7-alpha.13] - 2026-10-18

### Reliable Large Master Assembly

- 修复`REGENERATE DIRTY`的所有Shot／Segment已经100%完成后，画面长期停在`Assembling ... segments into the master video`的问题。实际失败Project的20个Segment均有效，但Windows FFmpeg一次开启20组Video／Audio输入的巨大`filter_complex`崩溃并留下0-byte `master.mp4`。
- 超过6个Segment时改为安全分批组装：每批最多6段并统一画布、SAR、24fps及音频格式，最后用concat demuxer直接串接批次，不再让20–40条Stream进入同一个Filter Graph。
- 批次Master不会再进行第二次影像编码；最终concat优先`-c copy`，只有极少数Codec／time-base不相容时才以少量批次执行规范化后备拼接。
- Worker逐批回报`Master assembly batch N/M`及最终阶段，完成100%后仍可看见实际进度，不会误以为Studio无反应。
- Windows Worker启用FFmpeg错误框抑制；即使FFmpeg异常退出，也会立即回传明确错误并结束Generating遮罩，不会卡在系统Application Error对话框后面。
- 每一阶段拒绝0-byte输出并清理`.master.assembly-*`临时目录。App版本升级至`0.3.7-alpha.13`；Project Format保持`28`，Render Policy保持`38`，旧Segment可直接复用，不需重新生成。

### Verification

- 既有Overlap裁切、混合解析度／SAR、Native Tail及新20-Segment分批测试通过；并使用失败项目`a_cartoon_character_with_a_suit_and_tie`的真实20段输出完成53.333秒、704×704、24fps、AAC 48kHz双声道Master。

## [0.3.7-alpha.12] - 2026-10-18

### Independent Cache and Resource Refresh Intervals

- Tray Settings把旧的单一刷新值拆分为两个独立选项：`VRAM / DRAM / GPU / CPU refresh`默认5秒，`Cache Folder refresh`默认120秒。
- 资源刷新可设2–300秒；Cache递归扫描可设5–3600秒。Cache TTL只限制大型目录扫描，资源仍按较短周期即时采样。
- Server API回传两项实际刷新间隔；Studio会自动采用资源间隔调整Timer，并在资源Tooltip显示两项设定。
- 旧`refresh_seconds`设定自动迁移为资源刷新间隔；没有旧Cache间隔的安装自动使用120秒，不影响既有IP及Cache路径。
- Installer升级时保留既有API地址、Cache路径与刷新间隔，不再把用户设定重置为默认值。
- App版本升级至`0.3.7-alpha.12`；Project Format保持`28`，Render Policy保持`38`。

### Verification

- 两项默认值与边界Clamp、旧设定兼容、Studio Timer/Tooltip、PowerShell Tray／Installer语法及资源监控回归测试通过。

## [0.3.7-alpha.11] - 2026-10-17

### Configurable H3 Server Status Tray

- Tray右键菜单新增`Settings...`设定页，可调整2–300秒刷新间隔、监听的ComfyUI URL／IP，以及H3 Relay Cache目录。
- IP可直接填写`192.168.0.185:8189`，Tray会自动补上`http://`；储存后立即更新API endpoint及轮询Timer，不需要重启Tray。
- Cache设定同时写入Tray的`tray-settings.json`及ComfyUI custom node的`status-settings.json`；Server API每次请求都会解析设定，Studio与Tray会共同统计新目录，而且换目录时自动丢弃旧路径的30秒统计缓存。
- Server API现在回传实际`cache_path`与目录是否存在；Studio资源Tooltip显示真正监听路径，不再固定显示默认目录。
- 安装器会初始建立两份设定并保存custom node设定位置。App版本升级至`0.3.7-alpha.11`；Project Format保持`28`，Render Policy保持`38`。

### Verification

- 自订Cache路径、错误JSON后备、Studio实际路径Tooltip、Tray／Installer PowerShell语法、Python编译及既有资源监控回归测试通过。

## [0.3.7-alpha.10] - 2026-10-17

### H3 Server Status Tray and Live Resource Meter

- `install_h3_cache_status_server.bat`现在同时安装ComfyUI只读状态API与Windows Tray监控器；Tray以隐藏PowerShell／WinForms进程运行、建立登录自启动捷径，并用Mutex避免重复图标。
- Tray每5秒显示Cache、VRAM、DRAM、GPU、CPU，可右键即时刷新、打开ComfyUI、打开`__h3_removal_cache`或退出；双击图标直接打开ComfyUI。高负载时图标会切换为Warning／Error。
- Server API新增CPU与整机DRAM，以及最繁忙NVIDIA GPU的利用率、VRAM容量与百分比；只返回汇总资源，不返回进程、文件名或用户资料。缺少`psutil`或`nvidia-smi`时对应项目返回`N/A`而不伪造0%。
- Studio的`ESTIMATE`右侧扩展为`CACHE …/100GB | VRAM … | DRAM … | GPU … | CPU …`，每5秒刷新并以Tooltip显示显卡名称、VRAM／DRAM实际容量及Cache细目。
- Cache目录递归统计在Server缓存30秒，因此频繁资源刷新不会反复扫描数十GB的H3 Relay Cache。
- 安装脚本第二参数可指定Tray访问的ComfyUI URL，例如`install_h3_cache_status_server.bat "D:\ComfyUI" "http://192.168.0.185:8189"`。
- App版本升级至`0.3.7-alpha.10`；Project Format保持`28`，Render Policy保持`38`。

### Verification

- Cache计量、双GPU选择、VRAM／GPU CSV解析、CPU／DRAM采集、Studio资源标签、工具栏顺序、Python编译及PowerShell Tray／Installer语法检查通过。

## [0.3.7-alpha.9] - 2026-10-17

### Editable V1 Character Boxes

- `Shot Visual Editor → Character → Unlock All Characters`的人物框现在可以直接拖拽移动，四边及四角可独立缩放；选中或聚焦框显示可见控制点及对应Resize鼠标指针。
- 聚焦一张`CURRENT ROLE`卡后，可在V1画面空白处`Ctrl+点击`加入默认人物框，也可`Ctrl+拖拽`直接画出所需范围，解决半脸、贴边或Qwen漏框人物无法定位的问题。
- `Ctrl+点击`已有框继续用于加入／移除多角色SWAP选择；重叠框循环选择及同排SWAP联动保持不变。
- 新增Shot-local `source_role_bbox_overrides`：手动框随Project保存、Undo/Redo并在重开Project后恢复；Character Swap编译时优先使用手动框并移除冲突的旧Qwen轨迹锚点。
- 手动框只影响当前Shot，不传播到邻近Shot。Render Policy升级至`38`，Director Project Format升级至`28`；Format 27及更早Project会自动以空手动框载入。

### Verification

- 人物框移动、边缘缩放、Current Role后Ctrl新增、坐标保存／重载、Shot隔离、Character Swap Prompt覆盖及既有点击／Ctrl多选回归测试通过。

## [0.3.7-alpha.8] - 2026-10-17

### Edge-Cropped Character Swap

- 修复半脸、半身或贴着V1画面边缘的人物无法被真正替换的问题。实际案例中Character Swap Pass已经执行，但旧扫描把R2位置保存为整屏`[0,0,1,1]`，Relay因而在画面另一边新增P角色并保留原演员。
- 逐帧Qwen人物扫描现在明确识别四边裁切人物，并要求bbox紧贴实际可见脸／上半身；禁止用整屏框代表“不确定位置”。
- Studio、人物框UI及Character Swap编译统一拒绝整屏假框；身份记录仍会保留，不会因为没有可靠bbox而删除Current Role。
- 单人Shot新增强制原位替换契约：锁定唯一现有前景人物，保留原始贴边裁切、位置、比例、动作、遮挡及口型；禁止补全被裁掉的身体、移动到空白区域、保留原演员或新增第二个人。
- 多人Shot继续使用每名演员的有效24fps轨迹框；Current Role、同排SWAP联动及`Ctrl+点击`多选行为保持不变。
- Render Policy升级至`37`，旧Project无需迁移；受影响Segment重新执行`Regenerate Dirty`即可使用新版Character Swap Prompt。

### Verification

- Character Swap单人贴边回归、整屏bbox拒绝、多人空间框、逐帧扫描标准化、Current Role无可靠bbox后备及Python编译检查通过。

## [0.3.7-alpha.7] - 2026-10-17

### Current Role SWAP Coupling and Accurate Person Boxes

- 点击`CURRENT ROLE · V1 SOURCE`卡时，现在会自动勾选同一排的`SWAP`并启用对应`REPLACE WITH`，但不会取消其他已经选择的角色。
- 修复人物框覆盖整个V1画面的根因：逐帧扫描保存的角色头像已经是裁剪图，其`[0,0,1,1]`只代表整张头像；旧逻辑却把它投影回完整V1帧。新版只接受原始V1帧轨迹bbox或非全尺寸Scene证据，绝不再把裁剪头像坐标当整屏人物框。
- 点击Current Role切换到角色专属帧后，会同时装载该帧内所有实际可见且具有可靠bbox的人物；因此可以继续`Ctrl+点击`其他人物框加入新角色。无可靠位置的角色仍保留Current Role卡和画面导航，但明确显示`run DETECT V1 PEOPLE`，不再画假框。
- Project Format保持`27`；旧Project无需迁移。

### Verification

- Current Role同排SWAP联动、同帧多人框保留、Ctrl多选、裁剪头像全屏bbox拒绝、角色专属换帧、无bbox后备提示及Studio编译专项测试通过。

## [0.3.7-alpha.6] - 2026-10-17

### Current Role Driven V1 Frame Navigation

- `Shot Visual Editor → Character → Unlock All Characters`的每张`CURRENT ROLE · V1 SOURCE`卡现在可以点击；点击R角色会自动把上方V1画面切换到该角色在本Shot内最适合辨认的24fps轨迹帧。
- 最佳帧优先采用真实存在的逐帧图像、正面／四分之三脸、较大的有效人物框，再以接近Shot中点作为排序依据；预览下方同步显示实际V1帧号、时间点和当前聚焦R角色。
- 聚焦画面只显示该Current Role的独立位置框，并以黄色高亮；Current Role卡同步显示黄色边框。该动作只用于查看与定位，不会勾选／取消`SWAP`、不会更改`REPLACE WITH`，也不会把Shot标记为dirty。
- 初次打开仍显示整个Shot的所有Current Role框；重复点击画面上的重叠框、`Ctrl+点击`多选及24fps位置轨迹规则保持不变。
- Project Format保持`27`；旧Project不需要迁移。

### Verification

- 角色专属轨迹帧选择、Current Role点击换帧、独立框聚焦、SWAP状态隔离、全角色后备框及重叠人物循环选择测试通过；Studio模块Python编译通过。

## [0.3.7-alpha.5] - 2026-10-17

### Complete Current Role Position Boxes

- 修复`Shot Visual Editor → Character → Unlock All Characters`只在V1画面显示部分R角色框的问题；所有已列在`CURRENT ROLE · V1 SOURCE`的角色现在都必须进入画面点选器。
- 当锚点帧没有该角色的精确检测框时，Studio会使用该Shot内最近的24fps轨迹位置；连有效bbox都没有时则保留全画面后备框，不再静默删除该Current Role。
- 多个R角色共用相同或高度重叠的位置时，框线与标签会错层显示；在同一位置连续点击可按R编号逐一切换，`Ctrl+点击`仍用于多选。
- Project Format保持`27`；本次不改变已保存的人物绑定、Prompt或Character Swap生成路径。

### Verification

- V1人物框精确命中、Ctrl多选、全重叠R角色循环选择及Studio编译专项检查通过。

## [0.3.7-alpha.4] - 2026-10-17

### Current Role Tooltip Contrast

- 修复`Unlock All Characters → CURRENT ROLE · V1 SOURCE`头像鼠标悬停说明出现深色文字叠在深色／半透明背景上、人物资料几乎无法阅读的问题。
- Studio Tooltip统一使用不透明`#071017`深色背景、`#f2f7fb`浅色文字、青色边框、Segoe UI 12px字体及明确内边距；Current Role的场景、时间、人物外观和服装资料现在保持清晰可读。
- Project Format保持`27`；本次只改变显示样式，不改变人物绑定、Character Swap Prompt或生成结果。

### Verification

- Tooltip样式契约与Studio模块Python编译通过。

## [0.3.7-alpha.3] - 2026-10-17

### Interactive V1 Person Picker

- `Unlock All Characters`新增可点击的完整V1 Shot画面，并在Qwen检测到的人物位置显示R角色框。普通点击只选择该人物，`Ctrl+点击`可加入／移除多个人物；下方每个`CURRENT ROLE`亦有独立`SWAP`开关，未选人物保持原V1身份。
- 每个Shot现在持久化可选的`source_role_swap_selection`。Character Swap编译器只为所选R角色建立Pass；空选择沿用旧Project的“全部可见已绑定角色”行为，不破坏既有工程。
- 24fps人物扫描新增Shot-local轨迹样本：保存帧号、绝对时间、人物框及可见区间，并把当前生成窗口的最多六个位置锚点写入H3角色选择器，减少同镜多人、走位及交叉遮挡时换错人的风险。
- `DETECT V1 PEOPLE`即使没有发现新角色，也会刷新既有角色的逐帧轨迹并重新打开人物选择器，不再因“所有人已有绑定”而丢弃本次扫描成果。

### Release and Compatibility

- 应用版本升级至`v0.3.7-alpha.3`；README及v0.3.7部署说明同步加入V1 Person Picker操作方式。
- Director Project格式由`26`升级至`27`，用于保存Shot-local点击人物选择；旧Project自动以“替换全部可见已绑定角色”读取，无需手动迁移。

### Verification

- V1人物框命中、Ctrl多选、Shot-local Pass过滤、轨迹锚点Prompt、角色矩阵保存及Project Format 27兼容专项测试通过。
- Director Studio、Character Swap Engine与测试模块通过Python编译。

## [0.3.7-alpha.2] - 2026-10-17

### Qwen 24fps Shot People Detection

- `Unlock All Characters`的`DETECT V1 PEOPLE`升级为真正的24fps逐帧扫描：Studio完整解码当前Shot，不跳帧建立带绝对帧号／时间码的故事板，并以每32帧一个批次交给Qwen分析。
- 前一批识别的新人物会取得稳定R编号及最佳参考头像并带入后续批次，能够补回短暂出场人物及同镜多人；结果只写入当前Shot的角色覆盖、场景绑定与Character-Swap Pass，只令对应Segment变为dirty。
- 解码与Qwen分析保持异步，界面显示总帧数、当前批次和进度；成功或失败都会关闭进度遮罩。单Shot安全上限为720个24fps Relay帧，超限时明确要求先切分Shot，不会静默抽样或删帧。
- 修复Qwen跨批次遗漏`matched_role_id`时把同一个人按每秒建立成R2、R3、R4的问题。Studio新增本地身份合并层，以脸部视觉指纹、人物描述、服装及相邻帧连续性复用稳定R编号，并合并Qwen指向的旧重复角色别名。
- `Unlock All Characters`改为中间角色矩阵独立滚动、底部Identity Scope、说明及Save／Cancel固定显示；大量Character资料不再把Save按钮推到屏幕之外。

### H3 Relay Cache Capacity Monitor

- Generation工具栏的`ESTIMATE`右侧新增`CACHE 已用 / 100GB`容量指示器，读取ComfyUI Server的`output/__h3_removal_cache`实际占用；启动、ComfyUI URL变化、Estimate及生成结束时自动刷新，并每60秒后台更新。
- 容量状态以阈值提示风险：低于70GB为绿色、70–90GB为琥珀色、90GB以上为红色；Server没有安装容量API或暂时无法连接时显示`N/A / 100GB`，不会把未知状态误报为0GB。
- 新增只读ComfyUI companion `comfyui_director_h3_cache_status`及一键安装脚本`install_h3_cache_status_server.bat`／`.ps1`。API只返回总容量、文件数量及直属子目录汇总，不返回文件名、不删除缓存，并拒绝沿符号链接越界扫描。
- Generation工具栏调整为三行稳定布局，确保窄窗口中`ESTIMATE`与`CACHE`始终相邻可见，不再被Qt原生overflow按钮截断。

### Release and Compatibility

- 应用版本升级至`v0.3.7-alpha.2`；README及v0.3.7部署说明同步记录逐帧人物检测、Cache Meter安装与显示规则。
- Director Project格式保持`26`，已有Project无需迁移；本次容量API与UI显示不会改变生成结果、Character-Swap缓存内容或自动删除任何Server文件。

### Verification

- Cache Status companion、容量格式／颜色阈值、工具栏布局及Qwen逐帧扫描专项测试通过。
- `version_info.py`、Director Studio与Cache Status companion通过Python编译；文档及版本引用完成一致性检查。

## [0.3.7-alpha.1] - 2026-10-17

### Automatic Remake Engine Routing

- Remake Engine改由当前Special Skill单一决定，顶部显示只读`Remake Engine · AUTO`：没有Skill与其他所有Skill使用`Create H3 Remake`；只有`Source Video Cast Remake H3`使用`LoRA Preserve V1`。
- Project载入、Design恢复、Apply及最终Compile都会重新按Skill计算Engine；旧Project保存的Creative／Directed手动值不再造成误路由，其他Skill也不会意外加载Character-Swap Relay。
- `Source Video Cast Remake H3`的环境重塑开关在LoRA Preserve V1路径明确停用；需要重新生成环境时选择其他Skill，交回普通Create H3 Remake编译器。

### MiniMax-H3 Character-Swap LoRA v1.5

- 正式接入`akatz-labs-character-swap-turbo8-adaptive-window-api.json`、`h3_character_swap_v1.5.safetensors`、`LabsH3PrepareVideo`与`H3RelayWindowedEdit`，以24fps V1 Shot板保留源表演、姿势、表情、构图、场景、时间与声音，再按人物卡映射P演员。
- 多角色Shot继续使用逐角色Pass，避免为同一窗口重复生成整套影片；Shot边界隔离、原声窗口、精确V1 Master Audio、听众闭嘴与角色对嘴合同保持生效。
- Character-Swap API需要的H3 UNet、Qwen encoder、两组VAE、Turbo LoRA、FFmpeg及Custom Node已加入README与v0.3.7部署清单。
- Shot Visual Editor的`CURRENT ROLE`现在显示该Shot／时间点实际V1人物脸孔，`REPLACE WITH`才显示目标P图，避免把已经绑定的P误认成源角色。

### Production Baseline and Documentation

- 首次`APPLY TO H3 WORKSPACE → RUN + QUEUE`完整生成成功后，会把全部Production Segment提交为clean基线；之后修改单一Shot，`REGENERATE DIRTY`只处理真正受影响的Segment，不再要求整片重新Preview／Accept。
- 新增[`v0.3.7 readme.md`](v0.3.7%20readme.md)、可直接发布的Character-Swap／自动Remake Engine论坛文章与16:9宣传图。
- Render Policy提升至36；Director Project格式保持26，无需迁移已有Project。

### Verification

- Character-Swap engine与Director Studio通过Python编译。
- 自动路由、Source Skill Relay、多角色Pass、工作流装载及Live-Action Cast开关专项测试通过。

## [0.3.6-alpha.2] - 2026-10-15

### Dirty Segment Repair

- 修复首次`RUN+QUEUE`完成整片1.0MP输出后，只修改一个Shot却在`REGENERATE DIRTY → ACCEPT 1.0M`阶段重新提交全部Shot的问题。首次正式输出现在作为持久化Production Segment基线；修复预览与正式Accept都只生成dirty Segment，clean Segment直接复用并重新组装完整Master。
- 修复Shot Visual Editor及Timeline Ask Qwen默认`Linked Continuity`无条件把前一Shot与后一Shot同时标记dirty的问题。现在只在Incoming／Outgoing Environment State、连续性边界或角色映射确实传播到邻镜时才使邻镜所属Segment失效；普通动作、机位、嘴形或单镜人物调整只影响当前Shot覆盖的Segment。
- `Whole Segment`仍保留明确的整段失效语义；首次Design尚未建立正式Production基线时，普通Preview／Accept流程保持原有完整生成行为。

### Program Monitor

- 修复同时显示V1 `TIMELINE SOURCE`与生成进度时，左侧原生视频表面覆盖`GENERATED OUTPUT`进度卡左半边的问题。生成遮罩现在只属于右侧Generated Output面板，并以该面板独立居中；V1素材保持可见但不再遮挡状态、百分比或进度条。
- 单画面、Segment完成预览及最终输出的播放器结构保持不变；新增离屏UI回归检查，固定验证遮罩父容器与几何范围只属于右侧面板。

### Featured Complete-Video Workflows

- 新增可直接发布论坛的[`Shot Visual Editor + Ask Qwen Step by Step`](forum/Shot_Visual_Editor_Ask_Qwen_Step_by_Step.md)，集中介绍卡片式Shot导演控制、全部Character替换、Qwen字段权限、结构化Patch Review、Timeline全局助手、保存范围及`REGENERATE DIRTY`局部生成流程。
- 主README与v0.3.6重点说明新增`MTV Singing H3`完整歌曲工作流：A1实际可播放长度自动控制全片，P1保持唯一主唱，P2/P3保持非发声陪衬，P4建立统一场景，P5–P9只作为P4派生环境状态；可选A2只作为嘴形时间源，最终声音仍使用A1原曲／Mix。
- 新增可直接发布论坛的[`MTV Singing H3 Step by Step`](forum/MTV_Singing_H3_Step_by_Step.md)，覆盖素材槽位、Audio Separator、Design、0.2MP对嘴检查、Shot Visual Editor、Regenerate Dirty、正式输出、验收清单与常见问题。
- 新增可直接发布论坛的[`Source Video Cast Remake H3 Step by Step`](forum/Source_Video_Cast_Remake_H3_Step_by_Step.md)，覆盖V1完整分析、逐时间脸孔绑定、Director Design、Preflight、原声对嘴、局部重生与最终Master Audio。
- 为`Shot Visual Editor + Ask Qwen`、`MTV Singing H3`及`Source Video Cast Remake H3`三个主题分别生成16:9论坛宣传图，并以项目内相对路径接入README及独立教程，离线复制仓库后仍可正常显示。

### Source-Video Qwen Reliability

- 修复长V1分析返回约100K字符后出现`Expecting ',' delimiter`：Qwen输出改为零温度、短字段Schema和紧凑描述，优先完整返回全部场景与人物出场证据。
- 结构化输出继续限制为32K tokens，避免把预测预算提升至64K后让本地Qwen长时间持续生成并触发worker watchdog。
- Source-Video导演分析改用独立30分钟HTTP时限；watchdog读取当前语义Job的真实timeout，不再固定按普通Design的时限错误终止长片分析。
- JSON截断、缺失场景、漏逗号或worker意外退出会自动进行一次紧凑重试。第二次失败保留`finish_reason`、输出字符数及明确的startup／job timeout原因，不再只显示模糊的`exited with code 1`。

### Verification

- `design_ai_service.py`、`source_video_analysis.py`、`director_cut_studio.py`及专项测试通过Python编译。
- Source Video Analysis 10项测试全部通过，覆盖长JSON缺失逗号修复、32K上限、零温度、完整场景、旧账本升级、视觉输入与指定Qwen模型保护。
- Director Project格式保持`26`，无需迁移已有Project。

## [0.3.6-alpha.1] - 2026-10-13

### Shot Visual Editor

- Character卡片新增安全`Unlock All Characters`矩阵：同时列出当前Shot全部角色，每一行以带缩略图的Media Pool P Picture选择器独立替换，并支持当前Shot、连续镜头及同角色全部出现位置三个范围。
- 多角色保存采用单次原子映射，安全支持`P1↔P2`互换及P1–P9批量重映射，不会因逐项替换产生身份合并或连锁污染。
- 角色替换会写入持久化`character_identity_overrides`，同步精确`@P`引用、AI identity direction与对应V1 Role Binding；目标P未覆盖相关时间时自动建立隐藏H3参考Clip。
- H3 Prompt新增Shot-local强制身份优先级，禁止旧脸残留、混脸、复制或由全局cast order覆盖；整次编辑、绑定同步和参考Clip共用一个Undo事务并只使受影响Segment dirty。

- 双击Timeline Shot现在打开图像化`SHOT VISUAL EDITOR`，把景别、机位、运镜、速度、幅度、主体动作、环境反馈、发声状态、嘴形与声音方位拆成可直接点击的结构化控件；原始／编译文字默认折叠在`ADVANCED`。
- Visual Editor改为完整卡片式工作区：顶部提供带真实素材预览的相邻Shot导航，中央提供Character／Camera／Speaking／Mouth／Voice／Action／Environment卡片，右侧提供Qwen字段权限与Restore Shot；窗口内Undo不会影响主Timeline Undo Stack。
- 新增按需显示的`REGENERATE DIRTY`：Shot、Text Layer、素材映射或Qwen Patch令Segment失效后按钮自动出现并显示dirty数量；点击后自动选择完整Timeline并启动0.2MP Smart Render Preview，只重新生成dirty Segment、复用clean Segment，避免手工抄写Work Area时间且保证Accept后仍为完整Final Master。
- 修复保存并重新打开已有`generated_preview.mp4`／`generated_output.mp4`的Project后，`REGENERATE DIRTY`因Preview seed、分辨率或缓存类型变化而从头生成的问题。Dirty repair现在保留已保存Seed，并跨Preview manifest、Production manifest与持久化Segment Takes恢复clean片段；只有dirty Shot所属Segment进入H3队列。
- Settings新增持久化`Unload all models before Regenerate Dirty / Preview / Accept / Run & Queue` ON/OFF开关（默认ON）。所有H3提交统一在TTS／素材预处理完成后执行一次异步预生成清理：释放ComfyUI模型与VRAM缓存、LM Studio、ACE-Step及SoulX，再恢复原请求；OFF时中央提交入口完全跳过清理。Smart Render Job内部仍保持H3常驻，只在整个Job开始前清理一次。
- 新增持久化`speech_visual_mode`、`mouth_behavior`及`voice_position`。H3编译器优先读取这些结构化事实，不再只依赖Prompt内是否碰巧出现`SPEAKER LOCK`关键词；可明确锁定画内说话者、静默听众、无人声、画外音或镜头后声音。
- 保存范围支持`Shot Only`、`Linked Continuity`与`Whole Segment`。默认Linked模式会把明确的环境边界状态同步给前／后Shot，并使相邻依赖Segment失效；Whole Segment会使实际隐藏Render Segment整体dirty，而非只重算看得到的单一Shot。
- 一次Shot编辑及必要的边界同步被封装成一次Undo transaction；不删除已接受成片，不改变不相关Media Pool素材。

### Timeline Qwen Assistant

- Timeline标题栏新增`ASK QWEN`与可停靠右侧助手，不必返回Design页面即可要求修改Shot、加入VFX、调整Camera、修正声音方位、处理Text Layer／Track或检查Work Area与整个Timeline。
- Qwen只能返回严格Schema的结构化Patch：`target kind + target ID + field + value + reason + risk`。未知ID、未授权字段、重复Patch和嵌套任意JSON会在本地被拒绝；助手不能直接覆盖已经编译的完整H3 Prompt。
- Patch在实际套用前以清单显示，可逐项勾选、Reject或`APPLY SELECTED`。对白原文、Speaker、Language、时间、轨道及Generation Work Area自动列为高影响修改并要求确认。
- Shot、Text Layer、Track与Work Area变更会走同一个Undo Stack。系统依据Assistant Scope将Selected Shot、相邻连续性Shot、完整Render Segment、Work Area或全Timeline标记dirty，避免只改一处却错误复用旧Segment。

### Project Format and Verification

- Director Project格式由25升级至26，用于保存三个新增Shot视觉发声字段；旧Project向后兼容并使用`auto`安全默认值。
- 新增Timeline Assistant纯逻辑与离屏PySide6 UI测试，覆盖严格Schema、未知／重复目标拒绝、高影响确认标记、邻接事实Prompt、字段保存兼容、Visual Editor控件及Patch review清单。
- 修改前建立完整可编辑源码快照`_backups/pre-v0.3.6-alpha.1-20261013-150438.zip`，SHA-256：`C80752A2684C3D55E919FB83E514A300524AAA7C208DF2404A661BFACE3BCF8E`。

## [0.3.5-alpha.17] - 2026-10-12

### V1 Principal Role Thumbnail Binding

- `Source Video Cast Remake H3`的Qwen3.8完整V1分析升级为V5账本：每位主要人物除稳定内部R编号、外观、职责与出场场景外，还为每个出场区间记录独立的early／late／midpoint面板、脸部可见度及近似正方形脸部裁切范围。
- Design新增人物绑定表，只显示正方形V1脸部、逐行独立出场时间及带缩略图的P替换选项，不再向用户显示内部Source Role栏。
- 允许多个源人物映射到同一P图。新增`Keep original V1 face`：选择后自动把对应V1脸部裁切物化为Project内的新P身份素材，供H3在相关Segment使用。
- 遗漏或绑定到不可用图片仍会在Design前明确阻止。映射写入`source_role_bindings`并随Project保存／恢复。
- Director Design与确定性Normalizer共同强制R→P账本；每个Shot依据`active_source_roles`选择人物，原声`speaker_role`及`listener_roles`沿用同一映射，防止角色互换、同脸复制及错误人物对嘴。
- 源人物缩略图仅供UI识别，绝不送进H3。H3仍只接收用户绑定的P身份图及每段V1原声。
- Render Policy提升至32，防止复用旧的顺序猜测人物Segment。

### Verification

- 修复已保存Project的分析版本兼容：V1角色绑定会读取V1–V5账本，不再因为项目仍保存`QWEN SOURCE VIDEO DIRECTOR ANALYSIS V4`而错误报告“没有principal-role ledger”。若旧／部分分析已有完整scene角色证据但遗漏顶层`principal_roles`，Studio会从`active_source_roles`、`speaker_role`与`listener_roles`确定性恢复角色及出场时间卡，不要求用户重复运行Qwen。
- 修复长V1的第二条误挡路径：Qwen V5完整角色／场景JSON不再被Design Context的32K字符摘要上限从中间截断；Preflight依次读取最新选中Context、刷新后的Dialog Context及主工作区实时V1资产，异步分析完成后不会继续校验打开窗口时的旧副本。Design Engine统一复用同一兼容解析器。
- Source Video角色分析升级至Qwen V5：每个角色的每个出场区间拥有独立面板、脸部框与可见度证据；角色绑定改为按时间排序的6列正方形卡片，同一卡片只显示一个时间点。同一角色的卡片初始沿用同一建议P图，之后不锁定、不联动，可逐时间点独立改成不同P图或原V1脸孔；“角色＋场景”映射会进入对应Shot、Speaker与Segment装载。
- 修复69张以上卡片时最后一排仍被裁切：根因是水平`QSplitter`不会把左侧普通子Widget的超高布局传递给外层页面。左侧Design编辑器现改为独立`QScrollArea`，角色表完整展开全部卡片行且不再使用嵌套表格滚动；滚到底时最后一排及状态文字都位于真实布局内，不会画到父容器裁切区之外。
- V1长片的Qwen结构化输出预算由16K提高至32K；对完整JSON中偶发的缺失逗号进行本地受限修复后仍执行全部Schema、场景数量与证据指纹校验，避免`Expecting ',' delimiter`令整次分析中断，同时绝不猜补被截断的内容。
- 新增Qwen V5逐时间点方形脸部裁切字段解析、R1／R2反向绑定P2／P1、重复P映射、原V1脸孔物化为方形P素材、Shot局部人物及原声Speaker锁定回归测试；同步执行Source Analysis、Design Engine、Skill与Timeline重点测试。

## [0.3.5-alpha.16] - 2026-10-11

### Fixed-Cast Original-Audio Remake Contract

- 新增通用“固定演员＋原声重演”识别：当Design Requirement把两个或以上已加载Picture明确设为固定身份，并把`@A`设为原声／唯一声音／主时间线时，Studio会自动进入严格重演模式。
- 原声Audio的实际可播放长度现在是硬时长权威；即使Design模型把53.29秒原声错误扩展到79秒，Studio也会把完整Shot、Reference与Cue重新缩放回原声长度，不再接受由自创对白造成的延长。
- 原声重演会强制清空模型自创的Dialogue／Voice-over／Lyrics Text Layers，防止重复对白、翻译、额外旁白或隐藏语音与原声竞争。
- 所有明确锁定的`@P1–@Pn`都会成为whole-design身份锚点。任何包含人物的Z-Image请求会被自动移除；只允许无人环境／道具空镜。匿名周边群众改由H3按Shot描述生成，且必须保持非说话状态。
- 新Design会排除上一轮失败Design遗留的AI generated Pictures，避免错误替身再次进入规划上下文。
- 为项目`a_woman_with_long_black_hair_and_a_white_top_15`新增53.291秒、16:9、P1–P4固定演员、A1原声驱动的可直接粘贴Design Requirement。

### Verification

- Design Engine 131项测试通过；新增79秒错误计划自动回收到53.290667秒、移除自创Text Layer、删除人物替代图、保留无人餐厅空镜及P1–P4／A1完整绑定的回归测试。

## [0.3.5-alpha.15] - 2026-10-11

### Verified Native Location-Sound Reference Pipeline

- 使用真实ComfyUI `192.168.0.185:8189`对受影响Segment完成三组H3实测：仅加强Prompt仍在对白后产生约0.94秒静音；把TTS与H3雨声作为两条Audio Reference仍产生约0.93秒静音；将准确TTS与H3原生无对白环境床合并成一条完整现场参考后，最终H3输出不再出现静音区，平均响度约`-14 dB`。
- 外部TTS且含画面内Dialogue的Segment现在自动执行低成本`Native Ambience Reference Pass`：沿用同一视觉参考及声景，移除全部Audio reference，强制空人声通道，由H3生成连续环境声和物理Foley；结果按Segment fingerprint缓存。
- Studio随后在提交最终H3前，把精确TTS与缓存的H3原生环境床组成一条完整现场录音参考，取代原来的干TTS loader。最终影片仍由H3一次生成，不在成片后覆盖或重混音轨；重跑相同Segment会复用环境床缓存。
- 修复实际Segment Prompt在`Production mix contract`截断时一并删除全局`CINEMATIC DIALOGUE ACOUSTIC INTEGRATION`合约的问题；含Dialogue／Lyrics的窗口会重新插入完整合约。
- Render Policy提升至30，旧Policy 29的干TTS Segment不会继续复用。

### Verification

- Smart Render Worker 19项、Native Audio／Design Engine 146项及标准生产流程14项测试通过；Timeline完整声学合约专项测试通过。真实服务器验证Prompt IDs：`7136dca9-bb3a-4155-9842-84516e5c07e9`、`dc80dd55-6898-4f32-b283-be2092cb8f0d`、`672293f5-5539-4193-820f-b45ab8baab2e`；最终`1.0 MP + RTX 2× ULTRA`验收为`fb539ec2-1bca-470e-a5e7-4a90f5efe76d`，输出`2752×1536 / 24fps`、平均约`-14.9 dB`且无可检测静音区。

## [0.3.5-alpha.14] - 2026-10-11

### Cinematic Dialogue Acoustic Integration

- 新增全局`CINEMATIC DIALOGUE ACOUSTIC INTEGRATION — MANDATORY`合约，并由`overall_soundscape`及每Shot Native Audio实际提交给MiniMax H3。对白、环境床与Foley必须共享同一空气、方向、遮挡、反射场和空间深度，禁止ADR／配音棚式中央干声叠加。
- 室内声学按可见空间大小、材质、陈设与开口推导早期反射、吸收和衰减；室外不再用简单`0–3% wetness`表示“几乎全干”，而是保留空气吸收、可见地面／湿地／建筑短反射、风雨环境渗漏、距离响度与高频损失。
- 声音透视随景别执行：近景保留呼吸与口腔细节但不隔离环境，中景使用自然交谈比例，远景降低响度和亮度并提高环境声相对比例；镜头移动时连续过渡。
- 新增动作与发声耦合：转头产生离轴方向性与高频损失，跑动／格斗／喊叫改变呼吸、力度与空间投射；仍严格禁止新增未授权文字或音节。
- 外部TTS reference现在明确是原文、Speaker、音色、时序、音素与Lip Sync控制，不是最终干声波形或不可改变的声学渲染；H3必须在保持这些事实的同时重建现场声学透视。
- Render Policy提升至29，避免复用旧的干声对白Segment缓存。

### Verification

- Native Audio与Design Engine 146项测试通过；新增ADR禁止、室外环境占比、TTS非最终干声、转头方向性和完整全局合约测试。Timeline雨景TTS与重复TTS合并专项测试通过。

## [0.3.5-alpha.13] - 2026-10-11

### TTS Reference Deduplication and Music-Level Restoration

- 修复Design物化与Timeline TTS刷新竞态可能占用两个Audio slot，并把同一份全片TTS以A1、A2同时提交给H3的问题。Studio现在从全部资产中按当前TTS签名、有效文件、Timeline状态及A1优先级选择唯一stem；其他重复stem自动设为`bypass`、禁用并移出Timeline，但不删除备份文件。
- Authored Speech Reference合约新增数字静音语义：语句间无声只表示没有人声，不代表静音现场；H3必须在空档及对白下方持续生成相同空间的环境底噪和可见Foley。
- 撤销alpha.12过强的`WEATHER/WATER ENVIRONMENT-PRIORITY MIX LOCK`。MUSIC AUTO恢复标准行为：音乐层清晰可闻，对白时约降低8 dB，对白空档自然回升；环境声和Foley继续保持可闻且不参与对白ducking。
- 现场对白质感由`low environmental bleed`加强为`clearly audible natural environmental bleed`，避免TTS听成脱离场景的录音棚配音。
- Render Policy提升至28，防止沿用含重复TTS reference或旧音乐压低指令的Segment缓存。

### Verification

- 新增重复Authored TTS自动合并、TTS数字静音环境延续及雨景标准AUTO音乐回归测试。

## [0.3.5-alpha.12] - 2026-10-10

### TTS / Native Environment Fusion Compiler Fix

- 修复Studio重新编译Prompt时只传入Shot动作与环境文字、漏掉起止时间，导致`Spatial acoustics contract`退化成`0.00–0.00s`的问题；现在传入完整时间、景别、机位、连续性与项目总时长，缺失时间的旧数据也会安全回退到下一Shot或项目实际结尾。
- Foley英文触发词改为词汇边界匹配，并移除`lock/open/close`等容易与导演术语冲突的单独触发。`stands / punchline / speaker lock / close-up / open-air`不再制造沙石、攻击、门锁或开门声。
- 新增`open rainy exterior`声学类型；雨、暴风与积水镜头持续生成开放空间雨、风、水面和湿地接触声。
- 外部TTS资产不再被Shot级`Audio Reference Intent`误报为“没有音频参考”。每个重叠Shot会声明其仅为精确台词、Speaker、时序、音素与口型stem；H3仍负责生成连续现场环境与同步Foley，并把对白放入可见空间，禁止干录音棚声和重复声音。
- 雨／风／水主导画面在MUSIC AUTO下加入环境优先混音锁：非叙事音乐必须低于现场环境床，且不得在对白空档盖过天气或水声。
- Render Policy提升至27，避免沿用Policy 26下已编译错误声学范围或错误Foley的Segment缓存。

### Verification

- 新增TTS reference intent、雨景声学、Foley子串污染、缺失Shot时间回退与天气环境优先音乐回归测试；Native Audio与Design Engine共144项测试通过。

## [0.3.5-alpha.11] - 2026-10-10

### Native H3 Best-Take Selection and Unison Deduplication

- 修复Native H3 Speech Guard连续三次都发现额外对白时，总是保留最后一个随机重生结果的问题；现在依据违规类型、额外文字长度与人声比例为每次take评分，重试耗尽后自动保留风险最低的一次，仍然不Hard Block整个Job。
- 两个明确`OVERLAP`、时间完全相同且文字完全相同的Dialogue Text Layer现在编译为一个同步齐声事件；H3只收到一次原文，并明确禁止串行复读、回声、改写或追加回应。
- 同步齐声不再完全跳过逐句检查：相同台词只转写检查一次；真正不同内容的重叠对白继续避免单声部误判。
- 授权对白窗口新增“实质改写／不相关对白”检查；Whisper从撞击声或环境底噪误认出的极短英文`you`／`so`不再触发无意义重生。

### TTS Dialogue Loudness

- Edge TTS、Qwen3-TTS与VoxCPM2的每条独立语音在进入Timeline前统一为约`-16 LUFS`、True Peak不高于`-1.5 dB`；只提升干净对白stem，不提高环境声、Foley或背景音乐。
- TTS签名加入响度配置版本，旧项目重新Preview时会自动重建旧的低音量TTS素材。
- Render Policy提升至26，旧Policy 25缓存不会绕过最佳take选择与同步齐声修正。

### Verification

- 新增同步齐声单次编译／单次转写、无关授权对白、短英文Whisper噪声、TTS响度链及Speech Guard最佳take选择回归测试。

## [0.3.5-alpha.10] - 2026-10-10

### Authored-line Repetition Guard

- 修复Speech Guard只检查Text Layer以外静音区、无法发现H3在合法对白窗口内复读同一句或擅自加词的问题。
- Smart Render现在把每条Dialogue／Voice-over的`layer_id、原文、Speaker、Language、Voice Gender及Segment本地时间`写入守卫合约；本机CPU Whisper会逐条转写授权窗口，并以容许简繁体及少量识别误差的字符比对检查实质复读和额外短句。
- 检测到授权窗口内复读或加词时，沿用非阻断策略自动换Seed重生同一Segment，最多两次；重试耗尽只显示WARNING并继续，不Hard Block整项Job。
- 明确设置为`OVERLAP`且时间重叠的多声部对白跳过单句忠实度比较，避免把另一条已授权声部误判成额外台词；共同覆盖区仍受既有授权与静音边界约束。
- 对`two_people_in_a_red_background_with_swords_4`只读验收确认：T1原文只含一次“怎么变成我害了雄霸”，成片在1.00–6.50秒内把该短语重复两次；新守卫准确标记`repeated_authored_phrase`，其余T2–T4没有被误判为复读。
- Render Policy提升至25，Policy 24的旧Segment缓存不会绕过逐句复读检查。

### Verification

- 新增授权窗口复读、Whisper简繁体／同音字容错、守卫合约逐句原文及现有Smart Render自动重试回归测试。

## [0.3.5-alpha.9] - 2026-10-10

### Dialogue Voice Gender

- Dialogue／Voice-over编辑器新增结构化`Voice Gender: AUTO / MALE / FEMALE`；该选择会保存到Text Layer，并传入H3 Prompt、Edge TTS、Qwen3-TTS、VoxCPM2及Windows SAPI后备，不再只依赖自由文字Delivery或Speaker奇偶编号猜测。
- Design JSON为每条语音新增`voice_gender`；只有P1人物证据或用户指示明确时才锁定男声／女声，否则保留AUTO。中文台词的模糊`Chinese`语言标签会统一为`Mandarin Chinese`，避免尾段错误切换成日语或其他语言。
- `comic-talk-show-h3`新增人数边界修复：明确只有两人的P1不会再生成S3；打开旧项目时，超出实际人数的Speaker会依发言顺序回收到有效S1…SN，并同步Authored Text与所属Shot。

### Silent-tail and External-TTS Speech Guard

- Native Speech Guard现在检查项目内所有Dialogue／Voice-over的完整Segment，包括没有任何Text Layer的最终静音Segment；最后一句结束后的尾段若出现日文、旁白、复读或其他无来源人声，也会触发自动换Seed重生。
- Edge TTS、Qwen3-TTS与VoxCPM2项目不再绕过静音区守卫；外部TTS仍是授权声源，但H3在授权窗以外新增的人声会被识别。MTV／Lyrics继续按既有音乐时序处理。
- Render Policy提升至24，旧的Policy 23 Segment缓存不会绕过上述保护；自动重试仍不Hard Block、不停止整项Job。

### Verification

- 新增Voice Gender UI、H3 Prompt、TTS路由、两人旧项目修复、外部TTS静音尾段及语言锁回归测试；Project格式保持向后兼容。

## [0.3.5-alpha.8] - 2026-10-10

### Independent Speech Tracks and Release Gaps

- 每一个Dialogue／Voice-over事件使用独立可见Timeline轨道；即使同一Speaker稍后再次发言也不复用旧轨道，避免一条轨道上的紧贴事件造成覆盖或错误归属。
- H3 Native的`AUTO`重叠策略改为安全顺序排程：相邻普通对白之间自动保留1.0秒闭嘴释放区，并同步顺延后续Text Layer、Shot、素材、已创作要求与实际Project时长。
- 只有明确设为`OVERLAP`的打断、齐声或同时回应保留重叠；Lyrics、MTV和外部TTS原时序不受影响。

### Native H3 Speech Guard · AUTO RETRY

- Smart Render完成每个原生H3 Segment后，以本机CPU Whisper仅检查Text Layer授权区以外的人声静默窗口，不对正确对白重新转写或修改。
- 检测到可辨识的无来源对白时，以确定性新Seed自动重生同一Segment，最多两次；不会Hard Block、不会停止整个Job，也不会在重试间卸载H3。
- 重试耗尽或Whisper不可用时显示WARNING并继续拼接，由用户验收决定是否Reject；检查结果写入Segment manifest。
- 短于等于15秒的原生对白Project同样进入Smart Render守卫路径；Render Policy提升至23，使旧缓存不会绕过新检查。

### Comic Talk Show and Verification

- 更新`comic-talk-show-h3`中英文Skill与Design Requirement模板，明确独立轨道、AUTO顺序语义、1.0秒释放区及环境声／Foley持续规则。
- 新增原生语音排程、独立轨道、单Segment Smart Render及自动重试回归测试；Project保存格式维持不变。

## [0.3.5-alpha.7] - 2026-10-10

### Global Speech Authorization Windows

- 修复短 Dialogue／Voice-over Text Layer 被扩展到完整 Shot 后，H3 在原句结束与下一句开始之间生成即兴、复读、翻译、耳语或无来源对白的问题。
- Design 会按语言、Delivery 与文字长度计算真实发声预算，收紧自动生成台词的授权结束时间；镜头长度、无声表情、环境底噪及 Foley 保持不变。
- Full、Batch 与长片 Segment 编译时统一建立有效语音区间及其补集 `EXPLICIT HUMAN-VOCAL SILENCE WINDOWS`，旧 Project 无需格式迁移即可在重新生成时获得修复。
- 静音 Shot 的实际 Prompt 副本会移除残留的发声状态描述；有声 Shot 加入逐句 Speaker Turn-End Lock，台词结束后嘴形回到闭合／自然状态。
- Lyrics、MTV 主音频及已提供外部 Dialogue／TTS 音频的完整时序保持不变，避免误裁切歌曲或用户已经准备好的声音文件。

### Comic Talk Show Guardrails

- `comic-talk-show-h3` 明确禁止当前 Speaker 在授权原句外即兴、复读、翻译或发出含字笑声，也禁止其他人物提前回答、耳语或背景交谈。
- 对话后的剩余 Shot 时间固定用于闭嘴反应、现场环境声与画面同步 Foley，不改变 P1 动态人数、身份、排列及原始视觉媒介锁定。

### Verification and Documentation

- 新增自动短句预算、旧 Project Prompt 编译、静音 Shot 清理、显式空档及 Talk Show Turn-End Lock 回归测试。
- 更新主 README、`v0.3.5 readme.md` 与应用版本号；Project 保存格式没有改变。

## [0.3.5-alpha.6] - 2026-10-09

### Comic Talk Show H3

- 新增 `comic-talk-show-h3` Special Skill 与可自动填入的 `DESIGN_REQUIREMENT.txt`：把 P1 群像改编为约 45 秒的轮流说段子短片，而不是依赖固定五人模板。
- Design 直接向支持视觉的 Qwen／OpenAI 模型提供 P1 像素，按完整、有意构图的前景主角动态建立从左到右的 `S1…SN` Speaker Ledger；裁切边缘残影、背景人物、海报、反射、雕像与人体模型不会计入主角。
- 视觉请求被模型拒绝时自动回退到文字设计，并加入明确的 Cast Count／Speaker Ledger 人工复核警告，避免整个 Design 流程失败。

### P1 人物与媒介完整性

- P1 现在作为 Talk Show 全片的唯一主角身份、脸部、服装、人数、排列及原始视觉媒介母版；照片、漫画、3D 与插画不会被自动改成另一种风格。
- 普通 Talk Show 自动移除人物图片 `media_requests`，阻止 P2–P9 或 Z-Image 陌生角色覆盖原图人物；编译后的 H3 Segment Prompt 会持续携带动态 P1 群像锁定。
- 每名检测到的主角获得独立、可编辑的 Dialogue Text Layer；Speaker 字段与编辑器支持任意 `S1…SN`，不再硬编码为 S1／S2。
- 只有当前 Speaker 可以发声和对嘴，其他角色只能执行无声表情与视线反应，降低多人同时开口及错误角色代读。

### Documentation and Verification

- 更新主 README 与 `v0.3.5 readme.md`，加入动态人数规则、P1 视觉优先级、模型回退行为及完整操作步骤。
- 新增 Special Skill 载入、动态 Speaker 恢复、Design Prompt 覆盖、P1 群像 Prompt 编译及任意 `S1…SN` 编辑器回归测试。

## [0.3.5-alpha.5] - 2026-10-09

### Native Speech–Environment Fusion

- 修复对白或旁白开始时，H3把持续环境底噪一起降低或完全移除的问题。旧自动Production Mix同时要求环境声与音乐在人声期间降低约6 dB，现改为只有非叙事音乐可以Ducking。
- 新增统一的`NATIVE SPEECH-ENVIRONMENT FUSION`合约：人声必须叠加在持续diegetic environment bed之上，不得替换、门限静音、重置或淡出该底噪；允许自然听觉遮蔽，但禁止对环境声执行增益Ducking。
- 画面同步Foley与有可见原因的one-shot效果在人声期间继续存在；对白结束时不再重新启动环境声，因为环境底噪从未停止。
- H3 Native Dialogue、VoxCPM2、Qwen3-TTS与Edge TTS的Speech Stem统一使用相同融合规则。外部TTS只授权文字、说话者、时序与嘴形，不能成为完整声轨或覆盖现场声。
- Full、Batch及长片Segment使用同一合约；跨段继续继承同一地点的环境底噪，不新增FFmpeg混音、EQ、卷积混响或其他改写H3输出的处理链。

### Verification

- 新增环境声不Ducking、Foley持续、仅音乐可Ducking、Native Audio Direction与外部TTS Prompt合约回归测试。

## [0.3.5-alpha.4] - 2026-10-09

### H3 空人声通道与提示词防朗读

- 修复一个Shot跨越有声与无声区间时，静音Segment仍继承Shot级`natural conversational volume`，与Segment级“无对白”规则互相冲突的问题。
- Full与Batch统一以当前编译窗口内实际存在的Dialogue、Voice-over、Lyrics Text Layer作为唯一生成式人声白名单；没有授权语音时加入`HUMAN VOCAL CHANNEL: EMPTY`硬约束。
- 旧`PromptSpec.dialogue`只保留为设计输入，不再拥有H3发声权限；即使其中残留旧台词，只要对应Text Layer已删除或不在当前窗口，编译Prompt便不会携带或朗读该文字。
- 无语音窗口会从Prompt副本移除Speaker、Speaking State、Dialogue、Narration、Lyrics等发声方向，禁止H3朗读、翻译、拼读或演唱提示词、区段标题、标签、元数据、文件名、参考说明及导演指令。
- 修复只在分段路径写入无语音规则、完整Work Area路径缺少同等保护的问题；旧Project无需迁移，重新生成Prompt即应用新规则。
- 空人声锁不会关闭环境底噪、音乐或画面同步非人声Foley，也不会改写用户保存的Shot Native Audio Direction。

### Verification

- 新增静音尾段、Full Prompt、离线结构化Prompt、保留环境声／Foley及有对白窗口不被误锁的回归测试。

## [0.3.5-alpha.3] - 2026-09-16

### Audio Separator · CUDA 自动部署与输出完整性

- 完成与 SoulX 一致的 Audio Separator 自动角色模式：具备 NVIDIA CUDA GPU、`Kim_Vocal_2.onnx`、模型资料及完整 runtime 的电脑进入本机 `SERVER MODE`，由 Studio 隐藏启动 `127.0.0.1:7862`；其他电脑保持 `CLIENT MODE` 并连接局域网主机，不会静默安装模型。
- 固定使用 `onnxruntime-gpu 1.23.2`，并以真实 `Kim_Vocal_2.onnx` Session 验证 `CUDAExecutionProvider`。健康检查未确认 CUDA 时禁用分离操作，不再静默退回 CPU；旧 CPU runtime 可由安装器安全升级。
- 每次分离在一次性 worker 中运行，Vocal、Music 与原始 Mix 写盘后立即结束 worker；关闭本机 Server Mode 窗口会停止本项目的 7862 API 与残留 worker，Client Mode 不会停止远端共用服务。
- 修复中文、繁体中文、日文等 Unicode 源文件名写入 Latin-1 HTTP Header 时导致上传失败的问题；文件名改以 UTF-8 百分号编码参数传送。
- 修复上游 `audio-separator 0.30.2` SoundFile 写出分支将 C-contiguous 双声道浮点 Vocal 错误截断、扁平化，产生双倍时长近静音单声道文件的问题。现在按 samples×channels 浮点 PCM 正确写出。
- 成功返回前新增 Stem QC：检查 Vocal／Music 时长、声道、RMS 与峰值；时长或声道不一致会失败，近静音 Vocal 会明确警告，避免无效人声继续进入 A2。
- Audio Separator 工作区提供 Vocal、Music、Mix 的独立 Play／Stop／Download，并以固定映射执行 `Music→A1`、`Vocal→A2`；Mix 作为未经改变的项目最终母带保存。

### Documentation

- 新增 `step4.md`，完整说明 Audio Separator / Kim_Vocal_2 的主机与副机部署、CUDA 验收、局域网连接、模型迁移、生命周期及故障排除。
- 更新主 README 与 v0.3.5 重点功能说明，并把应用版本统一提升为 `v0.3.5-alpha.3`。

### Verification

- 通过 Audio Separator 自动模式、CUDA runtime、API、Unicode 上传、Stem 写出与 Project 映射的聚焦测试，以及相关 Director Timeline 回归测试。

## [0.3.5-alpha.1] - 2026-09-14

### SoulX-Singer 独立歌声克隆

- 新增主页 `AUDIO SEPARATOR` 独立工作台（位于 `SOULX` 左边）：通过LAN Server API调用Kim_Vocal_2，一次输出Vocal、Music和未经改变的Mix，支持分别下载；`ADD TO A1 & A2`固定执行Music→A1、Vocal→A2，并把Mix保存为Project级最终MTV母带。
- Audio Separator新增与SoulX一致的自动角色检测：具备CUDA GPU与完整本机安装时进入 `SERVER MODE` 并隐藏启动127.0.0.1:7862；未安装或无CUDA GPU的电脑进入 `CLIENT MODE` 并连接远端Server，无需保留手动BAT窗口。
- Kim_Vocal_2改为强制 `onnxruntime-gpu 1.23.2`。启动时用真实模型Session验证 `CUDAExecutionProvider`，失败即保持操作按钮禁用并显示缺失项，禁止静默回退CPU；旧CPU runtime可由启动器自动原子升级，验证失败会保留原runtime。
- Audio Separator分离继续使用一次性CUDA worker，完成三份输出后立即退出；关闭本机Server Mode窗口会停止项目所属的7862 API与残留worker，释放VRAM/DRAM，Client Mode不会终止远端共用Server。
- 修复中文、繁体中文、日文或其他Unicode音频文件名在上传前触发 `'latin-1' codec can't encode characters` 的问题；文件名现在只通过UTF-8百分号编码的URL参数传递，不再写入仅允许Latin-1的HTTP Header。
- 修复 `audio-separator 0.30.2` 的SoundFile写出分支把C-contiguous双声道浮点Vocal先截断成int16零值、再错误扁平化为双倍时长单声道的问题。一次性Worker现在强制以samples×channels浮点矩阵写入PCM，并在返回成功前验证Vocal/Music时长、声道、RMS与峰值；近静音Vocal会在工作区明确警告，不再以“文件存在”冒充有效输出。
- 取消选择MTV Skill或加载A1时的静默自动分离。分离只由用户明确点击执行，避免完整A1残留人声与A2再次竞争而污染H3口型。
- MTV分离模式会在每个Segment同步推进A1 Music与A2 Vocal的源时间，全部画面完成后才恢复未经改变的Mix；手动替换A1/A2会清除旧Mix绑定，防止跨歌曲母带污染。

- 新增主页 `SOULX` 工作区：使用 Voice Reference 与 Source Song 调用 SoulX-Singer SVC，完成后试听并以 `SAVE AS MP3` 导出；结果不会未经确认自动写入 Media Pool、Timeline 或 MiniMax H3。
- 增加 SoulX 运行模式检测：完整本机 runtime 与模型进入 `SERVER MODE`，自动使用 `127.0.0.1:7861`；未安装电脑保持 `CLIENT MODE`，默认连接 `192.168.0.185:7861`，不自动下载或安装。
- 本机首次安装受严格的单卡显存门槛保护：必须大于 16GB VRAM；安装使用独立 Python 3.10 runtime 与 `models/SoulX-Singer-main`，避免污染 Studio、ACE-Step 或 H3 环境。
- SoulX 转换与安装期间显示全窗口半透明遮罩及青色旋转加载圈，阻止重复点击并清楚提示当前阶段。
- `UNLOAD ALL` 与转换后的清理会先探测 SoulX 卸载 endpoint；官方原始 WebUI 没有该 endpoint 时明确提示需停止／重启 SoulX server，不虚报已经释放显存。本项目自带的 Studio wrapper 提供本机 `/_unload_svc`。
- 修复 Windows 主机安装在包含空格的项目路径时被 `webrtcvad==2.0.10` C 扩展编译阻断的问题；Windows 改用提供相同 `webrtcvad` 导入名的 `webrtcvad-wheels==2.0.14`，Linux/macOS 继续使用官方依赖。
- 修复 Studio-managed SoulX wrapper 将 Gradio 回调名称改成 `lazy_start_svc` 后，Client 仍只查找 `/_start_svc` 而拒绝转换的问题。Wrapper 现在保留官方回调名称，Client 也会按完整参数合约发现兼容 endpoint，可连接修复前仍在运行的 `/lazy_start_svc` 服务。
- 兼容部分 Gradio/SoulX 部署把12个实际输入错误套用10参数 callback 名称、并把最后两项发布成匿名 `param_10`、`param_11` 的情况；Client 改为按照真实组件顺序传送 Device、FP16、Pitch、Steps、CFG 与 Seed，避免 Pitch 值 `0` 被误送进 Device 下拉框。
- 新增 Studio-owned `/_studio_start_svc` 稳定 endpoint，使用固定的12项命名参数并在 Server 内分别适配官方10参数及扩展12参数 SoulX callback；不再让 Gradio 自动命名决定 Client 合约。Server 启用详细错误回传，后台失败会显示真实异常并保留完整日志路径。
- 修复升级后旧 SoulX 进程继续占用7861、导致启动器与 Studio 健康检查误判“Server 已运行”而永远不载入新版 wrapper 的问题。Server Mode 现在必须检测到 `/_studio_start_svc` 才视为健康；新增 `stop_soulx_server.ps1`，按项目路径停止完整 SoulX 进程树、核对7861真实监听PID，并等待端口确认可重新绑定后才启动；非本项目监听器只报告而不停止。`restart_soulx_server.bat` 与隐藏启动器共用这套安全控制。重启器不再以跨行 `^` 传递 PowerShell pipeline，两个 Windows BAT 亦固定使用 CRLF，避免 `Get-CimInstance` 收到字面 `^` 或 `goto` 找不到实际存在的标签。Client 遇到已知0%成功率的旧12输入/10参数 wrapper 时会直接给出升级指引。
- 修复约32GB Blackwell GPU 使用旧 `torch 2.2.0+cu121` 时出现 `CUDA error: no kernel image is available for execution on the device`。SoulX 启动器现在实际建立CUDA tensor并核对设备 capability 是否存在于 `torch.cuda.get_arch_list()`；旧环境不兼容时只重装ABI配对的 `torch/torchaudio 2.7.1` CUDA 12.8 wheel，然后重新验证，无需删除模型或重建整个SoulX目录。新安装也默认使用同一兼容组合。
- 完成 SoulX 模型生命周期：官方WebUI import时建立的初始 `APP_STATE` 会在API绑定后立即释放，使空闲Server保持无模型待命；网页及Studio转换只在请求到来时懒加载。转换、懒加载与卸载共用同一把锁，避免任务执行中途清理。Studio默认在转换完成时调用 `/_unload_svc`；关闭SoulX窗口时再强制释放，本机Server Mode同时停止项目所属的7861隐藏进程树，远端Client Mode则不终止共用Server。SoulX窗口底部会连续显示Runtime、CUDA、模型与API检测阶段，直到 `SoulX API ready`。

### ACE-Step 1.5 Music Workbench

### Documentation

- Reorganized the main README into a concise deployment entry page. Moved the Studio Runtime, Qwen3-TTS and VoxCPM2 guide to `step1.md`, and the ACE-Step 1.5 host/client deployment guide to `step2.md`.

### ACE-Step 1.5 Music Workbench

- Extended the homepage `UNLOAD ALL` action to release all loaded ACE-Step 1.5 DiT/VAE/text-encoder and LM resources through a Studio-managed `/v1/unload` endpoint. The API process remains available and lazily reloads models on the next request; unload is rejected while music jobs are queued or running.
- Closing the Music Workbench now automatically unloads only the ACE-Step models from the exact API connection used by that window. Closing is deferred while an analysis, generation, connection test or installation is active, preventing an in-flight music task from being interrupted before cleanup.
- Added the native `MUSIC COVER` workspace beside the Studio workflow controls. It connects to an ACE-Step 1.5 HTTP API, uploads source and optional timbre-reference audio, analyzes the source, auto-fills editable Prompt, Lyrics, BPM, key, time signature and duration fields, and keeps the complete API response visible.
- Added four source-audio workflows: `Cover`, `Repaint`, `Lego` and `Extract`. Repaint exposes an explicit start/end window, preservation mode and strength. Lego/Extract expose twelve track classes and editable task instructions and automatically select the required `acestep-v15-base` model.
- Added selected-model initialization through `/v1/init`. A first Lego/Extract request can download/load Base; later Turbo/Base changes load the matching model before submission. Base uses an expanded Steps range while Turbo retains its optimized limit.
- Added a full-window translucent busy mask with a centered cyan spinner for analysis, generation and local installation. Generated audio can be played, paused, stopped and saved inside the same window.
- Added all 24 major/minor key presets with sharp/flat glyphs, output volume gain with peak limiting, six voice-age/gender presets, eight regional language-family presets, sixteen animal-sound presets and a 24-instrument multi-select palette.
- Changed Palette behavior so selecting instruments, voices, language families or animal sounds never starts an API job. `REMIX SELECTED PALETTE` runs explicitly; `GENERATE` also applies any unsubmitted selection automatically before generation.
- Corrected source-conditioned duration handling. The client builds an exact-length structural guide before submission and verifies/fits the downloaded result so a requested 120-second output is no longer silently restricted to the original clip length.

### Automatic Client / Server Mode

- Added per-computer ACE-Step runtime detection whenever Studio starts, including when launched through `run_h3_prompt_studio.bat`.
- A computer with a valid local runtime plus an installed Turbo checkpoint/installation marker enters `SERVER MODE`, starts ACE-Step invisibly and uses `http://127.0.0.1:8001`.
- A computer without a complete local installation remains in `CLIENT MODE`, performs no clone, environment setup or model download, and defaults to the shared LAN API at `http://192.168.0.185:8001`.
- Added an explicit `INSTALL LOCAL ACE-STEP` action for eligible Client machines. Installation is never automatic; the action is enabled only when the largest detected NVIDIA GPU has strictly more than 16GB VRAM, then clones the official repository when necessary, creates the isolated runtime, downloads the model and records successful Server Mode setup.
- Updated the launcher with duplicate-server detection, hidden-process support, local logs and safe on-demand Base model loading. Removed the rejected Windows-login scheduled-task approach; server startup is owned by Studio runtime detection instead.
- Kept Director Project format at `25`; these runtime and Music Workbench additions do not change the saved project schema.

### Verification

- Added focused Client/Server classification, strict VRAM-gate, local API selection, model initialization, four-mode request, Repaint window, Lego track, Palette deferral, duration and native-dialog tests.
- Passed the focused ACE-Step suite and the complete Director Timeline regression suite.

## [0.3.3-alpha.1] - 2026-09-12

### Complete AI Movie Making-of / VFX Breakdown / 4DX film format

- Added the Default-bound `ai-movie-making-of-4dx` Special Skill as a complete 45-second-or-longer film format.
- Corrected the format after reviewing `h3_project_291`: replaced the generic Source Photography / Reference Analysis / Character Extraction / Scene Assembly tutorial sequence with a dedicated ten-effect Making-of showcase. The default Timeline now contains an intro, one chapter each for Pitch, Roll, Heave, Wind, Air Shot, Vibration, Impact, Flash, Fog/Smoke and Water/Rain, plus a stable Final Hold.
- Each chapter now reveals a recognizable practical production setup, match-cuts to an original cinematic genre scene, exposes the visible trigger and material response, and creates one linked Physical Event and 4DX Event. All ten controls are selected by default; deselected chapters are omitted and the remaining duration is redistributed.
- Added original demonstration scenarios for fighter-jet pitch, high-speed corner roll, drop/landing heave, tornado wind, near-miss air shot, structural vibration, collision impact, lightning flash, fire-corridor smoke and ocean water/rain. Prompts prohibit copied franchise characters, logos and exact movie-scene recreations.
- Replaced unconstrained Design image expansion with at most one time-scoped Z-Image scene plate per selected effect and no alternate/per-Shot variants.
- Raised the embedded Experience Design schema to version 2 for the chapter-based showcase; the Director Project container remains version 25 and old projects still load safely.
- Corrected the live-experience grammar after reviewing `a_woman_with_long_black_hair_and_a_white_top_11`. Removed all automatically generated Voice-over/Dialogue/Lyrics layers and set this Skill to diegetic 4DX auditorium sound only: screen audio, seat motors, environmental rigs, impacts, clothing/seat movement and audience reactions.
- Changed effect timing from a late short demonstration to a 99% per-chapter active interval. The half-second intro begins inside an already-running auditorium and the half-second Final Hold retains only physically decaying residue.
- Required a purpose-built cinema with visible screen, three or more motion-seat rows and varied effect-specific audience reactions; explicitly rejected the banquet-hall/computer-lab/static-crowd failure seen in the reviewed output.
- Added an invisible FPV spectator camera that translates through aisles and makes wide spatial arcs around reacting audience rows while keeping the screen readable. Visible drones, in-place 360-degree spins, barrel rolls and zoom-out padding are forbidden.
- Added effect-count duration budgeting to the Design controls and managed requirement block: one effect requires 15 seconds and every additional selected effect adds 5 seconds, reaching 60 seconds for all ten. A longer authored duration is preserved; a shorter target is raised automatically, and the resolved value becomes the actual Timeline duration.
- Added a live Design duration status showing selected count, authored target, calculated minimum and resolved duration. `CREATE DIRECTOR DESIGN JSON` now synchronizes this block before generation and sends the resolved duration—not a conflicting shorter sentence—to the planning model.
- Corrected the flat-screen failure found in `a_woman_with_long_black_hair_and_a_white_top_12`. Every selected chapter now carries a deterministic `Screen-Plane Breakout`: one effect-bearing foreground element begins inside the framed movie image, occludes a small part of the visible screen border, and continues with matched perspective, light and atmosphere into the front-row airspace.
- Added a staggered audience-startle chain to the actual H3 Shot prompt: front rows react first in the incoming direction, middle rows follow a fraction later, and rear rows respond with smaller delayed gasps, pointing or social confirmation. Duplicate aircraft, vehicles, people, detached holograms, portals and full-size subjects among the seats are explicitly forbidden.
- Raised the embedded Experience Design schema to version 3 for the structured screen-plane bridge and audience-reaction trigger fields. The Director Project container remains version 25; existing projects continue to load with their saved v1/v2 experience data.
- Versioned the generated scene-plate requirement IDs as `fourdx_screen_breakout_v3_*`, preventing reopened projects from silently reusing an older flat-screen reference image after this upgrade.
- Corrected the audio failure found in `a_woman_with_long_black_hair_and_a_white_top_13`: the global `MUSIC AUTO` setting could regenerate a cinematic score during final H3 compilation even though the 4DX Skill owned `MUSIC OFF`. The 4DX format now forces effective music mode OFF at prompt-panel and segment-compilation boundaries without changing the user's saved preference for other Skills.
- Replaced the generic Native Audio inference that misclassified the 4DX venue as a furnished office. Every 4DX Shot now receives a purpose-built auditorium profile with four concurrent H3-native layers: front-screen event audio, near-field seat/mechanism Foley, directional environmental equipment, and staggered front/middle/rear audience reactions. User-edited Native Audio Direction remains authoritative.
- Added ten multi-select Design controls for Pitch, Roll, Heave, Wind, Air Shot, Vibration, Impact, Flash, Fog/Smoke and Water/Rain, plus independent Intensity and Event Density controls. Changes update one Studio-owned block inside Design Requirement without replacing the user's story.
- Added an authority-ranked reference-role ledger for enabled P/V/A media. Explicit user mapping and uploaded evidence outrank AI Enrich, BLIP and conservative inference; filenames remain transport metadata and never define a landmark, character or scene.
- Added separate structured `physical_events` and `fourdx_events`, linked by stable IDs. A selected effect is planned only when a visible causal source exists; otherwise it is reported as `skipped_no_causal_source`. Camera movement is explicitly excluded as a seat-motion source.
- Compiled every Making-of stage into the actual H3 Shot direction. Exact technical labels are created as editable Studio on-screen-text layers so H3 and Z-Image are not asked to generate UI, HUD or unstable lettering.
- Preserved the native H3 audio boundary: the feature adds no TTS replacement, speech separation, FFmpeg reverb, EQ, convolution reverb or post-generation remixing.
- Persisted preferences, Experience Design, reference ledger and both event families through Apply Undo/Redo and Director Project save/load. Raised Director Project format from `24` to `25`; older projects load with safe defaults.
- Added a release checklist and focused engine/UI/schema/save-load regressions for the new format.

## [0.3.2-alpha.7] - 2026-09-09

### Independent overlapping speech layers

- Added an editable `Overlap Policy` to every Dialogue, Voice-over and Lyrics Text Layer. `AUTO` preserves authored timing and routes a collision to another same-role track; `OVERLAP` explicitly authorizes simultaneous performances; `SEQUENTIAL` moves the later line after earlier speech without shortening either line.
- Added automatic role-specific speech lanes: `D1 / D2...`, `VO1 / VO2...` and `L1 / L2...`. A one-second performance-tail guard also separates immediately adjacent lines, preventing the previous H3 delivery from hiding or cutting the next cue.
- Kept each authored line as an independent editable Text Layer with its own role, speaker, language, delivery, timing, Shot binding, track and overlap policy. Automatic routing never merges, rewrites or truncates authored text.
- Reworked speech-aware Segment boundaries around overlapping speech groups. A later Speaker start can no longer split an earlier line while both are audible; one H3 Job receives the complete authorized overlap and its exact Timeline windows.
- Added `AUTHORIZED SPEECH OVERLAPS` and track/layer identity to the actual MiniMax H3 prompt. H3 is told to preserve the simultaneous performances while prohibiting merged, reordered, duplicated, translated or invented dialogue.
- Applied the new behavior to Design-created layers, Type Tool editing, Timeline tooltips, save/load, TTS job metadata and prompt reconciliation. Old Projects that do not contain `overlap_policy` load as `AUTO` and are normalized in memory before the next save.

### Reusable 60-second cinematic story adaptation

- Added the Default-bound `cinematic-story-60s-director` Special Skill with English and Chinese production instructions plus an auto-filled `DESIGN_REQUIREMENT.txt` template.
- The Skill treats pasted prose as adaptation material, extracts its causal conflict and ending, targets eight to twelve Shots around 60 seconds, generates concise Mandarin Dialogue and Voice-over as independent protected Text Layers, and leaves room for visual action, ambience, Foley and Final Hold.
- Explicit Media Pool references remain the highest visual evidence. Missing identity or scene facts may be designed from the current story without inventing `@P/@V/@A` IDs or generating one reference image for every Shot.
- Speech is compressed before the Timeline is extended; if further compression would damage natural delivery or the central reversal, the owning Shot and all downstream ranges extend together so no speech-only Segment is created.

### Beat-synchronized 19-second character entrance

- Added the Default-bound `beat-synced-entrance-18s` Special Skill with English/Chinese instructions and an auto-filled Design Requirement requiring P1, P2, P3, P4 and A1.
- Corrected the reusable grammar to five causally connected beats: P1 walks around a real corridor corner and meets P2; P2 continues around a second corner and meets P3; an eyeline cut returns to P1, who physically exits to campus and completes an architectural wipe before P4 appears.
- Added a deterministic Design normalizer for this Skill so stale or contradictory model output cannot silently turn P3 into architecture, omit P3, keep fashion-model faces turned away, leak identities across beats, request a redundant corridor image, or describe slow camera movement as final-scene slow motion.
- Passing models now turn naturally toward the lens for a short readable interval. During the campus bridge, the camera faces P1 from outside: P1 crosses the threshold with both eyes readable, shows an unmistakable surprised expression, and only then completes the architectural wipe.
- Added physical per-Segment audio source windowing for ordinary Timeline references. A later H3 Segment now uploads the matching A1 source slice instead of the complete file from source zero, preventing the reproduced 13-second music restart while preserving H3-native ambience and Foley.
- Bumped the internal Smart Render policy to invalidate previously cached Segments built with the restarted-audio behavior; no application version or project-format migration is required.
- Reworked the opening corridor extras as slow, readable activity performers instead of fast passers. Models now use locker/book handling, conversation, shoulder contact, watch checks and side-stepping, while holding a frontal or three-quarter face toward the lens for 1.0–1.5 seconds.
- Replaced the earlier full-scene P4 reset after reviewing `a_cartoon_character_with_headphones_on_5`. Design now creates exactly one P5 Z-Image school-exterior environment-population plate (or reuses a loaded P5), containing the campus exit, road, bus-stop zone and varied dismissal-time background activity.
- Added source-isolated P4+P5 compositing instructions. P5 owns architecture, ground plane, daylight, camera axis and background school-life people; P4 owns only foreground subject identity, appearance, count and arrangement. P4's original background is discarded, and its subjects are relit and grounded into P5 with coherent scale, perspective, foot contact, shared shadows, colour temperature and atmospheric depth.
- Restricted the bridge's final 24 silent frames to architectural-wipe timing and camera-motion continuity. They no longer own or synthesize the final campus environment, preventing the former corridor background from leaking into the P4 reveal.
- Fixed the missing 12.00–14.00-second causal bridge found in `a_cartoon_character_with_headphones_on_4`. Although the Timeline contained the P1 corridor-exit Shot, the former combined H3 request spent its action budget on the character encounters and omitted the two-second transition.
- The entrance Skill now compiles exactly three Render Segments: 0.00–12.00, 12.00–14.00 and 14.00–19.00 seconds. The middle Segment hard-resets to P1, starts with P1 already crossing the exit, visibly establishes P5's outdoor campus, rounds the adjacent corner and ends only after a full architectural wipe. The final camera uses a very slow horizontal slide instead of FPV or orbit.
- Removed the contradictory template rule that required the corridor to remain unchanged through Beat 4. Corridor continuity now ends after Beat 3; Beat 4 explicitly performs the indoor-to-outdoor change.
- Raised Smart Render policy to 22 so Segments cached under the former encounter, back-only campus exit, corridor-leaking P4 reset or policy-21 Motion-Reference-owned environment grammar are regenerated instead of being silently reused.

### Compatibility and verification

- Raised Director Project format from `23` to `24` for the persisted Text Layer overlap policy. The addition is backward compatible; no media, Take or approved Segment file is deleted during migration.
- Verified two complete 169-test suites: Timeline/UI/save-load/render-state coverage and Design/Prompt/Segment/Standard Pipeline coverage. All four modified runtime modules also pass Python bytecode compilation.

## [0.3.2-alpha.6] - 2026-09-08

### Hong Kong Comic Fighter production grammar

- Added `hong-kong-comic-fighter` as a reusable image-led Hong Kong manhua production profile. Loaded panels and explicit user mappings own character, costume, location, weather, palette and material facts; filenames and Skill examples cannot silently replace the current source world.
- Added comic-to-live-action source-plate rules: original printed pages remain analysis-only, while the minimum required photoreal identity and action-state keyframes use traceable source-image derivation instead of unconstrained text-to-image substitution.
- Reworked short combat pacing around immediate superhero pressure arrival, full-speed causal exchanges and persistent world-scale force from the first active attack. Every Beat must expose load, attack line or grip, defence, contact or miss, force, displacement, source-grounded environment response and the next trigger.
- Added action-triggered close moving-camera coverage, source-derived material/weather propagation, synchronized native technique sound, editable move-title/text layers and a stable causal final resolve. Fixed-market scenery, arbitrary spectators, graphic energy rings, slow-motion padding and non-causal background explosions are prohibited unless the current source or user explicitly requires them.
- Added a reusable universal Design Requirement and a complete 27-line narration/dialogue production script for the current Hong Kong comic workflow.

### Timeline Voice-over language control

- Added an editable `Language` field to every Timeline Voice-over layer. The selector includes Auto, Mandarin Chinese, Cantonese, Malay and the stable H3 dialogue-language set; custom values remain editable for forward compatibility.
- Persisted the selected language through Director Project save/load and passed it unchanged into H3 text ranges and the selected TTS job. Voice-over clips now expose their active language in the Timeline tooltip.
- Editing a Voice-over language no longer resets its hidden Speaker, Delivery or Shot binding. Lip synchronization remains Dialogue-only, while Lyrics also gain the same per-layer language control.
- Added regressions for Voice-over field visibility, value preservation, old-project restoration and H3 prompt/TTS data flow. The full 168-test Timeline suite passes.

### Compatibility

- Kept Director Project format at `23` because the persisted `language` field already existed in the schema; old projects therefore require no migration and retain their previous language/default behavior.

## [0.3.2-alpha.5] - 2026-09-06

### High-density Combat Action Continuity

- Added the structured v2 combat ledger: authority-ranked P1/P2 facts with BLIP/AI Enrich provenance, five duty labels per 15-second window, strict physical action-carrier routing, action-triggered FPV camera directions and screen-space force vectors. The new fields are additive and remain compatible with existing Director Project files.
- Material responses now consume the force vector and a material response table (water, ice, plastic, metal, hanging hardware, tank frames and carts), so splash, skid, dent, swing and roll directions follow the visible contact instead of a generic round-robin effect.

- Fused the useful causal/state ideas from the reviewed high-density fight reference into the existing Studio JSON workflow without importing its unrelated BUNNY wrapper, dual-format output, weapon/creature/giant routing or third-party platform contracts.
- Added a Street-Fighter-only Combat Action Continuity engine. Each Shot now carries two numbered executable Beats plus editable Combat Action Chain, Incoming Combat State, Outgoing Combat State and Next Action Trigger data; clear self-defence actor errors are corrected, while repeated exchanges and unexplained ground-position reversals are flagged.
- Standardized the proven 45-second baseline at six executable action Shots per 15-second Segment: 18 Shots and 36 non-repeating Beats. Dialogue may still extend the final Timeline, but combat timing and the indoor-to-outdoor threshold remain anchored to the authored 45.00-second baseline.
- Added red `ACTION RISK` visibility in Timeline and Storyboard, along with full Combat state editing in the Shot inspector. Storyboard reorder/trim reruns Combat state before Environmental state in the same Undoable transaction.
- Compacted actual H3 Segment prompts so FPV, P1/P2, market and causality invariants appear once at Segment level; Shot descriptions retain only executable action and local state deltas. Timeline source text remains intact and editable.
- Improved environment-target causality: authored stall, gate, tank, ice, crate, scale, puddle, awning, cart or bin contact now overrides round-robin prop selection. A dialogue extension no longer shifts the 30.0-second market-gate transition.
- Raised Director Project format to `23` for persisted Combat Action Continuity fields. Older projects load with safe defaults and can acquire the new state through a fresh Design Apply or Street-Fighter Storyboard Apply.
- Verified the completed integration with 508/508 bundled tests and all 13 Standard Pipeline Release Gates, including Storyboard/Segment Mapping and project save/reload coverage.

### Environmental Combat Physics

- Added a deterministic, Timeline-owned environment state engine for `street-fighter-live-action-h3`. Each Shot now carries an editable cause/contact record, one primary response, at most one secondary response, delayed perimeter-crowd reaction, incoming state, outgoing state and location transition.
- Assigned stable environment object IDs and persistent damage/displacement history. Missing contact produces a warning instead of spontaneous destruction; critical collapse and unrelated explosions are never authored automatically.
- Compiled the structured environment fields into every real H3 Segment prompt, in addition to the existing visual action and continuity text. User-edited environment fields are protected from later automatic reconciliation.
- Added Timeline warning/transition colours, Storyboard interaction/crowd/route badges and a scrollable Shot editor for the new fields. Storyboard and Smart Cut Apply recalculate the chronological state chain inside their existing single Undo transaction.

### Indoor-to-outdoor combat continuity

- Reworked the 45-second Street Fighter route into one connected Hong Kong Kowloon-style wet market: indoor seafood aisle, fish/vegetable junction, loading threshold, then the rainy exterior service alley beyond the same visibly forced-open gate.
- Time-isolated Z-Image into one indoor environment/spectator plate for the first two thirds and one matching exterior plate for the final third. P1 and P2 remain the only principal fighter identity anchors; each Segment receives only its currently relevant background plate.
- Added distinct H3-native acoustic profiles for the cramped indoor market and open rainy alley, including a doorway transition from pumps, drainage and short stall reflections into rain, traffic and reduced enclosure. No TTS replacement, FFmpeg reverb or post-generated remix was added.
- Updated the English/Chinese Skill and its editable `DESIGN_REQUIREMENT.txt` with causal object/crowd response, persistent state and active-combat route rules.

### Compatibility and cache safety

- Raised Director Project format to `22` for persisted environmental fields at the original alpha.5 checkpoint; the later Combat Action Continuity addition above advances the current format to `23`. Older Projects load with dataclass defaults, while unknown future Director Cue metadata is safely ignored instead of causing an `unexpected keyword argument` load failure.
- Kept Smart Render policy at `16`: the new environment fields are part of the per-Segment prompt fingerprint, so affected Street Fighter Segments invalidate precisely without discarding reusable cache from unrelated projects or Skills.
- Added focused environment-engine, native-acoustic, real-H3-prompt and Storyboard/Undo regressions. The original checkpoint passed 493/493 bundled tests; the current Combat Action Continuity checkpoint passes 508/508 bundled tests, 13/13 Standard Pipeline Release Gates and the UTF-8 Skill Creator validator. Full acceptance evidence is tracked in `V0.3.2-ALPHA.5_ENVIRONMENTAL_COMBAT_ACCEPTANCE_CHECKLIST.md`.

## [0.3.2-alpha.4] - 2026-09-05

### Global Design duration safety and image-generation regression release

- Applied the duration-range disambiguation globally to Design with no Special Skill and to every Special Skill, so camera angles, pixel ranges, percentages, frame counts and image dimensions cannot inflate the authored video duration or trigger runaway Picture generation.
- Preserved the existing reference-planning policy: ordinary Design remains story-, dialogue- and Shot-aware with an approximate five-second fallback coverage floor; only the two Drone Skills enforce an exact P1-derived five-second Picture chain.
- Kept the Virtual Media Pool unlimited at project scope. The physical 9 Image / 3 Video / 3 Audio limits remain Segment-local and are assigned dynamically during workflow compilation.
- Fixed the equivalent Segment prompt-scoping collision: bracketed camera degrees, pixel ranges, percentages and frame counts now remain visual instructions instead of being rebased or deleted as if they were Timeline ranges.
- Added this release checkpoint for focused Design-to-Timeline, Storyboard, Segment reference mapping, Workflow loader and Drone P1/P2/P3+ regression verification.

### Transactional post-Apply RAM/VRAM cleanup

- Moved Design cleanup behind the durable `APPLY TO H3 WORKSPACE` commit. The Design dialog now queues cleanup intent; Timeline, Mapping and Workspace persistence finish before any model is unloaded.
- Added local Python garbage collection plus ComfyUI `/free` with `unload_models=true` and `free_memory=true`, followed by a deferred Qt-side collection pass. LM Studio unload remains limited to an actually loaded matching instance.
- A failed Apply cancels its queued cleanup. Cleanup warnings never roll back a successful Apply, and temporary cleanup job files are removed after completion or worker-start failure.
- Added regression coverage proving cleanup remains idle while queued, starts only after the success gate and is discarded after a simulated Apply failure.
- Added a homepage `UNLOAD ALL` control beside `STORAGE` for safe manual Studio DRAM/cache cleanup, ComfyUI model/VRAM release, and unloading every LM Studio model instance actually reported as loaded.

### Sequential ground-launch / orbit / route FPV mission

- Updated both `drone-fly-on-city` profiles so the executable H3 camera instruction uses three ordered phases: near-ground P1 takeoff, one translated 360-degree orbit around P1's primary scene subject, then verified P2 route travel to its endpoint. Orbit and route movement are no longer issued simultaneously.
- Replaced the ambiguous orbit sentence with a physical flight contract: one complete, smooth, wide clockwise lap at a constant safe radius, advancing through front, right, rear, left and front positional checkpoints while background parallax proves translation.
- Removed the subject-centred look-at instruction that still made the camera appear to rotate around the landmark. The rigid FPV camera now follows the drone nose and instantaneous flight tangent; it cannot independently yaw, pan or gimbal-lock toward the landmark, which moves naturally along the inside frame edge and may pass behind the camera.
- Explicitly rejected in-place camera rotation, panoramic yaw, optical spin, barrel roll and rotating-background interpretations during the orbit. The orbit permits moderate coordinated banking only; dives, inversion and up to 180-degree rolls are delayed until the later verified-route or FPV-fallback phase.
- Expanded the 12-second orbit budget from the former 3.5 seconds to 7 seconds (0–2 launch, 2–9 orbit, 9–12 route) and added a hard phase-completion gate. The 15-second fireworks template uses 0–2, 2–10 and 10–15 seconds.
- Restored the executable Scene Keyframe Chain marker so Drone renders split at each five-second boundary. Each interval now uses only its exclusive current P1-derived scene state instead of loading P1 plus P3/P4/P5 together, preventing Ref2VA from multiplying one landmark reference into repeated buildings.
- Added a single-scene-instance contract and duplicate-building negative conditioning. A paired landmark such as twin towers is preserved exactly once, never as a second pair, mirrored clone or repeated landmark.
- Replaced the old unverified-route camera hold. A failed P2 analysis now keeps the takeoff and orbit, then uses a bounded collision-safe FPV fallback: ground skim, left climbing arc, brief inverted dive, right counter-roll, figure-eight crossover and level exit. It never claims an unreadable P2 endpoint.
- Changed P3 into the P1-derived near-ground takeoff anchor while retaining the exact five-second P1 scene-chain budget, P2 analysis-only isolation and ordinary/fireworks visual continuity contracts.
- Updated English/Chinese Skills and both automatic Design Requirement templates, plus executable-plan regressions for phase order, verified endpoint travel, fallback behavior and repeated normalization.

## [0.3.2-alpha.3] - 2026-09-03

### Design duration range disambiguation and mass-image guard — 2026-09-05

- Fixed a duration-parser collision where camera angles such as `0-360 degrees` were accepted as a 360-second Timeline range. The 12-second `drone-fly-on-city` template consequently scheduled 72 five-second references (P3-P74).
- Direct authored duration declarations now outrank later Skill examples and Timeline ranges. The ordinary Drone template resolves to 12 seconds and the Fireworks template to 15 seconds even though their documentation also mentions 35-second allocation examples.
- Time-range recognition now excludes degrees, pixels, percentages, FPS, frame counts and ordinary numeric dimensions while retaining bracketed timecodes, `HH:MM:SS`, `0-5s` and `0-5秒` speech/Shot ranges.
- Added a pre-generation Drone budget gate. Before any Z-Image request starts, the Plan must contain P1 as `h3_reference`, P2 as `analysis_only`, and exactly one uniquely timed P1-derived Picture per five-second interval. A malformed Plan remains editable but cannot launch mass generation.
- Added regression coverage for both Drone Skills, erroneous 360-second model output, P3-P5 allocation, non-time numeric ranges, missing P2 and a simulated 72-request Plan.

### Remote ComfyUI prompt-ID reconnect recovery — 2026-09-05

- Separated client transport loss from server generation failure. After ComfyUI accepts a prompt, native and Smart Render workers keep polling the same `prompt_id` for up to the configurable recovery window instead of posting duplicate work.
- Checkpointed accepted native prompts in the Job JSON and active Smart Render Segments in the project-scoped Manifest immediately after `/prompt` succeeds. A resumed worker reuses that persisted server Job when its server and Segment fingerprint still match.
- Added orange reconnecting Timeline status, live disconnect/reconnect progress messages and the `Connection recovery window` setting (`H3_CONNECTION_RECOVERY_TIMEOUT`, default 3600 seconds).
- Made output retrieval reconnect-safe with temporary `.part` files and atomic publication. A broken transfer retries the same ComfyUI output and cannot replace a valid MP4 with a partial file.
- Added regression tests for history polling across LAN failure, interrupted downloads, prompt checkpoint/restart recovery and the no-duplicate-queue guarantee.

### Route-controlled 360° drone scene chain — 2026-09-05

- Replaced the fixed seven-reference allocation with a five-second scene chain: P3 is the 0–5 second P1-derived opening anchor, P4 starts at 5 seconds, and later Pictures continue every five seconds without a P9 cap. A 35-second mission uses P3–P9; a 45-second mission reaches P11.
- Fixed the inverted orbit gate that disabled an explicit 360-degree request whenever P2 was loaded. A 360 mission now requires both an affirmative user request and a locally verified P2 start/direction/end; each Shot receives its proportional 0–360-degree phase plus the actual overlapping P2 path legs.
- Strengthened every generated Picture prompt to preserve P1's primary building, scene and composition, roads, sky, weather, colour palette, colour temperature, exposure, atmosphere and lens. P3 uses lower denoise than later scene states.
- Kept camera-motion language out of static Picture prompts and keywords, so the route-controlled orbit remains an H3 video instruction and cannot prime Z-Image to draw a glowing path or ring.
- Updated the ordinary and fireworks Skills, Chinese counterparts and Design Requirement templates, plus regression coverage for 35-second P3–P9 allocation, route-controlled orbit phases, P1 pixel binding and Segment Mapping.

### Withdraw automatic drone end-plate replacement — 2026-09-05

- At the user's request after visual review, removed automatic P1 terminal-image requests, the reserved last-second range, and the native-render/master-assembly calls that overwrote the ending with a still plate.
- Old `final_hold_*` render-job metadata no longer triggers output replacement. Legacy automatically marked immutable P1 tail assets are excluded from Timeline/render reference selection, while their Media Pool entries and files remain available.
- Both drone Skills and Design Requirement templates now direct a natural H3-generated ending, not a forced P1 return, local fireworks composite or one-second image freeze. The earlier immutable-tail entries below describe withdrawn behavior, not the current pipeline.
- Reference review used `generated_output_6.mp4` (12.256 s): low-to-high camera travel, shifting parallax and evolving fireworks are the visual target; automated test success is not a substitute for real-video acceptance.

### Drone pixel conditioning and route verification — 2026-09-05 correction

- Fixed a real data-flow gap: P3–P9 previously used only BLIP/AI text. They now upload the locally bound P1 image and connect `LoadImage → ImageScale → VAEEncode → KSampler` with low denoise. Missing P1 never silently falls back to text-to-image; scene backgrounds are not removed. Stage references retain source composition and are not claimed to reconstruct unseen camera views or preserve pixels exactly.
- Removed orbit/ring/trajectory vocabulary from positive still prompts (including Chinese), keeping exclusions in the dedicated negative field. P2 remains analysis-only and is never uploaded as a scene image. Existing contaminated images must be regenerated; artifacts already in P1 require a clean source.
- Added green-start/blue-end direction verification, bend-preserving path simplification and all-leg Shot motion clauses. Unreadable, ambiguous, branched or unmarked routes produce `ROUTE NEEDS REVIEW` and a camera hold, not an invented orbit. A loop needs a small gap and separate endpoint markers. Map Y no longer implies altitude.
- Updated both drone Skills and Design Requirement templates with the supported drawing convention and fidelity limits. The previous caption-only/new-view and automatic closed-loop claims below are superseded by this correction. Pixel-derived reference conditioning and prompt routing still require real render acceptance; unit tests are not video-quality certification.
- Added `test_drone_reference_pipeline.py` covering actual sampler source wiring, upload identity, background preservation, absent-source safety, route direction/bends, ambiguous-route handling and multilingual positive/negative isolation.

### P1/P2 drone route authority correction

- Replaced the example-biased drone plan with a deterministic P1/P2 contract: P1 remains the sole full-duration scene master, while P2 is locally analysed as non-visual red-path control data and never becomes an H3 or Z-Image Loader.
- Added local red-stroke skeleton extraction and ordered camera-stage language. Open, S-shaped and point-to-point paths retain visible translation and are no longer converted into a default 360-degree orbit; an orbit is allowed only for a closed P2 path or an explicit user request.
- Added seven time-scoped P1-derived route-stage references, normally P3-P9. Their prompts use only P1 BLIP/AI evidence and forbid example locations from replacing P1; Segment jobs retain P1 plus only the relevant stage reference.
- Removed the fixed Kuala Lumpur/Petronas example from the fireworks Design Requirement and generalized both English/Chinese Skills and Clean Frame contracts to any P1 scene.

### Drone still-reference orbit-ring isolation

- Split camera-motion planning from Z-Image still composition for `drone-fly-on-city`. Sentences and subject keywords describing a 360-degree orbit, orbital yaw, route or trajectory are removed from generated still-reference requests while the real H3 video Shot keeps its intended orbit movement.
- Added a mandatory clean-frame contract stating that the drone path is implied only through camera motion, plus a request-scoped Z-Image negative prompt covering visible flight paths, orbit rings, circular light trails, glowing ellipses, HUD graphics and neon loops.
- The active Z-Image ComfyUI template now receives request-specific negative conditioning instead of silently ignoring it. Right-click Z-Image regeneration applies the same protection to old drone reference Pictures without changing their stable `P` mapping.

### Drone city-fireworks Special Skill

- Added `drone-fly-on-city-fireworks`, a Default-bound night-city aerial celebration Skill that combines the proven P1 scene-master/P2 analysis-only route contract with one physically plausible 360-degree landmark orbit.
- Added a per-Shot fireworks continuity ledger covering launch and burst position, gold/white/deep-red particle phase, smoke drift, façade/wet-street reflections, exposure response and distance-delayed native firework sound.
- Added fireworks-aware Z-Image still isolation. Static references retain discrete chrysanthemum bursts and smoke while camera-orbit clauses are removed; an additional request-scoped negative contract rejects continuous firework rings, tower-wrapping effects, fused landmarks and solid neon fireworks.
- Added English/Chinese Skill instructions, an editable 15-second Petronas Twin Towers Design Requirement template, common Scene Keyframe Chain support and regression coverage for Design normalization, H3 motion retention and right-click Z-Image regeneration.
- Replaced the generative terminal-reference rule in both drone Skills with an immutable P1 Scene Plate contract. The ordinary Skill copies P1 without T2I reinterpretation; the fireworks Skill composites only discrete firework particles, thin smoke and physically plausible illumination over the unchanged P1 pixels.
- Both single-scene and multi-scene plans now reserve one terminal range, return the moving camera to P1's exact composition, and mark the final plate with explicit `source_plate_*` metadata. Local P1 paths are bound only after planning and are removed from the LM context.
- Preview, native renders and Smart Long Render masters now enforce the last one-second freeze during local FFmpeg output assembly while stream-copying the original audio. Partial ranges ending before the terminal plate are not modified.

### Live-action arcade fighter Special Skill

- Added `street-fighter-live-action-h3`, a Default-bound Special Skill for 15-45 second live-action arcade martial-arts film scenes. It distils the supplied 2026 trailer reference into reusable original production grammar rather than copying its edit: two readable fighters, grounded live-action materials, bold tournament staging and selectively heightened signature attacks.
- Added a deterministic seven-Shot, 12-Beat close-combat structure per 15 seconds: one eye-level establishing Wide capped at 1.0 second followed by six Close-up/Extreme close-up action Shots carrying two beats each. A 30-second design uses two continuous, non-repeating 12-Beat Segments and a stable two-fighter identity/style/ability ledger.
- Added move-specific execution rules for compact palm projectiles, rotating kicks, forward rolling attacks, close electric strikes and rapid hand strikes, with physically motivated light, Foley and post-contact environment response.
- Added English/Chinese Skill instructions, an editable 15-second Design Requirement template and regression coverage for profile loading, binding, action budgeting, Segment continuity, visible-text control and Virtual Media Pool mapping.
- Added fixed Karate, Judo, Jeet Kune Do and Wing Chun attack/defence reversals, contact-driven water splashes, sourced smoke, grounded cyberpunk practical lighting and an explicit ban on stage spotlights.
- Added an optional MMA ground-game branch inside the same 12-Beat budget: visible level change and single/double-leg capture, controlled takedown, locked top/bottom control, a maximum two-contact ground-and-pound burst, controlled submission, visible tap and immediate release. Ground-state continuity now records top/bottom identity, head direction, screen side, grip ownership and simple leg position across cuts.
- Extended the Skill to 45 seconds using three connected native Segments, 21 Shots and a 36-entry global Action Ledger. Duplicate technique/target/outcome combinations must be rewritten rather than disguised through a new camera angle or visual effect.
- Replaced generic gloves with locked open-finger MMA glove geometry: visible separate fingers for grappling, compact padded knuckles, rounded streamlined shell, secured wrist wrap and persistent wet grime along the lower cuff.
- Added a reference-derived fictional sealed industrial vertical-maze environment across a lower service corridor, flooded utility landing and upper maintenance catwalk. Per-Shot environment state now preserves gates, cable/pipe landmarks, wet patches, mould/rust, IES-profiled practical lights, alarms, steam sources and contact-displaced debris while allowing one causal environment change per Shot.

## [0.3.2-alpha.2] - 2026-09-03

### Dark rescue camera-mode repair

- Repaired the invalid mixed-case `dark-rescue-h3-no-POV` folder as the creator-valid `dark-rescue-h3-no-pov` profile and separated its behavior from the first-person Skill. The no-POV version now explicitly uses an external cinematic observer camera with a visible rescuer instead of accidentally inheriting rescuer-eye instructions.
- Strengthened `dark-rescue-h3` with positive in-frame POV evidence distilled from the five supplied production references: near-lens glove/forearm/tool/helmet anchors, eye-height geometry, body-motivated parallax, victim-to-eye-line interaction and reachable exterior/Final Hold viewpoints.
- Added deterministic Design normalization for `dark-rescue-h3`. Every Shot's framing, angle, movement, executable action, continuity and additional direction now carries the physical S2 eye-line contract; generated image references receive the same perspective proof and external-camera language is neutralized before H3 compilation.
- Updated both English/Chinese Skill files and their distinct Design Requirement templates, plus regression coverage proving the first-person and no-POV profiles cannot collapse into the same camera mode.

### Drone scene keyframe chain

- Added an ordered user-authored scene chain for `drone-fly-on-city`: P1 and later selected P3/P4/P5 Pictures now own disjoint Timeline ranges instead of being loaded together for the complete clip. A future Picture can no longer alter the earlier P1 scene.
- Added exactly one environment-only automatic terminal keyframe after the latest user scene. It has no forced Picture number, so the Virtual Media Pool assigns the next truly empty slot automatically: P4 after P1/P2/P3, or P6 after P1-P5.
- Each keyframe interval is compiled as an independent native H3 Job even inside a 12-second work area. Only the preceding final 24 silent video frames cross the boundary as motion context; future Pictures and previous audio never cross it.
- Replaced automatic terminal Pictures remain inactive history. If the user manually replaces one with a local image, stale generated-reference analysis is cleared and the new image becomes an authored scene anchor.
- Updated the English/Chinese Skill and `DESIGN_REQUIREMENT.txt` with the new keyframe ownership, terminal-frame and continuity contracts.

### Analysis-only route controls

- Added a real `analysis_only` Media Pool usage for planning maps, route drawings, masks and other control images. The compatibility alias `route_control_analysis_only` is accepted and normalized automatically.
- Analysis-only sources remain available to Design intelligence but are never placed on the Timeline, counted against per-Segment H3 capacity, uploaded to ComfyUI/MiniMax, treated as identity anchors or assigned an H3 Picture slot. Reapplying a Design also removes a control image that an older build mistakenly placed on a V track.
- Removed analysis-only `@P/@V/@A` labels from every H3-renderable Shot, cue and creative field, replacing them with the already extracted abstract control instruction so reference-token parsing cannot reactivate the source.
- Updated `drone-fly-on-city` in English, Chinese and its Design Requirement template. The former long negative-prompt catalogue repeated route-artifact vocabulary inside H3's single prompt and could visually prime the model; it is now replaced by a positive clean-frame/off-screen-control contract.
- Fixed a second prompt-priming path found during real-output acceptance: Special Skill frontmatter descriptions are discovery metadata and are no longer copied verbatim into the H3 render prompt. Control-only Skills also scrub legacy route-graphic vocabulary from loaded older Projects at final prompt compilation.
- Extended analysis-only isolation to generated-reference prompts and subject keywords, preventing a Z-Image continuation reference from inheriting control-image labels or visual annotation vocabulary.
- Reject incorrect `identity_anchor=true` metadata on environment-only image requests. Pure skyline, room, prop and landscape references now receive an environment-only subject-count guard instead of generating an unrelated prominent person.
- Added Design normalization and end-to-end workflow regressions proving a loaded P2 route-control picture remains in the Media Pool while its filename, loader and pixels are absent from the compiled H3 job.

### Design JSON completion reliability

- Removed the hidden 12,000-token completion bottleneck that could truncate a valid 45-second Special Skill plan even when LM Studio had a 100k context window. Director Design now allows up to 32,768 output tokens for its schema response.
- Added provider-neutral `finish_reason`, output-size and usage diagnostics so a completion stopped by `length` is distinguishable from a Design Requirement text-box problem.
- Added one automatic compact full-plan recovery pass when Qwen returns malformed or truncated JSON. The first failure no longer immediately blocks Apply; a second failure reports its exact line, column, finish reason and output size.
- Added a compact-output contract to every Design planning and BLIP-refinement prompt: required Shots, editable speech, continuity and media ranges are preserved while repeated prose and formatting overhead are removed.
- Refinement JSON failure is non-destructive: the already validated first Design Plan is retained instead of being replaced by incomplete BLIP-refinement output.

### Special Skill Design Requirement templates

- Added optional per-Skill `DESIGN_REQUIREMENT.txt` starter templates. Selecting a Special Skill and opening `DESIGN` now fills an empty Design Requirement with that Skill's editable production example.
- Existing authored Design Requirement text always has priority and is never overwritten. Skills without a template remain compatible and continue to open with an empty requirement.
- Added a `DESIGN REQUIREMENT TEMPLATE` editor to `SPECIAL SKILL CREATOR`; templates are loaded and saved independently from `SKILL.md` and the optional `SKILL.cn.md`.
- Added tailored templates for all 12 bundled Special Skills: 3D animation, brand promo, co-op game intro, dark rescue, hand-drawn/live-action fusion, long-form production, minimalist product advertising, music video, paper collage, papercraft stop-motion, short drama and wuxia blade film.
- Added the new `dark-rescue-h3` Default-bound Special Skill, distilled from five user-tested first-person rescue structures and their proven environmental-lighting vocabulary. Its starter request demonstrates a fictional Wall Street-inspired damaged office tower without inventing unloaded Media Pool IDs.
- Added a 45-second Tang-dynasty courtyard starter requirement to `wuxia-blade-film`, including executable action budgets, character/weapon/prop ledgers, native 15-second boundary contracts and non-magical physical combat constraints.
- Increased the Studio Special Skill Creator description limit from 600 to 1,200 characters so every bundled Skill can be edited and saved without rejecting its existing metadata.

### Verification and compatibility

- Added regressions proving every bundled Special Skill has a non-empty editable template, all templates load through the Studio profile system, and `dark-rescue-h3` opens Design with the expected starter requirement under `Default + Special` binding.
- All 38 focused Skill store, profile, creator compatibility and Design UI tests pass.
- Project format remains `21`; Workspace layout, Timeline mapping, Segment compilation, render policy, saved Projects and generated media are unchanged.

## [0.3.2-alpha.1] - 2026-09-01

### MiniMax H3 native production sound

- Added a three-state `MUSIC AUTO / OFF / TIMELINE` selector beside Design Requirement, defaulting to AUTO. AUTO sends Qwen's scene-aware score direction into every actual H3 segment prompt, OFF deterministically compiles `non_diegetic_music: N/A`, and TIMELINE enables music only for active Timeline Music Cues. The project-scoped policy persists through save/load and safely defaults old projects to AUTO.
- Added per-Shot prompt-only `Native Audio Direction`, `Environment Continuity`, `Audio Reference Intent`, and `Native Audio QC status` fields. Auto-derived values survive Timeline/segment compilation, while user edits are protected from automatic refresh.
- H3 Ref2VA prompts now time-align acoustic space, speaker-to-camera distance, screen position, natural speaking state, continuous ambience, picture-synchronous Foley and explicit diegetic-source rules with exact Dialogue Text Layers.
- Prohibited narration/announcer tone, recording-booth close-mic sound, dry studio voice and extra dialogue. Background music now follows the explicit project policy: AUTO, OFF or TIMELINE-only.
- Long renders preserve written acoustic continuity across same-space cuts, describe perspective changes for wide/close cuts, and declare interior/exterior acoustic transitions. The preceding 24-frame continuity clip is explicitly visual-only and never attaches paired audio.
- Real-world Audio/Video assets marked as acoustic references guide space, room tone, distance and location texture only; their words and voice identity cannot replace Timeline Dialogue/Speaker assignments.
- Reused the existing VAD/Whisper service for read-only Native Audio QC of expected dialogue, unauthorized speech and missing ambience. No repair, remix, filtering, TTS substitution or generated-audio rewrite was added.

### Compatibility and verification

- Project format is `21`; format 20 projects load with safe defaults for every new field. Smart Render policy is `16`, so cached segments built before the native-audio prompt contract are regenerated instead of silently reused.
- Added native-audio unit, workflow-prompt, user-override, visual-only continuity and no-external-effects regressions. Mapping, long-segment scheduling and MP4 assembly behavior remain unchanged.

## [0.3.2] - 2026-09-01

### Qwen3-TTS Local

- Added Qwen3-TTS Local as a fourth editable Dialogue Text Layer engine beside Ori, VoxCPM2 and Edge TTS. Design exposes a `Qwen` button and Settings exposes runtime/model health.
- Integrated the official `qwen-tts 0.1.1` API with the resource-efficient `Qwen3-TTS-12Hz-0.6B-CustomVoice` model, deterministic Studio Speaker mapping, exact authored words and Timeline WAV rebuilding.
- Isolated Qwen's pinned `transformers 4.57.3` / `accelerate 1.12.0` stack under `ai_libraries_common/qwen_tts_runtime` so the existing BLIP/Vox environment is not downgraded.
- Added CUDA-first loading, same-line CPU retry after CUDA load/inference failure, and immediate VRAM/RAM release before FFmpeg Timeline composition.
- Fixed the shared authored-TTS compositor so Edge, VoxCPM2 and Qwen WAV stems are padded to the exact Timeline duration instead of ending a fraction of a second early after the final line.
- Added verified Windows SoX support, runtime/model readiness warnings, one-command runtime/model setup helpers and a cross-computer transfer procedure. Large model weights remain outside GitHub under `models/`.

### Long Production Reliability

- Promoted the 120-second Long Timeline pipeline to a formal reliability baseline: approved prefixes remain reusable, Segment-local rerenders replace only the affected Take, and Preview/Final masters assemble selectively.
- Moved Smart Render jobs and worker manifests into each fixed Workspace under `project/render_jobs/`, using unique run tokens so two Projects or Studio instances cannot overwrite one another.
- Added a source fingerprint to every ComfyUI media upload name. Two concurrent Projects may now use different files with the same logical ID and basename (for example `P1/shared.png`) without colliding in the server's shared input directory.
- Added a bounded three-attempt Segment policy. CUDA out-of-memory, timeout, transport, media and unknown failures are classified; ComfyUI memory is released between retries, and the final failure class/retry budget is persisted without silently reducing quality.
- Project Load now evaluates every canonical and worker checkpoint and prefers the checkpoint containing the most durable completed Segment Takes. A newer failed/empty manifest can no longer hide an older recoverable run.
- Successful durable publication removes the large job file; interrupted or failed jobs remain available for diagnosis and resume.
- Storyboard and Smart Cut structural edits now detach the obsolete assembled Master while retaining reusable Segment checkpoints. Changed Shots dirty both their previous and remapped ranges; unchanged prefix Segments remain eligible for fingerprint reuse.
- Removed a UI-signal side effect that conservatively marked the entire Timeline dirty whenever the structural editor restored its Undo/Redo snapshot.

### Storage Optimization & Acceptance

- Added the `STORAGE` workspace with logical/physical byte reporting, Hard Link savings, category totals, SHA-256 duplicate groups and a conservative reclaim estimate.
- Added `SAFE CLEANUP` with dry-run output and confirmation. Masters, Media Pool sources, Project data, Segment Preview/Approved Takes and cache referenced by an interrupted job or standalone worker manifest are protected.
- Added verified `.h3project.zip` archives. Disposable cache/proxy/logs are excluded by default; external workflow/media are consolidated while preserving media basenames; `archive_manifest.json` records SHA-256 for every archived file.
- Archive is blocked while active/interrupted recovery data still lives only in excluded cache, preventing an apparently valid but non-resumable backup.

### Verification

- Added Standard Pipeline Release Gate 11 for interrupted cache protection, Archive blocking, durable publication and OOM classification. All eleven gates pass independently.
- Added a deterministic 120-second H.264/AAC acceptance fixture: an approved 45-second prefix is extended by five 15-second Segments, the complete Master is assembled, one middle Segment is replaced, and every outer Take hash remains unchanged.
- Added a 90-minute metadata-only stress fixture covering 900 Shots, Segment planning, fingerprints, Take state normalization, JSON save/reload and a 64 MB peak-memory ceiling without invoking H3 or the network.
- Added three focused simulations covering Storyboard reorder mapping, Smart Cut ripple/local reuse, and two separate Projects creating same-seed jobs/manifests without path or recovery contamination.
- All `401` bundled tests pass after adding Qwen runtime, CUDA fallback, exact WAV composition, Settings and Design UI regressions. A separate 31-test global Segment Mapping suite also passes.

### Compatibility and scope

- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`; existing saved Projects remain forward-compatible.
- One Studio instance still executes one ComfyUI job at a time. Centralized concurrent multi-Project scheduling and a full Scene/Sequence editing UI are explicitly deferred; project-scoped recovery and separate Studio instances are safe.

## [0.3.1-alpha.4.8.0] - 2026-09-01

### Fixed

- Fixed Qt playback failing with `moov atom not found` after Studio was closed while a high-resolution Monitor Proxy was still being encoded.
- Cached Monitor Proxies are now validated with FFprobe for a video stream, positive duration and duration agreement with the source master before Qt is allowed to open them. A non-empty filename alone is no longer considered a valid cache hit.
- Monitor Proxy encoding now writes to a process-specific `.building.mp4` and publishes the final cache path only with an atomic replace after successful validation. Closing Studio removes the active temporary proxy without touching the generated master.
- Existing interrupted／truncated proxies are automatically discarded and rebuilt from the intact `generated_output.mp4` or `generated_preview.mp4`.

### Compatibility

- Generated masters, Segment Takes, Project JSON, Reference Mapping and Timeline timing are unchanged. Only disposable `.director_cache/monitor_proxies` files are repaired.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Confirmed the original `the_black_panther_in_the_sun_3A/generated_output.mp4` is a valid 30.00-second H.264/AAC 2752×1536 master.
- Reproduced the failure in its 1.31 MB proxy, which FFprobe reported as missing the `moov` atom, then rebuilt and validated a 30.016-second H.264/AAC 1280×714 proxy.
- Added regressions for interrupted proxy rejection and atomic publication.
- All `380` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.9] - 2026-09-01

### Fixed

- Fixed completed Preview／Final masters reopening as `No generated output` when the Project JSON's `generated_output`, `smart_render` and `smart_render_manifests` fields were empty or stale even though durable Workspace files still existed.
- Project Load now treats `generated_output.mp4`, `generated_preview.mp4`, `project/render_manifest.json`, root `render_manifest.json` and durable Segment Takes as authoritative recovery sources without requiring a non-empty saved output path first.
- Copied／renamed Workspaces automatically rebase a recovered manifest's master and Segment output paths away from the previous computer or source folder.
- Recovered output immediately restores Program Monitor playback, Export, request kind and render status. The Project is marked modified so one Save persists the canonical paths.

### Compatibility

- No MP4 is duplicated, moved or regenerated. Recovery reads the existing master and Take files in place.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Confirmed `the_black_panther_in_the_sun_3A` contains a valid 30.00-second 2752×1536 `generated_output.mp4` despite empty output fields. It now reopens as the active generated output, enables Export, restores the Production manifest and prepares its Monitor Proxy.
- Added a current-format Project regression with deliberately empty output/manifest fields and a stale `D:\\...` manifest path; the Workspace master is recovered without regeneration.
- All `378` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.8] - 2026-08-31

### Fixed

- Picture cards now display a valid local image immediately and no longer depend on the asynchronous Media Preparation worker to obtain their first thumbnail.
- The direct-image fallback runs for old-Project path rebasing, Design-generated references, manual replacement, Z-Image regeneration and automatic transparent-background derivatives.
- The original source Picture is registered in the in-memory preview cache immediately. Media Preparation may later replace it with an optimized or transparent derivative without flashing `DROP MEDIA` or changing the logical P mapping.

### Compatibility

- This is a UI-preview correction only. It does not modify Picture files, Reference Mapping, Timeline placement, Segment fingerprints or generated video.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Reopened `the_black_panther_in_the_sun_3` with its old `D:\\...` paths on the current `C:\\...` Workspace. P1 was visible immediately while Media Preparation jobs were still active.
- Added a regression proving a newly resolved local P1 is placed into both the MediaCard pixmap and preview cache before any background preparation response.
- All `377` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.7] - 2026-08-31

### Added

- Generation Work Area End is no longer capped by the current Timeline endpoint. A default 12-second project can be extended directly by typing or clicking 45s, 120s or another larger End value.
- Increasing End beyond the current endpoint expands the Timeline, mapped workflow duration node, transport range and saved Project duration together. Reducing End only selects a shorter render range and never trims existing Timeline content.
- Manual Timeline extension supports up to six hours for future long-form structures. End is automatically kept at least one 0.5-second grid step after Start.
- Added a complete tooltip explaining the editable End behavior and a status message when the Timeline is extended.

### Compatibility

- New Project default remains `12.0s`. Existing Project Work Area values and Timeline durations remain unchanged when loaded.
- Project format remains `20`, Workspace layout remains `2`, and Smart Render policy remains `15`.

### Verification

- Added a UI regression covering `12s → 120s` Timeline expansion, non-destructive `120s → 45s` Work Area reduction, workflow duration-node synchronization and invalid End-before-Start correction.
- All `376` bundled tests passed; the focused post-validation for the final input guard also passed.

## [0.3.1-alpha.4.7.6] - 2026-08-31

### Fixed

- Fixed native H3 speech-tail protection moving a safe Segment boundary forward across the next authored line. A line starting at 8.50, 22.00 or 41.00 seconds can no longer be compiled into the preceding Segment and then disappear from its own Segment.
- Added dialogue-turn-aware Segment planning. Nearby safe boundaries align to on-camera speaker changes, so alternating S1/S2 lines are not compressed into one H3 generation window when a clean split is available.
- Added an explicit speaker-to-face identity contract to every native H3 Segment prompt: S1 is the female character and S2 is the male character; each is bound to the actual dynamically mapped Picture reference. Only the scheduled speaker may move lips or jaw, while listeners keep a closed, still mouth and voice-over never drives visible lip sync.
- Added a Run／Preview speech preflight against the live Timeline. Unsafe Dialogue／Voice-over／Lyrics durations, CJK layers mislabeled as English, downstream timing and the final 1.5-second breath／room-tone tail are repaired even when the Project was already open before this version.
- Fixed endpoint repair leaving Work Area and ending media at the old duration. Projects whose Work Area previously reached the endpoint now expand through the repaired final speech and decay tail.

### Compatibility

- Smart Render policy is now `15`; policy 14 Segment caches with shifted speech ownership or ambiguous speaker-face animation are intentionally invalidated.
- Project format remains `20` and Workspace layout remains `2`. Existing Projects are repaired in memory and remain loadable; Save Project persists the corrected Timeline.

### Verification

- Offline transcription of `那个替他说“不”的_AI_4/generated_preview.mp4` confirmed the 8.50-second narration had been pulled into the first Segment, the 41.00-second narration began around 38 seconds, later dialogue was compressed early, and the final phrase remained active through 69.99 seconds before the 70.00-second hard cut.
- The repaired Project is 72.00 seconds with render windows `0–8.5 / 8.5–22 / 22–25.5 / 25.5–28 / 28–32.5 / 32.5–41 / 41–50.5 / 50.5–54.5 / 54.5–60.5 / 60.5–72s`; every authored speech layer belongs to exactly one Segment and the last line has a 1.5-second tail.
- All `375` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.5] - 2026-08-31

### Fixed

- Fixed `Project load error: TextLayer.__init__() got an unexpected keyword argument 'speech_timing_auto_adjusted'` after the final-speech timing repair.
- `speech_timing_auto_adjusted` is now a first-class persisted Text Layer field.
- Project, Undo/Redo and Storyboard Text Layer restoration now accept known fields while safely ignoring additive metadata from newer Project versions, preventing future repair markers from blocking Load Project.
- Added a short retry for atomic provisional-workspace renames when Windows, OneDrive or a thumbnail scanner briefly retains a directory handle.

### Verification

- Added a real old-Project load regression that creates an undersized final Mandarin voice-over, runs automatic endpoint repair, then restores the resulting Text Layer into the Timeline.
- All `372` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.4] - 2026-08-31

### Fixed

- Fixed a confirmed hard cut at the 70.00-second Project endpoint while the final authored Mandarin voice-over was still active.
- Existing Projects now receive conservative speech-budget repair at 3.6 CJK characters per second. Unsafe Dialogue／Voice-over／Lyrics extends on the 0.5-second grid and ripples its owning Shot, later Shots, Text Layers, authored requirements, media clips and Work Area.
- The Project endpoint now reserves a 1.5-second final breath, room-tone and reverb tail after the last authored utterance.
- Fixed stale Prompt timing after an automatic Project repair; editable Prompt fields are rebuilt from the repaired Timeline during Load Project.
- Native H3 Segment prompts now include an exact speech-window whitelist and explicitly forbid filler syllables, false starts, repeated or translated words, commentary, whisper, crowd speech and phone voices in every vocal-silence gap.
- Removed orphan quoted words and all untracked visible-text directions from compiled Shot and global prompts. Exact visible text must be owned by an editable `on_screen_text` Timeline layer.

### Compatibility

- Smart Render policy is now `14`; policy 12/13 Segment caches containing cut dialogue, polluted speech or burned typography are intentionally invalidated.
- Project format remains `20` and Workspace layout remains `2`. Opening the affected 70-second Project repairs it in memory; Save Project persists the new timing.

### Verification

- Offline transcription of the supplied output confirmed non-authored speech at 25.23–26.91, 27.30–29.01, 32.00–32.63 and 55.08–55.83 seconds, plus active final speech through the exact 70.00-second endpoint.
- Verified `那个替他说“不”的_AI_2` repairs from 70.0 to 77.5 seconds; its final voice-over moves to 66.5–76.0 seconds and receives a 1.5-second tail.
- All `371` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.3] - 2026-08-31

### Fixed

- Fixed abrupt native dialogue／voice-over starts and cut-offs at independently generated H3 Segment boundaries.
- Authored Dialogue／Voice-over／Lyrics now protect every internal render cut through the complete utterance plus a 1.0-second breath, room-reverb and ambience decay tail when Timeline capacity permits.
- A fully packed 15-second sequence now inserts an additional safe Segment when moving one boundary would exceed H3's native limit; it no longer cuts the authored line merely to preserve the old Segment count.
- Every native Segment prompt now forbids unlisted speech, requires continuous location ambience, completes authored words by the Text Layer end, and forbids a new word, music cue or Foley transient in the final second.
- Preview／Final assembly applies a 40ms audio de-click fade at internal joins without changing video timing, Segment duration or Reference Mapping.

### Compatibility

- Smart Render policy is now `13`; old Preview／Final Segment caches are intentionally invalidated so already-encoded hard audio cuts cannot be reused.
- Project format remains `20` and Workspace layout remains `2`; existing Projects load without migration.

### Verification

- Extended Standard Pipeline Release Gate 4 with the speech-boundary case, including a fully packed 45-second Timeline that must add a fourth safe Segment.
- Verified `那个替他说“不”的_AI_2` now plans `0-8.5`, `8.5-20.5`, `20.5-32.5`, `32.5-41`, `41-53`, `53-61`, and `61-70` seconds. The 58-60 second line belongs only to the `53-61` Segment.
- All `371` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.2] - 2026-08-31

### Added

- Added `REGENERATE WITH Z-IMAGE` to the right-click menu of eligible Media Pool Picture cards.
- Regeneration reuses the Picture's original Design request metadata, including subject keywords, exact cast/count contract, identity-anchor relationship, environment, composition, time range and preferred stable P identifier.
- Successful output replaces the same logical Picture source without changing its Loader node, P mapping, repeated Timeline occurrences or Clip Prompt. Only intersecting render Segments are marked dirty.
- Every regenerated take is non-destructive and stored below `media/regenerated_references/P#/`; BLIP and optional semantic analysis are then refreshed against the new image.
- Added a per-card translucent Z-Image progress overlay and worker timeout/close protection.

### Verification

- Verified project `那个替他说“不”的_AI_2` P5 resolves as node 153, remains P5, retains 20.00–32.50s scope, `req_man_identity`, and the exact-two-person contract.
- Added regressions for Picture-only context-menu activation and in-place regeneration without Reference Mapping changes.
- All `368` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7.1] - 2026-08-31

### Fixed

- Fixed cross-computer Queue failure when canonical Project JSON lives in `Workspace/project` while generated image, video or audio sources live in sibling `Workspace/media` trees.
- Runtime media recovery now searches both the JSON directory and the complete canonical workspace, then accepts only a unique basename match.
- Clean Project export now rewrites unavailable absolute paths to verified local workspace files instead of preserving another computer's drive path.

### Verification

- Strengthened Standard Pipeline Release Gate 1 with the canonical `project/` plus sibling-media layout.
- Added regressions for runtime sibling-tree recovery and Clean Project path rebasing.
- Rebuilt `那个替他说“不”的_AI/project/director_project.clean.h3director.json`; all nine image Loader paths exist locally.
- Real 7-Segment Queue preflight passes with no missing media and no unresolved Loader.
- All `366` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.7] - 2026-08-31

### Fixed

- Closed a Reference Mapping leak where a generated environment still could be promoted as a whole-project character anchor and earlier airport/hotel/computer references could remain active in later story phases.
- Added exact cast/count contracts for identity, secondary-character, two-person and environment reference images. Existing malformed project references are repaired on load without overwriting the source JSON.
- Fixed dialogue timing expansion that increased Timeline duration without extending the owning final Shot, producing a render Segment with `shot_ids=[]` and allowing an earlier scene to reappear.
- Preserved normalized `text_layers.shot_id` during Apply instead of ambiguously recomputing ownership on an inclusive Shot boundary.
- Segment manifests now report only media Loader files actually connected in that Segment workflow, while uploads remain deduplicated job-wide.
- Clean projects with invalidated render state no longer auto-load a stale root `generated_output.mp4` into Program Monitor.

### Changed

- Removed project-total media-request capacity checks. Virtual Media Pool IDs may continue beyond P9/V3/A3; physical 9/3/3 limits are enforced only for simultaneously active references per Segment.
- Design/Qwen rules now require exact cast ledgers, one-location Shot Blocks, time-scoped environment references and complete Shot coverage after speech ripple.
- Strong multi-location `Cut to` montage prose is split into executable single-location Shots during project integrity repair.
- Added `project_integrity.py` for data-only portable Project repair and clean JSON export.
- Smart Render policy is now `12`, so older Segment caches compiled before the mapping/coverage correction are not silently reused.

### Verification

- Added Standard Pipeline Release Gate 9 for Reference Mapping isolation, P10+ virtual media and Segment-local manifest reporting.
- Added Standard Pipeline Release Gate 10 for dialogue-duration ripple, Text-to-Shot ownership and zero Shot-less render Segments.
- Project format remains `20`; Workspace layout remains `2`.
- All `364` bundled tests and all ten Standard Pipeline Release Gates pass.

## [0.3.1-alpha.4.6] - 2026-08-31

### Changed

- Replaced the seven AI Design Apply popup entry families with one inline `APPLY PREFLIGHT REPORT`, grouping all findings into Auto-fix, Warning and Hard Block sections.
- Made Apply transactional: the Design page stays open and duplicate submission stays disabled until Timeline/Workspace commit succeeds. Runtime failure returns the same JSON and page to a retryable state; only `_commit_ai_design` closes it.
- Routed generation-state, missing model/input, unknown explicit media, invalid generated JSON, Load JSON and downstream Workspace errors into the inline report instead of modal warning chains.

### Auto-repair and degradation

- Explicit duration mismatch now retimes the complete Shot/Text/Media/Cue plan onto the requested duration's 0.5-second grid during Apply preflight.
- Missing Creative Brief and Visual Style receive deterministic safe defaults; duplicate media `requirement_id` values receive stable suffixes.
- Unsafe Z-Image requests containing H3 Picture tokens, dependent-frame wording or neutral/studio action backgrounds are rebuilt as standalone in-world frozen frames.
- Camera overlap that cannot preserve two 0.5-second cells now merges both actions and continuity states into one executable Shot instead of blocking the whole Design.
- Disabled non-explicit model-selected Media Pool references are removed. Explicit missing `@P/@V/@A` references remain Hard Blocks.
- Missing VoxCPM2 models or fully occupied Audio slots now preserve exact editable speech Text Layers, defer WAV creation and mark Timeline TTS pending instead of aborting the visual Design.

### Compatibility

- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`. Existing projects and Design JSON remain loadable without migration.

### Verification

- Added [`APPLY_ARCHITECTURE_ACCEPTANCE_CHECKLIST.md`](APPLY_ARCHITECTURE_ACCEPTANCE_CHECKLIST.md) with the complete 17-family policy and lifecycle contract.
- Added Standard Pipeline Release Gate 8 for safe repair, no modal Apply chain, retry-after-failure and close-after-commit behavior.
- All `362` bundled tests pass.
- All eight Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.5] - 2026-08-31

### Fixed

- Replaced the blocking `Shot Sx overlaps Sy` failure for repairable AI Design output with deterministic camera-cut boundary repair on the 0.5-second Timeline grid.
- Adjacent overlapping Shots now share the nearest feasible midpoint boundary while retaining at least 0.50 seconds for each Shot. The warning records both original ranges and the repaired cut.
- Kept Media Pool clips and Dialogue／Voice-over／Lyrics／On-screen Text ranges untouched because those layers may legitimately overlap on separate V/A tracks.
- Retained a hard validation error only when the combined interval cannot preserve one 0.5-second Timeline cell for both camera Shots.

### Compatibility

- No project schema, Workspace layout or render-policy fields changed. Existing Design JSON and saved projects remain loadable; normalization repairs eligible overlap during Load／Apply.

### Verification

- Added regressions for automatic shared-boundary repair and irreparable sub-second overlap protection.
- All `356` bundled tests pass.
- All seven Standard Pipeline Release Gates pass in the complete suite.

## [0.3.1-alpha.4.4] - 2026-08-31

### Changed

- Rebuilt Generation Work Area in the exact requested order: start, end, Aspect, Mode, Batch seconds, Next, approved seconds, Export API, server address, Test, Run+Queue, Storyboard, story duration, Auto Cut, Preview, Accept, Reject and Estimate.
- Removed the custom `MORE ▾` control and all hover-to-expand behavior. When row one reaches the available width, every remaining control stays visible automatically on a persistent second row.
- Added compact Work Area formatting (`0s`, `15s`, `0.5s`) without losing sub-second values, and shortened the visible controls to `TEST`, `PREVIEW 0.2M` and `ACCEPT 1.0M`.
- Kept Batch seconds, Next and approval progress visible in both modes for a stable layout; they remain disabled in FULL and become active in BATCH.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Replaced the hover-overflow regression with an ordered persistent-wrap regression that checks both rows, compact second formatting and the absence of native Qt `»` overflow buttons.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.3] - 2026-08-31

### Fixed

- Fixed the real Generation toolbar failure shown at wide desktop resolution: Qt's native `»` extension no longer captures `AUTO CUT` or the custom `MORE ▾` control.
- Moved `AUTO CUT` and `MORE ▾` ahead of optional server/render groups, added DPI/layout safety reserve, and allowed Batch controls to move as one complete overflow group only at constrained widths.
- Preserved FULL/BATCH widget visibility through QWidgetAction transfers. FULL no longer re-shows Batch seconds, NEXT and progress after a responsive reflow.
- Clicking the custom `MORE ▾` now explicitly opens the complete second row; hovering continues to open it automatically.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Extended the toolbar regression to reject a visible native Qt extension button, keep `AUTO CUT` visible, retain the populated primary row, and verify both hover and click open the custom overflow row.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.2] - 2026-08-31

### Fixed

- Restored the missing Auto Cut entry point at constrained window widths. The compact `AUTO CUT` control is now pinned to the primary Generation Work Area row instead of being moved into the hidden overflow toolbar.
- Renamed the visible Smart Cut trigger and its Safe, Balanced and Aggressive menu entries to `AUTO CUT`, while preserving the existing protected Smart Cut planner and Manual Ripple Cut workflow.
- Kept the entry label stable as `AUTO CUT` even when the Timeline already matches the target, and corrected the responsive `MORE ▾` action/widget visibility synchronization.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Extended the responsive-toolbar regression to require `AUTO CUT` on the primary row at the minimum supported window width and to ensure it is never placed in the hidden overflow row.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4.1] - 2026-08-31

### Added

- Added a responsive two-row Generation Work Area. Complete control groups move to a hidden second toolbar row when the available window width cannot display them safely; Work Area, Aspect and Production Mode remain on the primary row.
- Hovering the Generation toolbar or its `MORE ▾` affordance now expands the second row immediately. Moving outside both rows starts a short delayed collapse so the row does not disappear while the pointer crosses between toolbars.
- Added immediate rich Hover Help to every compact Generation control, including complete name, purpose and expected effect for Work Area, Aspect, Full/Batch production, Export, ComfyUI connection, Run, Storyboard, Smart Cut, Preview/Accept/Reject and Estimate.

### Compatibility

- No project schema or render-policy fields changed. Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Added a UI regression that forces the minimum supported window width, verifies complete control groups move to the secondary toolbar, triggers its Hover Enter event and checks rich help metadata on compact controls.
- All `355` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.4] - 2026-08-31

### Added

- Added compact `MODE: FULL / BATCH` production controls, a configurable 30-second default Batch size, `NEXT` and live approved/total status to the Generation Work Area.
- Incremental production previews only the next unapproved range. Accept switches to a cumulative 0-to-horizon render, reuses approved Smart Render Segments and publishes one continuous Preview/Final master in Program Monitor.
- Added speech-safe approval horizons. A proposed Batch boundary moves past intersecting Dialogue, Voice-over or Lyrics and prefers a nearby Shot boundary instead of cutting exact authored speech.
- Persisted the approved horizon, pending range, Batch phase, Preview seed and Preview-ready state in Project and Design Undo/Redo state. Smart Render checkpoints therefore resume an interrupted Batch without returning to all-at-once production.
- Added the Default-bound `long-form-h3-director` English/Chinese Special Skill. It preserves the full story, plans Sequence/Shot responsibilities, Incoming/Outgoing State, 24-frame motion context, exact text layers, Segment-local references and exactly one real project-ending Final Hold.
- Selecting `long-form-h3-director` automatically selects Incremental production; selecting None or another Special returns to Full Range while retaining manual strategy controls.

### Compatibility

- Existing projects without the optional Incremental fields open in `FULL RANGE` with no behavioral change.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

### Verification

- Added nine regressions for bilingual Skill discovery/binding, automatic strategy switching, speech-safe Batch boundaries, next-range-only Preview, cumulative Accept, durable approval advancement, project payload state and Open Project resume.
- All `354` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.

## [0.3.1-alpha.3] - 2026-08-30

### Added

- Added the three-stage Smart Cut workflow. Phase 1 uses a deterministic dynamic-programming planner on the Studio's 0.5-second grid with Safe, Balanced and Aggressive modes, explicit speech/action minimums, protected narrative roles and impossible-target warnings.
- Added a non-destructive Smart Cut review window with Original/Edited/Target totals, per-Shot KEEP/TRIM/MERGE/REMOVE decisions, importance/risk/reason columns, manual Shot locks and duration overrides. Cancel never mutates the Timeline; Apply is one Undo/Redo transaction.
- Added Phase 2 dependency analysis for adjacent continuity state, shared P/V/A references, visible track relationships and native 15-second boundary risk. Accepted plans remap Shot-owned cues, text, media Source In/Out and local render-dirty ranges, then save `smart_cut_plan.json` in the fixed project Workspace.
- Added Phase 3 semantic refinement through the currently configured Design provider. Online GPT or LM Studio may classify story role, bounded importance, protection and redundancy only; its JSON schema contains no timing/edit authority and all durations are recalculated locally.
- Preserved the original manual purple-Shot Ripple Cut in the `SMART CUT` arrow menu alongside direct Safe/Balanced/Aggressive planning and the Storyboard Editor shortcut.

### Fixed

- Smart Cut LM cleanup now unloads the model instance actually resolved by LM Studio when a saved/deleted model identifier was automatically replaced, preventing a stale `model_not_found` unload request.
- Authored Dialogue, Voice-over and Lyrics cannot be removed or merged by either automatic planning or reviewed Apply. An unsafe target remains visibly over target instead of cutting words.

### Verification

- Added seven pure Smart Cut engine regressions and four Timeline/UI integration regressions covering exact grid targets, protected speech, deterministic critical-role floors, dependency graphs, merge audit, bounded LM hints, Cancel safety, Apply/Undo/local dirty state, legacy Manual Ripple Cut and resolved-model unload behavior.
- All `345` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.7] - 2026-08-30

### Changed

- Storyboard cards now lift three pixels with a raised border and shadow while the pointer hovers over them.
- Starting a drag now displays a 94%-opaque lifted card ghost with a layered soft shadow under the pointer while the real grid position remains a visible `DROP HERE` target.
- Neighboring cards now slide for 190ms as the target position changes. Releasing a card adds a 260ms lift-and-settle pulse with a fading cyan landing outline; arrow-button moves use the same landing feedback.

### Verification

- Expanded Storyboard interaction regressions to verify hover tracking, the dedicated card delegate, enlarged shadow ghost, reflow timing and drop-settle timing/state.
- All `334` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.6] - 2026-08-30

### Added

- Added selected-Shot left and right arrow buttons to the Storyboard Inspector. Each click moves the selected card exactly one position, animates the neighboring-card reflow and disables the unavailable direction at the first or last position.
- Added an Explorer-style `VIEW` menu with Extra large icons, Large icons, Medium icons, Small icons, List, Details, Tiles and Content layouts. Each mode changes both card geometry and information density without modifying Timeline data.

### Changed

- Large icons remains the default three-column Storyboard layout. The chosen view is remembered in Undo/Redo workspace state and in saved `.h3director.json` projects; New Project restores the default.

### Verification

- Added regression coverage for all eight display modes, left/right reordering, boundary button states and view preference persistence.
- All `334` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.5] - 2026-08-30

### Fixed

- Fixed Storyboard cards repeatedly selecting a global full-Timeline identity Picture such as P1. Thumbnail selection now prioritizes explicit Shot semantic direction, then a Picture whose start/end exactly matches that Shot, and only falls back to the global P1 identity anchor when no dedicated Shot frame exists.
- Verified the reported `Sam_Altman_The_Human_in_the_Machine` mapping: S2→P5, S3→P6, S4→P3, S5→P7, S6→P8, S7→P4 and S8→P9; S1/S9 correctly fall back to P1 because they have no dedicated Shot Picture.

### Changed

- Storyboard Drag & Drop now lifts a real card ghost under the pointer and leaves a visible `DROP HERE` placeholder in the board.
- Crossing another card moves the placeholder immediately, reflows neighboring cards into the vacated grid position and runs a 150ms OutCubic slide animation. Releasing commits the draft order; cancelling restores the original row.
- Every Storyboard card now displays `FRAME P#` so the exact thumbnail source is inspectable instead of being inferred from the broader `MEDIA` list.

### Verification

- Added a regression with a full-duration P1 plus an exact-range P5, proving S2 selects P5 and the drag placeholder changes `[S1,S2,S3]` to `[S2,S3,S1]` while preserving the selected card.
- All `333` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.4] - 2026-08-30

### Changed

- Rebuilt the Storyboard center pane as a responsive three-column visual card grid matching the requested film-board layout while retaining the duration header, selected-Shot Inspector, Add/Delete controls and Apply/Cancel workflow.
- Every Shot card now displays its Timeline time range, duration, preset, core action, environment response, speech count and active P/V/A IDs over a 16:9 visual reference thumbnail.
- Shot thumbnails prefer the actual overlapping Timeline image or cached video preview. A deterministic `NO VISUAL REFERENCE` card is used when that Shot has no valid visual source, preventing a neighboring Shot's image from being shown incorrectly.
- Upgraded Shot movement to real Qt Internal Move drag-and-drop with a visible drop indicator, snap layout and immediate order/time/duration refresh after Drop.

### Verification

- Expanded Storyboard UI coverage to require Icon Mode, Internal Move, enabled drag/drop, a three-column wide layout and non-empty card artwork.
- All `332` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.3] - 2026-08-30

### Added

- Replaced the main `STORYBOARD` action with a dedicated Storyboard Editor window built from the current Timeline Shot, speech and media state.
- Added draggable Shot blocks with live original duration, edited duration, target duration and over/under-target calculations.
- Added draft-only Shot creation, deletion, title/core-action editing and 0.5-second duration adjustment. `Cancel` leaves Timeline untouched; `APPLY TO TIMELINE` commits the entire board as one Undo/Redo operation.
- Storyboard cards report each Shot's current time range, must-complete action, editable speech-layer count and active P/V/A reference IDs.

### Changed

- Storyboard Apply now remaps downstream Shot ranges, Transition/Marker cues, Dialogue/Voice-over/Lyrics layers and media clips to the new order and duration.
- Audio and video spanning multiple reordered Shots are split with adjusted source in/out and playback speed; Media Pool originals remain intact. New Story Beats intentionally return as empty Timeline Shots ready for new media or Type Tool content.
- Any Storyboard structural edit invalidates generated output and marks render Segments dirty, while Cancel never changes render state.

### Verification

- Added UI coverage for live duration accounting, add/delete/reorder and the real Apply button.
- Added dependency-remapping coverage for Shot reorder, deletion, insertion, media splitting and Undo.
- All `332` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.2] - 2026-08-30

### Added

- Added `STORY CUT` beside Storyboard with an editable target duration. Editors can select an unwanted purple Shot Block and press Delete to perform a non-destructive ripple cut across Shots, cues, speech layers and source media while retaining the original Media Pool assets.
- Expanded Design plans now retain their original requested duration as the Storyboard target. Legacy projects recover this value from the latest Design revision, so a 107.5-second speech-safe plan can be reduced back toward the requested 45 seconds without another LM Studio pass.
- Added a render-time visible-text whitelist. Subtitles are permitted only when a synchronized Timeline `on_screen_text` layer exists; otherwise H3 receives a hard visible-text lock that forbids captions, lower thirds and speech burned into pixels.

### Fixed

- Chinese generation commands such as `帮我生成45秒视频...总结以下内容如下` no longer become Workspace names. A valid AI story title now outranks the instruction, and the fallback scanner skips the command to find the first meaningful story sentence.
- Storyboard Shot deletion now updates downstream timecodes, splits spanning audio/video safely, refreshes Shot ownership for Text Layers, invalidates only affected render state and remains fully Undo/Redo capable.

### Verification

- Added naming, subtitle-policy, render-whitelist, legacy-target recovery and Storyboard ripple-cut regressions.
- All `330` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2.1] - 2026-08-30

### Changed

- Missing AI-authored Dialogue／Voice-over／Lyrics is no longer a dead end. Studio still retries LM Studio once; if a broad speech request returns no editable words again, the visual Director Design remains valid and can be applied to the H3 Workspace.
- Added a red `⚠ ADD EDITABLE DIALOGUE / VOICE-OVER / LYRICS` Timeline marker at 0.00s for every unresolved requested role. The marker tells the editor to use the Type Tool, remains visible in saved projects and is deliberately excluded from H3 Prompt, TTS and technical directions.
- Exact time-coded user-authored wording remains a hard contract: Studio deterministically restores it, and Apply/Run is still blocked only if those supplied words genuinely cannot be recovered.
- Speech-reminder warnings are non-modal. Apply completes normally and reports the reminder in the Design Summary, Timeline and status bar instead of opening the former blocking `Invalid AI Design speech tracks` dialog.

### Verification

- Added regressions for generic missing-speech reconciliation, exact authored-speech protection, red Timeline rendering and exclusion of UI-only reminders from H3 Prompt compilation.
- All `325` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.2] - 2026-08-30

### Added

- Completed the Long Timeline Foundation for 120-second projects. Extending a 45-second Timeline now retains the existing production master seed, locks every unchanged Approved 0–45-second Segment for reuse and schedules only the new 75 seconds. Editing an older range explicitly dirties and unlocks only its affected Segment.
- Added automatic partial Smart Render checkpoints after every completed or failed hidden Segment. The canonical Director Project and project render manifest are updated before a full Master exists, so reopening the Project can reuse valid completed work.
- Added deterministic Workspace naming from the first loaded Picture's BLIP `Overview`. When no Picture exists, the first meaningful authored story sentence in Design Requirement becomes the name.

### Fixed

- Fixed provisional Workspace folders remaining named after `Create a 12.00-second full-reference video...` even though the manifest later had a descriptive name. A workspace containing only manifest/calibration/imported sources may now be safely renamed, and all in-memory imported paths are rebased to the new root.
- Prevented imported filenames from becoming project titles when BLIP or Design subject evidence is available.
- Expanded competing identity-reference detection to recognize `matching P1`, bare `P1` and `<Picture 1>` as well as `@P1`; old Design plans can no longer load a separately generated P1-lookalike action frame merely because the `@` was omitted.

### Changed

- Program Monitor, Timeline scene, millisecond scrubber, Render Status Bar and duration-weighted Shot progress now have explicit 120-second regression coverage.
- Resource Estimate now reports cached, non-dirty Segment core time as reusable; the 45→120-second regression reports exactly `75s new / 45s reusable`.
- The existing `_4` project folder is intentionally not moved automatically because it already contains a saved Project and approved render. The new naming policy applies to new or imported-only provisional Workspaces without risking broken saved paths.

### Verification

- Added regressions for P1 Overview extraction, Unicode story-sentence naming, imported-only Workspace rename/rebase, bare-P1 identity filtering, 45-to-120-second approved Segment reuse and partial-render resume checkpoints.
- All `321` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.9] - 2026-08-30

### Fixed

- Fixed the real P1 identity-routing defect found in `Create_a_12.00-second_full-reference_video._Treat_the_current_Timeline_its_activ_3`: support prompts that quoted the words “authoritative recurring face identity” could be promoted ahead of P1. The compiler now gives the explicit support declaration precedence and recognizes `authoritative identity reference` / `authoritative whole-design face identity anchor` on the actual user Picture.
- Prevented an independently generated action-state Picture such as “girl, face matching @P1” from entering the H3 request as a competing face. The real P1 remains the only face source; the Shot action supplies pose and movement. This filter also protects previously saved projects at compile time.
- Kept genuinely separate generated actors available as distinct secondary-character references instead of incorrectly forcing their faces to replace P1 or hiding them as P1 support art.
- Fixed instruction-derived Workspace folders that were allocated before Design completed. If the provisional Workspace contains only its manifest/resource estimate, Apply now renames it to the descriptive generated-reference keyword name before references or project files are written. Durable, saved and legacy Workspaces are never moved automatically.

### Verification

- Replayed the reported project data. Before the fix, the prompt stated that `<Subject 1>` came from `<Picture 2>` and marked Pictures 2-5 as authoritative; after the fix, `<Subject 1>` comes exclusively from `<Picture 1>` and only P1 is authoritative.
- Recompiled the saved project: the two independently generated P1 pose images are excluded, leaving P1 plus the separate adult runner and environment references in the H3 request.
- Added regressions for quoted-authority support prompts, redundant P1 pose generation, distinct secondary actors, provisional Workspace refinement and durable-Workspace protection.
- All `314` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.8] - 2026-08-30

### Added

- Upgraded every recurring-character identity anchor into a deterministic Character Continuity Contract. Face, age, skin tone, hairstyle and hair color, body proportions, upper/lower wardrobe style and color, trousers or skirt, shoes and accessory ownership are fixed by default.
- Explicitly separated motion-safe variation: expressions, poses, arm/leg angles, walking/running phase and physically caused hair or clothing motion remain free to change with each Shot.
- Restricted wardrobe/hairstyle changes, injury, dirt, damage, shoe removal and accessory loss or transfer to explicitly authored story events. The changed outgoing state must persist as every later Shot's incoming state until another authored change.

### Changed

- The contract is written into the identity reference, Design Constraints, independent T2I support-reference prompts and the final H3 `subject_definitions`/`detailed_description`. Supporting generated Pictures inherit the current wardrobe and prop ledger but remain unable to redefine the face.
- The Design system prompt now requires appearance-state transitions to cross Shot and Segment boundaries without an unexplained reset.

### Verification

- Replayed both user-supplied P1 and generated-only identity-anchor paths; each produces the fixed/variable/story-only contract idempotently, while support images receive the same current-state guardrails.
- All `309` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.7] - 2026-08-30

### Fixed

- Rejected copied instruction prose such as `Create a 12-second full-reference video...` as a Workspace title. Generic, corrupted and non-ASCII-only titles now use the complete first generated-reference keyword group, for example `marathon_track_morning_sunlight_trees`.
- Made an explicitly authored user Picture face/identity reference authoritative over every independently generated Picture. The supplied Picture is widened to the whole Design; generated references lose any accidental identity-anchor flag and become environment, prop or action-state support with no readable competing face.
- Clarified the final Ref2VA subject definitions and retention analysis so the authoritative face Picture and support-only Pictures cannot be interpreted as equal identity sources. The official `summary:\n[reference generation]` first-line contract remains enforced.
- Added lightweight `shots/SHOT_ID/shot_manifest.json` mirrors. Shot folders now expose Timeline/source ranges and portable Preview/Final Segment references while keeping each MP4 stored only once under `segments/SEGMENT_ID/takes/`.

### Verification

- Replayed the reported marathon Design plan: its Workspace name resolves to `marathon_track_morning_sunlight_trees`, `P1` is the sole whole-design identity anchor, and all four generated Pictures point back to P1 without retaining a generated identity anchor.
- Added Shot manifests to the reported Workspace for S1-S4 without creating any per-Shot MP4 copy.
- All `309` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.6] - 2026-08-30

### Fixed

- Fixed a universal Smart Render mapping defect where the global `unique_media` upload union repatched every Segment Workflow. When different Segments reused the same physical Loader node, the final Segment's file could overwrite every earlier Segment and replay the wrong reference. Segment Workflows now retain their own active upload names; the union is used only for one-time upload.
- Updated portable-media validation to support several valid virtual assets sharing one physical Loader across different Segments while still rejecting missing, unbacked and stale files.
- Added one whole-design generated character identity anchor when three or more independently generated Pictures contain a recurring person. Supporting action/environment references can no longer define a competing prominent face.

### Added

- Added a deterministic speech-duration budget based on language, punctuation and Delivery. Unlocked over-dense generated speech extends its owning Shot and shifts all later Shots, Text Layers, cues and media ranges on the 0.5-second grid.
- User-authored exact timecodes remain locked. Over-budget Dialogue, Voice-over and Lyrics clips render deep red with a bright-red edge so the user can see where H3 may speak early, reorder, omit or change words.
- Added Standard Pipeline Release Gate 6 for the `unique_media`/Segment Workflow collision. The previous compact Segment storage/reload gate is now Gate 7.

### Verification

- All `304` bundled tests pass.
- All seven Standard Pipeline Release Gates pass independently.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.5] - 2026-08-29

### Fixed

- Fixed Storyboard appearing unresponsive when a loaded project saved its Playhead exactly on the exclusive Work Area end. Storyboard now rewinds to the Work Area start, switches to Timeline source/audio and begins playback immediately while preserving the generated Final on the comparison side.
- Fixed `RUN+QUEUE` being silently redirected back into Storyboard or Motion Preview by a hidden persisted quality-profile state. `RUN+QUEUE` is now an independent settings-quality Final render; `PREVIEW 0.2MP` and `ACCEPT>1.0MP` retain their dedicated seed-reuse workflow.
- Removed the unreachable legacy upload branch that remained after the old Preview gate, leaving one authoritative ComfyUI generation path.

### Verification

- Reproduced the correction against `h3_project_young_male_influencer`: a saved 45.00-second Playhead rewinds to 0.00 and plays in Storyboard; the following `RUN+QUEUE` enters the Final generation path exactly once.
- All `299` bundled tests and all six Standard Pipeline Release Gates pass.
- Project format remains `20`; Workspace layout remains `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.4] - 2026-08-29

### Added

- Added Workspace layout 2 compact Segment storage. Every actual Render Segment now owns at most one `motion_preview.mp4` and one `approved_final.mp4`; Shot state stores portable Segment references plus Timeline and source in/out ranges.
- Added verified layout 1 migration. Legacy per-Shot Takes and `approved.mp4` aliases are removed only after their SHA-256 matches a successfully archived canonical Segment asset.
- Added relative Take paths for cross-computer project restoration and a post-save cache reclaimer that removes only an exact completed `.director_cache/generated_outputs/<kind>/<seed>` run after the Master and every Segment asset are verified inside the Workspace.
- Added Standard Pipeline Release Gate 6 covering a 45-second three-Segment/nine-Shot Preview and Final, middle-Segment rerender, unchanged outer Segments, project reload and cache cleanup.

### Changed

- Smart Render manifests now point to durable `segments/SEGMENT_ID/takes` outputs instead of disposable cache paths, preserving future reuse after cache cleanup.
- Full Preview and Final masters remain the two stable root files `generated_preview.mp4` and `generated_output.mp4`.

### Verification

- The real `h3_project_young_male_influencer` structure was exercised through a hard-linked shadow migration: 29 MP4 paths / 714.60 MB logical size became 8 MP4 paths / 244.33 MB, with all six Segment tier assets and all nine Shot references verified.
- All `298` bundled tests and all six Standard Pipeline Release Gates pass.
- Project format is `20`; Workspace layout is `2`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.3] - 2026-08-29

### Added

- Added a persistent `SUB OFF / SUB ON` switch beside Design Requirement and `LANG`. It defaults to off; on creates synchronized, editable subtitle Text Layers from Dialogue, Voice-over and Lyrics.
- Added a deterministic editable-speech contract. A Requirement that asks for Dialogue, Voice-over/narration or Lyrics must produce matching A-track `text_layers` with `explicit_user_requested=true`.
- Added descriptive fallback Workspace naming for non-ASCII titles. When a Chinese title cannot form an ASCII folder slug, Design now uses the first useful subject-media keyword, for example `h3_project_female_protagonist`.

### Fixed

- Reset the shipped and local Design language default to `Auto`. The previous persisted `English` selection could override a Chinese Requirement before Qwen was called.
- Dialogue and narration can no longer be hidden as English quotations inside Shot instructions. Missing editable speech tracks or wrong-language generated lines are rejected and retried once; Apply remains blocked if the retry still violates the contract.
- With subtitles off, AI-invented caption layers and theme hashtags are removed deterministically. Explicitly requested non-subtitle title/on-screen text remains supported.
- Preview and final publication now maintain only the stable user-facing Workspace masters `generated_preview.mp4` and `generated_output.mp4`; assembled full-length masters are no longer duplicated into an additional render-take history. Per-Shot Takes remain intact for editable Smart Render.
- Portable project reload now prefers the matching root Preview/Final master.

### Verification

- Added regressions for missing Voice-over tracks, speech hidden in Shot prose, subtitle off/on behavior, Auto language UI state, setting persistence and non-ASCII project naming.
- All `293` bundled tests and all five Standard Pipeline Release Gates pass.
- Project format remains `19`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.2] - 2026-08-29

### Added

- Added a compact `LANG` selector beside the Design Requirement dialogue-engine buttons with Auto plus MiniMax H3's 11 stably supported dialogue languages: Arabic, Chinese, English, French, German, Italian, Japanese, Korean, Portuguese, Russian and Spanish.
- Added persistent `H3_DESIGN_DIALOGUE_LANGUAGE` storage in `design_ai.env`.

### Fixed

- Auto language now deterministically resolves explicit language wording and the requirement's writing system before the LM request; a Chinese requirement therefore defaults generated dialogue to Chinese instead of English.
- Design planning and BLIP refinement now receive a mandatory dialogue-language contract. Generated Dialogue, Voice-over and Lyrics with an obvious wrong language/script are rejected and retried once instead of silently reaching Apply.
- Exact user-authored words remain protected and are never translated by the new language selector.

### Verification

- Added language-catalog, automatic-detection, wrong-script rejection, prompt-contract, setting-round-trip and Design UI regressions.
- All `289` bundled tests and all five Standard Pipeline Release Gates pass.
- Project format remains `19`; Smart Render policy remains `11`.

## [0.3.1-alpha.1.1] - 2026-08-29

### Changed

- Reordered the Generation Work Area controls as: Work Area, Aspect, Export API, ComfyUI address, Test Connect, Run+Queue, Storyboard, Preview 0.2MP, Accept 1.0MP, Reject and Estimate.
- Replaced the long quality selector with direct `STORYBOARD`, `PREVIEW 0.2MP` and `ACCEPT>1.0MP` actions while retaining the same persisted quality-profile state.
- Compacted `EXPORT ACTIVE API`, `TEST CONNECTION` and `UPLOAD + QUEUE` to `EXPORT API`, `TEST CONNECT` and `RUN+QUEUE`; full descriptions remain available through hover tooltips.

### Verification

- Added a toolbar-order regression covering all eleven requested control groups, compact labels, hover descriptions, hidden persisted quality state and direct Storyboard activation.
- All `286` bundled tests and all five Standard Pipeline Release Gates pass.
- Project format remains `19`; Smart Render policy remains `11`.

## [0.3.1-alpha.1] - 2026-08-29

### Added

- Added the first budget-aware long-form production foundation: one project now owns one stable Workspace containing project snapshots, Design revisions, imported and generated media, audio, Shot Takes, Preview/Final renders, proxies, cache and logs.
- Added non-destructive project-format 19 migration. Opening a format 18 or older project preserves the original JSON and records it in `project_manifest.json`; future saves use `project/director_project.h3director.json`.
- Added immutable per-Shot Take state with seed, quality profile, latest Take and approved Take. Preview, accepted and final outputs are archived with hard links when possible so historical Takes do not multiply video storage.
- Added visible Storyboard, Motion Preview 0.2MP and Approved Final 1.0MP quality tiers. Approved Final requires a completed preview and reuses its seed.
- Added per-Workspace resource estimates, observed render calibration and a configurable free-disk reserve that blocks unsafe generation before TTS/H3 work starts.
- Added `V0.3.1_ACCEPTANCE_CHECKLIST.md` as the staged release contract for the 45-to-120-second and future long-form workflow.

### Changed

- Repeated Design operations now create `R####` revisions inside the same Workspace instead of timestamped top-level project folders.
- Newly loaded Media Pool sources are hard-linked or copied into `media/imported`; legacy sources remain untouched until explicitly replaced.
- Preview and final masters use separate render directories while root-level compatibility links remain available to older scripts and portable projects.

### Verification

- Project Workspace, portable relocation, legacy preservation, quality-tier dispatch, resource calibration, Shot Take persistence and Settings `.env` round-trip regressions are included.
- All `285` bundled tests pass. All five Standard Pipeline Release Gates pass: P/V/A mapping, post-Design Timeline reconciliation, track-kind repair, 15-second continuity without replay and backend rejection of missing/stale cross-computer media.
- Project format is `19`; Smart Render policy remains `11`.

## [0.3.0-alpha.5] - 2026-08-29

### Added

- Added `short-drama-h3-director`, a Studio-native adaptation of the MIT-licensed `POUND0423/AI-drama-pound` short-drama screenwriting workflow. The new Default-bound Special Skill adds causal conflict, planted reversals, character/prop continuity, exact authored `text_layers`, vertical composition, executable Shot budgets, reference-media planning, location sound and episode-hook validation for H3 Director Design JSON.
- Added the full Chinese mirror `SKILL.cn.md` and retained the upstream MIT notice in `THIRD_PARTY_LICENSE.txt`.
- Added `SPECIAL SKILL CREATOR` beside the Default and Special selectors. It can create or edit English/Chinese Special Skill files, choose `Default + Special` or Standalone binding, validate metadata and instructions, then reload and apply the saved Skill without restarting Studio.
- Added automatic storage, binding, bilingual-content, attribution and toolbar regressions for the new Skill workflow.
- Added a two-round Design regression proving that loaded P1–P3 remain stable, first-round generated images occupy P4–P6, an explicit second-round `@P4` is reused, and three further generated images occupy P7–P9 without renumbering.

### Verification

- The adapted Skill passes the bundled `skill-creator` validator.
- All `276` bundled tests pass, including the new Skill storage/binding/bilingual-attribution checks, Creator toolbar assertion and two-round Media Pool allocation regression. All five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.4] - 2026-08-29

### Changed

- Restored the compact legacy Media Pool header proportions while retaining Virtual Media Pool support.
- Reduced the header typography and padding, compacted logical/Segment totals, and replaced `+ IMAGE / + VIDEO / + AUDIO` with same-row `+I / +V / +A` buttons. Full descriptions remain available through hover tooltips.

### Verification

- Added UI assertions for the compact labels, fixed 30px controls and reduced header typography together with the fixed three-column material grid.
- All `94` Timeline/UI tests and all five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.3] - 2026-08-29

### Changed

- Media Pool now uses exactly three material cards per complete row. Resizing the panel changes card width without silently increasing the grid to four or more columns.

### Verification

- Updated the Media Pool UI regression to require columns `0, 1, 2` at default, narrow and wide panel sizes.
- All `94` Timeline/UI tests and all five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.2] - 2026-08-29

### Changed

- Media Pool now opens in a three-column layout by default, using larger cards for easier visual identification.
- Responsive reflow remains enabled: a narrow panel can use two columns, while widening the panel continues to add columns automatically.

### Verification

- Added a UI regression assertion for the default three-column layout while retaining narrow- and wide-panel reflow coverage.
- All `94` Timeline/UI tests and all five Standard Pipeline Release Gates pass.
- Project format remains `18` and Smart Render policy remains `11`.

## [0.3.0-alpha.1] - 2026-08-29

### Added

- Promoted cross-computer missing-media protection into the independent fifth mandatory Standard Pipeline Release Gate.
- Gate 5 now verifies PNG/WEBP pictures, WAV/other audio and MP4/other video across both ordinary Preview/Run and Smart Render. A missing local source must stop before upload, `/object_info` or `/prompt`, and inactive LoadImage/LoadAudio/LoadVideo nodes containing stale paths from another computer must be absent from the compiled Segment workflow.

### Verification

- All five mandatory Standard Pipeline Release Gates pass.
- All `14` bundled test modules pass independently: `269 tests` total. The Program Monitor Qt Multimedia smoke test also passes when rerun directly.
- Project format remains `18` and Smart Render policy remains `11`; this patch adds release verification and documentation without changing saved-project compatibility or render-cache semantics.

## [0.3.0-alpha] - 2026-08-29

### Added

- Introduced the unlimited Virtual Media Pool. Projects may now own stable `P10+`, `V4+` and `A4+` logical sources while the existing ComfyUI workflow remains the per-Segment execution backend with 9 image, 3 video and 3 audio loader templates.
- Added `+ IMAGE`, `+ VIDEO` and `+ AUDIO` controls to the Media Pool. AI Director Design and authored TTS also create a new logical source automatically when every original workflow card is occupied.
- Added deterministic Segment allocation: active logical sources are sorted by permanent `P/V/A` identity, assigned to free physical loaders, uploaded under collision-safe names and compiled into request-local H3 ordinals. Permanent Media Pool IDs never change when a physical loader changes.
- Added pre-generation capacity validation. The project library is unlimited, but a time interval that exceeds the current workflow's physical 9/3/3 Segment capacity is rejected with the exact interval and media type before Z-Image/TTS/H3 work begins.

### Changed

- Design planning no longer treats empty workflow Loader cards as a project-wide generation ceiling. Long designs can create different reference sets for later Segments, and the Design prompt now distinguishes unlimited logical media from per-Segment physical capacity.
- Smart Render continuity reserves its 24-frame motion loader after dynamic allocation and, when necessary, releases only one eligible automatic video reference for that request. User references and the hidden continuity video cannot collide.
- Director Project format is now `18`, persisting logical source type, permanent reference ID and virtual-source status. Existing format-17 projects remain loadable; v0.3 projects containing P10+/V4+/A4+ require this or a later Studio version.
- Smart Render policy version is now `11`, invalidating Segment caches compiled with physical-loader-owned media identity.

### Verification

- Expanded Standard Pipeline Release Gate 1 to compile and validate P10, V4 and A4 together with sparse legacy P7/V2/A3 references, including copied-file rebasing, upload manifests and physical Loader alignment.
- Added virtual-pool regressions for per-Segment P10/V4/A4 remapping, more-than-nine overlapping-image rejection, repeated logical sources and format-18 project save/reload.
- All four mandatory Standard Pipeline Release Gates pass. The complete bundled suite passes `268` tests.

## [0.2.6-alpha.2] - 2026-08-28

### Fixed

- Removed inactive image, audio and video loader branches from every compiled H3 request, so an old computer's ComfyUI `input` filename can no longer leak into a reopened project's Preview/Run. This specifically fixes stale `authored_timeline_dialogue_*.wav` warnings when Ori / MiniMax H3 Native Dialogue is selected.
- Added a universal pre-Queue portability check for every retained `LoadImage`, `LoadAudio` and `LoadVideo`: each must resolve to a real local file, appear in the upload manifest and use the current deterministic upload name. Missing copied media is reported before ComfyUI generation instead of surfacing later as a background `[Errno 2]` warning.
- Preserved Smart Render's dedicated runtime video loader for the preceding silent 24-frame continuity tail while removing all other inactive loaders. Continuity injection therefore remains compatible with the stricter portability rules.
- Smart Render policy version is now `10`; old compiled Segment cache entries cannot bypass the new loader policy.

### Verification

- Expanded the first mandatory Standard Pipeline Release Gate to simulate a project copied from an unavailable old drive and verify local rebasing, upload rewriting and missing-file rejection for pictures, WAV/audio and MP4/video.
- Added an explicit Ori regression proving an old absolute `authored_timeline_dialogue_30.00s.wav` path and its loader are absent from the compiled request.
- All four Standard Pipeline Release Gates pass. The complete bundled suite passes `265` tests, including all long-render mapping, repeated-media, packed-shot, local-Segment edit and 24-frame continuity regressions.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.6-alpha.1] - 2026-08-28

### Changed

- Rebuilt authored speech as visible Timeline Type clips instead of hidden text appended to visual Shot prompts. Dialogue, Voice-over and Lyrics now remain independently editable on `A4 Dialogue`, `A5 Voice-over` and `A6 Lyrics`; On-screen Text remains on a V track.
- Changing a Type clip's Content Role automatically moves it to the matching visual/audio track. Loading an older project now repairs Dialogue clips previously mutated onto V tracks back to their correct A track.
- H3 prompt compilation now emits one independent, time-coded `TIMELINE TYPE / DIALOGUE TRACK EVENTS` contract. Exact text is emitted only once and is no longer duplicated inside Shot Action prose, reducing Ori paraphrase, omission and repeated-line pressure.
- Each hidden Segment receives only the Type/Dialogue events it owns. Editing the clip text, timing, Speaker, Language, Delivery or Lip Sync continues to invalidate the affected render range and regenerate the current Ori prompt automatically.
- Smart Render policy version is now `9`, so cached Segments compiled with the former Shot-embedded dialogue policy are not reused.

### Verification

- Added regression coverage for old V-track Dialogue migration, visible `DIA` clips on `A4 Dialogue`, independent timed-dialogue prompt compilation and single-occurrence exact text.
- The complete bundled test suite passed: `265` tests. All four Standard Pipeline Release Gates passed.
- Director Project format remains version `17`; existing projects are migrated in memory and need no manual JSON edit.

## [0.2.6-alpha] - 2026-08-28

### Release

- Promoted the latest Director Cut Studio build to `v0.2.6-alpha`.
- This alpha includes visible-scene-driven spatial acoustics, production ambience/Foley/music mixing, natural on-location dialogue treatment, safe LM Studio model replacement/unload handling, and the expanded Segment-mapping Release Gate.
- The complete bundled test suite passed: `263` tests. All four Standard Pipeline Release Gates and all ten Timeline mapping-matrix regressions passed.
- Director Project format remains version `17`; existing projects require no migration.

### Documentation

- Updated README highlights, LM Studio setup and `.env` examples to use the live model alias instead of a deleted quantized GGUF path.
- Documented the three-layer Production Mix, visible-space Reverb/Echo profiles, acoustic inheritance across cuts, Segment-local sound schedules and their isolation from P/V/A mapping.
- Added troubleshooting for LM Studio `model_not_found`, automatic model-family fallback/unload behavior, spatial-acoustics rerendering and the expanded `263`-test Release Gate.

## [0.2.5-alpha.9.6.1] - 2026-08-28

### Verification

- Expanded the mandatory fourth Release Gate with a spatial-audio/Segment-mapping cross-test covering three native windows with small-room, large-hall and open-exterior acoustic profiles.
- Changing only the middle Shot from a large hall to a corridor changed only the middle Segment fingerprint. All request-local image/video/audio bindings, physical H3 reference inputs, effective tags and 24-frame continuity metadata remained byte-for-byte equivalent across the acoustic edit.
- Verified that room profiles and their time ranges remain Segment-local: small-room, large-interior, open-exterior and corridor acoustics do not leak into adjacent native windows.
- All four Standard Pipeline Release Gates passed, followed by all ten Timeline mapping-matrix regressions. The complete `263`-test suite from `0.2.5-alpha.9.6` remains valid because this patch adds verification coverage only and does not change production code.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.6] - 2026-08-28

### Added

- Added deterministic, visible-scene-driven spatial acoustics for small reflective rooms, furnished rooms/offices, medium interiors, large halls, corridors/stairwells, caves/tunnels, vehicle cabins, covered semi-outdoor spaces and open exteriors.
- Every generated Soundscape now contains a time-scoped `Spatial acoustics contract` with space-appropriate decay, early-reflection character and restrained wetness. Every Shot also receives its own `SHOT SPATIAL ACOUSTICS` execution rule for dialogue, Foley and ambience.
- Acoustic spaces persist across close-up/cut changes when no location change is visible, then crossfade only when a later Shot explicitly enters a different space.

### Changed

- Small furnished rooms use close, brighter 0.18-0.45s reflections; large interiors use controlled 0.9-1.8s tails; corridors and caves receive directional returns rather than generic wash.
- Open exteriors use nearly dry 0-0.15s acoustics, no discrete echo and slightly reduced low-mid/proximity fullness, allowing distance, wind and open-air diffusion to replace indoor body.
- Covered stalls and awnings use only short 0.12-0.32s roof/counter/wall reflections while their open street-facing side remains free of an enclosed-room tail.
- The obsolete auto-authored `no artificial reverb tails` phrase is removed from older Design soundscapes before recompilation. Physically plausible acoustic reflections are now explicitly distinguished from duplicated or repeated dialogue performances.
- Time-local Segment audio planning now carries actual Shot start/end times, framing, camera angle and continuity evidence into the acoustic schedule.

### Verification

- Recompiled the reported `rainy_night_confession_20260828_095847_902149` sound design as one continuous `0.00-5.00s covered semi-outdoor space`; the former contradictory no-reverb direction is absent.
- Added regressions for room-size profiles, outdoor de-fullness, covered-space reflections, acoustic location changes, same-location inheritance, legacy no-reverb cleanup and per-Shot/Release-Gate prompt presence.
- The complete bundled test suite passed: `263` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.5] - 2026-08-28

### Fixed

- LM Studio generation now validates a saved model ID against the live `/v1/models` catalogue. If the GGUF was deleted or replaced, Studio selects the closest available model family/alias and persists the repaired selection instead of repeatedly using the stale path.
- Test Connection now replaces an unavailable editable model value with the resolved live model rather than silently retaining text that is absent from the discovered model list.
- LM Studio cleanup now unloads only instance IDs explicitly reported in `loaded_instances`; an unloaded or deleted saved model is already considered released and no longer causes repeated `model_not_found` requests.
- Saved full GGUF paths and LM Studio's shorter model aliases are matched safely during cleanup, while unrelated models with similar basenames remain isolated.
- Media Pool AI Semantic Enrichment receives and persists the same resolved LM Studio model, so Design and background enrichment cannot drift onto different stale identifiers.

### Verification

- Verified against the configured live LM Studio server at `192.168.0.185:1234`: 28 models were discovered and the deleted/stale GGUF path resolved to `qwen3.8-27b-uncensored-hauhaucs-aggressive-mtp`.
- Added regressions for deleted models, unloaded catalogue entries, quantized-family fallback, full-path-to-alias cleanup and unrelated-model isolation.
- The complete bundled test suite passed: `261` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.4] - 2026-08-28

### Added

- Added a universal three-layer production-audio contract to every Design and Timeline render: continuous diegetic location ambience, exact-frame contact Foley/one-shot SFX, and foreground authored speech.
- Added automatic story-aware non-diegetic music when the field is blank, plus a stable mix contract that keeps music audible between lines and transitions while ducking it beneath dialogue and important diegetic effects.
- Every Shot now receives an executable sound instruction requiring continuous location tone and physically caused, perspective-correct Foley/SFX with natural decay.

### Changed

- Native H3 Dialogue is now directed as live on-location production sound with conversational timing, natural breath and micro-pauses, camera-distance perspective, subtle early reflections and low environmental bleed instead of a dry announcer or studio voice-over.
- VoxCPM2 Voice Design now favors organic on-location film performance, restrained everyday projection and phrasing-driven emotion; Edge TTS applies a small delivery-aware rate/pitch adjustment instead of one fixed cadence.
- VoxCPM2/Edge authored WAVs are now classified as clean dialogue stems rather than finished soundtracks. H3 preserves their exact wording, speaker identity, timing and phoneme rhythm while spatializing them and generating ambience, Foley/SFX and ducked music around them.
- The Timeline TTS signature now includes the `on_location_production_v1` voice policy, so an older dry authored WAV is rebuilt automatically before Preview/Run.

### Verification

- Added regressions for sound/music contract idempotence, story-aware Foley and score selection, on-location VoxCPM instructions, native and supplied-dialogue spatialization, and authored-TTS stem retention semantics.
- Expanded the mandatory fourth Release Gate to require the production-mix, music-mix and per-Shot sound contracts in every native Segment prompt.
- The complete bundled test suite passed: `258` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.3] - 2026-08-28

### Fixed

- Hidden Segment prompts now filter project-global time-scoped visual style, reference rules, soundscape, music, constraints, technical rules and ending directions to the active render window, then rebase retained ranges onto the Segment's local clock.
- Earlier and later phases are removed from the executable Segment prompt instead of being reinterpreted from local `00:00`; this prevents a later Shot from blending an earlier location, lighting state, ambience or music phase into its opening frames.
- Segment prompts now state that the retained timed phase overrides incompatible untimed modifiers and that only subjects, locations, props, lighting states and actions present in the local Shots or active references may become visible.
- Smart Render policy version is now `8`, invalidating cached Segments compiled with the older leaking prompt policy while leaving the saved Director Project schema unchanged.

### Verification

- Added deterministic parser regressions for English numeric ranges, clock timecodes, point events, partial-window clipping, year-range safety and removal of off-window phases.
- Expanded the mandatory fourth Release Gate to verify that visual style, soundscape, music and constraint schedules never leak across native 15-second boundaries.
- Recompiled the reported `ai_design_20260828_014726_319700` final 25-30s window: P6 remains the sole active image, physical node `154` remains request-local `<Picture 1>`, the previous 24 frames remain `<Video 1>`, and the cotton-field schedule is absent from the final Segment prompt.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.2] - 2026-08-27

### Fixed

- Reopened long projects now patch every physical image/video/audio loader in every Segment to its collision-safe ComfyUI upload name. Inactive H3 references remain disconnected, but ComfyUI validation no longer reports misleading missing original basenames for orphan loader widgets.
- Portable project loading now rebases missing absolute media paths against the loaded project folder, including paths relative to the former `example_work_dir` and unambiguous nested matches. A recovered local file is no longer overwritten by the stale saved absolute path.
- Reopened projects continue saving beside the project that was actually opened instead of writing into an old work folder from another machine or drive.
- Regular and Smart Render workers now stop before queueing when a declared local reference is genuinely missing, with an actionable re-link error instead of silently skipping its upload.

### Verification

- Added regressions for all-loader Segment patching, portable nested-media rebasing and missing-reference preflight.
- Thirty-three relevant workflow, Smart Render, portable-project and project-round-trip regressions passed.
- The mandatory four-part Standard Pipeline Release Gate passed: sparse P/V/A executable mapping, post-Design Timeline reconciliation, V/A track-kind integrity, and native 15-second 24-frame continuity without replay or slot collision.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9.1] - 2026-08-27

### Changed

- VoxCPM2 now unloads immediately after the final source utterance WAV is written, before FFmpeg Timeline composition begins, so the multi-gigabyte model is not retained during audio post-processing.
- Model release is explicit and idempotent: it drops model references, runs Python garbage collection, clears CUDA cache/IPC, and reports both the unloading and released stages. All success and exception paths still terminate the isolated worker, allowing Windows to reclaim any remaining VRAM and DRAM.

### Verification

- Five focused provider lifecycle regressions passed, covering Timeline composition, CUDA-load fallback, CUDA-inference fallback, missing-model validation and idempotent model release.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.9] - 2026-08-27

### Fixed

- VoxCPM PyPI `2.0.3` compatibility: Studio no longer passes the unsupported `seed=` keyword to `VoxCPM._generate()`. The isolated worker seeds Python, NumPy and Torch RNGs before each line, preserving deterministic Speaker voices across both the PyPI and newer GitHub APIs.
- A Design-authored TTS failure no longer leaves a new project with an empty Timeline. Studio commits the planned Shots, visual materials and exact Text Layers, excludes the failed/silent Audio placeholder, and marks authored speech stale so the user can switch to `Etts` and rebuild on Preview/Run without loading the Design JSON again.
- CPU fallback progress now retains the CUDA failure reason instead of immediately overwriting it with a generic `loading model on cpu` message.

### Verification

- Added regressions for the seedless VoxCPM 2.0.3 API and recoverable Design Apply after authored TTS failure.
- A project-local VoxCPM2 CPU smoke run loaded the complete model and entered waveform inference without the previous `unexpected keyword argument 'seed'` exception; the long CPU benchmark was then stopped intentionally.
- The complete bundled test suite passed: `250` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.8] - 2026-08-27

### Added

- Added one explicit project-local VoxCPM2 weight location: `models/VoxCPM2/`. Large weights are excluded from GitHub and the bundled `ai_libraries_common` runtime so users can download them separately.
- Design highlights the `Vox` button and shows a `VOXCPM2 MODEL MISSING` panel when the required snapshot is absent or incomplete.
- Main Settings now displays a persistent ready/missing VoxCPM2 model status with the exact expected path and missing files.
- Apply, Preview and Run now preflight the local snapshot before reserving or rebuilding authored speech.

### Changed

- The VoxCPM2 worker no longer resolves `openbmb/VoxCPM2` through a hidden Hugging Face cache and never downloads model weights during generation.
- Added `models/README.md` with the accepted weight and AudioVAE filename alternatives; `.gitignore` retains the instructions while excluding downloaded weights.

### Verification

- Added regression coverage for the missing-model worker guard and both highlighted UI entry points.
- The complete bundled test suite passed: `249` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.7] - 2026-08-27

### Changed

- VoxCPM2 Local `auto` mode now attempts explicit CUDA whenever the bundled PyTorch runtime reports CUDA availability; the previous automatic CPU selection below 8 GB VRAM has been removed.
- If CUDA fails while loading VoxCPM2 or while synthesizing a dialogue line, the isolated worker releases the model and CUDA cache, reloads on CPU and retries the same line automatically.
- Runtime progress now identifies the attempted device, the ready device and any CUDA-to-CPU fallback stage.

### Verification

- Added regressions for CUDA model-load failure and CUDA inference failure, including exact CPU retry behavior.
- The complete bundled test suite passed: `248` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.6] - 2026-08-27

### Added

- Added three exclusive Dialogue mode buttons beside `DESIGN REQUIREMENT`: `Ori` (MiniMax H3 Native Dialogue), `Vox` (VoxCPM2 Local) and `Etts` (Edge TTS).
- Added `h3_native` as the persistent Settings／`.env` mode and made it the safe default for new workspaces.
- Switching an Ori Design to Vox／Etts from Timeline Settings now reserves an empty physical Audio slot, builds the authored WAV and restores it to Timeline automatically before Preview／Run.

### Changed

- The Design button choice is applied to the current project and persisted to `.env`; users can still override it later from the main Settings page without reopening Design.
- Ori mode explicitly bypasses and disables any previous authored-speech WAV while retaining the editable Text Layers for native H3 dialogue generation.
- Vox／Etts mode restores a deleted Timeline authored-speech clip when its reusable Media Pool source remains, or creates a fresh authored Audio reference when a free slot exists.

### Verification

- Added regressions for the three Design buttons, native default validation, Ori-to-Vox Audio reservation and native exclusion of an old TTS reference.
- The complete bundled test suite passed: `246` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.5] - 2026-08-27

### Added

- Qwen Design planning now assigns female on-screen speakers to `S1` and male on-screen speakers to `S2`, keeps the identity stable across Shots, and preserves an explicit user Speaker override.
- Added automatic diegetic ambience and contact-foley planning, with dialogue foregrounding and background/music ducking instructions.

### Fixed

- Exact-text protection no longer overwrites Qwen's valid gender-aware Speaker assignment with default `S1`.
- Editing Timeline Dialogue, Voice-over or Lyrics now makes the previous authored WAV stale, rebuilds it through the selected Edge/VoxCPM2 provider, refreshes the Shot/H3 Prompt, and prevents generation from resuming with an intermediate obsolete WAV.
- Preview and Run automatically enable, un-bypass and unmute the generated authored-speech Audio reference; if other A Tracks are soloed, the speech track joins the solo set.
- The current Timeline text becomes the updated authored-text contract after an intentional edit, so validation protects the edited words instead of demanding the superseded Design wording.

### Verification

- Added regressions for gender-aware Speaker preservation, explicit Speaker priority, automatic soundscape generation, edited-dialogue TTS invalidation/signatures and authored A Track recovery.
- The complete bundled test suite passed: `244` tests.
- Director Project format remains version `17`; no saved-project migration is required.

## [0.2.5-alpha.4] - 2026-08-27

### Added

- Added `Auto`, `CUDA preferred` and `CPU only` BLIP inference choices to the main Settings page and the persistent `H3_BLIP_DEVICE` environment setting.
- Auto is the safe first-run default: it loads BLIP on CPU, verifies a real CUDA operation, moves the model to CUDA when supported, and retains the existing same-job CPU fallback for any later inference failure.

### Changed

- Image BLIP analysis now runs one purposeful observation per crop instead of three repetitive conditional prompts per crop.
- Raw Recognition now removes echoed prompt prefixes, merges captions that add no meaningful visual evidence, replaces older BLIP blocks on re-analysis, and reports the inference device once in one compact summary.

### Verification

- Added deterministic tests for repeated prompt cleanup, semantic deduplication, preservation of genuinely new region evidence, legacy-output replacement, and the safe Auto settings default.
- Confirmed the actual local BLIP model loads CPU-first in Auto mode, selects CUDA after its runtime probe, and completes an image caption on CUDA.
- The complete bundled test suite passed: `241` tests.

## [0.2.5-alpha.3] - 2026-08-27

### Fixed

- BLIP now detects incompatible CUDA runtime／GPU-kernel failures during both model startup and individual image inference.
- The exact pending BLIP job is automatically retried with a freshly loaded CPU model instead of returning a permanent `no kernel image is available for execution on the device` error.
- Studio remembers an internal BLIP CUDA fallback for the current session, so later worker restarts begin directly on CPU.
- The legacy one-shot BLIP worker now follows the same safe CPU fallback policy.

### Documentation

- Added cross-computer deployment guidance explaining why the destination driver's CUDA version does not replace the CUDA runtime bundled with its copied PyTorch environment.

### Verification

- Added regression coverage for CUDA architecture errors and confirmed unrelated media errors do not trigger a misleading CPU retry.
- The complete bundled test suite passed: `236` tests.

## [0.2.5-alpha.2] - 2026-08-27

### Fixed

- Explicit Design duration now comes deterministically from phrases such as `30秒的视频`／`2分钟的视频` and the latest authored timecode, rather than the current workspace Timeline duration.
- Added an immutable Duration Contract to LM planning; an initial mismatch receives one automatic full-plan retry, while a refinement mismatch retains the validated first plan.
- Normalize, Load JSON, Apply and Run now reject plans that condense or stretch an explicitly requested duration.
- Timed Dialogue, Voice-over, Lyrics and On-screen Text now use the user-authored duration when preserving and validating cues, preventing all text after an incorrect LM duration from being silently clipped.

### Verification

- Added the exact 30-second four-dialogue regression and a 12-second workspace precedence regression.
- Confirmed explicit 30-second, 2-minute, final-timecode-only and 45-second Chinese duration inference while rejecting age text such as `39岁` as a duration.
- The complete bundled test suite passed: `235` tests.

## [0.2.5-alpha.1] - 2026-08-27

### Documentation

- Added a Common Issues explanation for action／boundary image requests that incorrectly use neutral, blank or studio backgrounds.
- Clarified that `Image media request N` is the ordinal image request in Design JSON and is not necessarily Media Pool `PN`.
- Added incorrect and corrected Prompt examples, the global Identity Reference exception and exact repair steps.

### Verification

- Confirmed README version and complete-suite count now match `v0.2.5-alpha.1` and the latest `233`-test result.

## [0.2.4-alpha.9.6] - 2026-08-27

### Added

- Added a persistent `Dialogue Text Layer TTS` selector to the main Settings page with `Edge TTS` and `VoxCPM2 Local` choices.
- Added the first native VoxCPM2 adapter to `tts_service.py`: local-only model loading, deterministic per-Speaker Voice Design, exact Timeline WAV composition and provider metadata in the generated sidecar.

### Changed

- VoxCPM2 is loaded once for all authored lines in one Design Apply job. The crash-isolated worker releases the model and CUDA cache after composition.
- Auto device selection uses safe CPU mode below 8 GB VRAM instead of attempting a likely GPU out-of-memory load.
- A selected VoxCPM2 failure now stops Apply explicitly instead of silently falling back to Edge; Edge retains its existing Windows SAPI fallback.

### Verification

- Added Settings persistence, invalid-provider, provider-selection and deterministic VoxCPM2 voice-control regressions.
- Confirmed the cached `openbmb/VoxCPM2` checkpoint loads through the bundled runtime in safe CPU mode; the complete waveform/compositor path is covered by an isolated provider integration test.
- The complete bundled test suite passed: `233` tests.

## [0.2.4-alpha.9.5] - 2026-08-27

### Added

- Added `run_voxcpm2_webui.bat`, which always launches VoxCPM2 through the bundled `ai_libraries_common/python_env` and defaults to the local-only `127.0.0.1:8088` endpoint.

### Fixed

- Documented that `app -port 8088` invokes the wrong Python association and uses an invalid single-dash argument; the supported direct form is `python app.py --port 8088`.

### Verification

- Confirmed `funasr 1.4.3`, `voxcpm 2.0.0` and the VoxCPM2 `app.py` argument parser through the bundled runtime.

## [0.2.4-alpha.9.4] - 2026-08-26

### Fixed

- AI Design no longer treats an editorial `A1` track chosen for authored Dialogue, Voice-over or Lyrics as proof that a real Media Pool `@A1` asset exists.
- Deterministically extracted timed text is now restored before media-plan repair, allowing an empty hallucinated A1 speech reuse to be removed and replaced later by the real `authored_speech_tts` request during Apply.
- Missing non-TTS Audio references remain strict validation errors, so the repair cannot hide a genuinely missing ambience, music or supplied-audio dependency.

### Verification

- Added regressions for the exact empty-A1 dialogue failure and for preservation of strict missing-audio validation.
- The complete bundled test suite passed: `229` tests.

## [0.2.4-alpha.9.3] - 2026-08-26

### Added

- Installed the complete official VoxCPM2 source dependency set into the bundled `ai_libraries_common/python_env`, including audio I/O, text normalization, ModelScope, FunASR, Gradio and voice-cloning support libraries.
- Installed the local `ai_libraries_common/VoxCPM-main` checkout as editable package `voxcpm 2.0.0`; the ZIP checkout receives a local build-version override because it does not contain Git metadata for `setuptools-scm`.

### Changed

- Replaced the unmatched `torch 2.12.1+cu126` runtime with the official ABI-matched `torch 2.11.0+cu126` and `torchaudio 2.11.0+cu126` pair. CUDA 12.6 remains active.

### Verification

- Verified imports for `voxcpm`, `torchcodec`, `torchaudio`, `librosa`, `soundfile`, `einops`, `pydantic`, `gradio`, `funasr`, `modelscope` and `wetext`.
- Verified that BLIP classes still import after the Torch change, CUDA remains available, and `pip check` reports no broken requirements.
- VoxCPM2 model weights are not part of this dependency installation; Edge TTS remains the active Studio engine until the local VoxCPM2 adapter is enabled.

## [0.2.4-alpha.9.2] - 2026-08-26

### Added

- Added a deterministic, timecode-aware Design parser for exact `Dialogue`, `普通话对白`, `旁白`, `Voice-over`, `Lyrics` and `On-screen Text`; these cues are created with `explicit_user_requested=true` before LM planning.
- Added an authored-text contract saved in Director projects. Apply and Preview / Run now stop with a precise error if explicit timed words have been lost or silently changed.
- Added asynchronous Mandarin neural TTS through `edge-tts 7.2.7`, with S1/S2 Mandarin voices, Windows SAPI fallback, exact Timeline placement, long-line tempo fitting, WAV composition and automatic A Track loading.
- Added hidden-segment TTS window extraction, so Smart Long Render and local Segment re-renders receive the correct part of the full authored speech instead of replaying the first line.

### Fixed

- LM image-caption Refinement can no longer erase or paraphrase Dialogue, Voice-over, Lyrics, On-screen Text or an explicitly requested theme from the first Design Plan.
- H3 prompts no longer claim that supplied audio exists when no valid Audio reference is active. Without Audio they request exact native-language speech; with Audio they identify the actual request-local `<Audio N>` and require precise phoneme/lip synchronization.
- AI Design no longer commits the old silent audio placeholder when explicit speech synthesis fails; Apply is stopped and the failure is shown to the user.

### Verification

- Added deterministic text-role, exact-word protection, Apply/Run contract, audio-conditional prompt, TTS tempo-chain and A-slot reservation regressions.
- Confirmed a real `zh-CN-XiaoxiaoNeural` Mandarin WAV through the bundled runtime and FFmpeg compositor.
- The complete bundled test suite passed: `227` tests.
- Director Project format is now version `17`; older projects remain loadable, and newly saved projects retain the authored-text contract.

## [0.2.4-alpha.9.1] - 2026-08-26

### Added

- Added a mandatory input-repair compiler to the English and Chinese `wuxia-blade-film` Skill. User-supplied Shot wording is now treated as creative intent rather than an immutable execution contract.
- Added preflight detection for missing or uneven timing, overloaded five-second windows, conflicting slow/fast instructions, repeated bullet-time, qi used as a movement shortcut, unsupported flight, full 360-degree combat orbits, competing camera programs and multi-phase still-reference prompts.
- Added deterministic rewrite rules that translate those failure patterns into exact 0.5-second ranges, contact-driven environmental reactions, visible launch and landing mechanics, 60–120-degree orientation-preserving coverage, two or three readable contacts and one primary camera movement per Shot.

### Changed

- Action-heavy 45-second inputs now default to nine five-second Shots across three native 15-second movements when the source timing is unusable; the user's story goal, identities, required weapons, key outcome and intensity remain protected while raw Shot count and unrenderable decoration may be restructured.
- The Skill now performs a final clause-level compiler pass and must simplify or split the causal chain until mandatory actions are unlikely to be demoted and the normalized Design is expected to produce zero action-budget warnings.
- Updated the Skill picker metadata so its default prompt explicitly requests diagnosis and repair before H3 choreography.

### Verification

- Added English/Chinese parity coverage for the new repair stage, timing fallback, 360-degree rewrite, camera limit and zero-warning compiler target.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `219` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.9] - 2026-08-26

### Added

- Added `example/one_leaf_kill_45s_design_requirement_v3.txt` and the directly loadable `example/one_leaf_kill_45s_design_plan_v3.json`, organized as nine exact 5-second Shots across three native 15-second render segments.
- Added stable character, weapon, projectile, hat, wound and footing ledgers, plus explicit 15-second boundary states so separately generated segments continue the same physical action without replay.
- Added one-frozen-instant reference-image rules and per-Shot reference budgets to prevent multi-action collages from becoming contradictory H3 guidance.

### Changed

- Replaced visible qi, magical aura, unsupported hovering, long aerial freezes and full 360-degree hero orbits with contact-driven airflow, grounded wall steps, gravity, tile breakage and a short orientation-preserving orbit.
- Limited each Shot to at most three mandatory physical beats and moved leaves, sparks, dust, cloth motion and secondary camera decoration outside the core action budget.

### Verification

- Added regressions for the V3 Shot count, exact timing, native-boundary continuity, projectile direction, duplication guard, frozen-reference rule and direct Design JSON normalization.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `218` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.8] - 2026-08-26

### Added

- Expanded `wuxia-blade-film` with limb, weapon-geometry, attachment, cumulative-damage and footing ledgers for asymmetric survival combat.
- Added an irreversible combat-degradation curve: unequal threat, committed attack, injury adaptation, feral collapse and visibly costly resolution.
- Added causal fragmented-editing rules that preserve one orientation anchor, reveal the physical result immediately after impact occlusion and prohibit random camera shake as a substitute for speed.

### Fixed

- A one-armed fighter can no longer regenerate a hand, use a phantom grip, perform a two-handed guard or gain unexplained balance from an absent limb.
- A broken blade with no usable point can no longer perform a clean thrust or impalement; its permitted actions are constrained to its fixed geometry unless a stable jagged point is explicitly established.
- Chain/rope actions must now preserve origin, attachment point, controlling hand, tension state and visible release or retraction instead of behaving as a duplicated or intangible weapon.
- Damage, damaged armor, breath loss, weakened footing, blood, mud and grip failure must persist through subsequent Shots and native 15-second boundaries.

### Verification

- Added an English/Chinese parity regression for the new limb, blade-geometry, attachment, damage, footing and feral-collapse rules.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `216` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.7] - 2026-08-26

### Added

- Expanded the English and Chinese `wuxia-blade-film` Skill with a renderable brutal-blade grammar: broken-blade inner-circle entry, tension-axis rotation, adhesive short combinations, grounded twin-blade aerial pressure, the decisive speed paradox and H3 timing translation.
- Added explicit direction for dense flurries, range asymmetry, gravity-driven attacks, recovery vulnerability, projectile ownership and close handheld impact coverage without copying game stats into generation prompts.

### Fixed

- Action-budget compression now resolves actor pronouns before selecting mandatory beats. An Assassin's throw, low slide or escape can no longer be silently reassigned to the General when intervening clauses are demoted.
- Automatically recovered or coverage-floor Z-Image requests now describe one frozen outgoing physical state instead of copying a whole multi-action Shot into one still.
- Legacy internal `auto_image_sN` requests are upgraded to the same atomic still format when an older Design JSON is validated or applied.
- Generated action-state references explicitly forbid temporal montages, repeated body positions and duplicate fighters, reducing contradictory pose anchors and character multiplication.

### Changed

- AI Design now requires every multi-character action clause to repeat the explicit role before its verb and weapon; cross-clause `he`, `his`, `she` and `they` are rejected as unsafe choreography notation.
- Action-state image planning now separates identity/ownership requirements, one frozen pose state and story location instead of treating a static reference as a miniature action sequence.

### Verification

- Re-examined the 45-second `one_leaf_kill_20260826_163317_529371` preview at one and three frames per second across all three native segments.
- Validated the updated Skill package in UTF-8 mode.
- The complete bundled test suite passed: `215` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.6] - 2026-08-26

### Fixed

- AI Design no longer rejects Apply when the model incorrectly lists an empty Media Pool slot such as P1 under `existing_media_uses`; the row is repaired into a Z-Image request and keeps its intended physical Picture slot.
- AI Design now enforces a bounded visual-reference coverage floor when LM Studio returns too few or zero image requests: approximately one useful Picture state per five seconds, never more than one per Shot and never beyond the available Picture capacity.
- Z-Image generation now retries each requested Picture once after a transient ComfyUI failure before falling back to a placeholder, reducing partially populated or image-free Design results.

### Changed

- Design validation, JSON loading, LM Studio completion and Apply all use the same media-plan repair path, so an already generated but repairable Design JSON can be validated and applied after restarting Studio.
- The Design system prompt now explicitly requires visual Shots to receive generated or reused Picture coverage while respecting the nine-Picture physical limit.

### Verification

- Added regressions for empty-Picture recovery, zero-image visual coverage, transient Z-Image retry and preservation of the requested physical Picture slot.
- The complete bundled test suite passed: `213` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.5] - 2026-08-26

### Added

- Added `test_standard_pipeline_regressions.py` as a four-part release gate for sparse P/V/A mapping, post-Design Timeline reconciliation, V/A track-type integrity and native 15-second continuity boundaries.
- The Design/Timeline gate also verifies that Shot-reference reassociation remains correct through Undo and Redo.

### Fixed

- Timeline media edits now immediately run Prompt Reconcile, so moving, trimming, changing track or editing a Clip Prompt after Design Apply updates the Creative Brief and generated H3 Prompt without reopening Design.
- Existing AI Semantic reference directions now follow every occurrence of their Media Pool source to the currently overlapping Shot and are removed from Shots that no longer overlap it.
- Runtime track lookup now validates media kind as well as `track_id`; Picture/Video cannot survive on an Audio track, and Audio cannot survive on a Visual track even when an old/corrupt project stores mismatched track data.

### Verification

- The four mandatory release-gate scenarios passed.
- The complete bundled test suite passed: `209` tests.
- The Director Project format remains version `16`; no saved-project migration is required.

## [0.2.4-alpha.4] - 2026-08-26

### Added

- Added an H3 action-generation budget shared by AI Design, manual Shot editing, AI Semantic Enrichment and final Prompt compilation: at most three must-complete physical beats, two required contact consequences and two optional flourishes per five seconds.
- Added structured Shot fields for `continuity_state` and `optional_flourish`, plus deterministic `h3_executable_action` and `action_budget` metadata with visible Design Summary warnings.
- Added English and Chinese generation-budget rules to `wuxia-blade-film`, including native 15-second boundary reservations and an explicit priority ladder.

### Changed

- `subject_action` now represents only the must-complete physical core. Contact-driven consequences remain in `environment_response`; dispensable particles, cloth motion, secondary feints and ornamental camera work are compiled as optional detail.
- Over-budget Shots are priority-compressed: secondary/decorative beats are demoted before the core action can be delayed or replayed. The authored action is retained in budget metadata for review.
- AI Design now rejects overlapping camera Shot Blocks, repairs blank constraints with continuity guardrails, fills legacy continuity state safely and assigns Shot IDs after chronological sorting.
- BLIP refinement and replacement-media Shot adaptations preserve the same core/state/optional hierarchy instead of expanding the action list again.

### Verification

- Added regressions for the new Design JSON fields, legacy-plan defaults, blank-constraint repair, causal setup merging, required-response limits, five-second overload compression, overlap rejection and Timeline Prompt hierarchy output.
- Validated the English and Chinese `wuxia-blade-film` Skill package.
- `205` automated tests passed with the bundled Python environment.
- Increased the Director Project format to `16` because saved Shot cues now include action-priority and continuity fields; older projects load with backward-compatible defaults.

## [0.2.4-alpha.3] - 2026-08-26

### Fixed

- Compacted every active Picture, Video, paired-video-audio and standalone Audio connection into contiguous request-local H3 input slots, so prompt labels and executable ComfyUI fields cannot diverge when Media Pool slots are sparse.
- Kept permanent Media Pool identities such as P5/V2/A3 separate from request-local H3 ordinals, preserving stable Timeline editing, repeated Clip Instances and saved-project references.
- Appended hidden 24-frame continuity video after ordinary active video references and added a hard collision guard that refuses to overwrite Timeline media.
- Removed the false `No previous rendered frame is supplied` sentence whenever the render pipeline may attach previous-segment motion context.
- Improved boundary-state extraction to retain the prior Shot's actual terminal pose, screen positions and camera direction instead of generic text such as `This is the boundary for Part 3`.
- Filled blank structured Shot labels with their stable Shot IDs instead of emitting empty names.

### Changed

- Increased the Smart Render policy to `7`, intentionally invalidating older cached segments compiled with sparse reference bindings or contradictory continuity text.

### Verification

- Added the One Leaf Kill P1/P2/P3/P5 third-segment regression: P5 is described as `<Picture 4>` and is now physically connected to `ref_images.ref_image_3`.
- Added mixed Picture/Video/Audio sparse-slot coverage, hidden-video append ordering, runtime collision protection and concrete boundary-state tests.
- Recompiled the real `one_leaf_kill_20260826_113835_147104` project and confirmed four contiguous image inputs, `<Picture 4>` for P5, `<Video 1>` for the 24-frame context and no contradictory no-frame sentence.
- `199` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; existing projects can be opened without migration.

## [0.2.4-alpha.2] - 2026-08-26

### Added

- Rewrote `example/one_leaf_kill_45s_design_requirement.txt` as a Design-ready V2 with three aligned native 15-second phases and nine exact Shot Blocks.
- Added explicit character, weapon, consumable/prop and spatial ledgers; four-dart accounting; physically tracked chain and hat states; exact 15s/30s exit states; first-new-action instructions; and no-replay boundary rules.

### Changed

- Expanded both `wuxia-blade-film/SKILL.md` and `SKILL.cn.md` with clean Design-handoff guidance, native H3 boundary contracts, spatial travel paths, unambiguous weapon verbs and delayed-prop lifetime rules.
- Updated the Skill UI metadata to reflect multi-segment continuity planning.

### Verification

- Validated the updated Skill package with `quick_validate.py`.
- Verified that the V2 Requirement covers exactly 45.00 seconds as `0–15 / 15–30 / 30–45`, defines exactly nine non-overlapping Shot ranges, and contains explicit no-replay rules at both native boundaries.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.4-alpha.1] - 2026-08-26

### Added

- Added the complete Chinese companion document `skill special/wuxia-blade-film/SKILL.cn.md`.

### Changed

- Small optimizations now increment only the suffix after `alpha`, leaving the three-part base version unchanged.

### Verification

- Verified the Chinese Skill companion covers the complete English workflow, action continuity, camera, physical qinggong, reference planning and quality gate sections.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.4-alpha] - 2026-08-26

### Documentation

- Added the public MiniMax H3 Director Cut Studio tutorial link to the README quick-start section.
- Converted application releases to the `v0.2.4-alpha` numbering style, with each numeric position limited to `0–9` and carrying into the position on its left.

### Verification

- Verified that the README displays the tutorial as a direct clickable link.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.3-alpha] - 2026-08-26

### Changed

- Changed `wuxia-blade-film` to the standard `Default + Special` binding requested for production use.
- AI Design now receives both `h3-prompt-writing` with its Ref2VA guide and the scene-specific wuxia blade-action rules whenever this Special Skill is selected.
- Kept the optional standalone marker mechanism available for future Special Skills, but `wuxia-blade-film` no longer declares it.

### Verification

- Updated the Skill loader and Director Design-context regressions to verify the Default and wuxia Special instructions are both bound.
- `196` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.2-alpha] - 2026-08-26

### Added

- Added the standalone `wuxia-blade-film` Special Skill for fast, physically grounded blade combat, weapon-driven causality, readable signature techniques, kinetic camera loss/reacquisition, synchronized environmental impacts and hard diegetic sound.
- Added a Design-ready 45-second, nine-Shot adaptation of 《一叶杀》 at `example/one_leaf_kill_45s_design_requirement.txt`.
- Added per-Skill `standalone` binding metadata through the `<!-- h3-studio-binding: standalone -->` marker.

### Changed

- When a standalone Special Skill is selected, AI Design receives only that Special Skill; `h3-prompt-writing` and its Ref2VA guide are intentionally omitted from the Design context.
- Updated H3 Prompt Studio binding labels and source preview so standalone Special Skills are no longer presented as `Default + Special`.
- Existing Special Skills remain `Default + Special`, and `None` remains Default-only.

### Verification

- Added regressions for standalone Skill discovery, AI system-prompt isolation and Director Design context isolation.
- `196` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.2.1-alpha] - 2026-08-26

### Fixed

- Fixed the Studio UI freezing when AI ENRICH was started consecutively for three or more Media Pool items.
- Removed all worker stdin writes and flushes from the Qt main thread. Large BLIP evidence, semantic schemas and LM Studio prompts now enter an in-memory queue immediately and are drained by a dedicated background writer thread.
- Applied the non-blocking queue to every persistent JSON worker, including media preparation, multi-region/video BLIP, audio analysis and AI Semantic Enrichment, so a busy child process can apply Windows pipe backpressure without freezing selection, scrolling or further clicks.
- Preserved ready-gating, FIFO request order, crash isolation, pending-job cancellation and worker error logging.

### Verification

- Added a Windows-pipe backpressure regression worker that intentionally refuses to read stdin for one second while the Studio queues three approximately 810 KB requests. All three UI-side enqueue calls return immediately and the worker later receives them in exact order.
- Re-ran multi-region image AI Enrich, video BLIP/audio waiting, manual LM Studio semantic enrichment and worker startup/failure tests.
- `194` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`.

## [0.2.0-alpha] - 2026-08-26

### Fixed

- Fixed AI Design Apply/Undo/Redo leaving the Track Header on the original V3/V2/V1 model after the Timeline had dynamically created V4/V5/V6. Picture clips remained correctly assigned to visual tracks internally but appeared beside A1/A2/A3 labels because the two panes displayed different track lists.
- Added the complete dynamic Track list to the AI Design workspace command state, so Undo restores the earlier track model and Redo restores all Design-created V/A tracks together with their media, text and Shot assignments.
- Rebuilt and resynchronized the fixed Track Header pane whenever an AI Design workspace state is restored.

### Verification

- Reloaded `bangkok_to_meiktila_the_midnight_escape_20260826_080038_515906` and confirmed that both panes expose `V6, V5, V4, V3, V2, V1, A1, A2, A3`; all six placed Picture assets resolve to tracks whose type is `visual`.
- Added an AI Design dynamic-track Apply/Undo/Redo regression test.
- `193` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.1.9-alpha] - 2026-08-26

### Verified

- Added an explicit end-to-end reference-mapping matrix for a single native 1.00-15.00s render, a 14.00-20.00s partial render crossing a reference boundary, and a hidden two-window 1.00-30.00s Smart Render.
- Verified that the second long-form window reserves `<Video 1>` for exactly 24 preceding motion frames while active Timeline video references and synchronized/standalone audio references retain their correct effective ordinals.
- Verified local edits independently in the first, middle and final Segment, plus an authored 30-second Timeline split into three ten-second Shot render units; only the edited unit's content fingerprint changes.
- Verified delete/re-add, movement from an old Segment into a new Segment, movement between compatible visible Tracks, and Track visibility filtering without changing the permanent Media Pool identity.
- Verified two non-contiguous uses of the same physical Media Pool source on one Track (1.00-4.00s and 25.00-30.00s): each window receives one correct H3 connection and its own Clip Prompt, without duplicate loader execution or ordinal drift.
- Re-ran project-format-15 save/restore, mixed Picture/Video/Audio compilation, collision-safe ComfyUI uploads, local cache reuse, 24-frame continuity generation and final Smart Render assembly as part of the complete suite.

### Verification

- `192` automated tests passed with the bundled Python environment.
- The Director Project format remains version `15`; no saved-project migration is required.

## [0.1.8-alpha] - 2026-08-26

### Fixed

- Re-audited the complete workflow from API discovery and Media Pool assignment through AI Design, Timeline Prompt Reconcile, native/Smart Render compilation, ComfyUI upload, segment assembly, generated MP4 archiving and Director Project restore.
- Applied Visual Track visibility and Audio Track Mute/Solo/enable state before compiling both the Prompt ordinals and H3 input connections for native renders and Active API exports; the two sides can no longer disagree after a track is disabled.
- Recompiled every native render directly from the filtered Timeline state so a stale visible Prompt cannot leak an earlier reference map into the queued workflow.
- Converted partial native work areas to segment-local Shot timestamps, preventing a 15.00-23.00s Timeline repair from sending global 16.00-22.00s timestamps into an eight-second H3 request.
- Assigned a deterministic collision-safe ComfyUI upload name to every physical image/video/audio loader and patched each compiled workflow accordingly. Different local files with the same basename can no longer overwrite or impersonate one another during `overwrite=true` uploads.
- Added structured upload manifests to both native and Smart Render workers while retaining backward compatibility with legacy string-only jobs.

### Verification

- Added an end-to-end 30-second Smart Render simulation that validates Segment Prompt tags, active H3 connections, 24-frame continuity Video numbering, paired Video Audio numbering, standalone Audio offset and loader upload names together.
- Added native hidden/Mute mapping, partial-work-area local-time and duplicate-basename upload regression tests.
- `182` automated tests passed with the bundled Python environment.

## [0.1.7-alpha] - 2026-08-26

### Fixed

- Completed a repository-wide Python mapping audit covering Picture, Video and Audio references across Media Pool, repeated Timeline Clip Instances, AI Design, Timeline Prompt Reconcile, classic H3 Studio, native generation, Smart Render and Active API export.
- Canonicalized internally generated bare media mentions such as `P3`, `V2` and `A1` into stable `@P3`, `@V2` and `@A1` references before per-Segment compilation, without rewriting literal product/model names globally.
- Prevented classic H3 Studio AI output and Director Active API exports from reusing a prompt compiled for a different work-area reference map.
- Deduplicated repeated Timeline instances by their physical source node and binding even when an editor instance carries its own node ID.
- Made enabled soundtracks from reference videos explicit in `subject_definitions` and `retention_policy`, and correctly offset standalone `<Audio N>` ordinals behind those synchronized video-audio signals.
- Removed request-local H3 angle-bracket tags from the AI Design Media Pool inventory so Design can author only permanent Media Pool IDs.

### Verification

- All `36` project Python files were statically inspected for reference-number construction, prompt compilation and workflow-binding paths.
- `178` automated tests passed with the bundled Python environment, including a mixed P4/P7/V2/A3 Segment test and inactive-reference anti-alias checks.

## [0.1.6-alpha] - 2026-08-26

### Fixed

- Separated permanent Studio media IDs (`@P4`, `@V2`, `@A1`) from MiniMax H3's request-local `<Picture N>`, `<Video N>` and `<Audio N>` ordinals.
- Remapped authored stable IDs and legacy angle-bracket references only when compiling each active render Segment, including Shot fields, Creative Brief, transition/marker instructions and Clip Prompts.
- Prevented inactive or unavailable legacy references from silently aliasing another connected asset after H3 renumbering; they now compile to an explicit non-reference diagnostic instead.
- Kept AI Semantic Enrichment fingerprints attached to the physical Media Pool source when that source receives a different effective ordinal or is used through a repeated Timeline Clip Instance.
- Updated the Director Cut and classic H3 Studio UI shortcuts to derive numbering from permanent physical bindings rather than mutable prompt tags.

### Changed

- AI Design now writes stable `@P/@V/@A` references in authored JSON and reserves angle-bracket H3 tags for the final per-Segment compiler.

### Verification

- `172` automated tests passed with the bundled Python environment.

## [0.1.5-alpha] - 2026-08-26

### Added

- Added independent Timeline Clip Instances so one Media Pool source can be reused in any number of non-contiguous ranges, tracks or overlapping layers.
- Added per-instance timing, activation, source trim, playback speed, fades, transitions, monitor visibility and Clip Prompt persistence with Undo/Redo.
- Allowed AI Design JSON to route the same `P`/`V`/`A` Media Pool ID into multiple time-scoped `existing_media_uses` rows.

### Changed

- Kept recognition and AI Semantic Enrichment source-owned and automatically shared across all repeated instances.
- Deduplicated repeated instances when assigning effective MiniMax H3 reference ordinals, uploading media and compiling subject definitions, while retaining every time range and per-instance direction in the generated prompt.
- Updated Program Monitor video/audio player keys and Smart Render fingerprints so repeated clips remain independently seekable and locally editable.
- Raised the Director Project format to version `15`; version 14 and older projects continue loading with their original media placements as first-use clips.

### Verification

- `168` automated tests passed with the bundled Python environment.

## [0.1.4-alpha] - 2026-08-25

### Fixed

- Resynchronized the Track Header vertical offset after project loading, dynamic V-track creation and header rebuilding. Picture clips with valid V-track IDs can no longer appear visually aligned with A1/A2/A3 labels because the two panes retained different scroll positions.

### Verification

- `162` automated tests passed with the bundled Python environment.

## [0.1.3-alpha] - 2026-08-25

### Fixed

- Gave the Timeline Tools palette a DPI-aware minimum width based on its longest button and scrollbar, so every icon keeps its visible Selection/Hand/Razor/Shot/Type/Prompt/Transition/Marker label even when the splitter is dragged left.

### Verification

- `161` automated tests passed with the bundled Python environment.

## [0.1.2-alpha] - 2026-08-25

### Added

- Allowed AI Design plans to create and populate editorial tracks beyond V3/A3 (up to V16/A16), including separate visual title and dialogue/voice-over/lyrics lanes.
- Added automatic cross-segment motion context using exactly the preceding 24 frames at 24 fps, without carrying prior audio.
- Added strict single-colour, edge-connected background detection and non-destructive transparent PNG derivatives for Media Pool and Design-generated images.

### Changed

- Reserved one of the three physical H3 video reference inputs for hidden continuity when possible; if all are occupied, the least-specific Auto reference is released for that segment while force-active references remain untouched.
- Raised the Smart Render policy version to `6`, invalidating older segment manifests whose continuity assumptions are no longer safe to reuse.

### Verification

- `161` automated tests passed with the bundled Python environment.

## [0.1.1-alpha] - 2026-08-25

### Added

- Added the machine-readable `VERSION` file and shared `version_info.py` loader.
- Displayed the application version in the main Studio title and Qt application metadata.
- Saved `application_version` beside the independent project-format `version` in every Director Project JSON.
- Added repository-wide line-ending and binary-file rules through `.gitattributes`.
- Documented versioning, runtime downloads, Timeline Prompt Reconcile, semantic Shot adaptation and the current 156-test baseline.

### Fixed

- Corrected a broken Design system-prompt sentence that previously produced `When a Treat each asset...` and weakened Media Pool reuse instructions.
- Updated public README examples to avoid development-machine LAN addresses and accurately describe the Z-Image workflow without RTX upscaling.

### Verification

- `156` automated tests passed with the bundled Python environment.
