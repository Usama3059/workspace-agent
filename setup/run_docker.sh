#!/bin/bash
# ========================================
# Workspace Agent - Docker Run Script
# ========================================

echo ""
echo "================================================================="
echo "         WORKSPACE AI AGENT - DOCKER SCRIPT                     "
echo "================================================================="
echo ""

# ----------------------------
# Check if Docker is running
# ----------------------------
echo "[1/4] Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
echo "SUCCESS: Docker is installed"
echo ""

echo "Checking if Docker daemon is running..."
if ! docker ps &> /dev/null; then
    echo "ERROR: Docker daemon is not running"
    echo "Please start Docker and try again"
    exit 1
fi
echo "SUCCESS: Docker daemon is running"
echo ""

# ----------------------------
# Set variables
# ----------------------------
IMAGE_NAME="workspace-agent"
CONTAINER_NAME="workspace-agent-container"
PORT=8501

# ----------------------------
# Build Docker image
# ----------------------------
echo "[2/4] Building Docker image..."
echo "Building image: $IMAGE_NAME"
echo "This may take several minutes on first run..."
echo ""

if ! docker build -t "$IMAGE_NAME" .; then
    echo "ERROR: Failed to build Docker image"
    exit 1
fi
echo "SUCCESS: Docker image built successfully"
echo ""

# ----------------------------
# Stop and remove existing container
# ----------------------------
echo "[3/4] Cleaning up existing containers and ports..."
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Stopping existing container..."
    docker stop "$CONTAINER_NAME" &> /dev/null
    echo "Removing existing container..."
    docker rm "$CONTAINER_NAME" &> /dev/null
fi

# Force clean ports 8501 and 8080 if still occupied
if lsof -Pi :8501 -sTCP:LISTEN -t &> /dev/null; then
    echo "Killing process on port 8501..."
    kill -9 $(lsof -Pi :8501 -sTCP:LISTEN -t) &> /dev/null
fi
if lsof -Pi :8080 -sTCP:LISTEN -t &> /dev/null; then
    echo "Killing process on port 8080..."
    kill -9 $(lsof -Pi :8080 -sTCP:LISTEN -t) &> /dev/null
fi
echo "SUCCESS: Cleanup complete"
echo ""

# ----------------------------
# Run Docker container
# ----------------------------
echo "[4/4] Starting Docker container in detached mode..."
echo "Running container: $CONTAINER_NAME"
echo ""

# Check if .env file exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$PORT:8501" \
        -p 8080:8080 \
        --env-file .env \
        "$IMAGE_NAME"
else
    echo "WARNING: No .env file found. Running without environment variables..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$PORT:8501" \
        -p 8080:8080 \
        "$IMAGE_NAME"
fi

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start Docker container"
    exit 1
fi

# ----------------------------
# Start both interfaces
# ----------------------------
echo ""
echo "Starting both interfaces..."
echo ""

# Start Streamlit in background
echo "Opening Streamlit UI in browser..."
sleep 3

# Open browser based on OS
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:$PORT" &> /dev/null &
elif command -v open &> /dev/null; then
    open "http://localhost:$PORT" &> /dev/null &
else
    echo "Please open http://localhost:$PORT in your browser"
fi

# Launch Terminal UI inside container
echo ""
echo "Launching Terminal UI (main.py) inside container..."
echo "================================================================="
echo "                   TERMINAL INTERFACE ACTIVE                     "
echo "         (Type 'exit' to return to host machine)                 "
echo "================================================================="
echo ""
docker exec -it "$CONTAINER_NAME" python main.py

echo ""
echo "Press Enter to continue..."
read
