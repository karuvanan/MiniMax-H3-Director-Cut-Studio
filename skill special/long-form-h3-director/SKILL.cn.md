---
name: long-form-h3-director
description: |
  把超过单次 15 秒 H3 窗口的故事规划成可编辑的 Sequence、Shot 与原生 Segment 契约，保护逐字对白、审批安全边界、24 帧连续性、参考素材纪律及唯一项目终点 Final Hold，供 Studio 分批增量制作。
---

# 长片 H3 导演

本 Special Skill 与 Default H3 Prompt Writing 一起使用。Skill 负责设计完整故事与 Timeline；Studio runtime 决定每一批何时真正渲染。

## 保留完整故事

严格保留用户要求的总时长、比例、语言、人物、地点、故事顺序与交付目标。不能把 120 秒故事缩成单一 15 秒或 45 秒生成单位。

先把完整 Timeline 组织成承担明确故事职责的 Sequence，例如 Hook、铺垫、发现、追查、反转与集尾 Hook，再拆成可执行 Shot。动作与对白允许时，Shot 以约 5–8 秒为宜，并落在 0.5 秒网格。

每个 Shot 必须定义：故事职责与必须完成动作、Incoming State、Outgoing State、一个主要镜头运动、由接触引起的环境反应，以及不影响因果时才可省略的 Optional Flourish。

## 规划批准点

默认以 30 秒作为批准点，不把它当成强制剧情切口。明确 Dialogue、Voice-over 与 Lyrics 尽量完整留在批准点同一侧。若批准点会切断逐字对白、Reveal、人物首次出现、决定性动作或直接后果，必须把它移动到下一个安全的 0.5 秒 Shot 边界。

30、60、90 秒批准点不是结局。除非故事确实在那里结束，否则禁止加入结论、淡黑、姿势重置或 Final Hold。全片只在真正项目终点建立一个 Final Hold。

## 编译原生 H3 Segment 契约

Runtime 会在连续 Timeline 背后隐藏每段最多 15 秒的原生 H3 窗口。每一个可能边界都必须可续跑：记录准确的身体、镜头与道具 Outgoing State；下一段从该状态立刻向前推进；保持身份、服装、伤势、道具归属、空间、灯光与行进方向；禁止重演、回顾或复述上一段尾动作。

连续运动时，下一 Segment 可以使用上一段在 24 fps 下最后 24 帧作为纯运动上下文。它是时间检查点，不是需要重播的片头素材。明确 Hard Cut 才重置运动上下文；Match Action 必须说明接触点、方向和物体。

## 保护对白与文字

用户提供的 Dialogue、Voice-over、Lyrics 与 On-screen Text 必须逐字放进 `text_layers`，保留语言、speaker 与顺序，并设置 `explicit_user_requested=true`。Shot Prompt 不能成为唯一台词副本。

对白超出时间预算时，应延长或重新分配 Shot，同时保留故事职责；不得为了批准点而翻译、改写、重复、漏字或截断。

## 节省参考素材

使用稳定的 `@P`、`@V`、`@A` ID 复用 Virtual Media Pool。只有身份、服装、地点、关键证据、道具状态或困难边界确实缺少可靠参考时才建立新素材，不机械地为每个 Shot 生成一张图。

每张生成图只表现剧情真实环境中的一个冻结瞬间。每个原生 Segment 只动态加载本段有效参考，不把整个项目素材池全部塞入。

## 保持长片因果

持续维护人物身份／服装／知识／目标／情绪，道具归属／损坏／位置，空间路线／屏幕方向，未完成动作／镜头运动，以及线索铺垫与揭示账本。每个 Shot 至少改变信息、目标、风险、关系、地点或物理状态，禁止重复反应和重复说明。后段可以依赖已批准前段，但不能静默改写前段事实。

## 声音、转场与交付

同一地点跨画面剪接时延续环境声，使用接触同步 Foley、匹配空间的对白声学及对白期间音乐 ducking。优先 Hard Cut、Sound Bridge、动机明确的 Insert 与 Match Action，避免在批准点加入装饰性转场。

输出一个覆盖完整总时长、符合 Studio schema 的 Director Design JSON，而不是每批一个 JSON。使用现有字段表达 Sequence 职责、边界状态与优先级，不发明 schema 不支持的字段。

交付前验证：全时长无间隙／重叠；Shot 动作预算可执行；每个 Shot 只有一个主要镜头运动；`text_layers` 逐字且时间安全；每个边界 Incoming／Outgoing State 明确；原生 Segment 不重复开场动作；reference ID 稳定且按 Segment 动态加载；批准点不形成假结局；Final Hold 只存在于真正项目终点。

选择本 Skill 时，Studio 默认进入 Incremental production；不选择时保持 Full Range，除非用户自行切换。
