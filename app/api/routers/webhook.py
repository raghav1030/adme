from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import verify_webhook_signature
from app.core.database import AsyncSession, get_db_session
import json

router = APIRouter()


class WebhookResponse(BaseModel):
    message: str


@router.post("/webhook", response_model=WebhookResponse)
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    # Get signature header
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(
            status_code=400, detail="Missing X-Hub-Signature-256 header"
        )

    # Read raw payload
    payload = await request.body()

    # Verify signature
    if not verify_webhook_signature(payload, signature, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse event
    event_type = request.headers.get("X-GitHub-Event")
    payload_data = json.loads(payload.decode())

    # Log event (placeholder for Celery task)
    print(f"Received {event_type} event: {payload_data}")

    return WebhookResponse(message="Webhook received")
