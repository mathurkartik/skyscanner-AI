"""
AI Travel Planner - FastAPI Application
Phase 0: Project skeleton with health check and stub plan endpoint.
"""

import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .api.routes import router as api_router
from .models import HealthResponse

settings = get_settings()

app = FastAPI(
    title="AI Travel Planner API",
    description="Multi-agent travel planning system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """Add trace ID to all requests for observability."""
    trace_id = str(uuid4())
    request.state.trace_id = trace_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Process-Time-Ms"] = str(int(process_time))
    
    return response


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Liveness check for load balancers and frontend preflight.
    Phase 0 exit criteria.
    Phase 2: Includes token budget status.
    """
    from .llm import get_token_tracker
    from .config import get_settings
    
    settings = get_settings()
    
    # Get token status if tracking enabled
    token_status = None
    if settings.enable_token_tracking:
        try:
            tracker = get_token_tracker()
            summary = tracker.get_usage_summary()
            token_status = {
                "daily_total": summary["daily_total"],
                "remaining": summary["remaining"],
                "percent_used": round(summary["percent_used"], 2),
                "daily_limit": summary["daily_limit"],
            }
        except Exception:
            token_status = {"error": "Token tracker unavailable"}
    
    return HealthResponse(
        status="healthy",
        tokens=token_status,
        llm_provider=settings.llm_provider,
        llm_available=(
            bool(settings.gemini_api_key) if settings.llm_provider == "gemini"
            else bool(settings.groq_api_key) if settings.llm_provider == "groq"
            else False
        )
    )


# Include API routes
app.include_router(api_router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with trace ID."""
    trace_id = getattr(request.state, "trace_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "trace_id": trace_id,
            "detail": str(exc) if settings.debug else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
