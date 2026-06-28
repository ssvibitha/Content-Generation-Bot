#!/usr/bin/env python3
"""
Calculator MCP Server
Mathematical operations via MCP protocol
"""
import asyncio
import math
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("calculator")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Define available calculator tools"""
    return [
        Tool(
            name="add",
            description="Add multiple numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Numbers to add",
                        "minItems": 2
                    }
                },
                "required": ["numbers"]
            }
        ),
        Tool(
            name="subtract",
            description="Subtract second number from first",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="multiply",
            description="Multiply numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Numbers to multiply",
                        "minItems": 2
                    }
                },
                "required": ["numbers"]
            }
        ),
        Tool(
            name="divide",
            description="Divide first number by second",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "Dividend"},
                    "b": {"type": "number", "description": "Divisor"},
                    "precision": {
                        "type": "integer",
                        "description": "Decimal places",
                        "default": 2
                    }
                },
                "required": ["a", "b"]
            }
        ),
        Tool(
            name="factorial",
            description="Calculate factorial (n!)",
            inputSchema={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number (0-20)",
                        "minimum": 0,
                        "maximum": 20
                    }
                },
                "required": ["n"]
            }
        ),
        Tool(
            name="convert_temperature",
            description="Convert temperature between C, F, K",
            inputSchema={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Temperature value"},
                    "from_unit": {
                        "type": "string",
                        "enum": ["C", "F", "K"],
                        "description": "Source unit"
                    },
                    "to_unit": {
                        "type": "string",
                        "enum": ["C", "F", "K"],
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        ),
        Tool(
            name="convert_distance",
            description="Convert distance between m, ft, mi, km",
            inputSchema={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Distance value"},
                    "from_unit": {
                        "type": "string",
                        "enum": ["m", "ft", "mi", "km"],
                        "description": "Source unit"
                    },
                    "to_unit": {
                        "type": "string",
                        "enum": ["m", "ft", "mi", "km"],
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        if name == "add":
            numbers = arguments["numbers"]
            result = sum(numbers)
            return [TextContent(
                type="text",
                text=f"Result: {result}\nCalculation: {' + '.join(map(str, numbers))} = {result}"
            )]
        
        elif name == "subtract":
            a, b = arguments["a"], arguments["b"]
            result = a - b
            return [TextContent(
                type="text",
                text=f"Result: {result}\nCalculation: {a} - {b} = {result}"
            )]
        
        elif name == "multiply":
            numbers = arguments["numbers"]
            result = 1
            for num in numbers:
                result *= num
            return [TextContent(
                type="text",
                text=f"Result: {result}\nCalculation: {' × '.join(map(str, numbers))} = {result}"
            )]
        
        elif name == "divide":
            a, b = arguments["a"], arguments["b"]
            precision = arguments.get("precision", 2)
            
            if b == 0:
                return [TextContent(type="text", text="Error: Division by zero")]
            
            result = round(a / b, precision)
            return [TextContent(
                type="text",
                text=f"Result: {result}\nCalculation: {a} ÷ {b} = {result}"
            )]
        
        elif name == "factorial":
            n = arguments["n"]
            
            if n < 0:
                return [TextContent(type="text", text="Error: Factorial undefined for negative numbers")]
            if n > 20:
                return [TextContent(type="text", text="Error: Factorial limited to n ≤ 20")]
            
            result = math.factorial(n)
            
            if n <= 5:
                steps = " × ".join(str(i) for i in range(1, n + 1)) if n > 0 else "1"
                calc = f"{n}! = {steps} = {result}"
            else:
                calc = f"{n}! = {result}"
            
            return [TextContent(type="text", text=f"Result: {result}\nCalculation: {calc}")]
        
        elif name == "convert_temperature":
            value = arguments["value"]
            from_unit = arguments["from_unit"]
            to_unit = arguments["to_unit"]
            
            if from_unit == to_unit:
                return [TextContent(
                    type="text",
                    text=f"Result: {value} {to_unit}\n(No conversion needed)"
                )]
            
            # Convert to Celsius
            if from_unit == "F":
                celsius = (value - 32) * 5/9
            elif from_unit == "K":
                celsius = value - 273.15
            else:
                celsius = value
            
            # Convert to target
            if to_unit == "F":
                result = celsius * 9/5 + 32
            elif to_unit == "K":
                result = celsius + 273.15
            else:
                result = celsius
            
            return [TextContent(
                type="text",
                text=f"Result: {result:.2f} {to_unit}\nConversion: {value} {from_unit} = {result:.2f} {to_unit}"
            )]
        
        elif name == "convert_distance":
            value = arguments["value"]
            from_unit = arguments["from_unit"]
            to_unit = arguments["to_unit"]
            
            if from_unit == to_unit:
                return [TextContent(
                    type="text",
                    text=f"Result: {value} {to_unit}\n(No conversion needed)"
                )]
            
            # Conversion factors
            to_meters = {"m": 1.0, "ft": 0.3048, "mi": 1609.34, "km": 1000.0}
            from_meters = {"m": 1.0, "ft": 3.28084, "mi": 0.000621371, "km": 0.001}
            
            meters = value * to_meters[from_unit]
            result = meters * from_meters[to_unit]
            
            unit_names = {"m": "meters", "ft": "feet", "mi": "miles", "km": "kilometers"}
            
            return [TextContent(
                type="text",
                text=f"Result: {result:.4f} {to_unit}\nConversion: {value} {unit_names[from_unit]} = {result:.4f} {unit_names[to_unit]}"
            )]
        
        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

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