@echo off
chcp 65001 >nul
title AI 代理服务器 - 智能主板维修系统

echo ========================================
echo   AI 代理服务器 - 智能主板维修系统 v9.0
echo ========================================
echo.
echo   启动后请打开浏览器访问:
echo   http://localhost:8899/
echo.
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

cd /d "%~dp0backend"
python run.py

pause
