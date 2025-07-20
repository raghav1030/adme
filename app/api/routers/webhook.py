from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from typing import List
import httpx
import uuid
import secrets

from app.core.config import settings
from app.core.database import AsyncSession, get_db_session
from app.core.security import decrypt_token
from app.models import (
    User,
    UserOAuth,
    Repository,
)
from app.models import Webhook
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, status, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import AsyncSession, get_db_session
from app.models import GitHubEvents, Webhook, Repository, User  # Import your models
from app.utils import github_ts  # Assuming this utility exists for timestamp conversion
import hmac
import hashlib
import json
from typing import Optional

router = APIRouter()


class WebhookCreate(BaseModel):
    repo_full_name: str
    events: List[str] = ["push", "pull_request", "issues", "commit_comment"]
    active: bool = True
    config_url: HttpUrl


class WebhookResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    repo_id: int
    github_webhook_id: int
    url: HttpUrl
    secret: str
    events: List[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhooksListResponse(BaseModel):
    message: str
    webhooks: List[WebhookResponse]


class WebhookDeleteResponse(BaseModel):
    message: str
    webhook_id: uuid.UUID


async def get_github_access_token(
    user_id: str, db: AsyncSession = Depends(get_db_session)
) -> str:
    """Helper function to get the decrypted GitHub access token for a user."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format"
        )

    stmt = select(UserOAuth).where(
        UserOAuth.user_id == user_uuid, UserOAuth.provider == "github"
    )
    result = await db.execute(stmt)
    user_oauth = result.scalar_one_or_none()

    if not user_oauth:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub OAuth not found for user",
        )

    return decrypt_token(user_oauth.access_token)


async def get_repository_details(repo_full_name: str, access_token: str) -> dict:
    """Helper to fetch repository details from GitHub."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{repo_full_name}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Repository '{repo_full_name}' not found on GitHub or not accessible.",
                )
            elif e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid GitHub token.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch repository details from GitHub: {e.response.text}",
            )


@router.post(
    "/{user_id}/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository_webhook(
    user_id: str,
    webhook_data: WebhookCreate,
    db: AsyncSession = Depends(get_db_session),
    access_token: str = Depends(get_github_access_token),
):
    """
    Attaches a webhook to a specified GitHub repository for the given user.
    """
    user_uuid = uuid.UUID(user_id)

    # 1. Fetch repository details from GitHub and store/update in DB
    repo_details = await get_repository_details(
        webhook_data.repo_full_name, access_token
    )
    repo_id = repo_details["id"]
    repo_full_name = repo_details["full_name"]

    stmt = select(Repository).where(Repository.id == repo_id)
    result = await db.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        # Create a new repository entry if it doesn't exist
        repository = Repository(
            id=repo_details.get("id"),
            node_id=repo_details.get("node_id"),
            name=repo_details.get("name"),
            full_name=repo_details.get("full_name"),
            owner_login=repo_details.get("owner", {}).get("login"),
            owner_type=repo_details.get("owner", {}).get("type").lower(),
            private=repo_details.get("private", False),
            default_branch=repo_details.get("default_branch"),
            description=repo_details.get("description"),
            language=repo_details.get("language"),
            topics=repo_details.get("topics", []),
            homepage=repo_details.get("homepage"),
            license=repo_details.get("license"),
            stargazers_count=repo_details.get("stargazers_count", 0),
            forks_count=repo_details.get("forks_count", 0),
            created_at_gh=repo_details.get(
                "created_at"
            ),  # Assuming github_ts conversion happens elsewhere or handled by ORM
            updated_at_gh=repo_details.get("updated_at"),
            pushed_at_gh=repo_details.get("pushed_at"),
        )
        db.add(repository)
        await db.commit()
        await db.refresh(repository)
    else:
        # Optionally update existing repository details if needed
        pass  # For this example, we'll assume details are up-to-date or not critical to update on webhook creation

    # 2. Check if webhook already exists for this repo and user
    stmt = select(Webhook).where(
        Webhook.user_id == user_uuid, Webhook.repo_id == repo_id
    )
    result = await db.execute(stmt)
    existing_webhook = result.scalar_one_or_none()
    if existing_webhook:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook already exists for this repository and user.",
        )

    # 3. Create webhook on GitHub
    webhook_secret = secrets.token_hex(20)  # Generate a secure secret
    github_webhook_payload = {
        "name": "web",  # "web" for a URL-based webhook
        "active": webhook_data.active,
        "events": webhook_data.events,
        "config": {
            "url": str(
                webhook_data.config_url
            ),  # The public URL where GitHub sends events
            "content_type": "json",
            "secret": webhook_secret,
        },
    }

    async with httpx.AsyncClient() as client:
        try:
            github_response = await client.post(
                f"https://api.github.com/repos/{repo_full_name}/hooks",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json=github_webhook_payload,
            )
            github_response.raise_for_status()
            github_webhook_data = github_response.json()
            github_webhook_id = github_webhook_data["id"]
            github_webhook_url = github_webhook_data[
                "url"
            ]  # The URL to manage the webhook on GitHub
        except httpx.HTTPStatusError as e:
            detail = f"Failed to create webhook on GitHub: {e.response.text}"
            if e.response.status_code == 404:
                detail = f"Repository '{repo_full_name}' not found on GitHub or user lacks permissions to create webhooks."
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error when creating webhook on GitHub: {str(e)}",
            )

    # 4. Store webhook information in your database
    new_webhook = Webhook(
        user_id=user_uuid,
        repo_id=repo_id,
        github_webhook_id=github_webhook_id,
        url=github_webhook_url,  # Store the GitHub-provided URL for management
        secret=webhook_secret,
        events=webhook_data.events,
        active=webhook_data.active,
    )
    db.add(new_webhook)
    try:
        await db.commit()
        await db.refresh(new_webhook)
    except IntegrityError:
        await db.rollback()
        # If there's a race condition and it somehow gets added between check and insert
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook already exists for this repository and user (DB conflict).",
        )
    except Exception as e:
        # Consider deleting the webhook from GitHub if DB commit fails
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"https://api.github.com/repos/{repo_full_name}/hooks/{github_webhook_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store webhook in database: {str(e)}",
        )

    return new_webhook


@router.get("/{user_id}/webhooks", response_model=WebhooksListResponse)
async def list_user_webhooks(user_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Lists all webhooks associated with the user for their selected repositories.
    """
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format"
        )

    stmt = (
        select(Webhook)
        .where(Webhook.user_id == user_uuid)
        .order_by(Webhook.created_at.desc())
    )
    result = await db.execute(stmt)
    webhooks = result.scalars().all()

    return WebhooksListResponse(
        message="Webhooks retrieved successfully",
        webhooks=[WebhookResponse.model_validate(webhook) for webhook in webhooks],
    )


@router.delete("/{user_id}/webhooks/{webhook_id}", response_model=WebhookDeleteResponse)
async def delete_repository_webhook(
    user_id: str,
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    access_token: str = Depends(get_github_access_token),
):
    """
    Deletes a specific webhook from a user's repository.
    """
    user_uuid = uuid.UUID(user_id)

    # 1. Find the webhook in your database
    stmt = select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user_uuid)
    result = await db.execute(stmt)
    webhook_to_delete = result.scalar_one_or_none()

    if not webhook_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found or does not belong to this user.",
        )

    # 2. Get repository details to construct GitHub API URL
    stmt = select(Repository).where(Repository.id == webhook_to_delete.repo_id)
    result = await db.execute(stmt)
    repository = result.scalar_one_or_none()

    if not repository:
        # This shouldn't happen if data integrity is maintained, but good to check
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated repository not found for webhook.",
        )

    repo_full_name = repository.full_name
    github_webhook_id = webhook_to_delete.github_webhook_id

    # 3. Delete webhook from GitHub
    async with httpx.AsyncClient() as client:
        try:
            github_response = await client.delete(
                f"https://api.github.com/repos/{repo_full_name}/hooks/{github_webhook_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            github_response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Webhook might already be deleted on GitHub, proceed to delete from DB
                print(
                    f"Webhook {github_webhook_id} not found on GitHub, deleting from DB anyway."
                )
            elif e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid GitHub token for deleting webhook.",
                )
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to delete webhook on GitHub: {e.response.text}",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error when deleting webhook from GitHub: {str(e)}",
            )

    # 4. Delete webhook from your database
    await db.delete(webhook_to_delete)
    await db.commit()

    return WebhookDeleteResponse(
        message="Webhook deleted successfully", webhook_id=webhook_id
    )


def verify_github_signature(payload_body: bytes, secret: str, signature: str) -> bool:
    """
    Verifies the SHA256 signature of the incoming GitHub webhook payload.
    """
    if not signature:
        return False

    # Extract the hash from the signature header (e.g., "sha256=abcdef12345...")
    sha_name, signature_hash = signature.split("=", 1)
    if sha_name != "sha256":
        return False

    # Create an HMAC object using the secret and the payload body
    # The secret must be bytes, and the payload_body must be bytes
    mac = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)

    # Compare the computed hash with the provided signature hash
    return hmac.compare_digest(mac.hexdigest(), signature_hash)


@router.post("/github/webhook-events")
async def github_webhook_receiver(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    # GitHub sends these headers
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """
    Endpoint to receive and process GitHub webhook events.
    """
    payload_body = await request.body()
    try:
        payload_json = json.loads(payload_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Extract repository ID from the payload to find the corresponding webhook secret
    # GitHub webhook payloads typically have a 'repository' object with an 'id'
    repo_id = payload_json.get("repository", {}).get("id")
    if not repo_id:
        print(
            f"Warning: Incoming webhook payload missing repository ID. Delivery ID: {x_github_delivery}"
        )
        # For security, if we can't identify the repo, we can't get the secret, so reject.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository ID not found in payload.",
        )

    # Fetch the webhook secret from your database using repo_id and potentially user_id
    # Note: A single repo might have multiple webhooks by different users.
    # For simplicity, we'll assume one webhook per repo for now, or you'll need
    # a more sophisticated way to map incoming webhooks to your stored secrets.
    # If a user can only attach one webhook per repo, then `repo_id` is sufficient.
    # If multiple users can attach webhooks to the *same* repo, your `Webhook` table
    # might need a `user_id` in the query to uniquely identify the secret.
    # For now, we'll fetch *any* webhook associated with this repo_id and use its secret.
    # A more robust solution might involve storing the GitHub webhook ID in the payload
    # or a unique identifier in the webhook URL itself.

    stmt = select(Webhook).where(Webhook.repo_id == repo_id)
    # If you have multiple webhooks per repo (e.g., different users setting them up),
    # you might need to refine this query to find the *exact* webhook.
    # For instance, if you embed a user_id or a custom identifier in your config_url,
    # you could extract it from request.url and use it here.
    # For now, we'll just pick the first one found.
    result = await db.execute(stmt)
    stored_webhook = result.scalar_one_or_none()

    if not stored_webhook:
        print(
            f"Warning: No matching webhook found in DB for repo_id {repo_id}. Delivery ID: {x_github_delivery}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found for this repository.",
        )

    # Verify the signature
    if x_hub_signature_256:
        if not verify_github_signature(
            payload_body, stored_webhook.secret, x_hub_signature_256
        ):
            print(
                f"Warning: Invalid signature for webhook. Delivery ID: {x_github_delivery}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature."
            )
    else:
        # GitHub always sends a signature for webhooks with a secret.
        # If no signature is present, it's either misconfigured or not from GitHub.
        print(
            f"Warning: No X-Hub-Signature-256 header. Delivery ID: {x_github_delivery}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature header missing."
        )

    # Process the event
    try:
        # Extract user_id from the stored webhook for the GitHubEvents table
        user_id_from_webhook = stored_webhook.user_id

        # Extract occurred_at from the payload, typically 'created_at' for most events
        # Or 'pushed_at' for push events, etc.
        # This might need more robust parsing based on event type.
        occurred_at_str = (
            payload_json.get("hook", {}).get("created_at")
            or payload_json.get("event", {}).get("created_at")
            or payload_json.get("created_at")
        )
        if not occurred_at_str and "push" in x_github_event:
            # For push events, the timestamp is often derived from the last commit
            # or the overall push event timestamp if available.
            # For simplicity, we'll use current UTC time if not explicitly in payload.
            occurred_at = datetime.utcnow()
        else:
            occurred_at = (
                github_ts(occurred_at_str) if occurred_at_str else datetime.utcnow()
            )

        # GitHub event ID (distinct from your internal UUID)
        event_id_gh = int(
            x_github_delivery.split("-")[0]
        )  # GitHub delivery ID can serve as a unique event ID

        # Check if an event with this GitHub event ID already exists to prevent duplicates
        existing_event_stmt = select(GitHubEvents).where(
            GitHubEvents.event_id_gh == event_id_gh
        )
        existing_event_result = await db.execute(existing_event_stmt)
        if existing_event_result.scalar_one_or_none():
            print(
                f"Info: Duplicate event received with GitHub ID {event_id_gh}. Skipping processing."
            )
            return {"message": "Event already processed"}

        # Store the event in your database
        github_event = GitHubEvents(
            user_id=user_id_from_webhook,
            repo_id=repo_id,
            event_type=x_github_event,
            event_id_gh=event_id_gh,
            payload=payload_json,
            occurred_at=occurred_at,
            processed=False,  # Mark as false, a background worker can process it later
        )
        db.add(github_event)
        await db.commit()
        await db.refresh(github_event)

        print(
            f"Successfully received and stored GitHub event: {x_github_event} for repo {repo_id}"
        )
        return {"message": "Webhook event received and stored successfully"}

    except IntegrityError:
        await db.rollback()
        # This might happen if event_id_gh is not truly unique across all webhooks,
        # or if there's a race condition for a very rapid duplicate delivery.
        print(f"IntegrityError storing event {event_id_gh}. Likely duplicate.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event already exists or database conflict.",
        )
    except Exception as e:
        await db.rollback()  # Ensure rollback on any other error
        print(f"Error processing GitHub webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}",
        )
