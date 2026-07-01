# """
# Azure OpenAI Client with MCP Integration - Gradio 6.0 Compatible
# """
# import os
# import json
# import logging
# from typing import List, Dict, Any, Optional
# from openai import AsyncAzureOpenAI
# from dotenv import load_dotenv

# load_dotenv()
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class AzureOpenAIClient:
#     """Client for Azure OpenAI with MCP tool integration"""
    
#     def __init__(self):
#         self.client = AsyncAzureOpenAI(
#             api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#             api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
#             azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
#         )
#         self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
#         self.conversation_history = []
#         self.max_history = int(os.getenv("MAX_HISTORY", "50"))
    
#     async def _get_mcp_tools(self, mcp_client) -> List[Dict]:
#         """Get tools from all MCP servers"""
#         functions = []
        
#         for server_name in mcp_client.get_all_servers():
#             try:
#                 tools = await mcp_client.list_tools(server_name)
                
#                 for tool in tools:
#                     # Create function definition
#                     function = {
#                         "type": "function",
#                         "function": {
#                             "name": f"{server_name}_{tool['name']}",
#                             "description": f"{tool.get('description', tool['name'])}",
#                             "parameters": tool.get('inputSchema', {
#                                 "type": "object",
#                                 "properties": {},
#                                 "required": []
#                             })
#                         }
#                     }
#                     functions.append(function)
#                     logger.info(f"Added tool: {function['function']['name']}")
#             except Exception as e:
#                 logger.error(f"Error getting tools from {server_name}: {e}")
        
#         return functions
    
#     async def chat(
#         self,
#         message: str,
#         mcp_client=None,
#         use_tools: bool = True,
#         temperature: float = 0.7,
#         max_completion_tokens: int = 2000
#     ) -> str:
#         """Send message and get response with optional MCP tool usage"""
        
#         # Add user message to history
#         self.conversation_history.append({
#             "role": "user",
#             "content": message
#         })
        
#         # Prepare messages
#         messages = self._prepare_messages()
        
#         # Get tools if available
#         tools = None
#         if use_tools and mcp_client and mcp_client.get_all_servers():
#             tools = await self._get_mcp_tools(mcp_client)
#             logger.info(f"Available tools: {len(tools)}")
        
#         try:
#             # Make API call
#             response = await self.client.chat.completions.create(
#                 model=self.deployment,
#                 messages=messages,
#                 temperature=temperature,
#                 max_completion_tokens=max_completion_tokens,
#                 tools=tools if tools else None,
#                 tool_choice="auto" if tools else None
#             )
            
#             assistant_message = response.choices[0].message
            
#             # Check if tool was called
#             if assistant_message.tool_calls:
#                 logger.info(f"🔧 AI is calling {len(assistant_message.tool_calls)} tool(s)")
#                 return await self._handle_tool_calls(
#                     assistant_message,
#                     mcp_client,
#                     temperature,
#                     max_completion_tokens
#                 )
#             else:
#                 # Regular response
#                 logger.info("💬 AI responded without tools")
#                 response_text = assistant_message.content
#                 self.conversation_history.append({
#                     "role": "assistant",
#                     "content": response_text
#                 })
#                 return response_text
                
#         except Exception as e:
#             error_msg = f"Error calling Azure OpenAI: {str(e)}"
#             logger.error(error_msg)
#             import traceback
#             traceback.print_exc()
#             return error_msg
    
#     async def _handle_tool_calls(
#         self,
#         assistant_message,
#         mcp_client,
#         temperature,
#         max_completion_tokens
#     ) -> str:
#         """Handle MCP tool calls from AI"""
        
#         # Add assistant message with tool calls
#         tool_calls_formatted = []
#         for tc in assistant_message.tool_calls:
#             tool_calls_formatted.append({
#                 "id": tc.id,
#                 "type": "function",
#                 "function": {
#                     "name": tc.function.name,
#                     "arguments": tc.function.arguments
#                 }
#             })
        
#         self.conversation_history.append({
#             "role": "assistant",
#             "content": assistant_message.content,
#             "tool_calls": tool_calls_formatted
#         })
        
#         # Execute each tool call via MCP
#         tool_results = []
#         for tool_call in assistant_message.tool_calls:
#             function_name = tool_call.function.name
            
#             try:
#                 function_args = json.loads(tool_call.function.arguments)
#             except json.JSONDecodeError as e:
#                 logger.error(f"Failed to parse arguments: {tool_call.function.arguments}")
#                 result = f"Error: Invalid JSON arguments"
#                 tool_results.append({
#                     "tool_call_id": tool_call.id,
#                     "role": "tool",
#                     "name": function_name,
#                     "content": result
#                 })
#                 continue
            
#             # Parse server_name and tool_name
#             # Format: "servername_toolname"
#             if "_" in function_name:
#                 parts = function_name.split("_", 1)
#                 server_name = parts[0]
#                 tool_name = parts[1]
                
#                 logger.info(f"🔧 Calling {server_name}.{tool_name} with args: {function_args}")
                
#                 try:
#                     # Call MCP tool
#                     result = await mcp_client.call_tool(
#                         server_name,
#                         tool_name,
#                         function_args
#                     )
#                     logger.info(f"✅ Tool result: {result[:100]}...")
#                 except Exception as e:
#                     result = f"Error executing tool: {str(e)}"
#                     logger.error(f"❌ Tool error: {e}")
#                     import traceback
#                     traceback.print_exc()
#             else:
#                 result = f"Error: Invalid function name format: {function_name}"
#                 logger.error(result)
            
#             # Add tool result to conversation
#             tool_results.append({
#                 "tool_call_id": tool_call.id,
#                 "role": "tool",
#                 "name": function_name,
#                 "content": result
#             })
        
#         # Add all tool results to history
#         self.conversation_history.extend(tool_results)
        
#         # Get final response from AI
#         messages = self._prepare_messages()
        
#         final_response = await self.client.chat.completions.create(
#             model=self.deployment,
#             messages=messages,
#             temperature=temperature,
#             max_completion_tokens=max_completion_tokens
#         )
        
#         final_text = final_response.choices[0].message.content
#         self.conversation_history.append({
#             "role": "assistant",
#             "content": final_text
#         })
        
#         return final_text
    
#     def _prepare_messages(self) -> List[Dict]:
#         """Prepare messages for API call"""
#         # Enhanced system message that encourages tool use
#         system_message = {
#             "role": "system",
#             "content": """You are a helpful AI assistant with access to tools for file operations and calculations.

# IMPORTANT: When users ask you to:
# - "list files", "show files", "what files" → USE the filesystem_list_files tool
# - "read file", "show file contents", "open file" → USE the filesystem_read_file tool  
# - "search files", "find in files" → USE the filesystem_search_files tool
# - "add", "sum", "calculate sum" → USE the calculator_add tool
# - "subtract", "minus" → USE the calculator_subtract tool
# - "multiply", "times" → USE the calculator_multiply tool
# - "divide" → USE the calculator_divide tool
# - "factorial" → USE the calculator_factorial tool
# - "convert temperature" → USE the calculator_convert_temperature tool
# - "convert distance" → USE the calculator_convert_distance tool

# ALWAYS use the appropriate tool when the user's request matches these patterns. Do not just describe what you would do - actually call the tool.

# When you use a tool, interpret the results and present them in a friendly, conversational way."""
#         }
        
#         messages = [system_message]
        
#         # Add conversation history (limit to max_history)
#         if len(self.conversation_history) > self.max_history:
#             messages.extend(self.conversation_history[-self.max_history:])
#         else:
#             messages.extend(self.conversation_history)
        
#         return messages
    
#     def clear_history(self):
#         """Clear conversation history"""
#         count = len(self.conversation_history)
#         self.conversation_history = []
#         return count
    
#     def get_history_length(self) -> int:
#         """Get number of messages in history"""
#         return len(self.conversation_history)


"""
Azure OpenAI Client with MCP Integration - Gradio 6.0 Compatible
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Client for Azure OpenAI with MCP tool integration"""
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self.conversation_history = []
        self.max_history = int(os.getenv("MAX_HISTORY", "50"))
    
    async def _get_mcp_tools(self, mcp_client) -> List[Dict]:
        """Get tools from all MCP servers"""
        functions = []
        
        for server_name in mcp_client.get_all_servers():
            try:
                tools = await mcp_client.list_tools(server_name)
                
                for tool in tools:
                    # Create function definition
                    function = {
                        "type": "function",
                        "function": {
                            "name": f"{server_name}_{tool['name']}",
                            "description": f"{tool.get('description', tool['name'])}",
                            "parameters": tool.get('inputSchema', {
                                "type": "object",
                                "properties": {},
                                "required": []
                            })
                        }
                    }
                    functions.append(function)
                    logger.info(f"Added tool: {function['function']['name']}")
            except Exception as e:
                logger.error(f"Error getting tools from {server_name}: {e}")
        
        return functions
    
    async def chat(
        self,
        message: str,
        mcp_client=None,
        use_tools: bool = True,
        max_completion_tokens: int = 2000
    ) -> str:
        """Send message and get response with optional MCP tool usage"""
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Prepare messages
        messages = self._prepare_messages()
        
        # Get tools if available
        tools = None
        if use_tools and mcp_client and mcp_client.get_all_servers():
            tools = await self._get_mcp_tools(mcp_client)
            logger.info(f"Available tools: {len(tools)}")
        
        try:
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )
            
            assistant_message = response.choices[0].message
            
            # Check if tool was called
            if assistant_message.tool_calls:
                logger.info(f"🔧 AI is calling {len(assistant_message.tool_calls)} tool(s)")
                return await self._handle_tool_calls(
                    assistant_message,
                    mcp_client,
                    max_completion_tokens
                )
            else:
                # Regular response
                logger.info("💬 AI responded without tools")
                response_text = assistant_message.content
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                return response_text
                
        except Exception as e:
            error_msg = f"Error calling Azure OpenAI: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return error_msg
    
    async def _handle_tool_calls(
        self,
        assistant_message,
        mcp_client,
        max_completion_tokens
    ) -> str:
        """Handle MCP tool calls from AI"""
        
        # Add assistant message with tool calls
        tool_calls_formatted = []
        for tc in assistant_message.tool_calls:
            tool_calls_formatted.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })
        
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": tool_calls_formatted
        })
        
        # Execute each tool call via MCP
        tool_results = []
        for tool_call in assistant_message.tool_calls:
            function_name = tool_call.function.name
            
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse arguments: {tool_call.function.arguments}")
                result = f"Error: Invalid JSON arguments"
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": result
                })
                continue
            
            # Parse server_name and tool_name
            # Format: "servername_toolname"
            if "_" in function_name:
                parts = function_name.split("_", 1)
                server_name = parts[0]
                tool_name = parts[1]
                
                logger.info(f"🔧 Calling {server_name}.{tool_name} with args: {function_args}")
                
                try:
                    # Call MCP tool
                    result = await mcp_client.call_tool(
                        server_name,
                        tool_name,
                        function_args
                    )
                    logger.info(f"✅ Tool result: {result[:100]}...")
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
                    logger.error(f"❌ Tool error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                result = f"Error: Invalid function name format: {function_name}"
                logger.error(result)
            
            # Add tool result to conversation
            tool_results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result
            })
        
        # Add all tool results to history
        self.conversation_history.extend(tool_results)
        
        # Get final response from AI
        messages = self._prepare_messages()
        
        final_response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            max_completion_tokens=max_completion_tokens
        )
        
        final_text = final_response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": final_text
        })
        
        return final_text
    
    def _prepare_messages(self) -> List[Dict]:
        """Prepare messages for API call"""
        # Enhanced system message that encourages tool use
        system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant with access to tools for file operations, calculations, and weather information.

IMPORTANT: When users ask you to:

FILE OPERATIONS:
- "list files", "show files", "what files" → USE the filesystem_list_files tool
- "read file", "show file contents", "open file" → USE the filesystem_read_file tool  
- "search files", "find in files" → USE the filesystem_search_files tool

CALCULATIONS:
- "add", "sum", "calculate sum" → USE the calculator_add tool
- "subtract", "minus" → USE the calculator_subtract tool
- "multiply", "times" → USE the calculator_multiply tool
- "divide" → USE the calculator_divide tool
- "factorial" → USE the calculator_factorial tool

CONVERSIONS:
- "convert temperature" → USE the calculator_convert_temperature tool
- "convert distance" → USE the calculator_convert_distance tool

WEATHER:
- "weather", "what's the weather", "temperature" → USE the weather_get_current_weather tool
- "forecast", "weather forecast" → USE the weather_get_forecast tool
- "compare weather", "weather difference" → USE the weather_compare_weather tool
- "list cities", "which cities", "available cities" → USE the weather_list_cities tool

DEADLINE TRACKER:
- "what's due", "what do I have due", "upcoming deadlines", "what's due this week", "any deadlines soon", "show my assignments" → USE the deadline_get_upcoming_deadlines tool
- "show all deadlines", "list all my deadlines", "all assignments" → USE the deadline_get_all_deadlines tool
- "I finished", "mark as done", "I submitted", "I completed" → USE the deadline_mark_done tool
- "add a deadline", "add assignment", "remind me about", "track this deadline" → USE the deadline_add_deadline tool

ALWAYS use the appropriate tool when the user's request matches these patterns. Do not just describe what you would do - actually call the tool.

When you use a tool, interpret the results and present them in a friendly, conversational way."""
        }
        
        messages = [system_message]
        
        # Add conversation history (limit to max_history)
        if len(self.conversation_history) > self.max_history:
            messages.extend(self.conversation_history[-self.max_history:])
        else:
            messages.extend(self.conversation_history)
        
        return messages
    
    def clear_history(self):
        """Clear conversation history"""
        count = len(self.conversation_history)
        self.conversation_history = []
        return count
    
    def get_history_length(self) -> int:
        """Get number of messages in history"""
        return len(self.conversation_history)