from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Adronaut AutoGen Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Adronaut AutoGen Service",
        "status": "running",
        "environment": {
            "port": os.getenv("PORT", "8000"),
            "python_path": os.getenv("PYTHONPATH", "not set"),
            "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
            "has_supabase_url": bool(os.getenv("SUPABASE_URL")),
            "has_supabase_key": bool(os.getenv("SUPABASE_KEY")),
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    try:
        # Test imports
        import openai
        import supabase
        import pandas

        return {
            "status": "healthy",
            "dependencies": {
                "openai": "✅",
                "supabase": "✅",
                "pandas": "✅"
            }
        }
    except ImportError as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/test-autogen")
async def test_autogen():
    """Test AutoGen import separately"""
    try:
        import autogen
        return {"autogen": "✅", "version": autogen.__version__}
    except ImportError as e:
        return {"autogen": "❌", "error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)