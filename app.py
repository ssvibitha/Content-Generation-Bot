"""
AI Chatbot with MCP Protocol
A Gradio-based chatbot using Azure OpenAI and real MCP servers
"""
import gradio as gr
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import after path setup
from mcp_client.client import MCPClient
from ai_client import AzureOpenAIClient
from deadline_db import (
    get_upcoming_deadlines,
    get_all_deadlines,
    mark_done,
    format_deadlines_as_markdown,
)
from deadline_extractor import process_uploaded_file
from digest_scheduler import start_digest_scheduler

# Load environment
load_dotenv()

# Initialize clients
ai_client = AzureOpenAIClient()
mcp_client = MCPClient()

# Track initialization
mcp_initialized = False

# Custom CSS
custom_css = """
.gradio-container {
    font-family: 'Inter', sans-serif;
}
.server-status {
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}
.server-running {
    background-color: #10b981;
    color: white;
}
.server-stopped {
    background-color: #ef4444;
    color: white;
}
"""


async def initialize_mcp_servers():
    """Initialize MCP servers on startup"""
    global mcp_initialized
    
    if mcp_initialized:
        return "Servers already initialized"
    
    print("Initializing MCP servers...")
    
    # Start file system server
    fs_success = await mcp_client.start_server(
        "filesystem",
        "src/mcp_servers/fs_server.py"
    )
    
    # Start calculator server
    calc_success = await mcp_client.start_server(
        "calculator",
        "src/mcp_servers/calc_server.py"
    )
    
    # Start weather server
    weather_success = await mcp_client.start_server(
        "weather",
        "src/mcp_servers/weather_server.py"
    )

    # Start deadline server
    deadline_success = await mcp_client.start_server(
        "deadline",
        "src/mcp_servers/deadline_server.py"
    )
    
    success_count = sum([fs_success, calc_success, weather_success, deadline_success])
    
    if success_count == 4:
        mcp_initialized = True
        return "✅ All MCP servers initialized (4/4)"
    elif success_count > 0:
        mcp_initialized = True
        return f"⚠️ Some servers initialized ({success_count}/4)"
    else:
        return "❌ Failed to initialize servers"


async def process_message(message: str, history: list, use_tools: bool):
    """Process user message and get AI response"""
    
    if not message.strip():
        return history, ""
    
    # Initialize history if None
    if history is None:
        history = []
    
    try:
        # Get AI response with MCP tools
        response = await ai_client.chat(
            message=message,
            mcp_client=mcp_client if use_tools else None,
            use_tools=use_tools,
        )
        
        # Gradio 6.0 expects messages format: list of dicts with 'role' and 'content'
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing message: {error_details}")
        
        error_msg = f"❌ Error: {str(e)}\n\nPlease check that:\n1. Azure OpenAI credentials are configured\n2. MCP servers are running\n3. Network connection is available"
        
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
    
    return history, ""


def clear_conversation():
    """Clear conversation history"""
    count = ai_client.clear_history()
    return [], f"Cleared {count} messages from history"


def get_stats():
    """Get chatbot statistics"""
    history_length = ai_client.get_history_length()
    servers = mcp_client.get_all_servers()
    
    server_status = "\n".join([f"  • {s} (running)" for s in servers]) if servers else "  No servers running"
    
    return f"""### 📊 Statistics
- **Messages in history:** {history_length}
- **MCP Servers:** {len(servers)}

**Active Servers:**
{server_status}

**Status:** {'✅ Ready' if servers else '⚠️ No tools available'}
"""


def get_deadline_panel_content() -> str:
    """Render the upcoming deadlines panel (next 3 days)."""
    try:
        deadlines = get_upcoming_deadlines(days=3)
        if not deadlines:
            return (
                "### 📅 Upcoming Deadlines\n\n"
                "🎉 Nothing due in the next 3 days — you're all caught up!"
            )
        md = format_deadlines_as_markdown(deadlines)
        return f"### 📅 Upcoming Deadlines (next 3 days)\n\n{md}"
    except Exception as e:
        return f"### 📅 Upcoming Deadlines\n\n⚠️ Could not load deadlines: {e}"


def handle_file_upload(file_obj) -> tuple:
    """
    Called when a user uploads a file via the Gradio file input.
    Runs the async extraction pipeline synchronously.

    Returns:
        (status_message, updated_deadline_panel_content)
    """
    if file_obj is None:
        return "⚠️ No file selected.", get_deadline_panel_content()

    file_path = file_obj.name if hasattr(file_obj, 'name') else str(file_obj)

    try:
        inserted, skipped, status = asyncio.run(
            process_uploaded_file(file_path, ai_client)
        )
    except Exception as e:
        import traceback
        status = f"❌ Upload error: {e}\n{traceback.format_exc()}"

    return status, get_deadline_panel_content()


def get_available_tools():
    """Get list of available MCP tools - runs on button click"""
    servers = mcp_client.get_all_servers()
    
    if not servers:
        return "### 🛠️ Available Tools\n\n⚠️ No MCP servers running\n\nPlease wait for initialization or restart the app."
    
    tools_text = "### 🛠️ Available Tools\n\n"
    
    for server_name in servers:
        try:
            # Use the synchronous run to get tools
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tools = loop.run_until_complete(mcp_client.list_tools(server_name))
            loop.close()
            
            tools_text += f"**{server_name.upper()}:**\n"
            for tool in tools:
                tools_text += f"- `{tool['name']}`: {tool.get('description', 'No description')}\n"
            tools_text += "\n"
        except Exception as e:
            tools_text += f"**{server_name}:** Error loading tools - {str(e)}\n\n"
    
    tools_text += """
**Usage Examples:**

📁 **Files:**
- "List all files in the directory"
- "Read test1.txt"
- "Search for 'MCP' in files"

🔢 **Math:**
- "Calculate 25 + 75 + 100"
- "What's the factorial of 8?"
- "Divide 144 by 12"

🌡️ **Conversions:**
- "Convert 100°F to Celsius"
- "Convert 5 miles to kilometers"

🌤️ **Weather:**
- "What's the weather in London?"
- "Show forecast for Tokyo"
- "Compare Dubai and Moscow weather"
- "List all available cities"
"""
    
    return tools_text


# ---------------------------------------------------------------------------
# Gradio Interface — Gradio 6.0 compatible
# ---------------------------------------------------------------------------

_EXTENDED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Global ── */
.gradio-container {
    font-family: 'Inter', sans-serif !important;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e) !important;
    min-height: 100vh;
}

/* ── Header ── */
.deadline-header h1 {
    background: linear-gradient(90deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 4px;
}

/* ── Deadline panel ── */
.deadline-panel {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(129,140,248,0.3) !important;
    border-radius: 14px !important;
    padding: 16px !important;
}

/* ── Upload zone ── */
.upload-zone {
    border: 2px dashed rgba(129,140,248,0.5) !important;
    border-radius: 12px !important;
    background: rgba(129,140,248,0.05) !important;
    transition: border-color 0.2s ease;
}
.upload-zone:hover {
    border-color: rgba(192,132,252,0.7) !important;
}

/* ── Chatbot bubble colours ── */
.message.user {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: #fff !important;
    border-radius: 18px 18px 4px 18px !important;
}
.message.bot {
    background: rgba(255,255,255,0.08) !important;
    color: #e2e8f0 !important;
    border-radius: 18px 18px 18px 4px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

/* ── Buttons ── */
.primary-btn {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: opacity 0.2s ease !important;
}
.primary-btn:hover { opacity: 0.85 !important; }

/* ── Status pill ── */
.status-box textarea {
    background: rgba(255,255,255,0.05) !important;
    color: #94a3b8 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
}
"""

app = gr.Blocks(
    title="🤖 AI Chatbot + Deadline Tracker",
    css=_EXTENDED_CSS,
)

with app:
    # ── Header ─────────────────────────────────────────────────────────────
    with gr.Row(elem_classes=["deadline-header"]):
        gr.Markdown("""
        # 🤖 AI Chatbot with MCP Protocol & 📅 Deadline Tracker

        Powered by **Azure OpenAI** · **MCP servers** (filesystem, calculator, weather, deadlines)

        **Chat capabilities:** file ops, math, weather, and deadline Q&A · **Upload a syllabus** to auto-extract deadlines
        """)
    
    # ── Main layout ────────────────────────────────────────────────────────
    with gr.Row():

        # ── LEFT: Chat column ───────────────────────────────────────────────
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Conversation",
                height=480,
                show_label=True,
            )

            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Type your message… or ask 'what's due this week?'",
                    show_label=False,
                    scale=4,
                    container=False,
                )
                submit_btn = gr.Button("Send 🚀", scale=1, variant="primary", elem_classes=["primary-btn"])

            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
                use_tools_cb = gr.Checkbox(
                    label="Enable MCP Tools",
                    value=True,
                    info="Allow AI to use MCP servers",
                )

        # ── RIGHT: Sidebar ──────────────────────────────────────────────────
        with gr.Column(scale=1):

            # ── Deadline Panel ──────────────────────────────────────────────
            deadline_panel = gr.Markdown(
                value=get_deadline_panel_content(),
                elem_classes=["deadline-panel"],
            )

            with gr.Row():
                refresh_deadlines_btn = gr.Button("🔄 Refresh", size="sm", scale=1)

            gr.Markdown("---")

            # ── Syllabus Upload ─────────────────────────────────────────────
            gr.Markdown("#### 📁 Upload Syllabus")
            upload_file = gr.File(
                label="Upload a syllabus (.txt, .md, .pdf)",
                file_types=[".txt", ".md", ".pdf"],
                type="filepath",
                elem_classes=["upload-zone"],
            )
            upload_status = gr.Markdown("Upload a syllabus to auto-extract deadlines.")

            gr.Markdown("---")

            # ── Stats & Tools ───────────────────────────────────────────────
            gr.Markdown("#### ⚙️ Control Panel")
            stats_display = gr.Markdown(get_stats())
            refresh_stats_btn = gr.Button("🔄 Refresh Stats", size="sm")

            with gr.Accordion("📖 Available Tools", open=False):
                tools_display = gr.Markdown("Loading tools...")
                refresh_tools_btn = gr.Button("🔄 Refresh Tools", size="sm")

            with gr.Accordion("💡 Quick Examples", open=False):
                gr.Markdown("""
**Deadline Tracker:**
- What's due this week?
- Show all my deadlines
- Mark Homework 1 as done
- Add deadline: CS101, Final Exam, 2025-12-15

**File Operations (MCP):**
- List all files
- Read test1.txt

**Calculations (MCP):**
- Add 10, 20, and 30
- Calculate factorial of 8

**Weather (MCP):**
- What's the weather in London?
- Compare Dubai and Moscow weather
                """)

            status_text = gr.Textbox(
                label="Status",
                value="Initializing...",
                interactive=False,
                elem_classes=["status-box"],
            )

    # ── Footer ──────────────────────────────────────────────────────────────
    gr.Markdown("""
---
### 🔒 Privacy & Security
- Conversations processed through Azure OpenAI · MCP servers run in isolated processes
- Deadlines stored locally in `deadlines.db` · File access restricted to designated directory

**Built with** Gradio · Azure OpenAI · MCP Protocol · SQLite
    """)

    # ── Event handlers ──────────────────────────────────────────────────────
    def submit_message(message, history, use_tools):
        return asyncio.run(
            process_message(message, history, use_tools)
        )

    submit_btn.click(
        fn=submit_message,
        inputs=[msg, chatbot, use_tools_cb],
        outputs=[chatbot, msg],
    )
    msg.submit(
        fn=submit_message,
        inputs=[msg, chatbot, use_tools_cb],
        outputs=[chatbot, msg],
    )
    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot, status_text],
    )
    refresh_stats_btn.click(
        fn=get_stats,
        outputs=stats_display,
    )
    refresh_tools_btn.click(
        fn=get_available_tools,
        outputs=tools_display,
    )
    refresh_deadlines_btn.click(
        fn=get_deadline_panel_content,
        outputs=deadline_panel,
    )

    # File upload: extract → save → refresh panel
    upload_file.upload(
        fn=handle_file_upload,
        inputs=[upload_file],
        outputs=[upload_status, deadline_panel],
    )

    # Auto-refresh on load
    app.load(fn=get_available_tools,       outputs=tools_display)
    app.load(fn=get_stats,                 outputs=stats_display)
    app.load(fn=get_deadline_panel_content, outputs=deadline_panel)


if __name__ == "__main__":
    print("Starting AI Chatbot with MCP Protocol + Deadline Tracker...")
    print("="*60)

    # 1. Initialize MCP servers
    try:
        init_result = asyncio.run(initialize_mcp_servers())
        print(init_result)
        print("="*60)
    except Exception as e:
        print(f"⚠️ Warning: MCP initialization failed - {e}")
        print("App will start but tools may not be available")
        import traceback
        traceback.print_exc()

    # 2. Start daily digest scheduler (background daemon thread)
    try:
        start_digest_scheduler()
        print("✅ Digest scheduler started")
    except Exception as e:
        print(f"⚠️ Digest scheduler failed to start: {e}")

    # 3. Debug info
    servers = mcp_client.get_all_servers()
    print(f"\n✅ Active MCP Servers: {servers}")
    print(f"✅ MCP Initialized: {mcp_initialized}")
    print("="*60 + "\n")

    # 4. Launch Gradio
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("APP_PORT", "7860")),
        share=False,
        show_error=True,
    )