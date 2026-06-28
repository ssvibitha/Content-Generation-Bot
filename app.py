# # """
# # AI Chatbot with MCP Protocol
# # A Gradio-based chatbot using Azure OpenAI and real MCP servers
# # """
# # import gradio as gr
# # import asyncio
# # import os
# # import sys
# # from pathlib import Path
# # from dotenv import load_dotenv

# # # Add src to path
# # project_root = Path(__file__).parent
# # sys.path.insert(0, str(project_root / "src"))

# # # Import after path setup
# # from mcp_client.client import MCPClient
# # from ai_client import AzureOpenAIClient

# # # Load environment
# # load_dotenv()

# # # Initialize clients
# # ai_client = AzureOpenAIClient()
# # mcp_client = MCPClient()

# # # Track initialization
# # mcp_initialized = False

# # # Custom CSS
# # custom_css = """
# # .gradio-container {
# #     font-family: 'Inter', sans-serif;
# # }
# # .server-status {
# #     padding: 10px;
# #     border-radius: 5px;
# #     margin: 5px 0;
# # }
# # .server-running {
# #     background-color: #10b981;
# #     color: white;
# # }
# # .server-stopped {
# #     background-color: #ef4444;
# #     color: white;
# # }
# # """


# # async def initialize_mcp_servers():
# #     """Initialize MCP servers on startup"""
# #     global mcp_initialized
    
# #     if mcp_initialized:
# #         return "Servers already initialized"
    
# #     print("Initializing MCP servers...")
    
# #     # Start file system server
# #     fs_success = await mcp_client.start_server(
# #         "filesystem",
# #         "src/mcp_servers/fs_server.py"
# #     )
    
# #     # Start calculator server
# #     calc_success = await mcp_client.start_server(
# #         "calculator",
# #         "src/mcp_servers/calc_server.py"
# #     )
    
# #     if fs_success and calc_success:
# #         mcp_initialized = True
# #         return "✅ All MCP servers initialized"
# #     elif fs_success or calc_success:
# #         mcp_initialized = True
# #         return "⚠️ Some servers initialized"
# #     else:
# #         return "❌ Failed to initialize servers"


# # async def process_message(message: str, history: list, use_tools: bool, temperature: float):
# #     """Process user message and get AI response"""
    
# #     if not message.strip():
# #         return history, ""
    
# #     # Initialize history if None
# #     if history is None:
# #         history = []
    
# #     try:
# #         # Get AI response with MCP tools
# #         response = await ai_client.chat(
# #             message=message,
# #             mcp_client=mcp_client if use_tools else None,
# #             use_tools=use_tools,
# #             temperature=temperature
# #         )
        
# #         # Gradio 6.0 expects messages format: list of dicts with 'role' and 'content'
# #         history.append({"role": "user", "content": message})
# #         history.append({"role": "assistant", "content": response})
    
# #     except Exception as e:
# #         import traceback
# #         error_details = traceback.format_exc()
# #         print(f"Error processing message: {error_details}")
        
# #         error_msg = f"❌ Error: {str(e)}\n\nPlease check that:\n1. Azure OpenAI credentials are configured\n2. MCP servers are running\n3. Network connection is available"
        
# #         history.append({"role": "user", "content": message})
# #         history.append({"role": "assistant", "content": error_msg})
    
# #     return history, ""


# # def clear_conversation():
# #     """Clear conversation history"""
# #     count = ai_client.clear_history()
# #     return [], f"Cleared {count} messages from history"


# # def get_stats():
# #     """Get chatbot statistics"""
# #     history_length = ai_client.get_history_length()
# #     servers = mcp_client.get_all_servers()
    
# #     server_status = "\n".join([f"  • {s} (running)" for s in servers]) if servers else "  No servers running"
    
# #     return f"""### 📊 Statistics
# # - **Messages in history:** {history_length}
# # - **MCP Servers:** {len(servers)}

# # **Active Servers:**
# # {server_status}

# # **Status:** {'✅ Ready' if servers else '⚠️ No tools available'}
# # """


# # def get_available_tools():
# #     """Get list of available MCP tools"""
# #     import asyncio
    
# #     servers = mcp_client.get_all_servers()
# #     if not servers:
# #         return "### 🛠️ Available Tools\n\n⚠️ No MCP servers running"
    
# #     tools_text = "### 🛠️ Available Tools\n\n"
    
# #     for server_name in servers:
# #         try:
# #             tools = asyncio.run(mcp_client.list_tools(server_name))
# #             tools_text += f"**{server_name.upper()}:**\n"
# #             for tool in tools:
# #                 tools_text += f"- `{tool['name']}`: {tool.get('description', 'No description')}\n"
# #             tools_text += "\n"
# #         except Exception as e:
# #             tools_text += f"**{server_name}:** Error loading tools - {str(e)}\n\n"
    
# #     tools_text += """
# # **Usage Examples:**
# # - "List all files in the directory"
# # - "Read test1.txt"
# # - "Calculate 25 + 75 + 100"
# # - "What's the factorial of 8?"
# # - "Convert 100°F to Celsius"
# # - "Convert 5 miles to kilometers"
# # """
    
# #     return tools_text


# # # Create Gradio Interface - Gradio 6.0 compatible
# # app = gr.Blocks(title="MCP Protocol Chatbot")

# # with app:
# #     gr.Markdown("""
# #     # 🤖 AI Chatbot with MCP Protocol
    
# #     A production-ready chatbot using Azure OpenAI and real MCP servers for tool execution.
# #     """)
    
# #     with gr.Row():
# #         with gr.Column(scale=3):
# #             # Gradio 6.0: Chatbot expects messages format by default
# #             chatbot = gr.Chatbot(
# #                 label="Conversation",
# #                 height=500,
# #                 show_label=True
# #             )
            
# #             with gr.Row():
# #                 msg = gr.Textbox(
# #                     placeholder="Type your message here...",
# #                     show_label=False,
# #                     scale=4,
# #                     container=False
# #                 )
# #                 submit_btn = gr.Button("Send 🚀", scale=1, variant="primary")
            
# #             with gr.Row():
# #                 clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
# #                 use_tools_cb = gr.Checkbox(
# #                     label="Enable MCP Tools",
# #                     value=True,
# #                     info="Allow AI to use MCP servers"
# #                 )
# #                 temperature_slider = gr.Slider(
# #                     minimum=0.0,
# #                     maximum=2.0,
# #                     value=0.7,
# #                     step=0.1,
# #                     label="Temperature",
# #                     info="Higher = more creative"
# #                 )
        
# #         with gr.Column(scale=1):
# #             gr.Markdown("## ⚙️ Control Panel")
            
# #             stats_display = gr.Markdown(get_stats())
# #             refresh_stats_btn = gr.Button("🔄 Refresh Stats", size="sm")
            
# #             gr.Markdown("---")
            
# #             with gr.Accordion("📖 Available Tools", open=False):
# #                 tools_display = gr.Markdown(get_available_tools())
            
# #             with gr.Accordion("💡 Quick Examples", open=False):
# #                 gr.Markdown("""
# #                 **File Operations (MCP):**
# #                 - List all files
# #                 - Read test1.txt
# #                 - Search for "MCP" in files
                
# #                 **Calculations (MCP):**
# #                 - Add 10, 20, and 30
# #                 - Calculate factorial of 8
# #                 - What's 144 divided by 12?
                
# #                 **Conversions (MCP):**
# #                 - Convert 32°F to Celsius
# #                 - Convert 1 mile to meters
                
# #                 **General:**
# #                 - Explain quantum computing
# #                 - Write Python code to sort a list
# #                 """)
            
# #             gr.Markdown("---")
            
# #             status_text = gr.Textbox(
# #                 label="Status",
# #                 value="Initializing...",
# #                 interactive=False
# #             )
    
# #     # Event handlers
# #     def submit_message(message, history, use_tools, temperature):
# #         return asyncio.run(
# #             process_message(message, history, use_tools, temperature)
# #         )
    
# #     submit_btn.click(
# #         fn=submit_message,
# #         inputs=[msg, chatbot, use_tools_cb, temperature_slider],
# #         outputs=[chatbot, msg]
# #     )
    
# #     msg.submit(
# #         fn=submit_message,
# #         inputs=[msg, chatbot, use_tools_cb, temperature_slider],
# #         outputs=[chatbot, msg]
# #     )
    
# #     clear_btn.click(
# #         fn=clear_conversation,
# #         outputs=[chatbot, status_text]
# #     )
    
# #     refresh_stats_btn.click(
# #         fn=get_stats,
# #         outputs=stats_display
# #     )
    
# #     gr.Markdown("""
# #     ---
# #     ### 🔒 Privacy & Security
# #     - All conversations processed through Azure OpenAI
# #     - MCP servers run in isolated processes
# #     - File access restricted to designated directory
# #     - No data stored permanently
    
# #     ### 📚 Documentation
# #     Built with Gradio, Azure OpenAI, and Model Context Protocol (MCP)
    
# #     **Architecture:** Real MCP protocol with stdio communication
# #     """)


# # if __name__ == "__main__":
# #     # Initialize MCP servers
# #     print("Starting AI Chatbot with MCP Protocol...")
# #     try:
# #         init_result = asyncio.run(initialize_mcp_servers())
# #         print(init_result)
# #     except Exception as e:
# #         print(f"⚠️ Warning: MCP initialization failed - {e}")
# #         print("App will start but tools may not be available")
    
# #     # Launch Gradio - CSS moved to launch() for Gradio 6.0
# #     app.launch(
# #         server_name="0.0.0.0",
# #         server_port=int(os.getenv("APP_PORT", "7860")),
# #         share=False,
# #         show_error=True
# #     )


# """
# AI Chatbot with MCP Protocol
# A Gradio-based chatbot using Azure OpenAI and real MCP servers
# """
# import gradio as gr
# import asyncio
# import os
# import sys
# from pathlib import Path
# from dotenv import load_dotenv

# # Add src to path
# project_root = Path(__file__).parent
# sys.path.insert(0, str(project_root / "src"))

# # Import after path setup
# from mcp_client.client import MCPClient
# from ai_client import AzureOpenAIClient

# # Load environment
# load_dotenv()

# # Initialize clients
# ai_client = AzureOpenAIClient()
# mcp_client = MCPClient()

# # Track initialization
# mcp_initialized = False

# # Custom CSS
# custom_css = """
# .gradio-container {
#     font-family: 'Inter', sans-serif;
# }
# .server-status {
#     padding: 10px;
#     border-radius: 5px;
#     margin: 5px 0;
# }
# .server-running {
#     background-color: #10b981;
#     color: white;
# }
# .server-stopped {
#     background-color: #ef4444;
#     color: white;
# }
# """


# async def initialize_mcp_servers():
#     """Initialize MCP servers on startup"""
#     global mcp_initialized
    
#     if mcp_initialized:
#         return "Servers already initialized"
    
#     print("Initializing MCP servers...")
    
#     # Start file system server
#     fs_success = await mcp_client.start_server(
#         "filesystem",
#         "src/mcp_servers/fs_server.py"
#     )
    
#     # Start calculator server
#     calc_success = await mcp_client.start_server(
#         "calculator",
#         "src/mcp_servers/calc_server.py"
#     )
    
#     if fs_success and calc_success:
#         mcp_initialized = True
#         return "✅ All MCP servers initialized"
#     elif fs_success or calc_success:
#         mcp_initialized = True
#         return "⚠️ Some servers initialized"
#     else:
#         return "❌ Failed to initialize servers"


# async def process_message(message: str, history: list, use_tools: bool, temperature: float):
#     """Process user message and get AI response"""
    
#     if not message.strip():
#         return history, ""
    
#     # Initialize history if None
#     if history is None:
#         history = []
    
#     try:
#         # Get AI response with MCP tools
#         response = await ai_client.chat(
#             message=message,
#             mcp_client=mcp_client if use_tools else None,
#             use_tools=use_tools,
#             temperature=temperature
#         )
        
#         # Gradio 6.0 expects messages format: list of dicts with 'role' and 'content'
#         history.append({"role": "user", "content": message})
#         history.append({"role": "assistant", "content": response})
    
#     except Exception as e:
#         import traceback
#         error_details = traceback.format_exc()
#         print(f"Error processing message: {error_details}")
        
#         error_msg = f"❌ Error: {str(e)}\n\nPlease check that:\n1. Azure OpenAI credentials are configured\n2. MCP servers are running\n3. Network connection is available"
        
#         history.append({"role": "user", "content": message})
#         history.append({"role": "assistant", "content": error_msg})
    
#     return history, ""


# def clear_conversation():
#     """Clear conversation history"""
#     count = ai_client.clear_history()
#     return [], f"Cleared {count} messages from history"


# def get_stats():
#     """Get chatbot statistics"""
#     history_length = ai_client.get_history_length()
#     servers = mcp_client.get_all_servers()
    
#     server_status = "\n".join([f"  • {s} (running)" for s in servers]) if servers else "  No servers running"
    
#     return f"""### 📊 Statistics
# - **Messages in history:** {history_length}
# - **MCP Servers:** {len(servers)}

# **Active Servers:**
# {server_status}

# **Status:** {'✅ Ready' if servers else '⚠️ No tools available'}
# """


# def get_available_tools():
#     """Get list of available MCP tools - runs on button click"""
#     servers = mcp_client.get_all_servers()
    
#     if not servers:
#         return "### 🛠️ Available Tools\n\n⚠️ No MCP servers running\n\nPlease wait for initialization or restart the app."
    
#     tools_text = "### 🛠️ Available Tools\n\n"
    
#     for server_name in servers:
#         try:
#             # Use the synchronous run to get tools
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#             tools = loop.run_until_complete(mcp_client.list_tools(server_name))
#             loop.close()
            
#             tools_text += f"**{server_name.upper()}:**\n"
#             for tool in tools:
#                 tools_text += f"- `{tool['name']}`: {tool.get('description', 'No description')}\n"
#             tools_text += "\n"
#         except Exception as e:
#             tools_text += f"**{server_name}:** Error loading tools - {str(e)}\n\n"
    
#     tools_text += """
# **Usage Examples:**
# - "List all files in the directory"
# - "Read test1.txt"
# - "Calculate 25 + 75 + 100"
# - "What's the factorial of 8?"
# - "Convert 100°F to Celsius"
# - "Convert 5 miles to kilometers"
# """
    
#     return tools_text


# # Create Gradio Interface - Gradio 6.0 compatible
# app = gr.Blocks(title="MCP Protocol Chatbot")

# with app:
#     gr.Markdown("""
#     # 🤖 AI Chatbot with MCP Protocol
    
#     A production-ready chatbot using Azure OpenAI and real MCP servers for tool execution.
#     """)
    
#     with gr.Row():
#         with gr.Column(scale=3):
#             # Gradio 6.0: Chatbot expects messages format by default
#             chatbot = gr.Chatbot(
#                 label="Conversation",
#                 height=500,
#                 show_label=True
#             )
            
#             with gr.Row():
#                 msg = gr.Textbox(
#                     placeholder="Type your message here...",
#                     show_label=False,
#                     scale=4,
#                     container=False
#                 )
#                 submit_btn = gr.Button("Send 🚀", scale=1, variant="primary")
            
#             with gr.Row():
#                 clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
#                 use_tools_cb = gr.Checkbox(
#                     label="Enable MCP Tools",
#                     value=True,
#                     info="Allow AI to use MCP servers"
#                 )
#                 temperature_slider = gr.Slider(
#                     minimum=0.0,
#                     maximum=2.0,
#                     value=0.7,
#                     step=0.1,
#                     label="Temperature",
#                     info="Higher = more creative"
#                 )
        
#         with gr.Column(scale=1):
#             gr.Markdown("## ⚙️ Control Panel")
            
#             stats_display = gr.Markdown(get_stats())
#             refresh_stats_btn = gr.Button("🔄 Refresh Stats", size="sm")
            
#             gr.Markdown("---")
            
#             with gr.Accordion("📖 Available Tools", open=False):
#                 tools_display = gr.Markdown("Loading tools...")
#                 refresh_tools_btn = gr.Button("🔄 Refresh Tools", size="sm")
            
#             with gr.Accordion("💡 Quick Examples", open=False):
#                 gr.Markdown("""
#                 **File Operations (MCP):**
#                 - List all files
#                 - Read test1.txt
#                 - Search for "MCP" in files
                
#                 **Calculations (MCP):**
#                 - Add 10, 20, and 30
#                 - Calculate factorial of 8
#                 - What's 144 divided by 12?
                
#                 **Conversions (MCP):**
#                 - Convert 32°F to Celsius
#                 - Convert 1 mile to meters
                
#                 **General:**
#                 - Explain quantum computing
#                 - Write Python code to sort a list
#                 """)
            
#             gr.Markdown("---")
            
#             status_text = gr.Textbox(
#                 label="Status",
#                 value="Initializing...",
#                 interactive=False
#             )
    
#     # Event handlers
#     def submit_message(message, history, use_tools, temperature):
#         return asyncio.run(
#             process_message(message, history, use_tools, temperature)
#         )
    
#     submit_btn.click(
#         fn=submit_message,
#         inputs=[msg, chatbot, use_tools_cb, temperature_slider],
#         outputs=[chatbot, msg]
#     )
    
#     msg.submit(
#         fn=submit_message,
#         inputs=[msg, chatbot, use_tools_cb, temperature_slider],
#         outputs=[chatbot, msg]
#     )
    
#     clear_btn.click(
#         fn=clear_conversation,
#         outputs=[chatbot, status_text]
#     )
    
#     refresh_stats_btn.click(
#         fn=get_stats,
#         outputs=stats_display
#     )
    
#     refresh_tools_btn.click(
#         fn=get_available_tools,
#         outputs=tools_display
#     )
    
#     # Auto-refresh tools on app load
#     app.load(
#         fn=get_available_tools,
#         outputs=tools_display
#     )
    
#     # Auto-refresh stats on app load
#     app.load(
#         fn=get_stats,
#         outputs=stats_display
#     )
    
#     gr.Markdown("""
#     ---
#     ### 🔒 Privacy & Security
#     - All conversations processed through Azure OpenAI
#     - MCP servers run in isolated processes
#     - File access restricted to designated directory
#     - No data stored permanently
    
#     ### 📚 Documentation
#     Built with Gradio, Azure OpenAI, and Model Context Protocol (MCP)
    
#     **Architecture:** Real MCP protocol with stdio communication
#     """)


# if __name__ == "__main__":
#     # Initialize MCP servers
#     print("Starting AI Chatbot with MCP Protocol...")
#     print("="*60)
    
#     try:
#         init_result = asyncio.run(initialize_mcp_servers())
#         print(init_result)
#         print("="*60)
#     except Exception as e:
#         print(f"⚠️ Warning: MCP initialization failed - {e}")
#         print("App will start but tools may not be available")
#         import traceback
#         traceback.print_exc()
    
#     # Debug: Show what servers are running
#     servers = mcp_client.get_all_servers()
#     print(f"\n✅ Active MCP Servers: {servers}")
#     print(f"✅ MCP Initialized: {mcp_initialized}")
#     print("="*60 + "\n")
    
#     # Launch Gradio - CSS moved to launch() for Gradio 6.0
#     app.launch(
#         server_name="0.0.0.0",
#         server_port=int(os.getenv("APP_PORT", "7860")),
#         share=False,
#         show_error=True
#     )

# #############################################################################
# """
# AI Chatbot with MCP Protocol
# A Gradio-based chatbot using Azure OpenAI and real MCP servers
# """
# import gradio as gr
# import asyncio
# import os
# import sys
# from pathlib import Path
# from dotenv import load_dotenv

# # Add src to path
# project_root = Path(__file__).parent
# sys.path.insert(0, str(project_root / "src"))

# # Import after path setup
# from mcp_client.client import MCPClient
# from ai_client import AzureOpenAIClient

# # Load environment
# load_dotenv()

# # Initialize clients
# ai_client = AzureOpenAIClient()
# mcp_client = MCPClient()

# # Track initialization
# mcp_initialized = False

# # Custom CSS
# custom_css = """
# .gradio-container {
#     font-family: 'Inter', sans-serif;
# }
# .server-status {
#     padding: 10px;
#     border-radius: 5px;
#     margin: 5px 0;
# }
# .server-running {
#     background-color: #10b981;
#     color: white;
# }
# .server-stopped {
#     background-color: #ef4444;
#     color: white;
# }
# """


# async def initialize_mcp_servers():
#     """Initialize MCP servers on startup"""
#     global mcp_initialized
    
#     if mcp_initialized:
#         return "Servers already initialized"
    
#     print("Initializing MCP servers...")
    
#     # Start file system server
#     fs_success = await mcp_client.start_server(
#         "filesystem",
#         "src/mcp_servers/fs_server.py"
#     )
    
#     # Start calculator server
#     calc_success = await mcp_client.start_server(
#         "calculator",
#         "src/mcp_servers/calc_server.py"
#     )
    
#     # Start weather server
#     weather_success = await mcp_client.start_server(
#         "weather",
#         "src/mcp_servers/weather_server.py"
#     )
    
#     success_count = sum([fs_success, calc_success, weather_success])
    
#     if success_count == 3:
#         mcp_initialized = True
#         return "✅ All MCP servers initialized (3/3)"
#     elif success_count > 0:
#         mcp_initialized = True
#         return f"⚠️ Some servers initialized ({success_count}/3)"
#     else:
#         return "❌ Failed to initialize servers"


# async def process_message(message: str, history: list, use_tools: bool, temperature: float):
#     """Process user message and get AI response"""
    
#     if not message.strip():
#         return history, ""
    
#     # Initialize history if None
#     if history is None:
#         history = []
    
#     try:
#         # Get AI response with MCP tools
#         response = await ai_client.chat(
#             message=message,
#             mcp_client=mcp_client if use_tools else None,
#             use_tools=use_tools,
#             temperature=temperature
#         )
        
#         # Gradio 6.0 expects messages format: list of dicts with 'role' and 'content'
#         history.append({"role": "user", "content": message})
#         history.append({"role": "assistant", "content": response})
    
#     except Exception as e:
#         import traceback
#         error_details = traceback.format_exc()
#         print(f"Error processing message: {error_details}")
        
#         error_msg = f"❌ Error: {str(e)}\n\nPlease check that:\n1. Azure OpenAI credentials are configured\n2. MCP servers are running\n3. Network connection is available"
        
#         history.append({"role": "user", "content": message})
#         history.append({"role": "assistant", "content": error_msg})
    
#     return history, ""


# def clear_conversation():
#     """Clear conversation history"""
#     count = ai_client.clear_history()
#     return [], f"Cleared {count} messages from history"


# def get_stats():
#     """Get chatbot statistics"""
#     history_length = ai_client.get_history_length()
#     servers = mcp_client.get_all_servers()
    
#     server_status = "\n".join([f"  • {s} (running)" for s in servers]) if servers else "  No servers running"
    
#     return f"""### 📊 Statistics
# - **Messages in history:** {history_length}
# - **MCP Servers:** {len(servers)}

# **Active Servers:**
# {server_status}

# **Status:** {'✅ Ready' if servers else '⚠️ No tools available'}
# """


# def get_available_tools():
#     """Get list of available MCP tools - runs on button click"""
#     servers = mcp_client.get_all_servers()
    
#     if not servers:
#         return "### 🛠️ Available Tools\n\n⚠️ No MCP servers running\n\nPlease wait for initialization or restart the app."
    
#     tools_text = "### 🛠️ Available Tools\n\n"
    
#     for server_name in servers:
#         try:
#             # Use the synchronous run to get tools
#             loop = asyncio.new_event_loop()
#             asyncio.set_event_loop(loop)
#             tools = loop.run_until_complete(mcp_client.list_tools(server_name))
#             loop.close()
            
#             tools_text += f"**{server_name.upper()}:**\n"
#             for tool in tools:
#                 tools_text += f"- `{tool['name']}`: {tool.get('description', 'No description')}\n"
#             tools_text += "\n"
#         except Exception as e:
#             tools_text += f"**{server_name}:** Error loading tools - {str(e)}\n\n"
    
#     tools_text += """
# **Usage Examples:**
# - "List all files in the directory"
# - "Read test1.txt"
# - "Calculate 25 + 75 + 100"
# - "What's the factorial of 8?"
# - "Convert 100°F to Celsius"
# - "Convert 5 miles to kilometers"
# """
    
#     return tools_text


# # Create Gradio Interface - Gradio 6.0 compatible
# app = gr.Blocks(title="MCP Protocol Chatbot")

# with app:
#     gr.Markdown("""
#     # 🤖 AI Chatbot with MCP Protocol
    
#     A production-ready chatbot using Azure OpenAI and real MCP servers for tool execution.
#     """)
    
#     with gr.Row():
#         with gr.Column(scale=3):
#             # Gradio 6.0: Chatbot expects messages format by default
#             chatbot = gr.Chatbot(
#                 label="Conversation",
#                 height=500,
#                 show_label=True
#             )
            
#             with gr.Row():
#                 msg = gr.Textbox(
#                     placeholder="Type your message here...",
#                     show_label=False,
#                     scale=4,
#                     container=False
#                 )
#                 submit_btn = gr.Button("Send 🚀", scale=1, variant="primary")
            
#             with gr.Row():
#                 clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
#                 use_tools_cb = gr.Checkbox(
#                     label="Enable MCP Tools",
#                     value=True,
#                     info="Allow AI to use MCP servers"
#                 )
#                 temperature_slider = gr.Slider(
#                     minimum=0.0,
#                     maximum=2.0,
#                     value=0.7,
#                     step=0.1,
#                     label="Temperature",
#                     info="Higher = more creative"
#                 )
        
#         with gr.Column(scale=1):
#             gr.Markdown("## ⚙️ Control Panel")
            
#             stats_display = gr.Markdown(get_stats())
#             refresh_stats_btn = gr.Button("🔄 Refresh Stats", size="sm")
            
#             gr.Markdown("---")
            
#             with gr.Accordion("📖 Available Tools", open=False):
#                 tools_display = gr.Markdown("Loading tools...")
#                 refresh_tools_btn = gr.Button("🔄 Refresh Tools", size="sm")
            
#             with gr.Accordion("💡 Quick Examples", open=False):
#                 gr.Markdown("""
#                 **File Operations (MCP):**
#                 - List all files
#                 - Read test1.txt
#                 - Search for "MCP" in files
                
#                 **Calculations (MCP):**
#                 - Add 10, 20, and 30
#                 - Calculate factorial of 8
#                 - What's 144 divided by 12?
                
#                 **Conversions (MCP):**
#                 - Convert 32°F to Celsius
#                 - Convert 1 mile to meters
                
#                 **General:**
#                 - Explain quantum computing
#                 - Write Python code to sort a list
#                 """)
            
#             gr.Markdown("---")
            
#             status_text = gr.Textbox(
#                 label="Status",
#                 value="Initializing...",
#                 interactive=False
#             )
    
#     # Event handlers
#     def submit_message(message, history, use_tools, temperature):
#         return asyncio.run(
#             process_message(message, history, use_tools, temperature)
#         )
    
#     submit_btn.click(
#         fn=submit_message,
#         inputs=[msg, chatbot, use_tools_cb, temperature_slider],
#         outputs=[chatbot, msg]
#     )
    
#     msg.submit(
#         fn=submit_message,
#         inputs=[msg, chatbot, use_tools_cb, temperature_slider],
#         outputs=[chatbot, msg]
#     )
    
#     clear_btn.click(
#         fn=clear_conversation,
#         outputs=[chatbot, status_text]
#     )
    
#     refresh_stats_btn.click(
#         fn=get_stats,
#         outputs=stats_display
#     )
    
#     refresh_tools_btn.click(
#         fn=get_available_tools,
#         outputs=tools_display
#     )
    
#     # Auto-refresh tools on app load
#     app.load(
#         fn=get_available_tools,
#         outputs=tools_display
#     )
    
#     # Auto-refresh stats on app load
#     app.load(
#         fn=get_stats,
#         outputs=stats_display
#     )
    
#     gr.Markdown("""
#     ---
#     ### 🔒 Privacy & Security
#     - All conversations processed through Azure OpenAI
#     - MCP servers run in isolated processes
#     - File access restricted to designated directory
#     - No data stored permanently
    
#     ### 📚 Documentation
#     Built with Gradio, Azure OpenAI, and Model Context Protocol (MCP)
    
#     **Architecture:** Real MCP protocol with stdio communication
#     """)


# if __name__ == "__main__":
#     # Initialize MCP servers
#     print("Starting AI Chatbot with MCP Protocol...")
#     print("="*60)
    
#     try:
#         init_result = asyncio.run(initialize_mcp_servers())
#         print(init_result)
#         print("="*60)
#     except Exception as e:
#         print(f"⚠️ Warning: MCP initialization failed - {e}")
#         print("App will start but tools may not be available")
#         import traceback
#         traceback.print_exc()
    
#     # Debug: Show what servers are running
#     servers = mcp_client.get_all_servers()
#     print(f"\n✅ Active MCP Servers: {servers}")
#     print(f"✅ MCP Initialized: {mcp_initialized}")
#     print("="*60 + "\n")
    
#     # Launch Gradio - CSS moved to launch() for Gradio 6.0
#     app.launch(
#         server_name="0.0.0.0",
#         server_port=int(os.getenv("APP_PORT", "7860")),
#         share=False,
#         show_error=True
#     )


# ###################################################################


"""
AI Chatbot with MCP Protocol
A Gradio-based chatbot using Azure OpenAI and real MCP servers
"""
import gradio as gr
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Import after path setup
from mcp_client.client import MCPClient
from ai_client import AzureOpenAIClient

# Load environment
load_dotenv()

# Initialize clients
ai_client = AzureOpenAIClient()
mcp_client = MCPClient()

# Track initialization
mcp_initialized = False

# Custom CSS
custom_css = """
.gradio-container {
    font-family: 'Inter', sans-serif;
}
.server-status {
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}
.server-running {
    background-color: #10b981;
    color: white;
}
.server-stopped {
    background-color: #ef4444;
    color: white;
}
"""


async def initialize_mcp_servers():
    """Initialize MCP servers on startup"""
    global mcp_initialized
    
    if mcp_initialized:
        return "Servers already initialized"
    
    print("Initializing MCP servers...")
    
    # Start file system server
    fs_success = await mcp_client.start_server(
        "filesystem",
        "src/mcp_servers/fs_server.py"
    )
    
    # Start calculator server
    calc_success = await mcp_client.start_server(
        "calculator",
        "src/mcp_servers/calc_server.py"
    )
    
    # Start weather server
    weather_success = await mcp_client.start_server(
        "weather",
        "src/mcp_servers/weather_server.py"
    )
    
    success_count = sum([fs_success, calc_success, weather_success])
    
    if success_count == 3:
        mcp_initialized = True
        return "✅ All MCP servers initialized (3/3)"
    elif success_count > 0:
        mcp_initialized = True
        return f"⚠️ Some servers initialized ({success_count}/3)"
    else:
        return "❌ Failed to initialize servers"


async def process_message(message: str, history: list, use_tools: bool, temperature: float):
    """Process user message and get AI response"""
    
    if not message.strip():
        return history, ""
    
    # Initialize history if None
    if history is None:
        history = []
    
    try:
        # Get AI response with MCP tools
        response = await ai_client.chat(
            message=message,
            mcp_client=mcp_client if use_tools else None,
            use_tools=use_tools,
            temperature=temperature
        )
        
        # Gradio 6.0 expects messages format: list of dicts with 'role' and 'content'
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error processing message: {error_details}")
        
        error_msg = f"❌ Error: {str(e)}\n\nPlease check that:\n1. Azure OpenAI credentials are configured\n2. MCP servers are running\n3. Network connection is available"
        
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
    
    return history, ""


def clear_conversation():
    """Clear conversation history"""
    count = ai_client.clear_history()
    return [], f"Cleared {count} messages from history"


def get_stats():
    """Get chatbot statistics"""
    history_length = ai_client.get_history_length()
    servers = mcp_client.get_all_servers()
    
    server_status = "\n".join([f"  • {s} (running)" for s in servers]) if servers else "  No servers running"
    
    return f"""### 📊 Statistics
- **Messages in history:** {history_length}
- **MCP Servers:** {len(servers)}

**Active Servers:**
{server_status}

**Status:** {'✅ Ready' if servers else '⚠️ No tools available'}
"""


def get_available_tools():
    """Get list of available MCP tools - runs on button click"""
    servers = mcp_client.get_all_servers()
    
    if not servers:
        return "### 🛠️ Available Tools\n\n⚠️ No MCP servers running\n\nPlease wait for initialization or restart the app."
    
    tools_text = "### 🛠️ Available Tools\n\n"
    
    for server_name in servers:
        try:
            # Use the synchronous run to get tools
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tools = loop.run_until_complete(mcp_client.list_tools(server_name))
            loop.close()
            
            tools_text += f"**{server_name.upper()}:**\n"
            for tool in tools:
                tools_text += f"- `{tool['name']}`: {tool.get('description', 'No description')}\n"
            tools_text += "\n"
        except Exception as e:
            tools_text += f"**{server_name}:** Error loading tools - {str(e)}\n\n"
    
    tools_text += """
**Usage Examples:**

📁 **Files:**
- "List all files in the directory"
- "Read test1.txt"
- "Search for 'MCP' in files"

🔢 **Math:**
- "Calculate 25 + 75 + 100"
- "What's the factorial of 8?"
- "Divide 144 by 12"

🌡️ **Conversions:**
- "Convert 100°F to Celsius"
- "Convert 5 miles to kilometers"

🌤️ **Weather:**
- "What's the weather in London?"
- "Show forecast for Tokyo"
- "Compare Dubai and Moscow weather"
- "List all available cities"
"""
    
    return tools_text


# Create Gradio Interface - Gradio 6.0 compatible
app = gr.Blocks(title="MCP Protocol Chatbot")

with app:
    gr.Markdown("""
    # 🤖 AI Chatbot with MCP Protocol
    
    A production-ready chatbot using Azure OpenAI and real MCP servers for tool execution.
    
    ### 🎯 Available Capabilities:
    - 📁 **File Operations** - List, read, and search files
    - 🔢 **Calculator** - Math operations and conversions
    - 🌤️ **Weather** - Real-time weather data and forecasts
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            # Gradio 6.0: Chatbot expects messages format by default
            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
                show_label=True
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Type your message here...",
                    show_label=False,
                    scale=4,
                    container=False
                )
                submit_btn = gr.Button("Send 🚀", scale=1, variant="primary")
            
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
                use_tools_cb = gr.Checkbox(
                    label="Enable MCP Tools",
                    value=True,
                    info="Allow AI to use MCP servers"
                )
                temperature_slider = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=0.7,
                    step=0.1,
                    label="Temperature",
                    info="Higher = more creative"
                )
        
        with gr.Column(scale=1):
            gr.Markdown("## ⚙️ Control Panel")
            
            stats_display = gr.Markdown(get_stats())
            refresh_stats_btn = gr.Button("🔄 Refresh Stats", size="sm")
            
            gr.Markdown("---")
            
            with gr.Accordion("📖 Available Tools", open=False):
                tools_display = gr.Markdown("Loading tools...")
                refresh_tools_btn = gr.Button("🔄 Refresh Tools", size="sm")
            
            with gr.Accordion("💡 Quick Examples", open=False):
                gr.Markdown("""
                **File Operations (MCP):**
                - List all files
                - Read test1.txt
                - Search for "MCP" in files
                
                **Calculations (MCP):**
                - Add 10, 20, and 30
                - Calculate factorial of 8
                - What's 144 divided by 12?
                
                **Conversions (MCP):**
                - Convert 32°F to Celsius
                - Convert 1 mile to meters
                
                **Weather (MCP):** 🌤️
                - What's the weather in London?
                - Show me a 5-day forecast for Tokyo
                - Compare weather between Dubai and Moscow
                - List all available cities
                
                **General:**
                - Explain quantum computing
                - Write Python code to sort a list
                """)
            
            gr.Markdown("---")
            
            status_text = gr.Textbox(
                label="Status",
                value="Initializing...",
                interactive=False
            )
    
    # Event handlers
    def submit_message(message, history, use_tools, temperature):
        return asyncio.run(
            process_message(message, history, use_tools, temperature)
        )
    
    submit_btn.click(
        fn=submit_message,
        inputs=[msg, chatbot, use_tools_cb, temperature_slider],
        outputs=[chatbot, msg]
    )
    
    msg.submit(
        fn=submit_message,
        inputs=[msg, chatbot, use_tools_cb, temperature_slider],
        outputs=[chatbot, msg]
    )
    
    clear_btn.click(
        fn=clear_conversation,
        outputs=[chatbot, status_text]
    )
    
    refresh_stats_btn.click(
        fn=get_stats,
        outputs=stats_display
    )
    
    refresh_tools_btn.click(
        fn=get_available_tools,
        outputs=tools_display
    )
    
    # Auto-refresh tools on app load
    app.load(
        fn=get_available_tools,
        outputs=tools_display
    )
    
    # Auto-refresh stats on app load
    app.load(
        fn=get_stats,
        outputs=stats_display
    )
    
    gr.Markdown("""
    ---
    ### 🔒 Privacy & Security
    - All conversations processed through Azure OpenAI
    - MCP servers run in isolated processes
    - File access restricted to designated directory
    - No data stored permanently
    
    ### 📚 Documentation
    Built with Gradio, Azure OpenAI, and Model Context Protocol (MCP)
    
    **Architecture:** Real MCP protocol with stdio communication
    """)


if __name__ == "__main__":
    # Initialize MCP servers
    print("Starting AI Chatbot with MCP Protocol...")
    print("="*60)
    
    try:
        init_result = asyncio.run(initialize_mcp_servers())
        print(init_result)
        print("="*60)
    except Exception as e:
        print(f"⚠️ Warning: MCP initialization failed - {e}")
        print("App will start but tools may not be available")
        import traceback
        traceback.print_exc()
    
    # Debug: Show what servers are running
    servers = mcp_client.get_all_servers()
    print(f"\n✅ Active MCP Servers: {servers}")
    print(f"✅ MCP Initialized: {mcp_initialized}")
    print("="*60 + "\n")
    
    # Launch Gradio - CSS moved to launch() for Gradio 6.0
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("APP_PORT", "7860")),
        share=False,
        show_error=True
    )