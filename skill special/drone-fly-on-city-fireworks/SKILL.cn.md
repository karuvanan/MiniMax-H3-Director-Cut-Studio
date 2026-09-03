---
name: drone-fly-on-city-fireworks
description: 建立电影级写实夜间城市无人机航拍，以路线控制一次360度地标环绕，并保持烟花、烟雾、反射、曝光及原生声音的物理连续。用于已有场景图和路线图的城市庆典航拍；不用于日间飞行、静态图片或人物主导场景。
---

# MiniMax H3 城市烟花无人机导演

本 Special Skill 与 Default H3 Prompt Writing 绑定使用。输出可以直接进入 H3 的可编辑、按时间排列的 Director Design。保留用户指定的时长、比例、城市、地标、天气、首尾构图和主页 MUSIC 设置。

## 1. 必填参考素材

- `@P1` 是场景母版及开场画面。锁定天际线几何、地标数量与间距、道路、天气、时段、光线、曝光、调色、空气感、镜头高度和视觉特效。
- `@P2` 只作路线分析。仅提取起点、重要转弯、曲线方向和终点，再转换成抽象摄影机运动。它不得成为H3／Z-Image视觉参考、Timeline Clip、首尾帧、风格／构图来源或身份锚点。

缺少真正载入的P1或P2时，明确阻止并指出缺少哪张图，不得虚构素材编号。Design JSON把P1登记为 `h3_reference`，把P2登记为覆盖全程的 `analysis_only`。P2留在Virtual Media Pool但不占H3实体Picture槽，也不进入上传和Loader。

## 2. 路线与环绕

把P2简化成3–6个归一化规划航点，保留所有重要弯位与起终方向，不从二维图宣称GPS或真实遥测。渲染前把航点翻译成自然物理运镜，删除P2／WP／坐标／红线／地图／导航字眼。

默认从地标左前方低位开始，向前并逐渐升高，以稳定水平线和真实惯性围绕命名地标完成一次顺时针360度环绕；保持自然视差和曝光适应，避开建筑、屋顶、电缆、树木、车辆和行人；最后到达右侧高机位，将地标置中，减速并稳定停留一秒。不得倒转、重复环绕、瞬移、穿楼或让城市几何闪烁。

## 3. Shot与Segment

Shot按0.5秒网格连续覆盖全片，不留空隙、不重叠；约每4–6秒一个Shot，每个Shot只有一个主要运镜，并写明必须完成动作、环境回应、Incoming State、Outgoing State与可舍弃的Optional Flourish。

15秒建议三阶段：

1. 接近／点火：建立地标并开始环绕，只有少量远处屋顶升空火花。
2. 侧面揭示／增强：金、白、深红烟花在建筑后方和上方绽放，玻璃和湿街产生回应。
3. 右侧高位结尾：环绕收束，一朵大型金色菊花烟花在尖塔后方绽放，进入一秒Final Hold。

其他时长按比例调整，不得每个Shot更换城市或重置烟花。

## 4. 烟花物理与连续性账本

烟花是环境中的真实事件，不是图形覆盖层。每个Shot记录并延续：发射区域、相对地标的爆发位置、颜色与类型、点燃／径向扩散／火星坠落／熄灭阶段、烟量和风向、玻璃与湿地反射、曝光变化，以及边界处尚未结束的爆炸声和噼啪尾音。

每枚烟花遵循发射或升空火星→空中爆发→离散粒子扩散→按距离延迟的爆炸声→余烬下坠→烟雾飘移→反射消退。烟花只能在地标后方或上方，不得触碰、包围、从塔身射出、取代或扭曲建筑。保留天际线纵深、负空间和清楚结构，不形成连续烟花墙。

最终金色菊花烟花是尖塔后方的离散径向粒子花朵，不是环绕轨道、光环、实心圆盘、霓虹圈、能量环或光带。前一Shot留下的烟雾必须继续飘动，不能切镜后消失。

## 5. 场景关键帧链

只有P1/P2时保持单一视觉场景。如果用户另外载入并选择P3/P4/P5等城市图，跳过analysis-only的P2，把它们作为有序场景链：每张图只拥有一个互不重叠的 `time_scoped` 区间；未来Picture不得提前载入；每个区间是独立原生H3 Job；边界只传递前段最后24个无声视频帧，不传递旧音频；最后一个用户锚点后只生成一张未指定P编号的environment-only收尾图。

收尾图继承最后场景的天际线、烟花阶段、烟雾、反射、曝光和Outgoing Camera State，不新增人物或改变城市。

## 6. Z-Image静态图隔离

每张生成Picture只是一个冻结摄影瞬间，不是运镜图解。从普通图片Prompt与 `subject_keywords` 删除360-degree、orbit、orbital yaw、circle path、trajectory、route、waypoint等运动规划内容，只保留城市、建筑、天气、光线、烟花状态、烟雾、反射、镜头和唯一冻结机位。

正向提示词准确追加：

`The drone flight path is implied only through camera motion and must never be visible in the image. No orbit ring, no circular light trail, no glowing ellipse, no trajectory line, no HUD, no graphic overlay around the towers.`

同时追加烟花澄清句：

`Fireworks are separate radial particle bursts located behind and above the skyline, with individual sparks, natural smoke and physically plausible reflections; they never form a continuous ring, ribbon, ellipse or flight path around any building.`

专用Z-Image负面提示词：

`visible flight path, orbit ring, circular light trail, glowing ellipse, light ribbon, trajectory line, energy ring, HUD overlay, graphic circle, neon loop around buildings, continuous firework ring around buildings, fireworks forming a flight path, fireworks wrapped around towers, solid neon fireworks, duplicated landmark, fused towers`

不得把这份负面词表放进最终H3 Prompt。P2永远不是任何生成图的视觉父级。

## 7. H3提示词合约

每个Segment编译成一段按时间排列的英文H3 Prompt，视觉、运镜、烟花状态和声音必须同步。先建立P1城市结构与冷蓝夜景；再描述连续飞行和唯一一次顺时针环绕；烟花使用金、白、深红离散粒子，在天际线后方／上方爆发，带烟雾、玻璃／湿街反射和自然曝光适应；最后在右侧高位用金色菊花烟花及一秒停留收束。

最终H3 Prompt不得出现P2、红线、航点图形、Z-Image负面词表、人物、字幕、文字、Logo、水印、重复地标、卡通风格、无来源Spot Light或额外建筑。结尾只用正向语言要求画面干净、规划控制位于画外、水平线稳定、城市几何一致、视差与惯性连续。

## 8. 原生声音与音乐

声音必须属于画内真实声源并符合距离：连续高空风、远处城市交通底噪、发射嘶声、延迟到达的低频爆炸和短促噼啪尾音，以及附近建筑反射声。不要在Shot／Segment边界突然重新开始或截断声音。Timeline没有明确对白／旁白时不得新增人声。

音乐服从主页 `MUSIC: OFF / AUTO / TIMELINE`：OFF不配乐；AUTO可用克制的电影庆典音乐并避让主要爆炸声；TIMELINE只使用用户已经编排的音乐说明。

## 9. Apply质量检查

- P1是唯一场景母版；P2精确为analysis_only且不进入视觉Loader。
- Shot完整覆盖时长、无空隙重叠，每Shot一个主运镜。
- 只有一次连续360度环绕和一次最终一秒停留。
- 地标数量、间距及建筑结构稳定，无碰撞和几何闪烁。
- 烟花保持后方／上方的离散粒子，烟雾、反射和曝光跨Shot连续。
- 自动Picture普通提示词与关键词不含orbit/yaw/trajectory，并带两条静态图合约与专用负面词。
- 最终H3 Prompt保留真实环绕运镜，但没有路线图形、负面词表或可见控制层。
- 多场景关键帧区间互不重叠，未来Picture和前段音频不跨错Segment。
- 烟花原生声音对应可见事件，不在边界被截断。

