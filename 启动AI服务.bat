@echo off
chcp 65001 >nul
title AI 代理服务器 - 智能主板维修系统

echo ========================================
echo   AI 代理服务器 - 智能主板维修系统 v9.0
echo ========================================
echo.
echo   启动中，请稍候...

:: 启动代理（新窗口）
start "" python "%~dp0backend/run.py"

:: 等5秒让服务启动
ping -n 6 127.0.0.1 >nul

:: 打开浏览器
start "" http://localhost:8899/

echo   浏览器已打开！
echo   按任意键关闭此窗口...
pause >nul
