@echo off
setlocal
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_audio_separator_cuda_runtime.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo [Audio Separator] CUDA runtime installation failed.
exit /b %RESULT%
