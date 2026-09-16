# Step 4：Audio Separator / Kim_Vocal_2 主机／副机部署

`AUDIO SEPARATOR` 是独立的人声／伴奏分离工作区。它通过 Kim_Vocal_2 把一份完整歌曲明确拆成 `Vocal`、`Music` 与未经改变的 `Mix`，完成后可分别试听、停止和下载；只有点击 `ADD TO A1 & A2`，Studio 才会执行 `Music→A1`、`Vocal→A2`。它不会因为载入歌曲或选择 MTV Skill 而静默分离。

## 先决定哪台电脑是主机

主机负责运行 Kim_Vocal_2 CUDA 模型与 API，例如：

```text
http://192.168.0.185:7862
```

| 电脑 | 需要安装的内容 | Studio 模式 |
|---|---|---|
| 主机 | NVIDIA CUDA GPU、完整 `models/audio-separator`、Kim_Vocal_2 模型及 GPU runtime | `SERVER MODE`，本机连接 `http://127.0.0.1:7862` |
| 副机 | 只完成 Step 1，不复制模型，不安装 ONNX Runtime | `CLIENT MODE`，连接主机局域网地址 |

所有电脑都必须先完成 [`Step 1：Studio Runtime`](step1.md)。API 没有公网鉴权，只应在可信任的私人局域网内使用，不要把 `7862` 直接暴露到互联网。

## A. 主机安装

### 1. 准备模型目录

把完整 Audio Separator 模型目录放在项目根目录下：

```text
models/audio-separator/
├─ Kim_Vocal_2.onnx
├─ download_checks.json
├─ mdx_model_data.json
├─ vr_model_data.json
└─ requirements.txt
```

`Kim_Vocal_2.onnx` 和 runtime 不随源码仓库分发。备份或迁移主机时，应备份整个 `models/audio-separator`，而不是只备份一个 ONNX 文件。

### 2. 安装并验证 CUDA runtime

在项目根目录运行：

```powershell
.\install_audio_separator_cuda_runtime.bat
```

安装器会准备隔离 runtime，把旧的 CPU `onnxruntime` 修复为 `onnxruntime-gpu 1.23.2`，并用真实 `Kim_Vocal_2.onnx` 建立 Session。只有健康检查明确返回 `CUDAExecutionProvider`，Studio 才会启用 `SEPARATE AUDIO`；CUDA 失败时不会静默转用 CPU。

### 3. 第一次手动启动与防火墙检查

```powershell
.\start_audio_separator_server.bat
```

服务监听：

```text
http://0.0.0.0:7862
```

Windows 防火墙询问时，只允许私人网络。主机本机可在 PowerShell 验证：

```powershell
Invoke-RestMethod http://127.0.0.1:7862/health | ConvertTo-Json -Depth 8
```

验收重点：

```text
ready: true
provider: CUDAExecutionProvider
```

验证完成后可以关闭这次手动启动的 CMD。以后从 Studio 点击 `AUDIO SEPARATOR` 时，本机完整安装会自动进入 `SERVER MODE`，并隐藏启动 `127.0.0.1:7862`，无需长期保留 BAT 窗口。

## B. 副机安装（Client Mode）

副机只需完成 [`step1.md`](step1.md)，不需要复制 `Kim_Vocal_2.onnx`，也不需要安装 `audio-separator` 或 `onnxruntime-gpu`。

1. 确认主机已经开机，而且 Audio Separator API 正在运行。
2. 在副机 PowerShell 测试主机：

   ```powershell
   Invoke-RestMethod http://192.168.0.185:7862/health | ConvertTo-Json -Depth 8
   ```

3. 启动 Studio，点击主页 `AUDIO SEPARATOR`。
4. 没有本机完整安装时，窗口会显示 `CLIENT MODE`，默认连接 `http://192.168.0.185:7862`。
5. 如果主机 IP 不同，直接在 API 地址栏改成实际地址，例如 `http://192.168.1.20:7862`，然后点击 `TEST`。

副机不能远程唤醒已经关机的主机。连接失败时，先在主机运行健康检查，再确认 Windows 防火墙允许私人网络 TCP `7862`。

## C. 日常分离流程

1. 点击 `SELECT AUDIO`，选择完整歌曲。
2. 点击 `SEPARATE AUDIO`。处理期间不要重复提交。
3. 完成后先分别试听 `Vocal`、`Music` 与 `Mix`：每一行都提供 `PLAY`、`STOP` 与下载按钮。
4. 确认 Vocal 有可听见的人声、Music 是伴奏、Mix 与上传母带一致。
5. 需要交给 MTV 工作流时才点击 `ADD TO A1 & A2`。

固定映射如下：

- `Music → A1`：提供伴奏、节拍、旋律及剪辑时序；
- `Vocal → A2`：只驱动 P1 的真实演唱区间、嘴形、下颌、呼吸与表情；
- `Mix → Project final master`：保留为未经改变的最终歌曲母带。

手动替换 A1 或 A2 会取消旧 Mix 绑定，避免上一首歌的母带污染新影片。

## D. 模型、进程与显存生命周期

- 每次分离由独立的一次性 CUDA worker 执行；三份输出写盘后 worker 自动结束并释放 Kim 模型显存。
- 本机 `SERVER MODE` 关闭 Audio Separator 窗口时，会停止本项目拥有的 7862 API 与残留 worker。
- `CLIENT MODE` 关闭窗口只断开当前副机，不会停止远端共用 Server。
- 如果由 `start_audio_separator_server.bat` 手动启动，关闭该 CMD 会停止手动服务；下一次从主机 Studio 打开窗口时可重新自动启动。

因此，正常使用 Studio 自动模式时不需要一直打开 `start_audio_separator_server.bat`。

## E. 输出 QC 与 alpha.3 修正

v0.3.5-alpha.3 在成功返回前检查 Vocal 与 Music 的：

- 实际时长；
- 声道数；
- RMS 音量；
- 峰值音量。

两条 Stem 的时长或声道不一致会直接失败；Vocal 接近静音时会显示警告，不能只凭“文件已经生成”判断成功。

本版本同时修复两个会产生假成功的错误：

1. 中文、繁体中文、日文等文件名不再写入只接受 Latin-1 的 HTTP Header，改用 UTF-8 百分号编码参数传送。
2. 上游 `audio-separator 0.30.2` 的 SoundFile 分支不再把双声道浮点 Vocal 扁平化为双倍时长、近乎全零的单声道文件；现在按 samples×channels 浮点 PCM 写出。

旧版已经生成的无声 Vocal 无法就地修复，必须更新到 alpha.3 后重新执行分离。

## F. 常见问题

### 显示 CPUExecutionProvider 或按钮保持禁用

不要继续生成。先在主机重新执行：

```powershell
.\install_audio_separator_cuda_runtime.bat
```

然后确认 NVIDIA 驱动正常，并再次检查 `/health`。只有 `CUDAExecutionProvider` 才是合格的 Server Mode。

### 副机无法连接 `192.168.0.185:7862`

依序检查主机是否开机、API 是否运行、IP 是否改变、Windows 防火墙是否允许私人网络 TCP `7862`，并从副机执行 `/health` 测试。不要先重装副机模型；Client Mode 本来就不需要模型。

### 中文文件名出现 Latin-1 错误

这是旧版 Client。主机与副机都需要更新到 v0.3.5-alpha.3，并重新启动 Studio。无需改成英文文件名来绕过。

### Vocal 文件存在但完全没有声音

先查看窗口显示的 Vocal 时长、声道、RMS 和峰值。如果旧输出是双倍时长单声道并接近 `-90 dBFS`，属于已修复的 SoundFile 写出错误，请用 alpha.3 重新分离。若新版只显示 near-silent warning，原曲可能确实没有清晰主唱；应先试听确认，不要直接加入 A2。

### 端口 7862 已被占用

先关闭 Audio Separator 窗口及手动 BAT。仍被本项目旧进程占用时，在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_audio_separator_server.ps1 -ProjectRoot "$PWD" -Port 7862 -WaitSeconds 20
```

脚本只应停止本项目拥有的服务；不要强制结束来源不明的同端口程序。

## G. 迁移到另一台主机

1. 把完整项目代码复制或更新到新主机。
2. 复制整个 `models/audio-separator`，包括 Kim 模型、模型资料 JSON 与 requirements。
3. 不必复制旧电脑生成的 runtime；在新主机执行 `install_audio_separator_cuda_runtime.bat`，让它按新 GPU 建立并验证环境。
4. 运行 `start_audio_separator_server.bat`，确认 `/health` 返回 CUDA Provider。
5. 在副机把 API 地址改成新主机的局域网 IP。

## 部署验收清单

- [ ] 主机 `/health` 返回 `ready: true` 与 `CUDAExecutionProvider`。
- [ ] 中文文件名的歌曲可正常上传。
- [ ] 用一段已知有人声的 10–20 秒音频测试。
- [ ] Vocal 与 Music 时长一致、声道一致，Vocal 可听见人声。
- [ ] Vocal、Music、Mix 三行都能 Play／Stop／Download。
- [ ] `ADD TO A1 & A2` 后确认 Music 在 A1、Vocal 在 A2。
- [ ] 关闭本机窗口后 7862 与一次性 worker 能按模式正确释放。

返回主说明：[`README.md`](README.md) · 返回 v0.3.5 重点功能：[`v0.3.5 readme.md`](v0.3.5%20readme.md)
