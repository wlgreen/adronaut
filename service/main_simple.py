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
        import crewai

        return {
            "status": "healthy",
            "dependencies": {
                "openai": "✅",
                "supabase": "✅",
                "pandas": "✅",
                "crewai": "✅"
            }
        }
    except ImportError as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/test-crewai")
async def test_crewai():
    """Test CrewAI import separately"""
    try:
        import crewai
        from crew_orchestrator import CrewAIOrchestrator
        orchestrator = CrewAIOrchestrator()
        return {
            "crewai": "✅",
            "version": getattr(crewai, '__version__', 'unknown'),
            "gemini_configured": hasattr(orchestrator, 'use_gemini') and orchestrator.use_gemini,
            "llm_type": type(orchestrator.llm).__name__
        }
    except ImportError as e:
        return {"crewai": "❌", "error": str(e)}
    except Exception as e:
        return {"crewai": "❌", "error": f"Other error: {str(e)}"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)