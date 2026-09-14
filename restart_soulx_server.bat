@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "SOULX_NO_PAUSE=1"

echo [SoulX] Checking port 7861 for an outdated Studio-managed server...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%stop_soulx_server.ps1" -ProjectRoot "%PROJECT_ROOT%." -Port 7861 -WaitSeconds 20
if errorlevel 1 goto :StopFailed

call "%PROJECT_ROOT%start_soulx_server.bat"
exit /b %ERRORLEVEL%

:StopFailed
echo [SoulX] Could not safely release port 7861.
echo [SoulX] Review the PID and process information above. If it is unrelated,
echo [SoulX] close that application manually; otherwise close the old SoulX console.
pause
exit /b 1
