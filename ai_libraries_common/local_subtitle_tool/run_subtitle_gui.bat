@echo off
setlocal
set "TOOL_DIR=%~dp0"
set "PYTHON=%TOOL_DIR%..\python_env\python.exe"
if not exist "%PYTHON%" set "PYTHON=%TOOL_DIR%..\Python313\python.exe"
if not exist "%PYTHON%" set "PYTHON=py"
"%PYTHON%" "%TOOL_DIR%subtitle_gui.py"
if errorlevel 1 pause
