@echo off
cd /d "%~dp0"
set "H3_PYTHON=%~dp0ai_libraries_common\python_env\python.exe"
if not exist "%H3_PYTHON%" (
    echo Missing H3 common runtime: %H3_PYTHON%
    echo Rebuild ai_libraries_common before launching.
    pause
    exit /b 1
)
"%H3_PYTHON%" director_cut_studio.py
if errorlevel 1 pause
