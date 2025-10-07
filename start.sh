#!/bin/bash

echo "🎤 Starting Karaoke Platform..."
echo "==============================="
echo ""

# Check if setup has been run
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   ./setup.sh"
    exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies not found. Please run setup first:"
    echo "   ./setup.sh"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ Environment file not found. Please run setup first:"
    echo "   ./setup.sh"
    exit 1
fi

# Check for existing processes and offer to kill them
BACKEND_PID=$(lsof -ti:8000 2>/dev/null)
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null)

if [ ! -z "$BACKEND_PID" ] || [ ! -z "$FRONTEND_PID" ]; then
    echo "⚠️  Found existing processes:"
    if [ ! -z "$BACKEND_PID" ]; then
        echo "   Backend (port 8000): PID $BACKEND_PID"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "   Frontend (port 3000): PID $FRONTEND_PID"
    fi
    echo ""
    echo "Would you like to kill these processes and start fresh? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🛑 Killing existing processes..."
        if [ ! -z "$BACKEND_PID" ]; then
            kill -9 $BACKEND_PID 2>/dev/null
            echo "   ✅ Killed backend (PID: $BACKEND_PID)"
        fi
        if [ ! -z "$FRONTEND_PID" ]; then
            kill -9 $FRONTEND_PID 2>/dev/null
            echo "   ✅ Killed frontend (PID: $FRONTEND_PID)"
        fi
        echo "   Waiting 2 seconds for ports to be released..."
        sleep 2
    else
        echo "❌ Cannot start - ports are already in use"
        echo "   Use ./stop.sh to kill existing processes, or choose 'y' above"
        exit 1
    fi
fi

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        echo "   Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "   Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    echo "✅ Shutdown complete!"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend
echo "🚀 Starting backend server..."
cd backend
source ../venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start. Check the logs above."
    exit 1
fi

echo "✅ Backend started (PID: $BACKEND_PID)"

# Start frontend
echo "🚀 Starting frontend server..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 5

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ Frontend failed to start. Check the logs above."
    cleanup
    exit 1
fi

echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo ""
echo "🎉 Karaoke Platform is running!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user to stop
wait