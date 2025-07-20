from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.core.config import settings
from app.api.routers import health, auth, webhook, events
import uvicorn

app = FastAPI(
    title="Adme: GitHub Resume & Social Media Platform",
    description="Backend for tracking GitHub activity and generating resume updates and social media suggestions",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Session Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.APP_SECRET_KEY)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(events.router, prefix="/api/v1/events")
app.include_router(webhook.router, prefix="/api/v1/webhook")

@app.on_event("startup")
async def startup_event():
    pass

@app.on_event("shutdown")
async def shutdown_event():
    pass

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )