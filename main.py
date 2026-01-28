
import os
import re
import asyncio
import subprocess
import json
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from dotenv import load_dotenv
from pydantic import PrivateAttr, BaseModel, Field

from langchain_core.tools import BaseTool, StructuredTool
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent
from openai import OpenAI
from rich.prompt import Prompt

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

# LangChain messages (for shared history)
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

# Rich
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.markdown import Markdown
from rich.align import Align
from rich import box
from routines import RoutineManager


# ----------------------------
# CONFIG / SETUP
# ----------------------------
console = Console()
load_dotenv()

MCP_SERVER_PATH = Path(r"C:\WeCrunch\experiments\ease_workspace\google_workspace_mcp")
CONVERSATIONS_DIR = Path(__file__).parent / "conversations"
MEMORY_FILE = Path(__file__).parent / "artifacts" / "memory.txt"
CONNECTION_MODE = "STDIO"

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USER_GOOGLE_EMAIL = os.getenv("USER_GOOGLE_EMAIL")  # REQUIRED


def init_llm(provider: str, model_name: str, temperature: float = 0.1) -> Any:
    """Initialize the LLM based on provider and model name."""
    provider = provider.lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment.")
        return ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
        
    elif provider == "google":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             # Fallback: check GOOGLE_API_KEY as per user request snippet, though we use GEMINI_API_KEY in .env
             api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) not found in environment.")
            
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            convert_system_message_to_human=True # Often needed for Gemini with system prompts
        )
        
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment.")
        return ChatAnthropic(model=model_name, temperature=temperature, api_key=api_key)
        
    elif provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment.")
        return ChatDeepSeek(model=model_name, temperature=temperature, api_key=api_key)
        
    else:
        raise ValueError(f"Unknown provider: {provider}")

# Placeholder for global LLM - will be set in main()
llm = None

openai_client = OpenAI(api_key=OPENAI_API_KEY)

GOOGLE_WORKSPACE_INSTRUCTIONS = """
**ROLE AND GOAL:**
You are an expert Google Workspace Assistant. Help users manage Gmail, Drive, Calendar, Docs, Slides, etc.
Be secure and privacy-conscious.

AUTH HANDLING (CRITICAL):
- If a tool result contains "ACTION REQUIRED: Google Authentication Needed", you must:
  1) Present the Authorization URL as a clickable hyperlink (Markdown) + raw URL
  2) Tell user to complete auth in browser and retry the same command
- Do not keep calling tools; wait for user retry.

SLIDES API RULES (CRITICAL):
- NEVER use insertText/replaceAllText on a slideId like "slide1".
  insertText.objectId MUST be a text shape ID (placeholder shape).
- After createSlide, fetch presentation structure to find placeholder object IDs,
  then insertText into those placeholder shape objectIds.
- NEVER call replaceAllText with empty containsText.text.

TERMINAL TOOL USAGE:
- You have access to a `terminal` tool to execute system commands on the local environment.
- **WINDOWS**: Commands run in **PowerShell**. Use PowerShell syntax (e.g., `Get-ChildItem`, `Select-String`).
- **LINUX/MAC**: Commands run in **Bash**. Use Bash syntax (e.g., `ls`, `grep`).
- Use it to manage local files, run data transformation scripts, or interact with the filesystem.
- PERFORMANCE CRITICAL: ALWAYS check the current working directory first. DO NOT run recursive searches on root unless explicitly asked.


AVAILABLE SKILLS (CRITICAL):
- You have access to local skill definitions in the 'skills' folder.
- Use the `read_skills` tool to read detailed procedures for:
  1) google_docs_output.txt (Doc creation/table formatting)
  2) google_mail_output.txt (Gmail search/metadata)
  3) google_sheets_output.txt (Sheet formatting/conditional rules)
  4) google_slides_output.txt (Presentation structure/image insertion)
- ALWAYS consult these skills when performing complex Workspace tasks.

STRICTLY AVOID:
- Do NOT send emails
- Do NOT share files to other accounts
- Do NOT use general purpose subagents

USER:
- Primary email: lmswecrunch@gmail.com
"""

GENERAL_ASSISTANT_INSTRUCTIONS = """
You are a helpful general assistant.
- You do NOT call tools.
- You do NOT claim you performed actions in Gmail/Drive/Calendar/Docs/Slides or on the local filesystem.
- If the user asks to do something in Google Workspace or local file/system operations, you can say you'll hand off to the Workspace Agent.
"""


# LLM Router schema
class RouteDecision(BaseModel):
    route: str = Field(..., description='Either "ASSISTANT" or "AGENT"')
    reason: str = Field(..., description="Short reason for routing")


ROUTER_INSTRUCTIONS = """
You are a routing controller for a chat system with two modes:

1) ASSISTANT:
- General conversation, explanations, brainstorming, code review, drafting text.
- MUST NOT use any Google Workspace tools.
- MUST NOT claim you performed actions in Google Workspace.

2) AGENT:
- Any request that requires interacting with Google Workspace: Gmail, Drive, Calendar, Docs, Sheets, Slides
  (e.g., read/search emails, create docs/slides, list drive files, schedule meetings, etc.)
- Any request asking to fetch/modify the user's Google account data.
- Any request involving local file system operations, running bash commands, or checking system status.

Return ONLY valid JSON with keys: route, reason.
route must be exactly "ASSISTANT" or "AGENT".
No extra text.
"""


def _extract_bracket_payload(text: str) -> Optional[str]:
    """
    Extract the first top-level [...] block from text.
    Works even if it spans multiple lines.
    """
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _parse_pythonish_list(payload: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parses either JSON list or Python repr list (single quotes) safely.
    Returns list[dict] or None.
    """
    # Try JSON first
    try:
        obj = json.loads(payload)
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return obj
    except Exception:
        pass

    # Fallback: Python literal (handles single quotes)
    try:
        obj = ast.literal_eval(payload)
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return obj
    except Exception:
        return None

    return None


def _status_badge(status: str) -> tuple[str, str]:
    """
    Returns (icon, rich_style) for a given status.
    """
    s = (status or "").strip().lower()
    if s == "completed":
        return "✅", "bold green"
    if s in ("in_progress", "in-progress", "in progress"):
        return "⏳", "bold yellow"
    if s == "blocked":
        return "⛔", "bold red"
    return "⬜", "dim"


def render_todo_list(items: List[Dict[str, Any]], title: str = "Updated TODO List") -> None:
    total = len(items)
    done = sum(1 for x in items if (x.get("status") or "").strip().lower() == "completed")

    console.print(
        Panel(
            f"[bold]Progress:[/bold] {done}/{total} completed",
            title=f"📌 {title}",
            border_style="magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    t = Table(
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold magenta",
        title="Tasks",
    )
    t.add_column("#", style="bold cyan", no_wrap=True)
    t.add_column("Status", style="white", no_wrap=True)
    t.add_column("Task", style="white")

    for i, item in enumerate(items, start=1):
        status = str(item.get("status", "") or "")
        content = str(item.get("content", "") or "")
        icon, style = _status_badge(status)

        # Make status look nice (snake_case -> Title Case)
        pretty_status = status.replace("_", " ").strip().title() if status else "Pending"

        t.add_row(str(i), f"[{style}]{icon} {pretty_status}[/{style}]", content)

    console.print(t)


def maybe_render_todo_from_text(text: str) -> bool:
    """
    Detects the pattern:
      'Updated todo list to [...]'
    and renders the list as a human-readable table.
    Returns True if it rendered.
    """
    if "updated todo list" not in text.lower():
        return False

    payload = _extract_bracket_payload(text)
    if not payload:
        return False

    items = _parse_pythonish_list(payload)
    if not items:
        return False

    # Only treat it as todo list if it looks like tasks
    if not all(("content" in x or "status" in x) for x in items):
        return False

    render_todo_list(items, title="Updated TODO List")
    return True


# ----------------------------
# HUMAN READABLE RENDERING
# ----------------------------
def _try_parse_json(text: str) -> Optional[Union[dict, list]]:
    try:
        obj = json.loads(text)
        if isinstance(obj, (dict, list)):
            return obj
        return None
    except Exception:
        return None


def _flatten_text_blocks(obj: Any) -> Optional[str]:
    """
    Many tool outputs end up like:
      [{"type":"text","text":"....","id":"..."}]
    Or nested under SafeTool "result".
    If we detect that structure, we return just the concatenated text.
    """
    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        # "content blocks"
        if all(("type" in x and x.get("type") == "text" and "text" in x) for x in obj):
            return "\n".join((x.get("text", "") or "").strip() for x in obj if x.get("text"))
    return None


def _render_kv_table(d: Dict[str, Any], title: str, border_style: str = "cyan") -> None:
    t = Table(title=title, box=box.ROUNDED, border_style=border_style, show_header=True, header_style="bold magenta")
    t.add_column("Key", style="bold cyan", no_wrap=True)
    t.add_column("Value", style="white")

    def fmt(v: Any) -> str:
        if v is None:
            return ""
        # Avoid dumping JSON
        if isinstance(v, (dict, list)):
            txt = _flatten_text_blocks(v)
            if txt is not None:
                return txt
            # Show compact summary
            if isinstance(v, dict):
                keys = ", ".join(list(v.keys())[:8])
                return f"(object) keys: {keys}" + (" ..." if len(v.keys()) > 8 else "")
            if isinstance(v, list):
                return f"(list) {len(v)} item(s)"
        return str(v)

    for k, v in d.items():
        t.add_row(str(k), fmt(v))

    console.print(t)


def _render_list(items: List[Any], title: str, border_style: str = "cyan") -> None:
    t = Table(title=title, box=box.ROUNDED, border_style=border_style, show_header=True, header_style="bold magenta")
    t.add_column("#", style="bold cyan", no_wrap=True)
    t.add_column("Item", style="white")

    for i, item in enumerate(items, start=1):
        if isinstance(item, dict):
            # Prefer "text blocks" to show real text
            maybe_txt = _flatten_text_blocks([item]) if item.get("type") == "text" else None
            if maybe_txt:
                t.add_row(str(i), maybe_txt)
            else:
                keys = ", ".join(list(item.keys())[:10])
                t.add_row(str(i), f"(object) keys: {keys}" + (" ..." if len(item.keys()) > 10 else ""))
        elif isinstance(item, list):
            maybe_txt = _flatten_text_blocks(item)
            if maybe_txt:
                t.add_row(str(i), maybe_txt)
            else:
                t.add_row(str(i), f"(list) {len(item)} item(s)")
        else:
            t.add_row(str(i), str(item))

    console.print(t)


def pretty_print_route_decision(route: str, reason: str) -> None:
    console.print(
        Panel(
            Group(
                Text(f"Route: {route}", style="bold white"),
                Text(f"Reason: {reason}", style="white"),
            ),
            title="🧭 Router Decision",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def pretty_print_tool_call(tool_name: str, args: Dict[str, Any]) -> None:
    console.print(
        Panel(
            Group(
                Text(f"Tool: {tool_name}", style="bold white"),
                Text("Arguments:", style="bold cyan"),
            ),
            title="🔧 Tool Call",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    if args:
        _render_kv_table(args, title="Arguments", border_style="yellow")
    else:
        console.print(Panel("(no arguments)", border_style="yellow", box=box.ROUNDED))


def pretty_print_tool_result(tool_name: str, raw_content: Any) -> None:
    """
    Always print tool result WITHOUT JSON.
    - If SafeTool envelope => show status + result text.
    - If content blocks => show text only.
    - Else show readable tables/panels.
    """
    if isinstance(raw_content, (dict, list)):
        # Already structured (rare) -> treat as "parsed"
        parsed = raw_content
    else:
        text = str(raw_content)
        show_google_auth_link(text)
        parsed = _try_parse_json(text) or text

    # SafeTool envelope?
    if isinstance(parsed, dict) and ("ok" in parsed) and ("tool" in parsed):
        ok = bool(parsed.get("ok"))
        tool = parsed.get("tool") or tool_name
        status = "OK" if ok else "ERROR"

        header = {"Tool": tool, "Status": status}
        if not ok and parsed.get("error"):
            header["Error"] = parsed.get("error")
        if not ok and parsed.get("hint"):
            header["Hint"] = parsed.get("hint")

        console.print(Panel("Tool Result", title="🔨 Tool Result", border_style="green", box=box.ROUNDED))
        _render_kv_table(header, title="Summary", border_style="green")

        if ok:
            result = parsed.get("result")
            # If result contains LC blocks: show text
            txt = _flatten_text_blocks(result)
            if txt is not None:
                console.print(
                    Panel(
                        txt.strip() or "(empty)",
                        title="Result",
                        border_style="green",
                        box=box.ROUNDED,
                        padding=(1, 2),
                    )
                )
                return

            # Other shapes
            if isinstance(result, dict):
                _render_kv_table(result, title="Result", border_style="green")
                return
            if isinstance(result, list):
                txt2 = _flatten_text_blocks(result)
                if txt2 is not None:
                    console.print(
                        Panel(
                            txt2.strip() or "(empty)",
                            title="Result",
                            border_style="green",
                            box=box.ROUNDED,
                            padding=(1, 2),
                        )
                    )
                    return
                _render_list(result, title="Result", border_style="green")
                return

            console.print(
                Panel(
                    str(result) if result is not None else "(empty)",
                    title="Result",
                    border_style="green",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
        else:
            # On error, we already printed summary
            pass

        return

    # Parsed but not SafeTool
    if isinstance(parsed, dict):
        console.print(Panel(f"Tool: {tool_name}", title="🔨 Tool Result", border_style="green", box=box.ROUNDED))
        _render_kv_table(parsed, title="Result", border_style="green")
        return

    if isinstance(parsed, list):
        console.print(Panel(f"Tool: {tool_name}", title="🔨 Tool Result", border_style="green", box=box.ROUNDED))
        txt = _flatten_text_blocks(parsed)
        if txt is not None:
            console.print(Panel(txt.strip() or "(empty)", title="Result", border_style="green", box=box.ROUNDED))
        else:
            _render_list(parsed, title="Result", border_style="green")
        return

    # Plain text fallback
    s = str(parsed)
    if len(s) > 4000:
        s = s[:4000] + "..."
    console.print(
        Panel(
            s,
            title=f"🔨 Tool Result: {tool_name}",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


# ----------------------------
# ORIGINAL HELPERS
# ----------------------------
def create_header() -> Text:
    header_text = Text()
    header_text.append(
        "╔═══════════════════════════════════════════════════════════════════════════════╗\n",
        style="bold magenta",
    )
    header_text.append("║                                                                               ║\n", style="bold magenta")
    header_text.append("║              ", style="bold magenta")
    header_text.append("🚀 WORKSPACE AI AGENT 🚀", style="bold cyan on #1a1a2e")
    header_text.append("                         ║\n", style="bold magenta")
    header_text.append("║                                                                               ║\n", style="bold magenta")
    header_text.append("║           ", style="bold magenta")
    header_text.append("Powered by EaseVision", style="bold yellow italic")
    header_text.append("  •  ", style="bold white")
    header_text.append("Your AI Workspace Assistant", style="bold green italic")
    header_text.append("          ║\n", style="bold magenta")
    header_text.append("║                                                                               ║\n", style="bold magenta")
    header_text.append(
        "╚═══════════════════════════════════════════════════════════════════════════════╝",
        style="bold magenta",
    )
    return header_text


def ensure_required_env() -> None:
    missing = []
    
    # These are strictly required for the Workspace Agent to function
    if not GOOGLE_OAUTH_CLIENT_ID:
        missing.append("GOOGLE_OAUTH_CLIENT_ID")
    if not GOOGLE_OAUTH_CLIENT_SECRET:
        missing.append("GOOGLE_OAUTH_CLIENT_SECRET")
    if not USER_GOOGLE_EMAIL:
        missing.append("USER_GOOGLE_EMAIL")
    
    # Warn but don't fail for model keys yet - we check them after selection
    
    if missing:
        console.print(
            Panel(
                "[bold red]Missing required environment variables:[/bold red]\n\n"
                + "\n".join([f"• {m}" for m in missing])
                + "\n\n[yellow]Fix:[/yellow]\n"
                "1) Put them in your .env\n"
                "2) Restart your terminal/app\n\n"
                "[dim]Example: USER_GOOGLE_EMAIL=lmswecrunch@gmail.com[/dim]",
                title="[bold red]❌ Configuration Error[/bold red]",
                border_style="bold red",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        raise SystemExit(1)


def create_client_secret_file() -> bool:
    client_secret_path = MCP_SERVER_PATH / "client_secret.json"
    client_secret_content = {
        "installed": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uris": [
                "http://localhost:8000/oauth2callback",
                "http://localhost:8000/",
            ],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
    }

    try:
        os.makedirs(MCP_SERVER_PATH, exist_ok=True)
        with open(client_secret_path, "w", encoding="utf-8") as f:
            json.dump(client_secret_content, f, indent=2)
        console.print("[bold green]✓ client_secret.json created/updated (localhost:8000)[/bold green]\n")
        return True
    except Exception as e:
        console.print(f"[bold red]✗ Failed to write client_secret.json:[/bold red] {e}\n")
        return False


def show_google_auth_link(text: str) -> bool:
    if "ACTION REQUIRED: Google Authentication Needed" not in text:
        return False

    url_match = re.search(r"Authorization URL:\s*(https?://[^\s]+)", text)
    if not url_match:
        url_match = re.search(r"(https?://accounts\.google\.com/o/oauth2/auth\?[^\s]+)", text)

    if not url_match:
        return False

    url = url_match.group(1).strip()
    link_text = Text("Click here to authorize Google access", style=f"bold blue link {url}")

    console.print(
        Panel(
            Group(
                Text("Google authentication is required.\n", style="bold yellow"),
                link_text,
                Text("\nMarkdown hyperlink:", style="dim"),
                Text(f"[Click here to authorize Google access]({url})", style="dim"),
                Text("\nRaw URL:", style="dim"),
                Text(url, style="dim"),
                Text("\nAfter authorization, retry the same command.", style="bold green"),
            ),
            title="[bold blue]🔐 Authorization Required[/bold blue]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    return True


def extract_tool_error_hint(err_text: str) -> str:
    low = err_text.lower()
    if "replacealltext" in low and "match text should not be empty" in low:
        return "Slides replaceAllText failed: match text was empty. Use a real placeholder string as containsText.text."
    if "inserttext" in low and "does not allow text editing" in low:
        return "Slides insertText failed: objectId was a slideId, not a text shape. Fetch presentation structure and insert into placeholder shape objectIds."
    return ""


def make_web_search_tool() -> StructuredTool:
    def web_search(query: str) -> str:
        console.print(f"[bold cyan]🔍 Performing Web Search:[/bold cyan] [yellow]{query}[/yellow]")
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research assistant. Provide technically detailed and concise summaries.",
                    },
                    {"role": "user", "content": f"Please provide a summary for the query: {query}"},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error during web search: {e}"

    return StructuredTool.from_function(
        name="web_search",
        description="Search the web and return a concise technical summary.",
        func=web_search,
    )



def make_read_error_history_tool():
    """Reads the error history file to provide debugging insights."""
    
    def read_error_history() -> str:
        """
        Reads the content of error_history.txt.
        Use this when you have failed a task 3 times and need to check past solutions.
        """
        try:
            history_file = Path(__file__).parent / "artifacts" / "error_history.txt"
            if not history_file.exists():
                return "No error history file found."
                
            with open(history_file, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                return "Error history is empty."
            return f"ERROR HISTORY (Consult this after 3 failed tries):\n{content}"
        except Exception as e:
            return f"Error reading history: {e}"

    return StructuredTool.from_function(
        func=read_error_history,
        name="read_error_history",
        description="Reads past error solutions. Use after 3 failed attempts."
    )


def make_read_skills_tool() -> StructuredTool:
    def read_skills() -> str:
        skills_dir = Path(__file__).parent / "skills"
        if not skills_dir.exists() or not skills_dir.is_dir():
            return "Skills folder not found."

        output = []
        for file in skills_dir.glob("*.txt"):
            try:
                content = file.read_text(encoding="utf-8")
                output.append(f"--- {file.name} ---\n{content}")
            except Exception as e:
                output.append(f"--- Error reading {file.name}: {e} ---")

        if not output:
            return "No skill files found in the skills folder."

        return "\n\n".join(output)

    return StructuredTool.from_function(
        name="read_skills",
        description="Read all available skill files from the skills directory to understand the agent's capabilities.",
        func=read_skills,
    )


def make_terminal_tool() -> StructuredTool:
    """Create a tool that runs system commands (PowerShell on Windows, Bash on Linux)."""

    def terminal_tool_func(command: str) -> str:
        """Execute a command within the environment using the native shell."""
        shell_name = "PowerShell" if os.name == "nt" else "Bash"
        console.print(f"[bold cyan]💻 {shell_name}:[/bold cyan] [yellow]{command}[/yellow]")
        
        try:
            if os.name == "nt":
                # Windows: Use PowerShell
                # -NoProfile: No user profile
                # -NonInteractive: No interactive prompts
                # -Command: The command to run
                proc_args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
            else:
                # Linux/Mac: Use Bash
                proc_args = ["bash", "-c", command]

            process = subprocess.run(
                proc_args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            output = process.stdout
            if process.stderr:
                output += f"\n[STDERR]\n{process.stderr}"
            return output.strip() or "(Command executed with no output)"
            
        except FileNotFoundError:
            return f"Error: Shell executable for {shell_name} not found."
        except Exception as e:
            return f"Error executing command: {e}"

    return StructuredTool.from_function(
        name="terminal",
        description="Run system commands. Windows uses PowerShell; Linux/Mac uses Bash. Use this for file management and system ops.",
        func=terminal_tool_func,
    )


def load_memory() -> str:
    """Load the agent's long-term memory from file."""
    if MEMORY_FILE.exists():
        try:
            return MEMORY_FILE.read_text(encoding="utf-8").strip()
        except Exception as e:
            console.print(f"[red]Failed to load memory: {e}[/red]")
    return ""


def save_conversation_log(chat_history: List[BaseMessage], filepath: Path) -> None:
    """Save the current conversation to a file."""
    try:
        filepath.parent.mkdir(exist_ok=True, parents=True)
        
        output = []
        for msg in chat_history:
            role = "Toolcall"
            if isinstance(msg, SystemMessage):
                role = "SYSTEM"
            elif isinstance(msg, HumanMessage):
                role = "USER"
            elif isinstance(msg, AIMessage):
                role = "ASSISTANT"
            
            content = getattr(msg, "content", "")
            output.append(f"[{role}]\n{content}\n")
            
        filepath.write_text("\n".join(output), encoding="utf-8")
        # console.print(f"[dim]Log updated: {filepath.name}[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to save conversation log: {e}[/red]")


def update_memory_with_llm(chat_history: List[BaseMessage]) -> None:
    """Update long-term memory using the LLM."""
    try:
        current_memory = load_memory()
        
        # Convert history to text (last 10 messages to keep it focused and fast)
        recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
        conversation_text = ""
        for msg in recent_history:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            if isinstance(msg, SystemMessage): continue
            conversation_text += f"{role}: {msg.content}\n"

        prompt = (
            f"You are a memory manager for an AI assistant. "
            f"Update the following memory based on the recent conversation.\n\n"
            f"### CURRENT MEMORY:\n{current_memory or '(Empty)'}\n\n"
            f"### RECENT CONVERSATION:\n{conversation_text}\n\n"
            f"### INSTRUCTIONS:\n"
            f"1. Extract key user preferences, facts, and specific feedback from the RECENT CONVERSATION.\n"
            f"2. Merge them into the Current Memory.\n"
            f"3. Remove outdated information.\n"
            f"4. Keep it concise/bulleted.\n"
            f"5. RETURN ONLY THE NEW MEMORY TEXT."
        )

        response = llm.invoke([HumanMessage(content=prompt)])
        new_memory = response.content.strip()
        
        MEMORY_FILE.write_text(new_memory, encoding="utf-8")
        console.print("[bold green]🧠 Memory updated[/bold green]")
        
    except Exception as e:
        console.print(f"[red]Failed to update memory: {e}[/red]")


def test_server_startup() -> Optional[Dict[str, Any]]:
    console.print("[bold yellow]🔍 Testing MCP server startup...[/bold yellow]")

    server_env = os.environ.copy()
    candidates = [
        {"name": "uv run (directory + main.py)", "command": "uv", "args": ["--directory", str(MCP_SERVER_PATH), "run", "main.py"]},
        {"name": "python (full path)", "command": "python", "args": [str(MCP_SERVER_PATH / "main.py")]},
    ]

    for cfg in candidates:
        console.print(f"\n[cyan]Testing: {cfg['name']}[/cyan]")
        try:
            proc = subprocess.Popen(
                [cfg["command"]] + cfg["args"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=server_env,
            )
            import time
            time.sleep(2)

            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                console.print(f"[red]❌ Exited with code {proc.returncode}[/red]")
                if stdout:
                    console.print(f"[yellow]STDOUT:[/yellow]\n{stdout[:800]}")
                if stderr:
                    console.print(f"[red]STDERR:[/red]\n{stderr[:800]}")
                continue

            console.print("[green]✓ Server started successfully[/green]")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
            return cfg

        except FileNotFoundError:
            console.print(f"[red]❌ Command not found:[/red] {cfg['command']}")
        except Exception as e:
            console.print(f"[red]❌ Error:[/red] {e}")

    console.print("\n[bold red]❌ No working server startup configuration found.[/bold red]")
    return None


class SafeTool(BaseTool):
    """A BaseTool wrapper that never raises; returns JSON ok/error back to the agent."""

    _inner: Any = PrivateAttr()
    _tool_name: str = PrivateAttr()

    def __init__(self, inner_tool: Any, name: str, description: str):
        super().__init__(name=name, description=description)
        self._inner = inner_tool
        self._tool_name = name

        schema = getattr(inner_tool, "args_schema", None)
        if schema is not None:
            try:
                self.args_schema = schema  # type: ignore
            except Exception:
                pass

    def _ok(self, result: Any) -> str:
        return json.dumps({"ok": True, "tool": self._tool_name, "result": result}, default=str)

    def _fail(self, err: Exception) -> str:
        err_text = str(err)
        hint = extract_tool_error_hint(err_text)
        payload: Dict[str, Any] = {"ok": False, "tool": self._tool_name, "error": err_text}
        if hint:
            payload["hint"] = hint
        return json.dumps(payload, default=str)

    def _run(self, **kwargs) -> str:
        try:
            if hasattr(self._inner, "invoke"):
                res = self._inner.invoke(kwargs)
            elif hasattr(self._inner, "run"):
                res = self._inner.run(kwargs)
            else:
                res = self._inner(kwargs)
            return self._ok(res)
        except Exception as e:
            return self._fail(e)

    async def _arun(self, **kwargs) -> str:
        try:
            if hasattr(self._inner, "ainvoke"):
                res = await self._inner.ainvoke(kwargs)
                return self._ok(res)

            if hasattr(self._inner, "arun"):
                try:
                    res = await self._inner.arun(kwargs)
                except TypeError:
                    res = await self._inner.arun(**kwargs)
                return self._ok(res)

            return self._run(**kwargs)
        except Exception as e:
            return self._fail(e)


def wrap_mcp_tools_safe(mcp_tools: List[Any]) -> List[Any]:
    safe: List[Any] = []
    for t in mcp_tools:
        name = getattr(t, "name", "Toolcall_tool")
        desc = getattr(t, "description", "") or f"Safe wrapper for {name}"
        safe.append(SafeTool(inner_tool=t, name=name, description=desc))
    return safe


def lc_messages_to_role_tuples(history: List[BaseMessage]) -> List[tuple]:
    out: List[tuple] = []
    for m in history:
        if isinstance(m, SystemMessage):
            out.append(("system", m.content))
        elif isinstance(m, HumanMessage):
            out.append(("user", m.content))
        elif isinstance(m, AIMessage):
            out.append(("assistant", m.content))
        else:
            role = getattr(m, "type", "assistant")
            out.append((role, getattr(m, "content", str(m))))
    return out


def build_router_llm():
    try:
        return llm.with_structured_output(RouteDecision)
    except Exception:
        return None


async def decide_route(router_llm_structured, chat_history: List[BaseMessage]) -> RouteDecision:
    router_messages: List[BaseMessage] = [
        SystemMessage(content=ROUTER_INSTRUCTIONS),
        *chat_history,
    ]

    if router_llm_structured is not None:
        try:
            decision: RouteDecision = await router_llm_structured.ainvoke(router_messages)
            if decision.route not in ("ASSISTANT", "AGENT"):
                return RouteDecision(route="ASSISTANT", reason="Invalid router output; defaulting to ASSISTANT.")
            return decision
        except Exception:
            pass

    raw = await llm.ainvoke(router_messages)
    txt = (getattr(raw, "content", "") or "").strip()
    try:
        data = json.loads(txt)
        route = data.get("route", "ASSISTANT")
        reason = data.get("reason", "")
        if route not in ("ASSISTANT", "AGENT"):
            route = "ASSISTANT"
        return RouteDecision(route=route, reason=reason)
    except Exception:
        return RouteDecision(route="ASSISTANT", reason="Router returned non-JSON; defaulting to ASSISTANT.")


# ----------------------------
# MAIN
# ----------------------------
async def main() -> None:
    console.clear()
    console.print(create_header())
    console.print()

    ensure_required_env()
    
    # ----------------------------
    # LLM SELECTION
    # ----------------------------
    global llm
    
    provider = os.getenv("MODEL_PROVIDER")
    model_name = os.getenv("MODEL_NAME")
    
    if not provider:
        console.print()
        console.print(Panel("[bold yellow]🤖 No MODEL_PROVIDER found in .env[/bold yellow]", border_style="yellow"))
        provider = Prompt.ask(
            "Select LLM Provider", 
            choices=["openai", "google", "anthropic", "deepseek"], 
            default="deepseek"
        )
    
    if not model_name:
        defaults = {
            "openai": "gpt-4o",
            "google": "gemini-1.5-pro",
            "anthropic": "claude-3-5-sonnet-20240620",
            "deepseek": "deepseek-chat"
        }
        default_model = defaults.get(provider, "gpt-4o")
        model_name = Prompt.ask(f"Enter Model Name for [cyan]{provider}[/cyan]", default=default_model)
        
    console.print(f"[dim]Initializing {provider} / {model_name}...[/dim]")
    try:
        llm = init_llm(provider, model_name)
        console.print(f"[bold green]✓ LLM Initialized check:[/bold green] {model_name}")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to initialize LLM:[/bold red] {e}")
        raise SystemExit(1)

    console.print("[bold cyan]🔧 Setting up OAuth credentials...[/bold cyan]")
    if not create_client_secret_file():
        raise SystemExit(1)

    if CONNECTION_MODE != "STDIO":
        raise ValueError("This file is STDIO-only. Set CONNECTION_MODE='STDIO'.")

    working = test_server_startup()
    if not working:
        raise SystemExit(1)

    console.print(f"\n[bold green]✓ Using server config:[/bold green] {working['name']}\n")
    server_params = StdioServerParameters(command=working["command"], args=working["args"], env=os.environ.copy())

    # Load Memory
    memory_content = load_memory()
    if memory_content:
        console.print("[bold magenta]🧠 Memory Loaded[/bold magenta]")

    console.print("[bold cyan]🔌 Connecting to MCP Server via STDIO...[/bold cyan]")

    web_search_tool = make_web_search_tool()
    read_skills_tool = make_read_skills_tool()
    terminal_tool = make_terminal_tool()
    router_llm_structured = build_router_llm()

    chat_history: List[BaseMessage] = []

    # Initialize Log File
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = CONVERSATIONS_DIR / f"conversation_{timestamp}.txt"

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            with Progress(
                SpinnerColumn(spinner_name="dots12", style="bold magenta"),
                TextColumn("[bold cyan]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Initializing MCP session...", total=None)

                await session.initialize()
                progress.update(task, description="[bold green]✓ MCP Session Initialized")
                await asyncio.sleep(0.2)

                progress.update(task, description="[bold cyan]📦 Loading MCP Tools...")
                raw_mcp_tools = await load_mcp_tools(session)
                progress.update(task, description=f"[bold green]✓ Loaded {len(raw_mcp_tools)} MCP tools")
                await asyncio.sleep(0.2)

                progress.update(task, description="[bold cyan]🛡️ Wrapping tools (no-fail mode)...")
                mcp_tools = wrap_mcp_tools_safe(raw_mcp_tools)
                progress.update(task, description=f"[bold green]✓ Tools wrapped: {len(mcp_tools)}")
                await asyncio.sleep(0.2)

                progress.update(task, description="[bold cyan]🤖 Creating Workspace Agent...")
                
                
                # Import learning module functions
                from src.learning import extract_and_save_skill, process_past_logs

                read_error_history_tool = make_read_error_history_tool()
                
                # Update instructions with Retry/Error logic
                DEEP_AGENT_INSTRUCTIONS = GOOGLE_WORKSPACE_INSTRUCTIONS + (f"\n\nMEMORY FROM PAST CONVERSATIONS:\n{memory_content}" if memory_content else "")
                DEEP_AGENT_INSTRUCTIONS += """
                
                **ERROR HANDLING PROTOCOL (CRITICAL)**:
                - If you encounter an error and fail to solve it 3 times in a row, you MUST use the `read_error_history` tool.
                - Check if this error has happened before and apply the known solution.
                - If you find a solution, try it.
                """
                
                agent = create_deep_agent(
                    [web_search_tool, read_skills_tool, terminal_tool, read_error_history_tool] + mcp_tools,
                    DEEP_AGENT_INSTRUCTIONS,
                    model=llm,
                ).with_config({"recursion_limit": 100})
                
                # --- START BACKGROUND ROUTINES ---
                routine_manager = RoutineManager(console, CONVERSATIONS_DIR)
                routine_manager.start_loop(agent)
                # ---------------------------------
                
                progress.update(task, description="[bold green]✓ Agent Ready")
                await asyncio.sleep(0.2)

            console.print()
            console.print(
                Panel(
                    "[bold cyan]💬 Chat Commands:[/bold cyan]\n\n"
                    "• Type your request naturally\n"
                    "• Type [bold yellow]/skills[/bold yellow] to extract a reusable skill\n"
                    "• Type [bold yellow]/learn [time][/bold yellow] to learn from logs (e.g. 'last week')\n"
                    "• [bold yellow]/routine[/bold yellow] (list tasks)\n"
                    "• [bold yellow]/routine add \"task desc\" HH:MM[/bold yellow] (daily)\n"
                    "• [bold yellow]/routine [pause|resume|delete] <ID>[/bold yellow]\n"
                    "• Type [bold yellow]'q'[/bold yellow] to quit\n\n"
                    "[dim]Router decides ASSISTANT vs AGENT. Both have full chat history.[/dim]",
                    title="[bold magenta]📋 How to Use[/bold magenta]",
                    border_style="bold blue",
                    box=box.DOUBLE_EDGE,
                    padding=(1, 2),
                )
            )
            console.print()

            while True:
                console.print("╭─────────────────────────────────────────────────────────────────────────────╮", style="bold blue")
                # CRITICAL FIX: Use asyncio.to_thread so we don't block the background routines!
                user_input = await asyncio.to_thread(console.input, "[bold cyan]👤 You[/bold cyan] [bold white]›[/bold white] ")
                console.print("╰─────────────────────────────────────────────────────────────────────────────╯", style="bold blue")


                if user_input.lower() in ("q", "quit", "exit"):
                    console.print()
                    console.print(
                        Panel(
                            Align.center("[bold yellow]👋 Bye![/bold yellow]"),
                            border_style="bold magenta",
                            box=box.DOUBLE_EDGE,
                            padding=(1, 2),
                        )
                    )
                    console.print()
                    break

                # ----------------------------
                # SLASH COMMANDS
                # ----------------------------
                if user_input.lower().startswith("/skills"):
                    console.print("[bold yellow]🧠 Analyzing conversation to extract skills...[/bold yellow]")
                    skills_dir = Path(__file__).parent / "skills"
                    status = extract_and_save_skill(chat_history, skills_dir, llm)
                    console.print(f"\n{status}\n")
                    continue

                if user_input.lower().startswith("/learn"):
                    # Parse time range
                    time_range = "last week" # Default
                    parts = user_input.split(" ", 1)
                    if len(parts) > 1:
                        time_range = parts[1]
                    
                    console.print(f"[bold yellow]📚 Learning from logs ({time_range})...[/bold yellow]")
                    logs_dir = Path(__file__).parent / "conversations"
                    error_history_file = Path(__file__).parent / "artifacts" / "error_history.txt"
                    best_practices_file = Path(__file__).parent / "artifacts" / "best_practices.txt" # New file
                    
                    # Ensure error history exists if not already
                    if not error_history_file.exists():
                        with open(error_history_file, "w") as f: f.write("# Error History\n")

                    status = process_past_logs(time_range, logs_dir, error_history_file, best_practices_file, llm)
                    console.print(f"\n{status}\n")
                    continue

                if user_input.lower().startswith("/models"):
                    console.print("[bold yellow]🔄 Switching Model...[/bold yellow]")
                    
                    new_provider = Prompt.ask(
                        "Select LLM Provider", 
                        choices=["openai", "google", "anthropic", "deepseek"], 
                        default="deepseek"
                    )
                    
                    defaults = {
                        "openai": "gpt-4o",
                        "google": "gemini-1.5-pro",
                        "anthropic": "claude-3-5-sonnet-20240620",
                        "deepseek": "deepseek-chat"
                    }
                    default_model = defaults.get(new_provider, "gpt-4o")
                    new_model_name = Prompt.ask(f"Enter Model Name for [cyan]{new_provider}[/cyan]", default=default_model)
                    
                    try:
                        llm = init_llm(new_provider, new_model_name)
                        
                        # Rebuild router
                        router_llm_structured = build_router_llm()
                        
                        # Recreate agent with new LLM
                        agent = create_deep_agent(
                            [web_search_tool, read_skills_tool, terminal_tool, read_error_history_tool] + mcp_tools,
                            DEEP_AGENT_INSTRUCTIONS,
                            model=llm,
                        ).with_config({"recursion_limit": 100})
                        
                        console.print(f"[bold green]✓ Switched to {new_provider} / {new_model_name}[/bold green]\n")
                    except Exception as e:
                        console.print(f"[bold red]❌ Failed to switch model:[/bold red] {e}")
                    
                    continue

                if user_input.lower().startswith("/routine"):
                    parts = user_input.strip().split(" ", 2)
                    # Usage: 
                    # /routine -> list
                    # /routine add "desc" HH:MM
                    # /routine pause <ID>
                    # /routine resume <ID>
                    # /routine stop <ID>
                    # /routine delete <ID>
                    
                    cmd = parts[1].lower() if len(parts) > 1 else "status"
                    
                    if cmd in ("status", "list"):
                        table = routine_manager.list_routines()
                        console.print(table)
                    
                    elif cmd == "add":
                        # /routine add "desc" HH:MM
                        # We need to parse quotes or just split by last space
                        args_str = parts[2] if len(parts) > 2 else ""
                        # Split from right to get time
                        if " " in args_str:
                            desc_part, time_part = args_str.rsplit(" ", 1)
                            desc_part = desc_part.strip('"').strip("'")
                            
                            # Validate time roughly
                            if ":" in time_part:
                                rid = routine_manager.add_routine(desc_part, time_part)
                                console.print(f"[bold green]✓ Routine added![/bold green] ID: [cyan]{rid}[/cyan]")
                            else:
                                console.print("[red]Invalid time format. Use HH:MM[/red]")
                        else:
                             console.print("[red]Usage: /routine add \"Task Description\" HH:MM[/red]")

                    elif cmd in ("pause", "resume", "start", "stop", "delete"):
                        rid = parts[2] if len(parts) > 2 else ""
                        if rid:
                            success = routine_manager.control_routine(rid, cmd)
                            if success:
                                console.print(f"[bold green]✓ Routine {cmd}d successfully.[/bold green]")
                            else:
                                console.print(f"[red]Failed to {cmd} routine. Check ID.[/red]")
                        else:
                             console.print(f"[red]Usage: /routine {cmd} <ID>[/red]")
                    
                    else:
                        console.print("[red]Unknown routine command. Use: status, add, pause, resume, stop, delete[/red]")

                    continue

                # ----------------------------


                chat_history.append(HumanMessage(content=user_input))
                save_conversation_log(chat_history, log_file)

                console.print()
                console.print(
                    Panel(
                        Align.center("[bold yellow]⚡ ROUTING ⚡[/bold yellow]"),
                        border_style="bold yellow",
                        box=box.HEAVY,
                        padding=(0, 2),
                    )
                )
                console.print()

                try:
                    decision = await decide_route(router_llm_structured, chat_history)
                except Exception as e:
                    decision = RouteDecision(route="ASSISTANT", reason=f"Router error: {e}. Defaulting to ASSISTANT.")

                # No JSON: Route/Reason
                pretty_print_route_decision(decision.route, decision.reason)

                # ASSISTANT (no tools)
                if decision.route == "ASSISTANT":
                    console.print()
                    console.print(
                        Panel(
                            Align.center("[bold yellow]⚡ ASSISTANT RESPONDING ⚡[/bold yellow]"),
                            border_style="bold yellow",
                            box=box.HEAVY,
                            padding=(0, 2),
                        )
                    )
                    console.print()

                    try:
                        assistant_messages: List[BaseMessage] = [
                            SystemMessage(content=GENERAL_ASSISTANT_INSTRUCTIONS + (f"\n\nMEMORY:\n{memory_content}" if memory_content else "")),
                            *chat_history,
                        ]
                        ai_msg = await llm.ainvoke(assistant_messages)
                        content = getattr(ai_msg, "content", "") or ""
                        chat_history.append(AIMessage(content=content))
                        
                        save_conversation_log(chat_history, log_file)
                        update_memory_with_llm(chat_history)

                        console.print(
                            Panel(
                                Markdown(content),
                                title="[bold magenta]🎯 Assistant[/bold magenta]",
                                border_style="bold magenta",
                                box=box.DOUBLE_EDGE,
                                padding=(1, 2),
                            )
                        )
                    except Exception as e:
                        err_text = str(e)
                        console.print(
                            Panel(
                                f"[bold red]Error:[/bold red] {err_text}\n\n[dim]{type(e).__name__}[/dim]",
                                title="[bold red]❌ Assistant Error[/bold red]",
                                border_style="bold red",
                                box=box.ROUNDED,
                                padding=(1, 2),
                            )
                        )
                    console.print()
                    continue

                # AGENT (tools allowed)
                console.print()
                console.print(
                    Panel(
                        Align.center("[bold yellow]⚡ AGENT PROCESSING ⚡[/bold yellow]"),
                        border_style="bold yellow",
                        box=box.HEAVY,
                        padding=(0, 2),
                    )
                )
                console.print()

                final_text: Optional[str] = None
                step_count = 0

                try:
                    agent_messages = lc_messages_to_role_tuples(chat_history)

                    async for event in agent.astream(
                        {"messages": agent_messages},
                        stream_mode="updates",
                    ):
                        for node_name, node_data in event.items():
                            step_count += 1
                            step_colors = ["magenta", "blue", "cyan", "green", "yellow"]
                            step_color = step_colors[step_count % len(step_colors)]

                            console.print(f"\n[bold {step_color}]{'━' * 80}[/bold {step_color}]")
                            console.print(
                                f"[bold white]📍 Step {step_count}:[/bold white] "
                                f"[bold {step_color}]{node_name}[/bold {step_color}]"
                            )
                            console.print(f"[bold {step_color}]{'━' * 80}[/bold {step_color}]\n")

                            if "messages" in node_data:
                                messages = node_data["messages"]
                                if not isinstance(messages, list):
                                    messages = [messages]

                                for msg in messages:
                                    # LOGGING: Append to history and save immediately
                                    chat_history.append(msg)
                                    save_conversation_log(chat_history, log_file)

                                    if getattr(msg, "type", None) == "ai":
                                        content = getattr(msg, "content", "")
                                        # if content:
                                        #     console.print(
                                        #         Panel(
                                        #             f"[italic white]{content}[/italic white]",
                                        #             title="[bold cyan]💭 Agent[/bold cyan]",
                                        #             border_style="cyan",
                                        #             box=box.ROUNDED,
                                        #             padding=(1, 2),
                                        #         )
                                        #     )
                                        if content:
                                            # If it's the ugly todo list dump, render a nice table instead
                                            if maybe_render_todo_from_text(content):
                                                # Optionally also show any non-list text around it:
                                                # (Usually not needed, but kept simple.)
                                                pass
                                            else:
                                                console.print(
                                                    Panel(
                                                        f"[italic white]{content}[/italic white]",
                                                        title="[bold cyan]💭 Agent[/bold cyan]",
                                                        border_style="cyan",
                                                        box=box.ROUNDED,
                                                        padding=(1, 2),
                                                    )
                                                )


                                        tool_calls = getattr(msg, "tool_calls", None)
                                        if tool_calls:
                                            for tc in tool_calls:
                                                tc_name = tc.get("name", "Toolcall")
                                                tc_args = tc.get("args", {}) or {}
                                                # No JSON tool call display
                                                pretty_print_tool_call(tc_name, tc_args)
                                        
                                        # Do NOT capture final_text from here anymore to avoid duplication in history
                                        # But we still want to show the Final Answer panel at the end? 
                                        # Actually, if we append incrementally, the final answer IS ALREADY IN HISTORY.
                                        # We just need to identify the "last" message content for the UI panel.
                                        if content:
                                            final_text = content

                                    elif getattr(msg, "type", None) == "tool":
                                        tool_name = getattr(msg, "name", "Toolcall")
                                        content = getattr(msg, "content", "")
                                        # No JSON tool result display
                                        pretty_print_tool_result(tool_name, content)

                except Exception as e:
                    err_text = str(e)
                    show_google_auth_link(err_text)
                    console.print(
                        Panel(
                            f"[bold red]Error:[/bold red] {err_text}\n\n[dim]{type(e).__name__}[/dim]",
                            title="[bold red]❌ Error[/bold red]",
                            border_style="bold red",
                            box=box.ROUNDED,
                            padding=(1, 2),
                        )
                    )
                    console.print()
                    continue

                console.print(f"\n[bold green]{'═' * 80}[/bold green]")
                console.print(Align.center("[bold green]✅ COMPLETE ✅[/bold green]"))
                console.print(f"[bold green]{'═' * 80}[/bold green]\n")

                if final_text:
                    # Note: We ALREADY appended the message incrementally in the loop.
                    # We just update memory/logs one last time to be sure? 
                    # Actually, if we appended it, we don't need to append again.
                    # But we usually run update_memory_with_llm at the end.
                    update_memory_with_llm(chat_history)
                    
                    console.print(
                        Panel(
                            Markdown(final_text),
                            title="[bold magenta]🎯 Final Answer[/bold magenta]",
                            border_style="bold magenta",
                            box=box.DOUBLE_EDGE,
                            padding=(1, 2),
                        )
                    )

                console.print()


if __name__ == "__main__":
    asyncio.run(main())
