#!/usr/bin/env python3
"""
Weather MCP Server
Provides weather data and forecasts via MCP protocol
"""
import asyncio
import random
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("weather")

# Mock weather database
CITIES = {
    "new york": {"temp": 22, "condition": "Partly Cloudy", "emoji": "⛅"},
    "london": {"temp": 15, "condition": "Rainy", "emoji": "🌧️"},
    "tokyo": {"temp": 28, "condition": "Sunny", "emoji": "☀️"},
    "paris": {"temp": 18, "condition": "Cloudy", "emoji": "☁️"},
    "sydney": {"temp": 25, "condition": "Clear", "emoji": "🌤️"},
    "dubai": {"temp": 38, "condition": "Hot and Sunny", "emoji": "🌞"},
    "moscow": {"temp": 5, "condition": "Cold and Snowy", "emoji": "❄️"},
    "mumbai": {"temp": 32, "condition": "Humid", "emoji": "🌫️"},
    "san francisco": {"temp": 20, "condition": "Foggy", "emoji": "🌁"},
    "singapore": {"temp": 30, "condition": "Tropical", "emoji": "🌴"},
}

CONDITIONS = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Clear", "Windy", "Stormy"]

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Define available weather tools"""
    return [
        Tool(
            name="get_current_weather",
            description="Get current weather conditions for any city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g., 'New York', 'London', 'Tokyo')"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["C", "F"],
                        "description": "Temperature unit: C for Celsius, F for Fahrenheit",
                        "default": "C"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_forecast",
            description="Get 5-day weather forecast for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days (1-7)",
                        "minimum": 1,
                        "maximum": 7,
                        "default": 5
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="list_cities",
            description="List all cities with available weather data",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="compare_weather",
            description="Compare weather between two cities",
            inputSchema={
                "type": "object",
                "properties": {
                    "city1": {
                        "type": "string",
                        "description": "First city name"
                    },
                    "city2": {
                        "type": "string",
                        "description": "Second city name"
                    }
                },
                "required": ["city1", "city2"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        if name == "get_current_weather":
            city = arguments["city"].lower()
            unit = arguments.get("unit", "C")
            
            if city not in CITIES:
                available = ", ".join([c.title() for c in sorted(CITIES.keys())])
                return [TextContent(
                    type="text",
                    text=f"❌ Weather data not available for '{city}'.\n\n📍 Available cities:\n{available}"
                )]
            
            weather = CITIES[city]
            temp = weather["temp"]
            
            # Convert to Fahrenheit if needed
            if unit == "F":
                temp = temp * 9/5 + 32
                unit_name = "°F"
            else:
                unit_name = "°C"
            
            # Add realistic details
            humidity = random.randint(40, 80)
            wind_speed = random.randint(5, 25)
            pressure = random.randint(1010, 1025)
            
            result = f"""{weather["emoji"]} Current Weather in {city.title()}

🌡️  Temperature: {temp:.1f}{unit_name}
☁️  Condition: {weather["condition"]}
💧 Humidity: {humidity}%
💨 Wind Speed: {wind_speed} km/h
📊 Pressure: {pressure} hPa

📅 Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}"""
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_forecast":
            city = arguments["city"].lower()
            days = arguments.get("days", 5)
            
            if city not in CITIES:
                return [TextContent(
                    type="text",
                    text=f"❌ Forecast not available for '{city}'"
                )]
            
            base_temp = CITIES[city]["temp"]
            today = datetime.now()
            
            forecast = f"📅 {days}-Day Weather Forecast for {city.title()}\n\n"
            
            for i in range(days):
                day = today + timedelta(days=i)
                day_name = day.strftime("%A, %b %d")
                
                # Vary temperature
                temp = base_temp + random.randint(-5, 5)
                condition = random.choice(CONDITIONS)
                high = temp + random.randint(2, 5)
                low = temp - random.randint(2, 5)
                
                # Add emoji based on condition
                emoji = "☀️" if "Sunny" in condition else "☁️" if "Cloudy" in condition else "🌧️" if "Rain" in condition else "🌤️"
                
                forecast += f"{emoji} {day_name}\n"
                forecast += f"   High: {high}°C | Low: {low}°C\n"
                forecast += f"   {condition}\n\n"
            
            return [TextContent(type="text", text=forecast)]
        
        elif name == "list_cities":
            cities_list = "🌍 Available Cities for Weather Data:\n\n"
            
            for city, data in sorted(CITIES.items()):
                cities_list += f"{data['emoji']} {city.title():<15} - {data['temp']}°C, {data['condition']}\n"
            
            cities_list += f"\n📊 Total cities: {len(CITIES)}"
            
            return [TextContent(type="text", text=cities_list)]
        
        elif name == "compare_weather":
            city1 = arguments["city1"].lower()
            city2 = arguments["city2"].lower()
            
            if city1 not in CITIES or city2 not in CITIES:
                return [TextContent(
                    type="text",
                    text=f"❌ One or both cities not found. Use 'list_cities' to see available cities."
                )]
            
            w1 = CITIES[city1]
            w2 = CITIES[city2]
            
            temp_diff = abs(w1["temp"] - w2["temp"])
            warmer = city1.title() if w1["temp"] > w2["temp"] else city2.title()
            
            comparison = f"""🌡️ Weather Comparison

{w1["emoji"]} {city1.title()}:
   Temperature: {w1["temp"]}°C
   Condition: {w1["condition"]}

{w2["emoji"]} {city2.title()}:
   Temperature: {w2["temp"]}°C
   Condition: {w2["condition"]}

📊 Analysis:
   • {warmer} is warmer by {temp_diff}°C
   • Temperature difference: {temp_diff}°C"""
            
            return [TextContent(type="text", text=comparison)]
        
        else:
            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())