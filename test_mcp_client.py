"""
Test script for MCP Client
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client.client import MCPClient


async def test_client():
    """Test MCP client functionality"""
    
    client = MCPClient()
    
    # Start file system server
    print("Starting file system server...")
    success = await client.start_server(
        "filesystem",
        "src/mcp_servers/fs_server.py"
    )
    
    if not success:
        print("❌ Failed to start server")
        return
    
    print("✓ Server started successfully")
    
    # List tools
    print("\nListing tools...")
    tools = await client.list_tools("filesystem")
    print(f"tools ==========%%%%%$$$$$$$$$$$==={tools}['tools]")
    # for tool in tools:
    #     print(f"  - {tool['name']}: {tool['description']}")
    for tool in tools:
        print(f"tool ====>>>>>>>>>>>>>>>{tool}")
    
    # Test list_files
    print("\n--- Testing list_files ---")
    result = await client.call_tool(
        "filesystem",
        "list_files",
        {"pattern": "*"}
    )
    print(result)
    
    # Test read_file
    print("\n--- Testing read_file ---")
    result = await client.call_tool(
        "filesystem",
        "read_file",
        {"filename": "test1.txt"}
    )
    print(result)
    
    # Test search
    print("\n--- Testing search_files ---")
    result = await client.call_tool(
        "filesystem",
        "search_files",
        {"query": "MCP"}
    )
    print(result)
    
    # Cleanup
    await client.stop_all()
    print("\n✓ Test completed")


if __name__ == "__main__":
    asyncio.run(test_client())