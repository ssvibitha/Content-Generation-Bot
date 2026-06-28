"""
MCP Client - Production Ready
Manages communication with MCP servers via stdio using JSON-RPC protocol
"""
import asyncio
import json
import subprocess
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MCPServer:
    """Represents a connection to an MCP server"""
    
    def __init__(self, name: str, process: subprocess.Popen):
        self.name = name
        self.process = process
        self.request_id = 0
        self.initialized = False
    
    def get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def send_request(self, method: str, params: Optional[dict] = None) -> Any:
        """Send JSON-RPC request to server"""
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": method
        }
        
        if params:
            request["params"] = params
        
        request_json = json.dumps(request) + "\n"
        logger.debug(f"→ {self.name}: {request_json.strip()}")
        
        try:
            self.process.stdin.write(request_json.encode())
            self.process.stdin.flush()
        except Exception as e:
            raise Exception(f"Failed to send request: {e}")
        
        # Read response
        try:
            response_line = self.process.stdout.readline()
            if not response_line:
                raise Exception(f"No response from server {self.name}")
            
            logger.debug(f"← {self.name}: {response_line.decode().strip()}")
            response = json.loads(response_line)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
        except Exception as e:
            raise Exception(f"Failed to read response: {e}")
        
        if "error" in response:
            raise Exception(f"Server error: {response['error']}")
        
        return response.get("result")
    
    async def send_notification(self, method: str, params: Optional[dict] = None):
        """Send JSON-RPC notification (no response expected)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params:
            notification["params"] = params
        
        notification_json = json.dumps(notification) + "\n"
        logger.debug(f"→ {self.name} (notification): {notification_json.strip()}")
        
        self.process.stdin.write(notification_json.encode())
        self.process.stdin.flush()
    
    async def initialize(self):
        """Perform MCP initialization handshake"""
        if self.initialized:
            return
        
        logger.info(f"Initializing {self.name}...")
        
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-client",
                "version": "1.0.0"
            }
        }
        
        try:
            result = await self.send_request("initialize", init_params)
            await self.send_notification("notifications/initialized")
            await asyncio.sleep(0.1)
            
            self.initialized = True
            logger.info(f"✓ {self.name} initialized")
        except Exception as e:
            raise Exception(f"Initialization failed: {e}")
    
    def stop(self):
        """Stop the MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()


class MCPClient:
    """Client for managing multiple MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
    
    async def start_server(
        self, 
        name: str, 
        script_path: str,
        python_path: str = "python3"
    ) -> bool:
        """Start an MCP server process"""
        try:
            logger.info(f"Starting MCP server: {name}")
            
            # Verify script exists
            script = Path(script_path)
            if not script.exists():
                logger.error(f"Script not found: {script_path}")
                return False
            
            # Start subprocess
            process = subprocess.Popen(
                [python_path, str(script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                cwd=str(script.parent.parent.parent)  # Project root
            )
            
            # Give process time to start
            await asyncio.sleep(0.3)
            
            # Check if process is running
            if process.poll() is not None:
                stderr = process.stderr.read().decode()
                logger.error(f"Process died: {stderr}")
                return False
            
            # Create server instance
            server = MCPServer(name, process)
            
            # Initialize
            await server.initialize()
            
            # Verify with tools/list
            tools = await server.send_request("tools/list")
            
            # Handle different response formats
            if isinstance(tools, dict) and "tools" in tools:
                tool_list = tools["tools"]
            elif isinstance(tools, list):
                tool_list = tools
            else:
                logger.warning(f"Unexpected tools format: {type(tools)}")
                tool_list = []
            
            logger.info(f"✓ {name} started with {len(tool_list)} tools")
            self.servers[name] = server
            return True
            
        except Exception as e:
            logger.error(f"Error starting {name}: {e}")
            if 'process' in locals():
                process.terminate()
            return False
    
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: dict
    ) -> str:
        """Call a tool on a specific MCP server"""
        if server_name not in self.servers:
            raise Exception(f"Server {server_name} not found")
        
        server = self.servers[server_name]
        
        try:
            result = await server.send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            # Handle different response formats
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict) and "text" in content[0]:
                        return content[0]["text"]
            elif isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "text" in result[0]:
                    return result[0]["text"]
            
            return str(result)
        
        except Exception as e:
            logger.error(f"Error calling {tool_name} on {server_name}: {e}")
            return f"Error: {str(e)}"
    
    async def list_tools(self, server_name: str) -> List[dict]:
        """List available tools from a server"""
        if server_name not in self.servers:
            raise Exception(f"Server {server_name} not found")
        
        server = self.servers[server_name]
        result = await server.send_request("tools/list")
        
        # Handle different response formats
        if isinstance(result, dict) and "tools" in result:
            return result["tools"]
        elif isinstance(result, list):
            return result
        else:
            logger.warning(f"Unexpected tools format: {type(result)}")
            return []
    
    def get_all_servers(self) -> List[str]:
        """Get list of running servers"""
        return list(self.servers.keys())
    
    async def stop_server(self, name: str):
        """Stop a specific server"""
        if name in self.servers:
            self.servers[name].stop()
            del self.servers[name]
            logger.info(f"Stopped server: {name}")
    
    async def stop_all(self):
        """Stop all servers"""
        for name in list(self.servers.keys()):
            await self.stop_server(name)