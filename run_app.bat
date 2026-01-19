@echo off
REM ========================================
REM Workspace Agent - Run Script
REM ========================================

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║         🚀 WORKSPACE AI AGENT - STARTUP SCRIPT 🚀            ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM ----------------------------
REM 1. Check if uv is installed
REM ----------------------------
echo [1/6] Checking for uv installation...
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ uv is not installed. Installing uv...
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo ❌ Failed to install uv. Please install manually from https://docs.astral.sh/uv/
        pause
        exit /b 1
    )
    echo ✅ uv installed successfully
) else (
    echo ✅ uv is already installed
)
echo.

REM ----------------------------
REM 2. Clone MCP server if needed
REM ----------------------------
echo [2/6] Checking for MCP server...
if not exist "mcp-server" (
    echo ⬇️  Cloning Google Workspace MCP server...
    git clone https://github.com/taylorwilsdon/google_workspace_mcp mcp-server
    if %errorlevel% neq 0 (
        echo ❌ Failed to clone MCP server. Please check your internet connection.
        pause
        exit /b 1
    )
    echo ✅ MCP server cloned successfully
) else (
    echo ✅ MCP server already exists
)
echo.

REM ----------------------------
REM 3. Create virtual environment
REM ----------------------------
echo [3/6] Setting up virtual environment...
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    uv venv .venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment already exists
)
echo.

REM ----------------------------
REM 4. Activate virtual environment
REM ----------------------------
echo [4/6] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment activated
echo.

REM ----------------------------
REM 5. Install dependencies
REM ----------------------------
echo [5/6] Installing dependencies...

REM Install main app dependencies
if exist "requirements.txt" (
    echo 📦 Installing from requirements.txt...
    uv pip install -r requirements.txt
) else (
    echo 📦 Installing default dependencies...
    uv pip install streamlit python-dotenv openai pydantic langchain-core langchain-deepseek deepagents mcp langchain-mcp-adapters
)

REM Install MCP server dependencies
if exist "mcp-server\requirements.txt" (
    echo 📦 Installing MCP server dependencies from requirements.txt...
    uv pip install -r mcp-server\requirements.txt
) else (
    echo 📦 Installing default MCP server dependencies...
    uv pip install fastapi uvicorn google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
)

REM Install project in editable mode if pyproject.toml exists
if exist "pyproject.toml" (
    echo 📦 Installing project in editable mode...
    uv pip install -e .
)

echo ✅ All dependencies installed
echo.

REM ----------------------------
REM 6. Set environment variables
REM ----------------------------
echo [6/6] Setting environment variables...
set PYTHONUNBUFFERED=1
set PYTHONDONTWRITEBYTECODE=1
set MCP_SERVER_PATH=%CD%\mcp-server
echo ✅ Environment variables set
echo.

REM ----------------------------
REM 7. Run both applications
REM ----------------------------
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                    🎯 STARTING APPLICATIONS                   ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Check if app.py exists for Streamlit
if exist "app.py" (
    echo 🌐 Starting Streamlit UI in background...
    start "Streamlit UI" cmd /k "call .venv\Scripts\activate.bat && streamlit run app.py --server.address=0.0.0.0 --server.port=8501"
    echo ✅ Streamlit UI started at: http://localhost:8501
    timeout /t 3 >nul
) else (
    echo ⚠️  app.py not found, skipping Streamlit UI
)

REM Check if main.py exists for Terminal UI
if exist "main.py" (
    echo.
    echo 💻 Starting Terminal UI (main.py)...
    echo ╔═══════════════════════════════════════════════════════════════╗
    echo ║                   TERMINAL INTERFACE ACTIVE                   ║
    echo ╚═══════════════════════════════════════════════════════════════╝
    echo.
    python main.py
) else (
    echo ❌ main.py not found. Cannot start terminal interface.
    pause
    exit /b 1
)

pause
