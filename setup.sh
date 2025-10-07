#!/bin/bash

echo "🎤 Karaoke Platform Setup"
echo "========================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Install from: https://www.python.org/downloads/"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    echo "   Install from: https://nodejs.org/"
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Please install FFmpeg manually: https://ffmpeg.org/download.html"
        exit 1
    fi
fi

# Setup environment variables
echo "🔧 Setting up environment variables..."
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Create .env from example
cp env.example .env
echo "✅ .env file created!"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install Python dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create cache directories
echo "📁 Creating cache directories..."
mkdir -p cache/audio cache/metadata cache/temp_separation

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔑 Next steps:"
echo "1. Get a Genius API token from: https://genius.com/api-clients"
echo "2. Edit .env file and replace 'your_genius_token_here' with your actual token"
echo "3. Or leave it as-is to run in Whisper-only mode (no corrections)"
echo ""
echo "🚀 To start the app:"
echo "   ./start.sh"
echo ""
echo "📁 Files created:"
echo "   - .env (your environment variables)"
echo "   - venv/ (Python virtual environment)"
echo "   - frontend/node_modules/ (Node.js dependencies)"
echo "   - cache/ (audio and metadata cache)"
