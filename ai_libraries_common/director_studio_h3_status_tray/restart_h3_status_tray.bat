@echo off
setlocal
rem Relaunch helper for the tray menu's "Restart Tray" item. The tray releases its mutex a moment after
rem the menu click, and a second instance would otherwise exit(0) silently, so wait ~2s before relaunching.
ping -n 3 127.0.0.1 >nul
call "%~dp0start_h3_status_tray.bat" %*
endlocal
