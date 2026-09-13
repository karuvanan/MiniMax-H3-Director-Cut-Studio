# Step 2：ACE-Step 1.5 Music Workbench 主机／副机部署

开始前，请先在所有电脑完成 [`Step 1：Studio Runtime 部署`](step1.md)。

v0.3.5 的 `MUSIC COVER` 是独立 ACE-Step 1.5 Music Workbench，支持 `Cover / Repaint / Lego / Extract`、参考音频分析、Prompt/Lyrics/BPM/调性/拍号/时长自动填写、Palette Remix、试听、下载及完整 API 返回。

## 部署原则

所有电脑都使用同一个入口：

```powershell
.\run_h3_prompt_studio.bat
```

Studio 启动后自动判断当前电脑角色，但不会在 Client Mode 自动安装或下载 ACE-Step：

| 检测结果 | 模式 | ACE-Step 行为 | Music Workbench API |
|---|---|---|---|
| 本机已有可运行环境及 Turbo checkpoint／安装标记 | `SERVER MODE` | Studio 静默启动本机 ACE-Step | `http://127.0.0.1:8001` |
| 本机尚未完整安装 | `CLIENT MODE` | 不安装、不下载、不启动本机服务 | `http://192.168.0.185:8001` |

## A. 主机安装（例如 `192.168.0.185`）

主机负责实际运行 ACE-Step 推理。Studio 只有在检测到最大单卡显存**严格大于 16GB**时，才允许第一次本机安装。

### 主机条件

- NVIDIA GPU，最大单卡 VRAM 大于 16GB；
- 兼容的 NVIDIA 驱动及可正常执行的 `nvidia-smi`；
- 可以执行 `git`；
- 能够访问 GitHub 与 Hugging Face；
- 已完成 [`step1.md`](step1.md) 的 Studio Runtime 部署。

### 推荐：在 Studio 内安装

1. 把完整 Studio 项目放到主机，例如：

   ```text
   D:\minimax h3\minimax h3 reference r2v\
   ```

2. 运行：

   ```powershell
   .\run_h3_prompt_studio.bat
   ```

3. 点击顶部最右侧 `MUSIC COVER`。
4. 尚未安装时，窗口显示 `CLIENT MODE`、检测到的 VRAM 和 `INSTALL LOCAL ACE-STEP`。
5. 点击 `INSTALL LOCAL ACE-STEP` 并确认。只有此时 Studio 才会开始安装：

   - 从官方 `https://github.com/ace-step/ACE-Step.git` Clone 到 `models/ACE-Step-1.5/`，已有完整源码时跳过；
   - 在 `models/ACE-Step-1.5/.runtime/<电脑名称>/.venv/` 建立独立环境；
   - 下载模型到 `models/ACE-Step-1.5/checkpoints/`；
   - 后台启动 `0.0.0.0:8001`；
   - 健康检查通过后写入 Server Mode 安装标记。

6. 安装成功后，当前 Music Workbench 会切换到：

   ```text
   SERVER MODE · http://127.0.0.1:8001
   ```

7. 以后在这台主机运行 `run_h3_prompt_studio.bat`，Studio 会自动判断 Server Mode 并启动 ACE-Step，不需要另外执行服务器 BAT，也不会注册 Windows 登录自启动任务。

### 主机健康检查

在主机打开：

- [http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)

副机需要能够打开：

- [http://192.168.0.185:8001/health](http://192.168.0.185:8001/health)

如果主机本机正常但副机无法连接，请检查：

- 主机 IP 是否仍为 `192.168.0.185`；
- Windows 网络类型是否为 Private；
- Windows Defender Firewall 是否允许私有网络 TCP 8001；
- 路由器是否启用了 Client/AP Isolation；
- ACE-Step 日志是否出现 CUDA 或模型错误。

请勿把没有鉴权的 8001 端口直接暴露到公网。

## B. 副机安装（Client Mode）

副机只需要普通 Studio Runtime，不需要 ACE-Step Python 环境、模型或独立启动脚本。

1. 完成 [`step1.md`](step1.md)。
2. 运行：

   ```powershell
   .\run_h3_prompt_studio.bat
   ```

3. Studio 检测不到完整本机 ACE-Step 时自动进入 `CLIENT MODE`，不会出现 Clone、环境安装或模型下载。
4. 打开 `MUSIC COVER`，确认 API 为：

   ```text
   http://192.168.0.185:8001
   ```

5. 点击 `TEST API`。连接成功后即可把副机音频上传到主机进行 Analysis、Cover、Repaint、Lego 或 Extract。
6. 显存不大于 16GB 的副机会保持 Client Mode，`INSTALL LOCAL ACE-STEP` 按钮不可用，但不影响使用远端主机。

如果主机地址不是 `192.168.0.185`，可直接在 Music Workbench 的 API 输入框改成实际局域网地址。

## C. 手动安装与诊断

自动安装无法使用时，在主机项目根目录操作。

ACE-Step 目录不存在时才执行 Clone：

```powershell
git clone https://github.com/ace-step/ACE-Step.git models\ACE-Step-1.5
```

然后启动：

```powershell
.\start_ace_step_api.bat
```

启动器会避免重复启动 8001 端口、修复电脑专属隔离 runtime，并启用 Base 模型按需加载。

后台日志：

```text
logs/ace_step_api.stdout.log
logs/ace_step_api.stderr.log
```

## 日常启动顺序

### 主机

```text
run_h3_prompt_studio.bat
→ Studio 检测 Server Mode
→ 自动启动本机 ACE-Step
→ 使用 127.0.0.1:8001
```

### 副机

```text
run_h3_prompt_studio.bat
→ Studio 检测 Client Mode
→ 不安装、不启动本机 ACE-Step
→ 使用 192.168.0.185:8001
```

主机必须保持开机并运行 Studio/ACE-Step。副机无法通过已经关闭的 HTTP API 反向启动已关机的主机。

## 释放主机显存

主机或副机可以点击 Studio 主页顶部的 `UNLOAD ALL`。Studio 会向当前显示的 ACE-Step API 发出卸载请求，释放 DiT、VAE、文字编码器及分析 LM，但保留 API 服务。下一次打开 Music Workbench 分析或生成时，模型会自动重新载入。

正常关闭 `MUSIC COVER` 视窗时，也会自动向该视窗实际使用的 API 发出同样的模型卸载请求；这项自动清理只处理 ACE-Step，不会连带卸载 ComfyUI 或 LM Studio。若分析或生成仍在进行，视窗会等待任务结束后才允许关闭。

为保护成品，ACE-Step 有任务正在运行或排队时会拒绝卸载。更新此功能后需要重新启动主机上的 Studio／ACE-Step 服务，让新的 `/v1/unload` 扩展生效。

## 延伸阅读

- v0.3.5 Music Workbench 功能：[`v0.3.5 readme.md`](v0.3.5%20readme.md)
- 返回主说明：[`README.md`](README.md)
