#!/bin/bash

# Debug startup script for Railway
echo "Starting Adronaut AutoGen Service..."
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Files in directory: $(ls -la)"

# Check environment variables
echo "Environment check:"
echo "PORT: ${PORT:-'not set'}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+set}"
echo "SUPABASE_URL: ${SUPABASE_URL:+set}"
echo "SUPABASE_KEY: ${SUPABASE_KEY:+set}"

# Try simple version first if main fails
if [ -f "main_simple.py" ]; then
    echo "Trying simple version first..."
    python -c "import main_simple" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "Starting with main_simple.py..."
        exec uvicorn main_simple:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
    fi
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    exit 1
fi

# Start the application
echo "Starting uvicorn server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info