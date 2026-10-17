@echo off
setlocal
set "CONFIG=%~dp0tray-settings.json"
if not "%~1"=="" set "CONFIG=%~1"
start "" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0h3_status_tray.ps1" -ConfigPath "%CONFIG%"
endlocal
