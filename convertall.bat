@echo off
setlocal enabledelayedexpansion

set "scriptdir=%~dp0"
set "inputdir=%scriptdir%InputFiles"
set "requirements=%scriptdir%requirements.txt"

echo Installing dependencies from %requirements%...
pip install -r "%requirements%"

echo.
echo Dependencies installed.
echo Processing JSON files...

for %%F in ("%inputdir%\*.json") do (
    set "filename=%%~nxF"
    echo Processing file: !filename!
    call python "%scriptdir%convert_single_file.py" "!filename!"
)

echo.
echo All JSON files processed. Press any key to exit...
pause > nul

endlocal