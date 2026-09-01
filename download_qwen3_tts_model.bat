@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
set "STUDIO_PYTHON=%PROJECT_ROOT%ai_libraries_common\python_env\python.exe"

if not exist "%STUDIO_PYTHON%" (
  echo ERROR: bundled Studio Python was not found.
  exit /b 1
)

"%STUDIO_PYTHON%" "%PROJECT_ROOT%qwen3_tts_setup.py" download-model
exit /b %errorlevel%
