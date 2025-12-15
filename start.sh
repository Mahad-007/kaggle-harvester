#!/bin/bash
# Start script for Kaggle Data Ingestion Engine
# Runs both the ingestion engine and web dashboard

echo "=================================================="
echo "Starting Kaggle Data Ingestion Engine"
echo "=================================================="

# Start the ingestion engine in the background
echo "Starting ingestion engine (main.py) in background..."
python3 main.py &
ENGINE_PID=$!
echo "✓ Ingestion engine started with PID: $ENGINE_PID"

# Wait a moment for the engine to initialize
sleep 3

# Start the web dashboard (foreground)
echo "Starting web dashboard on port $PORT..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 web_app:app
