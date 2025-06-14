from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import time

from api.routes import health, quiz, topics, auth, progress, personalization, topic_requests, mastery
from api.v1 import adaptive_learning
from core.config import settings
from core.logging_config import logger, performance_logger
from db.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Relevia backend server")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")
    yield
    # Shutdown
    logger.info("🛑 Shutting down Relevia backend server")
    await engine.dispose()

app = FastAPI(
    title="Relevia API",
    description="Adaptive Learning Platform API",
    version="0.1.0",
    lifespan=lifespan
)

# API request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    api_logger = logger.getChild("api")
    api_logger.info(f"→ {request.method} {request.url.path} | Query: {dict(request.query_params)}")
    
    # Process request
    response = await call_next(request)
    
    # Log response time
    duration_ms = (time.time() - start_time) * 1000
    api_logger.info(f"← {request.method} {request.url.path} | {response.status_code} | {duration_ms:.1f}ms")
    
    # Log slow requests
    if duration_ms > 1000:  # Slower than 1 second
        perf_logger = logger.getChild("performance")
        perf_logger.warning(f"SLOW REQUEST: {request.method} {request.url.path} took {duration_ms:.1f}ms")
    
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(topics.router, prefix="/api/v1/topics", tags=["topics"])
app.include_router(topic_requests.router, prefix="/api/v1/topics", tags=["topic_requests"])
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["quiz"])
app.include_router(progress.router, prefix="/api/v1/progress", tags=["progress"])
app.include_router(personalization.router, prefix="/api/v1/personalization", tags=["personalization"])
app.include_router(mastery.router, prefix="/api/v1", tags=["mastery"])
app.include_router(adaptive_learning.router, prefix="/api/v1", tags=["adaptive_learning"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)