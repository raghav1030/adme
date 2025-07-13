from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routers import health, auth, webhook

app = FastAPI(
    title="Adme: GitHub Resume & Social Media Platform",
    description="Backend for tracking GitHub activity and generating resume updates and social media suggestions",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust for your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(webhook.router, prefix="/api/v1/webhook")


@app.on_event("startup")
async def startup_event():
    # Placeholder for database/redis initialization
    pass


@app.on_event("shutdown")
async def shutdown_event():
    # Placeholder for cleanup
    pass
