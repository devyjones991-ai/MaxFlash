@echo off
chcp 65001 >nul
echo Остановка MaxFlash Trading System...
echo.

docker-compose -f infra/docker-compose.yml down

echo.
echo Система остановлена.
pause

