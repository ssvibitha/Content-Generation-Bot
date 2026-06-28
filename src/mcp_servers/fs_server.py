#!/usr/bin/env python3
"""
File System MCP Server
A real MCP server that communicates via stdio using JSON-RPC
"""
import asyncio
import os
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# import sys
# import logging

# logging.basicConfig(
#     stream=sys.stderr,
#     level=logging.INFO
# )

# Initialize MCP server
app = Server("filesystem")

# Get base path from environment or use default
BASE_PATH = Path(os.getenv("FILE_SERVER_PATH", "./test_files"))
BASE_PATH.mkdir(exist_ok=True)

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Define available tools"""
    return [
        Tool(
            name="list_files",
            description="List all files in the directory with optional pattern matching",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.txt')",
                        "default": "*"
                    }
                }
            }
        ),
        Tool(
            name="read_file",
            description="Read the contents of a specific file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to read"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="search_files",
            description="Search for text content within all files",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        if name == "list_files":
            pattern = arguments.get("pattern", "*")
            files = [
                f.name 
                for f in BASE_PATH.glob(pattern) 
                if f.is_file()
            ]
            
            if not files:
                result = f"No files found matching pattern: {pattern}"
            else:
                result = f"Files found ({len(files)}):\n" + "\n".join(
                    f"  - {f}" for f in sorted(files)
                )
            
            return [TextContent(type="text", text=result)]
        
        elif name == "read_file":
            filename = arguments["filename"]
            path = BASE_PATH / filename
            
            # Security: Validate path
            if not str(path.resolve()).startswith(str(BASE_PATH.resolve())):
                return [TextContent(
                    type="text",
                    text="Error: Access denied to file outside allowed directory"
                )]
            
            if not path.exists():
                return [TextContent(
                    type="text",
                    text=f"Error: File '{filename}' not found"
                )]
            
            try:
                content = path.read_text(encoding='utf-8')
                result = f"Contents of {filename}:\n\n{content}"
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"Error reading file: {str(e)}"
                )]
        
        elif name == "search_files":
            query = arguments["query"]
            query_lower = query.lower()
            results = []
            
            for file in BASE_PATH.rglob("*"):
                if file.is_file():
                    try:
                        content = file.read_text(encoding='utf-8')
                        if query_lower in content.lower():
                            lines = content.split('\n')
                            matching_lines = [
                                f"  Line {i+1}: {line.strip()}" 
                                for i, line in enumerate(lines) 
                                if query_lower in line.lower()
                            ]
                            results.append(
                                f"{file.relative_to(BASE_PATH)}:\n" + 
                                "\n".join(matching_lines[:3])
                            )
                    except:
                        pass
            
            if not results:
                result = f"No matches found for: {query}"
            else:
                result = f"Found '{query}' in {len(results)} file(s):\n\n" + "\n\n".join(results)
            
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]

async def main():
    """Run the MCP server using stdio transport"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())