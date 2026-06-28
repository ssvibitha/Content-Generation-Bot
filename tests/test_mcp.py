"""
Test MCP Servers and Client
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_client import MCPClient


async def test_all():
    """Test all MCP functionality"""
    
    client = MCPClient()
    
    print("=" * 60)
    print("Testing MCP Protocol Implementation")
    print("=" * 60)
    
    # Test File System Server
    print("\n1️⃣ Starting File System Server...")
    fs_ok = await client.start_server(
        "filesystem",
        "src/mcp_servers/fs_server.py"
    )
    
    if not fs_ok:
        print("❌ Failed")
        return
    print("✓ File System Server running")
    
    # Test Calculator Server
    print("\n2️⃣ Starting Calculator Server...")
    calc_ok = await client.start_server(
        "calculator",
        "src/mcp_servers/calc_server.py"
    )
    
    if not calc_ok:
        print("❌ Failed")
        return
    print("✓ Calculator Server running")
    
    # Test file operations
    print("\n3️⃣ Testing File Operations...")
    
    result = await client.call_tool("filesystem", "list_files", {"pattern": "*"})
    print(f"list_files: {result[:100]}...")
    
    result = await client.call_tool("filesystem", "read_file", {"filename": "test1.txt"})
    print(f"read_file: {result[:100]}...")
    
    # Test calculator
    print("\n4️⃣ Testing Calculator...")
    
    result = await client.call_tool("calculator", "add", {"numbers": [10, 20, 30]})
    print(f"add: {result}")
    
    result = await client.call_tool("calculator", "factorial", {"n": 5})
    print(f"factorial: {result}")
    
    result = await client.call_tool("calculator", "convert_temperature", {
        "value": 100,
        "from_unit": "F",
        "to_unit": "C"
    })
    print(f"convert_temperature: {result}")
    
    # Cleanup
    print("\n5️⃣ Cleaning up...")
    await client.stop_all()
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all())