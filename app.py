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
# CSS  — modern, clean, light workspace theme
# ---------------------------------------------------------------------------
# Token system
#   Surface   #FFFFFF   Canvas    #F5F6FA   Border   #E6E8F0
#   Text hi   #12131A   Text lo   #6B7280   Accent   #4338CA (indigo)
#   Accent soft #EEF0FE  Success  #0F9D58   Warning  #B7791F   Danger #D92D20
#   Display face: 'Manrope' (headings/labels) · Body/UI face: 'Inter'

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --canvas: #F5F6FA;
    --surface: #FFFFFF;
    --border: #E6E8F0;
    --text-hi: #12131A;
    --text-lo: #6B7280;
    --accent: #4338CA;
    --accent-soft: #EEF0FE;
    --success: #0F9D58;
    --warning: #B7791F;
    --danger: #D92D20;
}

* { box-sizing: border-box; }

.gradio-container {
    font-family: 'Inter', sans-serif !important;
    background: var(--canvas) !important;
    min-height: 100vh;
    color: var(--text-hi);
}

/* ── Header ── */
.app-header {
    padding: 18px 4px 10px !important;
    border-bottom: 1px solid var(--border);
    margin-bottom: 14px !important;
}
.app-header h1 {
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    font-size: 1.4rem;
    color: var(--text-hi);
    margin: 0 0 2px;
    letter-spacing: -0.01em;
}
.app-header h1 .accent-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    margin-right: 8px;
}
.app-header p {
    color: var(--text-lo);
    font-size: 0.85rem;
    margin: 0;
    font-weight: 500;
}

/* ── Sidebar panels ── */
.sidebar-panel {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 14px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03) !important;
}
.panel-title {
    font-family: 'Manrope', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-lo);
    margin: 2px 0 10px 2px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ── Empty state ── */
.empty-panel {
    color: var(--text-lo);
    font-size: 0.82rem;
    text-align: center;
    padding: 22px 10px;
    line-height: 1.6;
}
.empty-panel-icon {
    font-size: 1.1rem;
    color: var(--accent);
    margin-bottom: 6px;
    font-weight: 700;
}
.empty-panel-sub { color: #9CA3AF; font-size: 0.76rem; }
.empty-panel.error { color: var(--danger); }

/* ── Files sidebar ── */
.file-list { display: flex; flex-direction: column; gap: 6px; }
.file-item {
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--canvas);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 10px;
    transition: border-color 0.15s, background 0.15s;
}
.file-item:hover { border-color: var(--accent); background: var(--accent-soft); }
.file-icon {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    flex-shrink: 0;
    background: var(--accent-soft);
    color: var(--accent);
    border-radius: 6px;
    width: 30px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.file-info { flex: 1; min-width: 0; }
.file-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-hi);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.file-status {
    font-size: 0.7rem;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.file-status.ok   { color: var(--success); }
.file-status.warn { color: var(--warning); }
.file-status.err  { color: var(--danger); }
.file-remove-btn {
    background: transparent;
    border: none;
    color: #B0B4C0;
    border-radius: 6px;
    width: 22px;
    height: 22px;
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, color 0.15s;
}
.file-remove-btn:hover {
    background: #FEE4E2;
    color: var(--danger);
}

/* ── Deadline panel ── */
.deadline-panel {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 12px 14px !important;
    font-size: 0.83rem !important;
    max-height: 280px;
    overflow-y: auto;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03) !important;
}
.deadline-panel ul { margin: 0; padding-left: 18px; }
.deadline-panel li { margin-bottom: 6px; color: var(--text-hi); }
.deadline-panel strong { color: var(--accent); }
.deadline-panel::-webkit-scrollbar { width: 4px; }
.deadline-panel::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

/* ── Chat area ── */
.chatbot-wrap {
    border-radius: 16px !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03) !important;
}

/* ── Input bar ── */
.input-row {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 6px 8px;
    margin-top: 10px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}
.input-row:focus-within { border-color: var(--accent); }

/* + upload button */
.upload-plus-btn button {
    background: var(--accent-soft) !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    color: var(--accent) !important;
    font-size: 1.25rem !important;
    font-weight: 500 !important;
    width: 40px !important;
    min-width: 40px !important;
    height: 40px !important;
    padding: 0 !important;
    transition: background 0.15s !important;
    line-height: 1 !important;
}
.upload-plus-btn button:hover { background: #E0E4FC !important; }

/* Text input inside bar */
.chat-input textarea {
    background: transparent !important;
    border: none !important;
    color: var(--text-hi) !important;
    font-size: 0.92rem !important;
    resize: none !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 9px 4px !important;
    min-height: 40px !important;
    max-height: 120px !important;
}
.chat-input textarea::placeholder { color: #A3A7B5 !important; }
.chat-input .wrap { border: none !important; box-shadow: none !important; background: transparent !important; }

/* Send button */
.send-arrow-btn button {
    background: var(--accent) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-size: 1.05rem !important;
    width: 40px !important;
    min-width: 40px !important;
    height: 40px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: background 0.15s, transform 0.1s !important;
}
.send-arrow-btn button:hover {
    background: #372DB0 !important;
    transform: translateY(-1px) !important;
}

/* ── Secondary controls row ── */
.secondary-row { margin-top: 8px !important; align-items: center !important; }
.secondary-row button {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-lo) !important;
    border-radius: 9px !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    transition: border-color 0.15s, color 0.15s !important;
}
.secondary-row button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
.secondary-row label span { font-size: 0.78rem !important; color: var(--text-lo) !important; font-weight: 500 !important; }

/* ── Status box ── */
.status-box textarea {
    background: transparent !important;
    color: var(--text-lo) !important;
    border: none !important;
    font-size: 0.76rem !important;
    text-align: right;
}

/* ── Divider ── */
.sidebar-divider { border: none; border-top: 1px solid var(--border); margin: 4px 0 12px; }

/* ── Workspace accordion (stats / tools) ── */
.workspace-accordion { border: 1px solid var(--border) !important; border-radius: 14px !important; background: var(--surface) !important; }

/* ── Footer ── */
.app-footer {
    color: #9CA3AF !important;
    font-size: 0.74rem !important;
    text-align: center;
    padding-top: 14px;
    border-top: 1px solid var(--border);
    margin-top: 16px !important;
}

/* ── Hidden file input trick ── */
.hidden-upload { display: none !important; }

/* ── Scrollable sidebar ── */
.sidebar-scroll {
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    padding-right: 2px;
}
.sidebar-scroll::-webkit-scrollbar { width: 4px; }
.sidebar-scroll::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
"""

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

    // Wire the + button to click the hidden Gradio file input
    window.triggerFileUpload = function() {
        const inp = document.querySelector('#hidden-upload-input input[type=file]');
        if (inp) inp.click();
    };
}
"""

# ---------------------------------------------------------------------------
# Gradio App
# ---------------------------------------------------------------------------

app = gr.Blocks(
    title="Study Assistant · Deadline Tracker",
    css=_CSS,
    js=_JS_INIT,
    theme=gr.themes.Base(
        primary_hue="indigo",
        neutral_hue="gray",
        font=["Inter", "sans-serif"],
    ),
)

with app:
    # ── Header ──────────────────────────────────────────────────────────────
    with gr.Row(elem_classes=["app-header"]):
        gr.HTML("""
        <h1><span class="accent-dot"></span>Study Assistant</h1>
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

            # ── Input bar ───────────────────────────────────────────────────
            with gr.Row(elem_classes=["input-row"]):

                # + button (triggers hidden upload)
                upload_plus_btn = gr.Button(
                    "+",
                    scale=0,
                    min_width=40,
                    elem_classes=["upload-plus-btn"],
                )

                # Text input
                msg = gr.Textbox(
                    placeholder="Message… or ask “what's due this week?”",
                    show_label=False,
                    scale=1,
                    container=False,
                    lines=1,
                    max_lines=5,
                    elem_classes=["chat-input"],
                )

                # Send button
                submit_btn = gr.Button(
                    "↑",
                    scale=0,
                    min_width=40,
                    elem_classes=["send-arrow-btn"],
                )

            # ── Secondary controls row ───────────────────────────────────────
            with gr.Row(elem_classes=["secondary-row"]):
                clear_btn = gr.Button("Clear chat", size="sm")
                use_tools_cb = gr.Checkbox(
                    label="MCP tools",
                    value=True,
                    scale=0,
                )
                status_text = gr.Textbox(
                    value="Initializing…",
                    show_label=False,
                    interactive=False,
                    scale=2,
                    elem_classes=["status-box"],
                )

        # ━━━━━━━━━━━━━━━━ RIGHT: Files + Deadlines ━━━━━━━━━━━━━━━━━━━━━━━━
        with gr.Column(scale=2, min_width=280, elem_classes=["sidebar-scroll"]):

            # ── Uploaded Files panel ─────────────────────────────────────────
            gr.HTML("<div class='panel-title'>Uploaded files</div>")
            files_panel = gr.HTML(
                value=get_files_html(),
                elem_classes=["sidebar-panel"],
            )

            # Hidden: file uploader (triggered by + button)
            hidden_upload = gr.File(
                label="",
                file_types=[".txt", ".md", ".pdf"],
                type="filepath",
                visible=False,
                elem_id="hidden-upload-input",
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

            # ── Workspace (stats / tools / examples), tucked away ─────────────
            with gr.Accordion("Workspace", open=False, elem_classes=["workspace-accordion"]):
                stats_display = gr.Markdown(get_stats())
                refresh_stats_btn = gr.Button("Refresh stats", size="sm")

                with gr.Accordion("Available tools", open=False):
                    tools_display = gr.Markdown("Loading tools…")
                    refresh_tools_btn = gr.Button("Refresh tools", size="sm")

                with gr.Accordion("Quick examples", open=False):
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

    # + button → trigger hidden file input via JS
    upload_plus_btn.click(
        fn=None,
        js="() => { window.triggerFileUpload(); }",
    )

    # When hidden upload receives a file → extract + refresh sidebar + deadline panel
    hidden_upload.upload(
        fn=handle_file_upload,
        inputs=[hidden_upload],
        outputs=[files_panel, deadline_panel, upload_status_md],
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