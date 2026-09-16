@echo off
setlocal
cd /d "%~dp0"
set "STUDIO_PYTHON=%~dp0ai_libraries_common\python_env\python.exe"
set "SEPARATOR_SERVICE=%~dp0vocal_separator_service.py"
set "SEPARATOR_RUNTIME=%~dp0models\audio-separator\runtime"
set "SEPARATOR_MODEL=%~dp0models\audio-separator\Kim_Vocal_2.onnx"
set "STUDIO_SITE_PACKAGES=%~dp0ai_libraries_common\python_env\Lib\site-packages"
if not exist "%STUDIO_PYTHON%" (
  echo [Audio Separator] Studio Python is missing: %STUDIO_PYTHON%
  goto :Failed
)
if not exist "%SEPARATOR_MODEL%" (
  echo [Audio Separator] Kim_Vocal_2 model is missing: %SEPARATOR_MODEL%
  goto :Failed
)

echo [Audio Separator] Validating CUDAExecutionProvider and Kim_Vocal_2...
"%STUDIO_PYTHON%" -S "%SEPARATOR_SERVICE%" --runtime "%SEPARATOR_RUNTIME%" --studio-site-packages "%STUDIO_SITE_PACKAGES%" --model "%SEPARATOR_MODEL%" --probe
if errorlevel 1 (
  echo [Audio Separator] CUDA provider is missing or incompatible.
  if exist "%SEPARATOR_RUNTIME%\onnxruntime_gpu-1.23.2.dist-info" (
    echo [Audio Separator] onnxruntime-gpu 1.23.2 is already installed; check the NVIDIA driver, CUDA DLLs, and GPU compatibility.
    goto :Failed
  )
  echo [Audio Separator] Installing CUDA runtime automatically...
  call "%~dp0install_audio_separator_cuda_runtime.bat"
  if errorlevel 1 goto :Failed
  "%STUDIO_PYTHON%" -S "%SEPARATOR_SERVICE%" --runtime "%SEPARATOR_RUNTIME%" --studio-site-packages "%STUDIO_SITE_PACKAGES%" --model "%SEPARATOR_MODEL%" --probe
  if errorlevel 1 goto :Failed
)
set "AUDIO_SEPARATOR_CUDA_PREVALIDATED=1"
echo [Audio Separator] API: http://0.0.0.0:7862
echo [Audio Separator] Model: models\audio-separator\Kim_Vocal_2.onnx
"%STUDIO_PYTHON%" "%~dp0audio_separator_server.py" --host 0.0.0.0 --port 7862
set "RESULT=%ERRORLEVEL%"
if "%AUDIO_SEPARATOR_NO_PAUSE%"=="1" exit /b %RESULT%
if not "%RESULT%"=="0" pause
exit /b %RESULT%

:Failed
if "%AUDIO_SEPARATOR_NO_PAUSE%"=="1" exit /b 1
pause
exit /b 1
endlocal
