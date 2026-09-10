@echo off
REM ===========================================================
REM  Inglemoor football - local preview
REM
REM  Double-click this to see the site exactly as it will look
REM  online, before you commit anything.
REM
REM  A black window opens and stays open. That is the little web
REM  server. Close it when you are finished.
REM ===========================================================

title Inglemoor football - preview server
cd /d "%~dp0"

echo.
echo   Starting the preview...
echo.

REM find Python, however it is installed
set PY=
where py >nul 2>nul && set PY=py
if "%PY%"=="" (where python >nul 2>nul && set PY=python)

if "%PY%"=="" (
  echo   Python was not found on this computer.
  echo.
  echo   Install it from https://www.python.org/downloads/
  echo   and tick "Add Python to PATH" during setup.
  echo.
  pause
  exit /b 1
)

start "" http://localhost:8000/

echo   ===========================================================
echo.
echo     The site is now at:   http://localhost:8000/
echo     The admin page is at: http://localhost:8000/admin.html
echo.
echo     Your browser should have opened already.
echo.
echo     KEEP THIS WINDOW OPEN while you look around.
echo     Close it when you are done.
echo.
echo   ===========================================================
echo.

%PY% -m http.server 8000

echo.
echo   Preview stopped.
pause
