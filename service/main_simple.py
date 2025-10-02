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
            "has_gemini_key": bool(os.getenv("GEMINI_API_KEY")),
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
        import google.generativeai

        return {
            "status": "healthy",
            "dependencies": {
                "openai": "✅",
                "supabase": "✅",
                "pandas": "✅",
                "google_generativeai": "✅"
            }
        }
    except ImportError as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/test-gemini")
async def test_gemini():
    """Test Gemini orchestrator"""
    try:
        from gemini_orchestrator import GeminiOrchestrator
        orchestrator = GeminiOrchestrator()
        return {
            "gemini_orchestrator": "✅",
            "use_gemini": getattr(orchestrator, 'use_gemini', False),
            "model_configured": orchestrator.model is not None if orchestrator.use_gemini else "OpenAI fallback"
        }
    except ImportError as e:
        return {"gemini_orchestrator": "❌", "error": str(e)}
    except Exception as e:
        return {"gemini_orchestrator": "❌", "error": f"Other error: {str(e)}"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)