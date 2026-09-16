@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%ai_libraries_common\python_env\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ACE-Step Client] Python environment was not found:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

pushd "%PROJECT_ROOT%"
echo [ACE-Step Client] Opening http://127.0.0.1:7868
"%PYTHON_EXE%" "%PROJECT_ROOT%ace_step_webui.py" --host 127.0.0.1 --port 7868
set "CLIENT_EXIT=%ERRORLEVEL%"
popd

pause
exit /b %CLIENT_EXIT%
