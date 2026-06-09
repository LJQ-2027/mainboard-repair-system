@echo off
chcp 65001 >nul
title AI 代理服务器 - 智能主板维修系统

echo ========================================
echo   AI 代理服务器 - 智能主板维修系统
echo ========================================
echo.

:: 检查 .env 文件
if not exist "%~dp0.env" (
    echo [WARNING] 未找到 .env 文件
    echo 请复制 .env.example 为 .env 并填入你的 ANTHROPIC_API_KEY
    echo.
)

:: 如果有 .env 则加载
if exist "%~dp0.env" (
    for /f "usebackq tokens=1,2 delims==" %%a in ("%~dp0.env") do (
        if not "%%a"=="" if not "%%a"=="#" (
            set "%%a=%%b"
        )
    )
    echo [OK] .env 文件已加载
)

:: 检查 API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo [ERROR] ANTHROPIC_API_KEY 未配置！
    echo.
    echo 请按以下步骤操作：
    echo 1. 复制 .env.example 为 .env
    echo 2. 编辑 .env 文件，填入你的 Anthropic API Key
    echo 3. 重新运行本脚本
    echo.
    pause
    exit /b 1
)

echo [OK] ANTHROPIC_API_KEY 已配置
echo.

:: 检测 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [OK] 已检测到 Python
echo.
echo ========================================
echo   启动代理服务...
echo   前端请连接: http://localhost:8899
echo ========================================
echo.
echo   按 Ctrl+C 停止服务
echo.

echo [INFO] 使用 FastAPI 后端 (v9.0)
echo   管理后台: http://localhost:8899/admin/
echo   API 文档: http://localhost:8899/docs
echo.

python "%~dp0backend/run.py"

pause
