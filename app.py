







# import streamlit as st
# import asyncio
# import os
# import re
# import json
# import subprocess
# import sys
# import time
# from pathlib import Path
# from typing import Optional, Dict, Any, List
# import traceback

# # Load env immediately
# from dotenv import load_dotenv
# load_dotenv()

# from pydantic import PrivateAttr

# # LangChain & AI
# from langchain_core.tools import BaseTool, StructuredTool
# from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
# from langchain_deepseek import ChatDeepSeek
# from deepagents import create_deep_agent
# from openai import OpenAI

# # MCP
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# from langchain_mcp_adapters.tools import load_mcp_tools

# # -----------------------------------------------------------------------------
# # 1. SETTINGS & CONFIGURATION
# # -----------------------------------------------------------------------------
# CONFIG_PATH = Path.home() / ".workspace_agent" / "config.json"
# CONFIG_PATH.parent.mkdir(exist_ok=True)
# MCP_SERVER_PATH = Path(r"C:\WeCrunch\experiments\ease_workspace\google_workspace_mcp")

# def load_config():
#     """Load saved configuration from file"""
#     if CONFIG_PATH.exists():
#         try:
#             with open(CONFIG_PATH, "r") as f:
#                 return json.load(f)
#         except json.JSONDecodeError:
#             st.warning("⚠️ Corrupted config file, starting fresh")
#             return {}
#     return {}

# def save_config(data: dict):
#     """Save configuration to file"""
#     try:
#         with open(CONFIG_PATH, "w") as f:
#             json.dump(data, f, indent=2)
#     except Exception as e:
#         st.error(f"Failed to save config: {e}")

# def get_configured_keys():
#     """Get all API keys from env or saved config"""
#     config = load_config()
    
#     return {
#         "deepseek": os.getenv("DEEPSEEK_API_KEY", config.get("deepseek_key", "")),
#         "openai": os.getenv("OPENAI_API_KEY", config.get("openai_key", "")),
#         "google_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", config.get("google_id", "")),
#         "google_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", config.get("google_secret", ""))
#     }

# # Auto-load saved keys into session state
# if "api_keys" not in st.session_state:
#     st.session_state.api_keys = get_configured_keys()

# # Debug mode
# if "debug_mode" not in st.session_state:
#     st.session_state.debug_mode = False

# # MCP logs
# if "mcp_logs" not in st.session_state:
#     st.session_state.mcp_logs = []

# # -----------------------------------------------------------------------------
# # 2. PAGE CONFIG & DYNAMIC UI (Light/Dark Compatible)
# # -----------------------------------------------------------------------------
# st.set_page_config(
#     page_title="Workspace Agent",
#     page_icon="⚡",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # NEW CSS: Uses CSS Variables (var(--...)) to adapt to Light AND Dark modes automatically
# st.markdown("""
# <style>
#     /* --- GLOBAL ADAPTIVE THEME --- */
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
#     html, body, [class*="css"] {
#         font-family: 'Inter', sans-serif;
#     }

#     /* Main Container - Adapts to Streamlit Theme */
#     .stApp {
#         background-color: var(--background-color);
#         color: var(--text-color);
#     }

#     /* Sidebar - Adapts to Streamlit Theme */
#     section[data-testid="stSidebar"] {
#         background-color: var(--secondary-background-color);
#         border-right: 1px solid rgba(128, 128, 128, 0.2);
#     }

#     /* --- CARDS & CONTAINERS --- */
    
#     /* Glass Card that looks good in both modes */
#     .glass-card {
#         background-color: var(--secondary-background-color);
#         border: 1px solid rgba(128, 128, 128, 0.2);
#         border-radius: 12px;
#         padding: 1.5rem;
#         margin-bottom: 1rem;
#         box-shadow: 0 4px 6px rgba(0,0,0,0.05);
#         transition: transform 0.2s;
#     }
#     .glass-card:hover {
#         transform: translateY(-2px);
#         box-shadow: 0 8px 15px rgba(0,0,0,0.1);
#     }

#     /* Chat Messages */
#     .stChatMessage {
#         background-color: var(--secondary-background-color);
#         border: 1px solid rgba(128, 128, 128, 0.2);
#         border-radius: 12px;
#         padding: 1rem;
#         margin-bottom: 10px;
#     }

#     /* User Avatar */
#     div[data-testid="chatAvatarIcon-user"] {
#         background-color: #3b82f6 !important; /* Blue */
#     }

#     /* Assistant Avatar */
#     div[data-testid="chatAvatarIcon-assistant"] {
#         background: linear-gradient(135deg, #00C9FF, #92FE9D);
#     }

#     /* Input Box - Adapts to theme */
#     .stChatInput textarea {
#         background-color: var(--secondary-background-color) !important;
#         border: 1px solid rgba(128, 128, 128, 0.4) !important;
#         color: var(--text-color) !important;
#         border-radius: 12px !important;
#     }
#     .stChatInput textarea:focus {
#         border-color: #3b82f6 !important;
#         box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
#     }

#     /* --- TOOL CARDS --- */
#     .tool-card {
#         background-color: var(--background-color);
#         border-left: 4px solid #3b82f6;
#         border-radius: 6px;
#         padding: 12px;
#         margin: 8px 0;
#         font-family: 'Fira Code', monospace;
#         font-size: 0.85em;
#         color: var(--text-color);
#         border: 1px solid rgba(128, 128, 128, 0.2);
#         opacity: 0.9;
#     }
    
#     .icon {
#         margin-right: 8px;
#         font-size: 1.2em;
#     }

#     /* --- BUTTONS --- */
#     .stButton button {
#         background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
#         color: white !important;
#         border: none;
#         border-radius: 8px;
#         font-weight: 600;
#         transition: opacity 0.2s;
#     }
#     .stButton button:hover {
#         opacity: 0.9;
#         box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
#     }

#     /* --- HEADERS --- */
#     h1 {
#         background: linear-gradient(90deg, #3b82f6, #06b6d4);
#         -webkit-background-clip: text;
#         -webkit-text-fill-color: transparent;
#         font-weight: 800;
#         padding-bottom: 10px;
#     }

#     /* Status Container */
#     .stStatus {
#         background-color: var(--secondary-background-color);
#         border: 1px solid rgba(128, 128, 128, 0.2);
#     }

#     /* Error/Success Cards */
#     .error-card {
#         background-color: rgba(254, 226, 226, 0.5); /* Light Red */
#         color: #b91c1c;
#         padding: 10px;
#         border-radius: 8px;
#         border-left: 4px solid #ef4444;
#     }
#     /* Dark mode override for error card using media query */
#     @media (prefers-color-scheme: dark) {
#         .error-card {
#             background-color: rgba(127, 29, 29, 0.3);
#             color: #fca5a5;
#         }
#     }
# </style>
# """, unsafe_allow_html=True)

# # -----------------------------------------------------------------------------
# # 3. CONSTANTS & GUIDES
# # -----------------------------------------------------------------------------
# TOOL_ICONS = {
#     "gmail": "📧", "calendar": "📅", "drive": "📂", 
#     "docs": "📄", "slides": "📊", "sheets": "📗", 
#     "web_search": "🌐", "default": "🔧"
# }

# GOOGLE_SETUP_GUIDE = """
# ### 🔐 Google Workspace Setup Guide

# **Step 1: Create a Project**
# 1. Go to [Google Cloud Console](https://console.cloud.google.com/)
# 2. Click "Select a project" > "New Project" > Name it "Workspace Agent"

# **Step 2: Enable APIs**
# - Gmail API
# - Google Drive API
# - Google Calendar API
# - Google Docs API
# - Google Slides API
# - Google Sheets API

# **Step 3: Create OAuth 2.0 Credentials**
# - Application Type: **Web Application** (NOT Desktop)
# - Authorized redirect URIs:
#     - `http://localhost`
#     - `http://localhost:8080/`
#     - `http://127.0.0.1`
# - Download JSON and extract Client ID & Secret

# **Step 4: Configure Consent Screen**
# - Add required scopes (`.../auth/gmail.readonly`, etc)
# - Add test users if in testing mode
# """

# GOOGLE_WORKSPACE_INSTRUCTIONS = """
# **ROLE:** Expert Google Workspace Assistant
# **GOAL:** Manage Gmail, Drive, Calendar, Docs, Slides securely

# **AUTH RULE:** If tool returns "ACTION REQUIRED: Google Authentication Needed":
# 1. STOP immediately
# 2. Present URL to user
# 3. Wait for confirmation before retry

# **SLIDES API RULES:**
# - NEVER use 'slide1' as objectId
# - NEVER replaceAllText with empty text

# **USER:** lmswecrunch@gmail.com
# """

# # -----------------------------------------------------------------------------
# # 4. HELPER FUNCTIONS
# # -----------------------------------------------------------------------------
# def api_key_input(label, key_type, help_text=""):
#     """Reusable API key input with persistent storage"""
#     current_value = st.session_state.api_keys.get(key_type, "")
    
#     new_value = st.text_input(
#         label, 
#         value=current_value,
#         type="password",
#         help=help_text,
#         placeholder="Enter your API key..."
#     )
    
#     st.session_state.api_keys[key_type] = new_value
    
#     # Show source indicator
#     env_key_map = {
#         "deepseek": "DEEPSEEK_API_KEY",
#         "openai": "OPENAI_API_KEY",
#         "google_id": "GOOGLE_OAUTH_CLIENT_ID",
#         "google_secret": "GOOGLE_OAUTH_CLIENT_SECRET"
#     }
    
#     if os.getenv(env_key_map[key_type]):
#         st.caption("🔒 Loaded from environment")
#     elif current_value:
#         st.caption("💾 Saved in session")
    
#     return new_value

# def test_api_key(service, key):
#     """Test if an API key is valid"""
#     if not key:
#         return False, "No key provided"
    
#     try:
#         if service == "deepseek":
#             llm = ChatDeepSeek(api_key=key, model="deepseek-coder")
#             llm.invoke("Hello")
#             return True, "✅ Key is valid!"
#         elif service == "openai":
#             client = OpenAI(api_key=key)
#             client.models.list()
#             return True, "✅ Key is valid!"
#         return False, "Unknown service"
#     except Exception as e:
#         return False, f"❌ Error: {str(e)[:100]}"

# def test_mcp_server():
#     """Test if MCP server can start and respond"""
#     try:
#         server_env = os.environ.copy()
#         server_env.update({
#             "GOOGLE_OAUTH_CLIENT_ID": st.session_state.api_keys["google_id"],
#             "GOOGLE_OAUTH_CLIENT_SECRET": st.session_state.api_keys["google_secret"],
#             "OPENAI_API_KEY": st.session_state.api_keys["openai"]
#         })
        
#         # Check server files exist
#         if not MCP_SERVER_PATH.exists():
#             return False, f"❌ Server path does not exist: {MCP_SERVER_PATH}"
        
#         if not (MCP_SERVER_PATH / "main.py").exists():
#             return False, f"❌ main.py not found in {MCP_SERVER_PATH}"
        
#         # Detect server type
#         if (MCP_SERVER_PATH / "uv.lock").exists():
#             cmd, args = "uv", ["--directory", str(MCP_SERVER_PATH), "run", "main.py"]
#         elif (MCP_SERVER_PATH / "requirements.txt").exists():
#             cmd, args = "python", [str(MCP_SERVER_PATH / "main.py")]
#         else:
#             return False, "❌ No server startup method found (no uv.lock or requirements.txt)"
        
#         # Check if command exists
#         if cmd == "uv":
#             try:
#                 subprocess.run(["uv", "--version"], capture_output=True, check=True)
#             except:
#                 return False, "❌ uv package manager not found. Install with: pip install uv"
        
#         # Test server startup with timeout
#         proc = subprocess.Popen([cmd] + args, env=server_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#         try:
#             stdout, stderr = proc.communicate(timeout=5)
#             if proc.returncode != 0:
#                 error_msg = stderr.decode() if stderr else stdout.decode()
#                 return False, f"❌ Server failed to start:\n```\n{error_msg[:300]}\n```"
#             return True, "✅ Server executable is valid"
#         except subprocess.TimeoutExpired:
#             proc.kill()
#             proc.wait()
#             return True, "✅ Server started successfully (timeout expected for long-running process)"
#         except Exception as e:
#             proc.kill()
#             return False, f"❌ Unexpected error during server test: {str(e)}"
            
#     except Exception as e:
#         return False, f"❌ MCP Server Error: {str(e)}\n\nTraceback:\n```\n{traceback.format_exc()}\n```"

# def validate_credentials():
#     """Check if all required credentials are present"""
#     keys = st.session_state.api_keys
#     missing = []
    
#     for key_name, value in keys.items():
#         if not value:
#             missing.append(key_name.replace("_", " ").title())
    
#     return len(missing) == 0, missing

# def get_icon_for_tool(tool_name: str) -> str:
#     tool_name = tool_name.lower()
#     for key, icon in TOOL_ICONS.items():
#         if key in tool_name:
#             return icon
#     return TOOL_ICONS["default"]

# def log_mcp_event(event):
#     """Log MCP events for debugging"""
#     st.session_state.mcp_logs.append({
#         "timestamp": time.time(),
#         "event": str(event)[:200]
#     })

# # -----------------------------------------------------------------------------
# # 5. CORE AGENT LOGIC
# # -----------------------------------------------------------------------------
# async def run_agent(user_input, chat_history, keys, debug=False):
#     """Runs the DeepSeek Agent via MCP with enhanced error handling"""
    
#     try:
#         # Validate MCP server first
#         is_valid, server_msg = test_mcp_server()
#         if not is_valid:
#             return f"❌ MCP Server Validation Failed:\n\n{server_msg}"
        
#         # Prepare environment
#         server_env = os.environ.copy()
#         server_env["GOOGLE_OAUTH_CLIENT_ID"] = keys['google_id']
#         server_env["GOOGLE_OAUTH_CLIENT_SECRET"] = keys['google_secret']
#         server_env["OPENAI_API_KEY"] = keys['openai']
        
#         # Detect server type
#         if (MCP_SERVER_PATH / "uv.lock").exists():
#             cmd, args = "uv", ["--directory", str(MCP_SERVER_PATH), "run", "main.py"]
#         elif (MCP_SERVER_PATH / "requirements.txt").exists():
#             cmd, args = "python", [str(MCP_SERVER_PATH / "main.py")]
#         else:
#             raise FileNotFoundError(f"No server startup method found in {MCP_SERVER_PATH}")
        
#         server_params = StdioServerParameters(command=cmd, args=args, env=server_env)
        
#         status_box = st.status("🤖 Initializing AI Agent...", expanded=True)
        
#         if debug:
#             status_box.write(f"🛠️ Server Path: {MCP_SERVER_PATH}")
#             status_box.write(f"🛠️ Command: {' '.join([cmd] + args)}")
        
#         # Initialize LLM
#         status_box.write("🧠 Loading DeepSeek model...")
#         llm = ChatDeepSeek(
#             model="deepseek-coder",
#             temperature=0,
#             api_key=keys['deepseek']
#         )
        
#         web_tool = make_web_search_tool(keys['openai'])
        
#         # Connect to MCP
#         status_box.write("🔌 Establishing secure MCP connection...")
        
#         try:
#             async with stdio_client(server_params) as (read, write):
#                 async with ClientSession(read, write) as session:
                    
#                     status_box.write("🛠️ Loading Google Workspace tools...")
                    
#                     # Initialize session
#                     await session.initialize()
                    
#                     # Load tools
#                     try:
#                         mcp_tools = await load_mcp_tools(session)
#                     except Exception as e:
#                         raise RuntimeError(f"Failed to load MCP tools: {str(e)}")
                    
#                     # Wrap tools in error handlers
#                     safe_tools = []
#                     for tool in mcp_tools:
#                         try:
#                             safe_tools.append(SafeTool(tool, tool.name, tool.description))
#                         except Exception as e:
#                             status_box.warning(f"⚠️ Skipping tool {tool.name}: {e}")
#                             continue
                    
#                     if not safe_tools:
#                         raise RuntimeError("No valid tools loaded from MCP server")
                    
#                     # Create agent
#                     agent = create_deep_agent(
#                         [web_tool] + safe_tools,
#                         GOOGLE_WORKSPACE_INSTRUCTIONS,
#                         model=llm
#                     )
                    
#                     status_box.update(label="🧠 Processing your request...", state="running")
                    
#                     # Prepare messages
#                     messages = []
#                     for m in chat_history:
#                         if m["role"] == "user":
#                             messages.append(HumanMessage(content=m["content"]))
#                         else:
#                             messages.append(AIMessage(content=m["content"]))
#                     messages.append(HumanMessage(content=user_input))

#                     final_resp = ""

#                     # Process agent stream
#                     async for event in agent.astream({"messages": messages}, stream_mode="updates"):
#                         for _, node_data in event.items():
#                             if "messages" not in node_data:
#                                 continue
                            
#                             msg_list = node_data["messages"] if isinstance(node_data["messages"], list) else [node_data["messages"]]
                            
#                             for msg in msg_list:
#                                 # Tool Call
#                                 if hasattr(msg, "tool_calls") and msg.tool_calls:
#                                     for tc in msg.tool_calls:
#                                         t_name = tc.get("name", "unknown")
#                                         icon = get_icon_for_tool(t_name)
#                                         args_preview = str(tc.get('args', {}))[:80]
                                        
#                                         status_box.markdown(f"""
#                                             <div class="tool-card">
#                                                 <span class="icon">{icon}</span>
#                                                 <b>Executing:</b> {t_name}<br>
#                                                 <span style="opacity:0.7; font-size:0.8em">{args_preview}...</span>
#                                             </div>
#                                         """, unsafe_allow_html=True)

#                                 # Tool Output
#                                 elif isinstance(msg, ToolMessage) or msg.type == "tool":
#                                     text = str(msg.content)
                                    
#                                     # Check for Auth URL
#                                     if "Authorization URL" in text or "accounts.google.com" in text:
#                                         url_match = re.search(r"(https?://accounts\.google\.com/o/oauth2/auth\?[^\s]+)", text)
#                                         if url_match:
#                                             url = url_match.group(1).rstrip(".,)]>")
#                                             status_box.error("🛑 Google Authentication Required")
#                                             st.link_button("🔐 Click to Authorize Google Access", url)
#                                             return "⚠️ Please authenticate with Google using the button above, then try your request again."

#                                     status_box.markdown(f"<span style='color:#3b82f6'>✅ Tool completed successfully</span>", unsafe_allow_html=True)

#                                 # AI Response
#                                 elif isinstance(msg, AIMessage) or msg.type == "ai":
#                                     if msg.content and msg.content != final_resp:
#                                         final_resp = msg.content
#                                         with st.chat_message("assistant"):
#                                             st.markdown(final_resp)
                    
#                     status_box.update(label="✅ Task completed successfully", state="complete", expanded=False)
#                     return final_resp

#         except Exception as e:
#             raise RuntimeError(f"MCP connection error: {str(e)}")

#     except FileNotFoundError as e:
#         return f"❌ File Error: {str(e)}\n\nPlease verify MCP_SERVER_PATH is correct and all files exist."
#     except RuntimeError as e:
#         return f"❌ Runtime Error: {str(e)}"
#     except Exception as e:
#         error_msg = f"❌ Unexpected Error: {type(e).__name__}: {str(e)}"
#         if debug:
#             error_msg += f"\n\n<details>\n<summary>Full Traceback</summary>\n\n```\n{traceback.format_exc()}\n```\n</details>"
#         return error_msg

# def make_web_search_tool(openai_key: str) -> StructuredTool:
#     def web_search(query: str) -> str:
#         if not openai_key: return "Error: No OpenAI API Key provided."
#         client = OpenAI(api_key=openai_key)
#         try:
#             response = client.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {"role": "system", "content": "You are a tech researcher. Summarize concise technical info."},
#                     {"role": "user", "content": f"Query: {query}"},
#                 ],
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"Search Error: {e}"

#     return StructuredTool.from_function(
#         name="web_search",
#         description="Search the web for current information.",
#         func=web_search,
#     )

# class SafeTool(BaseTool):
#     """Prevents tool crashes from killing the agent."""
#     _inner: Any = PrivateAttr()
#     _tool_name: str = PrivateAttr()

#     def __init__(self, inner_tool: Any, name: str, description: str):
#         super().__init__(name=name, description=description)
#         self._inner = inner_tool
#         self._tool_name = name
#         if hasattr(inner_tool, "args_schema"):
#             self.args_schema = inner_tool.args_schema

#     def _run(self, **kwargs) -> str:
#         try:
#             res = self._inner.invoke(kwargs) if hasattr(self._inner, "invoke") else self._inner(kwargs)
#             return json.dumps({"ok": True, "tool": self._tool_name, "result": res}, default=str)
#         except Exception as e:
#             return json.dumps({"ok": False, "tool": self._tool_name, "error": str(e)}, default=str)

#     async def _arun(self, **kwargs) -> str:
#         try:
#             if hasattr(self._inner, "ainvoke"):
#                 res = await self._inner.ainvoke(kwargs)
#             else:
#                 res = self._run(**kwargs)
#             return json.dumps({"ok": True, "tool": self._tool_name, "result": res}, default=str)
#         except Exception as e:
#             return json.dumps({"ok": False, "tool": self._tool_name, "error": str(e)}, default=str)

# # -----------------------------------------------------------------------------
# # 6. UI LAYOUT
# # -----------------------------------------------------------------------------
# def main():
#     # --- Sidebar Configuration ---
#     with st.sidebar:
#         st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>⚙️ Configuration</h2>", unsafe_allow_html=True)
        
#         # Debug Mode Toggle
#         st.session_state.debug_mode = st.checkbox("🐛 Debug Mode", value=st.session_state.debug_mode, help="Show detailed error information and additional logging")
        
#         # MCP Server Status
#         st.markdown("### 🖥️ MCP Server")
#         if st.button("🔍 Test MCP Connection"):
#             with st.spinner("Testing server connection..."):
#                 is_valid, msg = test_mcp_server()
#                 if is_valid:
#                     st.success(msg)
#                 else:
#                     st.error(msg)
#                     if st.session_state.debug_mode:
#                         st.markdown('<div class="debug-panel">' + msg + '</div>', unsafe_allow_html=True)
        
#         # API Keys Section
#         with st.expander("🔑 API Keys", expanded=True):
#             st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            
#             # DeepSeek Key
#             st.subheader("🤖 DeepSeek API")
#             deepseek_key = api_key_input(
#                 "DeepSeek API Key", 
#                 "deepseek",
#                 "Get from platform.deepseek.com"
#             )
#             if deepseek_key and st.button("Test DeepSeek", key="test_ds"):
#                 valid, msg = test_api_key("deepseek", deepseek_key)
#                 st.markdown(f'<div class="{"success-card" if "✅" in msg else "error-card"}">{msg}</div>', unsafe_allow_html=True)
            
#             st.markdown("---")
            
#             # OpenAI Key
#             st.subheader("🔍 OpenAI API (Search)")
#             openai_key = api_key_input(
#                 "OpenAI API Key",
#                 "openai", 
#                 "For web search functionality"
#             )
#             if openai_key and st.button("Test OpenAI", key="test_oa"):
#                 valid, msg = test_api_key("openai", openai_key)
#                 st.markdown(f'<div class="{"success-card" if "✅" in msg else "error-card"}">{msg}</div>', unsafe_allow_html=True)
            
#             st.markdown("---")
            
#             # Google Credentials
#             st.subheader("🔐 Google OAuth")
#             google_id = api_key_input("Client ID", "google_id")
#             google_secret = api_key_input("Client Secret", "google_secret")
            
#             # Save/Load Client Secrets
#             st.markdown("**Client Secrets JSON**")
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 if st.button("💾 Save", help="Save credentials to client_secret.json"):
#                     if google_id and google_secret:
#                         secret_path = MCP_SERVER_PATH / "client_secret.json"
#                         # Standard Redirect URIs including port 8080 and port-less
#                         data = {
#                             "installed": {
#                                 "client_id": google_id,
#                                 "client_secret": google_secret,
#                                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                                 "token_uri": "https://oauth2.googleapis.com/token",
#                                 "redirect_uris": ["http://localhost", "http://localhost:8080/"]
#                             }
#                         }
#                         with open(secret_path, "w") as f:
#                             json.dump(data, f, indent=2)
#                         st.success("✅ Saved client_secret.json!")
#                     else:
#                         st.error("❌ Please enter both Client ID and Secret")
            
#             with col2:
#                 if st.button("📂 Load", help="Load existing client_secret.json"):
#                     secret_path = MCP_SERVER_PATH / "client_secret.json"
#                     if secret_path.exists():
#                         with open(secret_path, "r") as f:
#                             data = json.load(f)
#                         creds = data.get("installed", {})
#                         st.session_state.api_keys["google_id"] = creds.get("client_id", "")
#                         st.session_state.api_keys["google_secret"] = creds.get("client_secret", "")
#                         st.success("✅ Loaded existing credentials!")
#                         st.rerun()
#                     else:
#                         st.error("❌ No client_secret.json found")
            
#             st.markdown('</div>', unsafe_allow_html=True)
        
#         # Save configuration
#         if st.button("💾 Save All Settings", help="Persist keys to local config file"):
#             save_config({
#                 "deepseek_key": st.session_state.api_keys["deepseek"],
#                 "openai_key": st.session_state.api_keys["openai"],
#                 "google_id": st.session_state.api_keys["google_id"],
#                 "google_secret": st.session_state.api_keys["google_secret"]
#             })
#             st.success("✅ Settings saved to disk!")
        
#         if st.button("🗑️ Clear Saved Settings", help="Remove saved config file"):
#             if CONFIG_PATH.exists():
#                 CONFIG_PATH.unlink()
#             st.success("✅ Saved settings cleared!")
#             st.rerun()
        
#         st.markdown("---")
        
#         # Guide Section
#         with st.expander("📚 Setup Guide"):
#             st.markdown(GOOGLE_SETUP_GUIDE)
        
#         # Debug Log
#         if st.session_state.debug_mode and st.session_state.mcp_logs:
#             with st.expander("📋 MCP Event Log"):
#                 for log in st.session_state.mcp_logs[-10:]:  # Show last 10 events
#                     st.text(f"{log['timestamp']}: {log['event']}")
        
#         # User Info
#         if USER_GOOGLE_EMAIL := os.getenv("USER_GOOGLE_EMAIL"):
#             st.markdown(f'<div class="glass-card"><span class="icon">👤</span>{USER_GOOGLE_EMAIL}</div>', unsafe_allow_html=True)
    
#     # --- Main Content ---
#     st.markdown('<div class="glass-card">', unsafe_allow_html=True)
#     st.title("Workspace Agent")
#     st.caption("AI-Powered Automation for Google Workspace")
#     st.markdown('</div>', unsafe_allow_html=True)
    
#     # Validation
#     is_configured, missing = validate_credentials()
    
#     if not is_configured:
#         st.warning("⚠️ Configuration Required")
#         st.info(f"Please configure the following in the sidebar: **{', '.join(missing)}**")
#         return
    
#     # MCP Server Requirements Check
#     if not MCP_SERVER_PATH.exists():
#         st.error(f"❌ MCP Server path does not exist: {MCP_SERVER_PATH}")
#         st.info("Please update MCP_SERVER_PATH in the code to point to your Google Workspace MCP server directory.")
#         return
    
#     if not (MCP_SERVER_PATH / "main.py").exists():
#         st.error(f"❌ main.py not found in {MCP_SERVER_PATH}")
#         st.info("Make sure your MCP server has a main.py file.")
#         return
    
#     # Chat Interface
#     if "messages" not in st.session_state:
#         st.session_state.messages = [{
#             "role": "assistant", 
#             "content": "🚀 Hello! Your AI workspace agent is ready. I can help you search emails, manage calendars, organize Drive files, and create documents. What would you like to accomplish today?"
#         }]

#     # Display chat history
#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     # Chat input
#     if prompt := st.chat_input("💬 Describe your task..."):
#         # Clear previous logs
#         st.session_state.mcp_logs = []
        
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         with st.chat_message("user"):
#             st.markdown(prompt)

#         # Run agent
#         with st.chat_message("assistant"):
#             response = asyncio.run(run_agent(prompt, st.session_state.messages[:-1], st.session_state.api_keys, st.session_state.debug_mode))
            
#             # Show debug info if enabled and error occurred
#             if st.session_state.debug_mode and "❌" in response:
#                 with st.expander("🔍 Debug Information", expanded=True):
#                     st.markdown(f'<div class="debug-panel">{response}</div>', unsafe_allow_html=True)
#             else:
#                 st.markdown(response)
            
#             st.session_state.messages.append({"role": "assistant", "content": response})

# if __name__ == "__main__":
#     main()



import streamlit as st
import asyncio
import os
import re
import json
import ast
import subprocess
import uuid
import traceback
import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from dotenv import load_dotenv
load_dotenv()

from pydantic import PrivateAttr, BaseModel, Field

from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage, BaseMessage
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from deepagents import create_deep_agent
from openai import OpenAI

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from src.learning import extract_and_save_skill, process_past_logs


CONFIG_PATH = Path.home() / ".workspace_agent" / "config.json"
CONFIG_PATH.parent.mkdir(exist_ok=True)
CONVERSATIONS_DIR = Path(__file__).parent / "conversations"
MEMORY_FILE = Path(__file__).parent / "memory.txt"
ERROR_HISTORY_FILE = Path(__file__).parent / "error_history.txt"
BEST_PRACTICES_FILE = Path(__file__).parent / "best_practices.txt"
SKILLS_DIR = Path(__file__).parent / "skills"
ROUTINES_FILE = Path(__file__).parent / "routines.json"

# MCP_SERVER_PATH = Path(r"C:\WeCrunch\experiments\ease_workspace\google_workspace_mcp")
MCP_SERVER_PATH = Path(os.getenv("MCP_SERVER_PATH", r"C:\WeCrunch\experiments\ease_workspace\google_workspace_mcp"))

TOOL_ICONS = {
    "gmail": "📧", "calendar": "📅", "drive": "📂",
    "docs": "📄", "slides": "📊", "sheets": "📗",
    "web_search": "🌐", "default": "🔧"
}

GOOGLE_WORKSPACE_GUIDE_PATH = Path(__file__).parent / "docs" / "google_workspace_setup.md"

GOOGLE_SETUP_GUIDE = """
### 🔐 Google Workspace Setup Guide
Create a Google Cloud project, enable the Workspace APIs, and configure OAuth.

Quick steps:
1) Google Cloud Console -> New Project (or select existing).
2) APIs & Services -> Library -> enable:
   Gmail API, Google Drive API, Google Calendar API, Google Docs API,
   Google Slides API, Google Sheets API.
3) OAuth consent screen -> choose External, fill in app name + support email,
   add your email as a test user, and save.
4) Credentials -> Create Credentials -> OAuth Client ID -> Web application.
5) Add Redirect URIs:
   - http://localhost
   - http://localhost:8080/
   - http://127.0.0.1
6) Download the client JSON and keep it secure.

Full guide: docs/google_workspace_setup.md
"""

GOOGLE_WORKSPACE_INSTRUCTIONS = """
ROLE: Expert Google Workspace Assistant
GOAL: Manage Gmail, Drive, Calendar, Docs, Slides securely.

AUTH RULE: If tool returns "ACTION REQUIRED: Google Authentication Needed":
1) STOP immediately
2) Present URL to user
3) Wait for confirmation before retry

SLIDES API RULES:
- NEVER use 'slide1' as objectId
- NEVER replaceAllText with empty text

USER: lmswecrunch@gmail.com
"""

MAIN_CHAT_SYSTEM = """
You are the primary chat assistant for this app.

You can:
- respond normally (chat), OR
- trigger the Google Workspace Agent when the request requires Gmail/Drive/Calendar/Docs/Sheets/Slides actions.

When tool results exist, always use them as conversation context.
If user says "add this to sheet", interpret "this" as the most recent email list/summary/tool output.
Be concise but helpful.
"""

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
- Any request involving local file system operations or running system commands.

Return ONLY valid JSON with keys: route, reason.
route must be exactly "ASSISTANT" or "AGENT".
No extra text.
"""

DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "google": "gemini-3-flash-preview",
    "anthropic": "claude-3-5-sonnet-20240620",
    "deepseek": "deepseek-chat",
}


class RouteDecision(BaseModel):
    route: str = Field(..., description='Either "ASSISTANT" or "AGENT"')
    reason: str = Field(..., description="Short reason for routing")


def normalize_text(value: Any, default: str = "") -> str:
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else default
    if value is None:
        return default
    return str(value)


def init_llm(provider: str, model_name: str, temperature: float, keys: Dict[str, str]):
    provider = normalize_text(provider, "deepseek").lower()
    model_name = normalize_text(model_name, DEFAULT_MODELS.get(provider, ""))
    if provider == "openai":
        api_key = keys.get("openai") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found.")
        return ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
    if provider == "google":
        api_key = keys.get("gemini") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) not found.")
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            convert_system_message_to_human=True,
        )
    if provider == "anthropic":
        api_key = keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found.")
        return ChatAnthropic(model=model_name, temperature=temperature, api_key=api_key)
    if provider == "deepseek":
        api_key = keys.get("deepseek") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not found.")
        return ChatDeepSeek(model=model_name, temperature=temperature, api_key=api_key)
    raise ValueError(f"Unknown provider: {provider}")


# -----------------------------------------------------------------------------
# Config persistence
# -----------------------------------------------------------------------------
def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(data: dict):
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_configured_keys() -> dict:
    config = load_config()
    return {
        "deepseek": os.getenv("DEEPSEEK_API_KEY", config.get("deepseek_key", "")),
        "openai": os.getenv("OPENAI_API_KEY", config.get("openai_key", "")),
        "gemini": os.getenv("GEMINI_API_KEY", config.get("gemini_key", "")),
        "anthropic": os.getenv("ANTHROPIC_API_KEY", config.get("anthropic_key", "")),
        "google_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", config.get("google_id", "")),
        "google_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", config.get("google_secret", "")),
    }


def load_memory() -> str:
    if MEMORY_FILE.exists():
        try:
            return MEMORY_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    return ""


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "api_keys" not in st.session_state:
    st.session_state.api_keys = get_configured_keys()

if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "🚀 Hello! I can chat normally and also run Google Workspace actions. What do you want to do?"
    }]

# ensures input stays at bottom
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "last_agent_trace" not in st.session_state:
    st.session_state.last_agent_trace = []

# IMPORTANT: memory for follow-ups like “add this to sheet”
if "memory" not in st.session_state:
    st.session_state.memory = {
        "last_tool_output": "",
        "last_emails_payload": "",  # store top emails result so next message can reference “this”
    }

if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = os.getenv("MODEL_PROVIDER", "deepseek").lower()

if "llm_model" not in st.session_state:
    st.session_state.llm_model = os.getenv(
        "MODEL_NAME",
        DEFAULT_MODELS.get(st.session_state.llm_provider, DEFAULT_MODELS["deepseek"]),
    )

if "llm_temperature" not in st.session_state:
    try:
        st.session_state.llm_temperature = float(os.getenv("MODEL_TEMPERATURE", "0.2"))
    except ValueError:
        st.session_state.llm_temperature = 0.2

if "use_llm_router" not in st.session_state:
    st.session_state.use_llm_router = True

if "auto_memory" not in st.session_state:
    st.session_state.auto_memory = True

if "allow_terminal_tool" not in st.session_state:
    st.session_state.allow_terminal_tool = False

if "memory_text" not in st.session_state:
    st.session_state.memory_text = ""

if "log_file" not in st.session_state:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.log_file = CONVERSATIONS_DIR / f"conversation_{timestamp}.txt"

if "last_route" not in st.session_state:
    st.session_state.last_route = {"route": "ASSISTANT", "reason": "Not routed yet."}

if not st.session_state.memory_text:
    st.session_state.memory_text = load_memory()

if "routine_log_path" not in st.session_state:
    st.session_state.routine_log_path = None

if "show_routine_log" not in st.session_state:
    st.session_state.show_routine_log = False

if "show_google_guide" not in st.session_state:
    st.session_state.show_google_guide = False

if "pending_delete_routine_id" not in st.session_state:
    st.session_state.pending_delete_routine_id = None


config_cache = load_config()
if config_cache.get("llm_provider") and not os.getenv("MODEL_PROVIDER"):
    st.session_state.llm_provider = config_cache.get("llm_provider", st.session_state.llm_provider)
if config_cache.get("llm_model") and not os.getenv("MODEL_NAME"):
    st.session_state.llm_model = config_cache.get("llm_model", st.session_state.llm_model)
if config_cache.get("llm_temperature") is not None and not os.getenv("MODEL_TEMPERATURE"):
    try:
        st.session_state.llm_temperature = float(config_cache.get("llm_temperature"))
    except ValueError:
        pass
if config_cache.get("allow_terminal_tool") is not None:
    st.session_state.allow_terminal_tool = bool(config_cache.get("allow_terminal_tool"))
if config_cache.get("auto_memory") is not None:
    st.session_state.auto_memory = bool(config_cache.get("auto_memory"))
# -----------------------------------------------------------------------------
# Page config + CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Workspace Agent", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Manrope:wght@400;600;700&display=swap');

:root {
  --brand-1: #2563eb;
  --brand-2: #06b6d4;
  --brand-3: #0ea5e9;
  --card-border: rgba(128, 128, 128, 0.18);
  --card-shadow: 0 10px 30px rgba(2, 6, 23, 0.08);
}

html, body, [class*="css"] { font-family: "Manrope", sans-serif; }
h1, h2, h3, .brand-title { font-family: "Space Grotesk", sans-serif; }

.stApp {
  background:
    radial-gradient(1200px 600px at 18% -10%, rgba(37, 99, 235, 0.20), transparent 60%),
    radial-gradient(900px 500px at 90% 0%, rgba(6, 182, 212, 0.20), transparent 60%),
    var(--background-color);
}

section[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid rgba(128, 128, 128, 0.2);
}

@keyframes riseIn {
  from { transform: translateY(6px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.header-wrap {
  border: 1px solid var(--card-border);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(6, 182, 212, 0.10));
  border-radius: 18px;
  padding: 18px 20px;
  margin-bottom: 14px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  box-shadow: var(--card-shadow);
  animation: riseIn 0.4s ease-out;
}
.brand-title {
  font-weight: 700;
  font-size: 1.45rem;
  background: linear-gradient(90deg, var(--brand-1), var(--brand-2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}
.brand-sub { opacity: 0.8; margin-top: 2px; font-size: 0.95rem; }
.pill {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(37, 99, 235, 0.3);
  background: rgba(37, 99, 235, 0.08);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--brand-1);
}

.stChatMessage {
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 0.75rem 0.85rem;
  box-shadow: 0 8px 18px rgba(2, 6, 23, 0.06);
  animation: riseIn 0.3s ease-out;
}

.tool-bubble {
  border: 1px dashed rgba(37, 99, 235, 0.35);
  background: rgba(59,130,246,0.07);
  border-radius: 14px;
  padding: 12px 12px;
  margin: 6px 0;
}
.tool-bubble .title { font-weight: 700; margin-bottom: 6px; color: var(--brand-1); }
.small-muted { opacity: 0.85; font-size: 0.92rem; }

.tool-card {
  background-color: var(--secondary-background-color);
  border: 1px solid var(--card-border);
  border-left: 4px solid var(--brand-1);
  border-radius: 12px;
  padding: 10px 12px;
  margin: 6px 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.88em;
}

.success-card {
  background-color: rgba(34, 197, 94, 0.12);
  border-left: 4px solid rgba(34, 197, 94, 1);
  border-radius: 12px;
  padding: 10px 12px;
}
.error-card {
  background-color: rgba(239, 68, 68, 0.12);
  border-left: 4px solid rgba(239, 68, 68, 1);
  border-radius: 12px;
  padding: 10px 12px;
}

.stButton > button,
button[kind="primary"] {
  background: linear-gradient(90deg, var(--brand-1) 0%, var(--brand-3) 100%);
  color: white !important;
  border: none;
  border-radius: 12px;
  font-weight: 700;
  letter-spacing: 0.2px;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.25);
}
.stButton > button:hover,
button[kind="primary"]:hover {
  filter: brightness(1.05);
}

section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] button[kind="primary"] {
  background: linear-gradient(90deg, var(--brand-1) 0%, var(--brand-3) 100%) !important;
  color: #fff !important;
  border: none !important;
}

.stButton button[kind="secondary"] {
  background: var(--secondary-background-color) !important;
  color: var(--text-color) !important;
  border: 1px solid var(--card-border);
  box-shadow: 0 6px 12px rgba(15, 23, 42, 0.08);
  font-weight: 700;
  text-decoration: none;
}

.stChatInput textarea {
  background-color: var(--secondary-background-color) !important;
  border: 1px solid rgba(128,128,128,0.28) !important;
  color: var(--text-color) !important;
  border-radius: 14px !important;
}

/* Tabs */
button[data-baseweb="tab"] {
  border-radius: 10px;
  font-weight: 700;
}

div[role="dialog"] {
  width: 85vw !important;
  max-width: 1100px !important;
}

.routine-header {
  font-weight: 700;
  color: var(--text-color);
  letter-spacing: 0.2px;
  background: rgba(37, 99, 235, 0.08);
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 10px;
  padding: 8px 10px;
}
.routine-row {
  background: var(--secondary-background-color);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 8px 10px;
  box-shadow: 0 6px 16px rgba(2, 6, 23, 0.05);
  margin-bottom: 8px;
}
.routine-cell {
  font-weight: 600;
  min-height: 44px;
  display: flex;
  align-items: center;
}
.status-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.85em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  white-space: nowrap;
}
.status-pill::before {
  content: "";
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 999px;
  background: currentColor;
  vertical-align: middle;
}
.status-working {
  background: rgba(34, 197, 94, 0.15);
  color: rgba(21, 128, 61, 1);
}
.status-pending {
  background: rgba(59, 130, 246, 0.15);
  color: rgba(37, 99, 235, 1);
}
.status-paused {
  background: rgba(245, 158, 11, 0.18);
  color: rgba(180, 83, 9, 1);
}
.status-stopped {
  background: rgba(239, 68, 68, 0.15);
  color: rgba(185, 28, 28, 1);
}
.status-completed {
  background: rgba(16, 185, 129, 0.15);
  color: rgba(5, 150, 105, 1);
}
.status-unknown {
  background: rgba(148, 163, 184, 0.2);
  color: rgba(71, 85, 105, 1);
}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def get_icon_for_tool(tool_name: str) -> str:
    t = (tool_name or "").lower()
    for key, icon in TOOL_ICONS.items():
        if key in t:
            return icon
    return TOOL_ICONS["default"]


def validate_credentials() -> Tuple[bool, List[str]]:
    keys = st.session_state.api_keys
    missing = []
    provider = st.session_state.llm_provider
    provider_key_map = {
        "deepseek": "deepseek",
        "openai": "openai",
        "google": "gemini",
        "anthropic": "anthropic",
    }
    provider_key = provider_key_map.get(provider)
    if provider_key and not keys.get(provider_key):
        missing.append(provider_key.replace("_", " ").title())

    if not keys.get("google_id"):
        missing.append("Google Id")
    if not keys.get("google_secret"):
        missing.append("Google Secret")
    return len(missing) == 0, missing


def api_key_input(label, key_type, help_text=""):
    current_value = st.session_state.api_keys.get(key_type, "")
    new_value = st.text_input(label, value=current_value, type="password", help=help_text)
    st.session_state.api_keys[key_type] = new_value
    return new_value


def get_llm():
    return init_llm(
        st.session_state.llm_provider,
        st.session_state.llm_model,
        st.session_state.llm_temperature,
        st.session_state.api_keys,
    )


def build_router_llm(llm):
    try:
        return llm.with_structured_output(RouteDecision)
    except Exception:
        return None


async def decide_route(router_llm_structured, llm, chat_history: List[Dict[str, Any]]) -> RouteDecision:
    router_messages: List[BaseMessage] = [SystemMessage(content=ROUTER_INSTRUCTIONS)]
    router_messages.extend(convert_history_to_messages(chat_history, include_tool_messages=True))

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


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    return asyncio.run(coro)


def save_conversation_log(chat_history: List[Dict[str, Any]], filepath: Path) -> None:
    try:
        filepath.parent.mkdir(exist_ok=True, parents=True)
        output = []
        for msg in chat_history:
            role = msg.get("role", "assistant").upper()
            content = msg.get("content", "")
            output.append(f"[{role}]\n{content}\n")
        filepath.write_text("\n".join(output), encoding="utf-8")
    except Exception:
        pass


def update_memory_with_llm(chat_history: List[Dict[str, Any]]) -> None:
    try:
        llm = get_llm()
    except Exception:
        return

    current_memory = load_memory()
    recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
    conversation_text = ""
    for msg in recent_history:
        role = msg.get("role", "assistant")
        if role == "tool":
            continue
        conversation_text += f"{role.title()}: {msg.get('content', '')}\n"

    prompt = (
        "You are a memory manager for an AI assistant. "
        "Update the following memory based on the recent conversation.\n\n"
        f"### CURRENT MEMORY:\n{current_memory or '(Empty)'}\n\n"
        f"### RECENT CONVERSATION:\n{conversation_text}\n\n"
        "### INSTRUCTIONS:\n"
        "1. Extract key user preferences, facts, and specific feedback from the RECENT CONVERSATION.\n"
        "2. Merge them into the Current Memory.\n"
        "3. Remove outdated information.\n"
        "4. Keep it concise/bulleted.\n"
        "5. RETURN ONLY THE NEW MEMORY TEXT."
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        new_memory = response.content.strip()
        MEMORY_FILE.write_text(new_memory, encoding="utf-8")
        st.session_state.memory_text = new_memory
    except Exception:
        return


def test_api_key(service, key):
    if not key:
        return False, "No key provided"
    try:
        if service == "deepseek":
            llm = ChatDeepSeek(api_key=key, model="deepseek-coder")
            llm.invoke("Hello")
            return True, "✅ Key is valid!"
        if service == "openai":
            client = OpenAI(api_key=key)
            client.models.list()
            return True, "✅ Key is valid!"
        if service == "google":
            llm = ChatGoogleGenerativeAI(
                model="gemini-3-flash-preview",
                temperature=0,
                api_key=key,
                convert_system_message_to_human=True,
            )
            llm.invoke("Hello")
            return True, "✅ Key is valid!"
        if service == "anthropic":
            llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0, api_key=key)
            llm.invoke("Hello")
            return True, "✅ Key is valid!"
        return False, "Unknown service"
    except Exception as e:
        return False, f"❌ Error: {str(e)[:160]}"


def test_mcp_server() -> Tuple[bool, str]:
    try:
        keys = st.session_state.api_keys
        ok_secret, secret_msg = create_client_secret_file(keys)
        if not ok_secret:
            return False, secret_msg

        if not MCP_SERVER_PATH.exists():
            return False, f"❌ Server path does not exist: {MCP_SERVER_PATH}"
        if not (MCP_SERVER_PATH / "main.py").exists():
            return False, f"❌ main.py not found in {MCP_SERVER_PATH}"

        server_env = os.environ.copy()
        server_env.update({
            "GOOGLE_OAUTH_CLIENT_ID": keys["google_id"],
            "GOOGLE_OAUTH_CLIENT_SECRET": keys["google_secret"],
            "OPENAI_API_KEY": keys["openai"],
        })

        if (MCP_SERVER_PATH / "uv.lock").exists():
            cmd, args = "uv", ["--directory", str(MCP_SERVER_PATH), "run", "main.py"]
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
        elif (MCP_SERVER_PATH / "requirements.txt").exists():
            cmd, args = "python", [str(MCP_SERVER_PATH / "main.py")]
        else:
            return False, "❌ No startup method found (uv.lock or requirements.txt missing)."

        proc = subprocess.Popen([cmd] + args, env=server_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            _, _ = proc.communicate(timeout=5)
            return True, "✅ MCP server executable looks valid"
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return True, "✅ MCP server starts (timeout expected for long running server)"
    except Exception as e:
        return False, f"❌ MCP Server Error: {e}\n\n```{traceback.format_exc()}```"


def should_trigger_workspace_agent(user_text: str) -> bool:
    t = (user_text or "").lower()
    keywords = [
        # gmail
        "gmail", "email", "inbox", "label", "thread", "draft", "send",
        # calendar
        "calendar", "meeting", "invite", "event",
        # drive
        "drive", "folder", "file", "share", "permission",
        # docs/slides/sheets
        "docs", "document", "slides", "presentation",
        "sheets", "spreadsheet", "sheet",  # ✅ FIX: add "sheet"
        # general
        "google workspace", "google drive"
    ]
    return any(k in t for k in keywords)


def make_web_search_tool(openai_key: str) -> StructuredTool:
    def web_search(query: str) -> str:
        if not openai_key:
            return "Error: No OpenAI API Key provided."
        client = OpenAI(api_key=openai_key)
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a tech researcher. Summarize concise technical info."},
                    {"role": "user", "content": f"Query: {query}"},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Search Error: {e}"

    return StructuredTool.from_function(
        name="web_search",
        description="Search the web for current information.",
        func=web_search,
    )


def make_read_error_history_tool() -> StructuredTool:
    def read_error_history() -> str:
        if not ERROR_HISTORY_FILE.exists():
            return "No error history file found."
        try:
            content = ERROR_HISTORY_FILE.read_text(encoding="utf-8")
            if not content.strip():
                return "Error history is empty."
            return f"ERROR HISTORY (Consult this after 3 failed tries):\n{content}"
        except Exception as e:
            return f"Error reading history: {e}"

    return StructuredTool.from_function(
        func=read_error_history,
        name="read_error_history",
        description="Reads past error solutions. Use after 3 failed attempts.",
    )


def make_read_skills_tool() -> StructuredTool:
    def read_skills() -> str:
        if not SKILLS_DIR.exists() or not SKILLS_DIR.is_dir():
            return "Skills folder not found."

        output = []
        for file in SKILLS_DIR.glob("*.txt"):
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
        description="Read available skill files from the skills directory.",
        func=read_skills,
    )


def make_terminal_tool() -> StructuredTool:
    def terminal_tool_func(command: str) -> str:
        shell_name = "PowerShell" if os.name == "nt" else "Bash"
        try:
            if os.name == "nt":
                proc_args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
            else:
                proc_args = ["bash", "-c", command]

            process = subprocess.run(
                proc_args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            output = process.stdout
            if process.stderr:
                output += f"\n[STDERR]\n{process.stderr}"
            return output.strip() or f"(Command executed with no output via {shell_name})"

        except FileNotFoundError:
            return f"Error: Shell executable for {shell_name} not found."
        except Exception as e:
            return f"Error executing command: {e}"

    return StructuredTool.from_function(
        name="terminal",
        description="Run system commands. Windows uses PowerShell; Linux/Mac uses Bash.",
        func=terminal_tool_func,
    )


def create_client_secret_file(keys: Dict[str, str]) -> Tuple[bool, str]:
    client_secret_path = MCP_SERVER_PATH / "client_secret.json"
    client_secret_content = {
        "installed": {
            "client_id": keys.get("google_id", ""),
            "client_secret": keys.get("google_secret", ""),
            "redirect_uris": [
                "http://localhost:8000/oauth2callback",
                "http://localhost:8000/",
            ],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
    }

    if not client_secret_content["installed"]["client_id"] or not client_secret_content["installed"]["client_secret"]:
        return False, "Client ID/Secret missing. Save Google OAuth settings first."

    try:
        os.makedirs(MCP_SERVER_PATH, exist_ok=True)
        client_secret_path.write_text(json.dumps(client_secret_content, indent=2), encoding="utf-8")
        return True, f"client_secret.json updated at {client_secret_path}"
    except Exception as e:
        return False, f"Failed to write client_secret.json: {e}"

def extract_tool_error_hint(err_text: str) -> str:
    low = err_text.lower()
    if "replacealltext" in low and "match text should not be empty" in low:
        return "Slides replaceAllText failed: match text was empty. Use a real placeholder string as containsText.text."
    if "inserttext" in low and "does not allow text editing" in low:
        return "Slides insertText failed: objectId was a slideId, not a text shape. Fetch presentation structure and insert into placeholder shape objectIds."
    return ""


def load_routines() -> List[Dict[str, Any]]:
    if not ROUTINES_FILE.exists():
        return []
    try:
        return json.loads(ROUTINES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_routines(routines: List[Dict[str, Any]]) -> None:
    ROUTINES_FILE.write_text(json.dumps(routines, indent=2), encoding="utf-8")


def add_routine(description: str, time_str: str) -> str:
    routine_id = str(uuid.uuid4())[:8]
    new_routine = {
        "id": routine_id,
        "description": description,
        "scheduled_time": time_str,
        "status": "PENDING",
        "created_at": datetime.datetime.now().isoformat(),
        "last_run_date": None,
        "completed_at": None,
    }
    routines = load_routines()
    routines.append(new_routine)
    save_routines(routines)
    return routine_id


def control_routine(routine_id: str, action: str) -> bool:
    action = action.lower()
    routines = load_routines()
    target = next((r for r in routines if r.get("id") == routine_id), None)
    if not target:
        return False
    if action == "delete":
        routines = [r for r in routines if r.get("id") != routine_id]
        save_routines(routines)
        return True
    if action == "pause":
        target["status"] = "PAUSED"
    elif action in ("resume", "start"):
        target["status"] = "PENDING"
    elif action == "stop":
        target["status"] = "STOPPED"
    save_routines(routines)
    return True


class SafeTool(BaseTool):
    _inner: Any = PrivateAttr()
    _tool_name: str = PrivateAttr()

    def __init__(self, inner_tool: Any, name: str, description: str):
        super().__init__(name=name, description=description)
        self._inner = inner_tool
        self._tool_name = name
        if hasattr(inner_tool, "args_schema"):
            self.args_schema = inner_tool.args_schema

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
            else:
                res = self._run(**kwargs)
            return self._ok(res)
        except Exception as e:
            return self._fail(e)


def convert_history_to_messages(
    history: List[Dict[str, Any]],
    include_tool_messages: bool = True,
) -> List[BaseMessage]:
    msgs: List[BaseMessage] = []
    for m in history:
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            msgs.append(HumanMessage(content=content))
        elif role == "assistant":
            msgs.append(AIMessage(content=content))
        elif role == "tool" and include_tool_messages:
            tool_name = m.get("tool_name", "workspace_agent")
            msgs.append(SystemMessage(content=f"TOOL RESULT ({tool_name}):\n{content}"))
    return msgs


def deepseek_chat(history: List[Dict[str, Any]], keys: dict, extra_system: Optional[str] = None) -> str:
    llm = get_llm()

    msgs = [SystemMessage(content=MAIN_CHAT_SYSTEM + ("\n" + extra_system if extra_system else ""))]

    memory_text = st.session_state.memory_text or load_memory()
    if memory_text:
        msgs.append(SystemMessage(content=f"MEMORY:\n{memory_text}"))

    msgs.extend(convert_history_to_messages(history, include_tool_messages=True))

    return llm.invoke(msgs).content


# -----------------------------------------------------------------------------
# Context “this” resolver (key fix)
# -----------------------------------------------------------------------------
def resolve_implicit_request(user_prompt: str) -> str:
    """
    If user says "add this to sheet", expand "this" using stored memory.
    """
    p = (user_prompt or "").strip().lower()
    if re.search(r"\badd\s+(this|that)\s+to\s+(a\s+)?(sheet|sheets|spreadsheet)\b", p):
        emails_payload = st.session_state.memory.get("last_emails_payload", "").strip()
        last_tool = st.session_state.memory.get("last_tool_output", "").strip()

        # Prefer emails payload if we have it
        context_blob = emails_payload or last_tool
        if context_blob:
            return (
                "Create a Google Sheet (or use an existing one if appropriate) and add the following information as rows.\n\n"
                "Use columns: From, Subject, Date, Summary (and any other available fields).\n\n"
                f"CONTENT TO ADD:\n{context_blob}"
            )

        # if no context exists
        return (
            "The user said: 'add this to sheet' but there is no previous content available. "
            "Ask which content to add and which spreadsheet name to use."
        )

    return user_prompt


def _extract_bracket_payload(text: str) -> Optional[str]:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start:end + 1]


def _parse_pythonish_list(payload: str) -> Optional[List[Dict[str, Any]]]:
    try:
        obj = json.loads(payload)
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return obj
    except Exception:
        pass

    try:
        obj = ast.literal_eval(payload)
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return obj
    except Exception:
        return None

    return None


def _flatten_text_blocks(obj: Any) -> Optional[str]:
    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        if all(("type" in x and x.get("type") == "text" and "text" in x) for x in obj):
            return "\n".join((x.get("text", "") or "").strip() for x in obj if x.get("text"))
    return None


def maybe_render_todo_from_text(text: Any) -> bool:
    text = normalize_text(text, "")
    if "updated todo list" not in text.lower():
        return False

    payload = _extract_bracket_payload(text)
    if not payload:
        return False

    items = _parse_pythonish_list(payload)
    if not items or not all(("content" in x or "status" in x) for x in items):
        return False

    total = len(items)
    done = sum(1 for x in items if (x.get("status") or "").strip().lower() == "completed")
    st.markdown(f"**Progress:** {done}/{total} completed")
    st.table([
        {
            "#": i + 1,
            "Status": (item.get("status") or "pending").replace("_", " ").title(),
            "Task": item.get("content", ""),
        }
        for i, item in enumerate(items)
    ])
    return True


def sync_model_for_provider():
    provider = st.session_state.llm_provider
    if not st.session_state.llm_model or st.session_state.llm_model in DEFAULT_MODELS.values():
        st.session_state.llm_model = DEFAULT_MODELS.get(provider, st.session_state.llm_model)


# -----------------------------------------------------------------------------
# Workspace agent (IMPORTANT: includes tool messages in agent context)
# -----------------------------------------------------------------------------
async def run_workspace_agent(
    user_input: str,
    chat_history: List[Dict[str, Any]],
    keys: dict,
    on_event=None,
) -> Dict[str, Any]:
    is_valid, server_msg = test_mcp_server()
    if not is_valid:
        return {"final": f"❌ MCP Server Validation Failed:\n\n{server_msg}", "trace": [], "auth_url": None}

    server_env = os.environ.copy()
    server_env["GOOGLE_OAUTH_CLIENT_ID"] = keys["google_id"]
    server_env["GOOGLE_OAUTH_CLIENT_SECRET"] = keys["google_secret"]
    server_env["OPENAI_API_KEY"] = keys["openai"]

    if (MCP_SERVER_PATH / "uv.lock").exists():
        cmd, args = "uv", ["--directory", str(MCP_SERVER_PATH), "run", "main.py"]
    elif (MCP_SERVER_PATH / "requirements.txt").exists():
        cmd, args = "python", [str(MCP_SERVER_PATH / "main.py")]
    else:
        return {"final": f"❌ No server startup method found in {MCP_SERVER_PATH}", "trace": [], "auth_url": None}

    server_params = StdioServerParameters(command=cmd, args=args, env=server_env)

    try:
        llm = get_llm()
    except Exception as e:
        return {"final": f"❌ LLM initialization failed: {e}", "trace": [], "auth_url": None}

    web_tool = make_web_search_tool(keys.get("openai", ""))
    read_skills_tool = make_read_skills_tool()
    read_error_history_tool = make_read_error_history_tool()
    terminal_tool = make_terminal_tool() if st.session_state.allow_terminal_tool else None

    trace: List[Dict[str, Any]] = []
    auth_url: Optional[str] = None
    final_resp = ""

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = await load_mcp_tools(session)

                safe_tools = []
                for tool in mcp_tools:
                    try:
                        safe_tools.append(SafeTool(tool, tool.name, tool.description))
                    except Exception:
                        continue

                memory_text = st.session_state.memory_text or load_memory()
                instructions = GOOGLE_WORKSPACE_INSTRUCTIONS
                if memory_text:
                    instructions += f"\n\nMEMORY:\n{memory_text}"
                instructions += """

ERROR HANDLING PROTOCOL (CRITICAL):
- If you encounter an error and fail to solve it 3 times in a row, you MUST use the read_error_history tool.
- Check if this error has happened before and apply the known solution.
- If you find a solution, try it.
"""

                tools = [web_tool, read_skills_tool, read_error_history_tool]
                if terminal_tool:
                    tools.append(terminal_tool)

                agent = create_deep_agent(tools + safe_tools, instructions, model=llm).with_config({"recursion_limit": 100})

                messages = convert_history_to_messages(chat_history, include_tool_messages=True)
                messages.append(HumanMessage(content=user_input))

                async for event in agent.astream({"messages": messages}, stream_mode="updates"):
                    for _, node_data in event.items():
                        if "messages" not in node_data:
                            continue
                        msg_list = node_data["messages"] if isinstance(node_data["messages"], list) else [node_data["messages"]]

                        for msg in msg_list:
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    t_name = tc.get("name", "unknown")
                                    args_obj = tc.get("args", {})
                                    trace.append({"type": "tool_call", "name": t_name, "args": args_obj})
                                    if on_event:
                                        on_event({"type": "tool_call", "name": t_name, "args": args_obj})

                            elif isinstance(msg, ToolMessage) or getattr(msg, "type", "") == "tool":
                                text = str(msg.content)

                                if ("accounts.google.com" in text) and ("oauth2" in text):
                                    m = re.search(r"(https?://accounts\.google\.com/o/oauth2/auth\?[^\s]+)", text)
                                    if m:
                                        auth_url = m.group(1).rstrip(".,)]>")
                                        auth_url = auth_url.replace("\\n", "").replace("\n", "").strip()
                                        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

                                        u = urlparse(auth_url)
                                        q = parse_qs(u.query)
                                        if "prompt" in q:
                                            # keep only valid parts if prompt got polluted
                                            parts = q["prompt"][0].replace("\n", " ").split()
                                            valid = [p for p in parts if p in ("consent", "select_account", "none")]
                                            q["prompt"] = [" ".join(valid) or "consent"]
                                        auth_url = urlunparse(u._replace(query=urlencode(q, doseq=True)))


                                trace.append({"type": "tool_output", "name": getattr(msg, "name", "tool"), "content": text})
                                if on_event:
                                    on_event({"type": "tool_output", "name": getattr(msg, "name", "tool"), "content": text})

                            elif isinstance(msg, AIMessage) or getattr(msg, "type", "") == "ai":
                                if msg.content:
                                    final_resp = msg.content

        if auth_url:
            return {
                "final": "⚠️ Google Authentication Required. Please authorize, then retry your request.",
                "trace": trace,
                "auth_url": auth_url
            }

        return {"final": final_resp or "Done.", "trace": trace, "auth_url": None}

    except Exception as e:
        return {
            "final": f"❌ Workspace Agent Error: {type(e).__name__}: {e}"
                     + (f"\n\n{traceback.format_exc()}" if st.session_state.debug_mode else ""),
            "trace": trace,
            "auth_url": None
        }


# -----------------------------------------------------------------------------
# Rendering
# -----------------------------------------------------------------------------
def render_message(m: Dict[str, Any]):
    role = m.get("role", "assistant")
    content = m.get("content", "")

    if role == "tool":
        tool_name = m.get("tool_name", "workspace_agent")
        flattened = _flatten_text_blocks(content)
        if flattened:
            content = flattened
        with st.chat_message("assistant", avatar="🛠️"):
            st.markdown(
                f"""
                <div class="tool-bubble">
                  <div class="title">🛠️ {tool_name} result</div>
                  <div class="small-muted">{content}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        return

    with st.chat_message(role):
        if role == "assistant" and maybe_render_todo_from_text(content):
            return
        st.markdown(content)


# -----------------------------------------------------------------------------
# Main app
# -----------------------------------------------------------------------------
def main():
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        st.session_state.debug_mode = st.checkbox("Debug mode", value=st.session_state.debug_mode)

        with st.expander("Model & Routing", expanded=True):
            provider_options = ["deepseek", "openai", "google", "anthropic"]
            current_provider = st.session_state.llm_provider if st.session_state.llm_provider in provider_options else "deepseek"
            st.selectbox(
                "Model provider",
                provider_options,
                index=provider_options.index(current_provider),
                key="llm_provider",
                on_change=sync_model_for_provider,
            )
            st.text_input("Model name", value=st.session_state.llm_model, key="llm_model")
            st.slider("Temperature", min_value=0.0, max_value=1.0, value=float(st.session_state.llm_temperature), step=0.05, key="llm_temperature")
            st.checkbox("Use LLM router", key="use_llm_router")
            st.checkbox("Auto-update memory", key="auto_memory")
            st.caption(f"Default model for {st.session_state.llm_provider}: {DEFAULT_MODELS.get(st.session_state.llm_provider, 'custom')}")

        st.markdown("### MCP Server")
        if st.button("Test MCP Connection"):
            ok, msg = test_mcp_server()
            st.markdown(f'<div class="{ "success-card" if ok else "error-card" }">{msg}</div>', unsafe_allow_html=True)

        with st.expander("API Keys", expanded=True):
            st.subheader("DeepSeek")
            ds = api_key_input("DeepSeek API Key", "deepseek")
            if st.button("Test DeepSeek"):
                ok, msg = test_api_key("deepseek", ds)
                st.markdown(f'<div class="{ "success-card" if ok else "error-card" }">{msg}</div>', unsafe_allow_html=True)

            st.divider()

            st.subheader("OpenAI (search)")
            oa = api_key_input("OpenAI API Key", "openai")
            if st.button("Test OpenAI"):
                ok, msg = test_api_key("openai", oa)
                st.markdown(f'<div class="{ "success-card" if ok else "error-card" }">{msg}</div>', unsafe_allow_html=True)

            st.divider()

            st.subheader("Google Gemini")
            gm = api_key_input("Gemini API Key", "gemini")
            if st.button("Test Gemini"):
                ok, msg = test_api_key("google", gm)
                st.markdown(f'<div class="{ "success-card" if ok else "error-card" }">{msg}</div>', unsafe_allow_html=True)

            st.divider()

            st.subheader("Anthropic")
            an = api_key_input("Anthropic API Key", "anthropic")
            if st.button("Test Anthropic"):
                ok, msg = test_api_key("anthropic", an)
                st.markdown(f'<div class="{ "success-card" if ok else "error-card" }">{msg}</div>', unsafe_allow_html=True)

            st.divider()

            st.subheader("Google OAuth")
            api_key_input("Client ID", "google_id")
            api_key_input("Client Secret", "google_secret")

        with st.expander("Agent Tools"):
            st.checkbox("Allow terminal tool (local commands)", key="allow_terminal_tool")
            st.text_area("Memory (read-only)", value=st.session_state.memory_text, height=140, disabled=True)
            colM1, colM2 = st.columns(2)
            with colM1:
                if st.button("Refresh Memory"):
                    st.session_state.memory_text = load_memory()
                    st.success("Memory refreshed.")
            with colM2:
                if st.button("Update Memory Now"):
                    update_memory_with_llm(st.session_state.messages)
                    st.success("Memory updated.")

        with st.expander("Learning"):
            time_range = st.selectbox("Learn from logs", ["last week", "last month", "3 months", "all"], index=0)
            if st.button("Process Logs"):
                try:
                    llm = get_llm()
                    result = process_past_logs(time_range, CONVERSATIONS_DIR, ERROR_HISTORY_FILE, BEST_PRACTICES_FILE, llm)
                    st.info(result)
                except Exception as e:
                    st.error(f"Log processing failed: {e}")

        st.divider()
        colA, colB = st.columns(2)
        with colA:
            if st.button("Save Settings"):
                save_config({
                    "deepseek_key": st.session_state.api_keys["deepseek"],
                    "openai_key": st.session_state.api_keys["openai"],
                    "gemini_key": st.session_state.api_keys["gemini"],
                    "anthropic_key": st.session_state.api_keys["anthropic"],
                    "google_id": st.session_state.api_keys["google_id"],
                    "google_secret": st.session_state.api_keys["google_secret"],
                    "llm_provider": st.session_state.llm_provider,
                    "llm_model": st.session_state.llm_model,
                    "llm_temperature": st.session_state.llm_temperature,
                    "allow_terminal_tool": st.session_state.allow_terminal_tool,
                    "auto_memory": st.session_state.auto_memory,
                })
                ok_secret, secret_msg = create_client_secret_file(st.session_state.api_keys)
                if ok_secret:
                    st.success("Settings saved and client_secret.json updated.")
                else:
                    st.warning(secret_msg)
        with colB:
            if st.button("Clear Saved"):
                if CONFIG_PATH.exists():
                    CONFIG_PATH.unlink()
                st.success("Cleared!")
                st.rerun()

        with st.expander("Setup Guide"):
            st.markdown(GOOGLE_SETUP_GUIDE)
            if st.button("Open full guide"):
                st.session_state.show_routine_log = False
                st.session_state.show_google_guide = True
                st.rerun()

    if st.session_state.show_google_guide and not st.session_state.show_routine_log:
        try:
            guide_content = GOOGLE_WORKSPACE_GUIDE_PATH.read_text(encoding="utf-8")
        except Exception as e:
            guide_content = f"Failed to read guide: {e}"
        dialog_fn = getattr(st, "dialog", None)
        if callable(dialog_fn):
            def _show_dialog():
                st.markdown(guide_content)
                if st.button("Close", key="close_google_guide"):
                    st.session_state.show_google_guide = False
                    st.rerun()
            show_dialog = dialog_fn("Google Workspace Setup Guide")(_show_dialog)
            show_dialog()
        else:
            with st.expander("Google Workspace Setup Guide", expanded=True):
                st.markdown(guide_content)
                if st.button("Close", key="close_google_guide_expander"):
                    st.session_state.show_google_guide = False
                    st.rerun()

    st.markdown(
        f"""
        <div class="header-wrap">
          <div>
            <div class="brand-title">⚡ Workspace Agent</div>
            <div class="brand-sub">Model: {st.session_state.llm_provider}/{st.session_state.llm_model} • Router: {st.session_state.last_route.get("route")}</div>
          </div>
          <div class="pill">Mode: {"Debug" if st.session_state.debug_mode else "Normal"}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.caption(f"Router reason: {st.session_state.last_route.get('reason')}")

    ok, missing = validate_credentials()
    if not ok:
        st.warning("⚠️ Configuration Required")
        st.info(f"Please configure: **{', '.join(missing)}** (sidebar)")
        return

    if not st.session_state.api_keys.get("openai"):
        st.info("OpenAI API key is missing. Web search tool will be unavailable.")

    if not MCP_SERVER_PATH.exists() or not (MCP_SERVER_PATH / "main.py").exists():
        st.error(f"❌ MCP server path invalid: {MCP_SERVER_PATH}")
        return

    tab_chat, tab_trace, tab_routines = st.tabs(["💬 Chat", "🧾 Agent Trace (latest)", "⏱️ Routines"])

    with tab_chat:
        with st.container():
            colL1, colL2 = st.columns([1, 3])
            with colL1:
                if st.button("Extract Skill From Session", type="primary", use_container_width=True):
                    try:
                        llm = get_llm()
                        history_msgs = convert_history_to_messages(st.session_state.messages, include_tool_messages=True)
                        result = extract_and_save_skill(history_msgs, SKILLS_DIR, llm)
                        st.info(result)
                    except Exception as e:
                        st.error(f"Skill extraction failed: {e}")
                learn_range = st.selectbox(
                    "Learn from logs",
                    ["last week", "last month", "3 months", "all"],
                    index=0,
                    key="learn_range_main",
                )
                if st.button("Learn From Logs", type="primary", use_container_width=True):
                    try:
                        llm = get_llm()
                        result = process_past_logs(
                            learn_range, CONVERSATIONS_DIR, ERROR_HISTORY_FILE, BEST_PRACTICES_FILE, llm
                        )
                        st.info(result)
                    except Exception as e:
                        st.error(f"Log processing failed: {e}")
            with colL2:
                st.caption("Creates a reusable skill from the current conversation.")
                st.caption("Learns from past logs and updates best practices + error history.")

        chat_area = st.container()

        # Render history
        with chat_area:
            for m in st.session_state.messages:
                render_message(m)

            # Process pending prompt (keeps input at bottom)
            if st.session_state.pending_prompt:
                raw_prompt = st.session_state.pending_prompt
                st.session_state.pending_prompt = None

                st.session_state.messages.append({"role": "user", "content": raw_prompt})
                render_message({"role": "user", "content": raw_prompt})
                save_conversation_log(st.session_state.messages, st.session_state.log_file)

                # Expand "add this to sheet" using memory
                prompt = resolve_implicit_request(raw_prompt)

                route = None
                reason = ""
                if st.session_state.use_llm_router:
                    try:
                        llm = get_llm()
                        router_llm_structured = build_router_llm(llm)
                        decision = run_async(decide_route(router_llm_structured, llm, st.session_state.messages))
                        route = decision.route
                        reason = decision.reason
                    except Exception as e:
                        route = None
                        reason = f"Router failed: {e}"

                if route is None:
                    route = "AGENT" if should_trigger_workspace_agent(prompt) else "ASSISTANT"
                    if not reason:
                        reason = "Keyword fallback."

                st.session_state.last_route = {"route": route, "reason": reason}

                if route == "AGENT":
                    ack = "🛠️ Running the Google Workspace Agent..."
                    st.session_state.messages.append({"role": "assistant", "content": ack})
                    render_message({"role": "assistant", "content": ack})
                    save_conversation_log(st.session_state.messages, st.session_state.log_file)

                    with st.chat_message("assistant", avatar="🛠️"):
                        status_box = st.status("Agent running...", expanded=True)

                    def on_agent_event(ev: dict):
                        if ev["type"] == "tool_call":
                            icon = get_icon_for_tool(ev.get("name", "tool"))
                            args_preview = str(ev.get("args", {}))[:160]
                            status_box.markdown(
                                f"""
                                <div class="tool-card">
                                  <b>{icon} Executing:</b> {ev.get("name","tool")}<br/>
                                  <span style="opacity:0.75;">{args_preview}...</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        elif ev["type"] == "tool_output":
                            status_box.markdown(
                                f"<div class='tool-card'><b>✅ Tool completed:</b> {ev.get('name','tool')}</div>",
                                unsafe_allow_html=True
                            )

                    agent_result = run_async(run_workspace_agent(
                        user_input=prompt,
                        chat_history=st.session_state.messages,  # includes tool messages too
                        keys=st.session_state.api_keys,
                        on_event=on_agent_event
                    ))
                    auth_url = agent_result.get("auth_url")
                    if auth_url:
                        with st.chat_message("assistant"):
                            st.markdown(f"[🔐 Click here to authorize Google]({auth_url})", unsafe_allow_html=True)
                        st.stop()

                    status_box.update(label="✅ Agent finished", state="complete", expanded=False)

                    st.session_state.last_agent_trace = agent_result.get("trace", [])

                    # Update memory with last tool output
                    st.session_state.memory["last_tool_output"] = agent_result["final"]

                    # If the original request was about top emails, store it explicitly
                    if "top" in raw_prompt.lower() and "email" in raw_prompt.lower():
                        st.session_state.memory["last_emails_payload"] = agent_result["final"]

                    st.session_state.messages.append({
                        "role": "tool",
                        "tool_name": "google_workspace_agent",
                        "content": agent_result["final"]
                    })
                    render_message({
                        "role": "tool",
                        "tool_name": "google_workspace_agent",
                        "content": agent_result["final"]
                    })
                    save_conversation_log(st.session_state.messages, st.session_state.log_file)

                    # main chat continuation (has full history + tool results)
                    try:
                        post = deepseek_chat(
                            history=st.session_state.messages,
                            keys=st.session_state.api_keys,
                            extra_system="Continue using the tool result. Do not ask for info already present."
                        )
                        st.session_state.messages.append({"role": "assistant", "content": post})
                        render_message({"role": "assistant", "content": post})
                        save_conversation_log(st.session_state.messages, st.session_state.log_file)
                    except Exception as e:
                        st.session_state.messages.append({"role": "assistant", "content": f"❌ LLM error: {e}"})
                        render_message({"role": "assistant", "content": f"❌ LLM error: {e}"})
                        save_conversation_log(st.session_state.messages, st.session_state.log_file)

                else:
                    # normal chat
                    try:
                        answer = deepseek_chat(history=st.session_state.messages, keys=st.session_state.api_keys)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        render_message({"role": "assistant", "content": answer})
                        save_conversation_log(st.session_state.messages, st.session_state.log_file)
                    except Exception as e:
                        st.session_state.messages.append({"role": "assistant", "content": f"❌ LLM error: {e}"})
                        render_message({"role": "assistant", "content": f"❌ LLM error: {e}"})
                        save_conversation_log(st.session_state.messages, st.session_state.log_file)

                if st.session_state.auto_memory:
                    update_memory_with_llm(st.session_state.messages)

                st.rerun()

        # Chat input LAST
        user_in = st.chat_input("💬 Ask me, or ask me to do Workspace actions...")
        if user_in:
            st.session_state.pending_prompt = user_in
            st.rerun()

    with tab_trace:
        if st.session_state.last_agent_trace:
            st.json(st.session_state.last_agent_trace)
        else:
            st.info("No agent trace yet. Run a Workspace action (gmail/drive/calendar/docs/sheet/etc).")

    with tab_routines:
        st.subheader("Background Routines")
        routines = load_routines()
        if routines:
            st.markdown("#### Active Routines")
            header_cols = st.columns([2, 2, 1, 1, 1])
            header_cols[0].markdown('<div class="routine-header">Description</div>', unsafe_allow_html=True)
            header_cols[1].markdown('<div class="routine-header">Time</div>', unsafe_allow_html=True)
            header_cols[2].markdown('<div class="routine-header">Status</div>', unsafe_allow_html=True)
            header_cols[3].markdown('<div class="routine-header">Log</div>', unsafe_allow_html=True)
            header_cols[4].markdown('<div class="routine-header">Actions</div>', unsafe_allow_html=True)

            for r in routines:
                raw_status = r.get("status", "")
                status = str(raw_status).strip().upper()
                if status == "RUNNING":
                    status_label = "Working"
                    status_class = "status-working"
                elif status == "PENDING":
                    status_label = "Pending"
                    status_class = "status-pending"
                elif status == "PAUSED":
                    status_label = "Paused"
                    status_class = "status-paused"
                elif status == "STOPPED":
                    status_label = "Stopped"
                    status_class = "status-stopped"
                elif status in {"COMPLETED", "COMPLETE", "COMPELETE"}:
                    status_label = "Completed"
                    status_class = "status-completed"
                else:
                    status_label = status.title() if status else "Unknown"
                    status_class = "status-unknown"

                log_files = sorted(CONVERSATIONS_DIR.glob(f"routine_{r.get('id','')}_*.txt"))
                latest_log = log_files[-1] if log_files else None

                row_cols = st.columns([2, 2, 1, 1, 1])
                row_cols[0].markdown(
                    f'<div class="routine-row routine-cell">{r.get("description", "(no description)")}</div>',
                    unsafe_allow_html=True,
                )
                row_cols[1].markdown(
                    f'<div class="routine-row routine-cell">{r.get("scheduled_time", "")}</div>',
                    unsafe_allow_html=True,
                )
                row_cols[2].markdown(
                    f'<div class="routine-row"><span class="status-pill {status_class}">{status_label}</span></div>',
                    unsafe_allow_html=True,
                )
                if latest_log:
                    if row_cols[3].button(
                        "View",
                        key=f"view_log_{r.get('id','')}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        st.session_state.routine_log_path = str(latest_log)
                        st.session_state.show_routine_log = True
                        st.session_state.show_google_guide = False
                        st.rerun()
                else:
                    row_cols[3].markdown('<div class="routine-row routine-cell">—</div>', unsafe_allow_html=True)
                if row_cols[4].button(
                    "Delete",
                    key=f"delete_routine_{r.get('id','')}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_routine_id = r.get("id")
                    st.rerun()
        else:
            st.info("No routines configured yet.")

        if st.session_state.pending_delete_routine_id:
            del_id = st.session_state.pending_delete_routine_id
            st.warning(f"Delete routine {del_id}? This cannot be undone.")
            colD1, colD2 = st.columns([1, 1])
            with colD1:
                if st.button("Confirm delete", key="confirm_delete_routine"):
                    ok = control_routine(del_id, "delete")
                    st.session_state.pending_delete_routine_id = None
                    if ok:
                        st.success("Routine deleted.")
                    else:
                        st.error("Routine not found.")
                    st.rerun()
            with colD2:
                if st.button("Cancel", key="cancel_delete_routine"):
                    st.session_state.pending_delete_routine_id = None
                    st.rerun()

        if st.session_state.show_routine_log and st.session_state.routine_log_path and not st.session_state.show_google_guide:
            log_path = Path(st.session_state.routine_log_path)
            try:
                log_content = log_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                log_content = f"Failed to read log: {e}"

            dialog_fn = getattr(st, "dialog", None)
            if callable(dialog_fn):
                def _show_dialog():
                    st.code(log_content, language="markdown")
                    if st.button("Close"):
                        st.session_state.show_routine_log = False
                        st.rerun()

                show_dialog = dialog_fn(f"Routine Log: {log_path.name}")(_show_dialog)
                show_dialog()
            else:
                with st.expander(f"Routine Log: {log_path.name}", expanded=True):
                    st.code(log_content, language="markdown")
                    if st.button("Close", key="close_log_expander"):
                        st.session_state.show_routine_log = False
                        st.rerun()

        st.markdown("### Add Routine")
        with st.form("add_routine_form", clear_on_submit=True):
            desc = st.text_input("Routine description")
            time_str = st.text_input("Daily time (HH:MM, 24h)")
            submitted = st.form_submit_button("Add Routine")
            if submitted:
                if not desc.strip():
                    st.error("Description is required.")
                else:
                    try:
                        datetime.datetime.strptime(time_str.strip(), "%H:%M")
                    except ValueError:
                        st.error("Time must be in HH:MM 24-hour format.")
                        submitted = False
                if submitted:
                    rid = add_routine(desc.strip(), time_str.strip())
                    st.success(f"Routine added: {rid}")
                    st.rerun()

        st.divider()
        st.markdown("### Manage Routine")
        colM1, colM2, colM3 = st.columns([2, 1, 1])
        with colM1:
            routine_id = st.text_input("Routine ID")
        with colM2:
            action = st.selectbox("Action", ["pause", "resume", "stop", "delete"], index=0)
        with colM3:
            if st.button("Apply"):
                if not routine_id.strip():
                    st.error("Routine ID required.")
                else:
                    ok = control_routine(routine_id.strip(), action)
                    if ok:
                        st.success("Routine updated.")
                        st.rerun()
                    else:
                        st.error("Routine not found.")


if __name__ == "__main__":
    main()


