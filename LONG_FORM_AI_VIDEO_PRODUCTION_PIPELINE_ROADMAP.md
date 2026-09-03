# Long-Form AI Video Production Pipeline

> MiniMax H3 Director Cut Studio 长片生产架构预告  
> 当前基础版本：`v0.3.1-alpha.4`  
> 目标验收版本：`v0.3.1-alpha.5`

MiniMax H3 Director Cut Studio 正在从“单次生成一段短视频”，升级为真正面向长片制作的 **Long-Form AI Video Production Pipeline**。

这次升级的重点并不是单纯突破 MiniMax H3 单次约 15 秒的生成长度，而是建立一套可以持续扩展、局部修改、失败恢复、控制成本，并最终支持长篇项目的 AI 影片生产架构。

Studio 的最终目标是让使用者在画面上看到一条完整 Timeline，而所有复杂工作都在后台自动完成：

```text
完整故事 Timeline
        ↓
按 Shot 与原生生成窗口自动拆分
        ↓
为每段选择局部 P/V/A 参考素材
        ↓
生成、缓存及验证独立 Shot Takes
        ↓
使用前段最后 24 帧维持动作连续性
        ↓
只重算被修改的 Shot
        ↓
自动组装 Preview / Final Master
```

用户不需要手动把 120 秒影片切成八个 15 秒 Project，也不需要为了修改一秒画面而重新生成整段影片。

---

## 为什么需要这套 Pipeline

目前的 AI 视频生成通常面对以下问题：

- MiniMax H3 单次生成长度有限。
- 修改一秒画面，可能需要重新生成完整 15 秒。
- 长视频容易出现人物、服装、道具和场景变化。
- Segment 边界可能重复上一段动作或发生画面碰撞。
- 参考图片、声音和视频容易在不同 Segment 中发生 Mapping 错误。
- 连续生成会消耗大量 VRAM、RAM、储存空间和处理时间。
- 项目越长，失败后从头开始的成本越高。
- 生成结果如果没有 Shot 级结构，后期几乎无法精确修改。

Long-Form Pipeline 将把这些问题收进 Studio 内部处理。

---

## 核心设计目标

### 1. 一个项目，一个固定 Workspace

一部影片只拥有一个主工作目录。

```text
Project_Name/
├─ generated_preview.mp4
├─ generated_output.mp4
├─ project/
├─ design/revisions/
├─ media/
├─ shots/
├─ renders/
├─ proxies/
├─ cache/
└─ logs/
```

后续执行 Design、Preview、Accept、局部重算及 Final，都不会再建立大量散乱的顶层项目文件夹。

旧 `.h3director.json` Project 继续保持兼容，不会被破坏性覆盖。

### 2. 从 45 秒直接扩展到 120 秒

第一阶段长片目标：

- 载入已经批准的 45 秒影片。
- 把 Timeline 延长至精确 120 秒。
- 原有 45 秒不重新生成。
- 只处理新增的 75 秒。
- 最终 Program Monitor 仍然播放一条完整的 120 秒影片。

使用者看到的是完整成片，后台才处理 Shot、Segment、Take 和 Master Assembly。

### 3. Shot-Local Rendering

生成单位将逐步从固定 15 秒改为以 Shot 为主要单位。

例如只修改：

```text
SHOT 12 · 47.50–53.00s
```

Studio 应该只把该 Shot 及必要的边界连续性范围标记为需要重算，而不是重新生成：

```text
45.00–60.00s
```

这将明显减少：

- ComfyUI 运行时间
- GPU 占用时间
- VRAM／RAM 压力
- 重复生成费用
- 不必要的画面变化

### 4. 24 帧边界连续性

跨越原生生成窗口时，后段可以使用前段最后 24 帧作为无声动作上下文。

这段上下文只负责：

- 身体姿势
- 动作方向
- 摄影机运动
- 人物相对位置
- 服装及道具状态
- 场景空间连续性

它不能要求 H3 重播上一段动作，也不能覆盖当前 Segment 真正使用的 Video Reference。

每段提示词必须明确区分：

```text
Incoming continuity state
New action that must begin now
Outgoing continuity state
```

### 5. Virtual Media Pool 与动态实体装载

整个项目可以拥有：

```text
P1–P100+
V1–V20+
A1–A20+
```

但每个实际 H3 Segment 只动态装入自己需要的：

```text
最多 9 Picture
最多 3 Video
最多 3 Audio
```

Media Pool 的永久编号不会因为局部生成而改变。

例如永久素材 `P17` 在某个 Segment 中可以临时装入第一个实体 Loader，但 Project、Timeline 和 Prompt 解码仍然知道它是 `P17`，不会误认为永久 `P1`。

### 6. 可恢复的 Shot Takes

每个 Shot 可以拥有独立 Take：

```text
SHOT 08/
├─ T0001_motion_preview.mp4
├─ T0002_motion_preview.mp4
├─ T0003_approved_final.mp4
└─ approved.mp4
```

每个 Take 记录：

- Seed
- Quality Profile
- Prompt fingerprint
- Reference mapping
- 开始／结束时间
- 输入媒体状态
- 是否已批准
- 是否因为编辑而失效

这让使用者可以保留满意的 Shot，只重做不满意的部分。

### 7. 三档成本控制

#### Storyboard

- 不运行 H3。
- 立即查看故事结构、素材、Shot、对白和时间安排。
- 用于最低成本的早期判断。

#### Motion Preview 0.2MP

- 使用低分辨率快速测试动作。
- 不启用最终 Upscaling。
- 用于确认镜头运动、表演及连续性。

#### Approved Final 1.0MP

- 复用已批准 Preview 的 Seed。
- 只处理已经通过的 Shot。
- 用于最终 Master。

目标是尽可能先用廉价 Preview 发现问题，而不是在 Final 阶段浪费 GPU 时间。

### 8. Program Monitor 统一长片视图

Program Monitor 始终显示完整影片，而不是要求用户逐个打开 Segment。

未来视图可扩展为：

- Timeline Source
- Generated Output
- Depth
- Pose
- Motion Reference
- Segment Comparison
- Previous Take / Current Take

生成过程中继续显示：

- 已处理 Shot／总 Shot
- 剩余 Shot
- 已完成百分比
- 剩余百分比
- 本次处理时间
- 累计处理时间
- 当前 Segment／Shot
- Preview／Final 状态

---

## 重要的储存空间问题

Long-Form Pipeline 当前必须保留更多内部资料，包括：

- Design Revision
- Z-Image Reference
- BLIP 分析结果
- Shot Takes
- Segment 输出
- Preview Master
- Final Master
- Proxy
- Render Manifest
- Project Snapshot
- Audio／TTS 文件
- Continuity Context

在目前的 Alpha 基础架构中，我们已经观察到：

```text
旧项目：约一百多 MB
升级后的同类项目：可能膨胀至约 500 MB
```

这不一定代表所有内容都是真正独立占用的空间。

部分文件可能是：

- Hard Link
- 可重建的缓存
- 重复的 Preview
- 已失效 Take
- 已被 Final 取代的中间 Master
- 旧 Design Revision
- 不再被任何 Shot 引用的素材
- Monitor Proxy
- Segment Assembly 临时文件

但从使用者角度看，项目目录仍然会显得明显变大。

### 当前决定

在 `v0.3.1-alpha.2` 至 `v0.3.1-alpha.4` 期间，我们优先保证：

- 不丢失项目
- 不破坏 Approved Take
- 可以局部修改
- 可以恢复生成
- Segment Mapping 正确
- 长片不会因为缓存清理而无法继续编辑

因此不会过早删除仍可能影响恢复能力的内部文件。

### 储存优化安排

项目体积优化将作为 `v0.3.1-alpha.5` 正式验收前的重点任务。

计划包括：

- Content-addressed media storage
- 文件 Hash 去重
- Hard-link 使用统计
- Preview／Final Master 单一化
- 自动识别失效 Take
- 可重建缓存清理
- Proxy 清理
- 未引用素材检测
- Design Revision 保留策略
- 每项目储存预算
- Cleanup Preview
- Safe Cleanup
- Archive Project
- Project Size Report

清理前必须向用户显示：

```text
当前项目大小
真正独立占用空间
Hard Link 共享空间
可安全清理空间
清理后预计大小
会保留的 Approved Takes
无法恢复的内容
```

任何清理都不能静默删除 Approved Take 或仍被 Timeline 使用的素材。

---

## 版本路线图

### v0.3.1-alpha.2 — Long Timeline Foundation

**状态：已于 2026-08-30 完成基础实现及自动化验收。**

- 45 秒项目扩展至 120 秒
- 保留已批准的前段
- 只生成新增范围
- Shot-local render scheduling
- 完整 Program Monitor Timeline
- 长片进度、时间和状态显示
- 中断后继续处理

### v0.3.1-alpha.3 — Continuity & Dependency Graph

**状态：已完成相邻 Shot Dependency Graph 与 Smart Cut 可检查计划；全项目依赖可视化继续验收。**

- Shot dependency graph
- 24 帧上下文管理
- Incoming／Outgoing State 验证
- Segment 边界碰撞检查
- 防止重复上一段动作
- 局部修改传播范围计算
- Reference Mapping 可视化

### v0.3.1-alpha.4 — Long Production Reliability

**状态：已完成并合并进入 v0.3.2 正式可靠性基线。**

- [x] Full Range／Incremental production strategy
- [x] 30 秒默认批准 Batch 与安全对白边界
- [x] 新增范围 Preview、累计 Final Master 与 Approved Segment 复用
- [x] 批次阶段、批准点、Preview seed 与 checkpoint 恢复
- [x] `long-form-h3-director` Default-bound Special Skill
- [x] Project-scoped 多批次 Job／Manifest；不同 Project／Studio instance 不发生文件名碰撞
- [x] Crash recovery（Worker checkpoint 不依赖 UI 内存）
- [x] OOM 分类、释放内存、三次有界重试及失败原因持久化
- [x] Resume from last completed reusable Segment／Shot
- [x] Shot／Segment Take approval workflow
- [x] Preview／Final selective assembly
- [x] 90 分钟、900 Shots 元数据架构压力测试（不调用 H3）
- [ ] 集中式多项目并发调度器（不属于 v0.3.2；单一 Studio instance 仍串行）
- [ ] 完整 Scene／Sequence 编辑 UI（Design/Special Skill 已有语义结构，UI 延后）

### v0.3.1-alpha.5 — Storage Optimization & Acceptance

**状态：已完成并合并进入 v0.3.2。**

- [x] 项目文件去重与 physical/logical byte 统计
- [x] 缓存生命周期及中断恢复缓存保护
- [x] 仅 Hash 验证后清理失效／重复 Take
- [x] 单一 Preview／Final Master
- [x] Storage Report
- [x] Safe Cleanup dry-run／确认／保护合约
- [x] Portable Archive Project + SHA-256 manifest
- [x] 跨电脑 workflow／media／Take／Master 重定位验证
- [x] 十一项完整 Long-Form Standard Pipeline Release Gate
- [x] 120 秒确定性选择性拼接／局部替换／Archive 验收

---

## v0.3.2 已通过的不可妥协验收条件

- [x] 已批准的旧 Shot 不会被无原因重新生成
- [x] 修改一个 Shot 只重算必要范围
- [x] 所有 P/V/A Mapping 与实体 Loader 完全一致
- [x] 15 秒边界没有动作重播、碰撞或瞬移
- [x] 24 帧上下文不会覆盖当前 Segment 的参考视频
- [x] Dialogue／Voice-over／Lyrics 保持可编辑
- [x] Preview 和 Final 使用正确 Seed 策略
- [x] OOM 或中断后可以继续
- [x] Program Monitor 可以播放完整长片／验证后 Proxy
- [x] Open Project 可以恢复 Master、Timeline 和 Take 状态
- [x] 跨电脑移动后不会引用旧绝对路径
- [x] Cleanup 不会删除 Approved Take 或中断恢复缓存
- [x] 项目体积有清晰报告及安全清理机制
- [x] 120 秒确定性端到端技术 fixture 通过
- [x] 十一项 Standard Pipeline Release Gate 全部通过

---

## v0.4.0 — Story-Aware Auto Cut（已排期，v0.3.1 不继续扩张）

`v0.3.1-alpha.3` 保留现有的 0.5 秒 Smart Cut 安全基础、对白保护、依赖提示和非破坏式 Review。完整 Auto Cut 属于大型故事剪辑策划，延后到 `v0.4.0` 集中升级，避免在 Long-Form Pipeline 验收期间同时改变剪辑决策核心。

v0.4.0 计划包括：

- 明确区分 Opening Hook、关键人物首次出现、Clue、因果转折、Reveal／Reversal、Final Hook、重复说明、装饰性环境镜头、Optional Flourish 与重复人物反应。
- 建立可检查的 Shot Importance 分解：故事核心、对白、线索、连续性、独特画面、用户锁定、重复内容、装饰动作和可替代程度。
- 把逐字 Dialogue／Voice-over、Speaker、人物首次出现、素材视觉语义和跨 Shot 信息相似度纳入分析。
- 建立跨全片而非只限相邻 Shot 的重复信息／可替代关系矩阵。
- 先压缩 Optional Flourish 与装饰时间，再考虑合并重复反应或删除第二次说明；任何自动删除都必须经过 Review／Apply。
- 为每项 KEEP／TRIM／MERGE／REMOVE 显示完整加减分、依赖和风险证据，并建立专属 Auto Cut Release Gate。

### Universal Scene Keyframe Chain

把 `drone-fly-on-city` 已验证的场景关键帧隔离机制升级成不依赖 Special Skill 的通用 `Scene Keyframe Chain` 引擎。引擎必须先识别每张 Picture 的职责，再决定它是否可以跨 Shot／Segment 持续、是否需要隔离，以及是否需要自动建立收尾帧：

- **人物身份图**：可以跨多个 Segment 持续加载，用于固定脸、年龄、肤色、发型、服装、身材比例、鞋子和配饰归属；不得被误当成场景切换点。
- **场景关键帧**：必须按时间隔离。后一场景不得提前进入前一场景的原生 H3 Job，避免未来 Picture 改变较早画面的建筑、构图、照明、天气或色调。
- **动作状态图**：只在对应 Shot 或动作时间窗使用，不得扩散到之前或之后的 Shot，也不得重新定义人物身份。
- **路线／控制图**：永远只作 Design 分析；不得进入 Timeline、ComfyUI 上传、实体 Picture Loader 或最终 H3 Prompt。
- **自动收尾图**：每条场景链只生成一次，继承最后一个用户场景的环境与 Outgoing State，由 Virtual Media Pool 分配下一个真实空置 Picture ID。

实现边界：

- Default-only、Default＋Special 和 standalone Special 三种模式采用同一套职责分类，不再由某一个 Skill 私有处理。
- 用户可以在 Inspector 覆盖自动分类；手动修改后不得再次被 Qwen 或自动分析覆盖。
- 相邻场景 Job 只允许传递上一段最后 24 个无声视频帧作为运动上下文，不得传递旧音频、未来 Picture 或 analysis-only 素材。
- Storyboard、Auto Cut、Shot 移动、删除、增减时长和局部重算后，场景链范围、自动收尾图归属及 Segment Mapping 必须同步重算。
- 未建立多场景链的旧 Project 保持原有行为；人物身份图和产品母版不得因为升级而被错误切成短时间参考。

验收标准：

- [ ] 不选择任何 Special Skill 时，P1 人物身份图仍可跨 Segment 稳定使用。
- [ ] 不选择任何 Special Skill 时，P1 场景、P3 新场景和自动 P4 收尾不会在同一个错误时间窗互相污染。
- [ ] P1–P5 已占用时，自动收尾图稳定分配为 P6，不覆盖现有素材。
- [ ] 动作状态图只进入拥有它的 Shot；路线／控制图在最终 H3 Workflow 中为零 Loader、零上传、零 Prompt 引用。
- [ ] Storyboard／Auto Cut 调整后，每个 Scene Keyframe 的 ownership、时间范围、24 帧衔接和局部重算范围保持一致。
- [ ] 新增独立的 Universal Scene Keyframe Chain Release Gate，并通过 Default-only、Default＋Special、长片分段和旧 Project 回归。

---

## 最终愿景

我们并不是把多个 15 秒 MP4 简单连接起来。

目标是一套真正具有导演、剪辑、资产管理、版本控制和局部重算能力的 AI 影片工作台：

```text
45 秒短片
    ↓
2 分钟短剧
    ↓
多集连续剧
    ↓
90 分钟长片
```

每一次扩展都必须继续保持：

- 可编辑
- 可恢复
- 可重算
- 可验证
- 可迁移
- 可控制成本
- 可管理储存空间

这将是 MiniMax H3 Director Cut Studio 从“Prompt 工具”升级为完整 AI Video Production Pipeline 的关键阶段。

---

## GitHub Issue 建议资料

### Issue 标题

```text
[Roadmap / RFC] Long-Form AI Video Production Pipeline：从 45 秒走向 2 分钟及 90 分钟的可编辑 AI 电影工作流
```

### Labels

```text
roadmap
enhancement
long-form
performance
storage
render-pipeline
v0.3.1
```

### Milestone

```text
v0.3.1 — Long-Form AI Video Production Pipeline
```
