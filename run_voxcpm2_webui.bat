@echo off
setlocal

set "H3_ROOT=%~dp0"
set "H3_PYTHON=%H3_ROOT%ai_libraries_common\python_env\python.exe"
set "H3_VOXCPM=%H3_ROOT%ai_libraries_common\VoxCPM-main"

if not exist "%H3_PYTHON%" (
    echo [VoxCPM2] Bundled Python was not found:
    echo %H3_PYTHON%
    pause
    exit /b 1
)

if not exist "%H3_VOXCPM%\app.py" (
    echo [VoxCPM2] app.py was not found:
    echo %H3_VOXCPM%\app.py
    pause
    exit /b 1
)

pushd "%H3_VOXCPM%"
echo [VoxCPM2] Starting local WebUI at http://127.0.0.1:8088
echo [VoxCPM2] The first model load may download the VoxCPM2 weights.
"%H3_PYTHON%" app.py --host 127.0.0.1 --port 8088 %*
set "H3_EXIT=%ERRORLEVEL%"
popd

if not "%H3_EXIT%"=="0" pause
exit /b %H3_EXIT%
