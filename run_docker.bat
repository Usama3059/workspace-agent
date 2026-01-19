@echo off
REM ========================================
REM Workspace Agent - Docker Run Script
REM ========================================

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║         🐳 WORKSPACE AI AGENT - DOCKER SCRIPT 🐳             ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM ----------------------------
REM Check if Docker is running
REM ----------------------------
echo [1/4] Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✅ Docker is installed
echo.

echo Checking if Docker daemon is running...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker daemon is not running
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)
echo ✅ Docker daemon is running
echo.

REM ----------------------------
REM Set variables
REM ----------------------------
set IMAGE_NAME=workspace-agent
set CONTAINER_NAME=workspace-agent-container
set PORT=8501

REM ----------------------------
REM Build Docker image
REM ----------------------------
echo [2/4] Building Docker image...
echo 📦 Building image: %IMAGE_NAME%
echo This may take several minutes on first run...
echo.

docker build -t %IMAGE_NAME% .
if %errorlevel% neq 0 (
    echo ❌ Failed to build Docker image
    pause
    exit /b 1
)
echo ✅ Docker image built successfully
echo.

REM ----------------------------
REM Stop and remove existing container
REM ----------------------------
echo [3/4] Cleaning up existing containers and ports...
docker ps -a | findstr %CONTAINER_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo 🧹 Stopping existing container...
    docker stop %CONTAINER_NAME% >nul 2>&1
    echo 🗑️  Removing existing container...
    docker rm %CONTAINER_NAME% >nul 2>&1
)

REM Force clean ports 8501 and 8080 if still occupied
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /c:":8501" ^| findstr /i "LISTENING"') do (
    echo 🗡️ Killing process on port 8501...
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /c:":8080" ^| findstr /i "LISTENING"') do (
    echo 🗡️ Killing process on port 8080...
    taskkill /F /PID %%a >nul 2>&1
)
echo ✅ Cleanup complete
echo.

REM ----------------------------
REM Run Docker container
REM ----------------------------
echo [4/4] Starting Docker container in detached mode...
echo 🚀 Running container: %CONTAINER_NAME%
echo.

REM Check if .env file exists
if exist ".env" (
    echo 📄 Loading environment variables from .env file...
    docker run -d ^
        --name %CONTAINER_NAME% ^
        -p %PORT%:8501 ^
        -p 8080:8080 ^
        --env-file .env ^
        %IMAGE_NAME%
) else (
    echo ⚠️  No .env file found. Running without environment variables...
    docker run -d ^
        --name %CONTAINER_NAME% ^
        -p %PORT%:8501 ^
        -p 8080:8080 ^
        %IMAGE_NAME%
)

if %errorlevel% neq 0 (
    echo ❌ Failed to start Docker container
    pause
    exit /b 1
)

REM ----------------------------
REM Start both interfaces
REM ----------------------------
echo.
echo 🎯 Starting both interfaces...
echo.

REM Start Streamlit in background
echo 🌐 Opening Streamlit UI in browser...
timeout /t 3 >nul
start http://localhost:%PORT%

REM Launch Terminal UI inside container
echo.
echo 💻 Launching Terminal UI (main.py) inside container...
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                   TERMINAL INTERFACE ACTIVE                   ║
echo ║         (Type 'exit' to return to host machine)               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
docker exec -it %CONTAINER_NAME% python main.py

pause
