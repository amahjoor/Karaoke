#!/bin/bash

echo "🎤 Starting Karaoke Platform..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
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

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create cache directory
mkdir -p cache/audio cache/metadata

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "1. Backend: cd backend && python main.py"
echo "2. Frontend: cd frontend && npm start"
echo ""
echo "Then open http://localhost:3000 in your browser"
