#!/bin/bash
echo "Starting Z-Image-Turbo Backend Server..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
python main.py

