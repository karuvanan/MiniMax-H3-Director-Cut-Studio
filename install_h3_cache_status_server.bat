@echo off
setlocal
set "SCRIPT=%~dp0install_h3_cache_status_server.ps1"
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
) else if "%~2"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -ComfyUIRoot "%~1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" -ComfyUIRoot "%~1" -ComfyUIUrl "%~2"
)
if errorlevel 1 (
  echo [H3 Cache Status] Installation failed.
  exit /b 1
)
echo [H3 Server Status] Installation complete. Tray is running and will start with Windows.
echo [H3 Server Status] Right-click the Tray icon and open Settings... to configure refresh seconds, API IP and cache folder.
echo [H3 Server Status] Restart ComfyUI once to activate the expanded status API.
endlocal

