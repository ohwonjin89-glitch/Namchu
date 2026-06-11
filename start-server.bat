@echo off
title Suno API 서버
echo.
echo  ====================================
echo   Suno API 서버 시작 중...
echo   주소: http://localhost:3000
echo   종료하려면 이 창을 닫으세요.
echo  ====================================
echo.
cd /d "C:\suno-api"
node node_modules/next/dist/bin/next dev
pause
