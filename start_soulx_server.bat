@echo off
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
set "SOULX_HOME=%~dp0models\SoulX-Singer-main"
set "SOULX_RUNTIME=%SOULX_HOME%\.runtime\%COMPUTERNAME%"
set "SOULX_VENV=%SOULX_RUNTIME%\.venv"
set "SOULX_PYTHON=%SOULX_VENV%\Scripts\python.exe"
set "SOULX_REQUIREMENTS=%~dp0requirements-soulx-windows.txt"
set "UV_PYTHON_INSTALL_DIR=%SOULX_RUNTIME%\.uv-python"
set "UV_CACHE_DIR=%SOULX_RUNTIME%\.uv-cache"
set "UV_EXE="
set "SOULX_TORCH_VERSION=2.7.1"
set "SOULX_TORCH_INDEX=https://download.pytorch.org/whl/cu128"

if not exist "%SOULX_HOME%\webui_svc.py" goto :MissingSource

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_EXE (
    for /f "delims=" %%I in ('where uv.exe 2^>nul') do if not defined UV_EXE set "UV_EXE=%%I"
)

if not exist "%SOULX_PYTHON%" goto :RepairEnvironment
:ValidateRuntime
"%SOULX_PYTHON%" -c "import torch,gradio,librosa" >nul 2>&1
if errorlevel 1 goto :RuntimeImportFailed
"%SOULX_PYTHON%" -c "import torch; assert torch.cuda.is_available(), 'CUDA is unavailable'; cap=torch.cuda.get_device_capability(0); arch='sm_%%d%%d'%%cap; builds=torch.cuda.get_arch_list(); print('[SoulX] Torch',torch.__version__,'CUDA',torch.version.cuda,'GPU',torch.cuda.get_device_name(0),'capability',arch); assert arch in builds, 'PyTorch build does not contain '+arch+'; available: '+','.join(builds); torch.zeros(1,device='cuda').add_(1); torch.cuda.synchronize()"
if errorlevel 1 goto :RepairTorch
goto :EnsureModels

:RuntimeImportFailed
if defined SOULX_ENV_REBUILT goto :SetupFailed
goto :RepairEnvironment

:RepairTorch
if defined SOULX_TORCH_REPAIRED goto :CudaIncompatible
if not defined UV_EXE goto :RepairEnvironment
set "SOULX_TORCH_REPAIRED=1"
echo [SoulX] Existing PyTorch cannot execute kernels on this GPU.
echo [SoulX] Installing PyTorch %SOULX_TORCH_VERSION% with CUDA 12.8 architecture support...
"!UV_EXE!" pip install --python "%SOULX_PYTHON%" --reinstall torch==%SOULX_TORCH_VERSION% torchaudio==%SOULX_TORCH_VERSION% --index-url %SOULX_TORCH_INDEX%
if errorlevel 1 goto :SetupFailed
goto :ValidateRuntime

:RepairEnvironment
set "SOULX_ENV_REBUILT=1"
echo [SoulX] Building the isolated Python 3.10 runtime:
echo [SoulX] %SOULX_VENV%

if not defined UV_EXE (
    echo [SoulX] uv is not installed. Installing the official uv package manager...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression"
    if errorlevel 1 goto :SetupFailed
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_EXE goto :SetupFailed
if not exist "%SOULX_REQUIREMENTS%" goto :MissingRequirements

"!UV_EXE!" python install 3.10
if errorlevel 1 goto :SetupFailed
"!UV_EXE!" venv --clear --python 3.10 "%SOULX_VENV%"
if errorlevel 1 goto :SetupFailed

"!UV_EXE!" pip install --python "%SOULX_PYTHON%" torch==%SOULX_TORCH_VERSION% torchaudio==%SOULX_TORCH_VERSION% --index-url %SOULX_TORCH_INDEX%
if errorlevel 1 goto :SetupFailed
"!UV_EXE!" pip install --python "%SOULX_PYTHON%" -r "%SOULX_REQUIREMENTS%"
if errorlevel 1 goto :SetupFailed
goto :ValidateRuntime

:EnsureModels
set "SOULX_PREPROCESS_FOUND="
for /f "delims=" %%F in ('dir /b /s "%SOULX_HOME%\pretrained_models\SoulX-Singer-Preprocess\*" 2^>nul') do if not defined SOULX_PREPROCESS_FOUND set "SOULX_PREPROCESS_FOUND=1"
if exist "%SOULX_HOME%\pretrained_models\SoulX-Singer\model-svc.pt" if defined SOULX_PREPROCESS_FOUND goto :LaunchApi

echo [SoulX] Downloading official SVC and preprocessing models...
if not exist "%SOULX_VENV%\Scripts\hf.exe" goto :SetupFailed
pushd "%SOULX_HOME%"
"%SOULX_VENV%\Scripts\hf.exe" download Soul-AILab/SoulX-Singer --local-dir pretrained_models/SoulX-Singer
if errorlevel 1 goto :SetupFailedFromHome
"%SOULX_VENV%\Scripts\hf.exe" download Soul-AILab/SoulX-Singer-Preprocess --local-dir pretrained_models/SoulX-Singer-Preprocess
if errorlevel 1 goto :SetupFailedFromHome
popd

:LaunchApi
powershell.exe -NoProfile -Command "try { $i=Invoke-RestMethod -Uri 'http://127.0.0.1:7861/gradio_api/info' -TimeoutSec 2; if (@($i.named_endpoints.PSObject.Properties.Name) -contains '/_studio_start_svc') { exit 0 }; exit 2 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [SoulX] API is already running at http://0.0.0.0:7861
    exit /b 0
)
if errorlevel 2 goto :OutdatedServer

pushd "%SOULX_HOME%"
echo [SoulX] API: http://0.0.0.0:7861
echo [SoulX] Runtime: %SOULX_VENV%
echo [SoulX] Models: %SOULX_HOME%\pretrained_models
"%SOULX_PYTHON%" "%PROJECT_ROOT%soulx_server.py" --host 0.0.0.0 --port 7861 --fp16
set "SOULX_EXIT=%ERRORLEVEL%"
popd
if not defined SOULX_NO_PAUSE pause
exit /b %SOULX_EXIT%

:SetupFailedFromHome
popd
:SetupFailed
echo.
echo [SoulX] Environment/model setup failed. Review the error above.
if not defined SOULX_NO_PAUSE pause
exit /b 1

:CudaIncompatible
echo.
echo [SoulX] CUDA validation still failed after installing the CUDA 12.8 build.
echo [SoulX] Update the NVIDIA display driver, then run restart_soulx_server.bat again.
if not defined SOULX_NO_PAUSE pause
exit /b 1

:MissingSource
echo [SoulX] Missing source: %SOULX_HOME%\webui_svc.py
if not defined SOULX_NO_PAUSE pause
exit /b 1

:MissingRequirements
echo [SoulX] Missing requirements: %SOULX_REQUIREMENTS%
if not defined SOULX_NO_PAUSE pause
exit /b 1

:OutdatedServer
echo [SoulX] An outdated or incompatible API is still occupying port 7861.
echo [SoulX] Run restart_soulx_server.bat once, then start Studio again.
if not defined SOULX_NO_PAUSE pause
exit /b 2
