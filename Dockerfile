

FROM python:3.11-slim

# ----------------------------
# System dependencies
# ----------------------------
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ----------------------------
# Install uv
# ----------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# uv may land in /root/.local/bin OR /root/.cargo/bin depending on environment
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# Verify uv is available
RUN uv --version

# ----------------------------
# Clone MCP server
# ----------------------------
RUN git clone https://github.com/taylorwilsdon/google_workspace_mcp /app/mcp-server

# ----------------------------
# Copy your app code
# ----------------------------
COPY . /app

# ----------------------------
# Create venv + install deps with uv
# ----------------------------
RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:/root/.local/bin:/root/.cargo/bin:${PATH}"

# Install Streamlit app deps (prefer requirements.txt if present)
RUN if [ -f "/app/requirements.txt" ]; then \
      uv pip install -r /app/requirements.txt; \
    else \
      uv pip install \
        "pydantic>=2.0" \
        streamlit \
        python-dotenv \
        pyyaml \
        openai \
        langchain-core \
        langchain-deepseek \
        deepagents \
        mcp \
        langchain-mcp-adapters \
        langchain-openai \
        langchain-google-genai \
        langchain-anthropic \
        rich; \
    fi

# Install MCP server deps
RUN if [ -f "/app/mcp-server/requirements.txt" ]; then \
      uv pip install -r /app/mcp-server/requirements.txt; \
    else \
      uv pip install \
        fastapi uvicorn \
        google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client; \
    fi

# Editable install if pyproject exists
RUN if [ -f "/app/pyproject.toml" ]; then \
      uv pip install -e /app; \
    fi

# ----------------------------
# Environment
# ----------------------------
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_SERVER_PATH=/app/mcp-server

ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501 8080

# IMPORTANT: change app.py if your streamlit entry file differs
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
