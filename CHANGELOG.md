# Changelog

Every user-visible correction receives an application version and a dated entry in this file. Application versions follow Semantic Versioning pre-release notation. The `.h3director.json` project-format version is maintained separately and changes only when the saved schema changes.

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
