#!/bin/bash

echo "🚀 Setting up AI Chatbot with MCP Protocol..."
echo "=============================================="

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi
echo "✓ Python 3 found"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create test files
echo "Creating test files..."
mkdir -p test_files
echo "Hello from MCP protocol!" > test_files/test1.txt
echo "This is a real MCP server" > test_files/test2.txt
echo "Testing MCP communication" > test_files/data.txt

# Check .env
if [ ! -f .env ]; then
    echo "⚠ .env file not found. Creating template..."
    cat > .env << 'EOF'
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Application Settings
APP_PORT=7860
FILE_SERVER_PATH=./test_files
MAX_HISTORY=50
EOF
    echo "⚠ Please edit .env with your Azure OpenAI credentials"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Azure OpenAI credentials"
echo "2. Run: source .venv/bin/activate"
echo "3. Test: python tests/test_mcp.py"
echo "4. Run app: python app.py"