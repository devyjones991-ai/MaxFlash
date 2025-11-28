@echo off
chcp 65001 >nul
title Остановка MaxFlash

echo.
echo ============================================================
echo   ⏹️  ОСТАНОВКА MAXFLASH
echo ============================================================
echo.

cd /d "%~dp0"

echo Поиск процессов Python...
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq MaxFlash*" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Найдены процессы Python с MaxFlash
    taskkill /FI "WINDOWTITLE eq MaxFlash*" /F >nul 2>&1
)

echo Поиск процессов на порту 8050...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8050 ^| findstr LISTENING') do (
    echo Остановка процесса %%a...
    taskkill /PID %%a /F >nul 2>&1
)

echo Поиск процессов pythonw...
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Найдены фоновые процессы Python...
    for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO CSV ^| findstr pythonw') do (
        wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr start.py >nul
        if !ERRORLEVEL! EQU 0 (
            echo Остановка процесса %%a...
            taskkill /PID %%a /F >nul 2>&1
        )
    )
)

timeout /t 2 /nobreak >nul

echo.
echo ✅ Процессы остановлены
echo.
pause
