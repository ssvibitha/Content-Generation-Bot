#!/usr/bin/env python3
"""
Debug script for MCP servers
Helps diagnose why servers might not be starting
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client.client import MCPClient

load_dotenv()

async def debug_mcp_servers():
    """Debug MCP server initialization"""
    print("\n" + "🔍 "*30)
    print("MCP SERVER DIAGNOSTIC")
    print("🔍 "*30 + "\n")
    
    client = MCPClient()
    
    # Check if server files exist
    print("1️⃣ Checking server files...")
    fs_server_path = Path("src/mcp_servers/fs_server.py")
    calc_server_path = Path("src/mcp_servers/calc_server.py")
    
    if fs_server_path.exists():
        print(f"  ✅ Found: {fs_server_path}")
    else:
        print(f"  ❌ Missing: {fs_server_path}")
        
    if calc_server_path.exists():
        print(f"  ✅ Found: {calc_server_path}")
    else:
        print(f"  ❌ Missing: {calc_server_path}")
    
    # Check test_files directory
    print("\n2️⃣ Checking test_files directory...")
    test_files_dir = Path("test_files")
    if test_files_dir.exists():
        files = list(test_files_dir.glob("*"))
        print(f"  ✅ Directory exists with {len(files)} file(s)")
        for f in files:
            print(f"     - {f.name}")
    else:
        print(f"  ❌ Missing: {test_files_dir}")
        print("  💡 Run: mkdir test_files && echo 'test' > test_files/test1.txt")
    
    # Try starting filesystem server
    print("\n3️⃣ Starting filesystem server...")
    try:
        fs_ok = await client.start_server(
            "filesystem",
            "src/mcp_servers/fs_server.py"
        )
        if fs_ok:
            print("  ✅ Filesystem server started")
            
            # Try listing tools
            tools = await client.list_tools("filesystem")
            print(f"  ✅ Found {len(tools)} tools:")
            for tool in tools:
                print(f"     - {tool['name']}: {tool.get('description', 'No description')}")
            
            # Try calling a tool
            print("\n  Testing list_files tool...")
            result = await client.call_tool("filesystem", "list_files", {"pattern": "*"})
            print(f"  ✅ Result: {result[:100]}...")
        else:
            print("  ❌ Filesystem server failed to start")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Try starting calculator server
    print("\n4️⃣ Starting calculator server...")
    try:
        calc_ok = await client.start_server(
            "calculator",
            "src/mcp_servers/calc_server.py"
        )
        if calc_ok:
            print("  ✅ Calculator server started")
            
            # Try listing tools
            tools = await client.list_tools("calculator")
            print(f"  ✅ Found {len(tools)} tools:")
            for tool in tools[:3]:  # Show first 3
                print(f"     - {tool['name']}: {tool.get('description', 'No description')}")
            if len(tools) > 3:
                print(f"     ... and {len(tools) - 3} more")
            
            # Try calling a tool
            print("\n  Testing add tool...")
            result = await client.call_tool("calculator", "add", {"numbers": [10, 20, 30]})
            print(f"  ✅ Result: {result[:100]}...")
        else:
            print("  ❌ Calculator server failed to start")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check running servers
    print("\n5️⃣ Summary...")
    servers = client.get_all_servers()
    print(f"  ✅ Active servers: {servers}")
    
    # Cleanup
    await client.stop_all()
    
    print("\n" + "="*60)
    if len(servers) == 2:
        print("✅ DIAGNOSIS: All systems operational!")
    elif len(servers) == 1:
        print("⚠️ DIAGNOSIS: Partial success - one server failed")
    else:
        print("❌ DIAGNOSIS: No servers started - check errors above")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(debug_mcp_servers())