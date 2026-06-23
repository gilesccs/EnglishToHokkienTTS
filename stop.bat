@echo off
REM Stop the HokkienTTS chat app. Double-click, or run in PowerShell/cmd:  .\stop.bat
set _found=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "127.0.0.1:7860" ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo Stopped chat app ^(PID %%a^).
    set _found=1
)
if "%_found%"=="0" echo Chat app is not running.
