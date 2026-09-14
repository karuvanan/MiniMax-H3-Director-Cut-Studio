# Step 3：SoulX-Singer 主机／副机部署

`SOULX` 是独立的歌声转换工作区。它把 `Voice reference` 的目标音色转换到 `Source song`，输出 MP3；验收后由使用者手动把 MP3 放入 MTV Special Skill 的 `A1`。它不会自动改写 MiniMax H3 的原生音频，也不会自动写入 Timeline。

## 先决定哪台电脑是主机

主机运行 SoulX 模型与 API，例如：

```text
192.168.0.185:7861
```

第一次在某台电脑安装 SoulX，必须检测到最大单卡显存**严格大于 16GB**。16GB 或更低保持 Client Mode，不会开始安装。主机还需要 NVIDIA 驱动、可用的 `nvidia-smi`、Git、Hugging Face 网络访问，以及完成 [`step1.md`](step1.md) 的 Studio Runtime 部署。

## A. 主机安装

### 方法一：Studio 内安装（推荐）

1. 把完整项目放到主机并运行：

   ```powershell
   .\run_h3_prompt_studio.bat
   ```

2. 点击主页 `SOULX`。未安装时会显示 `CLIENT MODE`、检测到的 VRAM 与 `INSTALL LOCAL SOULX`。
3. 只有显存严格大于 16GB 时，点击 `INSTALL LOCAL SOULX` 才会开始安装。安装期间会出现全窗口半透明遮罩和青色旋转加载圈，请不要重复点击。
4. 安装器会在 `models/SoulX-Singer-main/` 建立独立的 Python 3.10 环境，安装 CUDA 版 PyTorch 与 SoulX 依赖，并下载：

   ```text
   models/SoulX-Singer-main/pretrained_models/SoulX-Singer/
   models/SoulX-Singer-main/pretrained_models/SoulX-Singer-Preprocess/
   ```

   Windows 会使用 `webrtcvad-wheels` 的预编译包，避免在包含空格的 Windows 项目路径中编译 `webrtcvad` C 扩展；它提供相同的 `webrtcvad` Python 导入名。

5. 安装完成后 Studio 会显示：

   ```text
   SERVER MODE · http://127.0.0.1:7861
   ```

### 方法二：主机手动启动

如果源码和模型已经准备好，可以在项目根目录执行：

```powershell
.\start_soulx_server.bat
```

代码升级后若旧 Server 仍占用7861，请改为执行一次：

```powershell
.\restart_soulx_server.bat
```

这个脚本只停止同一项目路径下的 SoulX 7861 进程，然后加载新版 wrapper；不会停止其他项目或其他端口的服务。

脚本会复用 `models/SoulX-Singer-main/.runtime/<电脑名称>/.venv/`，没有环境时才创建；缺少模型时才下载，然后由 Studio wrapper 启动：

```text
http://0.0.0.0:7861
```

主机本机验证：

```text
http://127.0.0.1:7861/gradio_api/info
```

必须能看到新版 `/_studio_start_svc` endpoint；旧版 `/_start_svc` 仍可兼容。日志位于：

如果看到 `CUDA error: no kernel image is available for execution on the device`，请覆盖最新 `start_soulx_server.bat` 后再次执行 `restart_soulx_server.bat`。启动器会保留模型，只把不支持当前GPU架构的旧 PyTorch CUDA 12.1 runtime 自动升级到经过验证的 CUDA 12.8 runtime。

关闭Studio里的SoulX窗口会自动请求 `/_unload_svc`。Server控制台出现 `[SoulX] models unloaded` 与显存前后数值即代表SVC和预处理模型已经释放；API进程继续在线，之后按需懒加载。

```text
logs/soulx_api.stdout.log
logs/soulx_api.stderr.log
```

旧版 wrapper 可能显示 `/lazy_start_svc`。v0.3.5-alpha.1 Client 会根据完整参数合约识别它，因此不会再阻止转换；重启新版 SoulX Server 后会恢复标准 `/_start_svc` 名称。

Studio 下次启动时会检查源码、隔离 Python、SVC checkpoint 和预处理模型。四者齐全就自动进入 Server Mode，并通过 `run_soulx_api_hidden.ps1` 静默启动，不需要在 Windows 登录时注册计划任务。

## B. 副机安装（Client Mode）

副机不需要复制 SoulX 模型，也不需要安装 SoulX Python 环境；只完成 `step1.md`，然后运行：

```powershell
.\run_h3_prompt_studio.bat
```

检测不到本机完整安装时，Studio 自动保持：

```text
CLIENT MODE · http://192.168.0.185:7861
```

副机打开 `SOULX` 后：

1. 点击 `TEST`，确认主机的 `/_start_svc` 可访问；
2. 选择 `Voice reference` 与 `Source song`；
3. 点击 `CLONE SINGING VOICE`，等待青色加载圈消失；
4. `PLAY` 验收，使用 `SAVE AS MP3` 保存，再手动把结果放入 MTV 的 `A1`。

如果主机不是 `192.168.0.185`，直接在 SoulX 窗口的 API 地址栏改成实际局域网地址，例如 `http://192.168.1.20:7861`。

副机不能反向启动已经关机的主机。主机必须保持开机，且 Windows 防火墙允许私有网络 TCP `7861`。不要把没有鉴权的 SoulX API 暴露到公网。

## C. 运行与显存注意事项

- SoulX 与 ACE-Step、ComfyUI、LM Studio 使用独立进程；转换完成后仍应先验收 MP3，再运行 H3。
- `Request server model unload after conversion` 会先探测卸载 endpoint。官方原始 WebUI 没有卸载 endpoint 时，状态栏会显示 `no unload endpoint`；这不是成功释放显存的承诺，应停止／重启 SoulX launcher。
- 本项目自带的 `soulx_server.py` 为本机 Studio 管理的服务提供 `/_unload_svc`，只有调用成功才会报告已卸载。
- Studio 主页的 `UNLOAD ALL` 不会中断进行中的转换；任务完成后才执行可用的卸载请求。

## D. 迁移到另一台主机

可复制以下项目内容到另一台主机，再运行 `start_soulx_server.bat`：

```text
models/SoulX-Singer-main/webui_svc.py
models/SoulX-Singer-main/pretrained_models/
requirements-soulx-windows.txt
start_soulx_server.bat
soulx_server.py
```

`.runtime/<电脑名称>/` 是电脑专属隔离环境；跨电脑复制时可以不复制该目录，让启动器按新电脑名称重新建立环境。新主机仍需满足严格大于 16GB VRAM，并重新通过 `SOULX` 的 Server Mode 检查。

## 官方参考

- [SoulX-Singer 官方仓库](https://github.com/Soul-AILab/SoulX-Singer)
- 返回主说明：[`README.md`](README.md)
