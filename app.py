"""
AI Chatbot with MCP Protocol
A Gradio-based chatbot using Azure OpenAI and real MCP servers
"""
import gradio as gr
import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

STATIC_DIR = Path(__file__).parent / "static"
STYLES_CSS_PATH = STATIC_DIR / "styles.css"

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

# In-memory list of uploaded files: [{"name": str, "path": str, "status": str}]
_uploaded_files: list[dict] = []


# ---------------------------------------------------------------------------
# MCP server init
# ---------------------------------------------------------------------------

async def initialize_mcp_servers():
    """Initialize MCP servers on startup"""
    global mcp_initialized

    if mcp_initialized:
        return "Servers already initialized"

    print("Initializing MCP servers...")

    fs_success = await mcp_client.start_server(
        "filesystem", "src/mcp_servers/fs_server.py"
    )
    calc_success = await mcp_client.start_server(
        "calculator", "src/mcp_servers/calc_server.py"
    )
    weather_success = await mcp_client.start_server(
        "weather", "src/mcp_servers/weather_server.py"
    )
    deadline_success = await mcp_client.start_server(
        "deadline", "src/mcp_servers/deadline_server.py"
    )

    success_count = sum([fs_success, calc_success, weather_success, deadline_success])

    if success_count == 4:
        mcp_initialized = True
        return "All MCP servers initialized (4/4)"
    elif success_count > 0:
        mcp_initialized = True
        return f"Some servers initialized ({success_count}/4)"
    else:
        return "Failed to initialize servers"


# ---------------------------------------------------------------------------
# Chat logic
# ---------------------------------------------------------------------------

async def process_message(message: str, history: list, use_tools: bool):
    """Process user message and get AI response"""

    if not message.strip():
        return history, ""

    if history is None:
        history = []

    try:
        response = await ai_client.chat(
            message=message,
            mcp_client=mcp_client if use_tools else None,
            use_tools=use_tools,
        )
        history.append({"role": "user",      "content": message})
        history.append({"role": "assistant", "content": response})

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing message: {error_details}")
        error_msg = (
            f"Something went wrong: {str(e)}\n\n"
            "Please check that:\n"
            "1. Azure OpenAI credentials are configured\n"
            "2. MCP servers are running\n"
            "3. Network connection is available"
        )
        history.append({"role": "user",      "content": message})
        history.append({"role": "assistant", "content": error_msg})

    return history, ""


def clear_conversation():
    """Clear conversation history"""
    count = ai_client.clear_history()
    return [], f"Cleared {count} messages from history"


# ---------------------------------------------------------------------------
# Stats / tools
# ---------------------------------------------------------------------------

def get_stats():
    """Get chatbot statistics"""
    history_length = ai_client.get_history_length()
    servers = mcp_client.get_all_servers()
    server_status = (
        "\n".join([f"- {s} &nbsp;·&nbsp; running" for s in servers])
        if servers else "- No servers running"
    )
    ready = "Ready" if servers else "No tools available"
    return f"""**Messages in history:** {history_length}  
**MCP servers connected:** {len(servers)}

{server_status}

**Status:** {ready}
"""


def get_available_tools():
    """Get list of available MCP tools"""
    servers = mcp_client.get_all_servers()

    if not servers:
        return (
            "No MCP servers running yet.\n\n"
            "Wait for initialization or restart the app."
        )

    tools_text = ""

    for server_name in servers:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tools = loop.run_until_complete(mcp_client.list_tools(server_name))
            loop.close()

            tools_text += f"**{server_name.upper()}**\n"
            for tool in tools:
                tools_text += f"- `{tool['name']}` — {tool.get('description', 'No description')}\n"
            tools_text += "\n"
        except Exception as e:
            tools_text += f"**{server_name}** — error loading tools: {str(e)}\n\n"

    return tools_text


# ---------------------------------------------------------------------------
# Deadline panel
# ---------------------------------------------------------------------------

def get_deadline_panel_content() -> str:
    """Render the upcoming deadlines panel (next 3 days)."""
    try:
        deadlines = get_upcoming_deadlines(days=3)
        if not deadlines:
            return (
                "<div class='empty-panel'>"
                "<div class='empty-panel-icon'>&#10003;</div>"
                "Nothing due in the next 3 days."
                "</div>"
            )
        md = format_deadlines_as_markdown(deadlines)
        return md
    except Exception as e:
        return f"<div class='empty-panel error'>Could not load deadlines: {e}</div>"


# ---------------------------------------------------------------------------
# Uploaded files sidebar
# ---------------------------------------------------------------------------

def _render_files_html() -> str:
    """Build an HTML list of uploaded files with remove buttons."""
    if not _uploaded_files:
        return (
            "<div class='empty-panel'>"
            "<div class='empty-panel-icon'>&#128193;</div>"
            "No files yet.<br>"
            "<span class='empty-panel-sub'>Use the + button to upload a syllabus.</span>"
            "</div>"
        )

    items = ""
    for i, f in enumerate(_uploaded_files):
        ext  = Path(f["name"]).suffix.upper().lstrip(".")
        icon = {"PDF": "PDF", "TXT": "TXT", "MD": "MD"}.get(ext, "DOC")
        status_class = "ok" if "Added" in f["status"] else ("warn" if "⚠️" in f["status"] else "err")
        short_status = (f["status"][:60] + "…") if len(f["status"]) > 60 else f["status"]
        items += f"""
        <div class='file-item' id='file-item-{i}'>
          <div class='file-icon'>{icon}</div>
          <div class='file-info'>
            <div class='file-name'>{f['name']}</div>
            <div class='file-status {status_class}'>{short_status}</div>
          </div>
          <button class='file-remove-btn'
                  onclick="removeFile({i})"
                  title='Remove file'>&times;</button>
        </div>"""

    return f"<div class='file-list'>{items}</div>"


def get_files_html() -> str:
    """Public accessor for the HTML panel."""
    return _render_files_html()


def handle_file_upload(file_obj) -> tuple:
    """
    Upload handler — extracts deadlines and adds file to sidebar list.
    Returns (files_html, deadline_panel_md, upload_status_md)
    """
    global _uploaded_files

    if file_obj is None:
        return get_files_html(), get_deadline_panel_content(), "No file selected."

    file_path = file_obj if isinstance(file_obj, str) else (
        file_obj.name if hasattr(file_obj, "name") else str(file_obj)
    )
    filename = Path(file_path).name

    try:
        inserted, skipped, status = asyncio.run(
            process_uploaded_file(file_path, ai_client)
        )
    except Exception as e:
        status = f"Upload error: {e}"

    # Add to sidebar list (avoid exact duplicates by path)
    if not any(f["path"] == file_path for f in _uploaded_files):
        _uploaded_files.append({
            "name":   filename,
            "path":   file_path,
            "status": status,
        })

    return get_files_html(), get_deadline_panel_content(), status


def remove_file_by_index(index_json: str) -> tuple:
    """Remove a file entry from the sidebar list by index."""
    global _uploaded_files
    try:
        idx = int(index_json)
        if 0 <= idx < len(_uploaded_files):
            _uploaded_files.pop(idx)
    except (ValueError, TypeError):
        pass
    return get_files_html(), get_deadline_panel_content()


# ---------------------------------------------------------------------------
# CSS  — modern, clean, neutral workspace theme (light + dark)
# ---------------------------------------------------------------------------

_CSS = (
    STYLES_CSS_PATH.read_text(encoding="utf-8")
    if STYLES_CSS_PATH.exists()
    else ""
)

# ---------------------------------------------------------------------------
# JavaScript helpers
# ---------------------------------------------------------------------------

_JS_INIT = """
async () => {
    // removeFile(i) is called by the remove button in the files HTML.
    // It sets a hidden textbox value and triggers the remove button.
    window.removeFile = function(index) {
        const tb = document.getElementById('remove-index-box').querySelector('textarea');
        if (!tb) return;
        tb.value = String(index);
        tb.dispatchEvent(new Event('input', {bubbles: true}));
        // Trigger the hidden remove button
        setTimeout(() => {
            const btn = document.getElementById('remove-trigger-btn');
            if (btn) btn.click();
        }, 50);
    };

    // Restore saved theme preference (falls back to OS preference)
    window.applyTheme = function(mode) {
        document.documentElement.classList.toggle('dark', mode === 'dark');
    };
    const saved = localStorage.getItem('study-assistant-theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    window.applyTheme(saved || (prefersDark ? 'dark' : 'light'));

    // Toggle handler for the header button
    window.toggleTheme = function() {
        const isDark = document.documentElement.classList.contains('dark');
        const next = isDark ? 'light' : 'dark';
        window.applyTheme(next);
        localStorage.setItem('study-assistant-theme', next);
    };
}
"""

# ---------------------------------------------------------------------------
# Gradio App
# ---------------------------------------------------------------------------

app = gr.Blocks(
    title="Vortex · Deadline Tracker",
    css=_CSS,
    js=_JS_INIT,
    theme=gr.themes.Base(
        primary_hue="gray",
        neutral_hue="gray",
        font=["Inter", "sans-serif"],
    ),
)

with app:
    # ── Header ──────────────────────────────────────────────────────────────
    with gr.Row(elem_classes=["app-header"]):
        with gr.Column(scale=1):
            gr.HTML("""
            <h1><span class="accent-dot"></span>Vortex</h1>
            <p>Azure OpenAI · MCP tools (filesystem · calculator · weather · deadlines) · Upload a syllabus to auto-track due dates</p>
            """)

    # ── Two-column layout: chat + right rail ─────────────────────────────────
    with gr.Row(equal_height=False):

        # ━━━━━━━━━━━━━━━━ LEFT/CENTER: Chat ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        with gr.Column(scale=4, min_width=420):

            chatbot = gr.Chatbot(
                label="Conversation",
                height=520,
                show_label=False,
                elem_classes=["chatbot-wrap"],
                avatar_images=None,
            )

            # ── Input bar (Gemini-style composer) ──────────────────────────
            with gr.Row(elem_classes=["input-row"]):

                # + button — a real upload control, opens the OS file
                # picker directly (no hidden-input / JS-click workaround,
                # which browsers block for hidden file inputs).
                upload_plus_btn = gr.UploadButton(
                    "+",
                    file_types=[".txt", ".md", ".pdf"],
                    scale=0,
                    min_width=44,
                    elem_classes=["upload-plus-btn"],
                )

                # Text input — bigger, roomier, multi-line like Gemini's box
                msg = gr.Textbox(
                    placeholder="Message… or ask “what's due this week?”",
                    show_label=False,
                    scale=1,
                    container=False
                )

                # Send button
                submit_btn = gr.Button(
                    "↑",
                    scale=0,
                    min_width=44,
                    elem_classes=["send-arrow-btn"]
                )

            # ── Secondary controls row ───────────────────────────────────────
            with gr.Row(elem_classes=["secondary-row"]):
                clear_btn = gr.Button("Clear chat", size="sm")
                use_tools_cb = gr.Checkbox(
                    label="MCP tools",
                    value=True,
                    scale=0
                )

        # ━━━━━━━━━━━━━━━━ RIGHT: Files + Deadlines ━━━━━━━━━━━━━━━━━━━━━━━━
        with gr.Column(scale=2, min_width=280, elem_classes=["sidebar-scroll"]):

            # ── Uploaded Files panel ─────────────────────────────────────────
            gr.HTML("<div class='panel-title'>Uploaded files</div>")
            files_panel = gr.HTML(
                value=get_files_html(),
                elem_classes=["sidebar-panel"],
            )

            # Hidden: upload status fed back to sidebar
            upload_status_md = gr.Markdown(visible=False)

            # Hidden machinery for JS → Python remove call
            remove_index_box = gr.Textbox(
                value="",
                visible=False,
                elem_id="remove-index-box",
            )
            remove_trigger_btn = gr.Button(
                "remove",
                visible=False,
                elem_id="remove-trigger-btn",
            )

            # ── Deadlines panel ──────────────────────────────────────────────
            gr.HTML("<div class='panel-title'>Upcoming deadlines</div>")
            deadline_panel = gr.Markdown(
                value=get_deadline_panel_content(),
                elem_classes=["deadline-panel"],
            )
            refresh_deadlines_btn = gr.Button("Refresh deadlines", size="sm")

            gr.HTML("<hr class='sidebar-divider'>")

            # ── Workspace launcher: opens stats/tools/examples in a dialog
            #    instead of an inline accordion, so the sidebar stays short
            #    and the composer never needs a page scroll to reach. ──────
            workspace_open_btn = gr.Button(
                "Workspace",
                elem_classes=["workspace-open-btn"],
                scale=0,
                min_width=0,
            )
            status_text = gr.Textbox(
                value="Initializing…",
                show_label=False,
                interactive=False,
                elem_classes=["workspace-status"],
            )

            # ── Workspace modal (stats / tools / examples) ────────────────────────
            with gr.Column(visible=False, elem_classes=["modal-overlay"]) as workspace_modal:
                with gr.Column(elem_classes=["modal-content"]):
                    with gr.Row(elem_classes=["modal-title-row"]):
                        gr.HTML("<h2>Workspace</h2>")
                        workspace_close_btn = gr.Button("✕", elem_classes=["modal-close-btn"], scale=0, min_width=30)

                    with gr.Accordion("Stats", open=True, elem_classes=["workspace-accordion"]):
                        stats_display = gr.Markdown(get_stats())
                        refresh_stats_btn = gr.Button("Refresh stats", size="sm")

                    with gr.Accordion("Available tools", open=False, elem_classes=["workspace-accordion"]):
                        tools_display = gr.Markdown("Loading tools…")
                        refresh_tools_btn = gr.Button("Refresh tools", size="sm")

                    with gr.Accordion("Quick examples", open=False, elem_classes=["workspace-accordion"]):
                        gr.Markdown("""
                        **Deadlines**
                        - What's due this week?
                        - Show all my deadlines
                        - Mark Homework 1 as done

                        **Files (MCP)**
                        - List all files · Read test1.txt

                        **Math (MCP)**
                        - Add 10, 20, and 30

                        **Weather (MCP)**
                        - Weather in London?
                                        """)

    # ── Footer ───────────────────────────────────────────────────────────────
    gr.HTML(
        "<div class='app-footer'>Conversations processed via Azure OpenAI · "
        "Deadlines stored locally in <code>deadlines.db</code> · "
        "Built with Gradio · Azure OpenAI · MCP · SQLite</div>"
    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Event wiring
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def submit_message(message, history, use_tools):
        return asyncio.run(process_message(message, history, use_tools))

    # Send on button or Enter
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

    # Clear chat
    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot, status_text],
    )

    # UploadButton opens the native file picker itself (no JS needed) and
    # fires .upload with the selected file the moment it's chosen.
    upload_plus_btn.upload(
        fn=handle_file_upload,
        inputs=[upload_plus_btn],
        outputs=[files_panel, deadline_panel, upload_status_md],
    )

    # Workspace button → open modal dialog; close (✕) → hide it again
    workspace_open_btn.click(
        fn=lambda: gr.update(visible=True),
        outputs=[workspace_modal],
    )
    workspace_close_btn.click(
        fn=lambda: gr.update(visible=False),
        outputs=[workspace_modal],
    )

    # JS remove button → remove_index_box changes → remove_trigger_btn fires → Python
    remove_trigger_btn.click(
        fn=remove_file_by_index,
        inputs=[remove_index_box],
        outputs=[files_panel, deadline_panel],
    )

    # Sidebar refresh buttons
    refresh_deadlines_btn.click(fn=get_deadline_panel_content, outputs=deadline_panel)
    refresh_stats_btn.click(fn=get_stats, outputs=stats_display)
    refresh_tools_btn.click(fn=get_available_tools, outputs=tools_display)

    # Auto-refresh on page load
    app.load(fn=get_available_tools,        outputs=tools_display)
    app.load(fn=get_stats,                  outputs=stats_display)
    app.load(fn=get_deadline_panel_content, outputs=deadline_panel)
    app.load(fn=get_files_html,             outputs=files_panel)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting AI Chatbot with MCP Protocol + Deadline Tracker...")
    print("=" * 60)

    try:
        init_result = asyncio.run(initialize_mcp_servers())
        print(init_result)
        print("=" * 60)
    except Exception as e:
        print(f"Warning: MCP initialization failed - {e}")
        print("App will start but tools may not be available")
        import traceback
        traceback.print_exc()

    try:
        start_digest_scheduler()
        print("Digest scheduler started")
    except Exception as e:
        print(f"Digest scheduler failed to start: {e}")

    servers = mcp_client.get_all_servers()
    print(f"\nActive MCP Servers: {servers}")
    print(f"MCP Initialized: {mcp_initialized}")
    print("=" * 60 + "\n")

    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("APP_PORT", "7860")),
        share=False,
        show_error=True,
    )