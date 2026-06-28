"""
Simple tests for Azure OpenAI MCP Server
Run manually to verify functionality
"""

import asyncio
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

async def test_connection():
    """Test Azure OpenAI connection"""
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    try:
        response = await client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "user", "content": "Say 'Connection successful!'"}
            ],
            max_tokens=50
        )
        print("✓ Connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())