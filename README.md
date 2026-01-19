# Workspace AI Agent: The Autonomous Assistant That Gets Things Done

## 🚀 What if your AI assistant could actually DO things for you?

Most AI chatbots just... talk. They answer questions, write emails, brainstorm ideas. That's helpful, but it's only half the battle.
I wanted more. So I built it.
Introducing **Workspace AI Agent**—an intelligent assistant that doesn't just tell you what to do, it **does it for you**.

### Here's what makes it different:

✅ **It takes action** → Creates Google Docs, schedules Calendar meetings, searches Gmail, builds Slides presentations, manages Tasks, organizes Drive files, updates Sheets—all from a simple conversation  
✅ **100+ tools at its fingertips** → From Google Workspace to local computer control (file management, system commands, data processing)  
✅ **It controls your computer** → Rename 500 files? Run data transformation scripts? It handles terminal commands seamlessly  
✅ **It remembers** → Learns your preferences and builds a personalized memory of how you work  
✅ **It's adaptive** → Routes simple questions to a fast assistant, complex tasks to a powerful agent with full tool access  
✅ **It automates workflows** → Set daily routines like "summarize unread emails at 9 AM" and let it run in the background  
✅ **It learns from mistakes** → Saves solutions to past errors, continuously improving its execution

### The Vision:

Fully autonomous Agent capabilities (like Claude Code etc), but for your entire workspace.
Imagine an AI that:

- Orchestrates complex multi-step workflows across apps
- Proactively manages your productivity stack
- Executes sophisticated automation without you writing code

_Coming soon: Asana, Jira, and deeper workspace automation._

### Why does this matter?

We're entering an era where AI doesn't just advise—it executes.

- "Find client emails from last month, create a summary doc, add action items to Tasks" → **Done in 60 seconds.**
- "Schedule a team sync, send invites, create a meeting agenda" → **Handled automatically.**
- "Analyze my Drive, organize by project, create a status report in Slides" → **Complete.**
- "Scan CSVs, merge data, generate a formatted Sheet with charts" → **Executed instantly.**

This isn't science fiction. It's what I've been building—and it works.

### What's next?

Expanding to cover the full productivity stack—Google Workspace, project management (Asana, Jira), local environments, and beyond.
The goal? An AI agent that operates across your digital workspace like a seasoned executive assistant—but faster, smarter, and tireless.

Are you ready for assistants that take real action across 100+ tools?
Because that future is already here. 🚀

---

## Prerequisites

- **Python**: Version 3.11 or higher is required.
- **uv**: An extremely fast Python package installer and resolver.

## Setup Guide

### 1. Install `uv`

If you haven't installed `uv` yet, you can obtain it via pip (or check [astral.sh/uv](https://astral.sh/uv) for other installation methods):

```bash
pip install uv
```

### 2. Initialize Environment

Sync the project dependencies to create a locked virtual environment:

```bash
uv sync
```

### 3. Activate Virtual Environment

You need to activate the virtual environment to work within it:

- **Windows**:
  ```powershell
  .venv\Scripts\activate
  ```
- **macOS/Linux**:
  ```bash
  source .venv/bin/activate
  ```

### 4. Configuration

Create your local environment configuration file:

1.  Copy the example template:
    - **Windows**: `copy .env.example .env`
    - **macOS/Linux**: `cp .env.example .env`

2.  Open `.env` in your text editor and fill in the following credentials:
    - `OPENAI_API_KEY`: For OpenAI models.
    - `DEEPSEEK_API_KEY`: For DeepSeek models (optional/if used).
    - `GOOGLE_API_KEY`: For Google Gemini models.
    - `ANTHROPIC_API_KEY`: For Anthropic Claude models.
    - `GOOGLE_OAUTH_CLIENT_ID` & `SECRET`: For Google Workspace integration.
    - `USER_GOOGLE_EMAIL`: The email address for the Workspace agent to act as.

### 5. Running the Agent

Start the main agent process:

```bash
uv run main.py
```
