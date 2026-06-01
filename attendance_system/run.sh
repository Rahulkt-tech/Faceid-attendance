#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  FaceAttend — Setup & Run Script
#  Run this once to install everything, then use it to start
# ─────────────────────────────────────────────────────────────

echo ""
echo "  ███████╗ █████╗  ██████╗███████╗ █████╗ ████████╗████████╗███████╗███╗   ██╗██████╗ "
echo "  ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗╚══██╔══╝╚══██╔══╝██╔════╝████╗  ██║██╔══██╗"
echo "  █████╗  ███████║██║     █████╗  ███████║   ██║      ██║   █████╗  ██╔██╗ ██║██║  ██║"
echo "  ██╔══╝  ██╔══██║██║     ██╔══╝  ██╔══██║   ██║      ██║   ██╔══╝  ██║╚██╗██║██║  ██║"
echo "  ██║     ██║  ██║╚██████╗███████╗██║  ██║   ██║      ██║   ███████╗██║ ╚████║██████╔╝"
echo "  ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═════╝ "
echo ""
echo "  Smart Face Detection Attendance System"
echo "─────────────────────────────────────────────────────────────"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Install dependencies
echo ""
echo "📦 Installing dependencies (this may take a few minutes on first run)..."
echo "   (face-recognition requires cmake + dlib — takes 2-5 mins to compile)"
echo ""

# cmake needed for dlib
pip3 install cmake --quiet
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Installation failed. Try manually:"
    echo "   sudo apt-get install cmake build-essential"
    echo "   pip3 install -r requirements.txt"
    exit 1
fi

echo ""
echo "✅ All dependencies installed!"
echo ""
echo "─────────────────────────────────────────────────────────────"
echo "  🚀 Starting FaceAttend on http://localhost:5000"
echo "  📁 Portal 1 — Student Database: http://localhost:5000/register"
echo "  📸 Portal 2 — Live Attendance:  http://localhost:5000/attendance"
echo "  Press Ctrl+C to stop"
echo "─────────────────────────────────────────────────────────────"
echo ""

python3 app.py
