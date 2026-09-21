@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || goto :nopython

echo Running tests...
%PY% -m unittest discover -s tests || goto :fail

echo.
echo Running AmanAccess...
%PY% run_demo.py --export-sample sample_data || goto :fail

echo.
echo Opening the dashboard...
start "" "results\dashboard.html"
echo Done. Results are in the results folder.
pause
exit /b 0

:nopython
echo.
echo Python was not found. Install Python 3.12 from python.org and tick "Add python.exe to PATH", then run this file again.
pause
exit /b 1

:fail
echo.
echo Something failed. Copy the message above and send it to Claude.
pause
exit /b 1
