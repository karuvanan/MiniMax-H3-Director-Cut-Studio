@echo off
setlocal
set "PROJECT_ROOT=%~dp0"
set "STUDIO_PYTHON=%PROJECT_ROOT%ai_libraries_common\python_env\python.exe"
set "QWEN_RUNTIME=%PROJECT_ROOT%ai_libraries_common\qwen_tts_runtime"
set "QWEN_REQUIREMENTS=%PROJECT_ROOT%requirements-qwen3-tts.txt"
set "SOX_ZIP=%PROJECT_ROOT%ai_libraries_common\sox-14.4.2-win32.zip"
set "SOX_ROOT=%PROJECT_ROOT%ai_libraries_common\qwen_tts_support"
set "SOX_EXE=%SOX_ROOT%\sox-14.4.2\sox.exe"

if not exist "%STUDIO_PYTHON%" (
  echo ERROR: bundled Studio Python was not found:
  echo %STUDIO_PYTHON%
  exit /b 1
)

if not exist "%QWEN_REQUIREMENTS%" (
  echo ERROR: Qwen3-TTS requirements file was not found:
  echo %QWEN_REQUIREMENTS%
  exit /b 1
)

if not exist "%SOX_EXE%" (
  echo Downloading the official SoX 14.4.2 Windows runtime required by qwen-tts.
  curl.exe -L "https://downloads.sourceforge.net/project/sox/sox/14.4.2/sox-14.4.2-win32.zip" -o "%SOX_ZIP%"
  if errorlevel 1 exit /b 1
  powershell.exe -NoProfile -NonInteractive -Command "$actual=(Get-FileHash -LiteralPath '%SOX_ZIP%' -Algorithm SHA1).Hash; if($actual -ne '825B218C275687A38E96BF838DCFDD2E9BD55A25'){Write-Error ('Unexpected SoX SHA1: '+$actual); exit 1}; Expand-Archive -LiteralPath '%SOX_ZIP%' -DestinationPath '%SOX_ROOT%' -Force"
  if errorlevel 1 exit /b 1
)

echo Installing the isolated Qwen3-TTS runtime. Existing BLIP/Vox packages will not be changed.
"%STUDIO_PYTHON%" -m pip install --upgrade --force-reinstall --no-cache-dir --target "%QWEN_RUNTIME%" --no-deps -r "%QWEN_REQUIREMENTS%"
if errorlevel 1 exit /b 1

icacls "%QWEN_RUNTIME%" /inheritance:e /grant:r "%USERNAME%:(OI)(CI)F" /T /C /Q
if errorlevel 1 exit /b 1
icacls "%SOX_ROOT%" /inheritance:e /grant:r "%USERNAME%:(OI)(CI)F" /T /C /Q
if errorlevel 1 exit /b 1

"%STUDIO_PYTHON%" "%PROJECT_ROOT%qwen3_tts_setup.py" verify
if errorlevel 2 (
  echo Runtime installation succeeded. The model is intentionally separate.
  echo Run download_qwen3_tts_model.bat or copy the model folder from another computer.
  exit /b 0
)
exit /b %errorlevel%
