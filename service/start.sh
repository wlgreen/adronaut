#!/bin/bash

# Startup script for Railway
echo "Starting Adronaut AutoGen Service..."
echo "Python version: $(python --version)"

# Check environment variables
echo "Environment check:"
echo "PORT: ${PORT:-'not set'}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+set}"
echo "SUPABASE_URL: ${SUPABASE_URL:+set}"
echo "SUPABASE_KEY: ${SUPABASE_KEY:+set}"

# Test main.py import
echo "Testing main.py import..."
python -c "
try:
    import main
    print('✅ Main module import successful')
except Exception as e:
    print(f'❌ Main module import failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "Main import failed, falling back to simple version..."
    exec uvicorn main_simple:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
fi

# Start the full AutoGen application
echo "Starting full AutoGen service on port ${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info