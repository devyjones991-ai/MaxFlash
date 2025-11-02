@echo off
echo Opening MaxFlash Modern Interface Demo...
cd /d %~dp0
start "" "demo_modern.html"
echo.
echo Dashboard opened in browser!
echo Close this window when done.
timeout /t 3 >nul

