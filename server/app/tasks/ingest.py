from celery import shared_task
from sqlalchemy import select
from app.api.core import AsyncSessionLocal
from app.api.models import GitHubEvents
from app.api.models import Summaries

# from app.services.summarizer import summarize_event
# from app.services.rag import embed_and_store


@shared_task(bind=True, max_retries=3)
async def process_github_event(self, delivery_id: str):
    async with AsyncSessionLocal() as db:
        stmt = select(GitHubEvents).where(
            GitHubEvents.event_id_gh == int(delivery_id, 16),
            GitHubEvents.processed.is_(False),
        )
        event = (await db.execute(stmt)).scalar_one_or_none()
        if not event:
            return

        summary_text, tech_stack = "test summary"
        embedding = [0.1] * 1536

        db.add(
            Summaries(
                event_id=event.id,
                occurred_at=event.occurred_at,
                summary_text=summary_text,
                tech_stack=tech_stack,
                embedding=embedding,
            )
        )
        event.processed = True
        await db.commit()
