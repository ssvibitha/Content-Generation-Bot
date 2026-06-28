#!/usr/bin/env python3
"""
Manual test showing MCP initialization sequence
"""
import subprocess
import json
import sys

def send_request(process, request):
    """Send JSON-RPC request and get response"""
    request_json = json.dumps(request) + "\n"
    process.stdin.write(request_json.encode())
    process.stdin.flush()
    
    response_line = process.stdout.readline()
    return json.loads(response_line)


def main():
    # Start MCP server
    process = subprocess.Popen(
        ["python", "src/mcp_servers/fs_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print("Step 1: Initialize")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    response = send_request(process, init_request)
    print(f"Response: {json.dumps(response, indent=2)}\n")
    
    print("Step 2: Send initialized notification")
    initialized = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    process.stdin.write((json.dumps(initialized) + "\n").encode())
    process.stdin.flush()
    
    print("Step 3: List tools")
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    response = send_request(process, list_request)
    print(f"Tools: {json.dumps(response, indent=2)}\n")
    
    print("Step 4: Call a tool")
    call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "list_files",
            "arguments": {"pattern": "*"}
        }
    }
    
    response = send_request(process, call_request)
    print(f"Result: {json.dumps(response, indent=2)}")
    
    # Cleanup
    process.terminate()
    process.wait()
    print("\n✓ Test completed")


if __name__ == "__main__":
    main()