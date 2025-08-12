#!/bin/bash

# Production Embedding Service Setup Script
# This script handles the SQLite3 compatibility issue and sets up the environment

echo "🚀 Setting up Production Embedding Service..."
echo "================================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📋 Python version: $python_version"

# Check current SQLite3 version
sqlite_version=$(python3 -c "import sqlite3; print(sqlite3.sqlite_version)" 2>/dev/null || echo "unknown")
echo "📋 Current SQLite3 version: $sqlite_version"

# Install requirements with SQLite3 fix
echo ""
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip

# Install pysqlite3-binary first to fix SQLite3 compatibility
echo "🔧 Installing pysqlite3-binary for SQLite3 compatibility..."
pip3 install pysqlite3-binary

# Install other requirements
echo "📦 Installing remaining dependencies..."
pip3 install -r requirements.txt

# Verify ChromaDB can be imported
echo ""
echo "🧪 Testing ChromaDB import..."
python3 -c "
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import chromadb
print('✅ ChromaDB imported successfully!')
print('📋 ChromaDB version:', chromadb.__version__)
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ ChromaDB setup successful!"
else
    echo "❌ ChromaDB import failed. Trying alternative approach..."
    
    # Alternative: Install chromadb with specific SQLite3 version
    pip3 install --force-reinstall --no-deps chromadb
    pip3 install pysqlite3-binary
    
    echo "🔄 Retesting ChromaDB import..."
    python3 -c "
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import chromadb
print('✅ ChromaDB imported successfully after retry!')
" 2>/dev/null
fi

# Create necessary directories
echo ""
echo "📁 Creating necessary directories..."
mkdir -p chroma_db
mkdir -p uploads

# Check if .env file exists and has API key
echo ""
echo "🔑 Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please create one with your GEMINI_API_KEY"
    echo "📋 Example .env content:"
    echo "GEMINI_API_KEY=your_api_key_here"
    echo "HOST=127.0.0.1"
    echo "PORT=5000"
    echo "DEBUG=false"
else
    if grep -q "GEMINI_API_KEY=" .env && ! grep -q "GEMINI_API_KEY=$" .env; then
        echo "✅ GEMINI_API_KEY found in .env file"
    else
        echo "⚠️  Please add your GEMINI_API_KEY to the .env file"
    fi
fi

echo ""
echo "🎉 Setup completed!"
echo "================================================"
echo "📋 Next steps:"
echo "1. Add your GEMINI_API_KEY to the .env file"
echo "2. Run the application: python3 app.py"
echo "3. Run tests: python3 unit_test.py"
echo "4. Access Swagger UI: http://127.0.0.1:5000/docs/"
echo ""
echo "🔧 If you still encounter SQLite3 issues, try:"
echo "   pip3 install --force-reinstall pysqlite3-binary"
echo "   pip3 install --force-reinstall chromadb"