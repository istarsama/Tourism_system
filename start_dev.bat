@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "DRY_RUN=0"
if /I "%~1"=="--dry-run" set "DRY_RUN=1"

where uv >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 uv，请先安装后再重试。
  echo 参考: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未找到 npm，请先安装 Node.js 后再重试。
  pause
  exit /b 1
)

if not exist "%ROOT%\frontend\node_modules" (
  if "%DRY_RUN%"=="1" (
    echo [DRY-RUN] frontend\node_modules 不存在，将执行 npm install
  ) else (
    echo [INFO] 正在安装前端依赖...
    pushd "%ROOT%\frontend"
    call npm install
    if errorlevel 1 (
      echo [ERROR] 前端依赖安装失败，请检查网络或 npm 配置。
      popd
      pause
      exit /b 1
    )
    popd
  )
)

if "%DRY_RUN%"=="1" (
  echo [DRY-RUN] start "Tourism Backend" cmd /k "cd /d ""%ROOT%"" ^&^& uv run uvicorn src.api:app --reload"
  echo [DRY-RUN] start "Tourism Frontend" cmd /k "cd /d ""%ROOT%\frontend"" ^&^& npm run dev"
  echo [DRY-RUN] 检查完成。
  exit /b 0
)

echo [INFO] 正在启动后端服务...
start "Tourism Backend" cmd /k "cd /d ""%ROOT%"" && uv run uvicorn src.api:app --reload"

echo [INFO] 正在启动前端服务...
start "Tourism Frontend" cmd /k "cd /d ""%ROOT%\frontend"" && npm run dev"

echo.
echo [DONE] 已分别启动前后端窗口。
echo 关闭服务时，请在对应窗口按 Ctrl+C。

endlocal
exit /b 0
