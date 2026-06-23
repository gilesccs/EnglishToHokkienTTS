@echo off
REM Start the HokkienTTS chat app. Double-click this file, or run it in PowerShell/cmd:
REM   .\run.bat
cd /d "%~dp0"
set PYTHONUTF8=1

REM If an instance is already on port 7860, stop it first so the port is free.
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "127.0.0.1:7860" ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo.
echo Starting HokkienTTS chat app in a new window...
echo It loads + warms up (~20-30s), then shows: Running on local URL  http://127.0.0.1:7860
echo Open that link in your browser. Close the app window (or run stop.bat) to stop it.
echo.

start "HokkienTTS Chat App" omnivoice_env\Scripts\python.exe chat_app.py
