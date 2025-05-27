@echo off
setlocal enabledelayedexpansion

REM Loop through each line in requirements.txt
for /f "usebackq tokens=* delims=" %%A in ("requirements.txt") do (
    set "pkg=%%A"
    echo Installing: !pkg!
    python -m pip install !pkg!
    if errorlevel 1 (
        echo Failed to install !pkg!
    )
    echo.
)

echo Done installing what could be installed.
