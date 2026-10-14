# Source Video Cast Remake H3｜分析V1导演语法，再由P演员重演

![Source Video Cast Remake H3](./source-video-cast-remake-h3-promo.png)

适用版本：`MiniMax H3 Director Cut Studio v0.3.6-alpha2`

`Source Video Cast Remake H3`不是逐帧换脸。Studio先把V1分析成场景、人物职责、动作因果、运镜、剪辑节奏与原声时间的导演蓝图，再让用户提供的P1–P9演员在重新生成的世界里重演。V1像素不会送进H3 Video Reference；最终声音则恢复为V1未经修改的原声。

> 只使用你拥有或获授权二创的源影片。

## 一、素材职责

| 槽位 | 内容 | 规则 |
|---|---|---|
| `V1` | 有权二创的源影片 | 只作为导演蓝图与原声时间权威，不作为H3画面参考。 |
| `P1–P4` | 基础替换演员 | 在人物时间卡中逐次指定，不按编号自动猜角色。 |
| `P5–P9` | 可选后续演员 | 只有V1确实存在额外主要角色时才启用。 |
| V1原声 | 对白、音乐、环境与节奏 | 每个Segment切出同一时间窗，最终恢复未经修改的Master Audio。 |

## 二、开始前检查

1. LM Studio Server已经启动，并能访问Design设置中的`/v1`地址。
2. 已加载指定的Qwen视觉模型，例如`qwen3.8-uncensored-nvfp4-mtp`。
3. V1可以正常播放，时长和内嵌声音已经识别。
4. 每张P演员图都能清楚辨认脸孔、发型和服装。
5. ComfyUI H3 Server可连接。

## 三、Step by Step

### Step 1｜把源片与演员放进Media Pool

1. 把源影片加载为`V1`。
2. 把第一组替换演员依次加载为`P1`、`P2`、`P3`、`P4`。
3. 如果V1有更多主要人物，再加入P5及后续图片；不需要时不要硬塞人物。
4. 不要把V1重复加载成普通Video Reference。

### Step 2｜选择Special Skill

1. 进入`Design`。
2. 选择`Source Video Cast Remake H3`。
3. 确认V1与P图片在Media Pool Intelligence中可见。
4. 点击`CREATE DIRECTOR DESIGN JSON`。

### Step 3｜等待Qwen完整分析V1

Studio会完成以下工作：

1. 读取V1完整时长和真实场景边界；
2. 为每个场景建立early／late／midpoint分析帧；
3. 生成最多三张清晰的带时间标签Storyboard；
4. 由Qwen建立地点、事件、动作交接、发声者、听众、镜头和连续性账本；
5. 把每一次主要人物出场变成独立的正方形脸孔时间卡。

长片分析采用紧凑32K结构化输出和独立30分钟时限。JSON漏逗号、输出不完整或分析worker意外退出时，Studio会自动进行一次紧凑重试。不要在分析期间重复点击Design或关闭Studio。

### Step 4｜逐张绑定人物时间卡

分析完成后，`V1 PRINCIPAL ROLE BINDINGS`会按源片时间排列：

1. 每行显示6张正方形卡片。
2. 每张卡只代表一个独立出场时间。
3. 同一源人物的卡片最初会采用相同建议P图，但建立后不会锁定或联动。
4. 在`REPLACE WITH`中选择P1–P9。
5. 可以让多个时间卡复用同一P图。
6. 如果某次出场要保留原演员，选择`Keep original V1 face`；Studio会把该脸孔裁切物化为新的P身份参考。
7. 滚到最下方，确认最后一排及ready状态完整显示。

人物绑定以“源角色＋场景时间”为单位，因此后段可以故意换成另一张P图，而不会误改前段。

### Step 5｜重新建立Director Design JSON

完成全部人物绑定后，再点击一次`CREATE DIRECTOR DESIGN JSON`。检查：

- 所有V1主要角色都有明确P绑定；
- `media_requests`没有自创人物图或场景替代图；
- V1被标记为`analysis_only`；
- Shot顺序与V1事件顺序一致；
- 每个Shot只写实际出现的P人物；
- `text_layers`为空，没有转录、翻译或新对白；
- 总时长等于V1真实可播放时长。

### Step 6｜通过Preflight并Apply

点击`APPLY TO H3 WORKSPACE`。如果Preflight提示缺少P图或角色账本，不要强行继续：

- 缺少P图：回到绑定卡选择已经加载的P图片；
- 缺少principal-role ledger：确认Qwen API在线后重新运行V1分析；
- 指定P4/P5未使用：只在对应V1角色确实存在时建立绑定。

### Step 7｜先做0.2MP Preview

1. 点击`PREVIEW 0.2M`。
2. 检查每次角色交接是否与V1相同。
3. 检查场景类型、建筑结构、主要物件、光向和构图是否仍可辨认来自V1。
4. 检查当前说话角色是否跟随对应V1原声音素。
5. 检查听众和群众是否保持非发声嘴形。
6. 检查切镜节奏与原声是否同步。

### Step 8｜局部修正而不是重跑整片

如果某个Shot人物、闭嘴状态、构图或动作不正确：

1. 在Timeline双击该Shot。
2. 在`SHOT VISUAL EDITOR`修改人物、Speaking、Mouth、Camera、Action或Environment。
3. 需要Qwen协助时，只勾选允许它改变的字段。
4. 保存后点击`REGENERATE DIRTY`。
5. Studio只重新生成受影响Segment，并复用已有clean片段。

### Step 9｜正式输出

Preview确认后点击`ACCEPT 1.0M`。Studio用完整分辨率重新生成dirty片段，装配全片并恢复V1未经修改的内嵌原声作为唯一Master Audio。

## 四、验收清单

- [ ] V1只作`analysis_only`，没有占用H3 Video Reference。
- [ ] 所有主要人物时间卡已经绑定。
- [ ] P演员没有互换、混脸、复制或被V1原演员覆盖。
- [ ] 每个Shot只加载真正出场的P人物。
- [ ] 保留V1事件次序、动作因果、镜头目的与剪辑节奏。
- [ ] 场景重新生成但仍保留V1的地点类型、拓扑、物件和光向。
- [ ] 只有当前发声人物对嘴；听众保持闭嘴反应。
- [ ] 没有新增对白、旁白、歌词或替代音乐。
- [ ] 最终声音为V1原声，总时长与V1一致。

## 五、常见问题

### `Qwen3.8 analysis stopped`

先确认LM Studio API地址可以打开并已加载正确模型。v0.3.6-alpha2会区分JSON损坏、HTTP失败与worker timeout，自动进行一次紧凑重试；第二次失败时会保留明确原因。

### 出来的画面只是重复V1

确认Skill确实是`Source Video Cast Remake H3`，且V1为`analysis_only`。它不应进入H3 Video Reference槽。

### 人物没有按照P1–P4替换

不要只在Media Pool放入图片；必须在每一张V1人物时间卡的`REPLACE WITH`中确认P绑定，再重新创建Director Design JSON。

### Preview对嘴但Full输出不对

检查Full是否复用了旧Segment。修改Shot后使用`REGENERATE DIRTY`，确认受影响Segment重新生成，再执行`ACCEPT 1.0M`。

## 六、论坛简介（可直接复制）

> Source Video Cast Remake H3把V1当作导演蓝图，而不是逐帧换脸底片。Studio先用Qwen分析全片人物出场、场景、动作因果、运镜、剪辑和原声，再把每次人物出场显示为独立脸孔时间卡，让用户逐张绑定P1–P9。H3随后在重新生成但仍保留V1场景语汇的世界中重演，最终恢复V1原声。人物或镜头需要调整时，可直接用Shot Visual Editor与Regenerate Dirty局部重做。
