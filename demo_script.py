#!/usr/bin/env python3
"""
Interactive Demo - Showcase All MCP Features
This script demonstrates all available tools in action
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client.client import MCPClient


async def demo_section(title: str):
    """Print a section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


async def run_demo():
    """Run complete feature demonstration"""
    
    client = MCPClient()
    
    print("\n" + "🎬 "*30)
    print("AI CHATBOT MCP PROTOCOL - FEATURE DEMONSTRATION")
    print("🎬 "*30 + "\n")
    
    # Initialize all servers
    print("🚀 Initializing MCP servers...")
    
    await client.start_server("filesystem", "src/mcp_servers/fs_server.py")
    await client.start_server("calculator", "src/mcp_servers/calc_server.py")
    await client.start_server("weather", "src/mcp_servers/weather_server.py")
    
    servers = client.get_all_servers()
    print(f"✅ {len(servers)} servers running: {', '.join(servers)}\n")
    
    # =================================================================
    # FILESYSTEM DEMONSTRATIONS
    # =================================================================
    
    await demo_section("📁 FILESYSTEM OPERATIONS")
    
    print("1️⃣ Listing all files...")
    result = await client.call_tool("filesystem", "list_files", {"pattern": "*"})
    print(result)
    
    print("\n2️⃣ Reading a specific file (test1.txt)...")
    result = await client.call_tool("filesystem", "read_file", {"filename": "test1.txt"})
    print(result)
    
    print("\n3️⃣ Searching for 'MCP' in all files...")
    result = await client.call_tool("filesystem", "search_files", {"query": "MCP"})
    print(result)
    
    await asyncio.sleep(2)
    
    # =================================================================
    # CALCULATOR DEMONSTRATIONS
    # =================================================================
    
    await demo_section("🔢 CALCULATOR OPERATIONS")
    
    print("1️⃣ Addition: 10 + 20 + 30...")
    result = await client.call_tool("calculator", "add", {"numbers": [10, 20, 30]})
    print(result)
    
    print("\n2️⃣ Subtraction: 100 - 45...")
    result = await client.call_tool("calculator", "subtract", {"a": 100, "b": 45})
    print(result)
    
    print("\n3️⃣ Multiplication: 5 × 10 × 15...")
    result = await client.call_tool("calculator", "multiply", {"numbers": [5, 10, 15]})
    print(result)
    
    print("\n4️⃣ Division: 144 ÷ 12...")
    result = await client.call_tool("calculator", "divide", {"a": 144, "b": 12})
    print(result)
    
    print("\n5️⃣ Factorial: 8!...")
    result = await client.call_tool("calculator", "factorial", {"n": 8})
    print(result)
    
    await asyncio.sleep(2)
    
    # =================================================================
    # CONVERSION DEMONSTRATIONS
    # =================================================================
    
    await demo_section("🌡️ TEMPERATURE & DISTANCE CONVERSIONS")
    
    print("1️⃣ Temperature: 100°F → Celsius...")
    result = await client.call_tool(
        "calculator", 
        "convert_temperature", 
        {"value": 100, "from_unit": "F", "to_unit": "C"}
    )
    print(result)
    
    print("\n2️⃣ Temperature: 0°C → Fahrenheit...")
    result = await client.call_tool(
        "calculator",
        "convert_temperature",
        {"value": 0, "from_unit": "C", "to_unit": "F"}
    )
    print(result)
    
    print("\n3️⃣ Distance: 5 miles → kilometers...")
    result = await client.call_tool(
        "calculator",
        "convert_distance",
        {"value": 5, "from_unit": "mi", "to_unit": "km"}
    )
    print(result)
    
    print("\n4️⃣ Distance: 100 meters → feet...")
    result = await client.call_tool(
        "calculator",
        "convert_distance",
        {"value": 100, "from_unit": "m", "to_unit": "ft"}
    )
    print(result)
    
    await asyncio.sleep(2)
    
    # =================================================================
    # WEATHER DEMONSTRATIONS
    # =================================================================
    
    await demo_section("🌤️ WEATHER INFORMATION")
    
    print("1️⃣ Listing all available cities...")
    result = await client.call_tool("weather", "list_cities", {})
    print(result)
    
    print("\n2️⃣ Current weather in London (Celsius)...")
    result = await client.call_tool(
        "weather",
        "get_current_weather",
        {"city": "London", "unit": "C"}
    )
    print(result)
    
    print("\n3️⃣ Current weather in Tokyo (Fahrenheit)...")
    result = await client.call_tool(
        "weather",
        "get_current_weather",
        {"city": "Tokyo", "unit": "F"}
    )
    print(result)
    
    print("\n4️⃣ 3-day forecast for Paris...")
    result = await client.call_tool(
        "weather",
        "get_forecast",
        {"city": "Paris", "days": 3}
    )
    print(result)
    
    print("\n5️⃣ Comparing Dubai vs Moscow weather...")
    result = await client.call_tool(
        "weather",
        "compare_weather",
        {"city1": "Dubai", "city2": "Moscow"}
    )
    print(result)
    
    await asyncio.sleep(2)
    
    # =================================================================
    # SUMMARY
    # =================================================================
    
    await demo_section("📊 DEMONSTRATION SUMMARY")
    
    # Count total tools
    total_tools = 0
    for server_name in servers:
        tools = await client.list_tools(server_name)
        total_tools += len(tools)
        print(f"✅ {server_name.upper()}: {len(tools)} tools")
    
    print(f"\n🎯 Total: {total_tools} tools across {len(servers)} MCP servers")
    
    print("\n✨ Feature Highlights:")
    print("   • Real MCP protocol with stdio communication")
    print("   • JSON-RPC 2.0 compliant")
    print("   • Async/await architecture")
    print("   • Tool chaining support")
    print("   • Error handling")
    print("   • Multi-server orchestration")
    
    # Cleanup
    await client.stop_all()
    
    print("\n" + "="*70)
    print("🎉 DEMONSTRATION COMPLETE!")
    print("="*70)
    print("\n💡 Next: Run 'python app.py' to try it with AI integration!\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
