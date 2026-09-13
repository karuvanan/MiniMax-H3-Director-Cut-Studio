@echo off
setlocal enabledelayedexpansion

set "ACE_STEP_HOME=%~dp0models\ACE-Step-1.5"
set "ACE_STEP_RUNTIME=%ACE_STEP_HOME%\.runtime\%COMPUTERNAME%"
set "ACE_STEP_VENV=%ACE_STEP_RUNTIME%\.venv"
set "ACE_STEP_PYTHON=%ACE_STEP_VENV%\Scripts\python.exe"
set "UV_PROJECT_ENVIRONMENT=%ACE_STEP_VENV%"
set "UV_PYTHON_INSTALL_DIR=%ACE_STEP_RUNTIME%\.uv-python"
set "UV_CACHE_DIR=%ACE_STEP_RUNTIME%\.uv-cache"
set "UV_EXE="

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)
if not defined UV_EXE (
    for /f "delims=" %%I in ('where uv.exe 2^>nul') do if not defined UV_EXE set "UV_EXE=%%I"
)

if not exist "%ACE_STEP_PYTHON%" goto :RepairEnvironment
"%ACE_STEP_PYTHON%" -c "import sys" >nul 2>&1
if errorlevel 1 goto :RepairEnvironment
goto :LaunchApi

:RepairEnvironment
echo [ACE-Step] The Python environment is missing or belongs to another drive.
echo [ACE-Step] Rebuilding it in: %ACE_STEP_VENV%
echo.

if not defined UV_EXE (
    echo [ACE-Step] uv is not installed. Installing the official uv package manager...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression"
    if errorlevel 1 goto :SetupFailed
    if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)

if not defined UV_EXE goto :SetupFailed

pushd "%ACE_STEP_HOME%"
"!UV_EXE!" python install 3.12
if errorlevel 1 goto :SetupFailedFromHome

"!UV_EXE!" venv --clear --python 3.12 "%ACE_STEP_VENV%"
if errorlevel 1 goto :SetupFailedFromHome

"!UV_EXE!" sync
if errorlevel 1 goto :SetupFailedFromHome
popd

if not exist "%ACE_STEP_PYTHON%" goto :SetupFailed
echo [ACE-Step] Environment rebuild completed.
echo.

:LaunchApi

set "ACESTEP_CHECKPOINTS_DIR=%ACE_STEP_HOME%\checkpoints"
set "ACESTEP_CONFIG_PATH=acestep-v15-turbo"
set "ACESTEP_INIT_LLM=true"
set "ACESTEP_LM_MODEL_PATH=acestep-5Hz-lm-1.7B"
set "ACESTEP_DOWNLOAD_SOURCE=huggingface"
set "ACESTEP_ON_DEMAND_MODEL_LOAD=true"
set "ACESTEP_QUEUE_WORKERS=1"
set "ACESTEP_API_WORKERS=1"

powershell.exe -NoProfile -Command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:8001/health' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [ACE-Step] API is already running at http://0.0.0.0:8001
    exit /b 0
)

pushd "%ACE_STEP_HOME%"
echo [ACE-Step] API: http://0.0.0.0:8001
echo [ACE-Step] Models: %ACESTEP_CHECKPOINTS_DIR%
echo [ACE-Step] First launch downloads the required model files.
echo.

"%ACE_STEP_PYTHON%" -m acestep.api_server --host 0.0.0.0 --port 8001
set "ACE_STEP_EXIT=%ERRORLEVEL%"

popd
if not defined ACE_STEP_NO_PAUSE pause
exit /b %ACE_STEP_EXIT%

:SetupFailedFromHome
popd

:SetupFailed
echo.
echo [ACE-Step] Environment setup failed. Review the error above.
if not defined ACE_STEP_NO_PAUSE pause
exit /b 1
