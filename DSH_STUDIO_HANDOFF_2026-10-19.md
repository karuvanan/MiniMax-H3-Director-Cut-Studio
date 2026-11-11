# MiniMax H3 Director Cut Studio — DSH 开发接手说明

更新日期：2026-10-19（Asia/Kuala_Lumpur；§13 于 2026-10-21 下午增补，§12 二次更新；2026-10-24 五次更新并新增 §14；2026-10-26 六次更新，新增 §19–§20；2026-10-28 七次更新，新增 §34–§35，§35 内同日追加 Round 35d hotfix——policy 70 的 GUI Preview 路径当时其实是崩的；同日再新增 §35e＝policy 70 首枪已实机跑完并读帧，§35／§35d 的「实机未跑」口径已被取代；2026-10-28 晚间第八次更新，新增 §37l–§37p＝policy 75→76→77，76 测出零增益、77 已实机且用户接受效果；2026-10-29 第九次更新，新增 §38–38b＝policy 78 fullfig 单图路由，已实机三窗，衣柜主色与 silent 改善但眼镜遗失与脸变老尚未解决；2026-10-29 晚间第十次更新，新增 §40＝**只换 workflow JSON**（node 7 → node 9 `RTXVideoSuperResolution` ULTRA ×2 喂 `ref_image_0`），policy 仍 78、源码零改动，seed 923010907 已实机三窗：眼镜回来、脸变年轻、invented 猫耳帽消失，但逐窗衣柜忠实度仍未修；2026-10-29 晚间第十二次更新，新增 §41＝policy 78→79，`plate_wardrobe_silent_clause` 不再被 prompt 长度守卫牺牲（源码已修复、视频未实机）；2026-10-30 第十三～十四次更新，新增 §42–§51＝policy 79→80→81→82 与实机两枪（82 出厂对齐用户认可的「手动 ComfyUI 图」：干净 plate＋保留音轨＋Relay 18 帧接力＋LoRA clamp 1.5；seed 923011107 0.5 MP 五项全部生效、seed 923011207 **1.0 MP 本专案首发单发 QC 全绿**）；2026-10-30 第十五次更新，新增 §52＝policy 82→83（silent 硬闸 12 % 容差改 advisory＋衣柜 floor 相对增益＋GARMENT SILHOUETTE 独立可丢弃条款＋参考上采倍率 env；**源码已修复＋981 项测试通过、影片未实机**）；2026-10-30 第十六次更新，新增 §53＝policy 83→84（crop lock 触发条件改读 plate 而非 box＋prepare bucket 地板垫到 1.0 MP；**源码已修复＋1004 项测试通过、影片未实机**）；2026-11-01 第十七次更新，新增 §56–§61＝policy 84→85→86 与实机三枪（§56 R54 源片残留造型归属条款；§57 R55 headless 重拼工具，零产品码；§58 R56 policy 85 实机一枪、导演「完美」但残留老人化；§59 R57 圆眼镜＋年龄锁 85→86；§60 R58 逐帧 A/B 读片，零产品码；§61 R59 参考图上采节点加 env 旋钮＋identity sheet 脸面板真实画素进 manifest；模块级合计 220 项测试通过；**policy 86 已实机一枪但导演尚未分级、老人化仍未解决**）
工作区：`D:\minimax h3\minimax h3 reference r2v`（2026-10-24 起；旧机 OneDrive 路径已弃用，代码曾整体自另一架电脑替换）  
应用版本：`0.3.8-alpha.3`（2026-10-21 发布；见 VERSION）  
Project Format：`29`  
当前源码 Render Policy：`86`（`SMART_RENDER_POLICY_VERSION`，`director_cut_studio.py` 911 行与 `smart_render_worker.py` 266 行两处必须同步；历史 42→43 Relay V2→44 主 H3 API→45 代码替换后现状→…→57 条款压缩／预算 12 320→58 遮罩羽化→59 遮罩＋sheet 配重进指纹（engine v5）→60 close-up 衣柜面板改用 `uhip`（§20）→61（§23，engine v6）→62（§23）→63（§26，engine 6→7）→64（§27）→65（§28）→66（§29）→67（§30）→68（round 29 fullfig sheet＋head 扩带；**68 这个号在 Round 26 回滚与 Round 29 都被提到**，已用两份 manifest 核实，见 §32 文档回填）→69（§31 衣柜带长到脚）→70 Identity Sheet 单图直通＋衣柜位移闸门（§34–§35）→…→74 官方模板五句正面改写（§37f–§37h）→75 silent plate 嘴带时域冻结＋QC 改读 plate（§37k）→76 去语音化措辞（**已实机 A/B，测出零增益**）→77 重试排名加入 silent articulation 扣分（已实机、用户接受，§37l–§37p）→**78 fullfig 单图路由（源图 <0.35 MP 不再单图直通，已实机三窗，§38–38b）**→**79 silent 衣柜段落改为不可丢弃（源码已修复、视频未实机，§41）**→80 衣柜线索加验「尾端窗」、重试选片改两窗较好者（§42，源码已修复、影片未实机）→81 medium-silent plate 出厂关掉「衣着带」（§43）→82 出厂对齐用户认可的「手动 ComfyUI 图」：干净 plate＋保留音轨＋Relay 18 帧接力＋LoRA clamp 1.5（§49–§51，**已实机、单发 QC 全绿**）→**83 silent 硬闸 12 % 容差改 advisory＋衣柜 floor 相对增益＋GARMENT SILHOUETTE 独立可丢弃条款＋参考上采倍率 env（源码已修复＋981 项测试通过、影片未实机，§52）**）→**84 读 plate 决定 crop lock＋prepare bucket 地板 1.0 MP（源码已修复＋1004 项测试通过、影片未实机，§53）**）→**85 路线 1 补回「源片残留造型属于被擦掉的演员」＋R55 headless 重拼已存 Job（§56–§57，源码已修复＋14 项测试通过；85 已实机一枪、导演分级「完美」但残留老人化，§58）**）→**86 圆眼镜条款＋年龄锁重写（§59，源码已修复＋17 项测试通过；已实机一枪、导演未分级，逐帧 A/B 读片见 §60；参考图上采 quality/strength 改 env＋脸面板真实画素进 manifest 见 §61）**）
当前 Identity Sheet 引擎：`8`（`IDENTITY_SHEET_ENGINE_VERSION`，`character_identity_sheet.py:62`，写进 sheet 档名；改面板几何必须递增。历史 4→5（§20）→6（§23）→7 head-run 脸面板填满格子（§26）→**8 新增 `OUTFIT_VIEW_*="full"` 全身衣柜视图**，见 CHANGELOG Round 29／30）  
Identity Sheet 引擎：4→5 的改动与实机结论见 §20；提示词预算 `CHARACTER_SWAP_PROMPT_CHAR_BUDGET = 12320`（天花板 12 326）。  
Identity Sheet 引擎 6→7→8 的改动与实机结论分别见 §26 与 CHANGELOG Round 29／30；本轮（§35）另加「单图直通」，P1 这类原图够大的参考可以**跳过 sheet** 直接上传。  

> 这份文件是给下一段 DSH 对话使用的开发上下文。它区分了“已经写入源码并通过自动测试”和“仍需用 ComfyUI 实际重生验证”的内容。不要把尚未重新生成的视频效果写成已完成。

## 1. Studio 是什么

MiniMax H3 Director Cut Studio 是一个 Windows/PySide6 本地导演与剪辑工作台，交互逻辑接近 Premiere：

- Media Pool：图片、视频、音频素材，使用 `@P1…`、`@V1…`、`@A1…` 等引用；
- Design：由 Qwen3.8 分析需求与 V1，生成结构化 Director Design JSON；
- Timeline：Shot、Dialogue、Marker、Text Layer、音频与生成区间；
- Shot Visual Editor：逐 Shot 修改人物、镜头、动作、环境、发声状态、对嘴与 Character Swap；
- Ask Qwen：在 Design 或 Timeline/Shot 内生成可审阅的结构化修改；
- Smart Render：预览、Dirty Segment 重生、Accept 1.0、Run + Queue、断点与缓存复用；
- ComfyUI：通过 API 提交 MiniMax H3 Ref2VA、Character Swap Relay、SAM3.1 等工作流；
- 附加服务器：SoulX Singer、Audio Separator/Kim_Vocal_2、ACE-Step、Qwen TTS、VoxCPM。

启动入口：

```powershell
.\run_h3_prompt_studio.bat
```

应用主要入口是 `h3_prompt_studio.py`，Studio 主 UI 与绝大部分编排逻辑在 `director_cut_studio.py`。

## 2. 当前外部服务和模型

常用服务：

- ComfyUI：`http://192.168.0.185:8189`
- LM Studio / Qwen3.8 OpenAI-compatible API：`http://192.168.0.185:1234/v1`
- Qwen 模型：`qwen3.8-uncensored-nvfp4-mtp`

Source Video Cast Remake / Character Swap：

- Workflow：`H3-Character-Swap-Relay-V2-api.json`（2026-10-20起取代旧`akatz-labs-character-swap-turbo8-adaptive-window-api.json`）
- H3 Relay：<https://github.com/akatz-ai/h3-relay>
- LoRA：<https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA>
- Character Swap LoRA：`h3_character_swap_v1.5.safetensors`
- Turbo LoRA：`minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`
- SAM3.1：`sam3.1_multiplex_fp16.safetensors`
- V2必需节点包括 `H3RelayPrepareSource`、`H3RelayWindowPlan`、原生Loop/History/Append/Finish节点、`SAM3_VideoTrack`、`SAM3_TrackToMask`。

用户要求：每次进行真实 ComfyUI 验证并完成后，一定执行 `/free` / unload all model，释放模型与 VRAM。

## 3. 关键源码地图

| 文件 | 责任 |
|---|---|
| `director_cut_studio.py` | 主 UI、Design/Timeline/Shot Visual Editor、项目载入保存、生成任务编译、Dirty/Accept/Queue |
| `source_video_analysis.py` | V1 全片与逐 Shot Qwen 角色/场景分析、schema normalize/parse |
| `design_ai_service.py` / `design_engine.py` | Qwen Design 请求与结构化 Director JSON |
| `character_swap_engine.py` | Character Swap pass、prompt、Relay workflow 编译 |
| `smart_render_worker.py` | Smart Render、ComfyUI 排队/下载、重试、QC、SAM3.1 合成、最终 assembly |
| `comfy_submit_worker.py` | ComfyUI API 提交与连接处理 |
| `project_storage.py` / `project_workspace.py` | `.h3director.json` 与 workspace 保存结构 |
| `prompt_engine.py` / `workflow_engine.py` | 普通 H3 prompt 和 workflow 编译 |
| `media_semantic_enrichment.py` | 素材语义分析服务 |
| `audio_engine.py` / `native_audio_engine.py` | 音频轨道、Native H3 声音、对白/环境声编排 |
| `audio_separator_*` | Kim_Vocal_2 音乐/人声分离的本地/远端服务器模式 |
| `comfyui_director_h3_cache_status/` | ComfyUI Cache/VRAM/DRAM/GPU/CPU 只读状态 API |

测试集中在（2026-10-24 起全部位于 `testing\`，每个文件顶部自带 sys.path bootstrap）：

- `testing\test_character_swap_engine.py`
- `testing\test_smart_render_worker.py`
- `testing\test_director_timeline.py`
- `testing\test_source_video_analysis.py`
- 其他 `testing\test_*.py`（共 49 个）

## 4. Source Video Cast Remake H3 的目标工作流

最少素材是 `@V1 + @P1`，不再强制 P1–P4 全部存在。额外 P 图是可选角色容量。

1. 用户把原始参考视频放入 `@V1`，人物图放入 `@P1…`。
2. 选择 Special Skill：`Source Video Cast Remake H3`。
3. `CREATE DIRECTOR DESIGN JSON` 启动 Qwen3.8，分析完整 V1 的场景、人物、动作、声音、镜头与时间。
4. Design 页面显示 V1 principal role/appearance cards；每一个时间卡独立可编辑，默认同一人物可继承同一 P，但不会锁定同步。
5. `V1 DEFAULT` 在运行层代表 `KEEP V1`：默认自动关闭该行 `SWAP`，不提交 Character Swap pass，只保护该人物不被其他 pass 改写。用户仍可手动重新打开。
6. Apply 到 H3 Workspace 后，Shot/Segment 使用 V1 的精确 24fps 时间和原声；普通 H3 reference loader 不应把 V1 当一般参考视频。
7. Remake Engine 当前可自由选择：
   - `Create H3 Remake`
   - `LoRA Preserve V1`
   - `LoRA + Reshape Environment`
8. Special Skill 只提供推荐值，不再永久锁死引擎。`Source Video Cast Remake H3`推荐 `LoRA Preserve V1`。
9. Character Swap 每个目标人物从同一份干净 V1 plate 独立生成；多人物最终用遮罩合成，避免后一个 pass 抹掉前一个结果。
10. 多人物合成使用 `V1 Mask ∪ Generated Character Mask`，原 V1 mask 用来消除旧人物，新生成 mask 用来容纳新发型、服装、四肢和体型。
11. 对话 Shot 使用明确 `lip_sync_mode`、`lip_sync_target=@P…`、`lip_sync_source=V1`；听众 Shot 应设 `disabled`，禁止跟着声音动嘴。
12. 最终 master 恢复 V1 原始 soundtrack；不允许提示词被 H3 当对白或旁白念出。

### Detect V1 People

- Shot Visual Editor 内的 `DETECT V1 PEOPLE` 使用 Qwen 逐帧扫描，不使用 YOLO。
- 扫描当前 Shot 的 24fps V1 relay frames，分批让 Qwen 找出短暂出现或多人同框的角色。
- 检测结果保存角色 ID、时间、frame index、bbox/track samples。
- 用户可点击 Current Role，加载该角色的代表帧和框；可 `Ctrl+click` 添加框、拖动/缩放框。
- 点击 Current Role 时，对应框提升到最高 z-level；框填充应半透明。
- 保存 Shot 后，Shot-local binding/bbox/identity overlay 必须优先于旧 Design ledger，并用于下一次 `REGENERATE DIRTY` 与 `RUN + QUEUE`。

## 5. Smart Render 与 Dirty Segment 规则

- Preview 的目标分辨率是 `0.2MP / 448×448` 级别；正式输出为 1.0MP 路径。
- 用户保存 Shot 后，不应强迫整片重生，只标记关联的 Dirty Segment。
- 从已保存且已有 preview/full output 的 Project 重新打开后，也应只重做被修改的 Shot/Segment。
- Apply 后直接 Run + Queue 完成 1.0 时，应建立可复用的接受状态；之后修改单 Shot，只出现对应 `REGENERATE DIRTY`。
- `REGENERATE DIRTY`、Preview、Accept、Run + Queue 是否先 unload model 由 Settings 的 `Unload all model` 开关决定。
- 一个 Smart Render Job 内 H3 模型应常驻；普通 Segment 完成后不执行 `/free`。
- 对嘴 QC 自动重生只更新 prompt/seed 后重交，不卸载 H3。
- 只有真正 CUDA OOM 才允许中途内存清理。
- 全部 Segment 拼接完成后统一执行一次 `/free`。
- `error=1450 / HostBuffer.read_file_slice failed` 必须单独识别，不得当普通失败反复卸载重载。

## 6. 当前重点项目

项目目录：

```text
example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_8
```

项目文件：

```text
example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_8\project\director_project.h3director.json
```

当前记录：

- Project Format：29
- 保存时应用版本：0.3.8-alpha.2
- Remake mode：`adaptive_character_swap`
- Skill：`source-video-cast-remake-h3`
- Illustrated cast → live-action adaptation：开启
- Timeline：约 22.61 秒
- ComfyUI：`http://192.168.0.185:8189`
- 当前所有十个 Segment 都因最新 Render Policy/修复被标记 Dirty；`S3`还在 isolated Shot 列表。

当前全局角色 ledger 的主要绑定：

- R1 → P1：Scenes 1, 2, 3, 5, 7, 8, 9, 10
- R2 → P3：Scenes 4, 6
- Scene 5/7 还有 R2 → P1 的记录
- S8 已改为 `lip_sync_target=P1`，而不是之前错误的 P3。

用户对上一版生成结果的逐 Shot评价：

| Shot | 用户观察 |
|---|---|
| S1 | R1 脸很大，P1 像直接贴脸，没有融入身体/画面 |
| S2 | 完美，可作为正向基准 |
| S3 | 错误生成 R3/选错源角色，替换失败 |
| S4 | 完美，可作为正向基准 |
| S5 | R1 脸很大，P1 未融合，替换失败 |
| S6 | R2 脸很大，P3 像直接贴脸 |
| S7 | 完美，可作为正向基准 |
| S8 | R1 应换 P1，却错误用了 P3；项目绑定现已修正为 P1 |
| S9 | R1 脸很大，P1 未融合，替换失败 |
| S10 | R1 脸很大，P1 像直接贴脸 |

> **2026-10-24 更新**：活跃项目已切换为 `_9`（用户更新的视频与参考图；2026-10-22 起全部实机验证在 _9 进行，master 输出位于 `_9\cache\generated_outputs\preview\<seed>\master.mp4`）。_8 保留原始 ledger 与旧渲染作历史基准。_9 逐 Shot 现状见 §14。

## 7. 针对上述问题，源码已经加入但尚待实机重生验证的修复

> **本节写于 2026-10-19（Render Policy 44），已过时。** 2026-10-25/26 的最新源码状态、根因取证与实机边界见 **§19**；当前 `SMART_RENDER_POLICY_VERSION = 57`，app `0.3.8-alpha.3`，Project Format 29。

以下内容已在源码中，但用户还没有拿最新源码把目标项目完整重生并确认最终画面：

1. **完整角色设计图输入**  
   卡通/插画 P Picture 不再先裁成脸部小图送进 H3。Character Swap 会把完整设计图当 identity/design sheet，让 H3重建头、颈、肩、身体、服装与四肢。

2. **禁止贴脸式 prompt**  
   `character_swap_engine.py` 已明确要求：以 V1 身体几何、镜头距离、头身比例和遮挡为准；禁止放大 P 图脸、禁止贴原图像素、禁止保留旧演员头发/衣领/身体。

3. **异常大框过滤**  
   近乎占满整帧的角色 bbox 不再被当可靠人物框，避免 H3 把整幅 P 图塞进整屏角色框。

4. **Source plate drift QC**  
   检查非目标背景/构图锚点。如果结果跳到错误 Shot、错误角色或完全改造场景，判为 drift，使用 fresh seed 自动重试，而不是接受。

5. **Strict temporal coverage**  
   对长 Shot/Relay windows 检查完整时间范围，不再只抽少量中间帧，让“开头有效、后半段没替换”误判通过。

6. **Whole-character integration audit**  
   不只比较脸部相似度；会检查头颈、肩膀、上身与服装是否形成一个完整人物。如果只是脸贴片或大头像，触发 fresh-seed retry。

7. **长 Relay Shot 平衡**  
   超过单一 Relay window 的 Shot 会按 window 建立平衡任务，同时仍保持 Shot 作为同一个渲染单元和正确时间覆盖。

8. **Render Policy 迁移**  
   2026-10-19的QC/编译修复升至42；2026-10-20接入Relay V2再升至43。旧缓存会失效，使受新规则影响的Segment重新生成。

注意：`VERSION`仍是 `0.3.8-alpha.2`；2026-10-20切换Relay V2后Render Policy先升至43，随后主H3 9-Image／3-Audio／3-Video API更新再升至44，确保两类旧缓存都不会被复用。这批更新记录在CHANGELOG的Unreleased区，尚未另升应用版本。

## 8. 已完成的自动验证

2026-10-19 在本工作区运行：

```powershell
.\ai_libraries_common\python_env\python.exe -m unittest discover -s testing -p "test_character_swap_engine.py" -v
.\ai_libraries_common\python_env\python.exe -m unittest discover -s testing -p "test_smart_render_worker.py" -v
.\ai_libraries_common\python_env\python.exe testing\test_director_timeline.py DirectorTimelineDragTests.test_character_swap_relay_keeps_every_source_shot_as_one_render_unit DirectorTimelineDragTests.test_character_swap_balances_a_shot_that_exceeds_one_relay_window

# 或一次跑完整套（testing\ 下全部 49 个测试文件）
.\ai_libraries_common\python_env\python.exe -m unittest discover -s testing -v
```

原交接时结果为`Ran 52 tests ... OK`；2026-10-20接入Relay V2后，相关测试增至`Ran 53 tests ... OK`。

编译检查：

```powershell
.\ai_libraries_common\python_env\python.exe -m py_compile director_cut_studio.py character_swap_engine.py smart_render_worker.py source_video_analysis.py
```

结果：通过，无 Python syntax error。

测试结束时出现 Audio Separator stop 的 Windows CIM 权限警告，但不影响 52 项测试通过；这是测试沙箱无法访问 CIM，不是 Character Swap 测试失败。

## 9. 下一位开发者的优先任务

1. 先重新启动 Studio 或重新载入项目，使内存中的旧 Project/代码状态失效。
2. 打开 `a_cartoon_character_with_a_mustache_and_a_yellow_shirt_8`。
3. 确认 S8 仍是 R1 → P1，且 `lip_sync_target=P1`。
4. 检查 S3 当前 Current Role 与框；不要允许旧的近全屏 bbox 或错误 R3 进入生成。
5. 先小范围生成 S1、S3、S5、S6、S8、S9、S10，比较 S2/S4/S7 的成功画面。
6. 重点核验：
   - 是否仍出现 P 图大脸直接贴入；
   - 新人物的头身比例、衣服、手臂是否完整；
   - V1 旧演员是否有残影；
   - 多人同框是否互盖或串脸；
   - 长 Shot 后半段是否停止换角；
   - S3 是否仍跳到错误人物/错误 Shot；
   - S8 是否真正使用 P1。
7. 若 QC 自动重试，记录每次 seed、失败原因、window、pass 和 ComfyUI prompt ID，避免“重复处理”无法追踪。
8. 全部实机验证结束后执行 ComfyUI `/free`。
9. 若实机效果通过，再决定是否升级 `0.3.8-alpha.3`，同步 `VERSION`、`README.md`、`CHANGELOG.md` 与 `v0.3.8 readme.md`。

## 10. 已知风险与不要误改的规则

- 工作区非常 dirty，含大量用户项目、生成物、未追踪文件和长期开发修改。**禁止 `git reset --hard`、`git checkout --` 或清理整个工作区。**
- 不要删除 `example/` 下用户项目，也不要把 generated videos/cache 全部纳入 Git。
- 使用项目内 bundled Python，不要假设系统 Python 依赖完整。
- 真实网络/ComfyUI 测试完成后必须 unload all model。
- 不要把 Character Swap 的正常 Relay windows 显示成多个重复 Job；状态格式应类似 `Segment S3 · Role R2 · Pass 1/2 · Window 2/3`。
- `KEEP V1` 默认零 pass；只加入非目标人物保护名单。
- 不同 P Picture 的必要角色 pass 可串行；相同 P Picture 可合并；多角色最终只组装一次 Shot 画面。
- 用户不希望 QC Hard Block 后停止整个 Job。应自动调整/重试，只有无法安全继续时才明确报告。
- 对嘴时间源：当前一般规则是 A2 非空则只以 A2 为嘴形时间源；A2 为空则只以 A1 为嘴形时间源。Source Video Cast Remake 例外地以 V1 soundtrack/ledger 为 source。
- 提示词不得隐藏对白或旁白。若人声通道为空，不应凭 prompt 自创对白/旁白。
- `skill special\source-video-cast-remake-h3\SKILL.md` 的部分旧说明仍写 Remake Engine“automatic and read-only”，也仍描述旧串行前一 pass 输出作为下一 pass source；这与 v0.3.8 的可选引擎和独立干净 V1 多角色合成已不完全一致。后续应修正文档，但修改前先以当前代码、README 和最新用户要求为准。

## 11. 相关文档

- `README.md`
- `CHANGELOG.md`
- `v0.3.8 readme.md`
- `step1.md` 至 `step4.md`
- `skill special\source-video-cast-remake-h3\SKILL.md`
- `skill special\source-video-cast-remake-h3\SKILL.cn.md`
- `forum\Source_Video_Cast_Remake_H3_Step_by_Step.md`
- `forum\MiniMax_H3_Character_Swap_LoRA_Auto_Remake_Engine.md`

## 12. 可直接复制给 DSH 的继续开发提示词

> 2026-10-21 更新：本节旧的“完成后执行 /free”单条规则已替换为 staged model driver ＋三条硬约束；版本号同步至 0.3.8-alpha.3，路径改为当前工作区。
> 2026-10-21 二次更新（下午）：补入 tray 状态翻转气球通知、LM Studio 自动重载竞态证据（main.log）与 tensor split 发现；详见 §13。
> 2026-10-21 三次更新（晚间）：tray 从观察者升级为执行者——auto_load_qwen_when_free 在 GPU 空闲 ~20s 且 ComfyUI 队列空时自动 start Qwen；并记录 instance-ID vs catalog-key 400 坑与 MessageBox 加固，详见 §13。
> 2026-10-22 四次更新（深夜）：Codex daemon eviction 假设 + config.toml 修复（u64 解析坑）+ keep-alive ping 接入 tray + Resolve-CodexCli bug 修复；详见 §13。
> 2026-10-24 五次更新：代码自另一架电脑整体替换（此前本地改动丢失后逐项重做）；卡通媒介保留修复（_9 项目 live-action flag 关闭）；working/ & testing/ 布局变更；活跃项目切换为 _9；Render Policy 45。详见 §14。

```text
请继续开发这个本地项目：
D:\minimax h3\minimax h3 reference r2v

第一步请完整阅读：
D:\minimax h3\minimax h3 reference r2v\DSH_STUDIO_HANDOFF_2026-10-19.md

当前应用版本是 0.3.8-alpha.3（见 VERSION），Project Format 29，Smart Render Policy 45。不要从头重写，不要重置或清理 dirty worktree，不要删除用户 example 项目；使用项目内 bundled Python（.\ai_libraries_common\python_env\python.exe）。先检查现有源码和目标项目（活跃为 _9；_8 保留原始 ledger 作历史基准）：
example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9
example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_8

待实机验证项（若已完成，以 CHANGELOG.md 最新状态为准）：Character Swap 修复——S1/S5/S6/S9/S10 的大脸贴片与全身融合、S3 的错误源角色/错误 Shot、S8 错误 P3（现应为 P1），并以 S2/S4/S7 作为成功基准；另外 Unreleased 中的 9-Image/3-Audio/3-Video H3 API 与 Character Swap Relay V2 改动同样待实机验证。

【GPU 操作流程】所有涉及 Qwen3.8（Design／AI Enrich）与 ComfyUI（H3 生成／实机验证）的步骤，统一走工作区根目录的 staged_model_driver.py 分阶段驱动，遵守三条硬约束：
1. Python 分阶段驱动——不要在一个长进程里同时持有两个模型，也不要绕过 driver 裸调 LM Studio／ComfyUI API。完整 H3 任务优先一条命令跑完：python staged_model_driver.py run "example\...\xxx.job.json"（内置管线 unload-qwen → wait-comfy → smart_render_worker → /free → report，Qwen 未干净即提前中止）。非 Smart Render Job 的测试手动分阶段：status → unload-qwen → wait-comfy --timeout 900 → 跑你的 ComfyUI 任务 → free。
2. ComfyUI 与 Qwen3.8 不同步加载——任何时刻显存里只能有一个：Design／AI Enrich 阶段 Qwen 常驻（agent 侧），H3 生成／验证阶段 ComfyUI 常驻。切换必须经 unload-qwen（等 verified_clean）→ wait-comfy；任务结束 /free 释放 ComfyUI 后，回到 Design 前先 load-qwen 把 Qwen 载回来并验证。关键坑：LM Studio 聊天页会在 API 卸载后数秒到数分钟内自动重载模型（竞态，main.log 已证实：2026-10-21 三次重载 14:12/14:30/14:46 均发生在空卡上），所以载回 Qwen 必须用 load-qwen 显式 start 并验证（轮询 /api/v1/models 直到 verified_loaded）——不要假设“发过请求就算加载了”，也不要只 list models 等它自己回来。
3. 每次测完 /free——ComfyUI 阶段结束后无论成功失败都执行 free（unload_models + free_memory）；driver 会校验 VRAM 实际下降后才报告 manifest。例外：单个 Smart Render Job 内部 H3 模型常驻、Segment 之间不 /free，全部拼接完成后统一一次——run 的内置行为已如此，不要额外插入。

Tray 仲裁者已在运行（ai_libraries_common\director_studio_h3_status_tray\，用其自带 bat 从该目录启动）：tooltip 显示 "QWEN loaded (agent owns GPU)" 或 "GPU free for H3"；owner 状态翻转（Qwen loaded ↔ unloaded）会在屏幕右下角弹气球通知（"Qwen unloaded - GPU free for H3" / "Qwen loaded - agent owns GPU"），不用悬停图标就能看到变化，菜单手动 load/unload/free 同样触发。拿不准当前状态时先看 tray（或等气球），再跑 status。模型名 driver 自动从 design_ai.env 的 H3_DESIGN_LM_STUDIO_MODEL 解析（可用环境变量 H3_STAGE_QWEN_LOAD_MODEL 覆盖）；ComfyUI／LM Studio 地址同理有 env override（H3_COMFYUI_URL / H3_LM_STUDIO_ORIGIN）。Tray 现在是执行者而非只读观察者：auto_load_qwen_when_free=true（默认开，菜单可切换）时，owner=FREE 且 ComfyUI 队列空闲持续 ~20s，tray 自动 POST LM Studio chat completion 把 Qwen start 回来并弹气球——agent 侧不会再卡在 "model unloaded"；菜单手动 Unload Qwen 有 120s 宽限不自动载回。关键坑：tray-settings.json 的 qwen_model（及 design_ai.env）必须填 LM Studio catalog key（qwen3.8-uncensored-mtp），不能填 loaded instance ID（如 qwen3.8-uncensored-nvfp4-mtp）——空卡时按 instance ID 发请求会直接 400 "No models loaded"，按 key 发才会触发 on-demand load。2026-10-21 晚间起 tray 又经 claim 文件 + 反向 auto-unload 仲裁（详见 §13「Claim protocol」），Studio pre-generation unload / job-end /free 已接入该协议。

每次修改后运行相关 unittest 与 py_compile，并明确区分“源码已修复”和“视频已实机验证”。
```

## 13. GPU 仲裁与模型生命周期（2026-10-21 增补）

### Tray v2：双源仲裁 + 状态翻转气球

- 位置 `ai_libraries_common\director_studio_h3_status_tray\`（用户从该目录用自带 bat 启动，勿再移动）。
- 每 5 秒轮询 ComfyUI status API（:8189）与 LM Studio `/api/v1/models`（:1234），判定 GPU owner：Qwen 实例已加载 → "agent owns GPU"；否则 → "GPU free for H3"。
- **新增（下午）**：owner 状态翻转时屏幕右下角弹气球通知（`Notify-OwnerChange`）：`Qwen unloaded - GPU free for H3` / `Qwen loaded - agent owns GPU (H3 needs unload-qwen first)`。不用悬停图标就能看到状态变化；菜单手动 load/unload/free 同样触发。
- 图标规则：QWEN 常驻且 VRAM≥80% → 黄 Warning；整体 ≥95% 或 cache ≥90GB → 红 Error；其余蓝 Information。

### Tray v2.5：auto-load enforcer（auto_load_qwen_when_free，2026-10-21 晚间）

- 背景症状：unload → ComfyUI run → /free 之后 Qwen 有时永远停在 unloaded，agent 侧只显示 "model unloaded"，必须人手点加载；聊天页自动重载竞态不可靠（有时它不回来）。
- 机制（h3_status_tray.ps1，Update-H3TrayStatus 每 tick）：owner=FREE（确认或 catalog 查询失败均算）且 ComfyUI `/api/queue` 空闲，持续 ~20s → POST LM Studio `/v1/chat/completions`（model=$config.qwen_model，"reply with the single word ok"，max_tokens=6，TimeoutSec 90）显式 start Qwen；成功弹气球 "GPU free ~20s + queue empty -> tray auto-loaded Qwen"，失败弹 "auto-load failed"。
- 设置：tray-settings.json `auto_load_qwen_when_free`（默认 true），菜单项可切换并持久化；关闭时 enforcer 不计时。owner=QWEN／队列忙／宽限期内 → 计时窗口重置；autoLoadInFlight 防重入。
- 宽限：菜单手动 Unload Qwen → 120s 内不自动载回（suppressAutoLoadUntil）；driver 的 unload-qwen 无宽限，~20s 后会被自动载回（预期——agent 需要 Qwen）。
- 实机验证（2026-10-21 18:11）：driver unload-qwen 18:11:14 → tray 18:11:31 FIRED → 18:11:50 LOADED OK，owner=QWEN；当晚清理临时调试日志后重启 tray（新 PID），/free 复测通过。
- MessageBox 加固：全部 [System.Windows.Forms.MessageBox]::Show 调用收拢到 Show-H3MessageBox（内部 try/catch），修掉偶发 "Cannot find an overload for 'Show' and the argument count: 4" 弹窗中断 tray 的问题。

### Claim protocol + reverse arbiter + Studio integration（2026-10-21 晚间）

- 症状：unload → ComfyUI run → /free 之后 Qwen 有时永远停在 unloaded；反之，"unload-qwen" 与 "ComfyUI 实际入队列" 之间的 gap 里 tray ~20s 窗口提前开火先载 Qwen → 两边同时互相抢资源（LM Studio 双 prompt + ComfyUI 同步 load H3）。
- Claim 文件协议：`ai_libraries_common\director_studio_h3_status_tray\comfy_claim.json`（{"ts","note"}，TTL 90 min，env override H3_COMFY_CLAIM_PATH）。driver 在 unload-qwen / wait-comfy 时写（note=phase），load-qwen / free 时清；--keep-qwen 写 note=keep-qwen。
- Tray 向前 enforcer：auto-load 条件变为 "owner=FREE + queue idle ~20s 且无 active claim" → H3 阶段中 Qwen 不会被提前载回。
- Tray 反向 arbiter（新）：owner=QWEN 且 ComfyUI queue busy ~15s → tray 自动 unload Qwen（弹球通知），除非 fresh claim note 为 keep*（--keep-qwen 共存场景）。菜单项文案："Auto-arbitrate Qwen vs ComfyUI (load ~20s after free, unload when H3 busy ~15s)"。
- 实机证据：19:42 driver unload → 与 20:07:46 下一次 load 之间 Qwen 保持 unloaded ~25 min（claim gating 生效）；standalone claim 计算 age_s=1797 active=True。
- Studio 接入（同晚）：之前走 Studio 执行时，每次 generation 开始 pre-generation "unload all models"、结束 /free，但都不通知 tray → 竞态。现在：director_cut_studio.py `start_design_cleanup` 在 operation=pre_generation 时写 claim（note=studio-pre-generation）；smart_render_worker.py final /free 后 clear；comfy_submit_worker.py（single-shot）退出时新增 /free + clear（成功失败都执行，之前 single-shot 根本不 /free）；`_generation_finished` 另加 stale claim 安全网无条件 clear。手动 UNLOAD ALL 按钮不写 claim（tray ~20s 后仍自动载回 Qwen，保持原行为）。
- 结果生命周期：Studio 开始 → claim（tray 不载 Qwen）→ H3 独占（含 Segment 间 gap）→ job 结束 /free → clear claim → tray ~20s 自动载回 Qwen。worker crash 时 `_generation_finished` 安全网 clear；没人 clear 时 TTL 90 min 兜底。
### staged_model_driver.py（工作区根目录）

子命令：`status` / `unload-qwen` / `load-qwen` / `wait-comfy [--timeout 900]` / `free` / `run JOB.json` / `report`。模型名解析顺序：环境变量 → design_ai.env 的 H3_DESIGN_LM_STUDIO_MODEL → 默认 qwen3.8-uncensored-mtp；ComfyUI／LM Studio 地址同理有 env override（H3_COMFYUI_URL / H3_LM_STUDIO_ORIGIN）。自测 16/16 通过。
- Claim 协议接口：`status` 额外报告 comfy_claim（none/active/stale + age）；write_comfy_claim(note) / clear_comfy_claim() / comfy_claim_path() 可被同目录其他模块 import（director_cut_studio.py 与两个 worker 直接调用，见上节 Claim protocol）。

### LM Studio 自动重载竞态与 tensor split（main.log 证据）

- 取证来源：`C:\Users\daniel\AppData\Roaming\LM Studio\logs\main.log`。每次模型加载都会记录当时的 "Live GPU memory info"，可还原当时谁占着卡。
- 竞态证据（2026-10-21）：三次 API 卸载后聊天页都在数秒到数分钟内自动重载（14:12/14:30/14:46），且当时 GPU 均为空卡 → **unload 之后不要假设它保持 unloaded；载回必须 load-qwen 显式 start 并验证**。
- tensor split 发现：Qwen 的 172K context 配置使模型本体（21.24GB）＋ KV cache（12.98GB）＝34.22GB ≈ 整卡（34.21GB），所以 LM Studio 永远做 tensor split（约 74% 层在 VRAM、26% 在 CPU 内存）。含义：tray 显示 "QWEN loaded vram=95%" 时实际并未占满整卡，ComfyUI 有时可共存（日志有 GPU 已被占 17GB 时的加载事件）；但按约束仍以最稳的分阶段独占为准。
- **instance-ID vs catalog-key（2026-10-21 晚间，server DEBUG log 证据）**：空卡时按 loaded instance ID（如 qwen3.8-uncensored-nvfp4-mtp）发 chat completion → LM Studio 直接 400 "No models loaded"（不 on-demand load）；按 catalog key（qwen3.8-uncensored-mtp）发才会触发 on-demand load（~19s）。所以 tray-settings.json 的 qwen_model 与 design_ai.env 的 H3_DESIGN_LM_STUDIO_MODEL 一律填 key，不要填 instance ID。
- H3 实验参考跑法（2026-10-21）：`H3-Character-Swap-Relay-V2-api.json` 原地改 source video＋prompt → POST /prompt → 124 帧单窗口/8 steps，含模型加载共 ~255s；输出 928×512（workflow resolution=480 设定）、音轨保留；ComfyUI run 结束自动释放（随后 /free freed 0.0GB）。

### Dead-thread auto-wake：active_run.json + codex queue（2026-10-21 深夜）

- 症状与根因：driver `run` 中途崩溃——worker 成功后会 unlink job 文件，而旧代码 `read_manifest(job_file)` 又重读该文件 → pathlib FileNotFoundError（截图 traceback 即此）；此时 Qwen 早在 run 开头被 unload，agent 下一个 LLM 调用撞上 "No models loaded" → thread 死掉。tray 稍后自动载回 Qwen 也没人给死掉的 thread 发消息，必须人手敲"继续"。
- driver 根因修复：`read_manifest(job_file, job=None)`——run 路径直接传已解析的 dict，不再重读文件；job 文件一开始就读不到 → 干净 JSON `run-aborted` + exit 2（不再是 traceback）。
- 注册协议：driver `run` 启动即在 tray 目录写 `active_run.json`（{"ts","status":"running|crashed|resumed","thread_id","job"}；thread_id 取自 $env:CODEX_THREAD_ID，env override H3_ACTIVE_RUN_PATH）。意外异常 → status=crashed + exit 3（emit run-crashed）；成功 → 删文件。
- happy path：`run` 在 /free 之后、返回之前等 tray forward-enforcer 把 Qwen 载回（wait_qwen_reloaded 轮询 catalog，~90s 超时）→ agent 下一个 LLM 调用不再撞 "No models loaded"（21:30 S9 那次成功跑缺的就是这一步）。
- tray auto-wake（h3_status_tray.ps1 `Invoke-AutoResume`，每 tick ~5s）：active_run.json status=crashed（或 running 但 >2h stale 视为 crashed）且 Qwen 确认已加载 → `codex.exe queue --thread <id> --message "Tray auto-resume: ..."` 自动把 continue 消息发回该 thread；成功改文件为 resumed（防双发），失败保持 crashed 下 tick 重试。codex.exe 解析顺序：PATH → %LOCALAPPDATA%\OpenAI\Codex\bin\* 最新版本目录。
- 端到端验证（2026-10-21 深夜）：直接 CLI queue exit 0；写入假 crashed registry 后，运行中的 tray 一个 tick 内自动发出并把文件改为 resumed。tray 已用新代码重启（新 PID）。

### Codex daemon eviction 假设 + config 修复 + keep-alive ping（2026-10-22 深夜）

- 症状：Qwen 反复"被强制 unload"，tray/driver 都解释不了 → 用户新假设：Codex CLI/app-server 的 background daemon（≥0.157）会激进卸载不活跃 thread 的模型/上下文以省内存——之前从未碰过这一层。
- config 修复（~/.codex/config.toml 顶层，已验证 TOML 可解析）：`thread_unload_delay_secs = 999999999`（~31 年 ≈ 永不卸载）。**坑**：用户原方案是 `-1`，但本机 build（0.155.0-alpha.9.2）把该 key 解析为 **u64** → `-1` 直接报 "invalid value: integer -1, expected u64"，导致**每一次 codex.exe 调用都在 config load 阶段失败**（包括 tray auto-resume 的 queue）。将来升级到接受 signed 的 build 可改回 -1。
- daemon 现状：`codex app-server daemon version` 报 socket dead network → **0.155 上 background daemon 尚未在跑**；`daemon restart` 另报 "this CLI has no complete local package"（alpha 包不完整）。即今天的诡异 unload 更可能来自其他层（LM Studio 聊天页竞态/手动操作）；config + ping 是为将来升级 ≥0.157 的预装防线。
- keep-alive ping（用户方案 #2）：`codex status --ping` 在本 build 尚不存在（clap 报 unexpected argument）。tray 新增 `Invoke-CodexKeepAlive`：启动时 probe 一次，存在则 tick loop 每 ~60s ping 一次防 daemon 进入 idle/draining；不存在则静默跳过（no-op），升级后自动生效。
- Resolve-CodexCli bug 修复（"tray 无动于衷"根因之一）：原 `Sort-Object Name -Descending | Select -First 1` 只看字典序最大的 bin 目录——本机恰好是无 codex.exe 的目录（73fd6465d9c76545，与有 exe 的 247581e40ee272fb mtime 相同）→ 返回 null → auto-resume 静默失败。改为按 mtime 降序遍历所有 bin 目录、返回第一个含 codex.exe 者。
- 旧 tray 卡死取证：PID 54240 跑 ~16h 仅 3.2s CPU，8s 窗口零增量 → 主循环已停（疑似被 modal MessageBox 阻塞）；bat 重启（新 PID）。重启 + config 修复后一个 tick 内 auto-resume 开火、active_run.json 变 resumed——**dev thread 自身 ID 首次入册**（S10 成功路径删过 registry，手动 re-arm：status=crashed + thread_id=01a15c24-…）。
- driver v2 safety net（同晚部署，py_compile 通过，未实机验证）：`run` 返回后若 wait_qwen_reloaded 超时 → emit run-note + 写 crashed + spawn detached resume-watcher（CREATE_NO_WINDOW|DETACHED_PROCESS，日志 logs/staged_model_driver/resume_wait_<stamp>.log）；新增 `resume-wait` 子命令：5s 轮询 Qwen ≤600s、复查 registry 仍为 crashed（tray 已处理则 "already handled"）、自行 codex.exe queue 并标 resumed。registry 仅在 status==running 且 thread_id 匹配当前 CODEX_THREAD_ID 时 unlink（防跨线程误删）。
- 结论：今天"无法 auto continue"= 两层叠加——① tray 主循环卡死（已重启）＋② config.toml u64 解析错误让每次 codex.exe 调用失败（已修）；修复后在 dev thread 自身上端到端验证 crashed → tray auto-queue → resumed。

### 升级后验证（2026-10-22 凌晨）

- 用户经桌面 app 内建更新升级：build 26.915.31945 → 26.1016.51333，CLI 0.155.0-alpha.9.2 → **0.163.0-alpha.11**（新 bin\6257d9e8f63c0f2b，旧目录已清）。`codex update` 本机不可用（"Could not detect the Codex installation method"，install method=other）→ **只能从 app 内升级**。
- config.toml 被 app 重写（hash 变化）：diff 显示只更新版本化路径（cua_node hash、CODEX_CLI_PATH→新 bin、APP_VERSION）＋新增 code-review plugin；**model_provider / lmstudio-local / thread_unload_delay_secs 全部保留 → Qwen 连接未断**。升级前快照 `config.toml.bak-20261022-pre-upgrade` 留作保险。
- **background daemon 真的在跑了**：升级时桌面 app 拉起 `codex.exe -c features.code_mode_host=true app-server ...`（PID 32140 @01:32）→ 0.163 上 daemon 是 app 子进程、stdio 连 app；CLI `daemon version/restart` 找的 control socket（~/.codex/app-server-control\app-server-control.sock）无人监听 → **CLI 管不到这个实例，要重启桌面 app 才会重建**。daemon 读 ~/.codex/config.toml → thread_unload_delay_secs=999999999 生效（若 0.163 尚不认该 key 则无害 no-op，将来版本自动激活）。
- `codex status --ping` 在 0.163-alpha 仍不存在 → tray keep-alive probe 继续 no-op（将来版本加入即自动生效）；daemon restart 的 "no complete local package" 是 alpha 打包问题，非致命。
- tray 单实例 Mutex 确认：ps1 有守卫——重复 bat 启动时第二个实例自动退出（今天 Start-Process 子进程即如此）。当前唯一实例 PID 80016（@00:47 用户手动重启，含全部新代码）；Qwen loaded、app-server alive。

### completed handoff + keep-alive 定义修复（2026-10-22 深夜）

- 症状：`source-video-cast-remake-h3` studio 代码测试端到端成功（master.mp4 产出、换人验证通过），但 agent thread 仍"无法 auto continue"。时间线取证：02:08 driver unload Qwen → ~02:09 本 turn LLM stream 死于 No models loaded（registry 还是 running）→ 02:14 worker done + /free → 02:15 tray 正确载回 Qwen（driver log `wait-qwen-reload ready:true`）——但 driver 成功路径在 finally 里 unlink 了 active_run.json，而 Invoke-AutoResume 只认 crashed → 没人给死掉的 thread 发消息，最后人手点继续。
- 根因①（driver）：run_job 成功路径不给 tray 留任何痕迹。修复：code==0 且 not keep_qwen 时——CODEX_THREAD_ID 有值 → `write_active_run("completed")`（即使本 turn 中途已死，tray 也能唤醒我们）；standalone run 直接 clear。finally 仍只 unlink status=running，completed/crashed 存活到 tray 标 resumed。
- 根因②（tray）：Invoke-AutoResume 只认 crashed。修复：新增识别 completed——90s grace period 后唤醒（活着的 turn 几秒内自己继续；死掉的 thread 靠这条消息被叫醒），queue 文案按状态区分（completed → "…successfully (see manifest)…only report again if the result was not already delivered"）；balloon 同样区分 crashed/completed。
- 根因③：Invoke-CodexKeepAlive 在 Update-H3TrayStatus 里每 ~60s 被调用但 ps1 从未定义 → try/catch 吞掉 CommandNotFoundException，keep-alive ping 静默 no-op（且本 build 本来就没有 status 子命令）。修复：补上定义——Start-Process `codex.exe status --ping`（5s 有界等待），失败即 no-op；将来 build 加入该子命令后自动变成真 ping。
- 重启 + 验证：杀旧 tray PID 80016，经 ai_libraries_common\director_studio_h3_status_tray\start_h3_status_tray.bat 重拉（单实例 mutex Local\MiniMaxH3DirectorServerStatusTray），新唯一实例 **PID 227984**；driver py_compile 通过、ps1 Parser::ParseFile 零语法错误。
- config.toml thread_unload_delay_secs：用户原方案 `-1`，本 build 按 u64 解析 → 谨慎改用 `999999999`（~31 年 ≈ 永不，见上一小节）。升级 0.163-alpha.11 后 background daemon 真的在跑并读该 key——但它只挡"daemon 驱逐不活跃 thread"，挡不住我们 run 中主动 unload；auto-load 靠的是上面的 completed handoff，别指望 config 单独解决。
- 注意：工作区根目录还留着一份旧 h3_status_tray.ps1（10/21 11:38 版）；运行实例用的是 ai_libraries_common\director_studio_h3_status_tray\ 这份，勿从根目录 bat 启动以免跑旧代码。

### S7 复现：worker 非零退出缺口 + CODEX_THREAD_ID 纪律（2026-10-22 午后）

- 症状：S7 测试（preview_940000301，job 在 _dsh_verify_9\round8\jobs_backup）12:21 经 staged_model_driver.py 启动，worker 立刻崩于 KeyError 'workflow'（smart_render_worker.py L4427 `deepcopy(segment["workflow"])`），本 turn 死于 No models loaded。tray 正确载回 Qwen，但 auto-resume 没开火 → 用户要求用 codex CLI 手动激活（queue message 01a161f9-… 成功入队）。
- 根因：worker 非零退出既不走异常分支也不走成功分支——run_job 只在 code==0 写 completed、只在 exception 写 crashed；非零返回时 registry 保持 running → finally unlink → tray 无迹可查（logs 目录无任何 resume_wait_*.log，证明两个 crash 分支都没走到）。修复：新增 `elif code != 0` 分支——写 crashed + spawn detached watcher（与崩溃同等待遇），worker 失败也能唤醒死 thread。
- 纪律：agent 启动 driver 前必须 export CODEX_THREAD_ID（否则 registry thread_id 为空 → tray 无唤醒目标）；本次是否导出已无法事后确认，code!=0 分支 + env 纪律两层补齐后该缺口关闭。### S7 重跑成功：builder workflow hoist 修复（2026-10-22 午后）

- 根因坐实：`_build_round8_jobs.py` 只把 per-pass workflow 写进 job、未把 pass-0 的 workflow 提升到 segment 级 → worker L4427 `deepcopy(segment["workflow"])` KeyError（round6 S9 job 有 segment-level workflow，round8 全部 8 个 job 都没有）。
- 修复：builder pass 循环后加一行 `seg["workflow"] = copy.deepcopy(seg["character_swap_passes"][0]["workflow"])`；重跑 builder 重新生成全部 8 个 job（同一 latent bug），逐一验证 segment-level workflow=True。
- 重跑（13:16，log preview_940000301..._20261022_131629.log）：完整 staged 流程——unload-qwen（vram 30.09→3.04GB）→ wait-comfy ready(1600 classes) → preflight passed → 上传 new-plate source video + P5 reference image（APP_MT 注入生效，prompt 含 NO INVENTED TEXTURE 条款）→ S7 生成 ~146s complete、identity audit 通过（target similarity 0.70 vs P5；R1+R2 complete erasure passed）→ master.mp4 assembled(705KB) + ComfyUI released → /free ok → wait-qwen-reload ready:true。
- tray completed handoff 首次实战开火：driver 写 active_run.json=completed → tray 90s grace 后唤醒本 thread 并载回 Qwen——同日上午"completed handoff + keep-alive 修复"的端到端验证（无需人手点击）。
- master 输出：example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9\cache\generated_outputs\preview\940000301\master.mp4；manifest 同目录 render_jobs 下（report 字段写的是 workspace-root 相对路径，实际落在 example project 内）。round8 其余 shot S10/S11/S5/S3/S4/S6/S8 可用同一 driver 逐个跑。

## 14. 2026-10-23 ~ 10-24 开发记录（本次增补）

> 本节记录 §13 上次更新之后的实机验证进展与源码变更；细节以 CHANGELOG.md Unreleased 区为准，此处只给结论与状态。

### 项目切换：_8 → _9

- 活跃项目为 `example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9`（用户更新的视频＋参考图）；2026-10-22 起全部实机验证走 staged_model_driver 在 _9 进行。
- 用户把 P4 原参考图移去 P1（cast 重分配）；S4 配对 P6。
- 项目级 `source_cast_live_action_adaptation`：_8=True、_9=False（见下方媒介保留修复）。

### 实机验证进展（_9，全部经 staged_model_driver）

| 项 | 状态 | 证据 |
|---|---|---|
| S7 多角色 head-band 身份抑制 | **已实机验证** | preview_970000001（2026-10-24 01:22）：`multi_role_head_band_dominant_closeup_identity_suppressed` 策略实机触发，attempts_used=2（attempt 1 QC 失败 → fresh-seed 重试），target P1 相似度 **0.476**（> floor 0.30、无 review flag）；R1/R2 head erasure、complete_actor_erasure、whole_character_integration 全过。master：`_9\cache\generated_outputs\preview\970000001\master.mp4` |
| S8 / S9 大脸角色替换 | **用户目视确认成功**（基准） | 用户确认大脸替换成功；其 prompt 写法可作为其他 Shot 参考 |
| S2 medium-silent plate 脸部模糊 | 条款＋模糊已实机生效；嘴部指标仍未过 | preview_995/996：gate 触发、模糊 plate 实际上传、SOURCE PLATE FACE BLURRED 条款嵌入一次；target-likeness 排序选中 attempt 3（相似度 0.546，历次最高）但 silent_mouth_audit 仍 violated——根因是 P1 design sheet 本身为张嘴大笑表情，H3「按 Picture 1 重建整张脸」时复刻了该表情。后备方案：为 silent pass 生成 P1 neutral-mouth 变体参考图 |
| S9 回归基准（close-up face anchoring） | 已实机验证（2026-10-22，A/B 对照） | Run-1 vs Run-2 均首次尝试通过全部 identity audit；target 相似度 0.459/0.419（Round-6 基线 ~0.179）；卡通转换提前至 ~2.0–2.5s。残留：前 ~2s V1 脸时间漂移、head_dominant 静态盒域模糊矩形 smudge |

### 源码修复（区分「源码已修复」与「视频已实机验证」）

细节见 CHANGELOG.md Unreleased 区；此处列关键项与状态：

1. **Round-8 per-shot 条款**（2026-10-22）：CLOSE-UP MEDIUM REINFORCEMENT / NO INVENTED TEXTURE OR PATTERN / EXTREME CLOSE-UP SILENT MOUTH；多角色身份抑制 v2（per-role gate 评估＋多区域模糊链，缓存 token v2）；`_closeup_gate_for_bbox` 共享助手；`choose_character_swap_identity_candidate` target-likeness 排序。
2. **Reference-Fidelity 条款**（2026-10-23）：MULTI-PERSON SUBJECT DEFINITIONS — AUTHORITATIVE（多人 pass 重定义单数 "person being replaced"）、COMPLETE WARDROBE REPLACEMENT — MANDATORY、NO INVENTED CHARACTER DETAILS — MANDATORY；medium reinforcement 扩展到整个可见角色；多角色全 dominant pass 改 head-band 30% 模糊（策略 `multi_role_head_band_dominant_closeup_identity_suppressed`，缓存 token v2→v3）；QC 新增 target-likeness review flag（floor 0.30、非阻断）。
   - 状态：单元测试通过；**S7 已实机验证**（见上表）；S4/S6/S8 wardrobe Shot 与 S1（P5 参考图自带烧录 UI 文字 confounder，建议先换干净 P5）待实机。
3. **卡通媒介保留修复**（2026-10-24）：代码自另一架电脑整体替换后发现「参考图卡通被改成真人」——根因是项目 `source_cast_live_action_adaptation=True` 时 `character_swap_engine.build_character_swap_prompt` 两处 `if live_action_adaptation:` 块附加真人化提示词。修复：_9 项目 flag 置 False（不再附加任何真人化提示词）；已验证有效的近景身份抑制方法（plate 脸部模糊）保留，CLOSE-UP MEDIUM REINFORCEMENT 条款 gate 为 `face_dominant_closeup and not live_action_adaptation`——flag 关闭时卡通媒介条款生效。
   - 状态：**源码机制在位＋项目 flag 已修；_9 上待实机验证**（确认保留卡通造型、不再真人化）。
4. **working/ & testing/ 布局变更**（2026-10-24）：约 130 个临时脚本移入 `working\`；49 个测试文件移入 `testing\`，每个顶部加 sys.path bootstrap（项目根自动入 path，任意 CWD 可直接运行或 `-m unittest discover -s testing`）；README「## 测试」与本文 §8 命令改为 discovery 形式；studio 源码无路径引用改动。
   - 验证：py_compile 49/49 通过；直接运行 `testing\test_character_swap_engine.py` 39 OK、`test_character_swap_closeup_gates.py` 12 OK、`test_smart_render_worker.py` 49 OK（skipped=1），与 CHANGELOG「39+12+49=100」一致；§8 点名的两个 relay 回归测试直接运行通过。
   - 完整 `python -m unittest discover -s testing` 在本节撰写时仍在跑（约 90 min、CPU 持续爬升、当时 ≥147 项通过零失败）；日志 `working\_full_discovery_20261024.log`，最终 tally 另行报告。

### 代码替换说明（2026-10-24 上午）

- 用户把另一架电脑的 studio 代码整体替换到本工作区 → 此前本地改动丢失、逐项重做；源码 mtime：director_cut_studio.py / smart_render_worker.py = 2026-10-24 ~12:00，character_swap_engine.py = 2026-10-23 23:51。
- v0.3.8-alpha.3 的三个 UI 功能（Ctrl+右键 shot 级删除 / Ctrl+左键自动合格框 / 大脸自动合格框）已确认在当前源码在位（director_cut_studio.py L6610/L6711/L6801）。

### 待办（下一位开发者）

1. **S10**：等用户目视确认 S7 take 后开跑。recon 已完成：segment 21.443–22.610s、R2→P1＋R1→P1 silent_listener、两框均 dominant → head-band 路径；plate `v1_relay_5fa4f238634c83069fe9_21.443-22.610.mp4`；P1 参考图 = node 137 最新上传。
2. **S4/S6/S8 wardrobe Shot**：验证 COMPLETE WARDROBE REPLACEMENT 条款实机效果。
3. **S1**：先换干净 P5（烧录 UI 文字 confounder）再重渲。
4. **卡通媒介保留修复**：_9 上实机验证（flag 关闭后确认保留卡通造型、不再真人化）。
5. 完整测试套最终 tally（见 `working\_full_discovery_20261024.log`）。

## 15. LM Studio → Strata 迁移与 unload/reload 实机验证（2026-10-24 晚间增补）

### 服务与路由（本机已验证，不要再猜）

本机 LLM host 已换成 **Strata** `http://127.0.0.1:47831`；LM Studio `:1234` 已停。本 thread 测试模型 = Qwen3.8-Flash-Next IQ3_S，API id `iq3_s`。

| 用途 | 路由 | 备注 |
|---|---|---|
| 是否已加载 | `GET /v1/models` | `data[0].id="iq3_s"`、`owned_by="strata"`、`meta.instanceId`（UUID，每次加载都换）、`meta.label`、`meta.aliases` |
| 判别 LM Studio | `GET /api/v1/models` | Strata 上 **404**，LM Studio 上 200 |
| 判别 Strata | `GET /api/models` | 200 |
| 加载 | `POST /api/native/operations`，body `{"kind":"load","args":{"model":"iq3_s"}}` | **202 异步**，实测 ~39s 才 ready；**不是 no-op**：fingerprint 变化时会重启 engine（曾把 agent 自己的 turn 打死） |
| 卸载 | `POST /api/native/instances/{instanceId}/unload`，body `{}` | 必须用 `meta.instanceId`，不是模型名 |

### 对 Codex 配置的影响

- `~/.codex/config.toml`：provider `lmstudio-local`、base_url `http://127.0.0.1:8931`（tray 的 responses→chat bridge）、`model="iq3_s"`、`thread_unload_delay_secs=999999999` 保持。
- `codex-cli 0.163.0-alpha.11`：`codex queue --thread <id> --message ...` 可用（auto-resume 依赖它）；`codex status --ping` **不存在** → §13 里那条 keep-alive ping 循环是 no-op，别再依赖它。

### Tray 迁移（`ai_libraries_common\director_studio_h3_status_tray\h3_status_tray.ps1`）

- 新增 `Get-LmOriginBase`（剥掉尾端 `/v1`）、`Write-TrayActionLog`（→ `h3_tray_actions.log`，全链路审计）、`Test-StrataHost`（探测 `/api/v1/models` 再 `/api/models`，只缓存正向结果）。
- `Get-QwenLoadedInstances`（用 `qwen_key_filter` 比对 id/aliases/label，回 `meta.instanceId`）、`Invoke-QwenAutoLoad`（Strata load + 3s 轮询 ≤180s，刻意 blocking）、`Invoke-QwenUnloadInstances`（两种 host 共用）都加了 Strata 分支；菜单 handler 复用同一批 helper。
- 启动与保存设置时会归一化 origin，并记录 owner 变化。

### 两个真正的根因（"tray 无动于衷" / "又强制 unload" 的答案）

1. `Update-H3TrayStatus` 在 ComfyUI 状态端点连不上时**立刻 throw** → 整个 forward-enforcer + auto-resume 被跳过 → tray 看起来完全不动。修：payload 抓取失败改为 `$payload=$null`（非致命），气球显示 `[ComfyUI status offline]`，enforcer 继续每个 tick 跑。
2. 反向 arbiter 把「ComfyUI 连不上」（`$queueIdle=$null`）读成 **busy** → ComfyUI 根本没开也强卸 Qwen。修：必须 `$queueIdle -eq $false` 才开火。

### driver / Studio 侧同步改动（py_compile 全过）

- `staged_model_driver.py`：`engine_kind()`、`_qwen_loaded_instances()`、`_load_instance`、`_unload_instance`；`DEFAULT_LM_ORIGIN=http://127.0.0.1:47831`、`DEFAULT_QWEN_LOAD_MODEL=iq3_s`。
- `design_cleanup_service.py`：新增 `_unload_strata()`。
- `design_ai.env`：base 改 `http://127.0.0.1:47831/v1`、model 改 `iq3_s`，并把 **`H3_DESIGN_UNLOAD_LM_AFTER_SEMANTIC_ENRICHMENT=false`**。语义变化要说清楚：**Studio 不再在每个 operation 开头强制 UNLOAD ALL**，改由 tray 仲裁；用户「ComfyUI 与 Qwen 不同步加载」的约束仍由 claim 文件 + driver 分阶段保证。想恢复旧行为就把该 env 改回 `true`。

### 实机验证（有时间戳，全部来自 `h3_tray_actions.log`）

- **E2E #1 — turn 死亡 + 自动唤醒**：`21:37:39 unload sent` → `21:37:41 owner QWEN→FREE` → `21:38:39 load requested` → `21:39:18 load confirmed（39s，instance 293a22d8-…）` → `21:39:19 auto-resume queued`（status 原为 crashed）。
- **E2E #2 — 真跑 staged driver（ComfyUI 在跑）**：job `preview_930000204_1792544802183425900`（启动前 export `CODEX_THREAD_ID=01a15c24-2664-7b73-b5b1-999449872b47`）。顺序全部达成：`unload-qwen verified_clean`，VRAM **26.36GB → 2.39GB** → `wait-comfy ready (1600 node classes)` → H3 工作 → `/free ok` → `wait-qwen-reload ready: true`（tray `21:54:34 load requested` → `21:55:13 load confirmed` instance `36fe4d74-…`）→ `21:55:15 auto-resume` 唤醒本 thread。
- **claim 抑制全程成立**：整段 render 期间 tray 被 `comfy_claim.json` 压住；reload 真正开始是在 `/free` 之后约 **12 分钟**。driver 端 claim 已即时 clear，tray 还需要 queue idle 累计 ~20s 才开火——这 12 分钟是 ComfyUI 队列/显存回落的时间，不是 bug。嫌久就调 tray 的 idle 窗口或 `wait_qwen_reloaded` 超时。

### 同一个 job 的失败属于内容问题，不是生命周期问题

- 报错：`Multi-character composite needs a selected-person rectangle for every role.` —— SAM3.1 给不出 role **R2** 的 selected-person 框（pass 0/R2 `composite_bboxes_normalized: []`，同期 pass 1/R1 是 `[0.23, 0.15, 0.52, 0.94]`）→ worker exit 1。
- 日志：`logs\staged_model_driver\preview_930000204_1792544802183425900.jo_20261024_214221.log`；manifest：`…\render_jobs\preview_930000204_1792544802183425900.manifest.json`。Shot S9，两个 swap pass（R2→P3、R1→P1）。
- 要证明「一次完整成功渲染穿过整个 unload/reload loop」，换一个 cast analysis 对每个 role 都有 selected-person 框的 job 再跑一次。

### 仍未做

- **GPU-idle watchdog**（Qwen 已加载 + VRAM 满载 + 对话进行中 + GPU 连续 60s 无活动 → 自动插一条 continue）仍是方案，未实现；上一版实现被用户判为「完全没有效果」后已回退。
- Strata 冷加载稳定 ~39s，且没有可用的 keep-alive ping（见上），所以「 unload 后必须显式 start 并验证」这条规则（§13）在 Strata 上依然成立。

## 16. Reference Fidelity 根因与 Identity Sheet（2026-10-25 增补）

> 细节以 CHANGELOG.md Unreleased 区「Identity Sheet v2」条目为准；本节只给结论与状态。**本轮零 GPU 使用**，全部是源码 + 单元测试。

### 逐段取证（policy 46 / 0.2MP 全片 11 段）

每段对自身目标 P 图的 colour-histogram 中位相似度（数字越高越像参考图）：

| shot | R→P | similarity | QC 当时是否报失败 | attempts |
|---|---|---|---|---|
| S1 | R1→P5 | 0.728 | 是 | 3 |
| S2 | R1→P1 | 0.578 | 是 | 3 |
| S3 | R1→P1 | 0.554 | 是 | 3 |
| S4 | R2→P6 | 0.370 | **否** | 1 |
| S5 | R1+R2→P1 | 0.343 | 是 | 3 |
| S11 | R1+R2→P1 | 0.463 | **否** | 2 |
| S6 | R2→P3 | 0.523 | 是 | 3 |
| S7 | R1+R2→P1 | 0.513 | **否** | 1 |
| S8 | R1+R2→P3 | **0.273** | **否** | 1 |
| S9 | R1→P1 | 0.310 | 是 | 3 |
| S10 | R1+R2→P1 | 0.587 | 是 | 3 |

- 用户目视不及格项：衣服完全不像参考图 S1/S3/S4/S6/S8；角色变老 S3/S5/S7(40%)/S10(20%)/S11(60%)。
- **关键结论：颜色线索看不见年龄与脸**。S7 0.513、S10 0.587 都远高于旧的 0.30 非阻断 review floor，却仍被判「变成老人」；只有 S8（0.273、首次 attempt 直接通过并拼进 master）属于颜色线索可靠能判的「根本不像」。所以硬门槛只用来抓 S8 那一类，年龄漂移改由 Identity Sheet + apparent-age lock 进攻，而不是拿看不见脸的指标去逼额外抽卡。
- 生成端共同根因：Media Pool 全身卡通图在 460x642 V1 帧里只贡献约 1/10 帧高的头部。**实测原始 head coverage**：P1 0.1097、P2 0.1749、P3 0.1746、P6 0.0644；P4/P5 近景照片 1.377。头像素不足时 Relay 保配色、丢年龄/脸/服装细节。

### 本轮源码改动（Smart Render Policy **46 → 47**，旧 Segment 缓存全部失效）

1. `project_workspace.PREVIEW_MEGAPIXELS` 0.2 → **0.5**（按钮/文案/job/manifest 全跟随）。
2. `character_identity_sheet.py` 引擎 **v2**：公开 `measure_head_coverage()`（never-throw，失败回 `None`）；compose 放大头部面板。preset 0 实测覆盖率：P1 0.1097→0.3704、P2 0.1749→0.2994、P3 0.1746→0.3708、P6 0.0644→0.1413、P4 1.377→0.241、P5 1.377→0.245。
3. 新增 `identity_sheet_page.py`（Design 页 `IDENTITY SHEET` 组 → `OPEN IDENTITY SHEET PAGE…`）：cast 列表／缩略图／preset 下拉／panel role 说明／覆盖率读数／预览／Measure／Compose／Compose all that need it／Export…／Open folder。**纯 PIL，不占 GPU、不连 ComfyUI**；上游 H3 still-model 生成器未安装，故本页本地合成同等多面板表义（见 `UPSTREAM_SHEET_NOTE`）。
4. Studio 集成：`set_identity_sheet_settings()`（preset 走 `SHEET_PRESET_KEYS` 白名单）、`open_identity_sheet_page()`（惰性 import + 单例）、`note_identity_sheet_page_closed()`；`identity_sheet_enabled` / `identity_sheet_preset` 持久化，new/load project 时关闭旧页并白名单校验。
5. 渲染接线：`_character_swap_identity_sheet_reference()` 按该 Shot V1 clip 真实分辨率量覆盖率，`< IDENTITY_SHEET_MIN_HEAD_COVERAGE`(0.22) 才合成 sheet → framing `illustrated_identity_sheet`，否则原图透传 `illustrated_full_design`；pass spec 带 `reference_framing` + `target_reference_path`(sheet) + `target_reference_qc_path`(原始 P 图)。
6. `character_swap_engine` 新条款：`PICTURE 1 IS ONE IDENTITY SHEET — AUTHORITATIVE`（仅 sheet framing）、`APPARENT AGE LOCK — MANDATORY`（`not live_action_adaptation` 恒定触发）；背景纹理合约门槛改常量 `PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA = 0.10`。
7. `smart_render_worker`：QC 参考图优先 `target_reference_qc_path`；target-similarity 从非阻断 flag 升级为**硬门槛** `target_similarity_floor`（默认 0.30，`minimum_target_reference_similarity` 覆盖，0 关闭）→ `target_similarity_failed` + `retry_fresh_seed`；警告带 `TARGET_SIMILARITY_WARNING_BAND = 0.06` 内仍拼装只标 `target_similarity_review`。

### 状态

- **源码已修复**：以上全部 + `testing\test_identity_sheet.py` 18 项、重写 `test_smart_render_worker.py::test_identity_audit_hard_rejects_take_that_never_matches_target`、五个源文件 py_compile。
- **视频尚未实机验证**：0.5MP、Sheet 合成、两条新条款、硬门槛、policy 47 全都没在 ComfyUI 上跑过一帧。
- 建议实机顺序（每步走 `staged_model_driver.py run`，测完 `/free`）：① S4（衣服 + 背景 invented pattern，Sheet + wardrobe + texture 三条同时受验）；② S10（曾报 no reliable box）；③ S3/S5/S7/S11 年龄漂移；④ S1（P5 自带烧录 UI 文字的 confounder，先换干净素材）；⑤ 最后整片。

### 待用户许可才能动的项目数据（Studio 关闭 + 先备份 JSON）

`example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9\project\director_project.h3director.json` 内仍与「全部参考图已改 P1」不一致：global binding idx13 `R1→P5 scene[1]`、idx12 `R2→P4 scene[5]`；S1 `lip_sync_target=P5`；S4 覆盖 `{"R2":"P6"}`；S6 `{"R2":"P3"}`；S8 `{"R2":"P3","R1":"P3"}`。另有 exists=False 的坏素材引用：A1-A3 `xxt_mv2_S3.wav`、V2/V3 `gp7yg5.mp4`、P7/P8/P9 `WhatsApp Image 2026-08-14 at 3.41.08 AM (2).jpeg`。

### 本轮踩到的工程坑（写给下一位）

- `apply_patch` 同一个 hunk 里**不要**把同一段文字既当前导上下文又当尾随上下文（会误报 "Failed to find expected lines"）；跨 hunk 必须按文件行号升序。
- 全量 `python -m unittest discover -s testing` 在本机看起来「非常慢甚至挂死」的真正原因已查明（见 §17）：**没设 `QT_QPA_PLATFORM=offscreen`**。Qt 测试在真实桌面建窗口时既慢又会以 `0xC0000409` 吞掉后续模块。

## 17. 2026-10-25 追加：单元测试契约全绿 + 正确跑测方式

### 唯一可靠的整轮跑法（6.5 分钟，已实测）

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'   # 必须先设，否则 Qt 测试在真桌面建窗口
.\ai_libraries_common\python_env\python.exe working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline
```

实测结果：`Ran 734 tests in 382.849s` → `failures=0 errors=0 skipped=10`，退出码 0（49 个模块；`test_director_timeline.py` 238 项因每项拉起 `design_ai_service.py` 子进程、单模块 2 小时以上而 `--skip`）。完整日志 `.director_cache\suite_full_20261025.log`。§8 里 2026-10-19 的 `-m unittest discover` 命令与 `Ran 52/53 tests` 只作历史保留，日常验改用上法。跳过 10 项全是环境条件：2 项需要本机不存在的 example 用户项目（`tang_ting_ci_ying_45s_demo`、`Dragon_Realm_vs_Immortal_Martial`，已改为缺文件即 `skipTest`）、7 项需要未安装的可选运行时、1 项既有跳过。

### 本轮清零的 8 项既存红项（只改测试／技能文案，未改产品语义）

| 位置 | 根因 | 处理 |
| --- | --- | --- |
| `test_project_workspace.py:250` | preview 期望仍 0.2，本轮有意升 0.5 | 期望改 0.5 |
| `test_fourdx_ui.py:95` | payload version 期望 25，格式已 29 | 改 29 |
| `test_soulx_dialog.py:112` | 本机装有 SoulX ⇒ `detect_soulx_runtime()` 回 127.0.0.1 覆盖默认服务器，测试随主机状态摇摆 | 注入确定性 `SoulXRuntimeState` fixture 专测 fallback |
| `test_staged_model_driver.py:314/:335` | auto-resume 的 detached `resume-wait`（`_spawn_resume_watcher`）被算进 Popen 次数 | patch 掉 watcher 并另断言「必须被唤醒」 |
| `test_skill_engine.py:829` | 本地 wuxia 技能根本没有 input-repair 章节 | `SKILL.md` / `SKILL.cn.md` 补章节（含 60–120 度、九个五秒 Shot、零预算警告等全部契约短语） |
| `test_comfy_connection_recovery.py:293/:302` | `comfy_submit_worker.main()` 的 `finally` 现在无条件 POST `/free` 且复用 `_request_json`，把「只排队一次」计数变成 2 | 新增 `_queue_posts()` 只数 `/prompt`，checkpoint 契约不变 |
| `test_design_engine.py:2056` | `unload_lm_studio` 先做宿主方言探针（进程级 per-origin 缓存）再读 catalog ⇒ 2 次 GET，且随测试顺序摇摆 | pop `_HOST_KINDS` 去顺序依赖；断言改为「不得出现 unload POST」 |
| `test_design_engine.py:3162/:3840` | 直接读本机不存在的 example 项目文件 ⇒ 环境 ERROR | 缺文件 `skipTest` |

`director_cut_studio.py`（37492 行）与 `character_swap_engine.py` / `smart_render_worker.py` / `identity_sheet_page.py` / `character_identity_sheet.py` / `staged_model_driver.py` / `project_workspace.py` / `comfy_submit_worker.py` / `design_cleanup_service.py` py_compile 全部通过。

### 托盘噪音的解释（不要再误判成实机渲染）

`testing\test_staged_model_driver.py` 会对**真实** LM Studio / ComfyUI 端点发 unload、`/free`、VRAM 读数控制请求，并写/清真实 claim 文件；跑它时 tray 会弹「Qwen loaded／unloaded」气球、并可能回报「staged driver crashed on job …\Temp\preview_test.job.json」。那是单元测试的临时 job，**不是**用户的 Smart Render Job，也没有产生任何视频。实机验证结论只能来自 `staged_model_driver.py run "<project 内 job.json>"` 的 manifest + 输出文件。

### 当前验证边界（务必区分）

- **源码已修复**：0.5MP preview、Identity Sheet v2 + 独立页面、Age Lock / Scene lock / Wardrobe lock / 官方字段内注入、0.200 背景纹理门槛、target-similarity 硬门槛 + 静止条带降级、dirty clamp、fingerprint 先定稿 derived 原生音频散文（Smart Cut 全部段被误重渲的根因）、多角色 head-band 抑制、Silent listener 条款强化。单元测试 734 项全绿。
- **仍未实机验证**：上述全部效果的成片表现。用户最新一支视频仍然报「替换角色全部失败／不像参考图」，所以**不能**宣称问题已解决。GPU 许可后的顺序不变：S4 → S10 → S3／S5／S7／S11 → S1（先换干净 P5）→ 整片，一律 `staged_model_driver.py run`，测完 `/free`（driver 内置）。

## 18. auto-resume 复活 + tray 自助重启（2026-10-25 增补）

本节只谈 unload/reload 与 tray auto-resume 管线，成片渲染在生产 thread `01a1531f-18f6-7a93-886b-22195e0516a5` 进行；本 thread（`01a15c24-…`）负责管线本身。

### 「tray 完全不能执行 Tray auto-resume」的真实原因

跑着的 tray 进程 07:16 启动，而 `Find-CodexCliOnDisk` 是 10:01 才写进 `h3_status_tray.ps1`。**PowerShell 在启动时就把脚本全文编译进进程**，之后的编辑永远不会进入正在跑的 tray → 每 5 秒刷 `auto-resume skipped: codex.exe not found`，auto-resume 全天失效。不是逻辑坏了，也不是 Codex CLI 不存在：`C:\Users\daniel\AppData\Local\OpenAI\Codex\bin\2993767bd1dfb009\codex.exe`（`0.164.0-alpha.11.1`）里 `codex queue --thread <id> --message <text>` 实测可用。

顺带确认的另一条：`http://127.0.0.1:8931/responses` 回 503 `Load a native Strata model to use the Responses API.` ＝ Strata 说「现在没载模型」，模型 loaded 后同一请求 **200**。8931 = Responses 前端（Codex base_url），47831 = OpenAI 兼容前端（tray 由此 load）。

### 已落地并实机验证

- `Resolve-CodexCli` 解析顺序：settings `codex_exe` / `H3_CODEX_EXE` → PATH → 磁盘扫描 `%LOCALAPPDATA%\OpenAI\Codex\bin\<hash>\codex.exe`（PATH 只在 tray 是 Codex app 子进程时存在）。单测方式：把 PATH 压成 `C:\Windows` 仍能解析出 codex.exe。
- 启动 fingerprint：`tray started: pid=… script_mtime=… codex=…`（`h3_tray_actions.log`），比对 mtime 与 log 首行即可判断「跑的是旧副本」。
- **Restart Tray (apply script edits)** 菜单项 + 同目录 `restart_h3_status_tray.bat`（`ping -n 3` 延迟后 `call start_h3_status_tray.bat`）。必须延迟：单例 mutex `Local\MiniMaxH3DirectorServerStatusTray` 未释放时第二个实例会静默 `exit 0`。
- **Stale-script watcher**：启动记录 `trayScriptPath` + `trayScriptMtimeAtStart`，每 tick 在 `Update-H3TrayStatus` **末尾**调用 `Invoke-TrayScriptStalenessWatch`（必须放末尾，两条 return 分支都会重写 `statusItem.Text` / `notify.Text`；放开头会被覆盖）。命中后菜单文字追加 `[script edited - use Restart Tray]`，log/气球限流 900 秒一次。
- 实机时间戳：10:07:08 新 tray（PID 2224）`codex CLI resolved` → 10:07:09 `auto-resume queued into thread 01a1531f-…`，生产 thread 10:07:18 真的开了新 turn，`active_run.json` 翻成 `resumed`。10:21:35 PID 5524、10:22:30 PID 28360 两次都通过 `restart_h3_status_tray.bat` 完成重启，中途 touch 脚本后 5 秒内出现 `stale tray script: …`，重启后归零。
- 陷阱：`Start-Process -ArgumentList` 不会为数组元素加引号，含空格路径静默失败；重启一律用 `Start-Process -FilePath "<dir>\start_h3_status_tray.bat"`（或 restart bat）。

### 操作纪律（新增，务必遵守）

改完 `h3_status_tray.ps1` 之后**必须**走 tray 菜单 Restart Tray（或 restart bat）才算生效；判断某个 PID 是否落后于源码，看 `tray started` 行的 `script_mtime`。`thread_unload_delay_secs` 必须是 u64（`-1` 会让每次 `codex.exe` 调用在 config load 阶段失败），本机现为 `999999999`。

## 19. Reference Fidelity 四条根因与长度天花板（2026-10-26 增补，policy 52→57）

### 用户最新整片分级（`example\a_cartoon_character_with_a_mustache_and_a_yellow_shirt_9`）
S1 完全不像；S2 角色 ok＋背景蜂窝；S3 变老人＋衣服不像；S4/S6/S8 角色 ok＋「衣服完全不像」；S5 80 % 可接受；S7 40 %；S10 20 %；S11 60 %；S9 前半段没换上。规格 = 官方 H3 character-swap prompt（逐字写入 `_relay_v2_author_prompt`）。

### 四条根因（都已取证，勿重复调查）

| # | 根因 | 证据 | 处理 |
|---|---|---|---|
| A | 长度守卫先丢掉 load-bearing 尾部条款 | `/history` 回读 seed 97000374–97000544 的**实际提交提示词**（`working\submitted_prompts_20261025\`）：每个 ok／80 % 的 take 都有 `CLOSE-UP MEDIUM REINFORCEMENT` 与 `NO INVENTED TEXTURE OR PATTERN`，每个 20–60 % 的 take 都缺这两条 | policy 52–55：条款冻结（无 rank 永不丢）＋重复表述压缩＋预算重校准 |
| B | P1 原图只有 209×600，头部裁片 136×163 px 被放大进 sheet 面板 | 对照 P5 head 面板原生 1734×1509（历史最高相似度 0.689，也是最好的一组） | 未实施：把 P 图先超分再进 Media Pool（需用户决定） |
| C | **plate 与 prompt 不一致**：`dominant_closeup_identity_suppressed` 糊掉近全屏框约 62 % 高度（头＋肩＋胸），提示词却说「只糊头」 | round 13（97000554 S3／97000564 S10／97000574 S6）从糊块平均色幻想出灰发老人与道袍腰带；同轮只有 plate 真的只糊头的 S2（97000584）被评 ok | policy 56：`plate_torso_blurred_clause`，措辞由 `pass_spec["identity_suppression_geometry"]` 上报的真实几何决定（Studio／Worker 双侧透传） |
| D | **Identity Sheet 分格漏进画面**：Relay 只有一个图片槽，多面板被当成场景人数 | round 13 背景复制人数量 == 面板数，且复制人穿 P 图正装 ⇒ 这才是「衣服完全不像」的观感来源 | policy 56：`identity_sheet_contract` 加 `Render exactly one instance ...` |

### 长度天花板（重要：别再凭感觉调预算）
- **12 326 字符** = 已验证可完整提交并渲染的最长提示词（seed 97000584，policy 55，`/history` 回读长度一致）；更早的 11 911（seed 97000374）只是地板。
- policy 57 压缩六条尾部条款（≈410 字/Shot）后，`CHARACTER_SWAP_PROMPT_CHAR_BUDGET = 12320`，11 个 pass 全部 `over_budget=False`（最长 S6 12 304）。此前 S2/S3/S6/S10 悬在 12 518–12 688。
- 三个 silent Shot 仍让出 ≈400 字 `close_up_silent_mouth`（完整长度 12 537–12 734，任何 ≤12 326 的预算都留不住）。round 10/11 已证明它不是决定性因素：seed 97000374 丢掉它对嘴，seed 97000454 带着 720 字完整版也照样对嘴；真正压住嘴的是 plate 头部模糊＋官方作者提示词的闭嘴替换。
- `close_up_medium_reinforcement` 与 `plate_texture_contract` **绝不能进 `CHARACTER_SWAP_TAIL_DROP_RANKS`**（`test_medium_and_plate_texture_clauses_are_never_droppable` 已锁死）。

### 当前状态（务必区分）
- **源码已修复**：policy 56（plate 几何条款＋sheet 单实例）、policy 57（条款压缩／预算 12 320）。`testing\test_character_swap_engine.py` 61/61、`testing\test_identity_sheet.py` 22/22，三个核心文件 `py_compile` 通过。
- **尚未实机验证**：年龄漂移、蜂窝背景、衣服不像、silent 对嘴——round 14（policy 57：S3/97000714、S10/97000724、S6/97000734 preset 2、S2/97000744，链脚本 `working\_chain_round14_20261026.ps1`，日志 `_dsh_verify_9\round14\logs\`）出片读帧前，以上四项一律算未验证。

### 本轮工具（都在 `working\`，全部离线）
- `_precheck_full_build_20261026.py`：Studio 真编译路径逐 pass 打印 `chars/over/dropped`，自动删除自造 job；`H3_PRECHECK_BUDGET=999999999` 看未裁剪全长。
- `_clause_census_20261026.py`：条款级长度普查（读 precheck 输出目录）。
- `_job_prompt_census_20261026.py`：读**真 job** 里的提示词，报告长度与 load-bearing 条款是否在场（本轮新建）。
- `_dump_submitted_prompts_r13_20261026.py`：从 ComfyUI `/history` 回读实际提交提示词（改 `want` 字典即可复用于 round 14）。
- `_board_seed_20261025.py` / `_plate_vs_take_20261026.py` / `_manifest_index_20261026.py`：读帧拼图、plate-vs-take 对照、manifest 索引。

### 若 round 14 背景仍有复制人（round 15 候选）
把 Identity Sheet 改成单一人形布局：`character_identity_sheet.py::compose_identity_sheet`，`IDENTITY_SHEET_ENGINE_VERSION` 4→5。可用 preset：0 head+body、1 head above body、2 head+body+outfit、3 head/mirror/body、4 head only、5 body+outfit、6 2x2 grid、7 head+front+rear。

## 20. Identity Sheet v5 + close-up 裁切线判定：policy 58→60 与 round 14–18（2026-10-26 增补）

### 版本指针（接手时请核对这三行）

| 项目 | 值 |
|---|---|
| 应用版本 / Project Format | `0.3.8-alpha.3` / 29（`VERSION`，未变） |
| `SMART_RENDER_POLICY_VERSION` | **60**（`director_cut_studio.py:535` 与 `smart_render_worker.py:54` 两处必须同步） |
| `IDENTITY_SHEET_ENGINE_VERSION` | **5**（写进 sheet 档名；改面板几何就必须递增，否则旧缓存混片） |
| `CHARACTER_SWAP_PROMPT_CHAR_BUDGET` | 12 320（已验证天花板 12 326 = seed 97000584） |
| GPU seed 水位 | 已用到 **97000874**，下一颗 **97000884**（`_build_real_preview_20261025.py` 自增） |

### 接 §19 的三条新根因（A–D 见 §19，勿重复调查）

| # | 根因 | 证据 | 处理 |
|---|---|---|---|
| E | identity-suppression 遮罩是**硬边矩形**，把人物框里 44 % 画幅的墙面一起糊掉 | round 13/14 的 S6 背景蜂窝；plate 帧里没有蜂窝 ⇒ 生成期幻觉 | policy 58：遮罩改圆角羽化 alpha 窗口，`H3_CHARACTER_SWAP_IDENTITY_MASK_MODE=rect` 回滚 |
| F | P1 只有 209×600，五官在 sheet 上只占 **15.3 %** 画布 ⇒ H3 没有头部证据，只能从 plate 颜色猜年龄 | 用户 grading 中 S3/S5/S7/S10/S11 全部「变老人」，相似度 20–80 % | engine v5：面板配重改脸部优先（`ORIENT_SECONDARY_PANEL_WEIGHT = 0.05`，已钉测试），脸占画布升到 34.2 %（uhip）／44.7 %（uchest） |
| G | 衣柜面板一律裁到全身，近景画不到的腿和鞋被读成「另一个人」 | round 15 S2 帧内出现小型 P1 分身；round 16 S2 同样复现 | engine v5：衣柜面板按景别裁切（`OUTFIT_VIEW_SHARES`：`close_up` 0.34=`uchest`、`medium` 0.62=`uhip`） |

### 实机轮次全记录（0.5 MP，全部经 staged driver；`sim` = `target_reference_similarity`，`sel` = 被选中的 attempt 序号）

| round | policy | seed / Shot | chars | dropped | sim | 判定 |
|---|---|---|---|---|---|---|
| 14 | 57 | 97000714 S3 | 12 134 | silent | 0.532 | 仍是老人＋金色团花袍 |
| 14 | 57 | 97000724 S10 | 12 180 | silent | 0.527 | 同上 |
| 14 | 57 | 97000734 S6 | 12 304 | silent | 0.478 | 背景蜂窝仍在 |
| 14 | 57 | 97000744 S2 | 12 309 | — | 0.572 | 五官 ok，分身仍在 |
| 15 | 58 | 97000754 S6 / 97000764 S2 / 97000774 S3 / 97000784 S10 | 12 132–12 309 | silent(3) | 0.458–0.565 | 羽化遮罩没治好蜂窝，分身仍在 ⇒ 触发 engine v5 |
| 16 | 59 | 97000804 S3（**uchest**） | 12 132 | silent | 0.537 | 无眼镜、无帽、金色团花袍 ⇒ uchest 失败 |
| 16 | 59 | 97000814 S2（**uhip**） | 12 309 | — | 0.551 | 五官回到卡通 P1 ⇒ uhip 有效，但有分身／真人／蜂窝／构图漂移 |
| 17 | 59 | 97000824 S3（**uhip**） | 12 132 | silent | **0.555** | P1 圆眼镜＋黑帽金带红顶＋胸前深色面板三白点**同时出现** |
| 17 | 59 | 97000834 S10（**uhip**） | 12 178 | silent | 0.509 | 至今最像 P1（大卡通眼／眼镜／张嘴大笑／P1 帽），但**长出黑色山羊胡**、鬓角仍是源演员深色发 |

### round 17 = policy 59 之后唯一干净的单变量实验 ⇒ 已落成产品默认
同 policy、同 engine v5、同 plate、同 12 132 字提示词，只差衣柜面板裁切线：**S3 uchest 失败、S3 uhip 成功**。因此 `director_cut_studio.py::_character_swap_identity_sheet_reference` 把 close-up Shot 的裁切线从 `close_up`(uchest, 0.34) 改成 `medium`(**uhip**, 0.62)，判定写成 `if medium_rows: "medium" elif closeup_rows: "medium"`，源码注释钉住本轮证据；回滚只需 `H3_IDENTITY_SHEET_OUTFIT_VIEW=close_up`，不必改码。`SMART_RENDER_POLICY_VERSION` 59→**60** 让默认裁切线进指纹，旧 close-up Segment 缓存全部作废。回归测试：`testing/test_identity_sheet.py::test_closeup_shot_gets_the_hip_height_wardrobe_panel`（metrics `identity_sheet_outfit_view == "medium"`、档名含 `_uhip_`；override 必须给 `_uchest_`）。

### 别再拿 QC 相似度当分数
round 14→17 的 `sim` 全落在 **0.458–0.572**，和用户 grading（20 %／40 %／60 %／80 %）没有相关性；0.537 与 0.555 是同一段的「失败」与「成功」。结论：**相似度只能用来发现「完全不同人」，判定必须靠人眼读帧**（`working\_board_seed_20261025.py`）。顺带：这些 run 的 `qc_pass` 末位一律 `False`，因为 `silent_mouth_excessive_articulation`（见下）。

### GPU 生命周期：409 unload 竞态这一次是**实机证明**修好了
- 症状：tray 会把 Qwen 载回并立刻预热，`run` 的 `unload-qwen` 撞在还开着的 warm completion 上，Strata 回 `HTTP 409 … Finish or cancel this model's requests first.`。2026-10-25 每一个 `preview_*.job.json` 都在 ComfyUI 收到任务前崩在这一步。
- 修法（`staged_model_driver.py`）：`_unload_busy_error()` 识别 busy；每轮重试前 `_cancel_inflight_requests()` 扫 host 的 serving request 列表并逐个 `POST /api/serving/requests/{id}/cancel`（`H3_STAGE_QWEN_FORCE_CANCEL=0` 关闭）；`UNLOAD_POLL_SECONDS` 30→**90**；`verified_clean` 仍要求 VRAM 实测下降 ≥ `MIN_VRAM_DROP_GB`。
- 证据：round 17 两条 Job attempt 1 撞 409、**attempt 2 成功**，VRAM **26.69 GB → 4.05 GB**，`exit=0`。round 18 第一条同样 attempt 1 撞 409 后自愈 ⇒ 设计如预期，不是回归。
- 三条硬约束不变（Python 分阶段驱动／不同步加载／测完 `/free`）。GPU 长任务**必须**用分离式 launcher：`_launch_chain_roundN_20261026.ps1` 里 `Start-Process -WorkingDirectory (Split-Path -Parent $script)` 且只传 leaf 名（根目录含空格），否则会把自家推理请求一起 cancel 掉。

### 本轮 env 开关一览（默认值＝出厂行为，全部无需改码）

| 变量 | 作用 | 默认 |
|---|---|---|
| `H3_IDENTITY_SHEET_OUTFIT_VIEW` | `close_up`／`medium`／`none` 强制衣柜裁切线 | 空＝逐 Shot 自动（现在 close-up 也走 medium） |
| `H3_CHARACTER_SWAP_IDENTITY_MASK_MODE` | `rect` 回滚硬边遮罩 | 羽化 alpha 窗口 |
| `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` | 躯干服装带 | `off`（**已否决，别再试**） |
| `H3_STAGE_QWEN_FORCE_CANCEL` | unload 时取消 host 在飞请求 | `1` |
| `H3_STAGE_QWEN_LOAD_MODEL` / `H3_COMFYUI_URL` / `H3_LM_STUDIO_ORIGIN` | 覆盖模型名与服务地址 | 从 `design_ai.env` 解析 |

### 状态：务必分清「源码」与「视频」
- **源码已修复＋单元测试绿**：policy 58（羽化遮罩）、59（遮罩＋sheet 配重进指纹）、60（close-up 用 uhip）；engine v5 脸部优先配重＋按景别裁切；driver unload 修复。`testing/test_identity_sheet.py`＋`test_character_swap_engine.py`＋`test_character_swap_closeup_gates.py`＋`test_character_swap_silent_audio` **118/118**，`test_smart_render_worker` **50 OK, skipped=1**，六个核心文件 `py_compile` 通过。
- **视频已实机验证**：uhip 让 S3 的 P1 五官／帽子／胸前面板同时回来（97000824）；uhip 让 S2/S3 五官绑定成功（97000814／97000824）；driver unload 修复。**仅此三项**。
- **仍是待验证假设**：close-up 全面改 uhip 后 S10/S7/S1/S11 的相似度（round 18 进行中）；年龄漂移；服装被源 plate 压过；凭空长出面部毛发；背景蜂窝；silent listener 对嘴。

### round 18 队列（policy 60、无 env override＝新默认；链 `working/_chain_round18_20261026.ps1`，日志 `_dsh_verify_9/round18/logs/`）

| 顺序 | seed | Shot | 角色 | 对照 |
|---|---|---|---|---|
| 1 | 97000844 | S10 | R1→P1，silent listener，dominant close-up | 97000834（round 17 uhip，用户 ~20 %）：看山羊胡与深色鬓角会不会重演 |
| 2 | 97000854 | S7 | R1→P1，on-screen speaker，11.838–15.848 s | 用户 grading 40 %（变老人） |
| 3 | 97000864 | S1 | R1→**P5**，on-screen speaker，0.0–0.242 s，head cov 0.471 | 现片「完全不像」；P5 sheet 第一次走 uhip |
| 4 | 97000874 | S11 | **R2**→P1，on-screen speaker，8.0–10.808 s | 用户 grading 60 % |

离线 pre-flight：`working/_r18_precheck_20261026.py` → `_dsh_verify_9/round18/precheck_policy60.txt`。四条 pass 长度 10 534–12 178，`over_budget` 全 False；**S10 仍是 `dropped_tail_clauses=['close_up_silent_mouth']`**，S7/S1/S11 无丢弃。判片：`working/_board_seed_20261025.py <seed> <label> [P图]` → `_dsh_verify_9/round9_frames/`。

### 五项残留问题与唯一可动的杠杆
① 年龄漂移 ② 服装被源 plate 压过 ③ 凭空长出面部毛发／细节 ④ 背景蜂窝 ⑤ silent 对嘴。提示词侧已饱和：`identity_sheet_contract`（禁第二个分身）、`apparent_age_lock`（禁加年龄）、`plate_torso_blurred_clause`（禁从糊掉的颜色猜服装）三条**都在提示词里，实机照样违反** ⇒ 再加措辞无效。⑤ 的两条候选（都还没做，动码前问用户）：(a) 再压缩约 200 字让 `close_up_silent_mouth` 活下来（headroom 只有 188 字；`close_up_medium_reinforcement` 与 `plate_texture_contract` 已被测试锁死不可丢）；(b) 所有 attempt 都违反 silent 时改选 mouth motion 最小的一条（现在已会选，但仍标 failed，白白烧 3 次 fresh-seed 重试）。**已否决方向**：source plate 躯干服装带（round 9 终局判定「只要动躯干带就变差」）。

### 本轮工具增补（全部离线，在 `working\`）
`_r18_precheck_20261026.py`（job 里到底写了什么：长度／dropped／silent 与 sheet 措辞 marker）、`_manifest_index_20261026.py`、`_audit_dump_20261026.py`、`_sheetpaths_probe_20261026.py`（sheet 档名与是否存在）、`_sheetvar_20261026.py`、`_job_prompt_probe_20261026.py`、`_board_seed_20261025.py`、`_plate_vs_take_20261026.py`、`_build_real_preview_20261025.py`（唯一离线建 job 入口）。rounds 14–17 的 QC 索引快照：`_dsh_verify_9/round18/rounds14_17_index.txt`。

## 21. round 18 实机基线 + 修因 I／J：两处让 Job 白烧的驱动与 QC 缺陷（2026-10-26 增补）

### round 18 结果（policy 60 第一次实机，0.5 MP，链 `_chain_round18_20261026.ps1`，日志 `_dsh_verify_9/round18/logs/`）

| 顺序 | seed / Shot | exit | sim | 人眼结论（读帧图 `_dsh_verify_9/round9_frames/`） |
|---|---|---|---|---|
| 1 | 97000844 S10 | **2** | — | `run-aborted reason=qwen-not-clean`，ComfyUI 从未收到任务 ⇒ 修因 I；**唯一没有产物的一条，必须在 round 19 补跑** |
| 2 | 97000854 S7（R1→P1） | 0 | 0.515343 | **大胜利**：五官回到卡通 P1（圆眼镜＋八字胡＋大笑），衣服＝黄长衫＋黑马甲三白点＋蓝格裤，媒介仍是卡通。用户 grading 40 % ⇒ 可接受 |
| 3 | 97000864 S1（R1→P5） | **1** | — | QC 采样点越界抛异常，take 其实已经渲染出来 ⇒ 修因 J |
| 4 | 97000874 S11（R2→P1） | 0 | 0.467493 | 仍不合格：脸变老人（银灰鬓、皱纹、长八字胡），衣服＝源演员的**金色团花袍** |

真实 plate（H3 实际收到的糊脸源片）：`_dsh_verify_9/round18_frames/{97000854_S7,97000874_S11}_suppressed_plate.png`，生成器 `working/_suppressed_plate_20261026.py <seed…>`。⚠️ `working/_plate_vs_take_20261026.py` 的顶行是 **RAW relay**，不是 blurred plate，别看错。

### 缺陷⑥（round 18 新发现，尚未修码）
close-up 改 `uhip` 之后，S7 把 identity sheet 的**衣柜面板整段搬进画面**：桌子被抬高、画面下缘多出垂手拳头、袍摆与格裤 ⇒ 违反 `do not widen the shot to reproduce the full-body reference`。这正好是 `uhip` 裁切线的代价：衣柜证据给够，H3 就想把衣柜画满。可动的杠杆是 close-up「遮蔽不变」条款（S7 当前 10 595／12 320 字，headroom 1 725 够写），还没做过 A/B。

### 修因 I：driver 的 unload cancel 白名单缺 state（源码已修复＋测试绿）
- **实测 state 词汇**（`working/_strata_states_live_probe_20261026.py`，log 同名 `.log`）：Strata `/api/serving` 只会给 `queued/True`、`generating/True`、`done/False` 三种 `(state, cancellable)`，而且 **finished row 永久留在 ledger**，不能靠「行消失」判断。
- **旧行为**：白名单只有 `queued/running/starting/pending`，缺 `generating` ⇒ `_cancel_inflight_requests()` sweep 命中 0 条 ⇒ 每轮 `HTTP 409 … Finish or cancel this model's requests first`，90 s 窗口耗尽后 `run` 直接 abort，ComfyUI 一分钱没花（97000844 就是这么死的）。
- **新行为**（`staged_model_driver.py`）：白名单补 `generating/streaming/processing`；新增 `TERMINAL_REQUEST_STATES`、`_request_state()`、`_request_is_live()`（判定＝`cancellable` 且 state 不在 terminal 集合，**未知 state 一律当作 live**）；`_inflight_request_ids(rows)` 接 row 列表不再二次 GET；`_cancel_inflight_requests()` 回报 `observed`（前 8 行带 `recognised` 标记）；sweep 空但 ledger 非空时 emit `cancel_sweep_empty`（attempt 1／7／最后一次），下次再撞就不用猜。
- 测试：`testing/test_staged_model_driver.py` **24 项全绿**，新增 `test_generating_and_unlisted_states_are_still_cancelable`、`test_strata_unload_cancels_a_generating_tray_request`；`_strata_host_mock(state, calls, live_state="running")` 多了 `live_state` 参数。

### 修因 J：短片 QC 采样点越界（源码已修复＋测试绿）
- **症状**：S1 只有 4 帧（duration 0.166667 s、interval 0.041667 s）。strict coverage 取 `0.82 × duration = 0.1367 s`，已经落在**最后一帧之后**；ffmpeg input seek 回 `rc=0` 且 **0 bytes**（不是报错），`_extract_identity_gray_frame` 于是抛 `Could not sample Character Swap identity region:`，已经渲染好的 `NN_save.mp4` 被判 failed。
- **修法**（`smart_render_worker.py`）：`_probe_frame_interval()`（avg_frame_rate，失败 0.0）、`_clamped_timestamps(duration, ratios, frame_interval)`（ceiling＝`duration − 2 × frame_interval`；interval＝0 时原样返回）、`_identity_sample_ladder()`（原值→0.9／0.75／0.5→0.0）、`_decode_probe_frame()`（5 个 stamp × 2 种 seek 变体，input-seek 先）。`_extract_identity_gray_frame`／`_extract_identity_rgb_frame` 改成委派，**错误讯息字串不变**；`inspect_character_swap_identity` 里 4 处时间戳（`(0.22,0.50,0.78)`、strict `(0.12,0.30,0.50,0.70,0.82)`、`mouth_timestamps`、`ambiguous_timestamps`）全部走 clamp，`frame_interval = max(plate, take)` 保证 source/result 同一组 stamp。
- 测试：`testing/test_smart_render_worker.py` **52 项全绿**，新增 `test_probe_helpers_keep_every_sample_decodable`、`test_identity_audit_survives_a_four_frame_character_swap_take`。
- **离线收口**：`working/_s1_audit_replay_20261026.py <seed…>` 对真实产物跑真 `inspect_character_swap_identity`，**逐 attempt 配对** `NN_source.mp4 → NN_save.mp4`（同目录还有 `master.mp4`；`00_`／`01_` 是 attempt 前缀，plate＝`NN_source.mp4`、take＝`NN_save.mp4`；97000854／97000874 只有 `00_source.mp4 + 01_save.mp4`，所以第一次 attempt 的 take 名叫 `01_save`，别再按「同号成对」猜）。结果：97000854 **sim 0.515343 accept**、97000874 **sim 0.467493 accept** ⇒ 与实机 manifest 逐位相同，修因 J 没改变任何评分行为；97000864 两个 attempt 都能跑完，返回 `action=retry_fresh_seed`、`source_plate_continuity_audit passed=False`、reason「output drifted away from the selected V1 Shot/plate」。

### 本轮测试总数（离线，一次跑完 165 项全绿）
`test_staged_model_driver` 24 ＋ `test_smart_render_worker` 52 ＋ `test_character_swap_engine`／`test_character_swap_closeup_gates`／`test_character_swap_silent_audio` 89 ＝ **165 OK，1 skipped**。跑法：`$env:PYTHONIOENCODING="utf-8"` 后用 bundled python `-m unittest testing.test_x`（**没有 pytest**）。渲染进行中不要跑整套。

### round 19 队列（seed 从 97000884 起）

| 顺序 | seed | Shot | 目的 |
|---|---|---|---|
| 1 | 97000884 | S10（R1→P1，silent，close-up） | 补 round 18 唯一没出片的一条；顺带给修因 I 第一次「走完 ComfyUI」的实机证明，对照 97000834／97000824 |
| 2 | 97000894 | S1（R1→P5） | 修因 J 的实机证明：4 帧 clip 的 QC 必须正常完成而不是抛异常；同时重抽用户 grading「完全不像」的那段 |

### 状态：务必分清「源码」与「视频」
- **源码已修复＋测试绿**：修因 I（driver cancel）、修因 J（QC clamp）。两者**都还没有实机产物**。
- **视频已实机验证**（累计）：close-up 用 `uhip` 能让 S7／S3 拿回 P1 五官与衣柜（97000824／97000854）；driver unload 的 409 自愈（attempt 2 成功，VRAM 26.69→4.05 GB）。
- **仍是假设**：`uhip` 对 S1／S10／S11 的相似度；年龄漂移；服装被强图案 plate 压过（根因 H，plate 躯干模糊**已否决**）；凭空面部毛发；背景蜂窝；silent listener 对嘴（S3/S6/S10 在 policy 57–60 一律 `dropped_tail_clauses=['close_up_silent_mouth']`，headroom 仅 ~188 字）；缺陷⑥ close-up 搬出衣柜面板。

### 本轮工具增补（离线，`working\`）
`_strata_states_live_probe_20261026.py`（把 host 真实 serving state 词汇钉成证据，附同名 `.log`）、`_s1_audit_replay_20261026.py`（真实产物 QC 回放，逐 attempt 配对）。

## 22. round 19 实机 + 修因 K（烧录字幕污染参考图）+ 缺陷⑥ 裁切锁 + 默认 preset 缓存 bug（2026-10-26 增补）

### round 19 实机结果（policy 60 / engine v5 / 0.5 MP，两条都走完 ComfyUI）

| seed | Shot | exit | similarity | 人眼 grading |
|---|---|---|---|---|
| 97000884 | S10 R1→P1（silent close-up，12 178 字，`dropped=['close_up_silent_mouth']`） | 0 | 0.5081 | **至今最好的脸**：圆框金属眼镜、细胡子、大眼大笑、黑帽红顶金带全到位，无年龄漂移；衣服＝源演员金色团花袍（根因 H 未解）；`silent_mouth_audit passed=False` |
| 97000894 | S1 R1→P5（speaker，10 653 字） | 0 | 0.615 | 卡通媒介与 medium 构图保住；脸＝「戴帽皱眉＋山羊胡」的真人味男人，与 P5 参考图本身一致 ⇒ 见修因 K |

修因 I 第一次拿到**实机**证明：attempt 1 `HTTP 409` → `cancel_requests=["req_89da1635"]` → attempt 25 `verified_clean=true`，VRAM 26.55 → 3.81 GB。修因 J 同时拿到实机证明：4 帧 S1 clip 正常产出 QC verdict，不再抛 `Could not sample Character Swap identity region`。看帧板 `_dsh_verify_9\round9_frames\{S10_uhip_P1_97000884,S1_uhip_P5_97000894}_*_board_20261025.png`。

### 修因 K：P5 是脏截图，不是干净角色图
P5 真身是一张播放器截图：左上标题「剧名：毒舌大壯」、底部两行硬字幕、右下 👍901 点赞 UI。engine v5 只做 alpha cut-out，脏截图（不透明）会整张进 sheet ⇒ H3 把白字与图标读成「角色设计的组成部分」，于是长出帽子、山羊胡和真人味。**结论：问题不在提示词，在喂进去的参考图。**

修法（`character_identity_sheet.py::suppress_burned_in_overlays`，engine v6）：只处理**不透明**输入，位置在 `compose_identity_sheet` 的 32 px 尺寸检查之后、`_segment_mask` 之前，全程 try/except 且结果写进 `notes`。条带＝上 20 %／下 13 %／左 10 %／右 16 %；判据＝近白（RGB 各通道 ≥240）连续行程 ≥2 px 且 ≤30 % 行宽；连删 9→5 px 光晕，两轮后 3.0 半径羽化；总删除 >8 % ⇒ 判定「图本身就是白的」，整体放弃并回报 `overlay hypothesis rejected`。常量：`OVERLAY_WHITE_MIN=240`、`OVERLAY_RUN_MIN_PX=2`、`OVERLAY_RUN_MAX_FRACTION=0.30`、`OVERLAY_ROUNDS=2`、`OVERLAY_HALO_DILATIONS=(9,5)`、`OVERLAY_BLEND_BLUR_RADIUS=3.0`、`OVERLAY_MAX_REPAIRED_FRACTION=0.08`。真图实测 P5 删 **1.306 %**、P6 **0.119 %**，P1／P3（透明 cut-out）跳过。落板图 `_dsh_verify_9\round20\*_decontam_land_check.png`。

### 缺陷⑥：close-up 把 sheet 衣柜面板整段搬进画面
97000854 的脸已合格，但画面里凭空多出垂手拳头、袍摆，桌子被抬高 ⇒ 违反 `do not widen the shot to reproduce the full-body reference`。新增 `CLOSE-UP SHEET CROP LOCK — MANDATORY`（`character_swap_engine.py`）：闸门 `face_dominant_closeup and reference_framing == IDENTITY_SHEET_FRAMING`，raw framing 与 medium 框不触发；位置在 `identity_sheet_contract` 之后、`apparent_age_lock` 之前；`CHARACTER_SWAP_TAIL_DROP_RANKS` 排名 3（`close_up_silent_mouth:1`、`medium_shot_silent_mouth:2`）。实测 sheet＋近景 silent = **12 258 字**（预算 12 320 内 ⇒ 可与 silent 条款共存），sheet＋近景 speaker = 10 272 字。policy **60→61**。注意：守卫回报的 `dropped_tail_clauses` 是**发射顺序**而非丢弃顺序 ⇒ 断言要用 `sorted()`。

### 顺带修掉：默认 preset 的 sheet 缓存从来没命中过
`_cached()` 原写 `int(payload.get("preset") or -1) != preset_index`，但 **preset 0 == `DEFAULT_SHEET_PRESET`，`or` 把 0 当缺失** ⇒ 每张默认布局 sheet 每次 Job 都重画。改成 `isinstance(payload.get("preset"), int)` fail-closed 守卫。只改校验、不改画面内容 ⇒ 不 bump 版本号。回归测试 `test_default_preset_cache_is_reused_then_invalidated_by_engine_bump`。测试素材注意：带烧录字的假图**永远不会**命中缓存（去污染会改变指纹），缓存测试要用 `make_figure`。

### 测试与状态
`test_character_swap_engine` **68**（+6 crop lock）、`test_identity_sheet` **39**（+9 去污染）、`test_smart_render_worker`／`test_staged_model_driver` 维持绿，四个核心文件 `py_compile` 通过。全量套件（`run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline`）log：`_dsh_verify_9\round20\logs\suite_policy61_decontam.log`。
**务必分清**：修因 K、缺陷⑥ 锁、preset-0 缓存 ＝ 源码已修复＋离线绿，**未实机验证**。round 19 两条片子都是 engine **v5**（未去污染、无 crop lock），所以两项目标都还没被证明。

### round 20 实机队列表（engine v6 + policy 61，seed 从 97000904 起，0.5 MP，链式 ps1，60 s 间隔）

| 顺序 | Shot | 目的 | 对照 |
|---|---|---|---|
| 1 | S1 R1→P5 | engine v6 去污染后 P5 是否不再长出真人味/帽子/山羊胡 | 97000894（sim 0.615，真人味脸） |
| 2 | S7 R1→P1 | crop lock 是否消除衣柜面板入侵且保住五官 | 97000854（sim 0.515343，有缺陷⑥） |

跑法：`python staged_model_driver.py run "<job.json>"`，前置 `working\_r18_precheck_20261026.py <seed…>`，看帧 `working\_board_seed_20261025.py <seed> <label> P1|P3|P5`；产物在 `...\preview\<seed>\segment_001_*\character_swap_pass_01_<R>\`（`NN_source.mp4` plate、`NN_save.mp4` take，编号不必相同）＋ `master.mp4`。

### 仍未解（round 20 之后的候选）
- 根因 H：强图案 plate 压过 sheet 衣柜 —— 唯一还没试的杠杆是 sheet 里的衣柜特写面板；plate 躯干「服装带」模糊**已否决**（`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` 出厂 `off`）。
- silent listener 对嘴：S3／S6／S10 在 policy 57–61 一律丢掉 `close_up_silent_mouth`，headroom 仅 ~188 字。两条候选 (a) 再压缩 ~200 字、(b) 全 attempt 都违反 silent 时改选 mouth motion 最小那条且不再标 failed —— **两条都要先问用户**。
- `target_reference_similarity`（0.458–0.615）与用户 grading 不相关，**只能人眼读帧**。

### 环境陷阱（新，别再踩）
`testing\test_director_timeline.py` = 238 项，**每项都会 spawn 一个 `design_ai_service.py` 子进程** ⇒ 单模块 2 小时以上。日常验证一律 `--skip test_director_timeline`（近期基线 `Ran 734/739/744/750/752`，failures=0 errors=0 skipped=10）。另外该模块需要 `testing\` 在 `sys.path` 上才能 `-m unittest test_director_timeline`，直接 `python -m unittest testing.test_director_timeline` 混在大套件里会出现一个 invocation-artifact error，不是真失败。

## 23. round 20 实机结果 + 修因 L／M／N + 缺陷⑦ + ComfyUI「新视频必崩」根因（2026-10-26 增补，policy 61→62）

### round 20 实机结果（engine v6 + policy 61 / 0.5 MP，两条都 `exit=0`）

| seed | Shot | attempts | similarity | verdict | 人眼 grading |
|---|---|---|---|---|---|
| 97000904 | S1 R1→P5（去污染后重跑，`prompt_chars 11 421`、`dropped=[]`） | 3 | 0.538173 → **0.602773**（attempt 2 被选）→ 0.597043 | `passed=false`，`retry_fresh_seed`，理由 `output drifted away from the selected V1 Shot/plate`（`source_plate_continuity_audit` 左右两条 similarity −0.195／0.0067） | 未读帧 |
| 97000914 | S7 R1→P1（crop lock 首跑，`prompt_chars 11 363`、`dropped=[]`） | 1 | 0.493088 | **`passed=true`／`accept`**，erasure／integration／plate 三项全过 | 未读帧 |

日志：`_dsh_verify_9\round20\logs\S1_97000904_P5_v6_driver.log`、`S7_97000914_P1_lock_driver.log`；成片 `...\cache\generated_outputs\preview\{97000904,97000914}\master.mp4`。两条提交的 prompt 都含 `CLOSE-UP FACE ANCHORING`／`CLOSE-UP MEDIUM REINFORCEMENT`／`CLOSE-UP SHEET CROP LOCK`／`APPARENT AGE LOCK`／`NO INVENTED TEXTURE OR PATTERN`，但**不含** `SOURCE COSTUME BELONGS…`（那是 policy 62 才加的）。⇒ 修因 K 与缺陷⑥ 已获实机**执行**，S7 已被 accept，但「不再长真人味」「衣柜面板不再入侵」仍需人眼读帧才能写「视频已实机验证」。

### 修因 L：背景长出蜂窝／龟裂图案
Relay 缩放把 plate 细小颗粒丢掉，模型自补装饰纹理，只在人物框外出现。`character_swap_engine.py:451-452` 新增 `BACKGROUND_EXTRA_MAX_BOX_AREA = 0.045`、`BACKGROUND_EXTRA_PROMINENCE_RATIO = 2.0`（使用点 `:842-843`）：框面积 <4.5 % 且背景显著度 ≥2 倍时判定「背景是自造的」，发射 `NO INVENTED TEXTURE OR PATTERN — MANDATORY`（`:1225`），闸门 `PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA = 0.060`（`:69`、`:1232`）。该条款与 `close_up_medium_reinforcement` 进**永不丢弃**白名单（回归 `test_medium_and_plate_texture_clauses_are_never_droppable`）；框很小时不必发（`test_a_lean_box_has_no_texture_contract`）。测试模块 `testing\test_character_swap_background_extra.py` = 9 项。

### 修因 M：silent listener QC 既漏判又误判
`smart_render_worker.py` 三处改动：① 嘴部取样点 `(0.12, 0.24, 0.36, 0.50, 0.64, 0.76, 0.88)`（`:1962`），判定值改走 `robust_temporal_frame_motion` 的 **median**（`:1273-1295`，mean 仍写进 `source_motion_mean`／`result_motion_mean` 供复核）；② 双重阈值：绝对上限 `maximum_motion = max(0.055, source*1.5+0.012)`（`:1984`）**且**上半脸参照 `upper_relative_limit = upper_face_motion*1.25+0.02`（`:1999-2000`），`violated = result > maximum_motion AND > upper_relative_limit`（`:2002`）⇒「只有嘴比眉眼动得多才算说话」；③ plate 条 `plate_motion < 0.010` ⇒ 该行 `audit_region_ambiguous`，全行 ambiguous ⇒ `identity_failed=False` + `plate_strip_ambiguous=True`（`:2129`），`target_similarity_failed` 同理降级 `target_similarity_ambiguous`（`:2137`）；④ 旁观者行改 `advisory`（`:1810`）并从 `retention_score` 剔除（`:1937`、`:1951`）。加固闸门在 `character_swap_engine.py:179-180`（0.050／0.25）。测试 `test_silent_mouth_transient_qc.py` 3 项、`test_smart_render_qc_advisory.py` 4 项。
**素材陷阱**：ffmpeg `drawbox enable=` 只求值一次 ⇒ 1 帧交替会被 2 帧网格的审计器读成恒定；用 `vstack` + `geq=lum='if(lt(mod(N,4),2),250,15)'`（见 `test_silent_mouth_transient_qc.py`）。

### 修因 N：衣服没换 + 角色变老
`character_swap_engine.py:1414` `SOURCE COSTUME BELONGS TO THE ERASED ACTOR — AUTHORITATIVE`；`:1700` `COMPLETE WARDROBE REPLACEMENT — MANDATORY` **无条件**发射（不再只在 close-up 分支）；`:1456` `apparent_age_lock` / `APPARENT AGE LOCK`，明写「不得漂成更老的人」；close-up 补 `:1186` `close_up_face_anchor`、`:1208` `close_up_medium_reinforcement`。

### 缺陷⑦：12 320 字预算 —— 第二次「写了却被丢」
新条款让 sheet＋近景 silent 到 13 072 字。改为显式丢弃优先级 `CHARACTER_SWAP_TAIL_DROP_RANKS`（`character_swap_engine.py:148-162`：`close_up_silent_mouth 1`、`medium_shot_silent_mouth 2`、`source_costume_leaves_plate 3`、`close_up_sheet_crop_lock 4`，算术推导见 `:139-148` 注释），守卫循环 `:1809-1847`，重复表述压缩后尾部 −301 字（13 072 → 12 771）。实测发出 12 245 字、`dropped=['close_up_silent_mouth']`、crop lock 存活（canary `test_shipped_budget_keeps_the_crop_lock_on_a_silent_sheet_closeup`）。

### 实机对照：black-shirt 单角色片同一 timeline，policy 61 vs 62
`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\`（**只有 manifest，没有 `.job.json`** ⇒ 要再跑得先在 Studio 按 Preview）：

| 项目 | policy 61 `preview_1516417359058198094` | policy 62 `preview_2448458047138852523` |
|---|---|---|
| 三段 verdict | 全 `passed=false`，理由 `selected region retains the V1 actor and the authored silent mouth is moving` | seg0 `false`／**seg1 `true`**／seg2 `false`，理由改 `authored Silent Listener mouth shows excessive articulation` |
| silent 审计行 | 每段 2 行：R1 0.2531／0.2003／0.2494 > maximum 0.1206／0.0801／0.2150；旁观者 0.1455／0.1413／0.0267 **从不**超标 | 每段 1 行（`advisory=false`）；seg1 `result 0.164414 > maximum 0.078027` 但 `< upper_relative_limit 0.178414` ⇒ 不判违反 |
| `selected_attempt` | 1／1／1 | 2／3／2（重试按「最像目标 P 图」排序） |
| `target_reference_similarity` | 0.501021／0.51596／0.52525 | **0.560221／0.53726／0.557678**（三段全升） |
| `prompt_budget` | 10 364／12 320，`dropped []` | 11 966／12 320，`dropped []` |
| `retention_score` | 0.84163／0.878907／0.791122（被旁观者灌水） | −0.262198／0.221604／0.157468（只剩目标） |
⇒ 修因 M 的 median＋上半脸参照＋advisory 降级在**真片**上确实改变了 verdict；但 seg0／seg2 是否真的对嘴仍未人眼确认。
**manifest 字段名（别再猜）**：`render_policy_version`、`segments[].attempts_used`、`segments[].character_swap_identity_audits[].{passed,reason,action,selected_attempt,roles[].advisory,source_role_id,target_media_id,target_reference_similarity,retention_score,quality_risk_score,plate_strip_ambiguous}`、`...silent_mouth_audit.rows[].{source_motion,result_motion,maximum_motion,source_motion_mean,result_motion_mean,upper_face_motion,upper_relative_motion_limit}`、`segments[].character_swap_passes[].{prompt_budget,reference_framing,live_action_adaptation,silent_audio_strategy,identity_sheet_head_coverage}`。**manifest 不含 prompt 正文** ⇒ 条款前后对比只能读 driver log。

### ComfyUI 阻断：新视频（R2V＋参考音频）必崩
`prompt id cd1a505b-dfb9-4cdc-8d35-bca2dd529e66` → ERROR node `125 SamplerCustomAdvanced`：`RuntimeError: The size of tensor a (3) must match the size of tensor b (2) at non-singleton dimension 0`，抛点 `C:\ai program\Data\Packages\ComfyUI-GPU-1\custom_nodes\comfyui-minimax-h3-turbo\__init__.py:235` `x = x + (bv @ (av @ sv.T)).T`，跑 135.52 s 才炸。
- 基座 `comfy\ldm\minimax\model.py`：`seg_t` 把 `ref_img` 钉在 `max(t_v, vis_aug)`、**`ref_audio`/`cond_audio` 钉在 `max(t_a, aud_aug)`**（`:678-683`）；`unique_t` 收集这两者＋segments＋mask 行（`:709-711`）；`PackedLayout` 给 `kind=="audio"`（`:414-417`）**和** `kind in ("video","video_audio")` 且 `rt>0`（`:423-430`）追加 `("ref_audio", rt*2)`，keyframes 追加 `("cond_audio", rt*2)`（`:392`）。
- 本机节点（mtime 2026-08-11，526 行，Manager 安装、无 `.git`）：`_unique_t(timestep, shift_v, shift_a, has_vis_cond)`（`:186-193`）**只**加 `max(t_v, 0.999)`；`has_vc = bool(payload.get("keyframes") or payload.get("refs"))`（`:375`）；闸门只有 `if st is not None:`（`:231`）⇒ 只要 payload 里有 audio ref 块就少一行。
- 离线证明 `working\_h3turbo_rowcount_sim_20261026.py`（log `_dsh_verify_9\round20\logs\h3turbo_rowcount_sim_20261026.log`）：σ=1.0 时 t_v=t_a=0 ⇒ 基座 `[0.0, 0.999, 1.0]` = 3 行 vs 节点 `[0.0, 0.999]` = 2 行，正是「a (3) vs b (2)」；后续步 4 vs 3；**只有 refs（无 audio）时每个 σ 都吻合** ⇒ 解释为什么 Character Swap／Relay 从不触发。
- 上游 `Larryvrh/ComfyUI-MiniMax-H3-Turbo` issue **#29** 已修；main 版已下载 `_dsh_verify_9\round20\upstream___init__.py`（553 行）：`_unique_t(timestep, shift_v, shift_a, payload)` 同时补视觉行（`payload["visual_cond_noise_aug"]`，默认 0.999）与音频行（`payload["audio_cond_noise_aug"]`，默认 1.0），另有 `adaln_t_table` 最近行查找与 `if st is not None and st.shape[0] == x.shape[0]`（`:249-251`）。差异约 −12／+39 行，只在 `_unique_t`、`_make_adaln_forward`、`_inject_adaln_egrid`。上游仍漏 `kind=="video_audio"` 音轨（靠 shape 闸门兜住）。
- 三个候选（**`C:\ai program\` 下任何改动都要先问用户**）：**B（推荐）** 只手补 `_unique_t` 补音频行（嗅 `kind in ("audio","video_audio")` ＋ keyframes 带 audio）＋ `st.shape[0] == x.shape[0]` 闸门，先备份到 `_backup\`，再重启 ComfyUI；**A** 直接换 upstream main（长期正确，但其 `adaln_t_table` 路径可能让 look 与既有基线偏移）；**C** Studio 侧在 Turbo LoRA 生效时断开 ref audio（会丢音色参考）。

### ComfyUI Turbo 节点补丁：方案 B 已执行（2026-10-26 19:31，用户批准「b」）
- 备份先做：`_backup\comfyui-minimax-h3-turbo___init__.py.20261026.bak`（24 895 B、SHA256 `65AE7F4B821B51D952ABF43931870D2C330160BEE3E4ECFCF080935D7EA27863`、原 526 行，与改前逐字相同）。被打断的文件现为 571 行、mtime 2026-10-26 19:31:49。
- 改动只三处：新增 `_cond_rows(payload)`（`:186-205`：视觉行 = keyframe `latent` 或 ref `kind in ("image","video","video_audio")`；音频行 = keyframe `audio_latent` 或 ref `kind in ("audio","video_audio")` 且 `ref_audio_t > 0`）；`_unique_t(timestep, shift_v, shift_a, cond)`（`:208-235`）改吃 **dict**（bool 仍向后兼容）并补 `max(t_v, payload["visual_cond_noise_aug"]=0.999)`（`:232`）＋ `max(t_a, payload["audio_cond_noise_aug"]=1.0)`（`:234`）；`_make_adaln_forward` 闸门改 `if st is not None and st.shape[0] == x.shape[0]:`（`:277` ⇒ 行数不合就跳过该 delta，而不是抛）。调用点 `us = _unique_t(ts, shift_v, shift_a, payload)`（`:421`），`has_vc`／`has_vis_cond` 已彻底消失。
- **刻意没采用**上游的 `adaln_t_table` 最近行查找重写：会改变 look，与既有 baseline 不可比。上游仍漏 `kind=="video_audio"` 音轨，本机靠 shape 闸门兜住。
- 离线证明（用 ComfyUI 自带解释器 `C:\ai program\Data\Packages\ComfyUI-GPU-1\venv\Scripts\python.exe`，AST 载入被改的 3 个函数，拿真 `PackedLayout`／`time_shift_sigma` 当基准）：`working\_h3turbo_rowcount_after_20261026.py`，log `_dsh_verify_9\round21\logs\h3turbo_rowcount_after_20261026.log` ⇒ 9 场景 × 8 σ = 72 组，**旧规则 24 组错行、补丁后 0 组**；真 torch 在失败形状上逐字复现 `The size of tensor a (3) must match the size of tensor b (2) at non-singleton dimension 0`，补丁后 `ok, out (3, 3)`；4/4 source check PASS。Character Swap／Relay（只有 picture ref）两规则都是 2／3 行 ⇒ 既有成功基线**零行为变化**。
- 节点级导入探针：`working\_h3turbo_import_probe_20261026.py`（同目录 `.log`，`exit=0`）在真 comfy 模块环境导入编辑后文件 ⇒ `NODE_CLASS_MAPPINGS` = `MiniMaxH3TurboLoRA` + `MiniMaxH3TurboSampler`，`_unique_t` 对新视频图 3 行、swap 2 行、裸 t2v 1 行。补丁文件 `py_compile` 通过（bundled python）。
- 已重启 ComfyUI（已获批准）：它由 **StabilityMatrix** 监管（`C:\ai program\StabilityMatrix.exe`）；动手前 `/queue` 空闲、VRAM free 30.51 GB。旧链 venv shim 16264 → base python 19968 结束后，用**逐字保留的原命令行**重启，新链 shim 10144 → base 26360（19:39:14 起，约 19:41 上线）。第一次重启输错参数引号 ⇒ `Start-Process -ArgumentList` 传数组会吞掉带空格路径内的空格（报 `can't open file 'C:\ai'`），**必须传单个字符串**。
- 重启后现状（本轮已复核）：`/system_stats` ⇒ comfyui `0.42.1`、`cuda:0 NVIDIA RTX PRO 4500 Blackwell`、VRAM total 31.83 GB／free 30.55 GB；`/queue` pending 0／running 0；`/object_info/MiniMaxH3TurboLoRA` 已注册（inputs `model,lora_name,strength,low_vram`）；启动 log `_dsh_verify_9\round21\logs\comfyui_restart_20261026\stdout2.log` 里 `IMPORT FAILED`／Traceback **0 次**，turbo 节点 0.0 s 导入。
- ⚠️ 要告诉用户：StabilityMatrix 界面可能把 ComfyUI 显示成 *Stopped*（进程是从外部起的），但 8189 实际活着。建议在 StabilityMatrix 里 Stop→Start 复位监管；补丁在 `custom_nodes\` 里，不会被这个动作弄丢。
- **补丁后尚未提交过任何 ComfyUI 任务** ⇒ 「新视频 R2V 能跑完」目前只是离线推断，**未实机验证**。

### 测试与状态
全量套件 `_dsh_verify_9\round21\logs\suite_policy62_registration.log`：**`Ran 842 tests in 242.682s … OK (skipped=10)`**（上一基线 801 ⇒ +41；`--stall 240 --skip test_director_timeline`）。分模块：`test_character_swap_background_extra` 9、`test_silent_mouth_transient_qc` 3、`test_smart_render_qc_advisory` 4、`test_character_swap_engine` 69、`test_identity_sheet` 39、`test_smart_render_worker` 52、`test_staged_model_driver` 25。六个核心文件 `py_compile` 通过。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29，`SMART_RENDER_POLICY_VERSION = 62`（`director_cut_studio.py:579`、`smart_render_worker.py:67`），`IDENTITY_SHEET_ENGINE_VERSION = 6`，`CHARACTER_SWAP_PROMPT_CHAR_BUDGET = 12320`。

### 状态：务必分清
- **源码已修复＋离线绿**：修因 L、M、N、缺陷⑦；ComfyUI Turbo 节点错行**已按方案 B 修补**＋72/72 行数吻合＋导入探针绿＋ComfyUI 已重启并注册正常。
- **已实机执行／已放行**：S7／97000914 `accept`；black-shirt policy 62 seg1 `passed=true`；policy 62 三段 similarity 全升、`selected_attempt` 不再恒为 1。
- **尚未实机验证**：蜂窝是否不再出现、衣服是否真的来自参考图衣柜、是否不再变老、seg0／seg2 是否真对嘴、S1 去污染后是否不再长真人味，**以及新视频 R2V＋参考音频能否跑完（补丁后一条任务都没提交）** ⇒ 全部**未实机／未人眼读帧**。

### 下一步（按性价比）
1. ComfyUI 补丁已落地并重启生效 ⇒ 下一步是**申请实机重跑**：新视频（R2V＋参考音频）在补丁后一条都还没提交过。
2. 人眼读 round 20 两支 `master.mp4`（`working\_board_seed_20261025.py <seed> <label> P1|P5`）。
3. black-shirt 需在 Studio 重按 Preview 才有 `.job.json`，之后才能用 `staged_model_driver.py run` 做 policy 62 的 L／N 验证。
4. 仍未解：根因 H（强图案 plate 压过 sheet 衣柜；`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` 出厂 `off`）；`target_reference_similarity`（0.458–0.615）与用户 grading 不相关，只能人眼。
5. 可选（未获批准）：`SheetPreset 9` 放大脸部面板 + 把脸主导的 close-up 路由过去（`director_cut_studio.py::_character_swap_identity_sheet_reference` `:34060-34127`，`IDENTITY_SHEET_CLOSEUP_PRESET = 8` 在 `:676-685`），届时 policy 62→63。

### 环境陷阱（新增，别再踩）
- **manifest 里没有 prompt 正文**，也没有 `policy_version`／`silent_mouth_rows` 这种键 ⇒ 用 `render_policy_version`、`silent_mouth_audit.rows[]`；先跑 `working\_manifest_keypaths_20261026.py` 看真实键路径。
- `apply_patch`：`*** Add File:` 路径不要加引号；最后一条 `+` 行与 `*** End Patch` 之间**不能有空行**（否则 `invalid hunk at line N`）。
- `rg` 里 `[^]]` 必须写 `\[[^\]]*\]`，Rust regex 不接受裸 `]`。
- PowerShell `Select-String` 混用 `"` 会被拆成位置参数 ⇒ 一律改 `rg -o -N '...'`。
- 长日志（driver log 单条 200 KB+）只 `Select-Object -First/-Last N`，需要细节就 dump 到 `_dsh_verify_9\roundN\`。

---

## 24. 「对话卡在 tool call」真相 + tray tool-call 看门狗（2026-10-26 增补）

**结论：不是卡住。**rollout 里那一条是 `payload.type=task_complete` 且 `last_agent_message` 以 `<tool_call>` 开头 —— turn **正常结束**，本地 Qwen/MTP 模型把工具调用写进**答案通道**而不是工具通道，Codex 没有可执行的东西就收了尾；工作没丢，所以敲「继续」必然接得上（现场 10 分钟那个 turn 的 gap 分析最长只有 110 秒，一直在干活）。

**已实机验证**（2026-10-26 23:22）：tray 新增 `Invoke-LeakedToolCallWatch`，重启后**第一个 tick** 就命中生产 thread `01a1531f…` 那条已静默 1958 秒的泄漏 turn，`codex queue` 成功，约 70 秒后该 thread 恢复跑 `exec_command`，全程零人工输入。tray 20336 → 2508，`h3_tray_actions.log` 留有 `leaked-tool-call wake: queued continue into thread …`。

**已排除的假设（别再走弯路）**：不是端点／路由问题。同一时刻同一模型各发 5 次带 tools 的请求 —— `POST 127.0.0.1:8931/responses`（Responses 前端，Codex `config.toml` 在用）与 `POST 127.0.0.1:47831/v1/chat/completions`（OpenAI 兼容前端，tray load/unload 在用）—— **10/10 返回结构化 `function_call` / `tool_calls`**（`finish_reason=tool_calls`），零泄漏。所以 `wire_api="responses"` 不必改，改 `chat` 没有证据更好。真实触发条件是上下文压力：82k token 输入、几十个工具、`model_reasoning_effort="high"`，加上 Qwen 系 `mtp`／speculative 变体解码丢 tool-call token（泄漏出来的工具名有时根本不存在，如 `read_code`、`read_file`，是在背 chat template）。频率实测 1/35、6/35、3/63 个 turn，间歇性。

**新代码**（`ai_libraries_common\director_studio_h3_status_tray\h3_status_tray.ps1`，现 1179 行）：

- 主函数 `Invoke-LeakedToolCallWatch`，挂在 `Update-H3TrayStatus` 末尾（ComfyUI 可用／不可用两条路径都会走到）；辅助 `Get-LeakedToolCallSessionsDir` / `Get-LeakedToolCallState` / `Save-LeakedToolCallState` / `Test-LeakedToolCallText` / `Read-JsonlTail` / `Get-LeakedCodexThreads`。
- 判定链：`%USERPROFILE%\.codex\sessions` 下 `leaked_toolcall_max_age_minutes`（180）内写过字的 `rollout-*.jsonl` → 倒查最后一个 `task_complete` → `last_agent_message` 以 `<tool_call` / `<tool_use` / `<toolcall` / `<function` / `<antml` / `<|` 开头（落在代码围栏内、或超过 4000 字符 ⇒ 判为正常回答，防误报）→ 该 turn 与日志文件**双双**静默 ≥ `leaked_toolcall_grace_seconds`（45，日志还在写就说明 thread 活着）→ Qwen 已加载 → `codex.exe queue`。
- 防噪音：`leaked_toolcall_state.json` 记 `threadId|turnId`（一个 turn 只叫醒一次、24h 清理、写盘限流 30s）；单 tick 最多叫醒 2 个 thread；`Invoke-AutoResume` 成功时写 `$script:autoResumeQueuedAt`，120 秒内看门狗不叠第二条消息；每个 thread 的 queue 各自 `try/catch`，一个 thread 不可达不影响其余。
- 配置（`tray-settings.json`，全部有默认值）：`watch_leaked_tool_call=true`、`codex_sessions_path=""`、`leaked_toolcall_grace_seconds=45`、`leaked_toolcall_max_age_minutes=180`。要关掉：写 `"watch_leaked_tool_call": false` 再菜单 **Restart Tray**。

**环境陷阱（新增）**：

- rollout `.jsonl` 被 app-server 持写句柄 ⇒ 只能 `[IO.File]::Open($p,'Open','Read',[IO.FileShare]::ReadWrite)`；`Get-Content` / `[IO.File]::ReadAllLines` 直接抛 *"being used by another process"*（62 MB 那份现场复现）。
- `task_complete` payload **没有** `thread_id`（只有 `token_usage_record` 有）⇒ thread id 从文件名取：`rollout-<date>T<time>-<threadId>[_<turnId>].jsonl`。
- 要在**不发消息**的前提下验证判定：AST 抽出那几个函数 + 把 `Resolve-CodexCli` 桩成 `$env:ComSpec`，用 **Windows PowerShell 5.1** 跑（tray 用 `powershell.exe`，不是 pwsh 7）；harness 留在 `%TEMP%\h3_tray_watch_test\watch_test.ps1`。注意 `$PSScriptRoot` 在 harness 里指向 temp，所以状态文件不会污染 tray 目录。
- 改完 `.ps1` 必须 Restart Tray 才生效（见 §18 坑六）。

**尚未验证**：调低 `model_reasoning_effort`／尽早开新 thread 能否真的降低泄漏频率（目前只是基于「短 prompt 10/10 干净、80k 上下文才漏」的推测，没做 A/B 统计）；多 thread 同时泄漏 >2 个时只做过单 tick 限流设计，没实机压过；看门狗在 Qwen 全程未加载（H3 独占期间）本就不动作，这条路径符合预期但没有独立取证。
---

## 25. tool-call 看门狗的三处加固（2026-10-26 深夜增补）

**动机**：§24 的看门狗实机命中过一次，但留下三个可诊断性／覆盖问题 —— (1) 日志里看不出它到底有没有 armed，「tray 完全不 auto-resume」无从下手；(2) `Test-LeakedToolCallText` 的 4000 字符天花板会把「泄漏的 tool call 参数很长」误判成正常回答（现场 `read_code` 带 `queries` 数组就超线）；(3) 想关掉只能手改 `tray-settings.json`。

**改了什么**（`h3_status_tray.ps1`，1179 → 1198 行，34 个函数，无重复函数）：

- 启动多打一行 `tool-call watchdog: armed (grace=45s, max_age=180min, codex_cli=found)`。以后先 grep 这行再怀疑判定链：`off` = 被人关过；`codex_cli=MISSING` = 找不到 `codex.exe`；显示 `armed` 却没动作，才轮到查 grace／written／状态键。
- 长度天花板 4000 → 20000 字符。真正的闸门是「前 24 字符前缀」＋代码围栏排除，长度只是挡 runaway dump，4000 太紧。
- 菜单新增可勾选项 **Tool-call watchdog**，点一下写回 `tray-settings.json` 的 `watch_leaked_tool_call` 并在日志记 `enabled`/`disabled`（handler 与 Auto-arbitrate 那条同构；`Write-TrayConfig` 本来就把整个 `$script:config` dump 回文件，所以新键自动持久化）。

**已实机验证**（23:54）：tray 2508 → 20288（`script_mtime=2026-10-26 23:52:43`），启动日志出现 `armed` 行；之后每 5s 一个 tick，无 `watch crashed`／`watch error`。生产 thread `01a1531f…` 那次 22:50:07 的泄漏 turn 已在 23:22:44 被叫过，`leaked_toolcall_state.json` 里 `threadId|turnId` 仍在 ⇒ 重启后**没有**再叫第二次，到 23:55 日志依旧只有 1 条 wake，且该 thread 的 rollout 仍在被写（说明它活着在跑，看门狗不该动）。

**顺带纠正 §24 一句话**：`task_complete` payload 的 `root_turn_id` 与 `turn_id` 实测**同值**（不是只有 `turn_id`），所以状态键不会退化成 `threadId|` 而变成「一个 thread 终身只叫一次」。

**环境陷阱（新增）**：这里给 `exec_command` 的内联 PowerShell 会被外层吃掉 `$变量`（`$_`、`$b` 都会凭空消失 ⇒ 语法错误）。凡是要用变量的 PS 命令，一律先 `apply_patch` 写成 `.ps1` 再 `powershell.exe -File`，只有完全不含 `$` 的一次行命令才直接写。UTF-8 文档追加用 `[IO.File]::AppendAllText`＋`UTF8Encoding($false)`，该 handoff 文件是**无 BOM**（首三字节 `35,32,77`）。

**尚未验证**：菜单勾选没实机点过（只做过 AST parse）；>20000 字符的真泄漏至今没见过实例，这条放宽目前是预防性的。

---

## 26. round 21 后续：Identity Sheet 脸面板被切在眼睛 → head-run 引擎 v7 ＋ 脸面板填满格子（2026-10-27 增补，policy 62→63、engine 6→7）

**用户 grading（black-shirt 单角色片，policy 62／engine v6 产物）**：S1／S4／S6／S8「衣服完全不像参考图」，S3／S7／S10／S11「角色变老人」（相似度 20 %–60 %，判不及格），只有 S5（80 %）可接受。

### 根因 O：脸面板是从眼睛以下才开始画的

`estimate_head_box` 量的是**整行**不透明范围。black-shirt P1 右手举在头侧（`x 204-250`，自 `y 76` 起），肩线因此落在 armpit，v6 head box = `(32, 5, 252, 92)`（220×87，宽高比 2.53；上限 `MAX_HEAD_BOX_ASPECT = 2.6` 拦不住这种扁带）。两层后果：

1. 脸面板里没有眉眼／眼镜／鼻子／胡子／下巴 ⇒ H3 只能自己发明五官 ⇒ **「变老人」**；
2. 衣柜面板从 `head_bottom` 起画，误差直接继承 ⇒ **「衣服完全不像参考图」**。

也就是说：这一轮不是 prompt 条款不够，而是**送进 H3 的参考图本身就没有那张脸**。§23 修因 N 加的 `APPARENT AGE LOCK` / `COMPLETE WARDROBE REPLACEMENT` 只能约束模型，不能补像素。

### 改了什么（`character_identity_sheet.py`，源码文件在**仓库根目录**，不在 `working\`）

- **head-run 引擎 v7**（`IDENTITY_SHEET_ENGINE_VERSION` 6 → 7）：头 = 与颅骨轴**相连**的那一段不透明行程，永不等于最宽行。`_head_run_walk()` 回传 `(seed_row, walked)`，`_head_run_landmarks(walked, seed_row)` 带 `skull_locked`。参数在 `:111-125`：`CROWN_SEED_SHARE 0.10`、`HEAD_RUN_BRIDGE_SHARE 0.12`、`HEAD_RUN_MAX_AXIS_SHIFT 1.10`、`HEAD_SEARCH_SHARE 0.62`、`HEAD_RUN_SHOULDER_VS_SKULL 1.05`、`HEAD_RUN_SHOULDER_VS_NECK 1.35`、`HEAD_RUN_NECK_CONFIRM_SHARE 0.92`、`MERGED_TORSO_RUN_SHARE 1.30`、`HEAD_HEIGHT_MIN_SKULL_SHARE 1.10`，行程用 `_OPAQUE_RUN_PATTERN = rb"[\x80-\xff]+"` 扫 alpha。
- **无 silhouette 的比例 fallback**：`peak_width >= max(2, (right-left)-2) and shoulder_row < 0`（不透明满幅、没有平坦背景）⇒ 取 0.34×主体高、宽 ≤ 1.15×H、居中，不再吐扁带。实测 300×420 渐变图：subject `(0,0,300,420)` → head `(69,0,232,142)`，hshare 0.34、宽高比 1.15。
- **脸面板填满格子**：正确 skull 框「高>宽」而 head 格「宽>高」，`_fit_into_cell` 只 contain-fit 不拉伸 ⇒ 脸在格子内再缩一次，`head_coverage` 0.304 → **0.194**，跌破 `character_swap_engine.py:188` 的 `IDENTITY_SHEET_MIN_HEAD_COVERAGE = 0.22`（两条既有测试当场红）。新增 `_grow_head_crop_to_cell()`（定义在 `_fit_into_cell` 之前）：横向以 `HEAD_PANEL_MAX_GROW = 1.45` 封顶、纵向 75 % 向下（`HEAD_PANEL_DOWNWARD_GROW_SHARE`，多出脖子／肩／领口这些**必须重画**的真实像素，下巴不动），只吃真实 artwork、不 upscale、不越 silhouette；调用点在 `compose_identity_sheet` 贴图循环 `if panel.slot == "head"`（`if panel.mirror` 之前），且 `raw_crop = crop`（原本存的是未生长的 `crops[index][0]`）。
- **居中分配**：`_balanced_growth_split()` 平分横向多出来的列，只有某一侧真的顶到画框才让位；剩下那一列由 `_column_artwork_scores()` 逐列覆盖率决定往哪边长（`strip.reduce((1, strip.height))` —— `reduce` 收的是**缩减因子**不是输出尺寸，这里踩过一次）。横向边界刻意用**画框** `x_bounds = (0, source.width)` 而不是 subject bbox：cut-out 旁边的空白和 sheet 底色同色，不是「发明背景」，而把侧向生长锁在 subject bbox 内正是把脸推出正中的原因。
- **本轮自己写出来的 bug（已修）**：`_balanced_growth_split()` 读 `span[1]` 当右边界，而调用方传的是 `(left, top, right, bottom)` ⇒ 右侧恒等于「没空间」，脸被推到最左。waving fixture：错的 `(0, 1, 197, 155)`；改读 `span[2]` 后 `(7, 1, 204, 155)`，脸中心 105.5 vs skull 中心 105。**教训：`(l,t,r,b)` 与 `(l,r)` 混用要用名字区分，不要靠 index。**
- **版本**：`SMART_RENDER_POLICY_VERSION` **62 → 63**（`director_cut_studio.py:579`、`smart_render_worker.py:67` 同步）—— 提交的**参考图本身**变了，policy 62 的 sheet／manifest／候选一律作废。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29，`CHARACTER_SWAP_PROMPT_CHAR_BUDGET` 仍 12320。

### 实测对照（9 张真 cast，探针 `working\_headpanel_fill_probe_20261027.py`，log `_dsh_verify_9\round21\logs\headpanel_fill_v71_probe_20261027.log`，落板图 `_dsh_verify_9\round21\sheets_v71\`）

| 素材 | head_coverage v6 → v7 | 脸面板 crop |
| --- | --- | --- |
| black-shirt P1 | 0.2435 → **0.3907** | `(32,5,252,92)` → `(7,1,203,153)`（196×152，右边界 203 < 袖管 204） |
| mustache-9 P4 | 0.5895 → **0.8544** | `(247,0,822,500)` → `(247,0,822,725)` |
| mustache-9 P5 | 0.3153 → **0.4314** | `(242,0,820,503)` → `(136,0,926,503)` |
| mustache-9 P6 | 0.1413 → **0.4297** | `(0,0,302,63)` → `(87,16,210,94)` |
| 其余 5 张 | 0.1989–0.2997 → 0.2868–0.3779 | 全部上升 |

人眼读过 black-shirt v7 落板图：脸面板完整含 crown → 眉毛 → 圆框眼镜 → 眼睛 → 鼻子 → 胡子 → 张嘴 → 下巴，右下角只有一小条蓝袖；body 面板是完整衣柜（黑马甲白滚边＋蓝袖＋蓝摆＋黄格裤＋黑鞋）。合成 fixture（`working\_wavetest_probe_20261027.py`）另证 head box `(37,1,173,155)`（136×154，a=0.88，袖管在外、下巴在内），coverage 0.3511（460×642）／0.3879（576×864）。

### 测试与状态

全量套件 `_dsh_verify_9\round21\logs\suite_policy63_headpanel_v7.log`：**`Ran 845 tests in 217.223s … OK (skipped=10)`**（上一基线 842 ⇒ +3；`--stall 240 --skip test_director_timeline`）。`test_identity_sheet` **39 → 42**，新增三项都在 `IdentitySheetEngineTests`：`test_head_box_ignores_an_arm_waving_at_head_height`、`test_face_panel_fills_its_cell_and_stays_centred`、`test_head_box_falls_back_to_proportions_without_a_background`（fixture `make_waving_figure`／`make_opaque_gradient_plate` 与模块级 `WAVING_*` 几何常量）。`test_character_swap_engine`＋`_closeup_gates`＋`_background_extra`＋`_silent_audio` **105 全绿**；引用 policy 版本符号的 `test_storyboard_segment_mapping` 绿（该套件引用符号不引用字面值，所以 bump 不需要改测试）。`character_identity_sheet`／`character_swap_engine`／`smart_render_worker`／`director_cut_studio` `py_compile` 通过。

- **源码已修复＋离线绿＋落板图已人眼确认**：head-run v7、比例 fallback、脸面板填满、`span[2]` 居中修正。
- **尚未实机验证**：black-shirt 三段 Character Swap 在 policy 63／engine v7 下**一条都没提交** ⇒ 「变老人是否消失」「衣服是否真的来自参考图衣柜」「蜂窝是否还在」全部仍未读新帧。恢复点 `_backup\character_identity_sheet.py.20261026_pre_headbox_v7.bak`。

### 下一步（按性价比）

1. **申请实机**：black-shirt 单角色片三段 Character Swap，走 `staged_model_driver.py run "<job.json>"`（先要在 Studio 里按 Preview 才有 `.job.json`）。engine v7 的 sheet 会由 Studio 自动生成，**不要手改 project 缓存**。
2. 读新帧时按「脸panel 是否被完整复制」判，不看 `target_reference_similarity`（0.458–0.615，与 grading 不相关）。
3. 仍未解：根因 H（强图案 plate 压过 sheet 衣柜，`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE` 出厂 `off`）；根因 L 蜂窝仍未实机；ComfyUI Turbo 补丁后新视频 R2V＋参考音频仍一条没跑过（§23）。

### 环境陷阱（新增，别再踩）

- 被改的引擎在**仓库根目录**（`character_identity_sheet.py`），`working\` 只放探针脚本；用 `Select-String -Path working\character_identity_sheet.py` 会直接 `Cannot find path`。
- `rg --glob` 才是 PowerShell 下的写法：`rg -n --glob "testing/*.py" PATTERN`；写成 `rg -n "PAT" testing\*.py` 会被当成单个路径并报 `os error 123`。
- 改生长／分配这类几何函数时，先跑 fixture 探针把 crop 坐标打出来再断言居中：本轮 `span[1]`/`span[2]` 那种错位**不会让任何既有测试变红**（fixture 两侧都是空白像素，coverage 数值一模一样），只有打印坐标才看得见。

## 27. round 22 实机：脸已修好＋三个残留缺陷 → round 23：medium 构图改用单脸 sheet（2026-10-27 增补，policy 63→64）

### 实机结论（black-shirt 单角色片，policy 63／engine v7，用户按 Preview）

Job 已被 Studio 自行消费（`job.json` 不在，manifest 保留）：`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_5946797166534131206_1793032633899288000.manifest.json`。关键字段：`render_policy_version 63`、上传的 sheet `image_137_4bd41c9e363a8278_nobg_identitysheet00_a0066_**v7**.png`、`identity_sheet_head_coverage 0.3907`（源图 0.214413）、3 段／576×864／12.86 s／0.5 MP、每段 3 次尝试、`prompt_chars 11966 / char_budget 12320`、**`dropped_tail_clauses []`**。逐帧证据：`_dsh_verify_9\round22\round22_policy63_v7_master_grid.png`（探针 `working\_round22_newvideo_frames_20261027.py`；ffmpeg 在 `C:\ffmpeg\bin\ffmpeg.exe`；**分段 mp4 拼好后会被清掉，评分要从 `generated_preview.mp4` 取帧**）。

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 脸（根因 O） | ✅ **已实机修复**：三段都是整张脸 —— 秃顶＋三根头发、额头纹、圆框眼镜、大鼻、八字胡、张嘴、下巴；卡通媒介保留，身份＝P1 | 12 帧人眼读过 |
| 衣柜（根因 H） | ❌ 仍是源 plate 的粉红黑条纹袍 | prompt 没丢字 ⇒ 只能在**视觉**上加码 |
| 缺陷⑧ 二次小人 | ❌ **新缺陷**：4/12 帧（每段首帧）左下多一个穿 P1 真衣柜的 chibi | 模型读对 body 面板，却当第二个实例 |
| 粉红假发 | ❌ seg0／seg2 保留，seg1 没有 | 头发／头饰归属条款缺口 |
| Silent Listener | ❌ 三段 `silent_mouth_excessive_articulation`（0.196／0.218／0.262 vs 0.055） | QC 数字可信，人眼也对 |
| `target_reference_similarity` | ⚠️ 0.588／0.614／0.554，与 grading 不相关 | **不要用它评分** |

### 缺陷⑧／②的开关：布局只由「抑制闸」决定，medium 构图从来拿不到授权

round 22 的 R1 框（manifest `identity_audit.source_bboxes_normalized`）是 `[0.35, 0.15, 0.65, 0.45]`：h 0.30／area 0.09。close-up 闸要 area ≥0.72 或 h ≥0.75，medium-silent 闸要 h ≥0.35 且 area ≥0.12 ⇒ **两道闸都没命中**，所以这个 Shot 提交的是 preset 0（两张脸＋全身）。离线用同一条 Shot 重排三种布局（`working\_round23_preset8_medium_sheet_20261027.py` → `_dsh_verify_9\round23\sheets\`）：

| 布局 | 脸数 | head coverage | 衣柜面板 |
| --- | --- | --- | --- |
| preset 0（round 22 实发的） | **2 张脸** | 0.3907 | 全身小人，衣柜只占下半一小块 |
| preset 8＋`outfit_view=medium` | **1 张脸** | 0.5259 | 脖子以下**齐胯**裁切，黑背心白滚边／蓝短裤／黄格纹都在 |
| preset 8＋`outfit_view=close_up` | 1 张脸 | 0.6023 | 断在白腰带**上方**，正是 round 17 丢掉可辨认行的高度 |

文件名带 `_uhip`／`_uchest` 标记，布局可直接从名字读出。

### 改了什么（源码，均在仓库根目录）

- `director_cut_studio.py`：新增 `_pass_spec_framing_medium_rows(pass_spec, min_height)` —— 框高 ≥ 门槛、面积 ≥ `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_AREA = 0.04`、且未被 close-up 闸接管 ⇒ 该 Shot 也用单脸＋hip 衣柜面板。**不看 `performance_mode`**（medium-silent 闸要静音是在保护嘴，这里是在数「画面容不容得下第二个人」）。`_character_swap_identity_sheet_reference` 里 `framing_rows` 只在另两闸都为空且门槛 > 0 时才查，命中就 `outfit_view = "medium"` 并强制 preset 8。
- 旋钮 `H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT`：**默认 0.0＝关闭**（默认行为与 policy 63 逐字相同），本轮要试的值是 `0.18`。
- `DESIGN_ENV_RENDER_KNOBS` ＋ `apply_design_ai_env_render_knobs()`（import 时执行）：allowlist 里的渲染旋钮也从 `design_ai.env` 读，**真实环境变量优先**、非 allowlist 忽略。没有这一步，按 Preview 的导演永远碰不到这些开关（`load_design_settings` 只管 LM Studio 设置，不注入 `os.environ`）。
- **布局决定进 manifest**：pass 记录新增 `identity_sheet_preset`／`_preset_requested`／`_preset_forced`／`identity_sheet_outfit_view`／`_outfit_view_override`／`identity_sheet_closeup_gate_rows`／`identity_sheet_medium_silent_rows`／`identity_sheet_framing_medium_rows`（round 22 只能从上传文件名反推）。
- `SMART_RENDER_POLICY_VERSION` **63 → 64**（`director_cut_studio.py`／`smart_render_worker.py` 同步）。VERSION 仍 `0.3.8-alpha.3`，Format 29，`CHARACTER_SWAP_PROMPT_CHAR_BUDGET` 仍 12320。

### 测试（离线）

`testing\test_character_swap_closeup_gates.py` **20 → 30**：`DesignEnvRenderKnobTests`（allowlist 安装＋忽略非 allowlist＋真 env 优先＋缺档空装）、`IdentitySheetFramingLayoutTests`（round-22 框逐字回放：旧闸全漏、framing 闸命中；sliver／远景／close-up／畸形输入不触发；门槛 0／-1／1.5／None／"abc" 不炸；默认 0.0 仍是 preset 0 两张脸；0.18 时 preset 8＋medium；close-up 旧行为不变）。stub 要点：`resolve_identity_sheet` 返回的 `sheet_path` **必须真的落盘**，否则 `_character_swap_identity_sheet_reference` 会退回 `illustrated_full_design`（第一轮就红在这里）。相关 6 模块 **183 全绿（skipped=1）**；`py_compile` 全过；全量套件 `Ran 855 tests … OK (skipped=10)`（845 → 855，log `_dsh_verify_9\round23\logs\suite_policy64_framing_sheet.log`；watchdog `--stall 240 --skip test_director_timeline`）。

### 状态界定（照例分开讲）

- **已实机验证成功**：engine v7 的 sheet 让 H3 **整张复制脸部**，「变老人」这条在 black-shirt 三段上消失；卡通媒介保留。
- **源码已修复＋离线绿＋落板图人眼确认、尚未实机**：medium 构图改用单脸＋hip 衣柜 sheet（policy 64）、manifest 布局记录、`design_ai.env` 渲染旋钮。
- **仍未修复**：衣柜漂移（根因 H）、缺陷⑧ 二次小人、粉红假发归属、silent 对嘴。

### 下一步（要许可）

1. **单一变量实机**：`design_ai.env` 加 `H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT=0.18` → 重启 Studio → 按 Preview。plate 不动（`source_identity_strategy: original`）、timeline 不动，唯一变量是 sheet 布局。读帧只看两件事：**左下还有没有第二个小人**、**衣服是不是 P1 的黑背心＋蓝短裤＋黄格纹**。
2. 过了再考虑 `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE=blur`（保留色度的躯干模糊；`blur_desat` 历史上会把灰衣服交给 Relay，所以出厂 `off`）。
3. 然后：头发／头饰归属条款、silent 对嘴。

### 2026-10-27 01:35 增补：knob 已装进 `design_ai.env`，顺手拆掉两处「测试依赖真实 config」的耦合

用户回报「已经按了 Preview」，但磁盘上 black-shirt 最新 take 仍是 **01:02:50 的 policy 63 manifest**（`preview_5946797166534131206_…`），`director_cut_studio.py` 的 policy 64 改动是 01:17 才落地 ⇒ **policy 64 至今零个实机 take**。ComfyUI 只读检查：`/queue` running=0 pending=0、`vram_free 26.07 GB`（GPU 空、Qwen 不在卡上）。当时的 Studio 进程是 00:2x 启动的，import 时 `design_ai.env` 里还没有 knob ⇒ 就算再按一次 Preview 也还是 preset 0。**knob 在 import 时读取，所以必须完全关闭 Studio 再重开。**

- **已写入 `design_ai.env`**（文件末尾，带注释）：`H3_IDENTITY_SHEET_MEDIUM_FRAMING_MIN_HEIGHT="0.18"`。allowlist 已有这个键，Studio 重开后 GUI Preview 与 staged driver 都会走单脸布局。要回滚就把这行删掉或写 `0.0`。
- **耦合 1（`director_cut_studio.py`）**：threshold 解析从 import 期的 `try/except` 抽成 `_identity_sheet_framing_medium_min_height(environ)`。之前那条「默认就是 0.0」的单元测试其实在断言**这台机器的 config 档**：knob 一写进 `design_ai.env`，全机器每个 import Studio 的进程（含测试）都变成 0.18，测试立刻假红。现在测试用空 mapping 证明出厂默认 0.0，另用 import 时的 environment 快照证明常量确实跟着 knob 走。
- **耦合 2（`testing\test_identity_sheet.py`）**：`_fake_studio()` 的 `SimpleNamespace` 缺 `_pass_spec_framing_medium_rows`。门槛为 0 时调用点被短路，所以 policy 64 当天全绿也没发现；knob 一开就 `AttributeError`。stub 现在挂上真实的 unbound 实现（和它挂 `_identity_sheet_head_coverage` 同一写法）。
- **测试**：`test_character_swap_closeup_gates` **30 → 31**（新增 `_identity_sheet_framing_medium_min_height` 的 knob 解析与 junk／-1／1.5／None／"" 夹取）。带 knob 的 7 模块 `Ran 214 tests … OK (skipped=1)`（log `_dsh_verify_9\round23\logs\env_knob_0p18_regress3.log`）；全量套件带 knob `Ran 856 tests … OK (skipped=10)`（207 s，log `_dsh_verify_9\round23\logs\suite_policy64_knob_on.log`）；`py_compile`：`director_cut_studio`／`smart_render_worker`／`character_identity_sheet`／`character_swap_engine`／`identity_sheet_page` ＋ 两个测试模块全过。
- **状态不变**：policy 64 的 medium 单脸 sheet 仍是「源码已修复＋离线绿＋三张落板 sheet 人眼确认」，**未实机验证**。等用户重启 Studio 并按 Preview 后，按上面第 1 条读帧 grading，帧图放 `_dsh_verify_9\round23\frames\`。

### 2026-10-27 03:05 增补：真元凶＝`save_design_settings()` 会吃掉 `design_ai.env` 的 advanced 键；布局授权搬进 Identity Sheet 页面

**实机状态：round 23 至今一次都没跑到（不是失败，是没跑）**。02:27:00 的新 take（`preview_197804093403812434_1793037707269261700.manifest.json`，0.5 MP、12.86 s、3 段、每段 3 次尝试）上传的 sheet 仍是 `image_137_4bd41c9e363a8278_nobg_identitysheet00_a0066_v7`、`identity_sheet_head_coverage 0.3907` ⇒ 与 round 22 **同一个 preset 0 布局（两张脸）**。ComfyUI 只读检查 `/queue` running 0／pending 0。

**为什么 preset 0**：`design_ai.env` 里已经没有 knob —— 文件 mtime 01:39:47、`Select-String IDENTITY_SHEET_MEDIUM_FRAMING` 零命中。原因在 `design_settings.py`：`save_design_settings()` 用 `KEYS` 重新生成整个文件，**不认识的行整行删除**，所以任何一个 settings 对话框点保存（`director_cut_studio.py` 11399／13004／13090／25595／26052 都会调用）都会把 knob 吃掉。这就是「明明写过又消失」的答案。manifest 里 `render_policy_version: 64` 说明那次 take 的 job 是 policy-64 代码写的（Studio 永远在 job 里打自己的常数，见 33825／35658／36286；worker 只在 hand-built job 缺字段时才回填 64，见 4904／4972／5049／5100），也就是 Studio **确实**重启过 —— 只是重启时 knob 已经不见了，threshold 仍是 0.0。

**顺带纠正上一轮的推断错误**：manifest 缺 `identity_sheet_preset*` 字段不能当作「进程是旧的」的证据。pass 记录过滤器 `if decision_value is None or decision_value in ("", 0): continue` 会把 `identity_sheet_preset = 0`（＝出厂布局）和 `identity_sheet_outfit_view = ""`（＝没有衣柜面板）当成空值丢掉，所以 round 23 的 A/B **根本无法从 manifest 验收**。这条比 knob 更毒，因为它让"看起来没记录"和"确实没生效"长得一模一样。

**本轮改动（源码）**

1. `design_settings.py`：新增 `_advanced_design_env_lines()`；`save_design_settings()` 现在先把页面不认识的赋值行读出（保持原顺序、同键取最后一次）再原样附回，并在段首加一行说明注释。页面拥有的键仍由页面决定：残留的同名行不会遮蔽页面值（测试用 `H3_DESIGN_TIMEOUT=1` 验证只剩一条且等于页面的 240）。注释行不 round-trip，避免每次存盘堆积过期说明。
2. `director_cut_studio.py`：**GUI 即授权**。`_character_swap_identity_sheet_reference()` 里 threshold 改成局部变量 `framing_threshold`：默认仍取 `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_HEIGHT`（出厂 0.0），但当用户在 Identity Sheet 页面**主动**选了 `IDENTITY_SHEET_CLOSEUP_PRESET`（8）时，自动改用新常数 `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_HEIGHT_WHEN_CHOSEN = 0.18`（定义在 `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_AREA` 之后）。于是 `framing` 闸（高 ≥0.18、面积 ≥0.04、未被 close-up 闸接管）会授权 medium Shot 用 preset 8＋hip 衣柜面板，而宽景（框高 <0.18）仍保留整身面板。`self.identity_sheet_preset` 是实例状态、按 Preview 现读 ⇒ **不再需要 `design_ai.env`，也不再需要为了 knob 重启 Studio**。回滚＝常数改 0.0。
3. **manifest 自证**：决策键过滤器改成只跳过 `None`，新增 `identity_sheet_framing_threshold`。`smart_render_worker.py`／`character_swap_engine.py` 都不读这些键（纯诊断），`queue_character_swap_passes()` 除 `workflow` 外原样保留 pass 行，所以字段能到 manifest。
4. 测试（新增 4 项，全离线）：`test_design_engine.test_save_preserves_advanced_keys_and_never_duplicates_them`；`test_character_swap_closeup_gates.test_round22_shot_choosing_the_single_face_layout_gets_the_hip_crop`（threshold 0 也要拿到 hip 裁切、`framing_threshold=0.18`、不写 `preset_forced`）与 `test_wide_shot_choosing_the_single_face_layout_keeps_the_whole_figure`（框高 0.10 ⇒ preset 仍 8 但 `outfit_view=None`）；`test_identity_sheet.test_framed_reference_records_the_layout_even_when_it_is_preset_zero`。三模块 `Ran 216 tests … OK (skipped=2)`（log `_dsh_verify_9\round23\logs\round23_advanced_keys_and_dropdown_gate.log`）；全量套件 `Ran 860 tests … OK (skipped=10)`，207 s（log `_dsh_verify_9\round23\logs\suite_policy64_advanced_keys.log`）；`py_compile`：`design_settings`／`director_cut_studio`＋3 个测试模块通过。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29，policy 仍 64（本轮不改 Relay 编译规则）。

**下一轮验收口径（缺一律算无效 A/B）**：manifest 出现 `identity_sheet_preset: 8` ＋ `identity_sheet_framing_threshold: 0.18` ＋ `identity_sheet_framing_medium_rows ≥ 1`，且上传 sheet 文件名含 `identitysheet08` 与 `_uhip`（离线 coverage ≈0.526，见 `working\_round23_preset8_medium_sheet_20261027.py`）。用户侧操作只有：完全关闭 Studio → 重开（这一次才需要重启，因为要载入本轮新代码）→ Identity Sheet 页面勾上 `AUTO-COMPOSE WHEN PICTURE 1'S FACE IS TOO SMALL`、Layout 选 `8 - Head + neck-down figure (single face)` → Save → Preview 0.5 MP。也可以让我用 `staged_model_driver.py` 直接跑（headless 载入工程＋`set_identity_sheet_settings(True, 8)`＋建 job），不碰 GUI 也不改项目文件。

**状态**：本轮全是「源码已修复＋离线全绿」；**policy 64 的 medium 单脸 sheet 仍未实机验证**。round 22 的四个残留缺陷（衣柜来自源 plate、第二个 chibi、粉红假发、silent 对嘴）全部还没重新 grading。

## 28. round 23 实机出片：二次小人已消失；衣柜／假发仍是源 plate ＝ plate 没被削弱（2026-10-27 03:26，policy 64→65）

### 先补上 §27 缺的那一半：布局决定进不了 Job

`_compiled_character_swap_window_job()` 在把 Character Swap pass 序列化进 Job 时只白名单了两个 coverage 键，所以 `identity_sheet_preset` / `framing_threshold` / `framing_medium_rows` 就算在内存里算对了也**永远不会出现在 Job 与 manifest**里。修法：

1. 新增模块常数 `IDENTITY_SHEET_DECISION_KEYS`（紧跟 `IDENTITY_SHEET_FRAMING_MEDIUM_MIN_HEIGHT_WHEN_CHOSEN`，约 line 790）：head／source coverage、preset、preset_requested、preset_forced、outfit_view、outfit_view_override、closeup_gate_rows、medium_silent_rows、framing_medium_rows、framing_threshold、reason。
2. 新增静态方法 `DirectorCutStudio._identity_sheet_decision_rows(pass_spec)`（`_compiled_character_swap_window_job` 之前，约 line 35263）：**只跳过 `None`**，preset 0 与 `outfit_view=""` 都是有意义的答案必须留下。
3. pass 行改成 `**self._identity_sheet_decision_rows(pass_spec)`（仅当 `reference_framing == IDENTITY_SHEET_FRAMING`）；identity audit 那个小字典仍保留自己那两份 coverage 拷贝（刻意如此，所以该方法里还有两处 `identity_sheet_head_coverage` 字面量是正常的）。
4. `_character_swap_framed_reference()` 里的决策拷贝循环改成遍历同一常数，以后加字段不会再只改一处。
5. `SMART_RENDER_POLICY_VERSION` **64 → 65**（`director_cut_studio.py:639`／`smart_render_worker.py:77`）；没有任何比较逻辑读这个数，它只是钢印。

测试：`test_identity_sheet` 新增 `test_the_decision_rows_survive_being_serialized_into_the_job`、`test_the_window_job_forwards_the_whole_decision_row`；三模块 `Ran 130 tests … OK (skipped=1)`；全量 `Ran 862 tests … OK (skipped=10)`（`_dsh_verify_9\round23\logs\suite_policy65_decision_row.log`）；`py_compile` 全过。

### 离线 Job 构建器（用户选的路线 b）

`working\_build_blackshirt_preview_20261027.py <SEED> [PRESET] [MEGAPIXELS]`：进程内载入 black-shirt 项目 → 设 `identity_sheet_enabled=True` / `identity_sheet_preset` → `window._build_smart_render_job(request_kind="preview", …)` 编出**真** Job → 打印每个 `identity_sheet_*` 字段 → 强制验收（`preset==8`、`framing_threshold==0.18`、`framing_medium_rows>=1`、sheet 名含 `identitysheet08`）。不合格 exit 1，杜绝「又跑了一轮无效的 A/B」。构建 log：`_dsh_verify_9\round23\logs\build_preset8_job_923000127_policy65.log`（VALIDITY OK）。

### 实机结果：round 23 第一次真跑成（seed 923000127，policy 65）

`staged_model_driver.py run` 全程正常：unload-qwen `verified_clean`（24.7→2.56 GB）→ wait-comfy → 三段 → `comfy-free ok` → tray 把 Qwen 载回。manifest `preview_923000127_1793041137147319300.manifest.json`：`render_policy_version 65`，三段上传的都是 `..._nobg_identitysheet08_uhip_a0066_v7.png`，每条 pass 行都带 `identity_sheet_preset 8`／`framing_threshold 0.18`／`framing_medium_rows 1`／`identity_sheet_head_coverage 0.5259`／`source_head_coverage 0.214413`／`reason "cached"` ⇒ **§27 的三条验收口径全部命中，这轮是有效实验**。

读帧（探针 `working\_round23_blackshirt_frames_20261027.py`，输出 `_dsh_verify_9\round23\frames\r23_p65_*_923000127*.png`；每段 4 帧共 12 帧，另有左下区专项 grid 与 V1 对照）：

| 项目 | 结论 |
| --- | --- |
| round 22 缺陷「左下第二个 chibi 小人」 | **已实机消失**：12/12 帧都没有第二个角色（round 22 是 4/12）⇒ medium 单脸 sheet 对这个缺陷＝**视频已实机验证成功** |
| 脸的归属／媒介 | 没退步：12/12 帧是 P1 卡通脸（秃头＋三根毛＋圆眼镜＋翘胡子＋圆鼻），仍是卡通，没真人化、没变老人 |
| round 22 缺陷「衣柜来自源 plate」 | **仍在 12/12 帧**：仍是源片的粉黑条纹＋网眼＋飘带 cosplay，不是 P1 黑背心＋蓝短裤＋黄格纹袜 |
| 粉红双马尾假发＋猫耳 | **仍在**：头套属源演员，与衣柜同一根因 |
| silent listener | seg1／seg3 QC `silent_mouth_excessive_articulation`（similarity 0.584／0.560），seg2 QC 通过（0.601） |

### 根因：送进 Relay 的 plate 完整无损

R1 框 `[0.35,0.15,0.65,0.45]`（高 0.30／面积 0.09）**低于全部身份抑制闸门**，worker log 里没有任何 suppression 记录 ⇒ H3 看到的是一帧原封不动的 V1。它因此只换脸：头发与衣服的轮廓＋色度是最强的像素条件，prompt 压不过它。证据链：

- `prompt_chars 11966 / char_budget 12320`、`dropped_tail_clauses []` ⇒ `COMPLETE WARDROBE REPLACEMENT — MANDATORY` 和 `…WARDROBE…AUTHORITATIVE` 两条**都确实送出去了**（worker log 内可读到原文）。
- `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE`（`director_cut_studio.py:672-683`，用在 `_character_swap_identity_suppressed_source`，line 34699）**已实现但默认 `off`**，而且 `WARDROBE_GATES = {"dominant","head_dominant"}` ⇒ 0.09 的小框永远进不到那条分支。
- 历史测量（S4 seeds 97000314/344/324/334）：`blur_desat` 会把色度抽干（饱和度 160→103）并长出medallion／extra vest；`blur` 保留色度但当时仍留 sash。⇒ 下一步用 `blur`，不要 `blur_desat`。
- sheet 侧还有个结构性小问题：`OUTFIT_VIEW_SHARES = {"close_up":0.34,"medium":0.62}`（`character_identity_sheet.py:64`），medium 的衣柜面板只到 `source_crop y=153..288`（源图 252×370），**黄格纹袜／鞋子基本被切掉** ⇒ 下半身服装没有参考权威。

### 下一轮单一变量（需要用户批准实机）

让 wardrobe band 不再只服务近景闸门：cartoon P（`live_action_adaptation=false`）且框面积 ≥0.06 时也启用 `blur`（只软化衣物边缘、保留色度），对照组＝seed 923000127，除 band 外全部冻结。若仍留 cosplay，第二档才考虑把 `medium` 的 share 从 0.62 提到接近 1.0（把袜子/鞋纳入衣柜面板），代价是 head coverage 下降、脸部权威变弱，需单独一轮。**在 band 生效之前，不要动 `OUTFIT_VIEW_SHARES`。**

**状态（本轮结束时）**：
- **源码已修复＋离线全绿**：policy 65 的决定行序列化、GUI 布局授权、`design_ai.env` advanced 键保命。
- **视频已实机验证成功**：medium 单脸 sheet（preset 8 + `_uhip`）修掉「第二个小人」；脸仍是 P1、媒介仍是卡通。
- **仍未解决（实机确认仍存在）**：衣柜来自源 plate、粉红假发／猫耳、seg1／seg3 silent 对嘴超标。
- 遗留杂项：`render_jobs\preview_923000127_1793040911358430700.job.json`（policy 64 的第一次探针构建）是无害重复，留着。

## 29. round 24 源码修复：prompt 闸门与 plate 抑制闸门脱节 ⇒ 「说了削弱、其实没削弱」（2026-10-27 03:55，policy 65→66，**尚未实机验证**）

### 证据（真实 worker log，不是推断）

`logs\staged_model_driver\preview_923000127_1793041137147319300.jo_20261027_030359.log`：

| 计数关键字 | round 23（policy 65，实机） | round 24 离线 Job（policy 66） |
| --- | --- | --- |
| `MEDIUM-SHOT SILENT MOUTH REINFORCEMENT` | 19 | 3（每段 1，逐段检查） |
| `COMPLETE WARDROBE REPLACEMENT` | 19 | 3 |
| `SOURCE PLATE FACE BLURRED` | **0** | 3 |
| `identity_suppressed`（plate 档名 token） | **0**／3 段全是 raw V1 plate | 3／3 段 plate 换成 `…_identity_suppressed_…_silent_*.mp4` |
| pass 行 `source_identity_strategy` | 无 | `medium_silent_listener_identity_suppressed` ×3 |
| 参考图 sheet | `…_identitysheet08_uhip_a0066_v7.png`，coverage 0.5259，`reason "cached"` | **同一片、bytes 不变** |
| `prompt_chars` | 11966 | 11901 |

⇒ round 23 是「prompt 声称 plate 削弱过、H3 实际收到完整无损的 V1」，所以它只肯换脸，头发与 cosplay 整套跟着源 plate 留下来。这不是猜测：三条上传 plate 的档名里根本没有 `identity_suppressed`。

### 根因：同一件事的两道闸门阈值不一致

- Relay 引擎侧（会发 prompt 条款）早已放宽：`character_swap_engine.py:179-180` → `SILENT_REINFORCEMENT_MIN_BOX_AREA = 0.050`、`SILENT_REINFORCEMENT_MIN_BOX_HEIGHT = 0.25`。
- Studio 侧真正决定「要不要改图」的 `_pass_spec_medium_silent_blur_rows()` 还写死 `width*height >= 0.12 and height >= 0.35`。
- black-shirt 这条 Shot 的 R1 框 `[0.35,0.15,0.65,0.45]`＝面积 0.09／高 0.30 ⇒ 落在 0.050–0.12 与 0.25–0.35 的空隙里 ⇒ **只发条款、不动图**。

### 改了什么（只碰 plate 闸门，其余冻结）

1. `director_cut_studio.py` 导入块（约 line 194）补进 `SILENT_REINFORCEMENT_MIN_BOX_AREA` / `SILENT_REINFORCEMENT_MIN_BOX_HEIGHT`。
2. 新增 `_medium_silent_blur_min_framing(environ=None) -> (area, height)` ＋快照常数 `CHARACTER_SWAP_MEDIUM_SILENT_BLUR_MIN_AREA` / `…_HEIGHT`（紧跟 `CHARACTER_SWAP_IDENTITY_MASK_MODE` 块，约 line 704）。knob：`H3_CHARACTER_SWAP_MEDIUM_SILENT_MIN_AREA` / `H3_CHARACTER_SWAP_MEDIUM_SILENT_MIN_HEIGHT`；**逐组件**容错（一个值坏掉只回退那一个到引擎档位）；成对写 `0.12 / 0.35`＝精确回到修复前。
3. `_pass_spec_medium_silent_blur_rows()`（约 line 34533）改读常数；docstring 同步。注意它与 `_pass_spec_framing_medium_rows()` 是互斥关系（约 line 34297：`not closeup_rows and not medium_rows`），所以 silent 行一旦成立，medium framing 行主动让位 ⇒ 离线构建器的验收改成 `framing_medium_rows + medium_silent_rows >= 1`（`working\_build_blackshirt_preview_20261027.py` 已改）。
4. `SMART_RENDER_POLICY_VERSION` **65 → 66**（`director_cut_studio.py:656`／`smart_render_worker.py:86`）。VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。

### 测试与离线验证

- `testing\test_character_swap_closeup_gates.py`：新增 `test_medium_silent_gate_defaults_to_the_engine_silent_tiers`、`test_medium_silent_gate_knob_rolls_the_plate_back`、`test_round23_medium_box_gets_a_blurred_head_band`、`test_round22_box_silenced_also_hits_the_aligned_suppression_gate`；旧断言 `test_round22_medium_box_gets_framing_rows_but_no_silent_rows` 改名重写为发言者 spec 版本（`…_without_any_silence`）。回滚用 `patch.object(studio_module, "CHARACTER_SWAP_MEDIUM_SILENT_BLUR_MIN_AREA/…_HEIGHT", …)` 测。
- `test_character_swap_closeup_gates`＋`test_identity_sheet` **82 OK**；`test_character_swap_engine` **69 OK**；全量 **Ran 866 tests OK (skipped=10)**（`_dsh_verify_9\round24\logs\suite_policy66_medium_silent_gate.log`）；`py_compile` 全过。
- 离线 diff 探针 `working\_round24_policy66_plate_diff_20261027.py` ⇒ `DIFF OK: plate suppressed, prompt describes it, reference unchanged`（log `_dsh_verify_9\round24\logs\policy66_plate_diff.log`）。第一次跑失败是因为探针从 `segments[i]` 顶层读 strategy；正确位置是 `segments[i]["character_swap_passes"][j]`，已修（注意 Job 里没有 `prompt` 键，条款只在真 worker log 里出现）。
- 新 Job：`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923000227_1793043950705503000.job.json`（seed **923000227**，policy 66，VALIDITY OK）。
- 备份：`_backup\V0.3.8-alpha.3_policy66_medium_silent_gate_20261027\`＋`ROLLBACK.md`（真正的运行时回滚是那两个 env knob；最近的完整源码快照是 `_backup\V0.3.8-alpha.3_blackshirt_roles_silent_wardrobe_pre_fix_20261026`＝policy 61）。

### 实机结果（seed 923000227，policy 66，2026-10-27 07:38）＝方向正确、部分修复

`staged_model_driver.py run` 全程正常（unload-qwen `verified_clean` → wait-comfy → 三段 → comfy free → tray 载回 Qwen）。**plate 真的上了线**：manifest `identity_suppressed` 18 次、每段 1 个 suppressed plate 上传；`logs\staged_model_driver\preview_923000227_…_073804.log` 里 `SOURCE PLATE FACE BLURRED` ×11、`identity_suppressed` ×25，对照 log（923000127）两项都是 **0**。三段 `attempts_used=3`、`status complete`。

探针 `working\_round25_blackshirt_grade_20261027.py`（帧图 `_dsh_verify_9\round25\frames\`，log `_dsh_verify_9\round25\logs\grade_round25_policy66.log`；每段 4 帧共 12 帧，另出 wardrobe／head／bottom-left 裁切与 V1 对照）：

| 口径 | policy 65（923000127） | policy 66（923000227） |
| --- | --- | --- |
| ① 衣柜是否换成 P1 | 0/12 | seg2 4/4＝黑背心白滚边＋蓝衣＋**黄格纹袜＋黑鞋**；seg0／seg1 仍是 cosplay ⇒ **4/12 换上** |
| ② 粉红假发／猫耳 | 12/12 仍在 | seg0＋seg2 全消失、seg1 仍在 ⇒ **8/12 消失** |
| ③ 第二个小人 | 0/12 | **0/12（没复发）** |
| ④ silent 对嘴 | seg2 过、seg1／seg3 不过 | **三段都不过**（result/source motion 0.287/0.063、0.229/0.071、0.213/0.080）⇒ 这项**变差** |
| 脸／媒介 | 12/12 P1 卡通 | 12/12 P1 卡通，无真人化／老人漂移 |
| `target_reference_similarity` 平均 | 0.5685 | **0.5955**（0.597／0.621／0.569，三段都涨） |

**读法**：模糊头部带把「源演员头部像素」这个最强条件削弱之后，头套／头发这类**头部权威**立刻倒向 P1（8/12），最干净的 seg2 甚至把衣柜＋袜子＋鞋子整套跟过来；但 seg0／seg1 的**躯干**仍由 cosplay 主导 ⇒ 说明残余权威已从头部转移到躯干，而不是 prompt 无效。因此下一个变量应该打在衣物带上，不要再动头部带（头部带已证明有效且没有长出第二个小人）。

若衣柜仍不跟（按优先级）：① `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE=blur`，并把 `WARDROBE_GATES`（约 `director_cut_studio.py:34757`）从 `{dominant, head_dominant}` 扩到含 `medium_silent`（cartoon P 才扩）；**永远别用 `blur_desat`**（会灰化并凭空长衣服，见 S4 seeds 97000324／334）。② 把 `OUTFIT_VIEW_SHARES["medium"]`（`character_identity_sheet.py:64`，现 0.62）往 1.0 提，让黄格纹袜／鞋进入衣柜面板，代价是 head coverage 下降（`IDENTITY_SHEET_MIN_HEAD_COVERAGE = 0.22`）。③ 模糊带始终只到头部（`PLATE_TORSO_BAND_BOTTOM = 0.45`）：62 % 的躯干带曾让 H3 自己长出年龄＋戏服（`character_swap_engine.py:1272-1284`）。

## 30. round 26：衣著带扩到 medium-silent，但「两条条款」会挤掉静音条款 ⇒ 合并成一条 847 chars（2026-10-27 15:40，policy 66→67，**源码已修复＋离线全绿，实机未跑**）

### 沿着 §29 的①往下走，但撞上预算墙

§29 的实机已经量化了「只糊头部」：假发／头套 8/12 被 P1 取代、相似度三段都涨（0.5685→0.5955），但衣柜只 4/12 换上（只有 seg2 整套跟过来）。结论是**方向有效、作用范围只到肩膀**，所以本轮照 §29 建议①把衣著带扩给 `medium_silent`。真正卡住的是预算：

| 配置 | 编译后 chars（真实 budget **12320**） | dropped tail clauses |
| --- | --- | --- |
| `off`（＝policy 66） | 11901 | 无 |
| `blur`，head 带＋衣著带**分开两条**（初版） | **12758** | 长度守卫丢掉 `MEDIUM-SHOT SILENT MOUTH`（525 chars）→ 12231 |
| `blur`，合并 978 chars | 12419 | 仍超 99 |
| **`blur`，合并 847 chars（现况）** | **12288** | **无 ⇒ 两条 silent 口型条款都在** |

衣著条款实价 **+857 chars** ⇒ 「修衣柜」会把「修静音」挤掉，两者互相抵消。所以本轮不是简单加条款，而是**把 head 带与衣著带合并成一条**（header `SOURCE PLATE HEAD AND WARDROBE BLURRED — AUTHORITATIVE:`），并把 `CHARACTER_SWAP_TAIL_DROP_RANKS` 里两条无效 key 换成单一 `"plate_wardrobe_silent_clause": 0`（最先被牺牲；衣著义务已由无条件 `COMPLETE WARDROBE REPLACEMENT` 承担，静音口型条款别无替补）。

### 改了什么（只碰 medium-silent 的 plate 语义）

- `director_cut_studio.py`：`CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE` + `_medium_silent_wardrobe_band_mode()`（env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`，`off|blur|blur_desat`，默认 **blur**）。全部 gate row 都是 `medium_silent` 时才启用；策略尾码 `_wardrobe_blur_suppressed`，plate cache token v7。
- `character_swap_engine.py`：`plate_wardrobe_silent_clause` 只在「有衣著带 且 策略含 `medium_silent` 且 **不含** `dominant`」时生成，命中即把 `plate_wardrobe_blurred_clause` / `plate_face_blurred_clause` 清空 ⇒ plate 在 prompt 里只被描述一次。措辞随模式：blur ⇒ `its colours survive while no collar line, seam or drape resolves`；desat ⇒ `below the shoulders it is a neutral grey template`。**近景大脸（dominant）路径完全没动**。
- `SMART_RENDER_POLICY_VERSION` **66→67**（两档同步）；VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。
- 回滚：运行时 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off`；源码快照 `_backup\V0.3.8-alpha.3_policy67_silent_merged_band_pre_run_20261027\`（四模块＋ROLLBACK.md）。**policy 67 的「两条分开写」初版没有快照**，因为它是已证明的坏交易。

### 测试

`test_character_swap_engine.py` +5（合并条款唯一且 <900 chars；两条旧条款必须消失；两条 silent 口型条款共存且排在合并条款之前；blur/desat 措辞不互串；`dominant` 不合并；**budget＝实测字数字节-1 时唯一被丢的是合并条款**——别用 budget=1，会把所有 ranked 条款丢光）⇒ **74 tests OK**。`test_character_swap_closeup_gates.py` +5（knob／回滚／优先级）⇒ **42 tests OK**（同一 test 内不要建第二个 `DirectorCutStudio()`：`subprocess.run` 已 fake ⇒ `detect_ace_step_runtime` 炸）。六档目标组合 **180 tests OK**；全量套件在 `_dsh_verify_9\round26\logs\suite_policy67_merged_silent_band.log`（基线 866，新增 5 ⇒ 预期 ~871）。

### 离线探针与 dump

`working\_round26_policy67_wardrobe_band_budget_20261027.py`（`H3_PRECHECK_BUDGET` / `H3_PRECHECK_OUT` 可覆盖）；log `_dsh_verify_9\round26\logs\policy67_merged_clause_compressed_budget_probe.log` verdict **OK**；prompts `_dsh_verify_9\round26\prompts_merged2\`。条款长度参考（mode=blur）：soundscape tail 9026、author template 3262、IDENTITY SHEET 1134、MULTI-PERSON 991、SILENT LISTENER 965、**合并 plate 847**、DESIGN-SHEET 785、NO INVENTED DETAILS 746、SILENT SUMMARY 669、COMPLETE WARDROBE 609、MEDIUM-SHOT SILENT MOUTH 525、APPARENT AGE 480、NO INVENTED TEXTURE 428。

### 状态与下一枪（**未取得批准，不得开跑**）

「源码已修复＋离线绿」≠「视频已实机验证」。要验的是（a）衣柜能否在**三段全部**换成 P1（policy 66 是 4/12）；（b）silent 对嘴能否回到阈值下（policy 66 三段全败 0.287／0.229／0.213，源 0.063／0.071／0.080）。提议 seed **923000327** 一族：`staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\<新 job>.job.json"`，跑完用 `working\_round25_blackshirt_grade_20261027.py` 读帧对比（wardrobe／head／bottom-left + P1 + V1）。

### silent 对嘴的另线索（**另一变量，勿混入本轮**）

已排除音频因素（silent plate `audio_stripped`）与措辞因素。新证据：identity sheet preset 8 的头部面板**本身就大笑张嘴**（`...\cache\identity_sheets\image_137_4bd41c9e363a8278_nobg_identitysheet08_uhip_a0066_v7.png`）⇒ 头部一带糊掉就由「张嘴 sheet」主导 mouth。下轮候选：闭嘴 head 变体，或 QC 阈值校准。

### 环境备忘（本轮踩过的）

- bundled Python 实路径 `ai_libraries_common\python_env\python.exe`（接手档写的 `python\_env\` 是错的）。
- 跑 Python 前先 `$env:PYTHONIOENCODING="utf-8"`（cp1252 会崩）；Qt 相关加 `$env:QT_QPA_PLATFORM="offscreen"`；`rg` 不可用 ⇒ 用 `Select-String`。
- 全量 `discover` 曾卡死在 audio-separator（log 冻结在 spawn `audio_separator_server.py` 那一刻）。这次没卡；若再卡：用明确 module 列表排除 `testing.test_audio_separator*` 并注明环境因素。
- 本机残留：多个 `design_ai_service.py`（测试泄漏）＋ `audio_separator_server.py`；ComfyUI（port 8189）在跑；GPU 先前状态 Qwen loaded、ComfyUI queue free。

## 31. round 30–31：head 带已长过假发，衣著带却停在普查框 ⇒ policy 69 把布带长到脚（2026-10-27 19:44，policy 68→69，**源码已修复，实机未跑**）

### 实机结论（black-shirt 单角色片，policy 68，seed 923001027，master `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\cache\generated_outputs\preview\923001027\master.mp4`）

| 项目 | 结果 |
| --- | --- |
| 头部仍是 P1 卡通（glasses／mustache／bald pate），不变老人、不真人化 | ✅ 三段都 OK |
| 身体／衣服换上 P1 | ✅ 明显改善（seg0 蓝袍下摆＋黄格纹大腿＋黑球鞋；seg1 黑白滚边背心；seg2 蓝袖＋黑背心。policy 67 同 Shot 全是 V1 粉黑条纹袖） |
| 头发／头饰换掉 | ❌ 仍失败：V1 黑猫耳皇冠＋镶金／宝石头带仍在（seg0／seg1 直接压在 P1 光头上，比 p67 更明显＝局部退步）；假发残留且跨段变色（粉／黑／粉） |
| 背景／路人 | ✅ 无蜂窩；R2 绿衣戴帽路人保留（seg2 t≈10 s 有一个灰色糊人物） |
| QC | seg0 sim 0.6187 passed、seg1 0.5529 passed、seg2 三次重试后 `silent_mouth_excessive_articulation` failed（取最佳 0.5904）；MEAN 0.5873（p67 同结构 0.5664／0.6045／0.5722 ⇒ 无退步） |
| manifest | uploaded 只有 2 件：**Picture 1 = `image_137_..._nobg_identitysheet08_fullfig_a0066_v8.png`（fullfig）** ＋ **Video 1 = 抑制后的 plate mp4** ⇒ 抑制带确实作用在模型看的动态影片上；budget 12210/12320 `dropped=[]` |

### 根因（读 Job 里的 `identity_suppression_geometry`，不是推断）

两条带都由 AI 角色普查的 thumbnail box 推出来：本 Shot 的 box 是 `[0.35, 0.15, 0.3, 0.3]` ⇒ head 带 (0.30, 0, 0.4001, 0.285) ＋ wardrobe 带 (0.30, 0.285, 0.4001, 0.165)，`suppressed_frame_area = 0.18`。但 V1 的假发＋猫耳＋粉黑条纹袖＋长裙实佔 x0.10–0.90 / y0.03–1.0（≈60 % 画面）。**框外的袖、裙、腿在 plate 里依旧锐利**，Relay 照抄；prompt 再怎么写「Picture 1 决定整套衣著」都输给一张没削弱的图。

### 改了什么（只碰 plate 几何，strategy 名称与 prompt 条款选择完全不动）

- `director_cut_studio.py`：`SMART_RENDER_POLICY_VERSION` 68→69。新增 `_figure_extent_parameters()`（env `H3_CHARACTER_SWAP_FIGURE_EXTENT`=0 回滚、`_WIDTH_SHARE`=1.75、`_MAX_WIDTH`=0.80、`_BOTTOM`=1.0、`_MAX_AREA`=0.56、`_MIN_PIECE_WIDTH/HEIGHT`=0.06）、`_subtract_protected_boxes()`（精确矩形相减，碎片互不重叠）、`_figure_extent_band_boxes()`（候选宽度按 1.0／0.8／baseline 递减，先扣 protected box，丢掉 <0.06 的碎片，含 head 带的总面积超 cap 就整套退回 policy-68 baseline）。
- 衣著带由单矩形改成多矩形，`kind` 仍是 `wardrobe` ⇒ **prompt 零增量**（预算已经顶到 12210/12320，加一句话就会掉静音条款，见 §30）。geometry 新增 `figure_extent{parameters, applied}` 与 `wardrobe_reaches_bottom`。
- `smart_render_worker.py`：`SMART_RENDER_POLICY_VERSION` = 69。
- `character_swap_engine.py`：merged silent plate 条款依 `wardrobe_reaches_bottom` 写 `crown to feet`／`crown to hips`（两串同长 ⇒ 预算不动）；缺该 key 的旧 geometry 仍写 `hips`。

### 离线几何取证（不碰 GPU）

探针 `working\_round31_figure_extent_geometry_20261027.py 923001027`（只建 Job＋建 plate，输出 `_dsh_verify_9\round31\`）。三段都：`chars=12210/12320 over=False dropped=[]`；strategy 名不变；bands 三条 ⇒ head (0.30,0,0.4001,0.285) 0.114 ＋ wardrobe (0.30,0.285,0.48012,0.715) 0.3433 ＋ wardrobe (0.21998,0.45,0.08002,0.55) 0.044 ⇒ **`suppressed_frame_area = 0.5013`（p68＝0.18）**；`wardrobe_reaches_bottom=true`；prompt 出现 `crown to feet`。

ffmpeg A/B（`_dsh_verify_9\round31\plate_ab_t2.png`／`plate_ab_t3.4.png`／差异图 `plate_diff_t2.png`／feather mask `plate_mask_p69.png`）判读：差异**只**落在新带 x0.22–0.78、y0.45–1.0；画面右侧背景 x>0.78 与绿衣摄影师 R2（protected box `[0.15,0.25,0.3,0.45]`）在两张 plate 里都保持锐利 ⇒ 没有把旁觀者糊掉，也没有 round-14「糊整面墙→背景长蜂窩」那种硬边。

### 测试

`python -m unittest discover -s testing -t testing -p "test_character_swap_*.py"` ⇒ **141/141 OK**（本轮新增 9 项：`_figure_extent_parameters` 预设值／env 回滚／junk 退回预设；`_subtract_protected_boxes` 100×100 逐格铺满且碎片零重叠、protected 完整抠除；area cap 退回 policy-68 baseline；engine `crown to feet`/`hips` 与 `wardrobe_reaches_bottom` 一致且字串等长）。py_compile：`director_cut_studio.py`／`smart_render_worker.py`／`character_swap_engine.py`／`character_identity_sheet.py`／`staged_model_driver.py` 全通过。备份 `_backup\V0.3.8-alpha.3_policy68_fullfigure_hairhalo_pre_run_20261027\ROLLBACK.md`。

### 状态界定（照例分开讲）

「源码已修复＋离线几何取证」＝policy 69 的 band 与措辞一致、旁觀者不被吞、面积有上限。**「新视频已实机验证」尚未成立**：还没跑过任何 p69 的 ComfyUI 生成。

### 回滚开关

`H3_CHARACTER_SWAP_FIGURE_EXTENT=0`（p69→p68 plate）、`H3_CHARACTER_SWAP_HAIR_HALO=0`、`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off|blur|blur_desat`、`H3_IDENTITY_SHEET_OUTFIT_VIEW=medium`。desat 变体会诱发灰衣（round-14 S4 证据），刻意**不**跟面积扩张混在同一枪。

### 下一枪（**未取得批准，不得开跑**）

一条命令：`staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\<p69 job>.job.json"`（job 由 `_round31` 探针或 Studio Preview 0.5 MP 产出）。判读沿用 `working\_round26_blackshirt_grade_20261027.py`（新 seed／tag `p69fig`），四指标：① 髋以下是否换成 P1 格纹裤＋黑球鞋；② 猫耳皇冠＋镶金头带是否消失；③ 头是否仍是 P1 卡通（不变老人／真人）；④ 有无第二小人或背景乱图案。

### 环境备忘（本轮新增）

- ffmpeg 两个 input 时 `-frames:v 1` 是 **output** option，写在两个 `-i` 中间会被当成第二个 input 的 input option ⇒ `exit -22`。正确写法：`-ss T -i A -ss T -i B -filter_complex "...[out]" -map "[out]" -frames:v 1 out.png`（filter 末端一定要自己贴 label，`-map "[a][b]"` 会报 `Output with label 'a' does not exist`）。
- `_subtract_protected_boxes`／`protected_source_roles` 吃的是 `source_bbox_normalized`，即 **(x1, y1, x2, y2)**，不是 width/height；写成 width/height 会被当成退化框直接跳过（测试曾这样踩过一次）。

## 32. round 32：policy 69 实机——抑制面积 0.18→0.5013 确实把衣柜抢回来，但 blur 保留轮廓与色相 ⇒ 头饰照抄；锚点变少 ⇒ seg1 身份跑飞（2026-10-27 21:03 实机 seed 923001027，**视频已实机验证＝部分有效**）

### 送达证据（不是「只写进 prompt」）

- job／manifest：`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923001027_1793100745085992400.{job.json,manifest.json}` ⇒ `render_policy_version=69`、`megapixels=0.5`、`final_model_release="ComfyUI models and VRAM released"`。
- 三段 mp4 的 mtime 落在 **20:46–21:03**，是这一枪全新重生成的档，不是复用上一轮（已用 mtime 逐一比过）。
- driver log `_dsh_verify_9\round31\driver_p69fig_run.{out,err}.log`：`unload-qwen → verified_clean → wait-comfy → smart_render_worker → /free`，实测 VRAM 释放约 1.5 GB，跑完 Qwen 由 Tray 自动载回。**没有**出现「Qwen 与 ComfyUI 同时在卡上」。

### 几何落地（离线取证，不碰 GPU）

- 三段都是 `suppressed_frame_area=0.5013`、`wardrobe_reaches_bottom=True`、bands=3（head 0.114 ＋ wardrobe 0.3433 ＋ wardrobe 0.044）、prompt `chars=12210/12320`、`dropped=[]`、strategy 名不变。
- ffmpeg A/B（`_dsh_verify_9\round31\plate_ab_t2.png`／`plate_ab_t3.4.png`／`plate_diff_t2.png`／`plate_mask_p69.png`）：差异**只**落在 x0.22–0.78、y0.45–1.0；绿衣戴帽摄影师 R2（protected box）与右侧背景 x>0.78 在两张 plate 里都锐利 ⇒ 抑制没有吞掉旁观者。

### QC（`character_swap_identity_audits`）

| 段 | 选中 attempt | `target_reference_similarity` | silent 口型 | 判定 |
| --- | --- | --- | --- | --- |
| seg0 0–4.288 s | 2 / 3 | 0.6081 | 0.239 | **通过** |
| seg1 4.288–8.576 s | 3 / 3 | 0.5163 | 0.165 | **通过** |
| seg2 8.576–12.864 s | 2 / 3 | 0.5319 | 0.290 | **通过** |
| MEAN | — | **0.5521** | — | 三段全过（policy 68 是 2/3） |

对照：p68 MEAN 0.5873、p67 是 0.5407、p66 是 0.5955 ⇒ **silent 首次三段全过，但相似度没有进步**。

### 读帧四指标（9 帧，`_dsh_verify_9\round31\frames_p69fig\`，一次出 master／head／wardrobe／bottom-left 四张 grid；探针 `working\_round31_p69fig_grade_20261027.py`）

1. **髋以下的 P1 黄格纹＋黑球鞋：7/9 帧出现**（policy 68 只有 seg0 有）——本轮真正的进步。但 V1 的粉黑条纹袖仍在；seg2 的短裤变成自创青绿微格纹；t12.3 退回黑色蜂巢 mesh。
2. **V1 黑猫耳冠＋镶金宝石头带：6/9 帧仍在**（t0.6／2.0／3.4／9.6／11.0／12.3）⇒ 相对 policy 68 **没有改善**。
3. **头部仍是 P1 卡通：6/9**；但 **seg1 t5.0／6.6 整段跑飞成棕发、无眼镜的另一张卡通男脸，t8.0 变灰发老人** ⇒ 同一段内身份漂移，这是本轮新增的缺点。
4. 背景：无第二小人、无蜂窝；R2 绿衣戴帽摄影师全程锐利。

### 判读（为什么「扩面」没有顺手把头饰解决）

- blur 只削细节、**保留轮廓与色相** ⇒ 大尺寸高对比头饰（黑＋金＋粉）的**轮廓本身**被模型照抄下来，糊不糊领口跟它无关。
- 抑制面积从 0.18 扩到 0.50 之后，plate 里剩下的身份锚点变少 ⇒ 身份方差上升：seg1 用满 3 次重试、region3 连续度只有 0.276。
- 所以「抑制面积」是同一个旋钮的两端：面积越大 ⇒ 衣柜越像 P1、但身份越容易飞。**不要再继续加大面积**，下一步应该换「保留什么」而不是「保留多少」。

### 状态界定（照例分开）

- **源码已修复**：policy 69 的 band 几何、prompt 措辞一致性、旁观者相减、面积上限——`test_character_swap_*` **141/141**、四模組 `py_compile` 全绿（本轮未改核心源码，故未重跑单测）。
- **视频已实机验证**：p69 这一枪已跑完并读帧。结论＝**部分有效**（衣柜 ↑ 7/9、头饰 ✗ 未改善、silent 三段首次全过、seg1 身份新缺点）。

### 下一枪（**未取得批准，不得开跑**）

单一变量：几何与 prompt 完全不动，只把 medium-silent 的 plate 模式改成去饱和——`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur_desat`。

- 源码里早已存在、从未在 medium 路径启用（`WARDROBE_SATURATION=0.25`）；round-14 的 S4（seeds 97000324／97000334）用过灰模板配方，**要盯的副作用就是「衣服变灰／自己发明衣物」**。
- env 名字别搞混：medium 路径是 `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`，close-up 那套是 `H3_CHARACTER_SWAP_WARDROBE_BAND_MODE`，两者互不影响。
- job 已经在项目 `render_jobs\` 内（探针直接写进去的），seed 923001027 的输出目录会被覆盖 ⇒ 想保留 p68／p69 对照，先把 `_dsh_verify_9\round31\frames_p69fig\` 另存。
- 一条命令：`staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\<desat job>.job.json"`。

### 文档回填（本轮一并做）

- `CHANGELOG.md` 已回填此前漏登记的 **Round 30／29／28／27／25**（当时直接从 Round 31 跳到 Round 26），并点名一处记帐不一致：**policy 68 这个号在 Round 26（回滚 `blur→off`）与 Round 29（fullfig sheet＋head 扩带）都被提到**，已用两份 manifest 的 `render_policy_version` 核实实机行为与 Round 29 源码一致，不影响回滚开关。
- VERSION 仍 `0.3.8-alpha.3`，Project Format 仍 29。

### 环境备忘（本轮新增）

- 探针 `working\_round31_p69fig_grade_20261027.py` 已单独 `py_compile` 通过（读帧评级用，输入 seed＋tag，一次产出四张观察 grid）。
- 读帧一次出 grid 比逐帧看快得多；ffmpeg 双 input 的 `-frames:v 1` 位置规则见 §31 末条。

## 33. round 33：`blur_desat`（衣柜灰模板）实机——数值赢了、读帧输了 ⇒ desat 记为已否决分支；瓶颈改判为「头上配件没被抑制＋P1 衣柜无强制证据」（2026-10-27 21:43 实机 seed 923001027，**视频已实机验证＝结论为负**）

### 做了什么（本轮**没有改核心源码**）

- 只把一个变量从 `blur` 换成 `blur_desat`（env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`，shipped default 仍 `blur`）。源码里 `WARDROBE_SATURATION=0.25` 与 ffmpeg `,hue=s=…` 早就在，只加在**非 head** 的 ROI filter 上；plate cache token 含 `band_mode:radius:saturation` ⇒ 换模式一定重建 plate。
- 跑前先备份 blur 版 p69 的 seed 923001027 输出：13 档／35,596,819 B → `_dsh_verify_9\round33\p69_master_backup\`（**同 seed 会被覆盖**，这轮真的覆盖了）。
- GPU 一枪（已批准）：`Start-Process` + `$env:H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE="blur_desat"` → `staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923001027_1793108487623275800.job.json"`。日志 `_dsh_verify_9\round33\driver_r33_desat.log`；worker 日志 `logs\staged_model_driver\preview_923001027_1793108487623275800.jo_20261027_214327.log`。收尾 `comfy-free ok=true`、`report` 出 manifest、`wait-qwen-reload ready=true`。
- manifest 现在会自记录 `identity_suppression_geometry.wardrobe_mode = "blur_desat"` ⇒ 以后不用猜当时跑的是哪个模式。

### 离线与在线证据

- 离线：`working\_round33_desat_plate_check_20261027.py`（verdict OK）⇒ blur／desat 两份 job 的几何、bands、`suppressed_frame_area=0.5013`、`wardrobe_reaches_bottom=True`、clause `crown to feet`、`dropped=[]` **完全一致**，prompt 只差 strategy 名 15 字符（12195／12210，预算 12320）。desat 不外泄：head 区 103.5→103.4、背景 x<0.20 105.3→105.4；带内 ratio 稳定 0.386–0.413（名义 0.25、实测 ~0.40）。A/B 板 `r33_desat_plate_ab.png`。
- QC（`working\_round33_qc_table_20261027.py`，纯读 manifest）：MEAN similarity blur(p69) 0.5521（silent 3/3）→ desat 0.5753（silent **2/3**，seg1 `silent_mouth_excessive_articulation` + `identity_failed=true`）；desat 的 seg1 similarity 0.5163→0.5930 是大改善，但 seg0／seg2 没动。attempts_used 在 `segment_completed` 里（不在 pass spec）：desat 3／3／1。
- plate 连续度（desat 明显下滑，框外改动变多）：seg0 r0 0.709（blur 0.922）／r1 0.538（0.880）／r3 **0.058**（0.741）；seg1 r2 **−0.243**（0.658）；seg2 与 blur 接近。
- 数值评级（`working\_round33_desat_grade_20261027.py` → `_dsh_verify_9\round33\frames_p69desat\`）：desat lower 区 yellow↑（t0.6 0.031→0.100、t3.4 0.000→0.102）、magenta↓（t3.4 0.677→0.033）、SAT↓ ⇒ 粉丝带确实没了。

### 读帧判读（决定性）

四判据来自 `r33_desat_vs_blur_bottom.png`／`r33_desat_vs_blur_head.png`／`r33_master_grid.png`（desat）／`p69_master_grid.png`（blur）／`r33_desat_vs_reference.png`：

1. **髋以下 P1 长裤：不通过。** desat 下半身是 V1 的黑底镶金 cosplay 长袍（深色蜂巢 mesh＋红/粉腰带＋粉或蓝袖），黄格纹只剩底缘小块。对照 `r33_desat_vs_reference.png` 里 P1 identity sheet（黑上衣＋蓝短裤＋黄格纹腿套＋黑球鞋）⇒ **完全不同的衣服**。
2. **猫耳冠＋镶金宝石头带：没改善**，desat 9/9 帧仍在（blur 6/9）。
3. **头部 P1 身份：退步。** desat seg0／seg1 六帧**圆眼镜消失**、P1 秃顶被 V1 整头灰长假发顶掉；seg2 三帧眼镜回来但换成大眼另张脸（与 QC seg1 `identity_failed=true` 对得上）。
4. 第二小人／新蜂窝背景：未见；R2 绿衣戴帽摄影师仍锐利。

### 根因与路线修正

- desat 把 cosplay 压成灰模板后，模型**照 plate 灰轮廓＋V1 先验自行重建原来的黑金 cosplay**，不是改读 P1。这与 round-13 S4 两次灰洗 take（ratio 0.64）同源；本轮 ratio ~0.40 更激进，历史警告成立。
- head 带按设计保留 chroma ⇒ 猫耳冠、宝石头带、V1 假发从来没被抑制过，而它们正是「不像 P1」的最大视觉证据。
- 三轮抑制强度曲线（policy 68 blur 0.5873 / policy 69 blur 0.5521 / policy 69 desat 0.5753）⇒ MEAN 卡在 0.55–0.59，**「再加大抑制」这条路到顶**。下一枪换成**换位置**：head 带拆成 face ROI（保护身份、不动）＋hair／accessory ROI（blur＋desat），先把头饰与假发干掉再谈衣柜。

### 状态界定（务必分开写）

- **源码已修复**：只有 Round 31／32 已登记的那些（policy 69 figure-extent 带＋`crown to feet`）。本轮**零核心源码改动**，shipped default 仍 `blur`。
- **视频已实机验证**：`blur_desat` = 已验证、**结论为负**，不升级成默认；`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur` 保持现况。
- 仍未结：silent listener 对嘴（identity sheet 头部面板本身张嘴）、`character_identity_sheet.resolve_identity_sheet(..., outfit_view=...)` 公开入口。

### 下一枪（**必须先取得用户批准**）

- 单一变量：新增 hair／accessory 抑制带（face box 之内保持锐利，box 之上＋两侧做 blur+desat），目标是判据②③（头饰消失＋P1 秃顶与圆眼镜回来）；衣柜与 prompt 条款一律不动。
- 探针照 `working\_round33_desat_plate_check_20261027.py` 改：先离线建两份 job 比几何＋plate A/B，再请示 GPU。
- job 命名与覆盖风险同 §32：同 seed 会覆盖输出目录 ⇒ 跑前先备份（本轮已备 `_dsh_verify_9\round33\p69_master_backup\`）。

---

## 34. round 34：crown／face 分带源码＋`design_ai.env` knob 白名单；Director GUI 自己跑的 0.5 MP／1.0 MP 新片仍有「sheet 下半身渗出」＋「只换头」两缺陷（2026-10-28 00:11–01:10 实机 seed 2027186731173264249，**视频已实机验证＝两缺陷仍在；分带源码未参与该新片**）

### 这一支新片是怎么来的

- 不是 staged driver：Director 自己在 Studio GUI 按 Preview／Accept。节奏 motion_preview 00:21 → `generated_preview.mp4` 7.13 MB@00:32（0.5 MP）→ `generated_output.mp4` 10.63 MB@01:10（1.0 MP）。用户口径「比一开始好很多，但偶尔有瑕疵」。
- manifest：`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\accepted_2027186731173264249_1793118846499730000.manifest.json` ⇒ `megapixels=1.0`、`master_seed=2027186731173264249`、**`render_policy_version=69`**。master 输出 `cache\generated_outputs\accepted\2027186731173264249\master.mp4`。

### 离线与在线证据

QC（纯读 manifest；探针 `working\_r35d_manifest_read.py`／`_read2.py`／`_read3.py`／`_r35d_manifest_keys.py`／`_r35d_hair_modes.py`）：

| 段 | seed | attempts | similarity | silent |
|---|---|---|---|---|
| seg0 0–4.288 s | 6533122960410627603 | 1 | 0.608703 | pass |
| seg1 4.288–8.576 s | 7217704202240956819 | 3 | 0.573653 | **fail**（`authored Silent Listener mouth shows excessive articulation`＋`character_swap_identity_failed=true`）|
| seg2 8.576–12.864 s | 3524457325454587044 | 1 | 0.506030 | pass |

MEAN **0.5628** ⇒ 与 §32 blur(p69) 0.5521、§33 desat 0.5753 同一档：**抑制强度这条曲线已经压不动了**（见 §33 根因段）。

pass rows（三段一致）：`reference_framing=illustrated_identity_sheet`、`identity_sheet_head_coverage 0.5259`／`identity_sheet_source_canvas_head_coverage 0.214413`、`identity_sheet_preset` forced 8、`identity_sheet_outfit_view=full`、`identity_sheet_reason=cached`。

`identity_suppression_geometry`（决定性）：`wardrobe_mode="blur"`、**`hair_band_mode="off"`**、`hair_extent.enabled=0.0`（params `vertical_share 0.42`／`saturation 0.25`／`blur_radius 18.0`／`extra_sigma 0.0`／`min_band_height 0.05`）、`mask_mode="feather"`、`suppressed_frame_area=0.5013`、bands 3（head 带 `[0.3, 0, 0.4001, 0.285]`＋两条衣柜带）⇒ **本轮写的头饰分带与 policy 70 都还没实机跑过一枪**，这支新片完全是 policy 69 旧 plate 的产物。

读帧：`_dsh_verify_9\round35\frames_new\`（18 帧＋`GRID_master.png`，01:23–01:24 抽）⇒ 4.287 s（seg0/seg1 边界）附近出现 sheet 的下半身面板；身体仍是 V1 衣柜。

### 本轮写进源码的东西（shipped default 一律保守）

- `_hair_band_mode()`（`director_cut_studio.py:1029`，`off` 默认／`blur_desat`）＋`_hair_band_parameters()`（1044）：head 带拆成 **face ROI 锐利保留**（护身份）＋**hair／accessory ROI blur+desat**，目标专打 V1 的猫耳假发与镶金宝石头带——这两样在 §32／§33 从来没被抑制过，是「不像 P1」的最大视觉证据。
- geometry 自记录 `hair_band_mode`（36133）：**只有实际套用分带才报真值**，没套用写 `off`；以后不用猜哪一枪带了什么（§33 的 `wardrobe_mode` 自记录是同一思路）。
- `H3_CHARACTER_SWAP_HAIR_BAND_MODE` 进 `DESIGN_ENV_RENDER_KNOBS` 白名单（433–444）⇒ GUI 按 Preview 时 knob 可经 `design_ai.env` 跨重启携带；**真 env 优先于 env 档**。不在 `design_ai.env` 留实验开关（会污染单测），只在跑的时候用 process env。
- program monitor 的 preview 无声：`_apply_monitor_audio_routing` 与 10-26 备份逐字相同（matches 21=21）⇒ **本轮没有新增源码**，不要把「无声已修」写进任何地方。

### 备份纪律（照例）

同 seed 会覆盖输出目录。跑前已把上一版 desat take 备份到 `_dsh_verify_9\round34\prev_desat_take_backup\`：三段 `character_swap_pass_01_R1\00_save.mp4`／`01_source.mp4`＋`master.mp4` 8,747,247 B。

### 状态界定（务必分开写）

- **视频已实机验证**：0.5 MP 与 1.0 MP 两支都读帧。**两缺陷仍在**——① sheet 下半身在段边界渗出；② 只换头没换身。silent listener **仍未结**（seg1 用满 3 次 fresh seed 仍压不住对嘴，且 `identity_failed=true`）。
- **源码已修复**：hair／face 分带＋knob 白名单＋geometry 自记录；shipped default 仍 `hair_band_mode=off`，**尚未实机**。

### 下一枪（**必须先取得用户批准**）

单一变量＝policy 70 第一枪：0.5 MP、单段、`staged_model_driver.py run "<job.json>"`；跑前备份会被同 seed 覆盖的 `approved_final.mp4`／master，跑完 `/free` 确认。读帧三判据：① 画面内不再出现 sheet 边框／无头面板；② 衣柜闸门会不会误杀（尤其 seg2 那种边界段）；③ 年龄漂移（head share 从 0.5259 掉到 0.2144 的代价，见 §35）。

---

## 35. round 35／35b／35c：两个根因定案 ⇒ Identity Sheet 单图直通＋衣柜位移闸门，policy 69→70（2026-10-28 01:23–03:00 离线＋修码，**源码已修复＋离线全绿，实机未跑**）

### 根因①｜喂给模型的参考图本身 55% 是空白垫板

探针 `working\_round35_sheet_bleed_and_body_probe_20261028.py`（CPU 只读）量被上传的 sheet `image_137_4bd41c9e363a8278_nobg_identitysheet08_fullfig_a0066_v8.png`（800×1216）：

- 近白像素 **55.0%**；head 面板占 **54.6%** 画布、面板内部空白 **50.6%**；outfit 面板占 **97.3%**、内部空白 **57.8%**；head／outfit 面积比 **0.56×**。
- 身份配重量化：sheet head coverage **0.5259** vs V1 源人物 **0.2144**（2.45 倍差）。⇒ 模型把面板边框与无头躯干当「要画进画面的内容」，在 4.287 s 段边界渗出来；同时头身配重失衡是历史「角色变老人」的同一条线索。

### 根因②｜27–29% 的 V1 衣柜根本不在抑制带里

R1 手动画框 `[0.35, 0.15, 0.65, 0.45]`＝29.2% 画面，plate 实际抑制 **61.0%**（manifest `suppressed_frame_area=0.5013`）。带外残留：**V1 衣柜像素 27.8／27.1／29.2%**（三段），**V1 粉腰带 20.6／23.2／27.4%**。叠加图 `_dsh_verify_9\round35\seg{0,1,2}_bands_vs_costume.png`。⇒ prompt 的 `crown to feet` 与 plate 实际削弱范围脱节；这也解释了为什么 §32／§33 再怎么调抑制强度都不动。

### 修码（全部已在树内，本轮逐条 grep 复核）

- `character_identity_sheet.py:62` `IDENTITY_SHEET_ENGINE_VERSION = 8`；新增 `measure_reference_head_metrics()`（883）、`compose_wardrobe_signature()`（931，**只裁衣服区**做衣柜签名，不混脸）。
- `director_cut_studio.py`：单图直通分支 34919–34936（决策回传 `FULL_DESIGN_FRAMING="illustrated_full_design"`，常数在 `character_swap_engine.py:237`）；`_character_swap_wardrobe_signature()`（35039）、`_character_swap_body_audit_box()`（35079）；knob `IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH`（1410，env 同名 `H3_IDENTITY_SHEET_..._PASSTHROUGH`）、`CHARACTER_SWAP_WARDROBE_AUDIT_MODE`（1421，env `H3_CHARACTER_SWAP_WARDROBE_AUDIT`，`on|advisory|off`，默认 `on`，非法值回落 `on`）；pass rows 送出／记录 5 个 identity_audit keys（36843–36850、36960–36966，含 `wardrobe_audit_mode`）。
- `smart_render_worker.py`：`_wardrobe_audit_bboxes()`（1567）；衣柜 audit 主体 2157–2262，回传 keys `checked/passed/mode/shift/rows/minimum_shift/reason`；衣柜相似度加成 `min(0.35, shift) * 1.5`（1613）；`whole_character_audit` 并入 strict temporal coverage 判定（1981）；两处源码守卫 `wardrobe_penalty * 4.0` 与 `strict_temporal_coverage or whole_character_audit`。
- 阈值（`character_swap_engine.py`）：`IDENTITY_SHEET_MIN_HEAD_COVERAGE=0.22`（205）、`IDENTITY_SHEET_MIN_SOURCE_CANVAS_HEAD_COVERAGE=0.18`／`IDENTITY_SHEET_MIN_SOURCE_SUBJECT_FILL=0.55`（221–222，注释里写明 black-shirt 实测证据）、`CHARACTER_SWAP_MINIMUM_WARDROBE_SHIFT=0.12`（233）。预算仍 `12320`（120）。
- `SMART_RENDER_POLICY_VERSION` **69→70**：`director_cut_studio.py:715`、`smart_render_worker.py:103` 两处已同步（本轮 grep 确认）。

### floor 0.12 是怎么定的（round 35b，别再回头猜）

`working\_round35b_wardrobe_shift_calibration_20261028.py` 对 §34 那支新片三段各取 9 点：seg0 **0.036–0.076**、seg1 **0.031–0.150**、seg2 **0.082–0.270**（seg2 有一帧 0.2699 超 floor；seg2 九点均值 0.134 > 0.12 ⇒ **边界段的判定会随取样点数摆动**，引擎用 3 点）。引擎注释里的参照值与实跑一致：三段中位数 0.053／0.089／0.114、最好单帧 0.177、真正整片换装 ≥0.20。positive control `_dsh_verify_9\round35\positive\`（标 0.152／0.177）读帧仍是「P1 头＋V1 猫耳假发＋粉黑 cosplay 身体」⇒ **0.15–0.18 不足以宣称整身替换**，故 floor 定 0.12（宁可重抽也不放过）。

`working\_round35c_offline_verify.py` 用 shipped 路径复核（不是手搓等价逻辑）：载入即 `passthrough=True`／`mode=on`／`floor=0.12`；P1 原图自量 head **0.220077**（刚好过 0.22）、fill **0.96257**、head box `[37,1,172,153]`、subject box `[0,11,250,370]`；编译决策 `illustrated_full_design`＋passthrough `true`，**上传＝Media Pool 原图**；签名档 `image_137_4bd41c9e363a8278_nobg_wardrobe_db6fde105445_v1.png`，bbox `[0, 0.418919, 0.992063, 1]`，第二次调用 `cached`。三段 accepted take 全被拒：shift **0.062375／0.078099／0.102392**（ROI＝manifest 衣柜带 `[0.30, 0.285, 0.78012, 1.0]`，3 点），`passed=false`、`action=retry_fresh_seed`，reason「replacement is only a head/face layer; the V1 wardrobe still fills the body region」。

> **更正（Round 35d 追加，别照抄这句）**：上面「不是手搓等价逻辑」只对 worker 侧成立。该探针第 67 行**手喂** `"body_bboxes_normalized": [BAND]`，从未调用 studio 侧的 `_character_swap_body_audit_box()`——那个 helper 当时**一次都没跑过**，所以它里面的 arity 崩（见文末 Round 35d）一路漏到用户 GUI 才暴露。真正走 shipped 路径的 Job 编译取证补在 Round 35d。

### 测试与编译

- `test_character_swap_engine`＋`test_character_swap_closeup_gates`＋`test_character_swap_silent_audio`＋`test_character_swap_background_extra` ⇒ **158 OK**（9.5 s）
- `testing.test_identity_sheet` ⇒ **52 OK**（3.2 s）
- `testing.test_smart_render_worker` ⇒ **57 OK（skipped=1）**（27.9 s）
- 另沿用本轮较早的重跑：storyboard_segment_mapping **7 OK**、smart_render_qc_advisory **5 OK**、project_workspace **19 OK**
- 四模組（studio／engine／worker／identity sheet）`py_compile` 全绿。`python -m unittest discover` 全量永远跑不完（>1 h），**不要声称跑过全量**。
- 跑法：bundled python `.\ai_libraries_common\python_env\python.exe`，`$env:QT_QPA_PLATFORM="offscreen"`、`$env:PYTHONIOENCODING="utf-8"`。
- 本轮新增测试覆盖：衣柜签名只裁衣服、签名 `cached`、量不到衣服时拒绝、大图直通 vs `=0` 退回 sheet、小头仍走 sheet、直通仍记决策行；worker 侧 head-only 拒／whole-body 收／advisory 只量不拦／`off` 完全不量／缺档 `no measurable garment region`／无身体框 `no body region`。

### 已知代价与风险（写清楚，别让下一段踩）

- head share 0.5259 → 0.2144：画面里头的相对占比下降，**年龄漂移风险上升**（历史 §26「角色变老人」正是身份／配重问题的表现）。读帧时要专门盯这一项。
- P1 原图 head coverage 0.220077 只比门槛 0.22 高 0.000077 ⇒ 任何裁图／换图都可能把它掉回 sheet 路径，这是**预期行为**，不是 bug。
- seg2 这类衣柜带边界段，闸门判定会随取样点数摆动（3 点 vs 9 点）；出现「同一段时而拒时而收」先怀疑这里。

### 回滚开关一览（本轮新增在最前）

`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH=0`（退回 sheet）、`H3_CHARACTER_SWAP_WARDROBE_AUDIT=off|advisory`、`H3_CHARACTER_SWAP_HAIR_BAND_MODE=blur_desat|off`、`H3_CHARACTER_SWAP_FIGURE_EXTENT=0`、`H3_CHARACTER_SWAP_HAIR_HALO=0`、`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE`／`H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`、`H3_CHARACTER_SWAP_IDENTITY_MASK_MODE=rect`，project json `identity_sheet_enabled`／`identity_sheet_preset`。

### 状态界定（务必分开写）

- **源码已修复**：单图直通、衣柜 audit＋闸门、policy 70、engine 8 的两个 helper——离线证据齐全、单测全绿。
- **视频已实机验证**：**无**。policy 70 一枪都没跑。§35 里那三个 0.062／0.078／0.102 是把 policy 69 已 accept 的 take 反过来套新闸门算的，只证明「闸门会拒只换头的 take」，**不证明**重抽后能通过。 > 已被 §35e 取代：policy 70 首枪已于 2026-10-28 07:54 实机跑完。
- 仍未结：silent listener 对嘴（seg1 三次 fresh seed 压不住）、`resolve_identity_sheet(..., outfit_view=...)` 公开入口。
- 已否决、别再重跑：加大抑制面积／去色（§32 blur、§33 blur_desat，MEAN 卡 0.552–0.587）。

### 下一枪（**必须先取得用户批准**）

1. 备份将被同 seed 覆盖的输出（`approved_final.mp4`／master）。
2. 0.5 MP 单段 job 一条命令：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\<job>.job.json"`（内置 unload-qwen → wait-comfy → worker → `/free` → report）。
3. 读帧三判据：① 无 sheet 边框／无头面板渗出；② 衣柜闸门是否误杀（重点 seg2）；③ 年龄漂移是否回来。
4. 独立问题（另开一枪）：silent listener 对嘴。

## 35d. Round 35d（2026-10-28 07:00–07:20 同日 hotfix）：policy 70 的 GUI Preview 路径其实一按就崩——`_character_swap_body_audit_box()` 的 `list.append()` arity 错（**源码已修复＋离线全绿，实机仍未跑**）

上面 §35 那句「policy 70 一枪都没跑」之外，还有一件更糟的事实：**用户在 GUI 按 Preview 根本到不了 GPU**。用户报「点 Preview 出现 Queue error」，附截图。

### 症状与 traceback

`TypeError: list.append() takes exactly one argument (2 given)`，调用链 `_start_generation` → `_build_smart_render_job` → `_compiled_character_swap_window_job` → `_character_swap_body_audit_box`（原 35119）。没有任何 ComfyUI／LM Studio 请求发出——Job 编译阶段就抛异常。

### 根因

Round 35 新 helper 里写成 `candidates.append((area), [box])`：一对 `(面积, 框)` 被当两个实参传给 `append`。衣柜 audit 默认 `on`，所以**只要该 Shot 有 wardrobe bands 就必崩**——100% 复现，与项目资料无关。也说明 §35 那批「shipped 路径」测试根本没覆盖 Job 编译的这一段（见上文更正）。

### 修法（`director_cut_studio.py:35105-35127`）

先组 `band_box`，再 `candidates.append(((right - left) * (bottom - top), band_box))`，附一行注释「`list.append` takes one argument」。判定逻辑不变：取面积最大的衣柜带。

### 防再犯

- `testing\test_character_swap_closeup_gates.py:2028` 新增 `WardrobeAuditBoxTests`（4 项，bands 几何直接抄 black-shirt 已 accept manifest 真值）：最大衣柜带 → `[[0.3, 0.285, 0.78012, 1.0]]` 且 float 可 JSON；细手臂 sliver（宽 0.08002）跳过 → 退回 role box；只有 head 带 → 退回 role box（`top+0.45*height`、`bottom≥0.999`）；无 geometry／无 role → `[]`，bands 塞 `None,7` 不炸。
- AST 扫描 `working\_r35e_scan_append_args.py`：四模組再无同型 arity 错的 `append/extend/update/add`（只剩 `dict.update(**kwargs)` 一类假阳性）。

### 走 shipped 路径的离线取证（这才是 §35 该做而没做的）

`working\_r35e_preview_rebuild_check.py [SEED]`：headless `DirectorCutStudio()._build_smart_render_job(request_kind="preview", megapixels=0.5, seed=923009999)` ⇒ **VERDICT OK**，三段（segments=3）逐条一致：

- `policy=70`、`framing=illustrated_full_design`、`identity_sheet_single_figure_passthrough=true`（在 pass／segment 行顶层）
- 上传参考＝**P1 原图** `image_137_4bd41c9e363a8278_nobg.png`（不是 sheet）；衣柜签名 `image_137_..._nobg_wardrobe_db6fde105445_v1.png`
- `identity_sheet_reference_head_coverage=0.220077`／`..._source_head_coverage=0.214413`／`..._subject_fill=0.96257`
- `identity_audit`：`body_bboxes_normalized=[[0.3, 0.285, 0.78012, 1.0]]`、`wardrobe_audit_mode="on"`、`minimum_wardrobe_shift=0.12`、`whole_character_audit=true`、bands 2
- prompt `11324 / 12320` 字元、`dropped_tail_clauses=[]`、`over_budget=false`

**命名与位置速记**（下一段别再翻）：这些 key 在 **`segments[i].character_swap_passes[j].identity_audit` 里面**；pass row 顶层只有 `identity_sheet_reference_head_coverage`／`…_source_head_coverage`／`…_subject_fill`／`…_single_figure_passthrough`，**没有** `head_coverage`／`source_canvas_head_coverage` 这种短名。

副产物：`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\` 多两个 scratch job（seed 923009999：`preview_923009999_1793142990323537600.job.json`、`preview_923009999_1793143069391241000.job.json`，131 003 bytes，二者内容同构）。后者是 policy 70 首枪的现成 job。

### 测试与编译（本轮第一手）

- `test_character_swap_engine`＋`test_character_swap_closeup_gates`＋`test_character_swap_silent_audio`＋`test_character_swap_background_extra` ⇒ **162 OK**（7.0 s）
- `testing.test_identity_sheet`＋closeup_gates ⇒ **123 OK**（7.8 s）
- `py_compile` studio／worker／engine／identity sheet＋新测试档 ⇒ exit=0
- §35 记的 158 OK 是加这 4 项之前的数；全量 `unittest discover` 依旧不跑（>1 h），**不要声称跑过全量**。

### 状态界定

- **源码已修复**：arity 崩＋回归测试＋AST 扫描＋shipped 路径 Job 编译证据。GPU 本轮**完全没碰**（那次 Preview 死在编译前，ComfyUI 全程空闲，Qwen 已由 tray 载回）。
- **视频已实机验证**：**无**。policy 70 至今零枪。 > 已被 §35e 取代（同日实机）。
- 未结不变：silent listener 对嘴（seg1 三次 fresh seed 压不住）、`resolve_identity_sheet(..., outfit_view=...)` 公开入口。

### 下一枪（**必须先取得用户批准**）

1. 先备份将被同 seed 覆盖的输出（`approved_final.mp4`／`cache\generated_outputs\…\master.mp4`）。
2. `.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923009999_1793143069391241000.job.json"`，背景 `Start-Process`，日志写 `_dsh_verify_9\round35\`。
3. 读帧三判据：① 画面内不再出现 sheet 边框／无头面板；② 衣柜闸门会不会误杀（重点 seg2，9 点均值 0.134 贴 floor）；③ 年龄漂移（head share 0.5259→0.2144 的代价）。
4. 测完 driver 自动 `/free`；回 Design 前 `load-qwen` 显式验证。
## 35e. Round 35e（2026-10-28 07:54–08:13 实机）：policy 70 首枪跑完 —— sheet 渗出已消除、衣柜闸门实机通过；主缺陷转为 V1 猫耳假发＋镶金头带（**视频已实机验证**）

本节取代 §35 与 §35d 里「policy 70 一枪都没跑」的口径。详细数据表见 `CHANGELOG.md` 的 `### Round 35e`；本节只留下次要用的判断。

### 跑法与产物
- 用户「批准」后：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923009999_1793143069391241000.job.json"`（0.5 MP、master seed 923009999、3 段、每段最多 3 次尝试）。
  > **PowerShell 坑**：`Start-Process` 的绝对路径参数含空格会被拆成 `D:\minimax` 而失败 ⇒ 必须 `-WorkingDirectory <root>` ＋**相对**参数。
- driver 全程合规：`unload-qwen verified_clean=true`（VRAM 25.69 → 2.77 GB）→ `wait-comfy ready node_classes=1600` → `worker-exit code=0` → `comfy-free ok`；回 Design 前 Qwen 已由 tray 载回（本轮 `status` 复核：`qwen_loaded=[e0e0dae3-...]`、`comfy_queue=free`）。
- master：`cache\generated_outputs\preview\923009999\master.mp4`（7,640,843 B、576×864、12.864 s）。manifest：`project\render_jobs\preview_923009999_1793143069391241000.manifest.json`。抽帧：`_dsh_verify_9\round35\p70_frames\`。备份：`_backup\r35d_20261028_pre_policy70\`。
- ⚠ 跑完 `.job.json` 被消耗，只剩 manifest 与同 seed 的另一份 scratch job（`..._1793142990323537600.job.json`）；重跑要先重新编译 job（`working\_r35e_preview_rebuild_check.py [SEED]`）。

### 实机结论（只写判据与口径）
1. **Round 35 根因① 已修实验证**：三段上传参考都是 P1 原图（`.director_cache\image_137_4bd41c9e363a8278_nobg.png`，注意它在**工作区根**的 `.director_cache`，不在项目 `media\`），16 格无 sheet 边框／无头面板。
2. **Round 35b 的衣柜闸门实机可用**：floor 0.12 三段全过（0.160258／0.129918／0.159559），且 seg0 attempt 1 真的以 shift 0.058691 被拒并重抽 ⇒ 「只换头」会被拦；seg2 一次就 accept ⇒ 不误杀。
3. **重试选择实机确认是 target-best**：seg0 三次候选（target 0.582741／0.503245／0.394576）里选了 #2，log 原文「keeping target-best take 2」，不是盲取最后一条。
4. **现在的身份瓶颈＝头发**：13/16 帧仍有猫耳假发、row1/row2 有镶金头带，P1 秃顶 ⇒ `target_reference_similarity` 0.503245／0.520336／0.531581，MEAN **0.5184**。与 policy 69 三个 seed（0.5521／0.5753／0.6187，均值 0.582）差 ≈0.06，但同 policy 的 seed  spread 就有 0.067 ⇒ **单 seed 不足以判定回归**。
5. **`wardrobe_audit.passed=true` ≠ 整身换装**：读帧＝腿已换 P1（黄格纹腿套／黑黄球鞋／蓝短裤），上身仍是 V1 粉袖＋金边黑背心。ROI 带 3 点均值被腿部变化抬过 floor，是当前闸门口径的已知盲区。
6. 年龄漂移只在 t≈4.0 s（seg0 尾）复现一处；卡通媒介保留 OK（`live_action_adaptation=false`，无真人化）。
7. **silent listener 仍未结**：seg0／seg1 `silent_mouth_excessive_articulation`，`result_motion_mean` 0.274679／0.248828（source 0.062185／0.070963）、`maximum_motion` 0.106289／0.086737 > limit 0.055，三次 fresh seed 无效；seg2 通过（mean 0.217998 vs 0.120635，max 0.129921 violated=false）。

### 已否决 vs 还没试
- **已否决**（别再重跑）：加大抑制面积／去色——§32 `hair_band_mode=blur` 路线、§33 `blur_desat`，MEAN 一直卡 0.552–0.587。`_hair_band_mode()` 目前只接受 `{off, blur_desat}`，shipped default `off`；本轮 manifest 实测 `hair_band_mode="off"`、`hair_extent.enabled=0.0`、`hair_halo.enabled=1.0`。
- **还没试（下一枪候选，需用户批准）**：
  1. 发型写成**具体正向事实**（bald pate／no animal ears／no headband），挂在既有 `source_hair_ownership_clause`（`character_swap_engine.py:1377-1381`，已含「animal ears」但没点名秃顶）而不是新增 clause 家族。预算 `12320-11324=996` 字元、`dropped_tail_clauses=[]`。
  2. 衣柜闸门口径要不要改：若要逼出整身，得让 ROI 对上／下身**分别**过 floor（现在只看整带均值）。改 floor 前先想 §35b 的标定依据。
  3. 独立一枪打 silent mouth（seg0/seg1）。

### 回滚开关（不变）
`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH=0`、`H3_CHARACTER_SWAP_WARDROBE_AUDIT=off|advisory`、`H3_CHARACTER_SWAP_HAIR_BAND_MODE=blur_desat|off`、`H3_CHARACTER_SWAP_FIGURE_EXTENT=0`、`H3_CHARACTER_SWAP_HAIR_HALO=0`、`H3_CHARACTER_SWAP_WARDROBE_BAND_MODE`／`…_MEDIUM_SILENT_WARDROBE_BAND_MODE`、`H3_CHARACTER_SWAP_IDENTITY_MASK_MODE=rect`。实验开关只用 process env，不进 `design_ai.env`。

### 状态界定
- **视频已实机验证**：通过＝判据①②＋重抽／选择逻辑＋卡通媒介保留；失败＝V1 头饰未抹除（身份天花板）、silent listener 对嘴（seg0/seg1）。
- **源码已修复（本轮无新增）**：树内仍是 policy 70／engine 8／Round 35d hotfix；本轮只做取证与文档。VERSION 仍 `0.3.8-alpha.3`。

## 36. Round 36（2026-10-28 08:48–09:15 修码＋实机）：policy 70→71 —— 头发条款补上「正面事实」（bald crown／headwear only where Picture 1 draws it）；首枪 seed 923010107 **猫耳＋头带仍在 15/16 格 ⇒ 「只加句子」这条路已否**（**源码已修复＋实机验证＝失败**）

详细数据表见 `CHANGELOG.md` 的 `### Round 36`；本节只留判断口径。

### 跑法与产物
- `staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923010107_1793148508260025000.job.json"`（0.5 MP、3 段、每段最多 3 次尝试）；driver 合规：`unload-qwen verified_clean` → `wait-comfy` → `worker-exit 0` → `comfy-free ok`，Qwen 已由 tray 载回。
- manifest `project\render_jobs\preview_923010107_1793148508260025000.manifest.json`；日志 `_dsh_verify_9\round36\round36_policy71_first_shot.log`；16 格抽帧 **`_dsh_verify_9\round36\p71_frames\montage_policy71.png`**（⚠ 帧在 `p71_frames\` 子目录，不在 round 目录顶层）。备份：`_backup\r36_20261028_pre_policy71\`。
- 尝试数 2／2／3＝**7 次生成**；target sim 0.617651／0.439179／0.597070 ⇒ MEAN **0.5513**；衣柜整带中位数三段全过 floor 0.12（0.121004／0.154807／0.123736）；seg2 `silent_mouth_excessive_articulation`。

### 实机结论
1. **头发＝失败**：15/16 格仍有猫耳，row1/row2 仍有镶金头带，只有 row4 的 2–3 格出现裸头顶（**仍带兽耳**）；另外新出现**发色漂移成桃红／magenta**（row3–row4）。⇒ 把条款从「谁拥有这块区域」升级成「可画的正向事实」并没有改变模型行为，**别再往同一方向堆句子**。
2. **顺带把 §35e 判据⑤ 变成修法动机**：三段衣柜中位数都 pass，读帧却是「腿已换 P1、上身仍 V1」⇒ 整带中位数分不出「换装」与「只换裤」，这正是导演一路在批的「只有头被换」。⇒ 交给 Round 37。

### 状态界定
- **源码已修复**：policy 71 头发条款已在树内并进入提交 prompt（只在 suppressed plate 上发言）。
- **视频已实机验证＝不合格**：头饰未抹除。VERSION 仍 `0.3.8-alpha.3`，Project Format 29，sheet engine 8。

## 37. Round 37（2026-10-28 09:18–09:30 修码＋实机）：policy 71→72 —— 衣柜闸门改成「上半身／下半身各自要动」，判定与重抽跟**最差半边**；首枪 seed 923010207 证明**闸门抓得住、全身替换仍未达成**（**源码已修复＋闸门实机有效；视频仍不合格**）

### 改了什么（`smart_render_worker.py`，+4.7 KB）
- 新增 `_wardrobe_region_boxes()`：把被审计的服装矩形沿中线切成 `upper`／`lower`（仅当高度 ≥0.36 且每半 ≥0.18，否则保持 `whole`，避免细矩形切出背景当衣服）；每半分别取 `target_reference_frame_similarity` 中位数，产出 `regions[]`。
- **binding 取位移最小的半边**：判定、manifest 顶层 `wardrobe_shift`、重抽排序全部跟最差半边，写 `binding_region` + `region_policy="each_half_must_move"`；失败原因与重抽 prompt 点名「the `<upper|lower>` half of the body region」。`director_cut_studio.py` 只改 policy 註解与常数。

### 跑法与产物
- 同一 job 重建跑法：`working\_r35e_preview_rebuild_check.py 923010207` → `staged_model_driver.py run`（`.job.json` 跑完即被消耗）。
- manifest `preview_923010207_1793150597426430600.manifest.json`；日志 `_dsh_verify_9\round37\round37_policy72_first_shot.log`；16 格抽帧 **`_dsh_verify_9\round37\p72_frames\montage_policy72.png`**（同样在子目录）。备份：`_backup\r37_20261028_pre_policy72\`。

| 段 | 窗口 | 尝试 | failure_class | target sim | 衣柜位移(binding) | ward pass | binding | 嘴 violated |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.0–4.288 | 3 | — | 0.612033 | **0.079174**（upper 0.145896／lower 0.079174） | **False** | **lower** | False |
| 1 | 4.288–8.576 | 3 | silent_mouth_excessive_articulation | 0.561566 | 0.162069（upper 0.16968／lower 0.162069） | True | passed | **True**（0.301936 > 0.280528） |
| 2 | 8.576–12.864 | 3 | silent_mouth_excessive_articulation | 0.531974 | 0.183196（upper 0.188221／lower 0.183196） | True | passed | **True**（0.236705 > 0.183148） |

### 实机结论
1. **闸门确实抓到用户的抱怨**：seg0 上半身 0.145896、下半身 0.079174 ⇒ 绑在 `lower` 判 fail；三次候选（0.088685／0.055641／0.079174）全低于 floor，预算耗尽后「keeping target-best take」。seg1/seg2 未被误杀 ⇒ 方向正确。
2. **相似度没有可宣称的增益**：MEAN **0.5685**（p72）vs **0.5513**（p71），差 0.0172 落在同 policy 的 seed 变异内（历史 spread ≈0.067）⇒ 不得宣称 policy 72 提升身份相似度；代价是**多烧 2 次生成（9 次 vs 7 次）**。
3. **读帧定案**：猫耳＋镶金头带几乎每格都在；上身仍是 V1 粉袖＋金边背心（部分格出现 P1 蓝袖＋红蓝裙）；头／脸 OK ⇒ **「整个角色替换（含头发）」仍未达成**。
4. silent 对嘴改到 seg1/seg2 被抓（见 §37b：这两条 violated 是 ROI 未配准造成的**假阳性＋真阳性混合**，措辞问题才是根因）。

### 状态界定
- **源码已修复**：policy 72 上下半身分半闸门。
- **视频已实机验证**：闸门＝有效（拦下 seg0 只换腿、不误杀 seg1/seg2）；整体替换＝**仍不合格**（头饰未抹除、上身衣柜未换、silent 对嘴）。

## 37b. Round 37b（2026-10-28 09:30–10:05 离线＋读帧）：silent-mouth QC 的两个独立根因定案 —— ① ROI 根本没对在路上 ② prompt 要模型复制 P1 张开的嘴（**诊断完成，当轮未改码**）

### 根因①｜QC 量的是「redraw 沸腾＋头晃」，不是口型
- silent 审计用的 actor box 是**硬编码默认** `[0.35, 0.15, 0.65, 0.45]`（`identity_audit.source_bboxes_normalized`），**不是检测到的人脸**；`_mouth_region_bbox()`（`smart_render_worker.py:1234`）在里面再切出嘴带 `[0.434, 0.225, 0.566, 0.291]`、对照带 `[0.4657, 0.1586, 0.5343, 0.1877]`。
- 带网格的标注帧（`_dsh_verify_9\round37\roi_check\f01_t001.00_roi.png`／`f05_t004.35_roi.png`／`f11_t008.70_roi.png`，生成器 `working\_r37b_roi_annot.py`）显示：「嘴带」压在**额头／眼睛／眼镜／头带**上，「对照带」压在**猫耳＋背景**上，而**真嘴在 y≈0.33–0.40**（seg0 0.315–0.385、seg1 0.340–0.410、seg2 0.355–0.425）。
- 整条 box 高度的运动剖面（`working\_r37b_profile.py` → `_dsh_verify_9\round37\round37b_motion_profile.json`）：result 侧每条带一律 **0.15–0.33 平坦**（无嘴部峰值）、plate 侧 0.01–0.09 ⇒ 绝对 floor 0.055 在这种画风下**永远达不到**，因为量到的不是口型。另：`maximum_motion` 是**阈值** `max(0.055, source_motion*1.5+0.012)`（`smart_render_worker.py:2105`），从来不是测量值。

### 根因②｜嘴真的在动，因为 prompt 叫模型复制 P1 的张嘴
- P1（`.director_cache\image_137_4bd41c9e363a8278_nobg.png`，**工作区根**的 `.director_cache`）是**张嘴大笑（露齿露舌）**的秃顶卡通男；三条真嘴 crops（`_dsh_verify_9\round37\true_mouth_crops\montage_true_mouth.png`，生成器 `working\_r37b_true_mouth.py`）显示 seg0 大笑与闭嘴交替、seg1 从抿嘴变到大张嘴、seg2 也有张嘴帧 ⇒ 用户「对嘴」的抱怨是真的。
- 两处自相矛盾的原文：`close_up_silent_mouth`／`medium_shot_silent_mouth` 末句「Picture 1's own open smiling mouth is **one static expression to copy**」，以及 `AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT` 只删「visible mouth movements」却**保留「facial expressions」**。权威 SILENT 契约在 `character_swap_engine.py:1781-1794`（已含「Even if Picture 1 is smiling or has an open mouth…」）。修法见 §37c。
- 顺带查实：喂给 H3 的 silent plate 整个头部是**糊掉的**（`.director_cache\character_swap_silent_audio\v1_relay_6a51a424164732e57f91_0.000-4.287_..._silent_3dcc95030363c88b6c8b.mp4`；crops `_dsh_verify_9\round37\plate_silent_crops\montage_silent_plate_head.png`）⇒ plate 不出口型线索，画出来的嘴只可能来自 prompt／P1。

### 已设计、**尚未实现**
- ROI 配准／boil-relative 审计：单张 ffmpeg crop 内同时叠嘴带与对照带，以**带中位数当沸腾底**，改比「下半带相对沸腾底的超出量」，取代绝对 floor 0.055。需用 `testing\test_silent_mouth_transient_qc.py` 的合成 fixtures 验证（articulating 必须 fail、transient 必须 pass），且要**单独一枪＋自己的批准**。
- 可复用探针：`working\_r37b_roi_annot.py`、`_r37b_profile.py`、`_r37b_true_mouth.py`、`_r37b_plate_crops.py`、`_r37b_prompt_mouth.py`。
- ⚠ 方法警告：旧 take 的离线重评分（`working\_r37_counterfactual.py`、`_r37_tradeoff2.py`）**无法**复现在线 audit 数值（重试时候选槽位会轮换），不得据其决策。

## 37c. Round 37c（2026-10-28 10:10–10:30 修码＋测试）：policy 72→73 —— silent 条款不再「请模型复制 P1 张开的嘴」，作者 prompt 也不再要 facial expressions（**源码已修复，实机未跑**）

### 改了什么（三处，全 CPU）
1. `character_swap_engine.py:546-549`：`AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT` → `blinking, brow and eye expression only, and a relaxed closed mouth with the jaw still.`（把可匹配的表演限制在**上半脸**）。
2. `character_swap_engine.py:555-567`：新增共用常量 `SILENT_MOUTH_REFERENCE_PORTRAIT_CLAUSE`（「Picture 1 may itself be drawn mid-laugh with an open mouth: copy that Picture's identity, not its mouth. Draw the same face with the lips gently together in every frame, and never let the lips open or change shape from frame to frame.」），两条 scale 条款改为拼接该常量 ⇒ 两条永远不会再各写各的。旧句「one static expression to copy」树内只剩註解。
3. `smart_render_worker.py:115` / `director_cut_studio.py:727`：`SMART_RENDER_POLICY_VERSION` **72 → 73**（提交的 prompt 变了 ⇒ policy-72 manifest 过期）。逐 byte 比对：两檔各**只有 1 個 byte**变化，无 BOM／encoding 走样。

### 测试跟着改
`testing\test_character_swap_engine.py:760-770` 改断新串并新增「旧串不得出现」；`testing\test_silent_mouth_motion_gates.py:115-128` 改名 `test_both_clauses_forbid_copying_the_reference_open_mouth`。policy 常数是符号引用，升版自动跟随。

### Verification（本轮第一手）
- `test_character_swap_engine` + `test_silent_mouth_motion_gates` + `test_silent_mouth_transient_qc` ⇒ **88 OK**（4.8 s）。
- `test_smart_render_worker` ⇒ **59 OK（1 skip）**（23.0 s）。
- `py_compile`（engine／worker／studio + 两个测试档）⇒ exit=0。
- 组串检查：`working\_r37c_prompt_check.py` 打印确认拼接处无缺空格。
- ⚠ `test_director_timeline`（238 项）**不作本轮回归判据**：本机对该模块没有近期 green 基线（日常基线明确 `--skip` 它，见 §「慢模块」），本轮 `-m unittest testing.test_director_timeline` 10:21:36 起跑、10:40 仍在跑（中途 200/238 ⇒ 173 ok／5 error／6 failure／16 skip；`audio_separator_service.py` 那类单项就要数分钟）。要判定 policy 73 有没有回归，按 `CHANGELOG` 口径看**分模块点名**，不要看这条。
- 备份：`_backup\r37b_20261028_pre_policy73\`（三个源檔 + 两个测试档）。VERSION 维持 `0.3.8-alpha.3`，Project Format 29，sheet engine 8。

### 已否决 vs 还没试
- **已否决**：加大抑制面积／去色（§32 `blur`、§33 `blur_desat`）；往头发条款堆句子（§36）。
- **还没试（需用户批准）**：① policy 73 闭嘴条款的**实机一枪**（下一 seed `923010307`，job 需 `working\_r35e_preview_rebuild_check.py 923010307` 重建）；② §37b 的 ROI 配准／boil-relative 审计（独立一枪）。

### 回滚开关（不变）
`H3_CHARACTER_SWAP_WARDROBE_AUDIT=off|advisory`、`…_HAIR_BAND_MODE=blur_desat|off`、`…_FIGURE_EXTENT=0`、`…_HAIR_HALO=0`、`…_IDENTITY_MASK_MODE=rect`、`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH=0`。实验开关只用 process env，不进 `design_ai.env`。

### 状态界定
- **源码已修复**：policy 73（silent 措辞去自相矛盾）——只有测试证明**文本正确**。
- **视频未实机验证**：「卡通角色闭嘴」必须在 seed 923010307 之后才能宣称修好。树内现状＝policy 73／engine 8／Project Format 29／VERSION `0.3.8-alpha.3`。

## 37d. Round 37d（2026-10-28 11:05–11:55 实机＋读帧＋离线复核）：policy 73 首枪 seed 923010307（9 次生成）—— **真嘴读帧判定：仍没闭嘴**；`violated` 的判定规则与它为什么不可信，已一手算清（**视频已实机验证＝未通过**）

### 跑法与产物
1. job 重建 `working\_r35e_preview_rebuild_check.py 923010307` ⇒ `preview_923010307_1793157449016312100.job.json`，`VERDICT OK`，knobs `passthrough=True / wardrobe_audit=on / hair_band=off / policy=73`，ROI `[[0.3,0.285,0.78012,1.0]]`，ref＝P1 原图直通，budget 11731/12320、`dropped_tail_clauses=[]`（日志 `_dsh_verify_9\round37\rebuild_923010307.log`）。
2. 措辞确认：job 内文 `copy that Picture`／`relaxed closed mouth`／`blinking, brow and eye expression only` 各 6 次；`one static expression`／`facial expressions, and visible mouth movements` 各 0 次。
3. `staged_model_driver.py run`（`Start-Process`，日志 `_dsh_verify_9\round37\round37c_policy73_first_shot.log`）⇒ `worker-exit 0` → `comfy-free ok` → `vram-release 3.14→2.87 GB` → `wait-qwen-reload ready=true`。master `7,981,117 B`，manifest 同名 `.manifest.json`。
4. 读帧产物：`_dsh_verify_9\round37\p73_frames\montage_policy73.png`（`working\_r37d_extract.py`）、`p73_frames\true_mouth_crops\montage_true_mouth_p73.png`（`working\_r37d_true_mouth.py`）、离线带比较 `working\_r37d_roi_audit2.py`。

### 实机结论（逐条）
- **仍对嘴**：真嘴带 crops 显示 seg0 t=0.50／2.70／3.20／3.70 大张嘴（露齿露舌）与 t=1.50／2.10 抿嘴交替；seg1 七个采样点 5 个张嘴；seg2 t=0.50／1.00 大张嘴。p72 同样在说话 ⇒ **policy 73 无可证实的增益**（措辞只影响 prompt，不影响 seed 变异）。
- **manifest 数字**：MEAN target sim 0.55945（p71 0.5513／p72 0.5685 ⇒ 同分布）；seg0 `wardrobe pass=False binding=lower`（lower_shift 0.101278 < 0.12 floor）＝闸门抓到「只换上身的反面」，但预算耗尽仍 accept；三段 erasure／whole_character／plate continuity 全 True。总生成 **9 次**。
- **头饰／衣柜**：猫耳 16/16 仍在；镶金头带＋长假发 9/16（seg0 4/5、seg1 5/6、**seg2 0/5**）。seg2 那批格最像 P1（秃顶／黑 mesh 坎肩／蓝短裤／黄格纹裤），但本轮只改嘴部措辞 ⇒ 属 seed 变异，**不得**当作头发或衣柜的进展。
- **`violated` 规则一手定案**（`smart_render_worker.py:2105-2125`）：`violated = 绝对阈值 AND 相对阈值`；绝对 `= max(0.055, source_motion*1.5+0.012)`，相对 `= upper_face_motion*1.25+0.02`。seg0 0.267488 vs 相对线 0.267978 ⇒ **差 0.00049 而判过**，seg1／seg2 越线判败。
- **两条阈值都可被非嘴部沸腾左右**（`working\_r37d_roi_audit2.py`）：审计带 y 0.225–0.291（额头／眼镜／头带）、对照带 y 0.156–0.222（头顶／猫耳），真嘴 y 0.315–0.425。实测（median 相邻帧差）p73 seg0 26.29／18.56／线 25.20／真嘴 26.14，p73 seg1 25.85／20.69／线 27.86／真嘴 **31.52**，p73 seg2 26.99／12.94／线 18.18／真嘴 22.35；p72 seg0 28.37／28.06／线 37.08／真嘴 25.53（三行数值×10⁻²）。⇒ **两条带都不含嘴唇**，额头带沸腾常高于真嘴带，所以 `violated` 判的是额头 vs 头顶。§37b 根因①升级为此形式。

### 已否决 vs 还没试
- **已否决**：头发条款堆句子（§36）；`blur`（§32）／`blur_desat`（§33）去色抑制；「靠 target sim 判断 policy 好坏」（三轮 sim 同分布）。
- **还没试（需用户批准，每枪都要）**：① silent QC **ROI 配准／boil-relative 审计**——先离线 fixtures（`testing\test_silent_mouth_transient_qc.py`：articulating 必 fail、transient 必 pass）再单独一枪；② 头饰／衣柜的**非 prompt 抹除机制**（inpaint／mask 侧，而非再加句子）。下一 seed 惯例 `923010407`。

### 回滚开关（不变）
`H3_CHARACTER_SWAP_WARDROBE_AUDIT=off|advisory`、`…_HAIR_BAND_MODE=blur_desat|off`、`…_FIGURE_EXTENT=0`、`…_HAIR_HALO=0`、`…_IDENTITY_MASK_MODE=rect`、`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH=0`（只用 process env）。本轮**无源码改动**，故无新备份。

### 状态界定
- **源码已修复**：policy 73（§37c）。**本轮（37d）不改码。**
- **视频已实机验证＝未通过**：seed 923010307 仍对嘴，且 V1 猫耳＋头带＋上身衣柜仍是主缺陷。Silent Listener 在本案目前**只能靠读帧判定**，manifest 的 silent 数字（含 `violated`）一律不可作判据。
- `test_director_timeline` 238 项 11:55 仍未收尾（200/238 ⇒ 173 ok／5 error／6 failure／16 skip），不作 policy 73 回归判据；日常全量仍 `--skip test_director_timeline`。

### 本轮新增探针（可复用）
`working\_r37d_extract.py`（网格＋montage）、`_r37d_true_mouth.py`（真嘴带 crops）、`_r37d_roi_audit2.py`（审计带／对照带／真嘴带三方 median 运动比较）、`_r37d_roi_audit.py`（由 ROI 反推带位的第一版，保留作对照）、`_r37c_manifest_summary.py`（manifest 摘要）。
## 37e. Round 37e（2026-10-28 12:10–12:30 离线＋修码；**当轮没登记，由 37f 补记**）：silent-mouth QC 的判决从「相邻帧差」换成「口腔开合 swing」，新增 `H3_CHARACTER_SWAP_MOUTH_GEOMETRY`（当时默认 `on`）——判据本身落码，但**实机增益为零**，37f 已把默认退回 `advisory`（**源码已修复，视频已实机验证＝不适用**）

### 代码面（`smart_render_worker.py`）
1. `_cavity_opening_profile(frames, size)`：把嘴带按行求「暗腔开启度」时间序列，取 **swing = max−min**，不用相邻帧差。动机是 §37d 一手定案：`violated` 的两条阈值都不含嘴唇（审计带 y 0.225–0.291 是额头／眼镜／头带，对照带 y 0.156–0.222 是头顶／猫耳，真嘴在 y 0.315–0.425），额头沸腾常高于真嘴带 ⇒ 旧判据实际在比「额头 vs 头顶」。
2. 判决式：`violated = mouth_swing > max(control_swing × margin, floor)`，`margin=1.60`、`floor=0.020`；控制带跑**同一套形状算法**，理论上剩下的是口腔开合本身，而不是沸腾／眨眼／道具／一直张着的参考笑。
3. `_silent_mouth_geometry_settings()` 暴露三个 **process env**（不读 `design_ai.env`）：`H3_CHARACTER_SWAP_MOUTH_GEOMETRY=on|advisory|off`、`…_MARGIN`、`…_FLOOR`。
4. manifest 新栏位：audit 层 `gate`／`geometry_mode`／`geometry_margin`／`geometry_floor`；row 层 `mouth_opening_median|swing`、`control_opening_median|swing`、`source_mouth_opening_median|swing`、`geometry_available`、`geometry_swing_limit`、`geometry_violated`、`decision_basis`、`articulation_excess`。帧是 §37b 已抽过的（嘴带／额带／plate 同源），**没多一次 ffmpeg 抽取**，只多 numpy 算术 ⇒ QC 成本几乎不变。

### 遗留代价（当轮没发现）
- 37e 没写专属测试就把默认设成 `on`，直接打破 `testing/test_silent_mouth_transient_qc.py::test_persistent_lip_motion_still_fails_the_take`（37e 基线 **2 OK／1 FAIL**）。37f 把默认退回 `advisory` 后该测试**自动恢复**（现在 3 OK），fixture 未改。
- p73 manifest 实测 `silent_mouth_audit` 只有 `checked/passed/rows` 三个键，**没有 geometry 栏位** ⇒ p71／p72／p73 三份 manifest 都验证不到 37e，必须等 policy 74 第一枪。

### 状态界定
- **源码已修复**：形状判据＋manifest 栏位＋三个 env。
- **实机增益＝零**：p71–p73 三段的 `violated` 本来就出自 pixel-motion（那三份 manifest 里没有 geometry 栏位）。
- 判据可用性已被 37f 一手数据否决为「只能 advisory」，见 §37f。

### 本轮新增探针（可复用）
`working\_r37e_frame_cache.py`、`_r37e_geometry_probe.py`、`_r37e_phase_probe.py`、`_r37e_silent_probe.py`、`_r37e_variants.py`／`_variants2.py`／`_variants3.py`（灰阶暗带 swing 的各种变体：平滑、自动配准、高-中心分解、phase-lock、control-relative，全部否决）。

## 37f. Round 37f（2026-10-28 12:25–12:56 离线＋修码＋测试）：policy 73→74 —— **负面条款已饱和**，改官方模板里那五句**正面**许可；同时用密集采样把 §37e 的口腔形状闸门从 `on` 退回 `advisory`（**源码已修复，实机未跑**）

### 根因（一手，离线）
1. **负面侧没牌了**：p71／p72／p73（seed 923010107／923010207／923010307，共 27 次生成）每段都带完整 SILENT LISTENER 合约＋medium 强化＋§37c 改写后的嘴句＋plate silent clause；p73 的 `prompt_budget = {prompt_chars: 11731, char_budget: 12320, dropped_tail_clauses: [], over_budget: false}` ⇒ 句子一封都没被预算丢掉，画面照样对嘴。
2. **还在授权对嘴的是官方模板的正面句**：`whose performance comes from the person being replaced in <Video 1>`、`transferring their complete visible performance`、`identity through every expression`、`Hair and clothing move naturally with the transferred performance`、`Retain the source clip's existing sound…`。

### 改码
- `character_swap_engine.py`：新增 `AUTHOR_PROMPT_SILENT_PERFORMANCE_REWRITES`（五组 `anchor → replacement` ＋ marker），`_author_prompt_with_silent_mouth()` 先套 §37b 嘴句替换、再逐条**就地改写**（`marker in silent or anchor not in silent` ⇒ 跳过）。只加词不换段 ⇒ 不新增段落、不改条款顺序、重编译／重放 Job 幂等；只在 `silent_mouth=True` 生效，说话镜头保留原句。`retention_analysis` 那句 `…as the character performs the source person's movements.` **故意不动**——`AUTHOR_PROMPT_WARDROBE_LOCK` 插在其后，动它就会静默丢掉衣柜锁。
- `smart_render_worker.py`：口腔形状默认 `on → advisory`；`gate` 三态化（`mouth_cavity_geometry_with_pixel_motion_fallback` / `pixel_motion_with_cavity_geometry_recorded` / `pixel_motion`）；修掉两处残留（env 为空或非法时仍落回 `on`，应落 `advisory`）；§37e 的两段注释按本轮数据改写。
- `director_cut_studio.py:727`、`smart_render_worker.py:116`：`SMART_RENDER_POLICY_VERSION 73 → 74`，两处都补了 policy 变更说明（73 的说明此前缺失，一并补上）。

### 长度实测（决定还能不能加句子的硬约束）
| 量 | 实测值 | 来源 |
| --- | --- | --- |
| 最重 silent pass（`SHEET_CLOSEUP_SPEC`，S8/S9 型）unbudgeted | **12 956** chars | `working\_r37f_len_probe2.py` |
| 已验证可提交的预算 | **12 320** | `CHARACTER_SWAP_PROMPT_CHAR_BUDGET` |
| 必须丢掉 | **636** | 同上 |
| guard rank-1（`close_up_silent_mouth`）能买到 | **638** | 同上 |
| 改写前／改写后的实际剩余余裕 | **14 → 2** chars | 把改写表设空再 build 一次 |
| 改写表成本 | 净 **+12**（＋5／−4／−15／0／＋26） | `working\_r37f_rewrite_probe.py` |
| drop 概况 | 改写前后都是 `['close_up_silent_mouth']`，`SOURCE COSTUME BELONGS TO THE ERASED ACTOR` 都在 | 测试断言 |

⇒ 纪律：这条 spec 上**再多 3 个字的 silent 条款**就会连 rank-3 `source_costume_leaves_plate` 一起丢（S4 衣服复辟的成因）；`12320` 不能当旋钮调。

### 否决 §37e 的密集采样（9 格，24 fps＋5 帧平滑）
| | seg0 | seg1 | seg2 |
| --- | --- | --- | --- |
| p71 生成侧「真嘴行 swing／最吵非嘴行」 | 1.73 | 2.53 | **1.26** |
| p72 | 2.08 | 1.98 | 5.39 |
| p73 | **1.41** | **1.53** | 1.80 |
| 静音 plate 的 mouth／noise | 0.0462／0 | 0.0769／0 | 0.1000／0 |

产物 `_dsh_verify_9\round37\r37f_dense.txt`（12:34）与本轮复跑 `_r37g_dense_rerun.txt`（12:55，`fc /B` **逐字不差**）。结论：margin 1.60 之下 **9 段里至少 3 段真在说话却判合格**（p71 seg2、p73 seg0／seg1）；而**不说嘴的源片** mouth 0.046–0.100 全部越过 0.020 floor ⇒ 还会把静音 plate 判成违规。两个方向都错，`on` 不能用；数字仍入 manifest 供离线 A/B。

### 测试与备份
- `test_character_swap_engine` **79 OK**（新增 3 项；`test_silent_performance_rewrites_stay_inside_the_measured_length_slack` 不 pin 死数字，而是把改写表关掉重建同一条 pass、实测 `cost ≤ 余裕`）；`test_silent_mouth_motion_gates` 9 OK；`test_silent_mouth_transient_qc` **3 OK**（§37e 遗留失败自动恢复）；`test_character_swap_closeup_gates`＋`test_character_swap_background_extra`（与前者合计 171 OK）；`test_smart_render_worker`＋`test_storyboard_segment_mapping` **63 OK／1 skip**；三个主档 `py_compile` 通过。
- 备份 `_backup\r37f_20261028_pre_silent_performance_rewrite\`（engine／worker／studio／CHANGELOG／HANDOFF／两个测试档）。VERSION 维持 `0.3.8-alpha.3`，Project Format 29，**Policy 74**，sheet engine 8。

### 回滚开关
- QC：`H3_CHARACTER_SWAP_MOUTH_GEOMETRY=on` 回到 §37e 行为；`off` 完全跳过形状算术；margin／floor 同名 env 可调，只读 process env。
- prompt：本轮**没有 env 开关**（改的就是提交给 H3 的文字本身），回滚＝从 `_backup\r37f_…` 还原并把两处 policy 改回 73。旧开关（`…_WARDROBE_AUDIT`／`…_HAIR_BAND_MODE`／`…_FIGURE_EXTENT`／`…_HAIR_HALO`／`…_IDENTITY_MASK_MODE`／`H3_IDENTITY_SHEET_SINGLE_FIGURE_PASSTHROUGH`）不变。

### 已否决 vs 还没试
- **本轮新否决**：把口腔形状 swing 当判决（§37e）；「继续往 silent 尾部堆句子」（余裕只剩 2 chars，堆一句就掉 rank-3 衣柜条款）。
- **还没试**：① **policy 74 第一枪**（建议 seed `923010407`，silent Shot 用 S2 型 medium box `[0.35,0.15,0.65,0.45]`，判据＝不再对嘴且 identity／衣服不退步；跑前先 `working\_r35e_preview_rebuild_check.py <SEED>`）——**需要新的用户批准**；② 真实**闭嘴**样本仍为 0，要扫两项目已授权 silent output 做 head montage 肉眼定阈值；③ **VLM QC**：`source_video_analysis.py` 已有 LM Studio contact-sheet 路径（`design_ai.env`：`H3_DESIGN_LM_STUDIO_MODEL="iq3_s"`，base `http://127.0.0.1:47831/v1`），但 `smart_render_worker.py` 从不调用 ⇒ 需 driver 在 post-`/free` 窗口分阶段载回 Qwen，成本／与重抽的互动先设计；④ 生成端非 prompt 机制（口部锁定、头饰衣柜后处理、换生成策略）。

### 状态界定
- **源码已修复**：五句正面改写（79 项测试证明文本正确＋幂等＋不伤条款预算）；QC 默认退回 advisory；policy 73→74。
- **视频已实机验证＝未通过／不适用**：policy 74 一枪都没跑过。「Silent Listener 不再对嘴」目前是**假设**；p71/p72/p73 仍是对嘴的既有证据。

### 本轮新增探针（可复用）
`working\_r37f_regscan_probe.py`／`_regscan_probe2.py`（manifest 里 geometry 栏位有没有落地）、`_r37f_prompt_mouth_scan.py`（job 内文逐句扫嘴／性能／声音声明）、`_r37f_dense_probe.py`（24 fps 密集取样；本轮复跑 `_r37g_dense_rerun.txt`）、`_r37f_author_anchor_check.py`（五个 anchor 是否仍在官方模板）、`_r37f_rewrite_probe.py`（anchor 命中＋幂等＋禁用词＋改写后逐句列出）、`_r37f_len_probe.py`／`_len_probe2.py`（改写表成本、unbudgeted 长度、drop 概况、降预算看下一个被丢的条款）。

## 37g. Round 37g（2026-10-28 12:55–13:05 离线；**无产品码改动**）：密集取样复跑证明 §37f 的「口腔形状 swing 不可当判决」不是取样运气（`fc /B` 逐字不差）

- 只做一件事：同一支探针 `working\_r37f_dense_probe.py`、同一批 p73 素材（`00_save`／`01_save`）复跑，输出 `_dsh_verify_9\round37\r37g_dense_rerun.txt`，与 37f 的 `r37f_dense.txt` 用 `fc /B` 比较 ⇒ **逐字节相同**。确定性成立，单次取样偏差这条怀疑被排除。
- 复述内容（供以后引用，不用再跑）：生成侧 101–102 帧 @24fps、5 帧平滑窗口下，**每一行 row band** 的 cavity 读数都在 0.10–0.60，最噪的非嘴行与真嘴行相差 ≤0.05（seg0 `00_save`：真嘴行 0.615，非嘴峰 0.557／0.523／0.508）；同一算法在 plate 侧只有 0.000–0.100，且 plate 的 dark-row 剖面有稳定的「下颌暗带」结构（peak 0.54）。⇒ 形状算法**对 plate 诚实、对 Relay 重画过的头不可读**。
- 影响：`H3_CHARACTER_SWAP_MOUTH_GEOMETRY` 默认停在 `advisory` 是对的；37h 可以放心用 policy 74 开枪，因为判据的可疑项已经清掉。
- **状态界定**：源码未变（policy 74，37f 的五句正面改写）；本轮不产生视频结论。

## 37h. Round 37h（2026-10-28 13:05–13:30 实机＋读帧＋离线复核）：policy 74 首枪 seed 923010407（3 段 ×3 次生成）—— 五句正面改写**确实提交到 ComfyUI**，但**三段真嘴全开（见牙齿／舌头）**（**视频已实机验证＝未通过**）

**实机（GPU 三硬约束都守住）**
- 一条 `python staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923010407_….job.json"` 跑完：manifest `…\project\render_jobs\preview_923010407_1793163682376883900.manifest.json`，driver 日志 `_dsh_verify_9\round37\round37h_policy74_shot.log`（+ `.err`）。跑后 `/free` 由 driver 内建，Qwen 由 tray 载回。
- 三段配置确认：`speaker=False`、`silent_audio_strategy=audio_stripped`、`reference_framing=illustrated_full_design`、`identity_sheet_single_figure_passthrough=True`、`target_media_id=P1`（单图直通 ⇒ 本轮没有 identity sheet 变量混进来）。

**判定（读帧，不看 QC 自评分）**
- `working\_r37h_true_mouth.py`／`_r37h_source_mouth.py` 出图：`_dsh_verify_9\round37\p74_frames\p74_s{0,1,2}_true_mouth_gen.png`、`true_mouth_crops\montage_true_mouth.png`（0.5/1.0/1.5/2.1/2.7/3.2/3.7 秒）——**三个 segment 的生成嘴都是张开的，含牙齿与舌头**；同位置的 plate crop `*_true_mouth_plate.png` 嘴是闭的。⇒ 「silent listener 不再对嘴」在 policy 74 下仍然失败。
- identity：`target_reference_similarity` = 0.607109／0.555407／0.509169，均值 **0.5572**（p73 = 0.5595）⇒ 同分布：改写没有伤害身份，也没有改善身份（用 target sim 判 policy 好坏仍是已否决事项，这里只当回归检查）。
- wardrobe：`wardrobe_shift` = 0.1539／0.1823／0.1685，全部 > 门槛 0.12 ⇒ 闸门过；但肉眼看 `p74_vs_reference.png`，源角色的**猫耳头箍＋黑长假发＋镶金清装袍**污染依旧存在（未解）。
- policy 74 的 QC 新栏位实机落地确认：`gate="pixel_motion_with_cavity_geometry_recorded"`、`geometry_mode="advisory"`、`decision_basis="pixel_motion"`。seg2 被判违规后重抽 3 次仍失败（`failure_class="silent_mouth_excessive_articulation"`），最终退回 `00_save.mp4`。
- `working\_r37h_identity_sheet.py` 确认本轮参考图是单张 P1（无 sheet 版面），`_r37h_dense_probe.py` → `r37h_dense.txt`、`r37h_montage.txt`、`r37h_source_mouth.txt` 是配套剖面／拼图证据。

**当轮的错误判读（由 37i 推翻，登记以免复活）**：当时看到 `source_motion≈0.11` 便解释成「plate 被 blur 后剩下的头部漂移」，于是认为闸门基准干净。37i 证明那个基准根本不是 plate。

**状态界定**
- **源码已验证正确**：37f 的五句改写（79 项测试）＋ policy 74 的 QC 栏位（实机 manifest 可见）。
- **视频已实机验证＝未通过**：三段仍对嘴；identity 未改善；猫耳／假发／清装袍未解。

## 37i. Round 37i（2026-10-28 13:35–13:40 离线；**诊断完成，未改码**）：推翻 37h 的 QC 判读 —— silent 闸门比的是**会说话的 RAW V1**，不是 H3 真正看到的 plate；顺带首次量化 P1 张嘴这件事

**一手量化**（`working\_r37i_qc_source_probe.py` → `_dsh_verify_9\round37\r37i_qc_source.txt`；嘴带 `[0.425, 0.306, 0.575, 0.414]`，与 manifest 的 `bbox_normalized` 逐字一致；7 点取样，`robust_temporal_frame_motion`）

| seg | QC 记录 `source_motion` | 重算 RAW relay（audit 的 source） | 重算 `00_source.mp4`（H3 实际 plate） | 重算 generated |
|---|---|---|---|---|
| 0 | 0.109043 | 0.121526 | **0.057028** | 0.183781 |
| 1 | 0.113240 | 0.108445 | **0.073365** | 0.269586 |
| 2 | 0.110444 | 0.105513 | **0.056258** | 0.236693 |

**结论（三条都推翻过东西）**
1. `identity_audit.source_video_path` = `.director_cache\source_remake_relay_video\v1_relay_a2ab54ce555f03ec7471_0.000-4.288.mp4`，由 `director_cut_studio.py` 的 `_source_remake_relay_source_clip()` 产出，ffmpeg 只做 `fps=24,setpts` ⇒ 它是**会说话的 RAW V1**。silent 的 cap = `max(0.055, source*1.5+0.012)` ⇒ 这道闸门只能回答「有没有比会说话的源片更会动」，**结构上回答不了「有没有闭嘴」**。
2. 生成的嘴带运动是 plate 的 **2–4 倍**、RAW V1 的 **1.6–2.4 倍** ⇒ 两个旧解释同时死掉：既不是「QC 基准被 blur 污染」，也不是「模型忠实转移了源片的说话表演」。
3. plate 的路径在 `identity_audit` 里**根本没有**，只在 manifest `uploaded[1].file` 以档名出现（`v1_relay_…_identity_suppressed_<token>_silent_<token>.mp4`；silent 版另由 `_character_swap_silent_audio_source()` 产出）⇒ QC 无从量到真正的模型输入，这是 37j 第 3 件套（`plate_video_path`）的直接由來。
- 附带：`_r37i_qc_source_probe.py` 顺手裁出 `p74_frames\p1_reference.png`／`p1_face_zoom.png` 供 37j 肉眼确认 P1 是大笑张嘴。

**状态界定**：源码未改；本轮交付的是「判准在量什么」的定义修正，以及 plate 冻结这个方向的动机。

## 37j. Round 37j（2026-10-28 13:41–14:10 离线＋读图；**诊断＋设计完成，未改码、未开枪**）：prompt 侧已彻底打光 ⇒ 再加文字没有正当性；唯一未试的非 prompt 杠杆是 **plate 嘴带时域冻结**

**A. 这个项目的 prompt 侧没有死角，而且不是预算卡住**
- `working\_r37j_manifest_probe.py`（扫 manifest 字段与 pass 记录）＋ `working\_r37j_prompt_probe.py`（headless 重组 Preview Job，从 `workflow` 里抓出**实际提交**的 prompt 再逐句扫嘴；副作用：多了一颗无害的 `preview_923010407_1793166170011720500.job.json`）。重组文本与 manifest 记录**逐字一致** ⇒ policy 74 确实到了 ComfyUI。
- `prompt_budget = {'prompt_chars': 11743, 'char_budget': 12320, 'dropped_tail_clauses': [], 'over_budget': False}`（三段同值）⇒ **还有 577 chars 余裕**。这一点很重要：shirt_9 的 `SHEET_CLOSEUP` pass 只剩 2 chars，那个项目「加句子会挤掉 rank-3 衣柜条款」的顾虑**不适用于本项目** ⇒ 这里还对嘴，不是因为句子被丢，也不是因为句子不够多。
- prompt 内已有 **23 句**嘴相关条款，其中「参考图嘴形剥离」三句早就在（`Picture 1 may itself be drawn mid-laugh with an open mouth: copy that Picture's identity, not its mouth.` / `Picture 1 supplies identity but never supplies an open-mouth pose, smile, visible teeth, tongue or speaking expression.` / `Even if Picture 1 is smiling or has an open mouth, reconstruct that same identity with relaxed closed lips for the whole Shot.`）。
- 已知未处理小项：locator 行仍带作者原文 `R1: Juggling orange balls while smiling at camera`，这是一句「笑」的正面授权。

**B. P1 参考图肉眼确认＝大笑张嘴**：已看过 `_dsh_verify_9\round37\p74_frames\p1_reference.png`（252×370）与 `p1_face_zoom.png` —— 秃头＋三根毛、浓眉、圆眼镜、**嘴大张露齿露舌**、黑蓝上衣＋黄格短裤。模型张嘴最可能的来源是图 conditioned，与 37i 的量化（生成比 plate 动 2–4 倍）自洽。

**C. 已设计好、尚未落地的三件套（policy 74→75）**
1. **共享嘴带定义**：`MOUTH_BAND_REGISTRATIONS`（worker 行 1258-1277）＋ `_mouth_band_registration`（行 1280）搬到 `character_swap_engine.py`（该档只 import stdlib，安全），worker 保留向后别名（`working\_r37e_*.py`、`_r37h_dense_probe.py` 从 `smart_render_worker` import；`testing\test_smart_render_worker.py:128`、`testing\test_silent_mouth_transient_qc.py:82` 依赖嘴带行为）。已验算 box `[0.35,0.15,0.65,0.45]` → `head_crop` → `[0.425,0.306,0.575,0.414]`，与 manifest 逐字相同。Studio 与 worker 从此量的是同一块肉。
2. **plate 嘴带时域冻结（本轮主轴）**：`director_cut_studio.py` 的 `_character_swap_identity_suppressed_source()` 内，对已 blur 的头带之下再裁出嘴带做 ffmpeg `tmix=frames=K`（预设 K=7；语嘴 2–6Hz、头部漂移 0.5–1.5Hz ⇒ 低通杀前者留后者）。env `H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE`（预设 on，`off` 回滚）；**只对 silent pass**；**必须写进 plate 的 cache token**（base_token 与第二层 token），并把 `{applied, band, registration, tmix_frames}` 写进 `identity_suppression_geometry`，让它自动进 pass 记录与 manifest。
3. **QC 诚实化**：Studio 在 `identity_audit` 加 `plate_video_path`；worker `inspect_character_swap_identity()` 加测 plate 嘴带 ⇒ `plate_motion`、`plate_relative_motion_limit`、`plate_relative_verdict`、`source_speech_conflict`、`verdict_scope="relative_to_source_performance"`；预设 **advisory**（只记录、不改 `violated`、不增加重抽），env `H3_CHARACTER_SWAP_SILENT_PLATE_GATE=on|advisory|off`。
4. 政策版号两处 74→75；开枪前必跑 `working\_r35e_preview_rebuild_check.py <SEED>` 到 **VERDICT OK**；离线证明＝对 p74 的 RAW relay 剪段跑新 plate 建置，同一 `robust_temporal_frame_motion` 算术量嘴带 motion（应从 0.056–0.073 → ≈0.01–0.02）。

**状态界定**
- **源码已修复**：本轮**无**产品码改动（仍是 37f 的 policy 74）。
- **视频已实机验证**：不适用（37j 没开枪）；p74 三段对嘴仍是现行证据。下一枪建议 seed `923010507`／policy `75`，**需要新的用户批准**。

## 37k. Round 37k（2026-10-28 14:12–15:10 修码＋测试＋真素材离线 A/B；**源码已修复＋离线 A/B 通过，影片未实机**）：把 silent plate 的嘴带**时域冻结**，让 QC 改读「模型真正看到的 plate」而不是会说话的 RAW V1；policy 74→75

**A. 本轮落地的四处产品码改动（全部已写入、已验绿；详细表格见 CHANGELOG.md `### Round 37k`）**
1. `character_swap_engine.py`：`MOUTH_BAND_REGISTRATIONS` / `mouth_band_registration()` / `mouth_region_bbox()` 从 worker 搬来，成为 **plate 建档与 QC 审计共用的同一把尺**（worker 保留向后别名，旧探针与测试不破）。手算 box `[0.35,0.15,0.65,0.45]` → `head_crop` → `[0.425, 0.306, 0.575, 0.414]`，与 p74 manifest 逐字相同。
2. `director_cut_studio.py`：`_silent_plate_mouth_freeze_settings()`（917 行）＋ plate 组装时把嘴带 `tmix=frames=K` 链放在**所有 blur 之后的最后一段**（`_mouth_freeze_chains`，36509 行）＋ `identity_audit["plate_video_path"]` 写入实际 plate 路径（~37126 行）＋ plate recipe 文件名加入 `mouthfreeze=…｜frames=N` 标签（缓存不会串臂）。env `H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE`（预设 **on**）／`..._FRAMES`（预设 **7**，clamp 2–60，**import 期解析**）。
3. `smart_render_worker.py`：`_silent_plate_gate_settings()`（1376 行）＋ 嘴带审计新增 `plate_measured`／`plate_motion`／`plate_relative_limit`／`plate_relative_violated`／`source_speech_conflict`／`verdict_scope`／`decision_basis`；判定顺序 plate-on → geometry-on → pixel_motion。env `H3_CHARACTER_SWAP_SILENT_PLATE_GATE=on|advisory|off`（预设 **advisory**）／`_MOTION_GAIN`（1.5）／`_MOTION_FLOOR`（0.012）。
4. Smart Render Policy **74→75**（`smart_render_worker.py` 129 行、`director_cut_studio.py` 741 行，两处都附理由注释）：plate 提交物与 QC 基准同时改变 ⇒ p74 的 manifests 视为 stale。

**B. 非换尺不可的一手证据（p74 manifest，`preview_923010407_*.manifest.json`）**
- 三段几何完全相同：hard head blur 只到 `y 0.285`，QC 注册的嘴带是 `[0.425,0.306,0.575,0.414]` ⇒ **嘴带落在衣襬 `boxblur=6:3` 内，不在头部硬模糊内** ⇒ p74 的 plate「脸糊了、嘴没动」。
- 三段 `silent_mouth_audit.plate_video_path` 全是 **None**：当时 silent 闸门读的是 `identity_audit.source_video_path`，也就是**会说话的 RAW V1**（`source_motion` 0.109／0.113／0.110），而 Relay 真正看到的是安静得多的 plate。基准与条件不是同一支影片，契约必然对不上。
- p74 三段 `result_motion` 0.184／0.270／0.237，`maximum_motion` 0.1756／0.1819／0.1777：只有 seg2 因 `result > upper_relative_limit` 落败；seg0 靠眼睛带控制区（0.1399）逃过，符合 §37d「道具经过嘴巴」而非嘴的结论。

**C. 真素材离线 A/B（`working\_r37k_offline_proof2.py` → **VERDICT OK**，输出 `working\_r37k_proof2c_out.txt`；无 GPU／无 ComfyUI／无 Qwen）**
plate 由**产品码** `DirectorCutStudio._character_swap_identity_suppressed_source(Path, spec, enabled=True)` 在 p74 同一批 relay 上重建，只 patch `CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE_MODE`；取样器与指标就是 QC 自己那套（`_extract_identity_gray_frame` + `robust_temporal_frame_motion`，比例 0.12…0.88、80px）。策略字符串必须等于 p74 的 `medium_silent_listener_identity_suppressed_wardrobe_blur_suppressed`，否则直接 FAIL。

| seg | raw V1 嘴带 | plate freeze=off | **plate freeze=ON** | p74 take 嘴带 | take 眼睛带 | 上限(off) | **上限(ON)** |
|---|---|---|---|---|---|---|---|
| 0 | 0.1215 | 0.0578 | **0.0358** | 0.1954 | 0.1701 | 0.0987 | **0.0656** |
| 1 | 0.1084 | 0.0726 | **0.0398** | 0.2799 | 0.1187 | 0.1209 | **0.0716** |
| 2 | 0.1055 | 0.0660 | **0.0369** | 0.2369 | 0.0569 | 0.1110 | **0.0673** |
| 平均 | 0.1118 | 0.0655 | **0.0375** | 0.2374 | 0.1152 | 0.1102 | **0.0682** |

- 冻结把**被审计的那条带**降 1.75×（0.0655→0.0375），三段全部跌破 silent 契约地板 0.055；对一支真的会动的 take（0.2374）安静 6.3×；plate 相对上限从 0.1102 收到 0.0682。六项 checks 全 PASS（含「两臂产生两个不同 plate 文件」「band 只在 on 臂记录」）。
- 量测口径：**1.75× 不是失败**。单测那块 4 帧 6 Hz 方波能衰到 0.129（7.1×）是因为它只有 4 帧；`tmix=7` 在 4.3s 实片只覆盖约 0.23s，头部摇摆、头发、道具都会在 0.15×0.11 的带内存活。目标从来不是归零，而是**让 plate 安静到足以当基准**。
- 探针踩过的坑（复用前必读）：① plate 建档会把 `identity_suppression_geometry` 写进**你传进去的那个 dict** ⇒ 每臂必须 `json.loads(json.dumps(spec))` 从副本读，读原 spec 只会看到最后一臂（旧探针印出 `{}` 的原因）；② freeze 审计键名是 `tmix_frames` 不是 `frames`（`director_cut_studio.py:36274`）；③ Job 里**没有** `source_roles`，flat 的 `source_role_ids`／`source_bboxes_normalized`／`body_bboxes_normalized` 只存在于 `segments[i].character_swap_passes[0].identity_audit`（26 keys），而 `_character_swap_identity_suppressed_source` 需要 `pass_spec["source_roles"]`（row 带 `source_bbox_normalized`）⇒ 手建即可，面积 0.09／高 0.30 会走 **medium_silent** 闸门（非 close-up）；④ 旧版 `_r37k_offline_proof.py` 已弃用（`str` 型 source 会 `AttributeError`）。
- 另外两个 ffmpeg 坑（曾烧光测试 180s timeout）：纯色来源颜色必须写满 `0xRRGGBB`（`0xFA` 被拒）；plate mask 模式 `-loop 1` + `-shortest` **来源无音轨时永不结束** —— 产品来源都带音轨所以实机正常，属**潜在风险，本轮只写进测试注释未改产品码**。`boxblur=18` 还要求 crop 后色度面 >36px，太小的 plate 会无声退回 raw V1（既有行为）。

**D. QC 行为的实际变化（含代价，这是下一枪要验的）**
- p75 Preview Job 重组检查 `working\_r35e_preview_rebuild_check.py 923010507` → **VERDICT OK**，产出 `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923010507_1793170434349510200.job.json`：policy **75**、3 段、三段 `identity_audit` 都带上 `plate_video_path`（silent-audio 变体 hash 已与 p74 不同 ⇒ 冻结确实进了 recipe）、prompt 11743／12320 chars 无丢条款。
- 若把闸门切成 `on`：按上表 plate 基准，p74 三段 take 会 **3/3 被判输**（上限 0.0682），但其中 **1/3 通过眼睛带控制区** ⇒ 仍会为一支「只是道具经过嘴巴」的好 take 白花一颗 fresh seed。这就是本轮维持 **advisory** 的理由，也是下一枪要用真 take 替 plate 相对数值定级的原因。

**E. 状态界定与回滚**
- **源码已修复**：嘴带共用尺、plate 嘴带时域冻结、QC plate 参照与诚实字段、policy 75。测试一手数字：`test_character_swap_closeup_gates`+`test_character_swap_background_extra` **85 OK**；`test_character_swap_engine`+`test_silent_mouth_motion_gates`+`test_silent_mouth_transient_qc` **91 OK**（新增 `SilentPlateRelativeGateTests` 6 测）；`test_smart_render_worker`+`test_storyboard_segment_mapping` **63 OK（1 skip）**＝基准；本轮末再以三模块合并跑一次 **Ran 94 tests / OK**（`working\_r37k_tests_final_err.txt`）。`py_compile` 三档 rc=0；`test_director_timeline` 会挂起，依惯例跳过。
- 写测试时必须知道：plate 建档读的是 **import 期常数**，所以 patch 冻结开关要用 `patch.object(studio_module, "CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE_MODE", mode)`，`patch.dict(os.environ, …)` 无效。
- **影片已实机验证＝尚未**：p74 仍是「silent listener 依然对嘴」的现行证据，本轮没有任何新影片，也没有碰 GPU。
- 回滚（纯环境变量，不改码）：`H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE=off` ⇒ plate 回到 p74 形状；`H3_CHARACTER_SWAP_SILENT_PLATE_GATE=off` ⇒ QC 回到只读源片；prompt 侧若要还原用 `_backup\r37f_20261028_pre_silent_performance_rewrite\` 并把 policy 改回 73。
- **已否决清单新增**：把 plate 冻结目标设成 ≤0.02／5× 衰减（实片上 `tmix=7` 只覆盖 ~0.23s，1.75× 已是正确落点；正确目标是「跌破 0.055 地板 ＋ 能当基准」）。
- 下一枪提议 **seed `923010507`／policy `75`**，一条 `python staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923010507_1793170434349510200.job.json"`；**尚未开枪，需要新的用户批准**。

## 37l–37p. Round 37l–37p（2026-10-28 15:30–20:20 修碼＋測試＋實機兩槍；**源碼已修復＋影片已實機驗證＝用戶接受**）：policy 75→76→77；76 是測出來的零增益，77 讓重試排名不再用「最像 P1」獎勵一張張開的嘴

**A. 本節落地的兩處政策改動（詳表見 CHANGELOG.md `### Round 37l–37p`）**
1. **policy 75→76（措辭）**：silent 條款**去語音化**。讀取端點真的收到的 prompt，speech／speaker／audible／voice／audio 出現 5 次且**全是正面語句**（"the speech is off screen"／"which is why <Video 1>'s audible speech keeps pulling the lips open"／"not the audible speaker"／"Every audible voice in this Shot … is background sound"）⇒ 用來壓嘴的句子同時是整段 caption 裡唯一證明「這 Shot 有可聽語音」的證據。改成本專案已驗證的 speech-free 說法：宣告人聲頻道為空。政策註解在 `smart_render_worker.py` 129–149 行。
2. **policy 76→77（排名）**：`smart_render_worker.py` 新增 `SILENT_ARTICULATION_PENALTY_WEIGHT = 8.0`／`_CAP = 0.35`（185–186 行）、`_silent_articulation_excess()`（1881 行，讀 `result["silent_mouth_audit"]["rows"][*]["articulation_excess"]` 最差值；**未受審回傳 `None` 不是 0.0** ⇒ speaker Shot 與舊 Job 排名不變）、在 `_candidate_target_likeness()` 扣分（1865–1869 行）、重試預算耗盡事件補印每候選 `silent_articulation_excess`＋`target_likeness_score`（~4012 行）。政策號兩處：`director_cut_studio.py` 777 行／`smart_render_worker.py` 169 行。`VERSION` 維持 `0.3.8-alpha.3`，Project Format 維持 29。

**B. p75／p76 是同 seed 923010507 的乾淨 A/B（三條 pass seed 相同，只差措辭）⇒ 76 判定為 null result**
被選 take 的 `articulation_excess`：seg0 0.0477→**0.0591**、seg1 0.0797→0.0489、seg2 0.0589→**0.0675**；兩個有重試的段落反而更動（+24%／+15%），silent 判定兩邊一模一樣（seg0／seg1 `violated=False`、seg2 `violated=True`），三段 `decision_basis` 都是 `pixel_motion`、`maximum_motion` 仍是 V1 嘴動 ×1.6。

**C. 本節挖到的三條結構性事實（manifest 一手欄位，下一節要動的就是這些）**
- `silent_mouth_freeze.applied: true`（mode on／tmix 7／head_crop）**只作用在 plate**：`director_cut_studio.py:36301` 只是記錄，plate 建圖在 36509 行 `_mouth_freeze_chains`。plate 嘴動 0.039–0.048，**生成結果 0.210–0.267 已大於 V1 原片 0.110–0.113** ⇒ 是 H3 自己把嘴畫動，不是複製 plate。「plate 凍結＝不會對嘴」自此列為已否決。
- 若把 silent 合格判定改成 **plate 相對**：plate 基準上限 0.0762／0.0707／0.0834 ⇒ `plate_relative_violated` **三段全 true**，只是 `plate_gate_mode=advisory` 不生效 ⇒ 這解釋 seg1 為何 artic 0.0855 還 `passed=True`。
- **P1 是露齒笑** ⇒ 相似度用色彩直方圖，天然奖励嘴張最大的 take。這是 77 只能減緩、不能根治的部分（根治＝閉嘴版 P1，需用戶供圖）。

**D. p77 實機（seed 923010607，0.5 MP，3 段全 `silent_listener`，`plate=True`，`roi=[[0.3,0.285,0.78012,1.0]]`）——seg2 排名翻轉是關鍵證據**
`working\_r37o_buildjob.py 923010607 0.5` 重建 → `preview_923010607_1793188535321641600.job.json`；`Start-Process`（隐藏、重導 `logs\r37p_run_923010607.out.txt`）跑 `staged_model_driver.py run`：`worker-exit code 0` → `comfy-free ok:true` → `vram-release`（before 3.01GB，模型已由 worker 自行釋放）→ `report` → `wait-qwen-reload ready:true`。成品 `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\cache\generated_outputs\preview\923010607\master.mp4`（12.86s，6580KB）。

seg2 三發候選（driver log 逐字）：a1 sim 0.5397／artic **0.0611** → likeness **0.2871 被選**；a2 sim **0.6115（最像 P1）**／artic 0.0846（最張嘴）→ 0.2073（舊排名 0.8844 會贏）；a3 0.5400／0.0817 → 0.0812。兩發相似度只差 0.004 而嘴動差 2×，75／76 兩次都選了最張嘴的。

被選 take 的 `articulation_excess` 三方對照：seg0 0.0477／0.0591→**0.0349**；seg1 0.0797／0.0489→0.0855（但 `attempts=1`，第一發就被 QC 接受，**從頭沒有可選**，77 無從介入）；seg2 0.0589／0.0675→**0.0611**。
**誠實標註**：75／76 同 seed 是純對照；**77 換了 seed ⇒ 非純對照**，所以「被選 take 較靜」不能全歸給 77；但 seg2 的**排名翻轉本身**是 log 逐字證明的機制事實，與 seed 無關。若用戶更看重像 P1，把 8.0 降成 4.0（4.0 下 seg2 舊贏家重新取勝）。

**E. 尚未動用的三個槓桿（已向用戶報告，未實作）**
- **A** silent 合格判定改 plate 相對（逼出重試，再由 77 挑最靜；`H3_CHARACTER_SWAP_SILENT_PLATE_GATE=on`，代價＝可能為一支「只是道具經過嘴巴」的好 take 白花 fresh seed）。
- **B** 把 mouth freeze 也套在**生成結果**上（確定性、不碰 prompt、不花 GPU 重抽）⇒ 若用戶回報「還是會動嘴」，**優先做 B**。
- **C** 閉嘴版 P1（需用戶供圖）。

**F. 測試／編譯（一手）** `testing\test_smart_render_worker` **Ran 65 OK (skipped=1)**；`test_storyboard_segment_mapping`＋`test_character_swap_engine` **Ran 84 OK**；`py_compile` 三檔 rc=0。⚠️ **全套 `unittest discover` 本輪未採集**：5 個不退出的 `design_ai_service.py` 子進程把 discovery 掛住（既有毛病，非本輪回歸），已終止 ⇒ 只交三模組綠燈，不宣稱全套通過。`test_director_timeline` 依慣例跳過。

**G. 狀態界定與下一步**
- **源碼已修復**：p76 措辭、p77 排名扣分＋候選欄印證。
- **影片已實機驗證＝通過（用戶接受）**：用戶回報「效果我接受」；本節验的是「**選到較靜的那發**」，`attempts=1` 的 Shot（如 seg1）仍可能第一發就張嘴 ⇒ 那屬 A／B 範圍，未被本節宣告治好。
- 用戶會自己在 Studio 點 Preview（0.5／1.0 MP），**不要主動佔 GPU**；要看新片用 `working\_r37p_scan.py <SEED>`（driver log 逐 attempt＋候補表）、`working\_r37p_qc3.py`（p75／p76／p77 manifest 三方表）、`working\_r37p_find.py`（找含 `silent_mouth_audit` 的 manifest）。
- 下一個新 seed 提議 **923010707**；每次開槍前都要新的用戶批准。
- 環境開關速查：`H3_CHARACTER_SWAP_SILENT_PLATE_GATE=on|advisory|off`（預設 advisory）、`H3_CHARACTER_SWAP_SILENT_PLATE_MOUTH_FREEZE`（預設 on）／`_FRAMES`（預設 7）、`H3_CHARACTER_SWAP_MOUTH_GEOMETRY`（advisory）。
- PowerShell 踩過的坑（本節新增）：`Start-Process -ArgumentList` 對**含空格路徑必須自己加引號**（``"`"$drv`""``），否則 driver 路徑被切開報 `can't open file 'D:\\minimax'`；`$pid` 是唯讀自動變數（改 `$procId`）；`if` 區塊結尾接 `|` 會 ParserError。
- 已用 seed：923010307／923010407／923010507（p75＋p76 兩槍）／923010607；`render_jobs\` 內另有 crash 殘留 job JSON（923000127／923001027／923009999／923010407），**勿誤用**。

## 38–38b. policy 78＝fullfig 單圖路由（2026-10-29，**源碼已修復＋影片已實機驗證＝部分改進、部分退步**）

**A. 本節為什麼存在**：用戶自己實測後換上新的 `H3-Character-Swap-Relay-V2-api.json`，並要求「改用 800×1216 的 `identitysheet08_fullfig` **單人**，node 7 目標改成 1.0 MP，其他照舊」。但專案裡 P1 原圖只有 **0.09324 MP**，policy 70 以來的「單圖直通」直接把這張小圖丟給 Relay ⇒ 参考 token 不足，身份細節最先被犧牲。本節的修法就是**小圖不再直通**。

**B. 源碼改動（全部已寫入、已驗綠）**

| 項目 | 位置 | 內容 |
|---|---|---|
| 地板常數 | `director_cut_studio.py` 約 1531–1573 | `_identity_sheet_min_source_megapixels()`／`IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS`＝**0.35 MP**；`H3_IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS=0` 或負值＝關閉 |
| 路由 | `director_cut_studio.py` 約 35060 起 `_character_swap_identity_sheet_reference()` | 用 `own["canvas"]` 算實際 MP；低於地板 ⇒ `single_figure_fullfig=True` ⇒ 強制 close-up 預設（引擎 8）＋ `outfit_view="full"` 全身衣柜视图，**不再單圖直通** |
| 取證欄位 | `IDENTITY_SHEET_DECISION_KEYS` | 新增 `identity_sheet_source_reference_megapixels`、`identity_sheet_single_figure_fullfig` |
| 政策 | `director_cut_studio.py:786`、`smart_render_worker.py:179` | **兩處同步＝78** |
| Workflow | `H3-Character-Swap-Relay-V2-api.json:24` | node `"7"` `ImageScaleToTotalPixels.megapixels` 2.0→**1.0**（用戶親測增益）。⚠️ 同目錄 `_OLD.json`／`-ori.json`／`.bak-*` 是歷史檔，**勿動** |
| 測試 | `testing\test_identity_sheet.py` | 新增 `HIGHRES_WAVING_CANVAS=(704,1034)` ＋ 3 項測試（低解析走 fullfig／地板=0 還原直通／預設地板生效） |

**C. 實機（GPU 三硬約束全程遵守；每槍都要用戶新的批准）**
- **923010707**＝只換 workflow 的 A/B，1 窗：lower wardrobe **0.0710 < 0.12 FAIL**、silent articulation **0.0（完美）**、target_sim 0.6016、attempts 3。⇒ 單窗不足以歸因換檔。
- **923010807**＝policy 78＋1.0 MP，0.5 MP×3 窗、12.86 s：worker-exit 0、`comfy-free ok`、VRAM 5.65→4.65 GB、三窗 `status=complete`、`attempts_used` 3/3/1。成品 `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\cache\generated_outputs\preview\923010807\master.mp4`。
- **路由生效的硬證據**：923010807 manifest 內 `identity_sheet_source_reference_megapixels=0.09324`、`identity_sheet_single_figure_fullfig=True`、`identity_sheet_preset=8`；923010607（p77 時建 Job）無此欄 ⇒ 前後對照成立。

| 窗 | wardrobe upper/lower（門檻 0.12） | 判定 | target_sim | attempts | silent artic（門檻 0.055） |
|---|---|---|---|---|---|
| W1 | 0.1090 / 0.0648 | FAIL(lower) | 0.6063 | 3 | 0.0 過 |
| W2 | 0.1134 / 0.1224 | FAIL(upper)＋silent violated | 0.6243 | 3 | 0.0038 violated |
| W3 | 0.1580 / 0.1228 | 全過 | 0.5309 | 1 | 0.0440 過 |

每 region `target_similarity > source_similarity` 在 923010607／923010807 **全部成立**；erasure／whole-body／plate 全過。

**D. 讀圖結論（`_dsh_verify_9\round38b\compare_ab.png`、`seam\seam.png` 親眼核對）**
- **改進**：衣柜主色轉黑色系（貼 P1 黑衫），V1 的粉紅袍＋貓耳不再出現；silent 對嘴三窗都比 923010607 同窗更靜。用戶上次報的「第 4 秒出現 character sheet 下半身」本槍**未重現**。
- **退步**：P1 的**大圓眼鏡**在 W2/W3 消失、臉變老（皺紋／法令紋）；W2 開頭 ≈4.2–4.5 s invented 黑帽＋長髮＋貓耳；衣柜細節仍是發明的紅金織錦滾邊，不是 P1 剪裁。
- **QC 與肉眼排序相反**：923010607 過閘但視覺更差；923010807 觸閘但衣柜更對 ⇒ `minimum_wardrobe_shift` 絕對地板對 medium shot 已失準。

**E. 狀態界定（不要把兩件事混在一起）**
- **源碼已修復**：低解析→fullfig 路由、決策欄位、policy 78、workflow 1.0 MP、3 項新測試。測試一手複驗：55＋76＋80＋65(skipped=1)＋25＋4 ＝ **Ran 305 OK**；`py_compile` 四檔 rc=0；`test_director_timeline` 依慣例跳過。
- **影片已實機驗證＝部分成功**：衣柜主色＋silent 變好＝可目視確認；**眼鏡遺失／臉變老尚未解決** ⇒ 本節**不得**寫成「角色替換已达标」。

**F. 下一步候選（單變量，開槍前要用戶批准；下一個新 seed ＝`923010907`）**
1. **(a)** 同 fullfig sheet、node 7 **改回 `megapixels: 2.0`** ⇒ 拆開本輪綁在一起的兩個變量，驗證「1.0 MP 讓参考 token 變少所以丟身份細節」這個假設。
2. **(b)** 保持 1.0 MP，**加第二張 close-up 頭部参考**到 `ref_images.ref_image_1`：`smart_render_worker.py:723–746 _canonicalize_reference_input_order` 已支援多槽＋連續重編號，但目前只接 `ref_image_0`，且要同步 prompt 的 Picture 語義。
3. **衣柜 QC 校準（離線，不花 GPU）**：把「絕對 shift ≥0.12」改成「target 明顯優於 source」的相對判定，避免對已經合格的好 take 白燒 3 次重試。
4. 遺留槓桿：plate 相對判定改 `on`、生成結果 mouth freeze、閉嘴版 P1（需用戶供圖）。

**G. 本節工具與坑**
- 探針：`working\_r38_buildjob.py <SEED> [MP] [MAX_SEG]`（**改 workflow／policy 後必須重建 Job**）、`_r38_manifest_qc.py <manifest>`、`_r38b_compare3.py`、`_r38b_targetsim.py`、`_r38b_montage2.py <seed...>`、`_r38b_seam.py <seed...>`、`_r38b_promptdump.py`（本槍 prompt 11 746 字元／預算 12 320，`dropped_tail_clauses=["plate_wardrobe_silent_clause"]`）、**本節新增** `working\_r38b_probe78.py <manifest...>`（直接印 policy 路由欄位＋逐窗 QC 摘要）。
- 啟動方式（可重現）：`$env:CODEX_THREAD_ID="01a1531f-18f6-7a93-886b-22195e0516a5"` 後 `Start-Process -WindowStyle Hidden` 跑 `staged_model_driver.py run "<abs job.json>"`，stdout→`working\_r38b_run_923010807.log`；tray 寫 `active_run.json` 並在完成後 auto-resume。
- 已用 seed 增加：**923010707／923010807**（下一槍 `923010907`）。⚠️ `unittest -p` 用 fnmatch，**不支援 `{a,b}` 大寫括號展開**（會靜默 `Ran 0 tests`），要逐模組跑。`test_staged_model_driver` 有一項會真的打 ComfyUI `/free`（空卡時無害，但別在 H3 跑到一半時跑它）。

---

## 40. Round 40（2026-10-29 22:47–23:12 實機三窗；**未改原始碼＋影片已實機驗證＝兩項已修、一項未修**）：workflow JSON 換檔 —— node 7 拿掉，改送 `RTXVideoSuperResolution`（ULTRA ×2）進 `ref_image_0`

**A. 這是 workflow 的改動，不是 code 的改動**
- 節點级 diff（vs `H3-Character-Swap-Relay-V2-api.json 261029-1`，`working\_r39_wfdiff.py`）只有三處：①砍 node `7`（`ImageScaleToTotalPixels` megapixels=1.0）②加 node `9` `RTXVideoSuperResolution`（`images=[reference,0]`、`quality=ULTRA`、`resize_type.scale=2.0`、`strength=1.0`、8-bit RGB）③`ref_images.ref_image_0 ← ["9",0]`。模板 `LoadVideo` 檔名換新片（對本專案無效，worker 逐段覆寫）。模型／VAE／LoRA／取樣器未動 ⇒ 對 923010807 是乾淨單變量 A/B。
- **policy 仍 78、VERSION 0.3.8-alpha.3、Project Format 29**；原始碼零改動 ⇒ 本輪不需要 unittest／`py_compile`。
- 遠端 `object_info/RTXVideoSuperResolution` 確認節點存在、欄位吻合。

**B. 「新 workflow 真的上線」的硬證據（不是離線宣稱）**
- `working\_r40_history_probe.py` 打 ComfyUI `/history/<prompt_id>`（`a86934b3…`、`6bf5bd30…`）：36 節點、node 9 在場且輸入完全吻合、`ref_images.ref_image_0 = ["9",0]`、整張圖已沒有任何 `*Scale*` 節點、`LoadImage` 仍是 `…_identitysheet08_fullfig_a0066_v8.png`。
- 幾何動機：sheet 800×1216（0.973 MP）裡**頭部面板只有 405×346**；×2 後 1600×2432＝3.89 MP、頭部約 810×692，而且是 ULTRA 智能放大（不是 nearest-exact）⇒ 直接對 38b 的「眼鏡消失／臉變老」。

**C. 目視判定（`_dsh_verify_9\round40\`：`faces\faces_ab.png`、`compare_ab.png`、`seam\seam.png`）**

| 項目 | 807（node 7，1.0 MP） | 907（RTX VSR ×2 ULTRA） | 界定 |
|---|---|---|---|
| 圓眼鏡／鬍子／臉齡 | W1 僅首格有眼鏡；W2、W3 全無，臉變老 | **W1 三格皆有圓眼鏡＋鬍子，臉變年輕** | ✅ 實機驗證（38b 兩項退步在 W1 已修） |
| W1│W2 邊界 invented 頭飾 | t≈4.5–5.0s 貓耳帽＋長黑髮＋真人臉 | 不出現 | ✅ 實機驗證 |
| 衣柜忠實度（P1＝黑上衣＋藍下襬＋黃格子短褲） | 三窗皆 invented 黑金長袍 | W1 黑藍袍紅帶；W2 棕針織袍；W3 黑袍藍襬；**僅 W3 t≈3.8s 出現真正的黑上衣＋黃格子短褲** | ❌ 未修（逐窗各自发明服装） |
| silent 閉嘴 | W2 excess 0.00376 | W1 0.0／W2 0.00157／**W3 0.0527（開合 0.275 vs 對照 0.0875）** | W3 未修 |
- 成本與 VRAM 無退步：907 九次生成 ≈25 min（807 七次 ≈37 min）；`/free` 實測 5.77→4.33 GB。產物 `…\cache\generated_outputs\preview\923010907\master.mp4`（11 041 424 bytes）。

**D. 挖到但尚未修的結構性根因**
1. `dropped_tail_clauses=["plate_wardrobe_silent_clause"]` 三窗全中：最終 11 746／12 320 只餘 574 字元，而該條 ≥575 字元 ⇒ 永遠塞不進去。它 rank 0 是歷史刻意安排（`character_swap_engine.py:153`、迴圈 2229–2247），前提是「衣柜義務由無條件 COMPLETE WARDROBE REPLACEMENT 分擔」；但 Silent Listener plate 現在連衣柜帶一起 blur，這條正是「plate 上糊掉的衣物色是故意的，不要照它重建服装」⇒ 與本輪三窗各自发明长袍高度吻合。
2. 衣柜 QC 絕對地板 `minimum_wardrobe_shift=0.12` 比的是**模糊後的 plate**，W3 row 同時寫 `target_similarity 0.513 > source_similarity 0.418`（已比源圖更像 P1）卻判 fail ⇒ 對合格好 take 白燒重試（本輪 3 窗全燒滿 attempts=3）。
3. `enable_rtx_vsr` 對 Character Swap pass 仍失效（只有 `workflow_engine.apply_generation_parameters()` 讀它，`character_swap_engine.compile_*` 從不呼叫）⇒ node 9 一律生效，Studio 那個勾選框對替换 pass 是裝飾。
4. `character_swap_engine.py:2307／2339`：`prepare["resolution"] = "768" if megapixels>=0.75 else "480"` ⇒ 0.5 MP preview 一直走 **480 bucket**，這是下一個身分細節槓桿。

**E. 下一步候選（各自要用戶批准；下一個新 seed ＝`923011007`）**
1. **(i) 最推薦**：把 768 bucket 門檻從 0.75 MP 降低（例如 ≥0.45 MP 就走 768），讓 0.5 MP preview 也吃 768 ⇒ 與本輪「把参考變大就變好」同一方向，policy 79＋測試＋一槍 A/B。
2. **(ii)** 讓 `plate_wardrobe_silent_clause` 活下來：從 never-droppable tail 压掉 ≥~120 字元（或把重複的 silent 措辭再壓短），policy 79＋測試；驗收视窗衣柜是否停止各自发明。
3. **(iii) 離線不花 GPU**：衣柜 QC 改成 target-vs-source 相對判定（修 D2），先離線回放 907／807 的 manifest 確認不再誤殺。
4. **(iv)** 决定 `enable_rtx_vsr` 的歸屬：要嘛接進 swap 編譯路徑（policy 79），要嘛宣告「模板即權威」並把 Studio 那個勾選框在 swap 模式灰掉。

**F. 本節工具與坑**
- 新增探針：`working\_r40_history_probe.py`（讀實際提交的 ComfyUI 圖）、`_r40_faces.py`（head-crop A/B）、`_r40_montage.py`／`_r40_seam.py`（round40 輸出目錄）、`_r40_prompt_probe.py`（逐窗預算／丢条款）、`_r40_retry_scores.py`（driver stdout 的候選分數）。
- ⚠️ `_r38b_montage2.py`／`_r38b_seam.py` 以**列索引**做影格快取檔名，換 seed 順序會無聲混入舊 seed 影格 ⇒ 换 seed 組合時一定要換輸出目錄。
- ⚠️ `Start-Process -ArgumentList` 不會自動加引號：含空白的絕對 job 路徑要寫成 `"`"$jobPath`"`"`，否則 `staged_model_driver.py` 收到半截路徑（本輪首次啟動就這樣失敗一次）。
- 已用 seed：**923010907**（下一槍 `923011007`）。Job 檔在成功後會被 worker 移除，只剩 manifest ⇒ 要看實際圖就查 `/history` 或 worker log。

## 41. Round 41（2026-10-29 23:20–23:55 離線修碼＋測試；**源碼已修復＋250 項測試通過，影片未實機**）：policy 78→79 —— 衣柜 silent 段落不再是 prompt 長度守衛的祭品

**A. 根因（用 Round 40 seed 923010907 的硬證據，探針 `working\_r41_prompt_sections.py`／`_r41_clause_lengths.py`）**

Silent Listener 的「plate 頭＋衣柜模糊」段落 `plate_wardrobe_silent_clause`（**847 字元**）在 `CHARACTER_SWAP_TAIL_DROP_RANKS` 裡是 **rank 0**（第一個被丟的條款）。907 的三個視窗提交 prompt 全部是 **11 746 / 12 320**，而這條 847 字元剛好就是超出的額度（超出 273）⇒ `dropped_tail_clauses=["plate_wardrobe_silent_clause"]` 三窗全中。後果：送進模型的 plate 頭像其衣柜顏色已被模糊，但 prompt 裡沒有任何一句話說明「那些顏色屬於被擦除的原始演員、不要照它重建服装」⇒ 模型逐窗自行發明服装（W1 黑袍紅腰帶、W2 棕色針織袍、W3 黑袍藍襬），这正是用戶回報的「衣服完全不像參考圖」。

同一批證據也顯示這次犧牲**沒換到東西**：該槍在保留 mouth reinforcement 的情況下 W2／W3 仍對嘴；模組註解另外記錄 seed 97000374 失去 reinforcement 照樣對嘴、97000454 保留 reinforcement 也照樣對嘴。所以「丟掉衣柜段落換嘴部提醒」這筆交易在實機上是**雙輸**。

**B. 改動（policy 78 → 79，三檔）**

| 檔案 | 內容 |
|---|---|
| `character_swap_engine.py` | `CHARACTER_SWAP_TAIL_DROP_RANKS` 移除 `"plate_wardrobe_silent_clause": 0` ⇒ 該條改為 **never-droppable**（繼承它所取代的兩段 never-droppable 段落的地位）。其餘 ranks 不變：1 `close_up_silent_mouth`／2 `medium_shot_silent_mouth`／3 `source_costume_leaves_plate`／4 `close_up_sheet_crop_lock` |
| `smart_render_worker.py:179`、`director_cut_studio.py:786` | `SMART_RENDER_POLICY_VERSION = 79`（兩處同步）；無任何 `policy >= N` 分支依賴 78 |
| `testing\test_character_swap_engine.py` | 測試改名 `test_silent_merged_clause_never_yields_and_the_mouth_reminder_does`：斷言 `plate_wardrobe_silent_clause` **不在** RANKS、超額時 `dropped == ["medium_shot_silent_mouth"]`、`MERGED_PLATE_HEADER` 仍在 prompt、`MEDIUM-SHOT SILENT MOUTH REINFORCEMENT` 不在 prompt |

**C. 離線驗證**
- 改後同一編譯路徑落在 **11 821 ≤ 12 320**：只丟一次、丟的是 `medium_shot_silent_mouth`，衣柜段落存活（實跑断言 `dropped` 正是這個值）。
- `py_compile` 三檔通過；`test_character_swap_engine` **80 tests OK**；`test_smart_render_worker`＋`test_storyboard_segment_mapping`＋`test_character_swap_closeup_gates`＋`test_workflow_engine` **170 tests OK（skipped=2）**，合計 **250 項**。
- VERSION 維持 `0.3.8-alpha.3`、Project Format 29 不動。

**D. 已查到但本輪刻意未修的結構性問題（下一輪依據）**
1. **衣柜 QC 的絕對地板 0.12 已失準**（`smart_render_worker.py:2647`，判定 2754-2759）：907 三窗 6 個 region **全部朝 P1 移動**（shift +0.039…+0.143，target > source）卻有 5/6 判 fail ⇒ `attempts_used=3`、`exhausted True`，9 次生成全部燒滿。離線規則模擬（`working\_r41_wardrobe_replay.py`）：現行規則只有 1/6 通過；改成「方向正確」6/6 通過；改成「相對邊際 tgt−src>0.04」5/6 通過。建議先不動（3 次抽卡對身份其實有利），等 79 的槍讀完再決定。
2. `enable_rtx_vsr` 對 swap pass 是**裝飾**：只有 `workflow_engine.apply_generation_parameters()`（548-594）讀它，`character_swap_engine.compile_*`（2266-2350）從不呼叫 ⇒ 換檔後的 node 9 `RTXVideoSuperResolution` 一律生效，Studio 那個勾選框在 swap 模式下無效。
3. **480 bucket 門檻**：`character_swap_engine.py:2307／2339` 是 `"768" if megapixels>=0.75 else "480"` ⇒ 0.5 MP preview 一直走 480。降低門檻（例如 ≥0.45 MP 走 768）與 Round 40「把參考變大就變好」同方向，是下一槍之後的首選候選。

**E. 下一步（照序；下一個新 seed ＝`923011007`）**
1. 重建 Job（改 policy 後必須重建）：`& "<abs python>" working\_r38_buildjob.py 923011007 0.5 3`，輸出 `policy=79`。
2. 取得用戶批准後開槍（tray 仲裁、`staged_model_driver.py run`）。
3. 讀帧：`_r40_history_probe.py` 確認 `/history` 的 `dropped` 已換成 `medium_shot_silent_mouth`、prompt ≈ 11 821；`_r40_faces.py`／`_r40_montage.py`／`_r40_seam.py`（**輸出目錄換 round41**）＋ `_r40_prompt_probe.py <manifest>` ＋ `_r40_retry_scores.py <driver log>`；**一定要 `view_image` 親眼看 montages**。判定重點：衣柜忠實度（P1＝黑上衣＋藍下襬＋黃格子短褲）、眼鏡/臉齡、invented 頭飾、三窗 silent excess。
4. 之後才談 D 節那三項（衣柜 QC 規則、768 bucket、`enable_rtx_vsr` 歸屬）。

**F. 本節工具與坑**
- 跑測試要 `cd testing` 再 `& "<abs python>" -m unittest test_character_swap_engine`；用 `-m unittest discover -s testing -t .` 會噴 *Start directory is not importable*。
- ⚠️ `test_staged_model_driver` 有一項會**真的打 ComfyUI `/free`**，別在 H3 跑一半時執行；`test_director_timeline`（238 項）依慣例跳過。
- 本輪新增探針：`_r41_wardrobe_replay.py`、`_r41_prompt_sections.py`、`_r41_clause_lengths.py`（全部離線，不佔 GPU）。
- 已用 seed：923010307／0407／0507／0607／0707／0807／0907；**下一槍 `923011007`**。

---

## 42. Round 42（2026-10-30 凌晨，離線修碼＋測試；**源碼已修復＋343 項測試通過，影片未實機**）：policy 79→80 —— 衣柜線索加驗「尾端窗」，只有排名能吃尾端數字

**A. 觸發點：用戶只接受 `pass_01_R1_00039_`，worker 卻選 `00040`**

seed 923010907（policy 78，Round 40 那三窗）九支候選裡，用戶唯一能接受的是 W3 的 `pass_01_R1_00039_.mp4`，而生產選的是 `00040`。離線逐幀證據（`_dsh_verify_9\round42\r{8,9,10}_*.png`）：

- `00039`：前段仍是 invented 紅金袍，**尾段 t≈0.886 已穿上 P1 黑背心＋白珠領＋藍袖＋黃格短褲** ⇒ 服装「來得晚」。
- `00040`：全程紫黑豹紋袍＋照片式陰影 ⇒ 服装「從來沒來」＋真人化漂移。
- 九支**全都没有** P1 的圓眼鏡（00039／00043 放大確認）；舊 handoff 若有「已修好眼鏡」之外的延伸宣讀，別沿用。
- 排名複合分數：00039 落後 00040 **0.0984**，`wardrobe_shift` 只差 **0.005** ⇒ 實際決定權在 `target_reference_similarity`（64×64 色彩直方圖，`target_reference_frame_similarity`），衣柜項（`1.5*min(0.35, shift)`）幾乎不影響勝負。

**B. 根因：衣柜取樣窗 + median + 「較差半身」綁定**

`inspect_character_swap_identity` 衣柜線索只按 `_clamped_timestamps(duration, (0.22, 0.50, 0.78), frame_interval)` 取點，binding 在 upper/lower 中挑**移動較少**的那一半，再取 **median**。尾端才換装的 take 在 0.22／0.50 仍是原始演員顏色 ⇒ median 被前段拖平，真实位移被低估。離線重放（`working\_r43_region_timing.py`，**照生產語義**：同一服装參考、manifest 內 upper/lower 框、worst-half binding、跨 body row 取 median）：

| 窗 | attempt（依序） | median | late(0.78/0.86/0.94) | 生產 pick |
|---|---|---|---|---|
| W1 | 00043／00044／00045 | +0.097／+0.113／+0.146 | +0.117／+0.233／+0.267 | 00044 |
| W2 | 00035／00036／00037 | +0.189／+0.134／+0.161 | +0.214／+0.262／+0.195 | 00037 |
| W3 | **00039**／00040／00041 | +0.165／+0.133／+0.137 | **+0.251**／+0.167／+0.284 | 00040 |

窗長 4.288 s @24 fps ⇒ 生產 stamps `[0.943, 2.144, 3.345]`、late `[3.345, 3.688, 4.031]`。回放（其他項固定）：`median`→W1 00044／W2 00037／W3 00040；`late` 與 `best_of`→**W3 選出 00039**，W1 不變，**W2 變成 00036**（00036／00037 用戶都不接受 ⇒ 不是已認可結果的倒退，但屬行為改變）。

⚠️ **必須保留的保留意見**：探針重算的 median 系統性比 manifest 記錄高 **+0.04…+0.11**，且 W3 兩者順序相反（探針 00039>00040 vs 記錄 00039<00040），推測是實際 probed duration／ffmpeg seek ladder 差異 ⇒ 上表結論是**方向性證據**，不是保證。

**C. 負面結果（已排除）**

`working\_r43_selection_replay.py`：把「卡通媒介平塗度／飽和度」（`working\_r43_media_probe.py` 的 satflat／peak8）放進排名，只能把 00040 擠到最後，抓到的是 flatness 而非身份/年齡（00041＝最卡通的老人會排第一），且會改 W2。⇒ **不要用平塗指標當排名項**。

**D. 改動（policy 79 → 80；原則：QC 判定與 retry 觸發仍讀 median，只有排名允許用尾端數字）**

| 檔案 | 內容 |
|---|---|
| `smart_render_worker.py` | `SMART_RENDER_POLICY_VERSION = 80`（179-192）＋政策 80 註解；`inspect_character_swap_identity`：`wardrobe_late_timestamps`（0.86／0.94，0.78 點沿用既有解碼 ⇒ 每線索只多 2 次 decode）；region row `wardrobe_shift_late`；body row 沿用同一半身 binding 只換窗 ⇒ `late_row_shifts`／`wardrobe_shift_late`；`wardrobe_audit` 新增 `late_shift`、`late_timestamps_normalized=[0.78,0.86,0.94]`；result 頂層 `wardrobe_shift_late`；`_candidate_target_likeness`（1869-1900）改讀 `max(wardrobe_shift, wardrobe_shift_late)`，仍 `min(0.35, …)*1.5`；candidate assembly／`identity_candidate_scores` 帶出 `wardrobe_shift_late`（4059／4114） |
| `director_cut_studio.py` | 799-804 政策 80 註解 + `SMART_RENDER_POLICY_VERSION = 80` |
| `testing\test_smart_render_worker.py` | 新 4 項（見 CHANGELOG Round 42 D/E）。`_windowed_take()` helper；`test_wardrobe_audit_records_a_costume_that_arrives_late` 用 `drawbox enable='gte(t,1.6)'` 生 2 s fixture，斷言 median 仍 fail、late 過線、audit 一致 |

**E. 驗證（全部離線，未碰 GPU）**
- `py_compile`：`smart_render_worker.py`／`director_cut_studio.py`／`testing\test_smart_render_worker.py` ✅
- `test_smart_render_worker` **69 OK（skip 1）**；`test_character_swap_engine`＋`closeup_gates`＋`background_extra`＋`silent_audio`＋`silent_mouth_motion_gates`＋`silent_mouth_transient_qc`＋`test_identity_sheet`＋`test_smart_render_qc_advisory`＋`test_workflow_engine` **274 OK（skip 1）** ⇒ 合計 **343 項**
- **源碼已修復 ≠ 影片已實機驗證**：policy 80 的槍還沒開。

**F. 下一步（照序；下一個新 seed ＝`923011007`）**
1. **重建 Job**（舊 `preview_923011007_1793288348406948300.job.json` 是 policy 79 殘留，勿用）：`& "<abs python>" working\_r38_buildjob.py 923011007 0.5 3` → 應輸出 `policy=80`。
2. 取得用戶批准後 `staged_model_driver.py run`。
3. 讀幀：`_r40_history_probe.py`、`_r42_candidates.py`（**輸出目錄換 `round44`**）、`_r40_retry_scores.py`、`_r40_seam.py`、`_r43_region_timing.py`；一定 `view_image` 親眼看。
4. 三個候選方向（需用戶批准才動）：①late-window（已做）②三次 attempt 全保留＋Studio 一鍵選片（離線、零 GPU）③Qwen3.8 VLM 當候選裁判（走 staged driver）。
5. 之後才談 Round 41 D 節三項（衣柜 QC 絕對地板 0.12 失準、`enable_rtx_vsr` 對 swap 是裝飾、480 bucket 門檻 `character_swap_engine.py:2307/2339`）。注意：late 數字會讓多數 region 過線，但目前**刻意**讓 QC 仍讀 median。

**G. 本節工具**：`_r43_media_probe.py`、`_r43_selection_replay.py`（負面）、`_r43_wardrobe_timing.py`（全身框 19 點）、`_r43_region_timing.py`（生產語義，log `working\_r43_rt.log`）。ComfyUI 輸出的實際位置在**本機** `C:\ai program\Data\Packages\ComfyUI-GPU-1\output\studio_character_swap\<segment_id>\pass_01_R1_%05d_.mp4`（計數器跨 run 累加；E:\ 同名目錄讀起來是空的）。

## 43. Round 43（2026-10-30，離線修碼＋測試；**源碼已修復＋344 項測試通過；影片證據來自 seed 923011007 的 env `off`，policy 81 出厂路徑本身未實機**）：policy 80→81 —— medium-silent plate 出厂關掉「衣著帶」，衣柜改由 P1 identity sheet 決定

**A. 觸發點：用戶連續多輪點名同一組症狀**

「只有頭替換、衣服完全不像參考圖」「背景出現蜂窩狀／怪圖案」。前幾輪都把矛頭指向 prompt 與 identity sheet，本輪把 medium-silent gate 的 **plate（送進 H3 的抑制版源片）** 逐條拆開量，才發現服装資訊是在 plate 上就被糊掉的。

**B. 根因（離線拆 plate filter graph，零 GPU）**

`_character_swap_identity_suppressed_source()` 在 medium-silent 路徑出廠就會畫 **3 條帶**：head band ＋ **2 條 wardrobe band（y 0.285 → 1.0）**，全部 `boxblur`。

| plate 臂 | bands | manifest `suppressed_frame_area` | 後果 |
|---|---|---|---|
| `blur`（policy 69–80 出厂） | head + 2 條 wardrobe | **0.5013** | 頭＋整個衣身糊成色斑 ⇒ H3 只好照 V1 cosplayer 的殘留配色自行發明服裝（紅金皇袍、金色鏤空滾邊、蜂窩紋） |
| `off`（policy 66 舊 plate 語義） | 只剩 head | **0.114** | 軀幹保留結構與明暗，服装改由 P1 identity sheet 決定 |

對照 plate 幀（同段同時刻）：`_dsh_verify_9\round46\PLATE_seg1_OFF_t2.09.png` vs `PLATE_seg1_BLUR_t2.09.png`。`blur` 臂那 6 列**沒有一列**過規則 A，且 `target_similarity` 全落在 0.51–0.57，比 `off` 的每一列都低。

**C. 實機證據（seed 923011007 ＝ policy 80 源碼 ＋ env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=off`，3 窗 ×1 發，`staged_model_driver.py run`）**

衣柜 QC 重放（`working\_r41_wardrobe_replay.py 923011007 923010907`，讀 manifest，零 GPU）：

| 量測 | `blur`（seed 923010907，policy 78） | `off`（seed 923011007，policy 80） |
|---|---|---|
| 規則 A 通過列數（3 窗 × upper/lower ＝ 6 列，`shift ≥ 0.12`） | 1/6 | **5/6** |
| `wardrobe_shift` 平均 | +0.0972 | **+0.1658** |
| 衣柜 `target_similarity` 平均 | 0.5359 | **0.5876** |
| `suppressed_frame_area` | 0.5013（3 bands） | **0.114**（1 band） |

逐列（`off` 臂，唯一失敗的是 W3 lower）：

| 窗 | upper `shift`／`tgt` | lower `shift`／`tgt` | audit |
|---|---|---|---|
| W1 | +0.2018／0.6311 | +0.1336／0.6203 | passed（`shift` 0.1336） |
| W2 | +0.2030／0.6320 | +0.2307／0.5985 | passed（0.2030） |
| W3 | +0.1351／0.5523 | **+0.0906／0.4905** | failed（`binding=lower` 卡在 0.12 地板） |

- manifest 另記 `wardrobe_mode: off`、`prompt_chars 12208/12320`、`dropped_tail_clauses []`、`attempts_used 1`；`master.mp4` 完成、`/free` 正常（`preview_923011007_1793291935999553700.manifest.json`）。三窗仍被 QC 點名 `authored Silent Listener mouth shows excessive articulation`，但不阻擋拼接。
- 讀幀拼圖 `montage_OFF_923011007.png`／`faces_off_923011007.png`／`compare_P1_blur_OFF.png`：黑上衣＋藍下襬＋黃格襪＋黑鞋＋卡通手 ⇒ 用戶認可為 **Studio 歷來最接近 P1 全身的一支**。
- ⚠️ **配對限制**：對照臂 923010907 是 policy 78 ＋ 每窗 3 次 attempt，`off` 臂是 policy 80 ＋ 每窗 1 次 ⇒ 這是**方向性證據**，不是嚴格 A/B。同 seed 同段的嚴格 `blur` 對照 Job 已建好但**未跑**：`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_923011007_1793291943180178000.job.json`（它是 `segment_attempts=3`，成本約 3 倍）。另兩份 `..._1793290942469688300`／`..._1793288348406948300` 各是 blur 預覽與 policy 79 殘留，**勿用**。
- **源碼註解更正（本輪）**：舊註宣稱「`blur` 多花 660 字 prompt ⇒ 被預算擠掉 Silent Listener 口型條款」。盤上證據不符：兩份 policy-80 `blur` Job 編譯出 **11935 字**，比 `off` 實際提交的 **12208 字更短**（只有跨政策的 policy-78 `blur` manifest 確實丟過 `plate_wardrobe_silent_clause`）。已改寫成可複驗的陳述：論點是 **plate 抑制面積 0.5013 vs 0.114**，prompt 長度不是論點。Silent Listener 口型條款的丟失與 plate 衣著帶是兩件事 —— 前者已在 Round 41 由 policy 79 解開，本輪修的是後者。

**D. 改動（policy 80 → 81；`VERSION` 維持 `0.3.8-alpha.3`，Project Format 29 不變）**

| 檔案 | 內容 |
|---|---|
| `director_cut_studio.py` | `_medium_silent_wardrobe_band_mode()` 出厂 `"blur"` → `"off"`（991-996；env `H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE` 仍可回 `blur`／`blur_desat`）；knob 上方註解塊改寫為上述實測鏈＋配對限制＋prompt 更正；`_character_swap_identity_suppressed_source()` docstring（35907／35984）同步標明出厂 `off`；817-823 政策 81 註解 + `SMART_RENDER_POLICY_VERSION = 81` |
| `smart_render_worker.py` | 179-207 政策 81 註解 + `SMART_RENDER_POLICY_VERSION = 81`（與 Studio 兩處同步 ⇒ 舊 plate／Job 快取自動失效） |
| `testing\test_character_swap_closeup_gates.py` | knob 預設斷言改 `off`（空 mapping、垃圾值兩處）；**新增** `test_default_medium_silent_plate_agrees_with_the_shipped_knob`（725）：未经 patch 的真實呼叫必須與 import-time 常量一致（`off` ⇒ strategy 不带 `_wardrobe_blur_suppressed` 尾碼、graph 內不得出現 `boxblur=6:3`）；另有 **5 項**原本依賴旧出厂值的測試改為**明確 pin `blur` 臂**（`test_medium_silent_suppression_blurs_head_band_with_own_strategy`、`test_figure_extent_knob_rolls_the_plate_back_to_policy_68`，以及經 `_hair_band_arm()` helper 的 3 項 hair-band 測試） |

備份：`_backup\r43_20261030_pre_policy81_bandoff\`。

**E. 驗證（全部離線，未碰 GPU）**
- `py_compile`：`director_cut_studio.py`／`smart_render_worker.py`／`character_swap_engine.py`／`testing\test_character_swap_closeup_gates.py` ✅
- `test_character_swap_closeup_gates` **77 OK**；基線 10 模組（`test_smart_render_worker`＋`character_swap_engine`＋`closeup_gates`＋`background_extra`＋`silent_audio`＋`silent_mouth_motion_gates`＋`silent_mouth_transient_qc`＋`test_identity_sheet`＋`smart_render_qc_advisory`＋`test_workflow_engine`）**Ran 344 tests OK（skipped=2）**（基線 343 ＋ 出厂一致性守門 1）
- 注意：上一輪 handoff 寫的模組縮寫會 ImportError，以上為**精確模組名單**；`testing\` 下跑、bundled python 無 pytest ⇒ `-m unittest`。

**F. 下一步（照序；下一個新 seed ＝`923011008`）**
1. **先離線量 prompt 預算**：`CHARACTER_SWAP_PROMPT_CHAR_BUDGET = 12320`（`character_swap_engine.py:120`），`off` 臂已提交 **12208** ⇒ 只剩 **112 字**，加不動新條款；要加就得先刪／合併（探針 `working\_r41_clause_lengths.py`、`_r41_prompt_sections.py`）。
2. 零 GPU 對照選項：先跑已建好的嚴格 `blur` 對照 Job（見 C 節配對限制，需批准）。
3. 下一槍單軸攻「**圓眼鏡丟失** ＋ **發明的額頭皺紋 ⇒ 變老人**」（新 seed `923011008`；開跑前照例 `_r38_buildjob.py <seed> 0.5 3` 應印 `policy=81`）。
4. 可選（零 GPU）：衣柜絕對地板 `0.12` 在 `off` regime 重新標定 —— W3 lower `shift 0.0906` 被規則 A 誤傷，但 `target_similarity 0.4905`、規則 C（`tgt-src>0.04`）／D（`tgt≥0.45`）／E（OR）全判過；規則 B（`shift>0`）在 `blur` 臂會 6/6 全過 ⇒ 失去鑑別力。探針已內建 A–E。
5. **仍未解**（prompt／sheet 軸，與 plate 無關）：① P1 圓眼鏡每窗都丟（只有用戶手動官方短 prompt 那支 `character-swap_00036_` 有）② 發明的額頭皺紋 ⇒ 變老人 ③ 滾邊仍是金色鏤空、非白滾邊 ④ silent 對嘴仍被 QC 點名（plate 相對上限 ~0.107–0.119，result motion 0.20–0.25）。


## 44–48. 空缺說明（2026-10-30，**無產品碼改動**）

`## 43` 之後直接是 `## 49`。中間的 Round 44–48 是**離線探針輪**，事實在本節與 CHANGELOG Round 49 裡一次登記，沒有各自的政策號：`working\_r44_*`～`_r48_*` 分別做「衣柜規則 A–E 重放」「plate 衣著帶 A/B（`_r45_band_ab.py`）」「prompt 條款長度盤點（`_r41_clause_lengths.py` 續用）」「**手動圖 vs Studio 逐節點比對（`_r48_manual_vs_studio_probe.py`）**」。`_r48` 是本輪政策號的**唯一觸發來源**，其餘四輪的結論已併入 Round 43／49 的 A 節。


## 49. Round 49（2026-10-30，離線讀圖＋修碼＋測試；**源碼已修復＋352 項測試通過；影片未實機**）：policy 81→82 —— 出廠行爲對齊用戶認可的「手動 ComfyUI 圖」，並修掉切段開關暴露出的 work area 端點缺陷

**A. 觸發點：用戶的三句質問**

用戶明說「單一角色替換，Studio 的效果遠差過手動 ComfyUI」，並點出四條具體差異：LoRA 不得超過 1.5、`ref_image_size` 在手動圖裡会被 RTX 放大兩倍、送進 H3 的應該是**乾淨 V1** 而不是糊过的 plate、音軌不要抽掉、以及 Relay loop 要用 18 幀接力讓身分前後一致。因此本輪**不再猜**，直接把用戶的 `H3-Character-Swap-Relay-V2-api.json` 逐節點讀出來（`.codex_tmp` 內 walk，零 GPU）：

| 手動圖事實（節點） | 值 |
|---|---|
| `adapter` `LoraLoaderModelOnly` | `h3_character_swap_v1.5.safetensors`、`strength_model=1.5` |
| `turbo` `LoraLoaderModelOnly` | `minimax_h3_dmd_ref2va_8step_turbo_pruned…`、`strength_model=0.8`（不同 adapter，本輪不動） |
| `9` `RTXVideoSuperResolution` | `resize_type=scale by multiplier`、`scale=2`、`quality=ULTRA` ⇒ 輸出接 `reference_conditioning.ref_images.ref_image_0` |
| `reference_conditioning` `MiniMaxH3ReferenceToVideo` | `ref_image_size="match"` |
| `prepare` `H3RelayPrepareSource` | 直接吃 `source` `LoadVideo` ⇒ **無任何濾鏡**、`resolution="480"`、`duration_seconds=0`、`missing_audio="silence"` |
| `plan`／`window`／`finish` | `window_frames=124`、`history_frames=18`、`schedule="adaptive"`、`history_audio_mode="source"`、`audio_mode="source"` ⇒ **原音保留**、單次提交由原生 loop 串窗 |

對照 Studio（policy 81）實機留檔（manifest `preview_923011008_1793300811411550100.json` ＋ ComfyUI `/history` 唯讀）：plate 檔名 `…_identity_suppressed…_silent_….mp4`、`silent_mouth_freeze.applied=True tmix_frames=7`、`mask_mode=feather`、`silent_audio_strategy: audio_stripped`、**3 段 × 4.288 s 且每段 `relay_window_count: 1`**（每段都從第 1 幀冷啟動，正是「後半完美、前半還是 V1」的機制）、重試階梯 `strength_model` 1.5→1.75→2.0。

**B. 根因四條（全部有留檔）**

1. **swap LoRA 被重試階梯推出官方範圍**。`smart_render_worker._workflow_for_attempt()` 原本 `base + 0.25*(attempt-1)`，出廠 1.5 時第 2、3 次嘗試变成 1.75／2.0。用戶對這批 take 的評語是「像是穿了大概對的衣服的另一個人」，且 S3／S7／S10／S11 的「變老人」同源 —— 超限強度正是讓 LoRA 自行發明年齡、臉與皺紋的條件。
2. **P1 的上採是「繼承來的」而非「寫進來的」**。`compile_character_swap_pass()` 從不碰 node `9` 與 `ref_image_size`，所以 ComfyUI 拿到的是模板 re-export 時的殘留值；一旦用戶重新導出模板，讓 P1 可读的 RTX ×2 就可能無聲消失，manifest 也不會說一聲。
3. **Studio 自己加了手動圖沒做的事**：糊 V1 臉（feather mask）＋ silent 嘴帶 `tmix` 凍結＋抽掉 plate 音軌。三者各自都是某輪為單一症狀加的，疊在一起就變成「H3 看到的是模糊且無聲的參考片，而不是用戶那支乾淨 V1」。
4. **切段 cold start**：超過 124 幀的 Shot 被 Studio 在時間軸端切成 N 個冷啟動 Job，每段失去 18 幀 history，身分自然斷。手動圖只提交一次，讓 `H3RelayWindowPlan` 自己按 `schedule="adaptive"` 串窗。

**C. 改動（policy 81→82；`VERSION` 維持 `0.3.8-alpha.3`，Project Format 29 不變）**

| 檔案 | 內容 |
|---|---|
| `director_cut_studio.py` | `_character_swap_parity_flag()` ＋ 三個**出厂 off** 開關 `CHARACTER_SWAP_PLATE_SUPPRESSION`／`CHARACTER_SWAP_SILENT_AUDIO_STRIP`／`CHARACTER_SWAP_RELAY_WINDOW_SPLIT`（加入 `DESIGN_ENV_RENDER_KNOBS` allowlist，881-930）；swap pass 呼叫點 `enabled=bool(target_is_illustrated) and CHARACTER_SWAP_PLATE_SUPPRESSION`；`_character_swap_silent_audio_source()` 開頭 `if not CHARACTER_SWAP_SILENT_AUDIO_STRIP: return source.resolve(), "original"`；`_planned_render_segments()` 的 `relay_parts` off 時恆為 1；**同輪補修** `native_relay_exact_endpoints`／`native_relay_grid_seconds=0.001`（22248-22349）；`SMART_RENDER_POLICY_VERSION = 82` |
| `character_swap_engine.py` | `CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH=1.5`、`_character_swap_lora_strength_ceiling()`（env `H3_CHARACTER_SWAP_LORA_MAX_STRENGTH` **只能調低**，>1.5／≤0／垃圾值回落 1.5）、`clamp_character_swap_lora_strength()`（NaN／非數字 → ceiling）；`compile_character_swap_pass()` clamp 所有 `lora_name` 含 `character_swap` 的 LoRA、把含 `ref_image_size` 的 inputs 寫成 env 或 `"match"`，contract 新增 `swap_lora_max_strength`／`swap_lora_ceiling`／`reference_upscale_node_id`／`reference_upscale_scale`／`reference_image_size` |
| `smart_render_worker.py` | 重試階梯改走 clamp ⇒ 出厂 1.5 時**只換 seed**；新增 `effective_generation_timeout_seconds(job)` = `generation_timeout × 最大 relay_window_count`（上限 86400），兩處 `wait_for_history` 採用；`SMART_RENDER_POLICY_VERSION = 82` |
| `testing\` | `test_character_swap_silent_audio` 4 項改為明確 patch 開關 on 才 strip ＋ 出厂守門 1 項；`test_director_timeline` 「平衡切兩半」拆成默认一段／開關 on 仍 `(0,2.6),(2.6,5.2)` 兩項，**新增** `test_character_swap_single_shot_work_area_keeps_exact_endpoints`；`test_smart_render_worker` 重試強度 2.0→1.5 ＋ 新增「1..7 次嘗試恆在 1.0–1.5」「timeout 隨窗數放大（3 窗 5400、上限 86400）」；`test_character_swap_engine` 新增 5 項（含 `ref_images.ref_image_0` 仍掛在 `RTXVideoSuperResolution` scale 2.0 之上） |

**D. 端點缺陷（切段 off 的必要配套，本輪後半發現）**

`_planned_render_segments()` 只登記**嚴格落在 work area 內部**的 cue 邊界（`start + 1e-6 < boundary < end - 1e-6`，22188／22195）。焦點專案是「單一 authored Shot 蓋滿時間軸」⇒ 邊界集合只剩 `{start, end}` ⇒ `mandatory_story_boundary_active=False`（22238）⇒ 落入末尾通用 `plan_render_segments(..., grid_seconds=TIMELINE_SNAP_SECONDS=0.5)` ⇒ `snap_seconds` 把 **5.200 s 截成 5.000 s**、把 **12.864 s 進成 13.000 s**（越過 22136 剛 clamp 過的 V1 EOF 12.863792 s ⇒ 幽靈尾巴、FFmpeg seek-at-EOF）。修法是把 native Relay 模式的格線降到 0.001 s（三處 fallback：22285／22332／22349）。**沒有這一步，「出廠只提交一段」會連端點都不準。**

**E. 驗證（本輪全部離線，未碰 GPU）**
- `py_compile`：`director_cut_studio.py`／`character_swap_engine.py`／`smart_render_worker.py` ⇒ `PY_COMPILE_OK`。
- 10 模組基線 **Ran 352 tests OK（skipped=2）**（精確名單見 §43 E 節，94.6 s）。
- character-swap 分段／端點 **5 項點跑 OK（18.942 s）**：`…_keeps_a_long_shot_in_one_native_window`、`…_single_shot_work_area_keeps_exact_endpoints`（新增）、`…_balances_a_shot_that_exceeds_one_relay_window`、`…_relay_keeps_every_source_shot_as_one_render_unit`、`…_relay_drops_rounded_subframe_tail_past_v1_eof`。修正前新增測試重現 `AssertionError: [(0.0, 5.0)] != [(0.0, 5.2)]`。整類別 240 項每項 spawn `design_ai_service.py`，依慣例不整跑、不當判据。
- 探針 `.codex_tmp\r49_probe_segments.py`（讀焦點專案，零 GPU）：`policy_version 82`、`scan_duration 12.863792`、`clip 0.0–12.86`、`shot S1 0.0–12.863792` ⇒ **factory 1 段 `0.000000–12.860000`**、`continuity=none`、`overrun 0.000000`；`RELAY_WINDOW_SPLIT=1` 才回到 4.287／4.286／4.287。`character_swap_relay_window_count(12.86)=3`、`(4.288)=1`；`effective_generation_timeout_seconds = 1800×3 = 5400 s`。
- 驅動器邊界：`staged_model_driver.py --wait-timeout`（默認 1500 s）只約束 `wait_comfy()` 交棒等待；worker 子進程是 `proc.wait()` **無上限**（964-983）⇒ 串窗長 render 不需額外傳參。

**F. 界定**
- **源碼已修復**：出厂不再糊 plate、不再抽音、不再切段；swap LoRA 永遠 ≤1.5；RTX ×2 與 `ref_image_size` 寫入 contract；native Relay 下端點保持毫秒級。
- **影片已實機驗證**：**無**。五項行為都要靠 ComfyUI 一槍取證（plate 檔名、`/history` 的 `strength_model`、segment 數、原音是否保留、身分前後一致）。
- **已知取捨**：clean plate ⇒ silent Shot 的嘴帶不再 `tmix` 凍結，且 plate 自帶會動的嘴＋原音 ⇒ 「silent listener 仍對嘴」有回升可能（Round 37i 的 QC 機制仍在，Round 37k 的凍結隨 plate 開關一起 off）。若實機證實回升，`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1` 或 `H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1` 單獨回退即可，不必回退整輪。
- **仍未表態**：① preview 要 0.5 MP 還是 1.0 MP（bucket `megapixels>=0.75 ⇒ "768"`；用戶曾實測 1.0 MP 大增益）② Round 47 三提案（衣柜門檻改相對、圓眼鏡／禁 invented 額頭皺紋、silent 微超標降 advisory）③ prompt 預算只剩 112 字（`CHARACTER_SWAP_PROMPT_CHAR_BUDGET=12320`，已提交 12208）。

**G. 下一槍（等批准）**：新 seed `923011107`，先 `working\_r38_buildjob.py 923011107 0.5 3` 應印 `policy=82`，再 `staged_model_driver.py run`。要證的四點：① plate 檔名是否乾淨 V1（無 `identity_suppressed`／`silent` 尾碼）② `/history` 的 swap LoRA `strength_model==1.5` ③ manifest 只剩 **1 個 segment**、`relay_window_count==3` ④ 輸出是否保留原音。回升觀察項：silent listener 是否重新對嘴。

**H. 本節工具**：`.codex_tmp\r49_probe_segments.py`（policy 82 分段與 EOF 探針，可重用）、`working\_r48_manual_vs_studio_probe.py`（手動圖 vs Studio 逐節點）、`working\_r45_band_ab.py`、`_r41_wardrobe_replay.py`、`_r38_buildjob.py`、`_r40_history_probe.py`；本輪 ComfyUI 只做過唯讀 `/history`，未載模型。

**G. 本節工具**：`working\_r45_band_ab.py`（讀 Job／manifest 比 plate 臂與 prompt 字數）、`_r41_wardrobe_replay.py`（衣柜規則 A–E 重放）、`_r41_clause_lengths.py`／`_r41_prompt_sections.py`（prompt 預算）、`_r38_buildjob.py`（重建 Job，會印 policy）、`_r40_history_probe.py`／`_r42_candidates.py`／`_r40_retry_scores.py`／`_r40_seam.py`（讀幀，輸出目錄 `_dsh_verify_9\round46\`）；driver log `driver_923011007_off.log`。本輪**未碰 GPU**，ComfyUI `/history` 只做過唯讀 GET。


## 50. Round 49b（2026-10-30 08:0x–08:29 **實機一槍**，seed 923011107／0.5 MP；**影片已實機驗證＝policy 82 五項全部生效、頭部貼片症狀消失；唯一 red 項換成 silent 嘴**）

**A. GPU 交棒（走 `staged_model_driver.py run`，未 bypass）**
`unload-qwen` ⇒ `verified_clean`（VRAM **26.5 → 2.57 GB**）⇒ `wait-comfy ready（1600 node classes）` ⇒ `smart_render_worker` ⇒ `/free`（manifest `final_model_release="ComfyUI models and VRAM released"`）⇒ tray 載回 Qwen。全程未同時常駐兩個模型。Job `preview_923011107_1793318258827680500`，約 31 分鐘，`attempts_used=3`，`render_policy_version=82`。

**B. 用戶五項要求的實機取證（manifest／`/history`／ffprobe／讀幀）**
1. **LoRA ≤1.5**：`/history` 本輪三發 attempt 全是 `h3_character_swap_v1.5.safetensors` `strength_model=1.5`；同一 list 裡上一輪 policy 81 的三發是 1.5→1.75→2.0 ⇒ clamp 在實機生效，重試只換 seed。
2. **RTX ×2 上採**：node `9` `RTXVideoSuperResolution` `scale=2`／`quality=ULTRA` → `ref_images.ref_image_0`，`ref_image_size="match"`；輸出 **576×864 = 0.498 MP**。
3. **乾淨 V1 plate**：source 是 `h3ref_video_V1-…_v1_relay_8df6283643bf459a39b2_0.000-12.864.mp4`，**無** `identity_suppressed`、**無** `_silent`；讀幀確認餵進去的是全銳利真人。
4. **原音保留**：plate 與 `master.mp4` 都帶 `aac LC 48000 Hz stereo`；`source_audio_timing_audit={status ok, offset 0.0, correlation 0.983089}`。
5. **18 幀 Relay 串窗**：manifest **1 個 segment**（`0.0–12.864`、`relay_window_count=3`、`window_frames=124`／`history_frames=18`／`schedule=adaptive`／`continuity=none`），`master.mp4` = 307 幀 @24 fps／12.8 s，`target_duration_seconds 12.863792` 完整 ⇒ §49-D 的端點缺陷實機未復發。

**C. 對 policy 81 基準（seed 923011008）的量化改進**
`target_reference_similarity` 0.555226 → **0.613560**；`retention_score` −0.2983 → **−0.225781**；`wardrobe_shift` 0.082626 → **0.136518**（`wardrobe_audit.passed=true`，upper 0.1826／lower 0.1365）；QC 失敗原因從「replacement is only a head/face layer; the V1 wardrobe still fills the lower half」變成**只剩** silent 嘴 ⇒ 用戶抱怨的「只有換頭、衣服還是 V1」在這一槍消失。
讀幀 `_dsh_verify_9\round49\montage_82_vs_81.png`：圓眼鏡回歸、光頭＋參考圖髮束、年輕臉（基準是灰髮老人）、P1 黑＋藍袍、**手/袖/袍全部卡通繪製**、背景乾淨**無蜂窩紋**、**無 sheet 下半身竄入**。
`montage_82_seams.png`：Relay 窗邊界 **≈4.29 s／≈8.58 s** 前後臉、頭飾、袍服、眼鏡**連續無跳變**；3.6–4.4 s 帶內無「character sheet 下半身」瑕疵 ⇒ 「history 串窗 ⇒ 身份前後一致」實機成立。

**D. 退步項與 QC 參照系過時（本輪未動碼）**
`silent_mouth_audit` 同一 bbox／同一 registration：`plate_motion` 0.071193（凍結）→ **0.142404**（乾淨 V1 自己會動）⇒ `plate_relative_motion_limit` 0.118790 → **0.225607**；`result_motion` 0.182128 → 0.260531；`articulation_excess` 0.012425（超 53%）→ 0.034924（**超 15%**）；`geometry_violated=false`（嘴腔 swing 0.325 vs 限 0.52）、`source_speech_conflict=false`、`decision_basis=pixel_motion`。
重點：`verdict_scope` 仍寫 `relative_to_suppressed_plate`，但出厂已無 suppressed plate ⇒ 門檻已自動放寬 1.9×、超標幅度反而變小。官方 Character Swap prompt 本來就要求 match「visible mouth movements」，Silent Listener 是我們疊加的語意 ⇒ 保留原音後兩者天然衝突，這是**閾值參照系要重新定義**（= Round 47 提案③），不是模型故障。

**E. 界定**
- **影片已實機驗證**：五項出厂對齊、單 Shot＝單 render unit × 3 原生窗且端點正確、原音保留且音畫對齊、身份與衣柜**雙雙改善**、跨窗身份一致、背景乾淨。
- **未通過**：`character_swap_identity_failed=true`、`failure_class silent_mouth_excessive_articulation`（`selected_attempt 3`）；影片仍輸出，接受與否由用戶肉眼判（這是迄今最接近 P1 的一支）。
- **等表態**：① silent 微超標降 advisory（硬數據已到位）② 0.5 MP → 1.0 MP ③ Round 47 另兩案（衣柜門檻相對化、禁 invented 額頭皺紋／維持參考圖年齡）④ 袍服紅金滾邊仍是 invented detail（P1 無）。
- **逃生門未動用**：三個 env 出厂 off 的假設獲實機支持；若 silent 嘴最終不可接受，`H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1` 一鍵回退凍結即可。

**F. 本節工具**：`working\_r49_montage.py`（82 vs 81 四列 × 7 時間點，左欄 P1 sheet）、`working\_r49_seam_montage.py`（三個 5 格時間帶 = 兩處 Relay 窗邊界＋可疑洩漏帶）；讀幀目錄 `_dsh_verify_9\round49\`。本轮 ComfyUI 除 driver 的一槍外只做唯讀 `/history`。

## 51. Round 49c（2026-10-30 12:25–12:51 **實機一槍**，seed 923011207／**1.0 MP**；**影片已實機驗證＝本專案首發「單發＋QC 全綠」**；本輪零源碼改動）

**A. 範圍與政策**：`VERSION` 仍 `0.3.8-alpha.3`、Project Format 29、`SMART_RENDER_POLICY_VERSION` 仍 **82**（megapixels 屬 Job 參數，不是 policy 行為）⇒ **未動產品源碼、未跑測試**（沿用 Round 49 的 352 項全綠）。變因只有一個：`megapixels` 0.5 → 1.0。

**B. GPU 交棒（走 `staged_model_driver.py run`，未 bypass）**：tray `12:25:55 QWEN→FREE` ⇒ worker ⇒ `/free` ⇒ `12:49:00 load requested` ⇒ `12:50:04 load confirmed（63 s）` ⇒ `12:51:40 auto-resume`。GPU 被 ComfyUI 佔用 **≈22.5 分鐘**（0.5 MP 那槍 ≈29 分鐘，因為本槍 `attempts_used=1`）。Job 檔 `preview_923011207_1793334264780896500` 已被 worker 刪除，只剩 manifest（18,463 B，`updated_at 2026-10-30T04:48:32+00:00`）⇒ 節點參數改查唯讀 `/history`。

**C. Pre-flight 七項全過（`working\_r49c_preflight.py`，零 GPU）**：policy 82／mp 1.0／單段 `0.0–12.864`；`h3_character_swap_v1.5.safetensors strength_model=1.5`＋turbo `0.8`；node `9` `RTXVideoSuperResolution scale=2 ULTRA` → `ref_images.ref_image_0`、`ref_image_size="match"`；plate 乾淨（無 `identity_suppressed`／`_silent`）且帶 `aac`；`window_frames=124`／`history_frames=18`／`schedule=adaptive`；**`H3RelayPrepareSource resolution="768"`（1.0 MP 生效判據）**；prompt 11,791 chars／1,802 words、`char_budget 12,320`、`dropped_tail_clauses=[]`。

**D. QC 全綠（首次）＋輸出規格**：`failure_class=""`、`character_swap_identity_failed=false`、`attempts_used=1`、`selected_attempt=1`、`passed=true`；`target_reference_similarity=0.630127`；`retention_score=-0.330738`；衣柜 `shift 0.130169`／`late 0.127764`（upper 0.16266、lower 0.130169，floor 0.12 兩半皆過、`source_wardrobe_retained=false`）；`complete_actor_erasure passed`（`identity_similarity_gap=-0.121683`）；`whole_character_integration passed`（`source_body_retained=false`）；`plate_continuity passed`；`source_audio_timing_audit{ok, offset 0.0, correlation 0.983089}`。ffprobe：`master.mp4` **800×1216＝0.973 MP**、24 fps、12.8 s、h264＋**aac**；1 segment、`relay_window_count=3`；ComfyUI 原始輸出 `pass_01_R1_00004_.mp4`。

**E. silent 判定的誠實拆解（`smart_render_worker.py:2470-2670`）**：`plate_relative_violated=true`（`result_motion 0.279222` > plate 上限 `0.225607`，`articulation_excess 0.053616`）但 `plate_gate_mode=advisory` ⇒ 不硬判；決定項 `motion_violated=false` 來自上半臉控制帶 `upper_face_motion 0.254111` ⇒ 相對上限 **0.337638** > 0.279（= 整張頭在動、非對嘴）；第二證據 `geometry_violated=false`（嘴腔 swing 0.15 vs 限 0.22）、`source_speech_conflict=false`、`decision_basis=pixel_motion`。**參照系措辭過時**：`verdict_scope` 仍寫 `relative_to_suppressed_plate`，出厂已無 suppressed plate。

**F. 讀幀結論（`_dsh_verify_9\round49c\`：`montage_10mp_vs_05mp.png`／`detail_fullheight.png`／`mouth_strips.png`）**：卡通媒介保留、**全身卡通（頭/手/袍/腿都是畫的，非貼頭）**、背景乾淨**無蜂窩**、**無 sheet 下半身洩漏**、三窗邊界無跳變、轉頭全程**閉嘴笑無開合**。

**G. 對 0.5 MP 基準（seed 923011107）**：相似度 0.613560 → **0.630127**；`retention_score` −0.225781 → **−0.330738**（更遠離 V1，對 swap 有利但分開講）；衣柜下半 0.136518 → 0.130169（略降、仍過線）；silent 由 `silent_mouth_excessive_articulation`（3 發用盡）轉為**單發通過**。

**H. 仍存的品質缺口＝模型服從度（非缺條款）**：`/history` 逐字證實 prompt 已含 `APPARENT AGE LOCK — MANDATORY`、`COMPLETE WARDROBE REPLACEMENT — MANDATORY`、媒介鎖定、silent `relaxed closed mouth with the jaw still`、旁角 `R2: KEEP V1`，且無 dropped clauses；但成片服裝**輪廓**仍沿用 V1 cosplayer 長袍（只推到 P1 的配色）、臉比 P1 顯老（額外額紋＋加出鬍子）、頭頂三根毛未出現、紅金滾邊屬 invented detail。

**I. 界定**
- **影片已實機驗證**：1.0 MP 出厂路徑（`resolution="768"` ⇒ 0.973 MP）、LoRA ≤1.5、RTX ×2、乾淨 plate＋原音保留、18 幀接力跨窗一致、身份／全身整合／衣柜／背景／無洩漏全綠，且**首次單發通過**。
- **尚未驗證**：無新的源碼宣稱需要驗證；本輪沒有代碼變更。
- **等用戶表態**：① silent 硬閘（方案 A，bump policy 83）② 衣柜門檻相對化 ③ 禁 invented 額紋／紅金滾邊、鎖參考圖年齡 ④ 服裝輪廓換變因（抽 seed／參考圖半身構圖／再上採）。
- **逃生門**：`H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1`／`H3_CHARACTER_SWAP_SILENT_AUDIO_STRIP=1`／`H3_CHARACTER_SWAP_RELAY_WINDOW_SPLIT=1`；LoRA 僅可調低 `H3_CHARACTER_SWAP_LORA_MAX_STRENGTH`。

**J. 本節工具**：`working\_r49c_preflight.py`、`working\_r49c_montage.py`、`working\_r49c_detail.py`、`working\_r49c_mouthstrip.py`（改 seed 即可重用）；讀幀目錄 `_dsh_verify_9\round49c\`。本輪 ComfyUI 除 driver 一槍外只做唯讀 `/history`。

## 52. Round 52 节（= CHANGELOG **Round 50**，2026-10-30 离线修码＋测试；**源码已修复＋981 项测试通过，影片未实机**）：policy 82→83 —— silent 硬闸加 12 % 容差改 advisory、衣柜 floor 加「相对增益」、GARMENT SILHOUETTE 拆成自己付帐的可丢弃条款、参考图上采倍率改由 env 决定

**A. 范围与动机**：用户在 Round 49c §I「等用户表态」四案里批准 1–4。`VERSION` 仍 `0.3.8-alpha.3`、Project Format 29；`SMART_RENDER_POLICY_VERSION` **82 → 83**（`director_cut_studio.py:856`、`smart_render_worker.py:222` 两处已同步）。bump 的正当理由＝两个 QC 判定语义改变＋prompt 尾部结构改变 ⇒ 旧 Job／旧 prompt 缓存必须作废。**本轮零 GPU**：没有向 ComfyUI 提交任何工作，policy 83 至今没有任何一枪。

**B. 四项改动（出厂值＝松绑后行为；每项都能一键回到 82）**

| 项 | 位置 | 要点 | env（出厂） |
|---|---|---|---|
| ① silent 硬闸容差 | `smart_render_worker.py:1555` `_silent_mouth_hard_gate_tolerance()`；用在 `:2566`；行内判定 `:2741-2805` | 先按 `decision_basis` 选 `governing_motion_limit`（plate 限／嘴腔 swing 限／pixel-motion 限），再把绝对超出换成跨 Shot 可比的 `overrun_ratio = articulation_excess / governing_limit`；`overrun_ratio ≤ 容差` **且** `not (geometry_available and geometry_violated)` ⇒ `advisory_overrun=true`、`violated=false`（不烧 fresh seed）。只降不升；嘴腔几何这条独立通道永远还能把它拉回硬判。manifest 新增 `overrun_ratio`／`hard_gate_tolerance`／`advisory_overrun`／`advisory_overrun_rows`／`hard_failed_rows` | `H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE`＝**0.12**（`0`＝精确回到 82 硬判） |
| ①b 参照系措辞 | `:1588 _silent_plate_verdict_scope()` | 自 policy 74 起每行都写 `relative_to_suppressed_plate`，但 82 出厂 plate 是干净 V1 ⇒ 现按实际开档的 plate 文件名回报 `relative_to_clean_source_plate`／`relative_to_suppressed_plate` | 无（纯措辞） |
| ② 衣柜 floor 相对化 | `:1964` `_wardrobe_floor_policy_settings()`、`:2004` `_wardrobe_region_passed()`；逐区 `:2988`、Shot 层 `:3129` | 通过条件＝绝对 floor（不动）**OR** 相对增益（`shift ≥ max(sanity_floor, source_median×0.10)` 且 `take_median ≥ source_median×1.10`）。`absolute` 精确重现 82；`floor=0` 仍是「该 Shot 不管衣柜」。两处在同一实现上 ⇒ manifest 不会宣称某区用了聚合层没套的规矩。manifest 新增 `floor_policy`／`relative_gain`／`sanity_floor`／`required_relative_shift`／`absolute_floor_passed`／`relative_floor_passed`／`aggregate_rule_passed` | `H3_CHARACTER_SWAP_WARDROBE_FLOOR_POLICY`＝**relative**／`_RELATIVE_GAIN`＝**0.10**／`_SANITY_FLOOR`＝**0.03** |
| ③ prompt 条款 | `character_swap_engine.py:1891`、`:2196-2237`、`:2220`、rank 表 `:213` | `APPARENT AGE LOCK`＋`NO INVENTED CHARACTER DETAILS`（禁 invented 面部毛／眼镜／饰品／徽章／滚边／金属边／绣花；也禁删 P1 已有的胡子、**圆眼镜**、帽、领口点）49c 已用 `/history` 逐字证实送达。本轮把 `COMPLETE WARDROBE REPLACEMENT` 尾句「剪裁／长度／贴身／下摆」**剪出来**做成独立条款 `GARMENT SILHOUETTE — MANDATORY`，挂 **rank 1** | 无新 env |
| ④ 参考上采倍率 | `character_swap_engine.py:75-77`、`:2370`、`:2541-2566` | `RTXVideoSuperResolution`（模板 `scale=2`／`ULTRA`）倍率可由 env 覆写，接受 **2／3／4**；节点缺席或值不认识 ⇒ 保留模板值并在 contract 现形（`reference_upscale_scale_source`＝`template`／`environment`）；模板只有 mode 没 multiplier 时也补 `resize_type.scale` | `H3_CHARACTER_SWAP_REF_UPSCALE_SCALE`＝出厂**不覆写**（沿用模板 2） |

五个开关都已进 `director_cut_studio.py:434 DESIGN_ENV_RENDER_KNOBS` ⇒ 写进 `design_ai.env` 就会随 Preview 生效、跨 Studio 重启保留；启动环境的真变量仍然赢。

**C. ①的 12 % 是怎么定的，以及它故意不救哪些枪（诚实边界，改代码前后同一公式重算）**

| 素材 | 判定通道 | excess／limit | overrun_ratio | 读帧真相 | 12 % 容差后 |
|---|---|---|---|---|---|
| seed 923011107（0.5 MP／policy 82，manifest 现存） | `pixel_motion` | 0.034924／0.225607 | **15.5 %** | 读帧＝闭嘴笑 | **仍硬判** |
| seed 923011207（1.0 MP） | `plate_relative`（advisory，不是决定项） | 0.053616／0.225607 | **23.8 %** | 读帧＝闭嘴、决定项 `motion_violated=false` | 本枪原本已 pass |
| 用户否决的 S3／S5 真对嘴 | `pixel_motion` | 15 %／53 % | **15 %／53 %** | 真的对嘴 | 仍硬判（正确） |

结论：pixel-motion 通道**分不出**「闭嘴但整张头在动」与「真对嘴」（两者落在同一个数字上），所以出厂容差刻意压在已观察到的最窄超标 15 % **之下** —— 只挡 micro-overrun，不 retroactively 平反 923011107。能分开两者的是独立几何通道（`H3_CHARACTER_SWAP_MOUTH_GEOMETRY=on` 时它的违规优先于容差）。要让那一类过关：`H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE=0.16`，不必改码。

**D. ③的结构性发现（本轮最重要的工程结论）**：`.codex_tmp\r50_probe_drop_order.py`（零 GPU，从无限预算往下扫，打印长度守卫**真实**的丢弃顺序与每笔赎回量；`dropped_tail_clauses` 报的是**发射顺序**不是丢弃顺序，读 manifest 时要小心）：

| 条款 | 新 rank | 赎回 chars | 它守住的失败 |
|---|---|---|---|
| `wardrobe_silhouette_reinforcement`（本轮新增） | **1** | 185 | 尚未验证的加固（剪裁／长度／下摆） |
| `close_up_silent_mouth` | 2 | 647 | close-up 对嘴 |
| `medium_shot_silent_mouth` | 3 | 660 | medium 对嘴 |
| `source_costume_leaves_plate` | 4 | 527 | **S4「源演员长袍回到 P1 身上」** |
| `close_up_sheet_crop_lock` | 5 | 768 | **S7／S9 防镜头位移、防 sheet 的手／袖／下摆窜入** |

Silent identity-sheet close-up 未预算 **13,096 chars**、预算 12,320 ⇒ 必须赎 **776**。rank 1＋rank 2 ＝ 185＋647 ＝ **832**，两笔就够 ⇒ **rank 4 与 rank 5 都留在页面上**。若那句话仍留在不可丢弃的 `COMPLETE WARDROBE REPLACEMENT` 里（同规格同样 13,096，但可丢弃池只剩 647／527／768）：第一笔 647 盖不掉 776 ⇒ 守卫必须再丢 `source_costume_leaves_plate`。⇒ **拿已验证的闸门去换一句未验证的加固是错误方向**；新增加固句必须自己付帐。

**E. 测试／编译**
- `testing\test_character_swap_engine.py` **85 项全绿**
- 全套：`.\ai_libraries_common\python_env\python.exe working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **981 项 OK（skipped=10）、exit 0**，log `testing\_r50_batchB.log`
- timeline 定点：`DirectorTimelineDragTests.test_character_swap_*` **6 项 OK（25.2 s）**
- allowlist 追加后复核：`testing\test_character_swap_closeup_gates.py` **77 项 OK**
- `py_compile`：`director_cut_studio.py`／`character_swap_engine.py`／`smart_render_worker.py`／`source_video_analysis.py`／`character_identity_sheet.py`／`identity_sheet_page.py`／`staged_model_driver.py` 全过
- 四项 stale 测试改成测出来的新顺序：`test_silent_merged_clause_never_yields_and_the_mouth_reminder_does`、`test_prompt_budget_guard_drops_restatements_in_declared_order`、`test_medium_and_plate_texture_clauses_are_never_droppable`、`test_sheet_crop_lock_is_the_last_clause_the_guard_sacrifices`

**F. 界定**
- **源码已修复**：①②③④ 全部落码且有测试覆盖。
- **影片未实机**（policy 83 零枪）。要看到差异分别需要：① 一支 `overrun_ratio` 在 12–16 % 的 take；② 一支暗色服装、绝对 shift < 0.12 但相对增益 ≥10 % 的 Shot（923011207 的 0.130169 本来就过线，本轮买的是余裕）；③ invented 滚边／额纹是否消失要肉眼判（49c 已证实「送达但不服从」）；④ 3× 上采的 GPU 成本取舍未测。
- **回退**：`_TOLERANCE=0` ＋ `_FLOOR_POLICY=absolute` 精确重现 82 的 QC 判定；prompt 侧无 env（要改得动 `CHARACTER_SWAP_TAIL_DROP_RANKS`）；不设 `H3_CHARACTER_SWAP_REF_UPSCALE_SCALE` 即回到模板 ×2。Round 49 的三个 off 开关不受影响。
- **下一枪怎么跑**（用户会用 Studio 亲自 Preview；CLI 等价）：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`；fresh seed 从 **923011307** 起。GPU 三条硬约束不变（见 §12）：driver 内置 unload-qwen → wait-comfy → worker → `/free`，Segment 之间不插 `/free`。

**G. 本节工具**：`.codex_tmp\r50_probe_drop_order.py`（丢弃顺序与每笔赎回量，换 spec 即可重测）。本轮 ComfyUI 端**零请求**。

## 53. Round 53 节（= CHANGELOG **Round 51**，2026-10-30 离线修码＋测试；**源码已修复＋1004 项测试通过，影片未实机**）：policy 83→84 —— crop lock 的触发条件改读 plate 而非 box（根治「V1 半身、生出 P1 全身」）、prepare bucket 地板垫到 1.0 MP（根治人物老人化）

**A. 范围与动机**：用户回报最新一支 black-shirt 影片「效果很好，唯一的问题：人物变成老人化；v1 的人物是半身，但创作出来的却是 p1 的全身」。`VERSION` 仍 `0.3.8-alpha.3`、Project Format 29；`SMART_RENDER_POLICY_VERSION` **83 → 84**（`director_cut_studio.py:875`、`smart_render_worker.py:239` 两处已同步）。bump 理由＝prompt 尾部结构改变（crop lock 触发条件变宽）＋ prepare bucket 出厂值改变 ⇒ 旧 Job／旧 prompt 缓存必须作废。**本轮零 GPU**：ComfyUI 端零请求，policy 84 至今零枪，全部证据取自既有 manifest 与离线探针。

**B. 两个根因（各自独立，都已在真数据上验证）**

| 症状 | 根因 | 修法 | 位置 |
|---|---|---|---|
| V1 半身、结果却是 P1 全身（脚跑出来） | 阻止 Relay 拉宽镜位的 `CLOSE-UP SHEET CROP LOCK` 只由 `face_dominant_closeup` 触发。失败那枪 plate 头覆盖只有 **0.214413**、sheet 头覆盖 **0.5259** ⇒ 脸不 dominant ⇒ 条款没上桌；而 neck-down 全身衣柜视图是 Relay 收到的最强「整个人该在框里」讯号 ⇒ 它把镜头拉到出现鞋子。手动合格矩形又被 UI 刻意缩到 0.30×0.30，**用 box 尺寸永远猜不到 plate 自己在底边切人** | 新增 plate 探针 `measure_source_figure_reveal()`（ffmpeg 解 96 宽灰阶、均匀 6 幀、在框中央带量移动主体最低列）⇒ `reaches_frame_bottom` 为真就不分脸大小一律送 crop lock | `character_identity_sheet.py:1073`（探针）、`director_cut_studio.py:7709 source_figure_probe_box()`、`:35401-35425`（跑探针并写 metrics）、`character_swap_engine.py:1934-1940`（闸门） |
| 人物老人化、头跟参考图不像 | prepare 节点的 `resolution` 是 **bucket 不是尺寸**：只发布 480／768，H3 按 bucket 自己的长宽比出片 ⇒ **480→576×864、768→800×1216（像素 2.4 倍）**。0.5 MP 的每一窗都回报「媒介对、头不像、人变老」；导演接受的那枪（`preview_923011207`，policy 82、1.0 MP、take 800×1216、307 幀）prompt 形状相同且**首次尝试就过** ⇒ `APPARENT AGE LOCK` 只在 768 服从，选小 bucket 等于把它默默买掉 | `character_swap_megapixels_floor()` 出厂地板 **1.0 MP**，`character_swap_effective_megapixels()` 只抬不降（0.5 MP Preview 从此走 768） | `character_swap_engine.py:2425-2473`、`:2476-2489`、`:2539` |

**年龄漂移先是分辨率问题，然后才是 prompt 问题** —— 这条也解释了 50 轮「条款送达却不生效」的谜。

**C. plate 探针的六个控制组（`working\_r51f_probe.py`，真 plate `.director_cache\source_remake_relay_video\v1_relay_7055bf5e541b4614b9cb_0.000-12.860.mp4`，426×642@24，就是失败那枪 manifest 里的 plate）**

| 控制组 | 探针读数 | 结果 |
|---|---|---|
| 真 plate 框 `[0.35,0.15,0.65,0.45]` | deepest **1.000**、median **0.9444**、证据 2 帧 | 举旗 ✓ |
| 框缩小、下方仍黑边 | deepest 0.983696、证据 0 帧 | 不举旗 ✓（实测要 ≥2 列余裕才判 False，不是贴边就翻） |
| 框缩小、上方加垫 | deepest 1.000、证据 2 帧 | 举旗 ✓ |
| 整幅都在动 | qualifying share 0.538（未触发 0.90 全域动态守卫） | 举旗（已知良性） |
| 窄框 `[0.48,…,0.52,…]` | 中央带自动放宽到 8 px、证据 3 帧 | 举旗 ✓ |
| 框在主体外 `[0.02,0.62,0.20,0.95]` | deepest 0.965、证据 0 帧 | 不举旗 ✓ |

探针框**只取横向坐标**（整帧解码、由帧自己的行决定下方是不是背景），所以合格矩形怎么缩都不影响读值；`source_figure_probe_box()` 优先用被选角色自己的框，退回最大角色框（与身份审计选主体的老规矩一致）。无 ffmpeg／无主体证据／框太窄／`global_motion` 一律 `None`，呼叫端一律当 False ⇒ **每个失败模式都精确等于 policy 83 的旧行为**，这就是为什么不需要额外的回退开关。

**D. prompt 预算（12 320 字元；新条款要自己付帐）**

| prompt 形状 | 未预算 | 送达 | 余裕 | 被丢条款 |
|---|---|---|---|---|
| 静音 Identity-Sheet 大脸特写（框 `[0.05,0.02,0.98,0.99]`） | 13 137 | 12 305 | **15** | `close_up_silent_mouth`、`wardrobe_silhouette_reinforcement` |
| 说话者大脸特写（同框） | 10 944 | 10 944 | 1 376 | — |
| medium 框 `[0.42,0.26,0.85,0.82]`、探针不举旗（＝83 形状） | — | 11 152 | 1 168 | — |
| medium 框＋探针举旗（＝真正失败的那种 Shot） | — | **11 961** | **359** | —（crop lock 已上桌、`MEDIUM-SHOT SILENT MOUTH REINFORCEMENT` 保留） |

- 场景选得对的交叉验证：末列与失败那枪实际送达的 `prompt_chars 11 977 / 12 320、dropped []` 只差 16 字元。
- **真正需要被救的那种 Shot 一分钱没付**（359 余裕）。只剩大脸特写形状卡在 15 字元，而它 83 就已经带着 crop lock，本轮只多约 40 字措辞。长度 pin `12 300`→**`12 320`**，并注明 36 字元安全窗已不复返（只剩 15）；真正会拦住未来 rank-4/5 丢失的是 `test_shipped_budget_keeps_the_crop_lock_on_a_silent_sheet_closeup`。

**E. manifest 新键**：探针四键 `source_figure_reaches_frame_bottom`／`source_figure_bottom_normalized`／`source_figure_reveal_status`／`source_figure_reveal_sample_count`（allowlist `director_cut_studio.py:1850-1858`；第一个不加前缀，因为 engine 闸门就读这个名字）＋ prepare 四键 `relay_prepare_node_id`／`relay_prepare_resolution`／`requested_megapixels`／`effective_megapixels`（contract `character_swap_engine.py:2695-2703` → manifest `director_cut_studio.py:37560-37571`）。Job 上的 `megapixels` 仍是导演的请求，缺了后四行就没法事后区分「0.5 MP 却默默渲染成 800×1216」与「真的在 576×864 变老」。

**F. 测试／编译**
- `testing\test_character_swap_engine.py` **96 项全绿**（85→96：探针触发 crop lock 5 项、无探针时大脸仍送 crop lock 1 项、`CharacterSwapPrepareResolutionTests` 6 项）
- `testing\test_identity_sheet.py` **67 项全绿**（55→67，新增 `SourceFigureRevealProbeTests`；顺带修该档自己的 `_frames()` helper 误写 `range(6)`，导致多帧情境一直没被覆盖）
- `testing\test_round50_qc_relaxations.py` **21 项全绿**（长度 pin 改 12 320）
- timeline 定点：`-m unittest testing.test_director_timeline -k character_swap` **6 项 OK（21.3 s）**（该测试需要 `PYTHONPATH` 含 `testing` 目录）
- 全套：`working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **RAN 1004、failures=0、errors=0、skipped=10、exit 0（277 s）**
- `py_compile`：7 支产品／测试档全过

**G. 界定与回退**
- **源码已修复**：读 plate 决定 crop lock、prepare bucket 地板，两者都落码且有测试覆盖。
- **影片未实机**：policy 84 零枪。① crop lock 只在「plate 于底边切人」的 Shot 看得出差异（black-shirt 案正是；`a_cartoon…shirt_9` 那种全身 Shot 不会变）；② 老人化要看同一枪里 `APPARENT AGE LOCK` 是否开始服从。**A、B 必须在同一枪评分**：静音大脸形状只剩 15 字元余裕，拆两枪看不出取舍。
- **回退**：`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 立刻回到 480 bucket；探针不举旗（含全部失败模式）即回到 83 的 crop lock 条件，无需另设开关。Round 50 的四个开关不受影响。
- **成本**：0.5 MP Preview 现在出 800×1216 ⇒ 每枪 GPU 时间约 **2.4 倍**。用户用 Studio 按 Preview 即可；CLI 等价 `.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`，GPU 三条硬约束见 §12。**下一枪 fresh seed 建议从 923011307 之后另取**（83 那一枪已用 923011207）。
- **仍未表态的用户项**（不要擅自动）：silent 嘴部容差要不要超过 0.12（失败那枪 3 颗 seed 都烧在 0.361）；衣柜相对 floor 要不要再收紧（0.4909 过线却生成了黑金长袍＋蜂窝纹理）；圆眼镜残差；禁止发明的额头皱纹／维持参考图年龄（49c 已证实「送达但不服从」）；186 字的 `GARMENT SILHOUETTE` 是否反而帮它发明长袍（未证）。

**H. 本节工具**：`working\_r51f_probe.py`（六组控制组探针读数）、`working\_r51h_headroom.py`／`working\_r51i_medium.py`（预算表两端）、`working\_r51_delivered_prompt.txt`、`working\r51\*.png`。本轮 ComfyUI 端**零请求**。

## 54. Round 52 节（= CHANGELOG **Round 52**，2026-10-31 离线修码＋测试；**源码已修复＋1051 项测试通过，影片未实机＝0 枪**）：角色替换模块「推到重来」——三条 prompt 路线（路线 1 出厂、路线 2 Design 开关、legacy 逃生口）、身份 QC 全转目击者、prepare bucket 地板退回 0

**A. 范围与用户裁定**

用户的原话是「我想把这个角色替换 skill 所有的人物优化完全推到重来，但是保留主要的多角色 sam3.1 并接、自动分切 V1 片段、自动选角色、自动多角色检测、多人物替换」，并在随后给出的路线选项里选 **路线 1**、要求「路线 2 改成在 design 开关，default 路线 1」、要求「先补一次 `/free` 并清掉那张 70 分钟的 stale claim」。本节就是这三件事的落地。

`VERSION` 仍 `0.3.8-alpha.3`、Project Format 29；`SMART_RENDER_POLICY_VERSION` **保持 84**（`director_cut_studio.py:883`、`smart_render_worker.py:240`）。**本轮故意不 bump**：路线已经写进每个 pass 的 `prompt_budget.route` 并落到 manifest（`director_cut_studio.py:37648-37664`），事后归因读那一栏比读政策号更精确；政策号不动还能让 `example\` 里 2 066 份既有 manifest 继续互相比对。**本轮零 GPU 请求**；`/free`＋stale claim 经 driver `status`（只读）确认早已干净（`comfy_claim: none`、`comfy_queue: free`、Qwen 已由 tray 载回），所以没有补跑任何回收动作。

**B. 70 分钟那一枪的事后剖析（改码的直接动机）**

那一枪（policy 84、约 70 分钟）留下三处证据缺口，任何一处单独存在都不会让人误判，三处同时存在就完全无法归因：

| 缺口 | 现场 | 修法 |
|---|---|---|
| 死因只剩一行 | Segment 失败时 manifest 只存 `str(exc)`，实际值是 `[Errno 22] Invalid argument`，没有 traceback、没有 frame ⇒ 分不清 H3 拒绝／take 写档失败／claim 过期 | `smart_render_worker.py:4276` 起保留每次尝试的 traceback；失败列 `:6245-6254` 新增 `error_traceback`、`attempt_error_tracebacks`、`retry_budget` |
| 闸门自己烧掉 40 分钟 | `source_plate_drifted`（框外 median／MAE 粗闸门）先重摇两枪各约 20 分钟，第三枪才死在无关的写档错误 | lean 路线出厂 `plate_audit: False`（`director_cut_studio.py:37417-37426` → `smart_render_worker.py:2465-2472`）：**仍量、仍写 manifest**，只是不再单独判失败重摇 |
| 预算裁句不可见 | 12 320 字元预算从尾端裁掉条款，manifest 只记裁了哪几条、不记「不裁会多长」⇒ 无从判断「条款送达但不服从」和「条款根本没送达」 | 附录预算改为**只记录不裁句**（`append_chars`／`append_budget`／`append_over_budget`），legacy 分支保留老裁句行为 |

**C. 三条 prompt 路线（`character_swap_engine.py:316-373`）**

| route | 名称 | 怎么选到 | QC |
|---|---|---|---|
| `route1` | 路线 1「精准拆」（**出厂默认**） | 什么都不设，或 `H3_CHARACTER_SWAP_ROUTE=route1｜precise｜lean｜1` | advisory |
| `manual` | 路线 2「手动对齐」 | Design 页 checkbox `sourceRemakeManualAlignPrompt`（默认关，`director_cut_studio.py:11440-11474`）或 `=manual` | advisory |
| `legacy` | 逃生口 | `H3_CHARACTER_SWAP_ROUTE=legacy` | 旧的硬判定 |

- `character_swap_route()`：空白值与未知值回 **route1** 而不是 legacy —— 胖 prompt 正是这次要离开的对象；显式 `route=` 参数（Studio）永远赢过环境变量。route 每 Shot 决定一次、盖在每个 pass 列上（`director_cut_studio.py:37325-37328`）。
- 两个 env 名都在 `DESIGN_ENV_RENDER_KNOBS`（`:469`、`:474`）⇒ 写 `design_ai.env` 按 Preview 即生效、跨重启保留；启动环境变量仍优先。
- **官方作者模板逐字未改**：`prompt[:len(_relay_v2_author_prompt())] == _relay_v2_author_prompt()` 且 `author_prompt_chars` 对帐（3 377 字元）。只有模板之后的 Studio 附录长短是变量。

**D. 保留／删除／转 advisory 三栏（用户从菜单里选的那一份，逐条对应到码）**

| 处置 | 项目 | 现状 |
|---|---|---|
| **保留** | V1 自动分切、Qwen 多角色检测、自动 binding、手动画框优先＋大脸自动合格框、Identity Sheet preset 8 `fullfig`（800×1216 单人）、官方作者模板、bucket 逻辑、LoRA ≤1.5、turbo 8-step、relay 124＋18 帧接力、参考图 RTX ×2、job compile、preflight、upload、SAM3.1 多角色并接＋角色合成（仅多角色）、错误分类重试、组装／tail padding、源音轨时间稽核、`/free`＋manifest | 未改 |
| **删除（出厂不再做）** | 模糊 plate、silent-audio plate、prompt 字元预算裁句、silent megapixel 地板、`source_plate_drifted` 判定、QC 失败→fresh-seed 自动重试、best-of 多候选 | plate／silent-plate builder 仍在档内，由 Round 49 的三个 parity 开关控制（`H3_CHARACTER_SWAP_PLATE_SUPPRESSION`／`_SILENT_AUDIO_STRIP`／`_RELAY_WINDOW_SPLIT`，出厂全 off，`=1` 逐条还原）；地板出厂 `0.0`；lean 下 `plate_audit: False`、`maximum_attempts: 1` |
| **转 advisory** | 源相关性／相似度／mae、erasure gap、strict temporal coverage、whole-character audit、silent mouth audit、wardrobe shift、目标参考相似度、reveal probe／crop lock | 全量测、全写 manifest，但不让 Segment 失败（`smart_render_worker.py:4395`、`:4406`、`:5972-5992`；manifest 键 `character_swap_identity_advisory_only` `:6016`；Studio `director_cut_studio.py:34883-34884` 对 advisory verdict `continue`） |

真实错误（H3 拒绝、缺 P 图、缺档、写档失败）**没有**被一起弱化：仍照 `segment_attempts`（默认 3）重试。

**E. 三条路线的 prompt 实测（`working\r52_route_probe.py`，可重跑；lean 预算 4 200／manual 2 400／char budget 12 320）**

| 形状 | 路线 1 全文／附录 | 路线 2 全文／附录 | legacy 全文／附录（被裁条款） |
|---|---|---|---|
| A 静音 sheet 大脸特写（含抑制 plate＋保护 R2） | **8 373／4 977**（`append_over=True`、`over=False`、dropped `[]`） | 5 670／2 274 | 13 145／9 749 ⇒ `over=True`，丢 `close_up_sheet_crop_lock`、`close_up_silent_mouth`、`wardrobe_silhouette_reinforcement` |
| B raw medium 说话者 | 6 426／3 049 | 4 865／1 488 | 8 391／5 014 |
| C 双人 sheet | 6 965／3 588 | 4 984／1 607 | 9 864／6 487 |
| D tiny box medium | 6 208／2 831（框面积 <0.060 ⇒ 无 texture contract） | 4 865／1 488 | 7 468／4 091 |

- 用户的原始观察被量化：失败那枪送达 11 941 字元，其中 **9 065 字元是 Studio 附录**；路线 1 同形状 8 373（附录 4 977）、路线 2 5 670（附录 2 274）。三个 shape 上恒有 `manual < route1 < legacy`。
- 附录超预算也**不裁句**（A 的 4 977 > 4 200，`dropped_tail_clauses == []`，只把 `append_over_budget=True` 记进 manifest）。
- 措辞黑名单：路线 1／路线 2 永不出现 9 条 legacy 专属措辞（blurred plate、split panel、costume 等），避免「附录已经不做模糊 plate，条款还在讲模糊 plate」。
- crop-lock 举旗矩阵（路线 1）：sheet＋closeup **有**／raw＋closeup **无**／sheet＋figure_bottom **有**／sheet＋medium **无**；A＋live-action ⇒ 7 985 字元且**无** `APPARENT AGE LOCK`（medium 那句换成 live-action 版本）。

**F. megapixel 地板退回 0（把 Round 53／CHANGELOG Round 51 的 2.4 倍成本退还）**

`CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT = 0.0`（`character_swap_engine.py:2774-2782`）：0.5 MP Preview 回到 480 bucket（576×864，一枪约 9-10 分钟）；`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=1.0` 找回 768／800×1216（约 22 分钟）。只抬不降、`0` 精确重现、`>4.0`／负值／解析失败／**含 `nan`** 退回出厂值（NaN 守卫保留：`float("nan")` 解析成功、活得过上下界两道检查，会让 `max(requested, floor)` 变回 requested 且 `nan >= 0.75` 为 false ⇒ 地板无声消失）。**取舍要写明白**：Round 51 实测 `APPARENT AGE LOCK` 只在 768 服从，所以地板取消是把「老人化」的处方暂时换成「便宜、可多枪重试」；`relay_prepare_resolution`／`requested_megapixels`／`effective_megapixels` 三栏仍在 manifest，地板有没有生效一眼可查。

**G. 测试／编译／快照**

- 新建 `testing\test_round52_swap_routes.py` **47 项全绿**：`RouteResolutionTests` 6、`Route1ClauseSetTests` 9、`Route1GateTests` 10、`Route2ManualTests` 6、`ShippedMegapixelFloorTests` 5、`RouteKnobWiringTests` 5、`AdvisoryIdentityVerdictTests` 6（档内 marker 一律 ASCII 前缀，因为 headers 含 em dash）。
- 回归：`test_character_swap_closeup_gates`（77）＋新模组（47）= **Ran 124／OK**；新建 helper `testing\legacy_swap_route.py`（`pin_legacy_swap_route`／`pin_legacy_megapixel_floor`／`pin_legacy_megapixel_default`）把 7 个既有测试模组钉回旧行为后 **211 项 legacy 钉选测试全过** ⇒ 证明「胖 prompt 与其硬 QC 在 legacy 下一字未变」。
- 全套守门：`working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **RAN 1051、failures=0、errors=0、skipped=10、exit 0（267 s）**（基线 1 004＋本轮 47）。
- `py_compile`：`character_swap_engine.py`／`smart_render_worker.py`／`director_cut_studio.py`／`character_identity_sheet.py`＋新 test／helper／probe 全过。
- 快照：`_backup\r52_20261031_route1_policy84\`（四支产品码＋新 test＋helper＋probe）。本轮改动集中在 prompt 附录与 QC 判定，**没有任何一处需要靠 git 还原**。

**H. 界定（必须区分）**

- **源码已修复**：三条 route 的措辞与闸门、advisory QC、地板取消、traceback 落 manifest —— 全部落码且有测试覆盖。
- **影片未实机**：扫过 `example\` 全部 **2 066 份 manifest**，80 份带 `prompt_budget`、**0 份带 `route` 栏** ⇒ 路线 1 与路线 2 **至今 0 枪**。用户先前认可的「这次角色替换效果不错」来自 policy 82／83／84 的 legacy 形状，**不能记在路线 1 名下**。
- **回退**：`H3_CHARACTER_SWAP_ROUTE=legacy` 一条还原 prompt＋硬判定 QC；`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=1.0` 单独找回 1.0 MP 地板；Round 49 三个 parity 开关语义不变。
- **下一枪怎么跑（GPU 三条硬约束见 §12）**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`。验收顺序：① manifest `prompt_budget.route == route1`、`append_chars`／`author_prompt_chars` 与上表量级一致；② `character_swap_identity_advisory_only == true`、`attempts_used == 1`、`relay_prepare_resolution` 与请求 MP 一致；③ 才读片评「脸、衣服、头发、镜位、嘴」。地板取消后 0.5 MP 一枪约 9-10 分钟，跑完 driver 自带 `/free`。
- **仍未表态的用户项**（不要擅自动）：圆眼镜残差；禁止发明的额头皱纹／维持参考图年龄；衣柜相对 floor 要不要再收紧；silent 嘴部容差要不要超过 0.12。

**I. 本节工具**：`working\r52_route_probe.py`（三路线长度＋条款矩阵＋crop-lock 矩阵）、`working\r52_lean_sizes.py`、`working\r52_measure.py`、`working\r52_clear_claim.py`（stale claim／`/free` 核对）、`working\r52_dump1-15.py`、`working\r52_probe_failedjob*.py`、`working\r52_prompt_anatomy.py`、`working\r52_multi.py`（70 分钟那枪的事后剖析）。本轮 ComfyUI 端**零请求**。

## 55. Round 55 节（= CHANGELOG **Round 53**，2026-10-31 离线修码＋测试；**源码已修复＋1081 项测试通过，影片未实机＝0 枪**）：prepare bucket 改由「这一个 pass 有没有承诺年龄」决定，根治 0.5 MP 老人化

**A. 用户诉求与结论**

用户在 `example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4` 回报：「这一次效果完美，只有被替换的角色还是会发生老人化的问题，只要修正这个，我就可以马上更新 GitHub」。本轮只做这一项：**只动 bucket 判断**，不动 prompt 措辞、不动政策号、不动 Project Format。

结论先讲：老人化不是「年龄条款没送达」，而是**送进 H3 的 prepare 分辨率 bucket 太低**。同一张 identity sheet、同一组框架、同一套条款下，480 bucket 那一枪老人化、768 bucket 那一枪被导演采纳。

**B. 干净 A/B（老人化那一枪 vs 已采纳那一枪）**

| 项目 | 老人化（`_4`） | 已采纳（`preview_923011207`） |
| --- | --- | --- |
| `relay_prepare_resolution` | **480**（take 576×864） | **768**（take 800×1216） |
| requested / effective MP | 0.5 / 0.5 | 1.0 / 1.0 |
| identity sheet | preset 8，800×1216，`source_fingerprint a7d8b999cf3e69a3` | 同一张 |
| 框架数 / 尝试次数 | 307 / 1 | 307 / 1 |
| `APPARENT AGE LOCK — MANDATORY` | 已送达 | 已送达 |
| `failure_class` | `''` | `''` |

两边条款都在 prompt 里 ⇒ prompt 不是变量，bucket 是唯一还活着的变量。这一组对照同时**否决了那个最诱人的条件式修法**（「只在大脸／特写抬 bucket」）：老人化那一镜是 **medium**（design_plan `medium`×9、`face_dominant_closeup` false），特写导向的规则永远不会在需要它的这一镜上触发。

老人化那一枪的 prompt 只存在于 **job 档**（`segments[0].workflow.reference_conditioning.inputs.prompt`），manifest 里没有 prompt 副本 —— 这是本轮取证绕了一段路的原因，记下来省下次的时间。

**C. 改码（`character_swap_engine.py`＋`director_cut_studio.py`；`smart_render_worker.py` 无需改）**

- 新增常数 `APPARENT_AGE_LOCK_PROMPT_MARKER = "APPARENT AGE LOCK"`、`APPARENT_AGE_LOCK_MIN_MEGAPIXELS = 1.0`，以及三个理由常数 `megapixel_floor_reason` ∈ {`environment`、`apparent_age_lock`、`shipped_default`}（`character_swap_engine.py:2783-2818`）。地板取 1.0 而不是刚好跨过的 0.75：bucket 相同，但 manifest 读起来要和对照组一致。
- 新增 `character_swap_megapixels_floor_override()`（`:2849`）：把「操作者没表态」和「操作者明确说 0」分开 —— 两者从 `floor()` 都返回 `0.0`，只有这一支分得出来。公开的 `character_swap_megapixels_floor()` 语义**一字未改**（未设 → 出厂 0.0）。
- 新增 `character_swap_apparent_age_lock_in_prompt()`（`:2875`）：检测**编译后**的文字而不是 Shot 的旗标 —— 要付钱的是真正送进 H3 的那个承诺。路线 1 精简版与 legacy 完整版用同一个 heading，且 `apparent_age_lock` 没有 drop rank，所以 marker 缺席就代表这一 pass 真的没许过年龄（live-action adaptation、路线 2），而不是被长度守门裁掉。
- 新增 `character_swap_megapixel_decision()`（`:2889`）：优先序 **明确 env 覆写（含 `0`）→ 年龄条款地板 → 出厂默认**；请求**永不降低**（2.0 MP 仍是 2.0）。回传 `requested_megapixels`／`megapixel_floor`／`effective_megapixels`／`megapixel_floor_reason`／`megapixel_floor_applied`。非数字的请求退到地板而不是小 bucket（小 bucket 才是让角色变老的那一个）。
- `character_swap_effective_megapixels()`（`:2942`）新增 **keyword-only** 的 `apparent_age_lock`，默认 `False` ⇒ Round 53 之前写的所有调用方看到的仍是 Round 52 的世界。
- `compile_character_swap_pass`（`:3015-3019`）改用 decision；contract 多四栏 `megapixel_floor`／`megapixel_floor_reason`／`megapixel_floor_applied`／`apparent_age_lock_in_prompt`（`:3189-3196`），`requested_megapixels` 原样保留；`director_cut_studio.py:37698-37712` 把四栏同步写进 pass row。
- 理由要分开记是有意义的：`effective_megapixels` 单独看无法区分「导演自己要求 1.0」与「Studio 不肯在 0.5 MP 的 bucket 上让角色变老」，而那正是 70 分钟那笔账的全部问题；把 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 设成逃生口时，也必须能从 manifest 证明「旋钮有在场，只是这次没动数字」。

**D. 成本、缓存与 ESTIMATE（要对用户讲明白的三件事）**

- **一枪变贵**：那镜 12.86 s 原本 0.5 MP 约 9-10 分钟，现在带年龄条款的 pass 一律走 1.0 MP／768，约 22 分钟。不要的时候 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 一条还原 Round 52 的定价。
- **旧 take 不会被复用**：pass row 进入 `content_fingerprint({... "passes": pass_rows ...})`（`director_cut_studio.py:37798`），栏位新增＋workflow 的 bucket 改变 ⇒ 之前 480 bucket 的已存 take 不会当缓存命中（预期行为，不是 bug）。
- **ESTIMATE 会先低估**：`project_workspace.py:494` 的 `estimate_resources` 依 profile 校准、不含 MP，所以 1.0 MP 的头几枪预估时间偏低，之后由 `record_resource_sample` 自我修正。
- `VERSION` 保持 `0.3.8-alpha.3`、Project Format 29、`SMART_RENDER_POLICY_VERSION` **保持 84**：事后归因靠 contract 的 `megapixel_floor_reason` 这一栏，政策号不动可让 `example\` 里 2 066 份既有 manifest 继续互相比对（沿用 §54 的裁量）。

**E. 测试／编译／快照**

- 新建 `testing\test_round53_age_lock_bucket.py` **30 项全绿**：`AgeLockMarkerTests` 7（含「长度守门永不裁掉 age lock」：legacy 最大形状 13 145 字元、`over_budget=True`、裁了三条仍留 marker）、`MegapixelDecisionPrecedenceTests` 9、`MegapixelKnobParsingTests` 4、`CompiledPassBucketTests` 5（真 V2 模板：路线 1＋0.5 MP ⇒ 768／reason `apparent_age_lock`／applied True；live-action＋0.5 MP ⇒ 480／`shipped_default`；env=0 ⇒ 480 且 reason 仍是 `environment`）、`StudioContractRowTests` 2（含「Studio 只转发、不自行决定 bucket」）、`EarlierRoundRegressionTests` 3（Round 51 的 env 地板与畸形值退回出厂值、Round 52 的 0.5 MP 定价都仍在）。
- 全套守门：`working\run_testing_suite_watchdog.py --stall 240 --skip test_director_timeline` ⇒ **RAN 1081、failures=0、errors=0、skipped=10、exit 0（253 s）**（基线 1 051＋本轮 30）。
- `py_compile`：`character_swap_engine.py`／`director_cut_studio.py`／`smart_render_worker.py`＋新 test＋probe 全过。
- 快照：`_backup\r53_20261031_age_lock_bucket\`（两支改动产品码＋新 test＋helper＋probe＋CHANGELOG＋本节 HANDOFF）。本轮改动集中在 bucket 决策与 contract 栏位，**没有一处需要靠 git 还原**（本目录非 git repo）。

**F. 界定（必须区分）**

- **源码已修复**：bucket 由年龄条款决定、四栏 contract、env 明确值永远赢过自动地板、非数字不退小 bucket —— 全部落码且有测试覆盖。
- **影片未实机**：本轮 ComfyUI **零请求**；`_4` 之后没有任何一支在 `megapixel_floor_reason == "apparent_age_lock"` 下渲染过的视频。「老人化已消失」**尚未验证**，必须跑一枪才算。
- **已知边界**：路线 2（manual）的 prompt 本来就没有年龄条款 ⇒ 它不会自动抬 bucket（已用测试钉选，避免以后被当成 bug）；要 768 就 `H3_CHARACTER_SWAP_MIN_MEGAPIXELS=1.0`。另一条尚未动的量测事实：identity sheet 的脸面板只有 178×152 px（来自用户 252×370 原图 LANCZOS 放大），但被采纳那一枪用的就是同一张 sheet ⇒ sheet 不是本轮变量。
- **回退**：`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 一条回到 480 bucket；其余不动。
- **下一枪怎么跑（GPU 三条硬约束见 §12）**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants\project\render_jobs\preview_<seed>_<ns>.job.json"`。验收顺序：① manifest `prompt_budget.route == route1`、`relay_prepare_resolution == "768"`、`megapixel_floor_reason == "apparent_age_lock"`、`attempts_used == 1`；② 才读片评「脸的年龄、衣服、头发、镜位」。跑完 driver 自带 `/free`。
- **仍未表态的用户项**（不要擅自动）：圆眼镜残差；禁止发明的额头皱纹／维持参考图年龄的措辞；衣柜相对地板 0.12；silent 嘴部容差。

**G. 本节工具**：`working\r53_dump_project4.py`、`r53_dump_prompt4.py`、`r53_find_prompt_key.py`、`r53_dump_job_prompt.py`（prompt 只在 job 档）、`r53_src_resolution.py`、`r53_clause_matrix.py`、`r53_compare_aged_vs_accepted.py`（A/B 对照表）、`r53_template_nodes.py`、`r53_probe_expectations.py`（本轮全部断言的实测依据，可重跑）。本轮 ComfyUI 端**零请求**。

## 56. Round 54 节（= CHANGELOG **Round 54**，2026-10-31 离线修码＋测试；**源码已修复＋14 项测试通过，影片未实机＝0 枪**）：policy 84→85 —— 路线 1 补回「源片残留造型属于被擦掉的演员」，治 V1 假发与 cosplay 背带挂回 P1 头上

**A. 用户诉求**

`example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4` 里 seed 5037347289670054459（31 22:41，policy 84、768 bucket）那支被导演判 **「不接受」**：V1 的红色双马尾假发＋猫耳长在 P1 的光头顶上、身上挂着粉色 cosplay 背带、圆框眼镜不见。要点是这一支的 `target_reference_similarity 0.688663` 是四支里**最高**的，却最差 ⇒ 相似度指标看不见「造型归属」这一类错，必须靠条款而不是靠 QC 数字。

**B. 证据（根因不在措辞不够长，在路线 1 留下的语义空洞）**

Round 52「推到重来」把 plate 模糊拿掉（出厂 `suppressed_plate = False`），而「头发归谁／戏服归谁」那几句原先是**挂在 plate 叙述上**的，于是它们**静默**了。模型看到的画面里 V1 的造型还在，但没有任何一句告诉它：**那些造型属于已被擦掉的演员，不属于参考角色**。manifest 侧的旁证：prompt 8 204 字元、`append_chars 4808`、`append_over_budget True`、`dropped_tail_clauses []` ⇒ 附录确实送达，只是里面没有这一句。

**C. 改码**

- `character_swap_engine.py:455` 新增 `LEAN_SOURCE_LOOK_OWNERSHIP`（**525 字元**），标题 `SOURCE LOOK BELONGS TO THE ERASED ACTOR — MANDATORY`，逐项点名头发、假发、头饰、戏服、配件不得转给参考角色；插入位置在 route-1 附录末尾、`FINAL MEDIUM PRIORITY` 之前；emission 在 `:2642-2651`，只在路线 1 且 plate 未被抑制的形状上触发。
- `SMART_RENDER_POLICY_VERSION` **84→85**，理由写在 `smart_render_worker.py:256-265`：会改变成片行为的强制条款必须换政策号，否则无法把「假发有没有被压住」归因到具体片。Project Format 29、`VERSION` `0.3.8-alpha.3` 不变。
- GPU 侧沿用 §12 三条硬约束（`staged_model_driver.py`）；Qwen 端已是 Strata，迁移本身已在 2026-10-26 那节登记，本轮只引用、不重复登记。

**D. 测试／编译**

- 新建 `testing\test_round54_source_look_ownership.py` **14 项全绿**（本轮注册时再跑一次仍 14 OK）：条款存在＋位置（必须在 `FINAL MEDIUM PRIORITY` 之前）、只在 plate 未抑制的路线 1 触发、live-action adaptation 开启时不冲突、长度守门不得裁掉它、旧路线不受影响。
- `py_compile` 三支产品码 exit 0。本轮 ComfyUI **零请求**。

**E. 界定（必须区分）**

- **源码已修复**：条款落码、位置与闸门有测试钉住、政策号已换。
- **影片未实机（0 枪）**：注意一件容易被误解的事 —— 已存 Job 把 prompt 当数据存着，**重新编译不会把这条款加进去**（见 §57），所以本轮连「顺手重跑旧 job」都不算验证。真正把 525 字元送进 H3 是 §58。
- **仍未表态的用户项**：圆眼镜形状漂移；禁止发明的额头皱纹／维持参考图年龄（下一节做）；衣柜相对地板 0.12；silent 嘴部容差。

**F. 本节工具**：条款长度与新旧对照 `working\r60_clause_lengths.py`（本轮注册时新增，可重跑）；四支 manifest 的 prompt／bucket／相似度对帐 `working\r60_compare_manifests.py`。

## 57. Round 55 节（= CHANGELOG **Round 55**，2026-10-31 23:35 工具轮；**零产品码改动，影片未实机＝0 枪**）：把新条款塞回「已存 Job」的 headless 拼装工具

**A. 为什么需要这一节（这是本项目的一个结构性坑，值得单独记）**

Smart Render Job 落盘时把 prompt 当**数据**存在 `segments[0].workflow.reference_conditioning.inputs.prompt`。因此对产品码新增的条款来说，「重跑这支已存 Job」只会重新决定 bucket，**永远不会把新条款写进 prompt**。要验证 §56 那条 525 字元，只有两条路：在 Studio 里重新 Preview（会新建 job），或者 headless 拼装。当时选拼装，因为它只动一个变量。

**B. 工具与它的自我防卫（`working\r55_build_source_look_job.py`，31/10 23:35）**

- 从产品码读 `LEAN_SOURCE_LOOK_OWNERSHIP`，断言**全档只有一份连续副本**（若将来出现第二份或被覆写，立即中止，避免拼到错的那份）。
- 把该段字串**逐字**插进已存 prompt 的同一位置（route-1 tail 末、`FINAL MEDIUM PRIORITY` 之前），再跑**已出货的编译器**重算 bucket。
- 出档前断言：graph prompt 逐字一致、bucket 不变、**只有 prepare-bucket 与那一条字串**发生变化、只有 master seed 变化。任一不符就不产出 job。

**C. 一笔必须留的帐**

拼装发生在**编译之后** ⇒ 该枪 manifest 的 `append_chars` 仍是「编译时的长度」，**不含拼进去的 525 字元**。读片评断时要手工加回：4808＋525＝5333。§61 的 5946＝4808＋525＋613 就是靠这条算式对上的，而不是拿两枪的栏位直接相减。

**D. 界定**：本轮零产品码、零 GPU 请求；工具的断言就是它的测试。实际的那一枪在 §58。

## 58. Round 56 节（= CHANGELOG **Round 56**，2026-11-01 00:39 **实机一枪**；**影片已实机＋导演分级「完美」，但残留老人化；本轮零源码改动**）

**A. 目的**

只验一件事：§54 那条 source-look ownership 条款真的送进 H3 以后，V1 的假发／cosplay 背带还会不会挂到 P1 身上。

**B. 这一枪的帐（manifest `preview_8178175072880861825_1793461399421021800.manifest.json`，01 00:38）**

| 项目 | 值 |
| --- | --- |
| driver log | `logs\r56_source_look_driver.log`（00:39 收工，`/free` 已执行，Qwen 由 tray 载回） |
| policy / route | 85 / `route1` |
| bucket | requested 0.5 → **effective 1.0**、`relay_prepare_resolution "768"`、`megapixel_floor_reason apparent_age_lock`、`megapixel_floor_applied True` |
| prompt_budget | `prompt_chars 8204`、`append_chars 4808`（少记 525，见 §57-C）、`append_over_budget True`、`dropped_tail_clauses []` |
| 结果 | `status complete`、`attempts_used 1`、`failure_class ''`、`character_swap_identity_advisory_only true`、`target_reference_similarity 0.668491` |
| 导演分级 | **「完美」**＋回报**角色仍老人化**、眼镜不见 |

**C. 意义与局限**

- **影片已实机且被导演采纳为「完美」**（路线 1 第一次）⇒ 「路线 1 ＋ 768 bucket ＋ 干净 V1」的**身体、衣服、头发、构图**已通过，这是这整段开发最重要的一个里程碑。
- 同一条言下：**老人化**与**眼镜**两项未过 ⇒ 直接催生 §59。分级「完美」不等于「没有问题」，两件事要分开讲。
- 本轮 ComfyUI 请求 **1 枪**（1.0 MP／768，12.86 s 镜约 22 分钟）。

**D. 本节工具**：driver 自身产出的 manifest＋`logs\r56_source_look_driver.log`；注册时的对帐 `working\r60_compare_manifests.py`、`working\r60_job_prompt_marks.py`。

## 59. Round 57 节（= CHANGELOG **Round 57**，2026-11-01 离线修码＋测试；**源码已修复＋17 项测试通过；影片已实机一枪但导演尚未分级**）：policy 85→86 —— 圆眼镜条款＋年龄锁重写

**A. 用户诉求**

§58 之后用户指定：「完成后继续修『圆眼镜』或『禁止发明的额头皱纹／维持参考图年龄』这类新条款」。本轮做这两项；眼镜**形状**漂移（圆→方）本轮不解决，登记为残差。

**B. 证据**

- 84／85 两枪的成片**眼镜 0／5 帧**（P1 本人戴圆框眼镜）⇒ 眼镜被「保持干净脸部」这类默认倾向擦掉，不是画歪。
- 两枪都画出比 P1 更深的额头皱纹（P1 只有三条浅额线）⇒ 旧的 `LEAN_AGE_LOCK` 只讲「维持年龄」太抽象，模型不知道**禁止发明什么**。

**C. 改码（`character_swap_engine.py` 两条款式＋`smart_render_worker.py` 政策注释）**

- 新增 `LEAN_EYEWEAR_WORN`（`:484`，**448 字元**）：`DRAWN EYEWEAR STAYS WORN — MANDATORY`。
- 重写 `LEAN_AGE_LOCK`（`:542`）：**280 → 445 字元（＋165）**，点名六种不得发明：叠加的额头皱纹、眉间纹、鱼尾纹、鼻唇沟、色斑、胡渣点；并要求维持参考图的平坦卡通画法与实际年龄。
- 合计 **+613 字元**。与 §54 的 +525 一起正好对上 manifest：`append_chars` 4808 → **5946**（4808＋525＋613），`prompt_chars` 8204 → **9342**（+1138）。
- `SMART_RENDER_POLICY_VERSION` **85→86**（注释 `smart_render_worker.py:256-265`）。Project Format 29、`VERSION` 不变。

**D. 本轮的实机一枪（policy 86 首发，导演尚未分级）**

manifest `preview_755358368423936257_1793466974167283100.manifest.json`（01 01:38）：policy 86／`route1`；`prompt_chars 9342`、`author_prompt_chars 3396`、`append_chars 5946`、`append_budget 4200`、`append_over_budget True`、`over_budget False`、`dropped_tail_clauses []`；`relay_prepare_resolution "768"`、`megapixel_floor_reason apparent_age_lock`；`status complete`、`attempts_used 1`、`failure_class ''`、`identity_advisory_only true`、`target_reference_similarity 0.686148`。**导演尚未分级** ⇒ 不能说「老人化已被压住」。

**E. 测试／快照**

- 新建 `testing\test_round57_eyewear_and_age.py` **17 项全绿**（本轮注册时再跑仍 17 OK）。
- 本轮状态被 §61 的 pre-run 快照 `_backup\V0.3.8-alpha.3_policy86_round59_reference_detail_pre_run_20261101\` 完整保存；本目录非 git repo，回退靠 env，不靠 git。

**F. 界定**

- **源码已修复**：两条款式＋政策号 86＋contract 栏位，落码且有测试。
- **影片已实机但未获导演采纳**：policy 86 已有 1 支；助理逐帧看到眼镜 3／5（见 §60），但导演未分级 ⇒ 结论未定。
- **仍未解决**：眼镜形状漂移；两枪的额头皱纹都比 P1 深。
- **下一枪怎么跑（三条硬约束见 §12）**：`staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4\project\render_jobs\preview_<seed>_<ns>.job.json"`；验收顺序 ① manifest `render_policy_version == 86`、`append_chars` ≈ 5 946、`relay_prepare_resolution == "768"`、`attempts_used == 1`；② 才读片评「眼镜在不在、形状、额头、衣服」。跑完 driver 自带 `/free`。

**G. 本节工具**：`working\r60_clause_lengths.py`（AST 抽出新旧条款常数并计字元数，本轮注册的算术依据）、`working\r60_append_probe.py`（policy 86 pass row 的 prompt_budget 逐栏展开）。

## 60. Round 58 节（= CHANGELOG **Round 58**，2026-11-01 逐帧 A/B；**零产品码改动，0 枪；读片为助理判定，不是导演分级**）

**A. 目的**

§59 两条条款的效果不能只看 manifest 数字，必须看帧。把 policy 85（00:38）与 policy 86（01:38）各抽 0.5／3／6／9／12 s 五帧并排，专看眼镜、额头皱纹、蜂窝背景。

**B. 工具与产出**

`.codex_tmp\r58_montage.py`、`.codex_tmp\r58_sweep.py`；ffmpeg `C:\ffmpeg\bin\ffmpeg.exe`；输出 `.codex_tmp\r58_frames\r58_faces.jpg`、`r58_full.jpg`、`r58_sweep_n86.jpg`、`r58_sweep_o85.jpg`。脚本要 `sys.path.insert(0, ROOT)` 才能 import 产品码。

**C. 助理读片（**不是导演分级**）**

| 观察项 | policy 85（seed 8178175072880861825） | policy 86（seed 755358368423936257） |
| --- | --- | --- |
| 眼镜出现的帧数 | **0／5** | **3／5**（6.0／9.0／12.0 s） |
| 眼镜形状 | — | 圆 → 方有漂移 |
| 额头皱纹 | 比 P1 深 | 比 P1 深（两边都有） |
| 蜂窝状背景 | 明显 | **大幅减少** |
| `target_reference_similarity` | 0.668491 | 0.686148 |

限制：**两枪 master seed 不同** ⇒ 这是方向性对照，不是受控 A/B；「眼镜回来了」要成立必须同 seed 再打一枪或由导演读片采纳。评断基准是 P1 本身：三条浅额线＋圆框眼镜＋黑金背心、蓝裤、黄格纹袜。

**D. 全套守门的插曲（与产品码无关但要留帐）**

`test_director_timeline` 会打真实端点，01:47 起跑后卡住约 75 分钟、最后写入 01:58（`logs\r58_director_timeline_tests.err`，41 677 B）。残留进程（PID 16028＋`design_ai_service.py` 子进程 16748／16840／27672／16576／28336）仍在与 Strata 抢资源。**以后全套计时不含该模块**（沿用 `--skip test_director_timeline`）；要清理那组进程需先问用户。

**E. 界定**：本轮**零产品码改动**、**零 ComfyUI 请求**（只读既有 take 的帧）；「眼镜已修好」「蜂窝已消失」都还没有被导演认可的片子支撑。

## 61. Round 59 节（= CHANGELOG **Round 59**，2026-11-01 离线修码＋测试；**源码已修复＋新增 26 项测试通过，影片未实机＝0 枪**）：参考图上采节点的 `quality`／`strength` 变成 env 旋钮，identity sheet 脸面板的「真实画素」进 manifest

**A. 用户诉求与本轮结论**

§60 之后残差是「脸不像 P1」。本轮先把像素链量清楚，再只发布**能改变送进模型的资讯**的杠杆。

| 环节 | 实测 |
| --- | --- |
| P1 原图 | `media\imported\P1_2d515d5f365e_…_n.jpg` = 252×370 = **0.09324 MP**（媒体池唯一一张 P 图） |
| identity sheet | preset 8，800×1216 = 0.9728 MP，`head_coverage 0.5259` |
| 脸面板真艺术 | sidecar `source_crop [16,1,194,153]` ⇒ **178×152 = 0.02706 MP** |
| 脸面板版面 | 774×662 = 0.51239 MP ⇒ **线性 4.35×**（面积 19.6×） |
| 衣服面板 | 250×217 = 0.05425 MP → 0.40248 MP ⇒ 线性 2.72× |
| 输出需求 | V1 plate 头覆盖 **0.214413** × 1.0 MP = **0.21441 MP** ⇒ 真艺术的 **7.9× 面积／2.81× 线性**（0.5 MP 仍 2× 线性） |
| 中继节点 | 模板 node `reference` LoadImage → **node 9 `RTXVideoSuperResolution` `scale=2, quality=ULTRA, strength=1.0`** → `ref_images.ref_image_0`，`ref_image_size="match"` |

结论：`ULTRA` 是**生成式**增强。0.09 MP 缩图迫使它猜脸上从不存在的微细节，而卡通脸上被猜出来的微细节就读成皱纹、胡渣、老人。同时**否决两条看起来最省事的杠杆**：`IDENTITY_SHEET_MIN_SOURCE_MEGAPIXELS` 出厂 0.35 > P1 的 0.09324 ⇒ 地板早已触发、preset 已被强制 8，「再调 layout／preset」在本案是 no-op ⇒ 本轮不发布任何不会改数字的改动。

**B. 改码（三个文件；未设 env 时 ComfyUI workflow 与已验证基线 byte-identical ⇒ 不影响推 GitHub）**

- `character_swap_engine.py:82-116`：`H3_CHARACTER_SWAP_REF_UPSCALE_QUALITY`（接受已安装节点公布的 `nvvfx.QualityLevel` 成员：`BICUBIC`／`LOW`／`MEDIUM`／`HIGH`／`ULTRA`／`HIGHBITRATE_*`／`STREAMING_*`）与 `H3_CHARACTER_SWAP_REF_UPSCALE_STRENGTH`（上限 1.0）。
- **不提供 `DENOISE_*`／`DEBLUR_*`**：那两种模式保持输入尺寸，选了就悄悄取消 ×2，一次动两个变量。提供 `BICUBIC` 是因为它是唯一「只插值、不增强」的模式 —— 检验「皱纹是不是 ULTRA 画的」的诚实做法。
- 编译段 `:3269-3364`：写 **6 个 record-only contract 栏** `reference_upscale_{quality,strength}{,_source,_override}`（`:3359-3364`）；`reference_upscale_scale*` 三栏是 Round 50 旧有，本轮不动。
- `director_cut_studio.py`：旋钮进 `DESIGN_ENV_RENDER_KNOBS`（`:465-470`）、缓存辨识 key（`:1886-1890`）、pass row 只转发（`:37749-37786`）。
- 新度量 `source_head_crop_megapixels`（`character_identity_sheet.py:470/485`，旧 sidecar 就地重算 `:1957-1959`，compose 写入 `:2155/2181`）→ Studio `identity_sheet_source_head_crop_megapixels`（`director_cut_studio.py:35661-35663`）。它与 `identity_sheet_source_head_coverage`（`:35467-35472`，**V1 clip** 的头覆盖）、`…_reference_head_coverage`（P1 自己的覆盖）是三个不同量，不要再混。
- `SMART_RENDER_POLICY_VERSION` **保持 86**：record-only pass row 本来就进 `content_fingerprint({... "passes": pass_rows ...})`；86→87 会把 `example\` 既有 R2V 缓存一起打掉，不值得。

**C. 成本与操作**

- 那一镜 12.86 s 在 1.0 MP／768 一枪约 **22 分钟**；改完码**要先重启 Studio** 再自己按 Preview。
- 性价比排序：① **重新导入高分辨率 P1**（≥0.35 MP，最好 ≥1 MP）是唯一**增加资讯**的修法，**零 GPU**；② `QUALITY=BICUBIC` 一枪；③ `STRENGTH=0.4–0.5` 一枪；④ `SCALE=3` 一枪；⑤ seed 抽卡（最弱，不改变 4.35× 这个事实）。

**D. 测试／编译／快照**

- 新建 `testing\test_round59_reference_detail.py` **26 项全绿**：`ReferenceUpscaleKnobParsingTests` 8、`CompiledPassReferenceUpscaleTests` 6、`HeadCropMegapixelsTests` 5、`ComposedSheetReportsReferenceDetailTests` 2、`StudioRegistrationTests` 4。
- 本轮注册时实跑：`test_identity_sheet.py` 67 OK、`test_character_swap_engine.py` 96 OK、`test_round54_source_look_ownership.py` 14 OK、`test_round57_eyewear_and_age.py` 17 OK（模块级合计 **220**）；`py_compile` 五支根 .py＋三支 test exit 0。**未跑全套**：全套最后一次是 §55 的 1081，`test_director_timeline` 会打真实端点且会卡（见 §60-D）。
- 快照：`_backup\V0.3.8-alpha.3_policy86_round59_reference_detail_pre_run_20261101\`（四支产品码＋H3 模板＋CHANGELOG＋本 HANDOFF＋VERSION＋三支 test＋driver）。
- 本轮对 `test_identity_sheet.py` 约 L1458 的「缺席白名单」做了一次**仅测试侧**修正（产品码未动）。

**E. 界定（必须区分）**

- **源码已修复**：两个 env 旋钮＋6 个 contract 栏＋Studio 转发与 key＋脸面板真实画素度量，全部落码且有测试。
- **影片未实机（0 枪）**：`QUALITY=BICUBIC`／`STRENGTH=0.4`／`SCALE=3` **一个都没跑**；「皱纹因此消失」目前只有机制推断，没有片子。「老人化已修好」在导演层面上**仍未成立**（§58 是「完美＋老人化」，§59 那支尚未分级）。
- **回退**：未设 env ⇒ 模板原样（×2／ULTRA／1.0）；`H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0` 回 480 bucket；`H3_CHARACTER_SWAP_ROUTE=legacy` 回旧胖 prompt。
- **下一枪怎么跑（三条硬约束见 §12）**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4\project\render_jobs\preview_<seed>_<ns>.job.json"`；验收顺序 ① manifest 出现 `reference_upscale_quality*`／`strength*` 六栏且 `attempts_used == 1`；② 才读片评皱纹／眼镜／衣服。跑完 driver 自带 `/free`，Qwen 由 tray 载回。

**F. 本节工具**：`working\r60_compare_manifests.py`（四枪对帐）、`working\r60_append_probe.py`、`working\r60_job_prompt_marks.py`、`working\r60_clause_lengths.py`、`working\r60_head_probe.py`／`r60_eol_fix.py`／`r60_handoff_eol.py`（本轮注册的文档行尾核对）。本轮 ComfyUI 端**零请求**。

## 62. Round 60 节（= CHANGELOG **Rounds 60–61** 前半，2026-11-01；**零产品码改动，0 枪**）

- 四枪 manifest 逐栏对帐（`r60_compare_manifests.py`）：policy 84 的三枪加 policy 85 一枪，`prompt_budget` 长短与「老人化」的严重度**没有相关性**（最短那支也老化、最长那支反而完美）。结论：继续在附录里加句子不是杠杆，要找的是**说了什么**而不是**说了多少**。
- 本轮 ComfyUI 端零请求；文档行尾核对工具也在本节登记（见 §60-F）。

## 63. Round 61 节（= CHANGELOG **Rounds 60–61** 后半，2026-11-01；**零产品码改动，0 枪**）

- 用 `r61_submitted_graph.py` 把 Studio 实际提交的 graph 与用户手动那张模板逐节点 diff，锁定唯一可单独移动的变量：**Relay 模板在 2026-10-29 22:26 被整组替换**。差异四项 —— PRISM merge 取代官方 ref2va checkpoint、video VAE 变 int8、新的 8-step turbo 挂在 0.8、Picture 1 上多一颗 RTX VSR（ULTRA、strength 1.0）。这正是「Studio 远差过手动 ComfyUI」的最可能来源。
- `r61_build_official_stack_job.py` 产出**只回退这四项**的候选图 `working\r61_candidate_relay_official_stack.json`，锚在存活的 policy-84 Job（导演分级「效果很好，唯一问题＝老人化」）上，prompt 逐字不变，因此文字不会漂。
- **界定**：本轮只有工具与候选档案，**一枪都没跑**；「官方 stack 能治老人化」至今是推断。

## 64. Round 62 节（= CHANGELOG **Round 62**，2026-11-01；**源码已修复＋测试绿，影片未实机＝0 枪**）

- 根因确认（Round 56–58 的对帐成果）：那支「效果很好，唯一问题＝老人化」的送件 prompt 8 204 字元里，author template（用户的官方模板）**0 个 aging 名词、0 个 texture 名词**，7＋7 全部来自 Studio 附录。模块自己的 canary 早就写着「点名字单里的物件会被画出来」，所以 `NO WRINKLES／NO STUBBLE／NO HONEYCOMB` 这类 do-not-add 清单是**自我实现的邀请**。
- 改法：八处站点从「不要加 X」改写成「把 P1 画的东西照原样重现」，`NO INVENTED DETAILS` → `EVERY DETAIL COMES FROM PICTURE 1`、`NO INVENTED TEXTURE` → `SURFACE PROVENANCE` 等；净 **+127 字元**。原有 gate（route／遮板／真人化）一个都没动，route 2 与 legacy 不受影响。
- 基准存档 `working\r62_submitted_prompt_pol84.txt` 从此是各轮的对照基线；快照 `_backup\V0.3.8-alpha.3_policy86_round62_negative_clauses_pre_fix_20261101\`。

## 65. Round 63 节（= CHANGELOG **Round 63**，2026-11-01，policy 86 → 87；**源码已修复，影片未实机＝0 枪**）

- 正面化之后剩下的长度是「同一件事讲两次」。逐站点删重复重申：五个常数值小计 **1 696 字元（−239）**，八处站点合计 **3 095 → 2 962**。
- `working\r63_measure_pins.py`／`r63_check_pin_strings.py`：把测试里钉死的字串与产品码逐字比对，避免「测试钉的是被删掉的旧句子」这种假绿。
- 全套 **1 138 项通过（0 failure／0 error，10 skipped）**，`logs\r63_full_suite2.log`。

## 66. Round 64 节（= CHANGELOG **Round 64**，2026-11-01；**影片已实机验证＝1 枪，导演分级「最完美」**）

- 为什么必须重建 Job 而不是重跑：Smart Render Job 把组装好的 prompt 存成**资料**（`segments[i].workflow.reference_conditioning.inputs.prompt`）。旧 Job 只会重跑它出生时的文字，Round 62/63 的正面前缀永远送不到 ComfyUI。
- `working\r64_build_policy87_job.py`（351 行，headless，`QT_QPA_PLATFORM=offscreen`，不碰 GPU）：开真专案 → 走真编译 `_build_smart_render_job(request_kind="preview")` → 读回 Job 稽核**实际送出**的 prompt。`window.clip_start.value = lambda: start` 那招是为了绕开 `CompactSecondsSpinBox` 的 2 位小数四舍五入（12.86 → 12.87 会生出一段幽灵 Segment）。
- 稽核清单：aging／texture 名词（送件全文＋Studio 附录分开算）、必需正面子句、clause header 与 policy-84 基准逐项比（`CLAUSE_RENAMES` 处理改名而非删除的两条）、`prompt_budget`、identity sheet 全套栏位、upscale／prepare／req-eff MP；任一失败就不保留 Job。
- **实机结果**：seed 6401000000000000001，policy 87，0.5 MP 请求 → 1.0 MP 生效（`megapixel_floor_reason=apparent_age_lock`），prepare 768，identity sheet preset 8 fullfig，attempts 1。导演分级：**「这一次最完美，只是画面出现眼镜」** → 唯一残差交给 Round 65。

## 67. Round 65 节（= CHANGELOG **Round 65**，2026-11-01，policy 87 → 88；**源码已修复＋全套 1 159 项绿，影片已实机验证＝1 枪**）

**A. 用户诉求**：「这一次最完美，只是画面出现眼镜，帮我修复掉，不要在画面强制放入眼镜」；并且（上一轮指令）**不许动**用户的 `H3-Character-Swap-Relay-V2-api.json`，力气全部放在 Studio 编译出来的 prompt。

**B. 根因（读片＋读码同时成立）**：`LEAN_EYEWEAR_WORN` 的 `DRAWN EYEWEAR STAYS WORN` 把眼镜写成强制条件。P1 画的是**无框小椭圆**，模型要满足「每一帧都戴著」只有两条路：画出 P1 那副（它画不好），或去 `<Video 1>` 捡现成的 —— 实测就是第二条：0–2.5 s 没戴，约 3 s 起换成 V1 那副粗黑方框，9 s 时一片镜片挂在下颌上。**眼镜不是被画错，是被条款逼出来的**。

**C. 改动（四支产品码：`character_swap_engine.py`、`smart_render_worker.py`、`director_cut_studio.py`＋测试）**

1. env 旋钮 `H3_CHARACTER_SWAP_EYEWEAR`：`uncovered`（默认）／`worn`（旧行为）／`neutral`（完全不提眼镜），带别名表与 `character_swap_eyewear_policy()`；拼错一律回落 `uncovered`（宁可不戴，也不要被逼出来）。
2. `LEAN_SOURCE_LOOK_OWNERSHIP` 结尾句改成格式槽 `headwear only if Picture 1 draws it{eyewear}.` —— `worn` 才追加眼镜从句。
3. 新增 `LEAN_EYEWEAR_UNCOVERED`（`THE FACE STAYS UNCOVERED — MANDATORY`，**430 字元 < worn 的 448**）：正面描述一张完整的脸（眼睛是 P1 自己的眼睛、没有框／镜片／镜圈／镜脚线／眼镜阴影），并明说被擦掉的演员的眼镜不得残留。**这里的命名逻辑与 canary 一致**：同样的名词清单，这次用来要求它们的缺席，而不是保证它们的存在。
4. `EYEWEAR_DETAIL_KEEP_LIST`（含 "spectacle"）／`BARE_DETAIL_KEEP_LIST`（不含）＋ `DETAIL_KEEP_LISTS`／`detail_keep_list()`；`LEAN_NO_INVENTED` 变成 `{details}` 模板。
5. `build_character_swap_prompt(..., *, eyewear_policy=None)`，在 `route` 旁解析 `eyewear`；route 1 依政策插子句并记 `eyewear_clause_shipped`；route 2／legacy／遮板／真人化四种形状逐一验证过**不会**带上裸脸子句。
6. lean audit 新增 `eyewear_policy`、`eyewear_clause_shipped` 两栏（`test_round52_swap_routes` 钉死的 key 集合同步更新）。
7. `SMART_RENDER_POLICY_VERSION` **87 → 88**，两侧各附一段本轮证据文字。

**D. 验证**

- 离线的送件数字（route 1，说话场景）：uncovered 附录 **4 532**／prompt 7 876；worn 4 545／7 889；neutral 4 042／7 386；silent 变体各 +1 043。四种形状都是 `append_over_budget True` 但 `over_budget False`、`dropped []`（长度护栏不会吞子句）。默认政策下 "glasses"／"spectacle" 在送件文字里出现 **0 次**。
- 测试：新建 `testing\test_round65_eyewear_optional.py`（19 项）；`test_round57_eyewear_and_age` 用 `pin_worn_eyewear()` 把那两项眼镜测试钉在 `worn`（默认已改）；`test_round54_source_look_ownership` 改成 mode-aware 并新增「worn 能恢复 Round 54 那句结尾」。**定向 52 项 OK → 邻近 9 个 suite 311 项 OK → 全套 1 159 项 OK（0 failure／0 error，10 skipped，269 s，`logs\r65_full_suite.log`）**。三支根 .py 与新测试 `py_compile` exit 0。
- 坑（下一个人会踩）：这批 suite 需要 `PYTHONPATH` 同时含仓库根**与** `testing\`（它们 import `legacy_swap_route` helper），否则会假报 3 个 ImportError；**永远不要**跑 `test_director_timeline*`（会打真实端点并卡住）。
- 离线建 Job 与稽核：`working\r65_build_policy88_job.py`（由 r64 fork，`FORBIDDEN_CLAUSES` 检查 `DRAWN EYEWEAR STAYS WORN` 必须缺席、`REQUIRED_POSITIVE` 换成 `THE FACE STAYS UNCOVERED`、`CLAUSE_RENAMES` 补上这次改名）。输出：policy 88、11 个 clause header、aging／texture 名词 0、glasses=0 spectacle=0、`dropped []`，送件全文存 `working\r65_submitted_prompt_pol88.txt`。
- **实机（1 枪）**：Job `preview_1482118348682408297_1793500493650525500.job.json`，master seed 1482118348682408297，pass seed 4947594498930359714，0.5 MP → 1.0 MP 生效（`apparent_age_lock`），prepare 768，identity sheet preset 8 fullfig（`identity_sheet_reason=cached`），`attempts_used=1`，走 §12 三条硬约束（`unload-qwen` → `wait-comfy` → worker → `/free` → report；driver 回报 `comfy-free ok`，Qwen 由 tray 载回）。抽帧 0.5／1.5／3／6／9／12 s 存 `working\r65_grade\save_*.png`：**6/6 全部裸脸，零眼镜、零镜片、零眼镜阴影**。同一批帧里 P1 的秃头＋三根呆毛＋额纹＋鼻型＋胡须线、黑金背心＋青蓝长袍＋黄格纹未回退，卡通媒介未漂移，背景无蜂窝。
- 本轮**没修**也仍会看到的残差（与 policy 87 相同，别误当回归）：虹膜偏写实、手偏写实；`silent_mouth_audit` 相对干净 plate 超限（result_motion 0.309 vs limit 0.226）但 `advisory_only=True`，`character_swap_identity_failed=False`。

**E. 界定（必须区分）**

- **源码已修复**：裸脸成为默认、眼镜不再是强制项、`worn` 仍可一键回退；有测试、有 audit 栏位、有离线稽核。
- **影片已实机验证**：「不再被塞眼镜」这件事在 1.0 MP 那一枪的 6 帧里成立（0/6 出现眼镜，对照 policy 87 那支的 3/5）。**没有**验证的东西：`worn`／`neutral` 两条回退路径的片子、silent 嘴部 advisory、整片 11 Shot。
- **回退**：`$env:H3_CHARACTER_SWAP_EYEWEAR="worn"`（恢复 Round 57 的强制戴眼镜）／`"neutral"`（完全不提眼镜）。两者都不改 policy 版本，audit 的 `eyewear_policy` 栏会如实记录。
- **下一枪怎么跑（§12 三条硬约束不变）**：`.\ai_libraries_common\python_env\python.exe staged_model_driver.py run "example\a_cartoon_character_with_a_black_shirt_and_yellow_pants_4\project\render_jobs\preview_<seed>_<ns>.job.json"`；验收顺序 ① manifest `render_policy_version==88` 且 `attempts_used==1`；② 才读片评眼镜／皱纹／衣服／背景。

**F. 本节工具**：`working\r65_build_policy88_job.py`（headless 建 Job＋稽核）、`working\r65_submitted_prompt_pol88.txt`（送件全文）、`working\r65_grade\`（六帧分级）、`logs\r65_full_suite.log`、`logs\r65_build_job.log`、`logs\r65_driver_run.log`。本轮 ComfyUI 端**恰好 1 枪**，跑完 `/free`。

> **§68–§72 是 2026-11-02 的补登记。** Round 66／67／69／75 当时都没有写进本文件（Round 66 更被导演整体 undo），本节以下把事实重建一次。**旧的「§N = Round N−3」编号惯例从 §68 起不再成立**，每节标题都显式写自己对应的 Round 编号。

## 68. Round 66 节（= CHANGELOG **Round 66**，2026-11-01；**当天被导演整体 undo，只留下 480 手工钉值；0 枪**）

- **诉求**：「preview 使用 768 解像度，而不是原装的 480，造成 preview 时间特别久，请改正这一点」。
- **当时的证据链**（今天在 `_5` 的 `project\render_manifest.json` 仍可复核）：`request_kind="preview"`、`requested_megapixels=0.5`、`effective_megapixels=1.0`、`megapixel_floor_reason="apparent_age_lock"`、`relay_prepare_resolution="768"`（前五栏分处两层：`request_kind` 在最外层，四栏在 `segments[].character_swap_passes[]`）。Preview 与 Final 走同一条编译路径，Round 53 那条「承诺了外观年龄 ⇒ 地板 1.0 MP」的**自动**地板照样落在草稿上。
- **当时的修法（现已不存在于工作树）**：env `H3_CHARACTER_SWAP_PREVIEW_MIN_MEGAPIXELS`（出厂 0.0＝不设地板，`1.0`＝把 768 买回来，进 `DESIGN_ENV_RENDER_KNOBS` 白名单）；`character_swap_megapixel_decision(..., preview_request=False)` 新增一级优先序（通用旋钮 ＞ 预览分支 ＞ 年龄锁 ＞ 出厂默认）；contract 多一栏 `preview_request`；`director_cut_studio._compiled_character_swap_window_job(..., preview=)` 由 `_build_smart_render_job` 以 `request_kind=="preview"` 送旗。当时也把 policy 88 → 89，新增 29 项专属测试，全套 1 188 项绿（278.6 s）。完整条文在 `_backup\r66_20261101_preview480_pre_undo\CHANGELOG.md:19-48`，那里曾以 `## [0.3.8-alpha.5] - 2026-11-01` 发布。
- **undo 之后的事实**：导演分级「效果完全失败，请 undo 全部去上一次的代码」之后，今天的工作树找不到那个 env、找不到 `testing\test_round66_preview_bucket.py`、contract 也没有 `preview_request`；`VERSION` 仍是 `0.3.8-alpha.3`。持久结果只有两样：（a）导演亲手把 `character_swap_engine.py:3807-3808` 的 `PREPARE_RESOLUTION_HIGH` / `PREPARE_RESOLUTION_LOW` 都钉成 `"480"`（指令：「請不要再改這一點」）；（b）残留常量 `OUTPUT_UPSCALE_REASON_NOT_PREVIEW = "not_preview_request"`（`character_swap_engine.py:182`，Round 67 的输出增强器后来在用它）。
- **对后世的直接影响（每一轮都要以此为前提）**：两个 prepare bucket 都被钉在 `"480"` ⇒ 768 这个 bucket 已不可达 ⇒ Round 53 那条「用分辨率买年龄准确度」的防线现在只剩 prompt 文字在做事；`0.5 MP` 与 `1.0 MP` 请求都会在 480 prepare。

## 69. Round 67 节（= CHANGELOG **Round 67**，2026-11-01 约 14:17；**源码已修复，同日即被 Round 69 关成默认 off；影片未实机＝0 枪**）

- **当时没登记**：快照 `_backup\r67_20261101_preview_vsr_output\`（引擎 mtime 14:17）里的 CHANGELOG 头仍停在 Round 65。机制条文一直活在产品码 design note `character_swap_engine.py:117-135`。
- **动机**：`PREPARE_RESOLUTION_HIGH="480"` 让 0.5 MP 草稿便宜到能反复试，代价是 576×864 的 take 看着软。RTX VSR 不是第二次 diffusion，而是模板已经在 Picture 1 上信任的那颗 NVFX 硬件增强器，所以在 Relay 发布帧之后、`CreateVideo` mux 之前对 Preview 的**答案**跑一次 ×2，就能让 480 草稿在 1x 下可分级而不多买一代生成。**Final Render 刻意不挂**：会自己发明细节的增强器可能添加参考图里没有的褶皱，Final 必须就 H3 实际产出被分级。
- **落码**：`CHARACTER_SWAP_OUTPUT_UPSCALE_CLASS`（与参考图那颗同 class）、node id `rtx_vsr_output`、title `RTX Video Super Resolution - Preview Output`、`..._DEFAULT_SCALE = 2`、resize mode `scale by multiplier`、附图 fallback 的 quality／strength／encoding 钉值（`:140-177`）；pass 列自证一组 contract 栏（`CHARACTER_SWAP_OUTPUT_UPSCALE_CONTRACT_KEYS`，由 `..._ROW_DEFAULTS` 生成）；reason 三值 `not_preview_request`／`environment_disabled`／`no_image_input_to_upscale`；开关 `character_swap_output_upscale_switch()`（`:3432`）读 `H3_CHARACTER_SWAP_PREVIEW_VSR`，肯定词或裸倍率（`=4`）才开。挂载幂等：优先接 muxer，muxer 不存在而 Save 就在末端则直挂，图里没有可接影像输入就老实报 `no_image_input_to_upscale`。
- **同日反转（并入 Round 69 第 5 项）**：导演分级两支 take 的**背景**长出手动 ComfyUI 同 clip 同 seed 从未出现过的蜂窝格，而增强器是线上唯一能发明它的东西；它的 2x 输出是 576×866，与每张 H3 bucket 帧的 576×864 差两列，拼出来的 Preview 与被分级的那张不是同一张画布 ⇒ 节点改成出厂 off，`H3_CHARACTER_SWAP_PREVIEW_VSR` 变 opt-in；未设／空白／解析不了一律 off，绝不会把增强器偷偷放回一张正在分级身份的 take 上。
- **今天的测试背书**：`testing\test_round69_manual_parity.py::PreviewOutputEnhancerRollbackTests`（class E，12 项：出厂常数、没人命名时就是 off、contract 栏等于出厂默认、开启时重接 muxer 并如实回报、挂两次幂等、Final Render 永不买增强器、env 可否决 preview 请求、缺影像输入的回报、非 muxer 后 Save 的直挂、显式倍率记为 environment、呼叫点接线）。

## 70. Round 69 节（= CHANGELOG **Round 69**，2026-11-01，policy 88 → 89；**源码已修复＋九项各有测试；影片未实机＝0 枪**）

**A. A/B 的标的**：同一支 clip（`a_woman_in_a_pink_dress_and_polka_dots`），手动 ComfyUI 的 `character-swap_00042_`／`character-swap_00043_` ＝ **接受**（576×864、325 帧、一条 job、plan 124/18、seed 904239、LoRA swap 1.5＋turbo 0.8、prepare `['480',0,'silence']`、RTX 节点 id 9 只挂参考图）；Studio 自己编译的 Preview ＝ **拒绝**。代价量化出来的差距：手动那张 `appends nothing`，Studio 同一支 append 了 **4 050 字元**，而每张被拒绝的帧都含一个参考图没画的东西（crown、cat ears、belt、honeycomb）。

**B. 九项改动（只动 Studio 编译产物；用户的 `H3-Character-Swap-Relay-V2-api.json` 一字未改）** —— 每项由 `testing\test_round69_manual_parity.py` 的一个类钉住：

1. **class A — Prompt 去污染＋风格上限**：点名一个被禁止的物件就是把它画上屏幕，所以附录说 `the top of the head` 不说 `the crown`；路线 1 附录可增长的那一半被 `CHARACTER_SWAP_LEAN_STYLING_BUDGET = 1200`（`character_swap_engine.py:702`，vanilla 侧同名上限 `:703`）封顶，超出部分**按证据强度丢弃**，不再只是记录 overflow。
2. **class B — Relay 窗口分段合并**：短于一个 124 帧 Relay 窗口的 Segment 会用自己的 seed 冷启动自己的 H3 请求。粉红外实测 `1.589 s + 11.420 s + 0.559 s` 三段三 seed，只有中间那段落地。现在碎片融合，同一个 job 的所有 Segment 共用一颗 Relay seed。
3. **class C — QC 头部图层否决权**：只重建 head/face 图层、且离 Picture 1 比 `CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR = 0.5`（`smart_render_worker.py:375`）更远的 take，从 advisory 通过改成 **blocking**，换新 seed 重摇。
4. **class D — 多角色错置保护**：SAM3.1 配对分数低于 `SAM31_MIN_MATCH_SCORE = 0.7`（`smart_render_worker.py:403`）时 raise 要人工框，不再用 delta 兜底合成一副不可信的身体；reference framing class **每个 Shot 量一次**，同一 Segment 的每条 pass 讲同一种相机语法。
5. **class E — Preview 输出增强器回滚**：见 §69。
6. **class F — 参考图变不透明**：透明裁切图曾被渲染成软边鬼影；alpha 先压到白底，pass 列记录有压。
7. **class G — Identity Sheet 视图来源**：rear／side 画稿只读有标那个视图的 layout（Round 75 修的是它必须以可解析路径送达引擎，见 §71）。
8. **class H — 画布对齐 H3 网格**：480 bucket 的 2x 是 576×866，与每张 H3 bucket 帧差两列；Preview 组装 snap 到 `PREVIEW_CANVAS_MULTIPLE = 16`（`smart_render_worker.py:3697`）。
9. **class I — `vanilla` 成为出厂默认 route**：`CHARACTER_SWAP_ROUTE_DEFAULT = CHARACTER_SWAP_ROUTE_VANILLA`（`character_swap_engine.py:481-482`）——author template 逐字原样上线，与手动那张图的文字 **byte-for-byte 相同**（author prompt **2 876 字元**，`test_round69_manual_parity.py:397` 钉死），Silent Shot 唯一允许的 append 是 silent listener 契约。

**C. policy 语义**：`SMART_RENDER_POLICY_VERSION` **88 → 89**（`smart_render_worker.py:325`、`director_cut_studio.py:963`；两侧注释逐项列出 (a)–(g) 的语义变化：capping／去点名／分段合并＋单一 relay seed／head-layer blocking／SAM3.1 低分配对要人工框＋每 Shot 统一 framing／画布 snap 16／alpha 压白）。88 之下编出来的 prompt、分段边界、QC 判定、画布全部作废；graph json 照导演要求不动。**归属提醒**：Round 66 的快照也曾 88→89，但那一版被 undo，所以 89 的归属是 Round 69。

**D. 验证（2026-11-02 补登记时重跑）**：`test_round69_manual_parity.py` 自身 78 项（另有从 Round 52 汇入的 48 项 TestCase）；用 `.codex_tmp\r69_run_tests.py` 跑 19 个 Character-Swap 相关 suite ＝ **569 项通过（0 failure／0 error，1 skipped，97.3 s）**，日志 `.codex_tmp\r82_r69subset.log`。该 runner 必须**预先 import** 全部模块，否则 `test_smart_render_qc_advisory` 会把仓库根插进 `sys.path`，之后所有 `loadTestsFromName` 解析到根目录那批**过期副本**（会假报 `Ran 489 tests FAILED` 而不是真实的 568/569 OK）。

**E. 界定**：**源码已修复**＝九项都有测试钉住「源码送出什么」。**影片未实机**＝这九项叠起来之后的 Studio Preview 有没有真的变成跟 `character-swap_00042_` 一样，目前没有任何新片子证明（Round 69／75／81–83 全是 0 枪）。

## 71. Round 75 节（= CHANGELOG **Round 75**，2026-11-02 约 00:50–01:47；**源码已修复；影片未实机＝0 枪**）

- **本轮没有任何 `Round 7x` 标记在产品码里**（四支产品文件 grep `[Rr]ound 7x` ＝ 0 命中）。可引用的证据只有两处：`testing\test_round69_manual_parity.py` docstring item 7／class G（第 35 行附近明写「the bug round 75 found」），以及文件 mtime —— `character_identity_sheet.py` 00:50:57、`smart_render_worker.py` 01:06:45、`character_swap_engine.py` 01:21:27、`director_cut_studio.py` 01:47:13。
- **根因**：`_character_swap_identity_sheet_view_sources`（`director_cut_studio.py:35568`）扫 Media Pool 同目录、按 asset family ＋ 整字 token 找到正确的 rear／side 画稿之后，`chosen` 存的是**裸文件名**。引擎那端 `collect_view_sources` 只保留「它打得开的图」，裸文件名一律死在自己的 `is_file()` ⇒ 每张真实的 rear／side 都被丢掉，**镜像正面的 fallback 回到线上**，整个扫描变成一个还会回报 `matched` 的 no-op。也就是说 manifest 显示「有 rear 视图」，实际送上的是正面镜像。
- **改动**：交给引擎的映射改成 `str(folder / chosen[name])`（同函数 35640-35655 的注释把理由钉在产品码里）；`metrics["identity_sheet_view_sources"]` 仍存文件名，让 Job／manifest 可对账而不把绝对路径扩散到 contract。family 规则（正面图的 asset id，不是整个文件名）与整字 token 规则两者都是 load-bearing：少了 family，第二个角色的 rear 会变成第一个角色的 rear；少了整字，`background_test.png` 会抢下 rear 面板。
- **验证**：`IdentitySheetViewSourceTests::test_a_tagged_layout_finds_this_character_s_own_drawings` 对每个 view 来源断言 `is_absolute()` **与** `is_file()`（第 1161 行失败讯息写著 `round 75: a bare file name fails its own is_file check`），并钉住 `identity_sheet_view_*` 五个 metrics 栏。今日重跑 class G 12 项全过，所在 19-suite 网 569 项绿。

## 72. Rounds 81–83 节（= CHANGELOG **Rounds 81–83**，2026-11-02；**测试基准已修复并分级验证；产品码零改动；影片未实机＝0 枪**）

**A. 缘起**：补登记 §68–§71 之前先让「全套绿」这个信号可信。结果发现两件事同时在污染它：六处测试把**旧值**钉死（产品码对、测试错），以及测试收尾一个**原生崩溃**。这两类都会让一次真实的回归被读成假绿或假红。

**B. 六处测试重新对齐（只改 `testing\`，产品码一字未动）**

| # | 文件 | 钉错的地方 | 修法 |
|---|---|---|---|
| 1 | `test_fourdx_ui.py` | `payload["version"] == 25`，实际 29 | 改用 `from version_info import PROJECT_FORMAT_VERSION` 对常数断言（先例 `test_director_timeline.py:5578`） |
| 2 | `test_project_workspace.py` | `motion_preview.megapixels == 0.2`，实际 0.5 | 对汇入的 `PREVIEW_MEGAPIXELS` 断言，**另加** `== 0.5` 明文钉值＋讯息（防两侧一起漂） |
| 3 | `test_music_video_engine.py:53` | `load_skill_profiles(Path(__file__).parent)` → `FileNotFoundError: skill default/h3-prompt-writing` | 改 `parents[1]`＋注释：真正的 skill pack 在仓库根，`skill_engine.py:121-131` 不会往父目录找 |
| 4 | `test_design_engine.py`（两处） | golden fixture 读 `example\tang_ting_ci_ying_45s_demo\design_plan.json` 与 `example\Dragon_Realm_vs_Immortal_Martial\DESIGN_REQUIREMENT_WORLD_POWER_REVISION.txt`，**这两个 example 目录已不存在** | 提前 `self.skipTest(...)`，名称＋原因都写出来 |
| 5 | `test_design_engine.py:~2069` | `len(calls)==1`，实际 2 —— `unload_lm_studio` 现在先探主机方言（`_is_strata_host`／`_host_kind`，Strata 支援）再 GET 目录 | 改成断言**所有** call 都以 `/api/v1/models` 结尾（没 POST 过 unload）；该 guard 本来就不计 GET |
| 6 | `test_comfy_connection_recovery.py:287/296` | `queue.call_count==1`／`assert_not_called()`，实际 2 —— worker 现在飞完会 POST `/free`（`comfy_submit_worker.py:566`） | 只数 `full_url == "http://remote:8188/prompt"`：首跑必须 1 且要有 `/free`；resumed 那跑必须 0 个 `/prompt` |

**C. 两项环境性故障（登记，不当产品 defect 修）**

- **原生崩溃**：身份 `0xC0000005`，发生在 `testing\test_standard_pipeline_regressions.py` 跑完之后、Qt `processEvents()` 与 ffmpeg `[h264_mf]`／`[hevc_mf]` 拆帐的阶段；fault dump 显示泄漏线程（`audio_separator_dialog.run` 卡在 `socket.create_connection`；`director_cut_studio.py:2640 _read_loop`／`:2691 _write_loop`）。bisect（`.codex_tmp\r81_bisectA..E.log`）：A／B／D（不含该模块）不崩，C 与 E 崩，**E 崩在该模块 :376（test_03）、C 崩在 :306（test_02）** ⇒ 定位到模块而非某一行，崩点由累积线程压力决定。**决定性证据**：`--only test_standard_pipeline_regressions` 单独跑＝15 项 OK／51 s／EXIT=0（`.codex_tmp\r82_iso_stdpipe.log`）；它早于 Round 81 就能重现，而 Round 65 基线是绿的（`logs\r65_full_suite.log`，1 159 OK／269 s）。**实务做法**：要全套 tally 就用 `working\run_testing_suite_watchdog.py --stall 300 --skip test_standard_pipeline_regressions`。
- **机器负载 stall**：本日全套（跳过上面那个模块）跑到第 526 项时，watchdog 的 `faulthandler` 5 分钟计时在 `test_director_timeline.DirectorTimelineDragTests.test_shot_tool_drags_visual_range_and_shot_dialog_is_structured` 引爆（`.codex_tmp\r82_full_nostdpipe.log:537`，EXIT=1）。同一支测试**单独跑 2.047 s OK**（`.codex_tmp\r83_iso_dragtest.log`）。引爆当下机器上同时常驻：ComfyUI（8189）、Studio 本体（06:38 启动）＋ `media_prepare_service`／`blip_service`／`audio_service`，以及 07:50 才被拉起来的 `audio_separator_server`。⇒ 全套 tally 要挑空档跑，或先关掉 Studio 那组服务。

**D. 验证（本日重跑，全离线）**：五个被对齐的模块（`--only test_comfy_connection_recovery,test_design_engine,test_fourdx_ui,test_project_workspace,test_music_video_engine`）＝ **187 项通过（0 failure／0 error，2 skipped）**，`.codex_tmp\r82_fixed_pins.log`；分级 Character-Swap 网（19 suite）＝ **569 项通过（1 skipped，97.3 s）**，`.codex_tmp\r82_r69subset.log`；`test_standard_pipeline_regressions` 隔离 **15 项 OK**（51 s）。执行本身即证明可编译，未另跑 `py_compile`。

**E. 界定与回退**：这三轮**没有产品码改动** ⇒ `SMART_RENDER_POLICY_VERSION` 仍 89、`PROJECT_FORMAT_VERSION` 仍 29、`VERSION` 仍 `0.3.8-alpha.3`、既有 Job／manifest 缓存一律不作废。测试端改动都可回退（只是把断言对齐产品事实，没有放松任何 gate）。**影片未实机**：0 枪，Round 69／75 的成片对账仍欠一枪。

**F. 本节工具与日志**：`.codex_tmp\r81_bisectA..E.log`、`r81_isolate_stale.log`、`r82_iso_stdpipe.log`、`r82_iso_pins.log`、`r82_iso_design.log`、`r82_fixed_pins.log`、`r82_r69subset.log`、`r82_full_nostdpipe.log`、`r83_iso_dragtest.log`；`.codex_tmp\r69_run_tests.py`（19-suite 分级网 runner）。本轮 ComfyUI 端**零请求**。

**G. 等导演的开放问题（本轮未擅自动手）**：出厂默认已是 `vanilla`（Round 69 第 9 项），意味着多角色遮罩、大脸合格框、年龄锁这些**Studio 侧条款**在多角色／大脸／年龄敏感的镜头里**不再送到模型**。要不要为这类镜头自动切到 `route1`／`legacy`（或反过来，只有这些镜头允许手动开 `H3_CHARACTER_SWAP_ROUTE`）？这是一个会影响成片形态的选择，没有导演的话不擅自改。

## 73. Round 86 節（= CHANGELOG **Round 86**，2026-11-02；**原始碼已修復；本輪 0 槍；影片未實機**）

**A. 緣起（導演的問題：「Preview 為什麼重複三次，我覺得第一次已經是最好的效果了」）**：先排除「成片裡真的排了三段」這個讀法 —— `example\a_woman_in_a_pink_dress_and_polka_dots_4` 的 `generated_preview.mp4` 是 **325 影格 / 13.54 s / 576×864**，與乾淨 plate 等長，所以時間軸沒有重複。真正的情況是**同一支渲染被跑了三次**：Studio 的 Preview 路徑編譯出來的是 `maximum_attempts: 1`（`director_cut_studio.py:37871`；完整渲染才是 `:38233` 的 3），但 Round 69 第 3 項的 blocking QC（`head_layer_only=True` 且 `target_reference_similarity=0.387293 < CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR=0.5`，floor 在 `smart_render_worker.py:375`）把上限抬到 3，於是 Preview 花了三顆 seed。選中第三槍是因為 `choose_character_swap_identity_candidate`（`:2373`）取顏色直方圖最接近 P 圖的那一筆，而 0.387 是三筆裡最高的。**三次都是白燒**的結構性原因也在 manifest 裡：wardrobe 上半 `+0.11186` 過線、下半 `-0.044346` 不過線 ⇒ 下半身從頭到尾穿的是 V1 的衣服，換 seed 修不了它。證據案與檔名：job / manifest `project\render_jobs\preview_1265738911004531245_1793578640785883400.*`（policy 89、0.5 MP、單段 13.568 s）。三槍已從 ComfyUI 伺服器自己的 output 資料夾撈回本地並用 ffprobe 校驗：`.codex_tmp\r86_attempts\pass_01_R1_0000{1,2,3}_.mp4`（subfolder `studio_character_swap/segment_001_000000000_000013568`，皆 576×864 / 24 fps / 325 影格）。

**B. class A — 止血：blocking 裁決不再自己加發 seed**（`smart_render_worker.py`）

- 新增常數與讀取器：`CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS = 3`（**留作 clamp**）、`CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_DEFAULT = 1`、`CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_ENV = "H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS"`、`character_swap_blocking_max_attempts()`（第 376–386、416–438 行）。出廠值是 **1 = 完全不抬**，所以「Spec 說一槍就只花一槍」；把環境變數設成 3 就回復 Round 69 的行為；任何值都被夾在 `[1, 3]`，打錯字不會燒掉無限顆 seed。
- `character_swap_identity_attempt_ceiling()`（第 466–510 行）新增**第 4 個參數** `blocking_max_attempts=None`：只有傳 `None` 才去讀環境，這樣測試／呼叫端可以直接表態，不必動程序環境。Job 自己的預算依然是雙向硬上限，答案永遠不低於「产生这次裁決的那一槍」。呼叫點（第 4858–4862 行）**維持三個引數**，也就是走環境預設 ⇒ 現況 Preview 預期 `attempts_used=1`。

**C. class B — 留檔留帳：每一取都留下来並寫進 Manifest**（同檔）

- 常數（第 2407–2420 行）：`CHARACTER_SWAP_KEEP_ATTEMPTS_ENV = "H3_CHARACTER_SWAP_KEEP_ATTEMPTS"`、`CHARACTER_SWAP_ATTEMPT_DIRECTORY = "identity_attempts"`。
- `character_swap_keep_attempts_enabled()`（2423）：預設 **on**；`0/off/false/no/none/disable/disabled` 才回復舊的「選完就刪」，給磁片吃緊的機器用。
- `_character_swap_attempt_filename()`（2432）：快照原名是 `.identity_audit_attempt_<n>_<ComfyUI 輸出名>`，落地時丟掉前綴、保留伺服器那端的檔名 ⇒ `attempt_NN__pass_01_R1_0000K_.mp4`，尾巴跟伺服器 output 資料夾裡那支檔案對得上，可以直接交叉核對或重抓而不必重渲染。
- `character_swap_identity_attempt_row()`（2451）：每一取列出一列可比較證據 —— `attempt`／`selected`／`quality_risk_score`／`target_reference_similarity`／`wardrobe_shift`／`wardrobe_shift_late`／`silent_articulation_excess`／`target_likeness_score`／`blocking`／`head_layer_only`／`reason`／`prompt_id`。Round 52 以來 Manifest 只留「被選中的那一筆」，所以才會被看成「只量了一次」。
- `persist_character_swap_identity_attempts()`（2486）：把每個快照 `shutil.copy2` 到 `<download_dir>\identity_attempts\`，回傳每取一列（`take_path` 為落地檔，關掉保留或复制失敗時是空字串）。**複製失敗只記 `take_copy_error`，绝不拋錯** —— QC 層不得把已經付過錢的渲染搞失敗。
- 接線：attempt 迴圈新增 `identity_attempt_table`（4773）；選出 winner 之後呼叫 persist（4890–4894）；progress 訊息會報「N take(s) kept in identity_attempts/」（4895–4908）；emit 的 `identity_candidate_scores` 改用這張表（4911）；`queue_segment` 回傳新增 `identity_attempt_table`（5024）並已有 `attempts_used`（5015）；Manifest 的 `character_swap_identity_audits.append({...})` 新增 `attempts_used` 與 `attempt_table`（6242–6249）。
- 實際落盤位置例：`cache\generated_outputs\preview\<seed>\<segment>\character_swap_pass_01_R1\identity_attempts\attempt_01__pass_01_R1_00001_.mp4`。

**D. 環境變數速查**

| 變數 | 出廠 | 效果 |
|---|---|---|
| `H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS` | 未設 ⇒ 1 | blocking 裁決最多抬到幾槍；`3` 回復 Round 69；一律夾在 `[1,3]` |
| `H3_CHARACTER_SWAP_KEEP_ATTEMPTS` | 未設 ⇒ on | off 係數列仍寫進 Manifest，只是 `take_path=""` 且不留檔 |

**E. 驗證（本輪全離線）**：`testing\test_round69_manual_parity.py` 把 Round 69 那顆 pin 從 `(4, 1, True, 3)` 重新對齊成 `(4, 1, True, 1)`（附上理由註解），並新增 class `AttemptEconomyAndEvidenceTests`（10 項：預設不抬升、env=3 回復、env 雜值與夾限、显式參數不讀 env、Job 預算仍是硬上限、保留開關的讀值、檔名保留伺服器尾巴、列欄位完整、落地與 `take_copy_error`、keep=off 仍有列）。該模組 **88 項通過**（原 78）。分級防護網（14 個 import `smart_render_worker` 的 suite）＝ **392 項通過／1 skipped／51 s**，日誌 `.codex_tmp\r86_net.txt`。`py_compile` 過 `smart_render_worker.py`／`director_cut_studio.py`／`character_swap_engine.py`。`test_director_timeline` 在機器載重下跑超過 15 分鐘未收（輸出 `.codex_tmp\r86_timeline.txt`），屬 §72-C 已登記的環境性慢測試，以分級網為準。**本輪 ComfyUI 端只有讀取請求**（`/view` 抓三槍、`/history` 對帳，不載模型）；**沒有新渲染**。**影片未實機**：A 省的鐘點與 B 的留檔有沒有真的變成這樣，目前沒有任何新片子證明。

**F. 界定**：`SMART_RENDER_POLICY_VERSION` 仍 **89**、`PROJECT_FORMAT_VERSION` 仍 **29**、`VERSION` 仍 `0.3.8-alpha.3`（導演指定不動）、`character_swap_engine.py:3807-3808` 的 `PREPARE_RESOLUTION_HIGH/LOW = "480"` 不動、導演的 `H3-Character-Swap-Relay-V2-api.json` 一字未改。A/B 只改「一節 Segment 允許花幾顆 seed」與「rejected 的 take 要不要留下來」，**prompt 文字、identity sheet 送法、QC floor 本身都沒有改** ⇒ 既有 Job／manifest 快取一律不作廢，也都不會因為本輪而需要重跑。

**G. 還欠的根修與開放問題（未獲批准，未擅自動手）**

1. **D — 外觀參考該換成全身 identity sheet**：本輪送進 graph 的參考是 310×703 的 PNG，專案內沒有 identity sheet ⇒ 下半身不會跟著換，这正是 A 那三槍白燒的同一個根因。方向是 front／rear／side 全身稿（参考 `800×1216 identitysheet08_fullfig` 單人）。
2. **C — 同因重複提前停**：若第二槍的裁決與第一槍同因（同一個 floor 不過線），直接停而不燒第三槍。本輪的預設 1 已经把最糟情況擋掉，這一項是更細的優化。
3. **§72-G 仍未決**：出廠 `route=vanilla` 之下，多角色遮罩／大臉合格框／年齡鎖這些 Studio 側條款不會送到模型，要不要為這類鏡頭自動切 `route1`／`legacy`。

**H. 本輪 scratch**：`.codex_tmp\r86_attempts\`（三槍實檔）、`r86_ceiling.txt`、`r86_a_num.txt`、`r86_loop.txt`、`r86_manifest.txt`、`r86_final.txt`、`r86_test69.txt`、`r86_net.txt`、`r86_timeline.txt`。ffprobe／ffmpeg 在 `ai_libraries_common\engine_ffmpeg\bin\`。

## 74. Round 91 節（= CHANGELOG **Round 91**，2026-11-02；**原始碼已修復；本輪 0 槍；影片未實機**）

**A. 緣起（為什麼非改不可）**：§73-G 第 1 項點名「送進 graph 的參考只有 310×703 的立繪 ⇒ 下半身永遠不會換」。本輪查證它**為什麼**沒跑 identity sheet：`example\a_woman_in_a_pink_dress_and_polka_dots` 的 P1 本来就是去背卡通立繪（`D:\minimax h3\minimax h3 reference r2v\.director_cache\image_137_ef2009c5827da7cb_nobg.png`，RGBA 310×703，`is_alpha_cutout=True`），但它的 **BLIP caption 沒有任何 cartoon／illustration 字** ⇒ `_looks_like_illustrated_cast()`（`director_cut_studio.py:532`）答 No ⇒ `preserve_full_design=False` ⇒ identity sheet 分支從頭到尾沒被選到。換言之 §73 那三槍白燒不是 QC 的錯，是**參考資格判定過度依賴 caption 文字**。

**B. 本輪的核心決定：把「媒介」與「framing」拆成兩條永不再混的 predicate**（導演先前明確要求「P 圖是什麼媒介就保留什麼媒介」，這裡是同一條邊界的另一端）

- **媒介問題**（是不是卡通？真人化開關 `source_cast_live_action_adaptation` 與 close-up plate gate 要的答案）⇒ 永遠只讀 caption，用 `_looks_like_illustrated_cast`，本輪一字未改。
- **framing 問題**（這張是不是「必須保留整套設計」的 cast 設計圖？identity sheet 分支要的答案）⇒ 新 predicate `_character_swap_design_reference_evidence()`，caption 命中也算，**沒命中時接受 alpha 摳圖證據**。
- 这样 BLIP 把卡通描述成照片也不會再把整套設計裁丟，而照片不會因為檔案格式意外被改標成卡通。

**C. class — 源碼改動逐項定位**

| 檔案 | 行 | 內容 |
|---|---|---|
| `character_identity_sheet.py` | 1101 | `ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE = 0.02` |
| `character_identity_sheet.py` | 1111-1165 | `is_alpha_cutout()`：需要真 alpha 帶（RGBA／PA／P／LA）＋透明像素佔比 ≥ 2% |
| `director_cut_studio.py` | 573-577 | `H3_ILLUSTRATED_CAST_IMAGE_EVIDENCE` 註解、`_ILLUSTRATED_CAST_CUTOUT_CACHE: dict[str, tuple[int, bool]]`、`_ILLUSTRATED_CAST_CUTOUT_CACHE_MAX = 512` |
| `director_cut_studio.py` | 580-598 | `_illustrated_cast_image_evidence_enabled(environ=None)`（`0/off/false/no/none/disable/disabled` 關掉）與 module 級 `ILLUSTRATED_CAST_IMAGE_EVIDENCE` |
| `director_cut_studio.py` | 600-656 | `_character_swap_design_reference_evidence(asset, picture_path, *, image_evidence=None)`：caption 短路 → 探測 → (path, mtime) 快取；`image_evidence=` 讓測試不需真圖；探測例外一律 `False`（「無法探測＝沒有證據」） |
| `director_cut_studio.py` | 1080-1091 | policy 90 註解（cast 摳圖透明比實測 46–68%，照片 0.0%）＋ `SMART_RENDER_POLICY_VERSION = 90` |
| `director_cut_studio.py` | 37902-37915 | 編譯 pass：`target_is_illustrated`（媒介）與 `target_is_design_artwork`（framing）分开算，註解寫死兩條問題不得互用 |
| `smart_render_worker.py` | 324-330 | policy 90 註解：worker 不讀新證據，決定发生在 Job 編譯期；framing 翻轉的 Shot 其 prompt／take 快取作廢 |

**D. 環境變數**：`H3_ILLUSTRATED_CAST_IMAGE_EVIDENCE` — 出廠未設＝**on**；設 `0`／`off` 回復「只讀 caption」的 Round 90 之前行為。

**E. 驗證**：新增 `testing\test_round91_illustrated_evidence.py`，**26 項通過**（2026-11-02 本輪再次回跑：`Ran 26 tests in 0.229s OK`）。本輪 **0 槍**，ComfyUI 端零請求 ⇒ **影片未實機**。

**F. 界定**：prompt 文字本身沒有改字，只有「哪些 Shot 會走 identity sheet」的資格變寬 ⇒ policy 89 的 manifest 對那些 framing 翻轉的 Shot 才算 stale；`VERSION` 仍 `0.3.8-alpha.3`、`PROJECT_FORMAT_VERSION` 仍 29、`character_swap_engine.py:3807-3808` 的 480 不動、導演 JSON 未動。

## 75. Round 92 節（= CHANGELOG **Round 92**，2026-11-02；**原始碼已修復；本輪 1 槍；影片已渲染、尚未由導演分級**）

**A. 緣起**：兩件事。其一是 §74 那條 predicate 的漏洞 —— 只要透明像素 ≥2% 就算摳圖，所以「整張全透明」或「只剩幾個邊緣像素」的 PNG 也会被當成 cast 設計圖證據，identity sheet 的 head／outfit 框錨到空畫布，送進 graph 等於沒給參考。其二是導演批准 D 方案實測（「现在执行D，看看效果」）⇒ **本輪允許 1 槍，已用完，ComfyUI 已 `/free`，Tray 已把 Qwen 載回**。

**B. class — 源碼改動（本輪產品碼只有這一處）**：`character_identity_sheet.py:1108` 新增 `ALPHA_CUTOUT_MIN_OPAQUE_SHARE = 0.02`；`:1154` 新增 `_opaque_share()`（讀 256-bin alpha 直方圖，不逐像素掃）；`:1161-1165` 讓 `is_alpha_cutout()` 採**雙重下限**（透明佔比 ≥ `ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE` **且** 有畫到的不透明佔比 ≥ `ALPHA_CUTOUT_MIN_OPAQUE_SHARE`）。真 cast 摳圖（46–68% 透明、內涵充足）照樣通過。

**C. 驗證（離線）**：`testing\test_round91_illustrated_evidence.py` 26 項 OK；identity sheet／swap 相關既有 suite **211 項通過**（policy pin 90）；`py_compile` 過 `character_identity_sheet.py`／`director_cut_studio.py`／`smart_render_worker.py`。

**D. headless 編 job（不開 GUI 重現这一槍的做法，下次直接用）**：`.codex_tmp\r92_headless_job.py` — `QApplication` offscreen → `load_project_path` → `quality_profile="motion_preview"` → `_reconcile_speech_timing_before_run()` → `_read_settings_ui()` → `_build_smart_render_job(request_kind="preview", megapixels=0.5, seed=…, enable_rtx_vsr=False)`，再把 job json 交給 `staged_model_driver.py run`（內建 unload-qwen → wait-comfy → worker → `/free` → report）。**注意**：headless 編出的 job json 在暫存目錄，專案 `project\render_jobs\` 只留 manifest（該專案目前 `*.job.json` 計 0、`*.manifest.json` 計 2），要重現必須重跑腳本。

**E. 實機那一槍的全部事實（讀自 manifest）**：案 `example\a_woman_in_a_pink_dress_and_polka_dots_5`，seed **592000107**、policy **90**、0.5 MP、13.57 s 單段，manifest `project\render_jobs\preview_592000107_1793589625959997100.manifest.json`；輸出 `cache\generated_outputs\preview\592000107\segment_001_000000000_000013568\character_swap_pass_01_R1\01_save.mp4`（576×864／24 fps／325 幀／11,787,718 B）。

- **D 生效**：`reference_framing=illustrated_identity_sheet`、`identity_sheet_reason=composed`、`identity_sheet_preset_requested=0 → identity_sheet_preset_forced=8`、`identity_sheet_outfit_view=full`、`identity_sheet_head_coverage=0.5251`、`identity_sheet_source_head_coverage=0.099588`（V1）、`identity_sheet_reference_head_coverage=0.149153`（原 P1）、`identity_sheet_source_reference_megapixels=0.21793`、`identity_sheet_source_head_crop_megapixels=0.0331`、`identity_sheet_medium_silent_rows=1`、`identity_sheet_closeup_gate_rows=0`、`identity_sheet_framing_threshold=0.0`、`character_swap_route=vanilla`、prompt 3609 字（author 2895）。sheet 本體：`cache\identity_sheets\image_137_ef2009c5827da7cb_nobg_identitysheet08_fullfig_a0066_v8.png`（head rect `[13,13,787,675]` coverage 0.5251、outfit rect `[13,683,787,1203]` coverage 0.131；sidecar 同名 `.identity_sheet.json`，notes 含 `overlay suppression: source artwork is a transparent cut-out`）。
- **§73-A 的止血被這一槍證實生效**：`attempts_used=1`、`selected_attempt=1`，`attempt_table` 有完整一列且 `take_path` 落在 `…\character_swap_pass_01_R1\identity_attempts\attempt_01__01_save.mp4` ⇒ Round 86 的「編譯說一槍就只花一槍」與「每取留檔留帳」在 policy 90 實機成立。
- **QC 判决未變**：`head_layer_only=true`、`blocking=true`、`target_reference_similarity=0.277282` < floor 0.5；`wardrobe_audit.binding_region="lower"`、`shift=-0.04061`（late `-0.045396`）、floor 0.12／relative 0.04131 ⇒ **下半身仍是 V1 的衣服**；`passed=false`、`action=retry_fresh_seed`、`character_swap_identity_advisory_only=false`、`character_swap_identity_failed=true`（`smart_render_worker.py:4810` 的「blocking 不得被 lean route 赦免」這條路徑有走到）。

**F. 對照基準（同規格才放同一張表）**：手動金標 `example\a_woman_in_a_pink_dress_and_polka_dots\character-swap_00043_.mp4`（576×864／24／325 幀／13.541667 s）；政策 89 基線是同專案 seed 582453245502616783（`preview_582453245502616783_1793583819109516200.manifest.json`，`reference_framing=original`、similarity 0.321361、shift +0.048341、attempts 1），備份影片 `.codex_tmp\r92_baseline\policy89_motion_preview.mp4`。

**G. 量化＋目視（工具只有 PIL 12.3.0／numpy 2.4.6，無 cv2／mediapipe／insightface ⇒ 這些是色彩掩膜代理指標，不是 face detector）**

| 指標 | 手動金標 | policy 89 | policy 90（D） |
|---|---|---|---|
| 粉裙面積／金標 | 1.00 | 0.77–1.26 | 0.78–1.16（後半 0.90–0.97）⇒ 身體尺度無系統漂移 |
| 頭部區 skin（loose，5 點均值） | 0.2176 | 0.2445 | **0.2736**（對 V1 = 3.51×；金標 2.79×、p89 3.13×）⇒ **臉比手動大約 26%** |
| 頭部區 skin（strict，14 幀均值） | 0.1607 | 0.1814 | 0.2080 |
| 頭部區 white（P1 白色頭箍） | 0.1134 | 0.0603 | **0.0388** ⇒ 頭箍逐輪丢失，D 最差（0/2/5/8/9/10/12/13 s 消失） |
| 1 fps 幀間差（穩定度） | 67.28 | 60.73 | 64.03 ⇒ 無闪烁回归 |

目視 14 秒 1 fps contact sheet：D 無 sheet 面板洩入、無蜂窩背景、無老人化、卡通媒介保留；**8–13 s 的臉比較像 P1**（圓頰、眉／瀏海筆觸）＝ D 的實際增益。P1 短 bob 在兩邊都變長髮 ⇒ **髮型漂移屬 H3／relay 固有，不是 Studio 缺陷**。圖與產生器留在 `.codex_tmp\r92_montage\compare_4col.png`（960×1834，V1｜金標｜p89｜p90）、`head_crops_4col.png`、`contact_new.png`／`contact_man.png`／`contact_old.png`、`reference_p1_and_sheet.png`；腳本 `r92_montage.py`、`r92_facecrop.py`、`r92_contact.py`、`r92_pinkmetrics.py`、`r92_headmetrics.py`、`r92_headmetrics_v2.py`、`r92_flicker.py`、`r92_manifest2.py`、`r92_sheetpath.py`；抽幀在 `r92_scan\`、`r92_frames\`。

**H. 尚未分級／尚未獲准動手的項目前清單**

1. **等導演分級 D**：身份更像 P1，但臉比手動大 ~26%、P1 白色頭箍被稀釋、下半身仍未換。备选方向（**只提不實作**）：把 sheet 頭面板 coverage 壓到接近 V1 的 0.0996，或給 `forced preset 8` 一個 coverage 上限（例如 ≤0.30）。
2. **QC 代理指標與目視相反**：p90 的 `target_reference_similarity=0.277` 低於 p89 的 0.321，但 p90 目視更像 P1 ⇒ 這個數量的是顏色直方圖，不是身分；能不能換成「頭髮／膚色／服裝三区加權」或乾脆把它降為參考值，要導演決定。
3. **observability 缺口**：`reference_design_evidence` 與 `reference_alpha_flattened` 沒有進序列化 pass row（本槍 manifest 全文查證 `rg` 零命中），所以「framing 是被 caption 還是被 alpha 決定」無法從 manifest 回溯。
4. **§73-G 第 2、3 項仍未決**（同因重複提前停；`route=vanilla` 下多角色遮罩／大臉合格框／年齡鎖要不要自動切 route1／legacy）。
5. **preset 9 的 rear／side 素材仍缺**（§71 identity sheet 三視圖那條路）。

**I. 界定**：`SMART_RENDER_POLICY_VERSION` 維持 **90**、`PROJECT_FORMAT_VERSION` 仍 **29**、`VERSION` 仍 `0.3.8-alpha.3`、`character_swap_engine.py:3807-3808` 的 `PREPARE_RESOLUTION_HIGH/LOW = "480"` 不動、導演的 `H3-Character-Swap-Relay-V2-api.json` 一字未改。本輪只是**收緊**證據條件（空畫布不再算證據），沒有放寬任何 framing 判定 ⇒ 既有 Job／manifest 不作廢。

**J. 本輪 scratch**：`.codex_tmp\r92_headless_job.py`、`r92_reprobe.py`、`r92_ls.py`、`r92_manifest.py`、`r92_manifest2.py`、`r92_paths.py`、`r92_sheetpath.py`、`r92_enc.py`、`r92_baseline\`、`r92_frames\`、`r92_scan\`、`r92_montage\` 與上列 `r92_*.py`。
