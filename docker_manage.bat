@echo off
REM ========================================
REM Workspace Agent - Docker Management
REM ========================================

:menu
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║       🐳 WORKSPACE AGENT - DOCKER MANAGEMENT 🐳              ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo Select an option:
echo.
echo  [1] Build Docker image
echo  [2] Run container (detached mode)
echo  [3] Run container (interactive mode)
echo  [4] Stop container
echo  [5] Start existing container
echo  [6] Restart container
echo  [7] View container logs
echo  [8] View container logs (follow)
echo  [9] Execute bash in running container
echo  [10] Remove container
echo  [11] Remove image
echo  [12] Clean up (stop + remove container)
echo  [13] Full rebuild (remove image + rebuild)
echo  [14] Show container status
echo  [15] Show container resource usage
echo  [0] Exit
echo.
set /p choice="Enter your choice (0-15): "

set IMAGE_NAME=workspace-agent
set CONTAINER_NAME=workspace-agent-container

if "%choice%"=="1" goto build
if "%choice%"=="2" goto run_detached
if "%choice%"=="3" goto run_interactive
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto start
if "%choice%"=="6" goto restart
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto logs_follow
if "%choice%"=="9" goto exec_bash
if "%choice%"=="10" goto remove_container
if "%choice%"=="11" goto remove_image
if "%choice%"=="12" goto cleanup
if "%choice%"=="13" goto full_rebuild
if "%choice%"=="14" goto status
if "%choice%"=="15" goto stats
if "%choice%"=="0" goto end

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:build
echo.
echo 📦 Building Docker image: %IMAGE_NAME%
docker build -t %IMAGE_NAME% .
echo.
pause
goto menu

:run_detached
echo.
echo 🚀 Running container in detached mode...
if exist ".env" (
    docker run -d --name %CONTAINER_NAME% -p 8501:8501 -p 8080:8080 --env-file .env %IMAGE_NAME%
) else (
    docker run -d --name %CONTAINER_NAME% -p 8501:8501 -p 8080:8080 %IMAGE_NAME%
)
echo ✅ Container started: %CONTAINER_NAME%
echo 📍 Access at: http://localhost:8501
echo.
pause
goto menu

:run_interactive
echo.
echo 🚀 Running container in interactive mode...
if exist ".env" (
    docker run -it --name %CONTAINER_NAME% -p 8501:8501 -p 8080:8080 --env-file .env %IMAGE_NAME%
) else (
    docker run -it --name %CONTAINER_NAME% -p 8501:8501 -p 8080:8080 %IMAGE_NAME%
)
pause
goto menu

:stop
echo.
echo 🛑 Stopping container: %CONTAINER_NAME%
docker stop %CONTAINER_NAME%
echo.
pause
goto menu

:start
echo.
echo ▶️  Starting container: %CONTAINER_NAME%
docker start %CONTAINER_NAME%
echo ✅ Container started
echo 📍 Access at: http://localhost:8501
echo.
pause
goto menu

:restart
echo.
echo 🔄 Restarting container: %CONTAINER_NAME%
docker restart %CONTAINER_NAME%
echo.
pause
goto menu

:logs
echo.
echo 📋 Container logs:
echo ----------------------------------------
docker logs %CONTAINER_NAME%
echo.
pause
goto menu

:logs_follow
echo.
echo 📋 Following container logs (Press Ctrl+C to stop)...
echo ----------------------------------------
docker logs -f %CONTAINER_NAME%
pause
goto menu

:exec_bash
echo.
echo 💻 Opening bash shell in container...
echo Type 'exit' to return to this menu
echo.
docker exec -it %CONTAINER_NAME% /bin/bash
pause
goto menu

:remove_container
echo.
echo 🗑️  Removing container: %CONTAINER_NAME%
docker rm %CONTAINER_NAME%
echo.
pause
goto menu

:remove_image
echo.
echo 🗑️  Removing image: %IMAGE_NAME%
docker rmi %IMAGE_NAME%
echo.
pause
goto menu

:cleanup
echo.
echo 🧹 Cleaning up container...
docker stop %CONTAINER_NAME% 2>nul
docker rm %CONTAINER_NAME% 2>nul
echo ✅ Cleanup complete
echo.
pause
goto menu

:full_rebuild
echo.
echo 🔨 Full rebuild: stopping, removing, and rebuilding...
docker stop %CONTAINER_NAME% 2>nul
docker rm %CONTAINER_NAME% 2>nul
docker rmi %IMAGE_NAME% 2>nul
echo.
echo 📦 Building new image...
docker build -t %IMAGE_NAME% .
echo ✅ Rebuild complete
echo.
pause
goto menu

:status
echo.
echo 📊 Container Status:
echo ----------------------------------------
docker ps -a --filter "name=%CONTAINER_NAME%" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.
pause
goto menu

:stats
echo.
echo 📈 Container Resource Usage (Press Ctrl+C to stop):
echo ----------------------------------------
docker stats %CONTAINER_NAME%
pause
goto menu

:end
echo.
echo Goodbye! 👋
timeout /t 1 >nul
exit /b 0
