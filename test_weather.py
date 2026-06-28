#!/usr/bin/env python3
"""
Test Weather MCP Server
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_client.client import MCPClient


async def test_weather_server():
    """Test weather server functionality"""
    
    client = MCPClient()
    
    print("\n" + "🌤️ "*30)
    print("TESTING WEATHER MCP SERVER")
    print("🌤️ "*30 + "\n")
    
    # Start weather server
    print("1️⃣ Starting weather server...")
    success = await client.start_server(
        "weather",
        "src/mcp_servers/weather_server.py"
    )
    
    if not success:
        print("❌ Failed to start weather server")
        return
    
    print("✅ Weather server started\n")
    
    # List tools
    print("2️⃣ Available tools:")
    tools = await client.list_tools("weather")
    for tool in tools:
        print(f"   • {tool['name']}: {tool['description']}")
    print()
    
    # Test: List cities
    print("3️⃣ Testing list_cities...")
    result = await client.call_tool("weather", "list_cities", {})
    print(result)
    print()
    
    # Test: Get current weather
    print("4️⃣ Testing get_current_weather (New York in Celsius)...")
    result = await client.call_tool(
        "weather",
        "get_current_weather",
        {"city": "New York", "unit": "C"}
    )
    print(result)
    print()
    
    # Test: Get current weather in Fahrenheit
    print("5️⃣ Testing get_current_weather (Tokyo in Fahrenheit)...")
    result = await client.call_tool(
        "weather",
        "get_current_weather",
        {"city": "Tokyo", "unit": "F"}
    )
    print(result)
    print()
    
    # Test: Get forecast
    print("6️⃣ Testing get_forecast (London, 3 days)...")
    result = await client.call_tool(
        "weather",
        "get_forecast",
        {"city": "London", "days": 3}
    )
    print(result)
    print()
    
    # Test: Compare weather
    print("7️⃣ Testing compare_weather (Dubai vs Moscow)...")
    result = await client.call_tool(
        "weather",
        "compare_weather",
        {"city1": "Dubai", "city2": "Moscow"}
    )
    print(result)
    print()
    
    # Test: Invalid city
    print("8️⃣ Testing error handling (Invalid city)...")
    result = await client.call_tool(
        "weather",
        "get_current_weather",
        {"city": "Atlantis"}
    )
    print(result)
    print()
    
    # Cleanup
    await client.stop_all()
    
    print("="*60)
    print("✅ All weather server tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_weather_server())