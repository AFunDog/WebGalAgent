@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

if "%1"=="--dev" goto :dev

:: ========== 生产模式 ==========
echo === 构建前端 ===
if not exist "src\frontend\node_modules" (
    echo [1/2] 安装依赖...
    call npm install --prefix src/frontend
) else (
    echo [1/2] 依赖已存在，跳过安装
)
echo [2/2] 执行构建...
call npm run build --prefix src/frontend
if errorlevel 1 (
    echo 前端构建失败！
    pause
    exit /b 1
)
echo === 前端构建完成 ===
echo.
echo === 启动后端服务 http://127.0.0.1:8000 ===
python -m uvicorn webgal_agent.api.app:create_app --host 127.0.0.1 --port 8000 --factory
exit /b

:: ========== 开发模式 ==========
:dev
if not exist "src\frontend\node_modules" (
    echo === 安装前端依赖 ===
    call npm install --prefix src/frontend
)
echo === 启动开发模式 ===
echo   后端: http://127.0.0.1:8000  (uvicorn --reload)
echo   前端: http://localhost:5173   (Vite HMR)
echo.

start "WebGalAgent-Backend" /min python -m uvicorn webgal_agent.api.app:create_app --host 127.0.0.1 --port 8000 --factory --reload
start "WebGalAgent-Frontend" /min npm run dev --prefix src/frontend

echo 两个服务已在新窗口启动，关闭任一窗口即可停止
pause
