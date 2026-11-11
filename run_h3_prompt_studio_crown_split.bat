@echo off
rem Round 34 grading launcher: same Studio as run_h3_prompt_studio.bat, but the
rem head-suppression band is split so the crown (wig / cat ears / headband) is
rem blurred AND drained of chroma while the face keeps its colour.  Everything
rem else -- policy 69, the wardrobe blur, the prompt -- is the shipped recipe.
rem Remove the variable (or set it to off) to render the stock plate again.
set "H3_CHARACTER_SWAP_HAIR_BAND_MODE=blur_desat"
cd /d "%~dp0"
set "H3_PYTHON=%~dp0ai_libraries_common\python_env\python.exe"
if not exist "%H3_PYTHON%" (
    echo Missing H3 common runtime: %H3_PYTHON%
    echo Rebuild ai_libraries_common before launching.
    pause
    exit /b 1
)
echo Crown split ON: H3_CHARACTER_SWAP_HAIR_BAND_MODE=%H3_CHARACTER_SWAP_HAIR_BAND_MODE%
"%H3_PYTHON%" director_cut_studio.py
if errorlevel 1 pause
