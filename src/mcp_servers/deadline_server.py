#!/usr/bin/env python3
"""
Deadline MCP Server
Exposes deadline tracking operations as MCP tools via stdio JSON-RPC.

Tools:
    get_upcoming_deadlines(days)    — deadlines due within N days
    get_all_deadlines()             — every deadline in the DB
    mark_done(assignment_name)      — mark an assignment complete
    add_deadline(course,            — manually add a deadline
                 assignment,
                 due_date)
"""

import asyncio
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import deadline_db
_src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_src_dir))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from deadline_db import (
    get_upcoming_deadlines as _get_upcoming,
    get_all_deadlines as _get_all,
    mark_done as _mark_done,
    add_deadline as _add_deadline,
    format_deadlines_as_markdown,
)

app = Server("deadline")


# ---------------------------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Describe all deadline tools."""
    return [
        Tool(
            name="get_upcoming_deadlines",
            description=(
                "Return student deadlines due within the next N days "
                "(default 3). Use this when the user asks things like "
                "'what's due this week?', 'what do I have coming up?', "
                "'any deadlines soon?', 'show my upcoming assignments'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days from today to look ahead (default 3, max 30).",
                        "default": 3,
                    }
                },
            },
        ),
        Tool(
            name="get_all_deadlines",
            description=(
                "Return ALL deadlines stored in the tracker (pending and done). "
                "Use when the user wants a full list of all tracked assignments."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="mark_done",
            description=(
                "Mark an assignment as completed/done. "
                "Use when the user says 'I finished X', 'mark X as done', "
                "'I submitted X'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "assignment_name": {
                        "type": "string",
                        "description": "Name of the assignment to mark done.",
                    }
                },
                "required": ["assignment_name"],
            },
        ),
        Tool(
            name="add_deadline",
            description=(
                "Manually add a deadline to the tracker. "
                "Use when the user says 'add a deadline for...', "
                "'remind me about...'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "course": {
                        "type": "string",
                        "description": "Course name or code (e.g. 'CS 101').",
                    },
                    "assignment": {
                        "type": "string",
                        "description": "Assignment or exam name.",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD format.",
                    },
                },
                "required": ["course", "assignment", "due_date"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool Execution
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls."""
    try:

        # ── get_upcoming_deadlines ──────────────────────────────────────────
        if name == "get_upcoming_deadlines":
            days = int(arguments.get("days", 3))
            days = max(1, min(days, 30))         # clamp 1-30
            deadlines = _get_upcoming(days)

            if not deadlines:
                text = (
                    f"🎉 No pending deadlines in the next {days} day(s). "
                    "You're all caught up!"
                )
            else:
                text = (
                    f"📅 **Upcoming Deadlines (next {days} day(s)):**\n\n"
                    + format_deadlines_as_markdown(deadlines)
                )

            return [TextContent(type="text", text=text)]

        # ── get_all_deadlines ───────────────────────────────────────────────
        elif name == "get_all_deadlines":
            deadlines = _get_all()

            if not deadlines:
                text = "📭 No deadlines tracked yet. Upload a syllabus to get started!"
            else:
                # Add days_left for pending items
                from datetime import date
                today = date.today()
                for d in deadlines:
                    try:
                        due = date.fromisoformat(d["due_date"])
                        d["days_left"] = (due - today).days
                    except ValueError:
                        d["days_left"] = None

                text = (
                    f"📋 **All Tracked Deadlines ({len(deadlines)} total):**\n\n"
                    + format_deadlines_as_markdown(deadlines)
                )

            return [TextContent(type="text", text=text)]

        # ── mark_done ───────────────────────────────────────────────────────
        elif name == "mark_done":
            assignment_name = arguments.get("assignment_name", "").strip()
            if not assignment_name:
                return [TextContent(
                    type="text",
                    text="❌ Error: 'assignment_name' is required.",
                )]

            count = _mark_done(assignment_name)
            if count > 0:
                text = f"✅ Marked **'{assignment_name}'** as done! ({count} entry updated)"
            else:
                text = (
                    f"⚠️ No pending deadline found matching **'{assignment_name}'**. "
                    "Check the exact assignment name."
                )

            return [TextContent(type="text", text=text)]

        # ── add_deadline ────────────────────────────────────────────────────
        elif name == "add_deadline":
            course     = arguments.get("course", "").strip()
            assignment = arguments.get("assignment", "").strip()
            due_date   = arguments.get("due_date", "").strip()

            if not (course and assignment and due_date):
                return [TextContent(
                    type="text",
                    text="❌ Error: 'course', 'assignment', and 'due_date' are all required.",
                )]

            added = _add_deadline(course, assignment, due_date, source_file="chat")
            if added:
                text = (
                    f"📌 Added deadline: **[{course}] {assignment}** → due {due_date}"
                )
            else:
                text = (
                    f"⚠️ This deadline already exists: "
                    f"**[{course}] {assignment}** due {due_date}"
                )

            return [TextContent(type="text", text=text)]

        # ── unknown ─────────────────────────────────────────────────────────
        else:
            return [TextContent(
                type="text",
                text=f"❌ Unknown tool: '{name}'",
            )]

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        return [TextContent(
            type="text",
            text=f"❌ Error executing '{name}': {str(e)}\n{err}",
        )]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
