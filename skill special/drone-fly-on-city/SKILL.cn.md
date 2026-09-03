---
name: drone-fly-on-city
description: 将用户绘制的红色路线转换为 MiniMax H3 无人机航点任务，生成连续路线飞行及受控 360 度环绕或旋转。适用于城市航拍、地图转航拍、房地产飞越、旅游宣传及可控航拍运镜；不用于静态图片或无关人物视频。
---

# MiniMax H3 城市无人机航线控制

将用户绘制的红线转换为可编辑航点任务与 H3 英文运镜提示词。红线仅为路线分析数据，绝不得进入视觉生成参考集或出现在成片中。

## 1. 理解请求

接受带红线的图片、地图、卫星图、城市照片、视频帧、口述路线，或“沿红线飞行并 360 度旋转”等请求。有路线图时，将红线作为权威航线并转换成文字航点；绝不可将路线图当作地点、构图或视觉风格参考。所有视觉决策以 `@P1` 为准。保留用户给定的时长、比例、地点、天气、时间、无人机类型、地标、速度和首尾画面；未给定时，使用匹配参考光线的中速平滑航拍与清晰锚点。

## 2. 必填参考图角色与视觉隔离

生成 H3 视频提示词前必须加载两张 Media Pool 图片：

- `@P1`：必填场景母版，也是唯一视觉事实来源。保留地点、地标、建筑、布局、天气、时间、光向与强度、色板、调色、曝光、对比度、氛围、镜头特性、机位高度和特效。
- `@P2`：仅限路线控制数据。只读取红线起点、转弯、曲线和终点，并转为抽象文字航点。禁止作为 H3 或 Z-Image 参考、首尾帧、风格、构图、场景来源或媒体请求的视觉来源；不得把 `@P2` 的像素、物件、文字、图形、颜色、叠层、注释、箭头或红线复制到视频。

缺少 `@P1` 或 `@P2` 时，返回硬拦截并要求补齐。不得从 `@P2` 创建 `@P1`，也不得仅凭 `@P2` 生成最终 H3 提示词。

### Design JSON 预检约定

每个 Design JSON 的 `existing_media_uses` 必须登记两张已加载图片：

```json
"existing_media_uses": [
  {
    "requirement_id": "scene_master_visual",
    "media_id": "P1",
    "media_type": "image",
    "usage": "h3_reference",
    "reuse_policy": "whole_design",
    "start_seconds": 0.0,
    "end_seconds": "<DURATION>",
    "track": "V1",
    "instruction": "Use @P1 as the mandatory visual scene master for the entire video. Preserve its setting, layout, weather, lighting, colour grade, mood, exposure, atmosphere, lens character, and effects."
  },
  {
    "requirement_id": "route_control_nonvisual",
    "media_id": "P2",
    "media_type": "image",
    "usage": "analysis_only",
    "reuse_policy": "whole_design",
    "start_seconds": 0.0,
    "end_seconds": "<DURATION>",
    "track": "V1",
    "instruction": "Use @P2 only to extract abstract route waypoints. It is non-visual control data: never use it as an H3 or Z-Image image reference, start/end frame, style, composition, or scene source. Do not copy its pixels, red lines, arrows, labels, colours, text, or overlays into the video."
  }
]
```

将 `<DURATION>` 替换成用户要求的数值时长。

## 3. 场景关键帧链与自动收尾帧

把用户提供的视觉图片视为有先后顺序的场景关键帧链。`@P1` 永远是第一锚点，`@P2` 永远不属于视觉链。Design 明确选用的其他用户图片，例如 `@P3`、`@P4`、`@P5`，默认按 Picture 编号成为后续权威场景锚点；用户明确提供其他时间顺序时，以用户顺序为准。

当视觉链包含 `@P1` 及至少一个后续用户场景时：

- 每张用户场景图只拥有一个互不重叠的 `time_scoped` 时间区间。不得让 P1 或后续锚点覆盖整个 Design；渲染较早场景时，不得在同一个原生 H3 请求中加载未来场景图片。
- 每次场景变化都必须写明 Incoming／Outgoing 物理状态。Studio 将每个所有权区间独立渲染，只把前段最后 24 个视频帧作为无声运动上下文；不得复制前段音频，也不得提前加载下一场景。
- 只在最后一个用户锚点之后建立一张未命名 Z-Image 请求，`requirement_id` 使用 `auto_terminal_keyframe_after_<last-anchor>`。它是根据最后场景环境和 Outgoing State 建立的稳定收尾画面。已有用户场景锚点时，不得再机械创建中点图或逐 Shot 补图。
- 不得填写 `preferred_media_id`。由 Studio 自动选择真正空置的下一个 Virtual Media Pool 编号：P1/P2/P3 已占用时成为 P4；P1 至 P5 已占用时成为 P6。
- 下一次重新 Design 时，旧的 `AI DESIGN GENERATED REFERENCE` 或 `AUTO TERMINAL KEYFRAME` 只是不再启用的历史资料，不得自动升级为用户场景锚点；只有用户替换或明确提升它时才可使用。

自动收尾请求绝不得设置 `identity_anchor=true`。城市、建筑、道路、天际线等纯环境图禁止人物、人脸、人形、肖像、假人、雕像式人物和楼顶人物。提示词不得引用任何 Picture 标签或控制图外观，而要用自包含文字重述最后场景的已观察环境、光线、构图与最终机位状态。

所有Z-Image／T2I请求都是冻结静态画面，不是摄影机运动图解。从普通图片提示词和 `subject_keywords` 删除 `360-degree`、`orbit`、`orbital yaw`、圆形、轨迹、路线、航点及同类运动规划短语，只保留城市建筑、构图、天气、光线、色彩、曝光、镜头与唯一冻结机位。随后准确追加：`The drone flight path is implied only through camera motion and must never be visible in the image. No orbit ring, no circular light trail, no glowing ellipse, no trajectory line, no HUD, no graphic overlay around the towers.` 并设置专用Z-Image负面提示词：`visible flight path, orbit ring, circular light trail, glowing ellipse, light ribbon, trajectory line, energy ring, HUD overlay, graphic circle, neon loop around buildings`。这份负面词表绝不能复制进H3视频提示词。

只有 `@P1` 与控制用 `@P2` 时，保持普通单场景流程。只有用户明确要求且确实有助连续性时才可创建其他机位参考，而且每张图仍只能继承 P1 的地点、布局、地标、建筑、物件、天气、时间、光线、色彩、曝光、氛围、镜头和特效；P2 始终不得成为视觉母版。

## 4. 旋转模式

除非用户明确要求组合，否则只选一种模式：

- **环绕模式（默认）**：无人机沿路线飞行，镜头平滑绕目标地标偏航。
- **机身偏航自旋**：机身前进时完成一次 360 度偏航；只用于明确要求机身旋转的请求。保持水平线稳定，不翻滚。
- **镜头平移/摇镜**：无人机跟随路线，镜头平移、俯仰或观察目标。
- **环绕加跟随**：无人机沿路线平移并绕稳定地标完成一次可测量环绕，仅在路线物理上支持时使用。

默认全程只完成一次完整 360 度循环，旋转速度必须物理可信，并与前进运动同步。

## 5. 将红线转换为航点

把图片平面视为归一化屏幕坐标；不可从 2D 图像声称精确 GPS、米制高度或真实遥测。创建 3–6 个严格贴合路线几何的有效航点：

- `WP0`：路线起点与初始朝向。
- 中间 WP：每一个显著曲线顶点、转弯或方向变化；不得跳过弯道。
- 最终 WP：路线终点、最终目标构图与稳定朝向。

每个航点必须定义 `screen_position`（`x` 与 `y`，0.00–1.00）、`travel_vector`、`altitude_relation`、`look_target`、`yaw_progress_degrees`、`speed` 与 `continuity_note`。S 弯必须在屏幕坐标中形成 S 形序列。偏航按路线长度分配，最终偏航必须正好为 `360`。

## 6. 方向映射

| 路线表现 | H3 运镜语言 |
|---|---|
| 由下至上，主体变大 | 向前飞、推进、轻微上升 |
| 由上至下，主体变小 | 后拉、后退、轻微下降 |
| 左至右 | 保持动量向右漂移或平移 |
| 右至左 | 保持动量向左漂移或平移 |
| 大弧线 | 沿平滑弧形航线飞行 |
| 围绕地标的圆形 | 维持受控环绕半径 |
| S 弯 | 以缓和偏航执行平滑 S 弯 |
| 指向天际线 | 向天际线推进，逐步打开纵深 |
| 指向街道或巷道 | 沿街道轴线推进或下降，不穿过几何体 |

路线方向与可见地理冲突时，保留路线方向，但调整飞行以避开墙体、车流、屋顶、树木、电线和行人。

## 7. H3 提示词构造

最终提示词必须是单段英文，不含中文说明。视觉语言来自 `@P1`，运动语言来自由 `@P2` 提取的文字航点：

1. 开头明确描述 `@P1` 的地点、布局、地标、光线与时间、天气与氛围、调色、曝光和镜头特性。
2. 只描述物理路线运动；不得在正文提及 “red line”、“map” 或 “route graphic”。说明连续运动、真实惯性、加速与减速。
3. 明确写出环绕或偏航自旋模式及稳定目标锁定。环绕可用：`While translating along the path, the camera completes one seamless full 360-degree orbital yaw around [target], keeping the target continuously readable and the horizon stable.`
4. 写出最终构图与短暂稳定停留。
5. H3 只有一个视频生成提示词，不要把Z-Image负面词表附加到H3；反复写出这些图形反而可能诱导视频模型画出来。结尾只加入正向约束：`写实城市画面保持干净无遮挡，所有导航控制均为非视觉数据并完全位于画外；水平线稳定，航拍视差与惯性连续可信。` 精确的静态图排除句和负面词表只属于Z-Image参考图生成，Studio会在H3编译前排除它们。

若启用音频生成，只追加与场景相符的环境音描述；除非用户要求，否则不要加对白。

## 8. 可编辑航点 JSON

用户要求 Design、计划、JSON 或可编辑控制时，先输出可编辑航点 JSON，再输出英文 H3 提示词。JSON 必须包含 `existing_media_uses` 约定、`route_overlay: "hidden"`、旋转模式、一次旋转循环、360 总偏航度、命名目标锁定、3–6 个文字航点，以及稳定水平线、避碰、无突然瞬移和真实视差/惯性的安全约束。所有 `end_seconds` 必须使用用户要求时长。

```json
{
  "mission_type": "camera_trajectory_control",
  "existing_media_uses": [
    {
      "requirement_id": "scene_master_visual",
      "media_id": "P1",
      "media_type": "image",
      "usage": "h3_reference",
      "reuse_policy": "whole_design",
      "start_seconds": 0.0,
      "end_seconds": 15.0,
      "track": "V1",
      "instruction": "使用 @P1 作为必填视觉场景母版；保留其全部场景与视觉属性。"
    },
    {
      "requirement_id": "route_control_nonvisual",
      "media_id": "P2",
      "media_type": "image",
      "usage": "analysis_only",
      "reuse_policy": "whole_design",
      "start_seconds": 0.0,
      "end_seconds": 15.0,
      "track": "V1",
      "instruction": "只用 @P2 提取抽象文字航点；绝不可作为视觉输入或复制其中的红线路径图形。"
    }
  ],
  "route_overlay": "hidden",
  "rotation_mode": "orbit",
  "rotation_cycles": 1,
  "total_yaw_degrees": 360,
  "target_lock": "命名的可见地标",
  "waypoints": [
    {
      "id": "WP0",
      "screen_position": { "x": 0.15, "y": 0.78 },
      "travel_vector": "向前并轻微向右，跟随路线初始曲线",
      "altitude_relation": "level",
      "look_target": "命名的可见地标",
      "yaw_progress_degrees": 0,
      "speed": "medium",
      "continuity_note": "从红线起点开始，立即建立前进动量。"
    },
    {
      "id": "WP1",
      "screen_position": { "x": 0.52, "y": 0.46 },
      "travel_vector": "向左平滑弯曲，跟随路线弯道",
      "altitude_relation": "higher",
      "look_target": "命名的可见地标",
      "yaw_progress_degrees": 180,
      "speed": "medium",
      "continuity_note": "维持环绕半径，横向移动必须匹配路线曲率。"
    },
    {
      "id": "WP2",
      "screen_position": { "x": 0.86, "y": 0.22 },
      "travel_vector": "向最终天际线构图推进，跟随路线出口",
      "altitude_relation": "higher",
      "look_target": "命名地标与天际线",
      "yaw_progress_degrees": 360,
      "speed": "slow",
      "continuity_note": "在红线终点缓慢稳定收束，并停留一秒。"
    }
  ],
  "safety_constraints": [
    "稳定水平线",
    "不得碰撞建筑、电线、树木、车流或行人",
    "禁止突然瞬移或方向反转",
    "真实航拍视差与惯性",
    "路径严格遵循已提取航点"
  ]
}
```

## 9. 输出规则与质量检查

- 用户只要视频提示词时，只输出最终英文 H3 提示词。
- 用户要求 Design、计划、JSON 或路线说明时，先输出可编辑 JSON，再输出 `H3 Prompt:` 和最终英文提示词。
- 每个 Design JSON 均将 `P1` 登记为 `h3_reference`，将 `P2` 登记为 `analysis_only`；P2 只参与规划，不进入 Timeline、Segment 容量、上传清单或 H3 图片槽。
- 存在多个用户场景图时，必须按第 3 节建立互不重叠的关键帧链，并在最后一个锚点之后只创建一张未命名的环境收尾帧；不得预先指定其 P 编号。
- 所有航点必须贴合路线形状，不得出现无解释捷径。
- 最终 H3 提示词必须为英文、只含一次 360 度循环、保持 `@P1` 场景连续性，并对 `@P2` 保持零视觉使用与零文字引用。
- 成片绝不得出现红色 waypoint、红线、路线叠层、箭头、标记、HUD、UI、注释、涂鸦或其他控制图形。
- 不得声称已执行真实无人机飞行、获得 GPS 数据或实施物理航点控制。

### 质量检查清单

返回前逐项确认：

- **路径保真**：JSON 与提示词的航点严格描摹红线形状、转弯与曲线；除非用户要求直接飞行，否则不得走直线捷径。
- **视觉隔离**：最终 H3 提示词不得出现 P2 标签或描述其可见控制图形，只使用第 7 节的正向干净画面约束。
- **旋转准确**：一次旋转的最终累积偏航严格等于 360°。
- **模式清晰**：环绕与机身自旋不可混淆，必须符合用户意图。
- **物理可信**：避开建筑与树木等几何体；水平线稳定，视差与惯性自然。
- **语言**：最终提示词只用英文，不含实现说明。
- **JSON 完整**：`@P1` 与 `@P2` 均正确登记于 `existing_media_uses`；只使用归一化屏幕坐标，不声称真实世界遥测。
- **关键帧隔离**：后续用户场景图各自拥有独立区间；自动收尾图只位于链尾；渲染前一场景时没有加载任何未来 Picture。
- **静态参考图隔离**：每张生成城市Picture都是冻结环境画面；普通提示词及关键词没有orbit／yaw／trajectory运动指令，包含精确Clean Frame句，并在专用负面提示词保存光环／光带伪影词表。

## 10. 控制数据卫生

具体路线伪影词汇只允许出现在P2的 `analysis_only` 登记与专用Z-Image `negative_prompt`。正向补图提示词只能额外保留一条精确Clean Frame排除句。不得把负面词表复制进creative_brief、Shot、constraints、marker、transition或最终H3 Prompt；H3最终生成指令只用正向语言描述稳定水平线、连续惯性、干净写实画面、避碰航线和一致城市几何。
