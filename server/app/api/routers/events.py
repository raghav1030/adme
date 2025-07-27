from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.core.database import AsyncSession, get_db_session
from app.api.models import User, UserOAuth, GitHubEvents, Repository
from app.api.core.config import settings
from app.api.core.security import decrypt_token
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import httpx
import uuid
import asyncio
from app.api.utils import github_ts, model_to_dict

router = APIRouter()


class GitHubEventResponse(BaseModel):
    id: str
    event_type: str
    repo_id: int
    payload: dict
    occurred_at: datetime
    processed: bool


class EventsResponse(BaseModel):
    message: str
    events: List[GitHubEventResponse]


class RepositoryResponse(BaseModel):
    id: int
    node_id: str
    name: str
    full_name: str
    owner_login: str
    owner_type: str
    private: bool
    default_branch: Optional[str]
    description: Optional[str]
    language: Optional[str]
    topics: Optional[List[str]]
    homepage: Optional[str]
    license: Optional[dict]
    stargazers_count: int
    forks_count: int
    created_at_gh: Optional[datetime]
    updated_at_gh: Optional[datetime]
    pushed_at_gh: Optional[datetime]


class RepositoriesResponse(BaseModel):
    message: str
    repositories: List[RepositoryResponse]


class LatestEventsRequest(BaseModel):
    user_id: str
    limit: int = 10


@router.post("/latest", response_model=EventsResponse)
async def fetch_latest_github_events(
    user_id: str, limit: int = 10, db: AsyncSession = Depends(get_db_session)
):
    # Step 1: Validate user_id format
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Step 2: Fetch user
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Step 3: Fetch GitHub OAuth credentials
    stmt = select(UserOAuth).where(
        UserOAuth.user_id == user.id, UserOAuth.provider == "github"
    )
    result = await db.execute(stmt)
    user_oauth = result.scalar_one_or_none()
    if not user_oauth:
        raise HTTPException(status_code=404, detail="GitHub OAuth not found for user")
    print("user oauth", model_to_dict(user_oauth))
    access_token = decrypt_token(user_oauth.access_token)

    try:
        async with httpx.AsyncClient() as client:
            # Step 4: Get GitHub username using /user
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            user_resp.raise_for_status()
            github_user = user_resp.json()
            username = github_user.get("login")
            if not username:
                raise HTTPException(
                    status_code=500, detail="Unable to fetch GitHub username"
                )

            # Step 5: Fetch public events using the username
            events_resp = await client.get(
                f"https://api.github.com/users/{username}/events/public",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                params={"per_page": min(limit, 100)},
            )
            events_resp.raise_for_status()
            events = events_resp.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"GitHub API error: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # Step 6: Transform events to internal model
    response_events = []
    for event in events:
        try:
            occurred_at = datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            occurred_at = datetime.utcnow()

        response_events.append(
            GitHubEventResponse(
                id=event["id"],
                event_type=event["type"],
                repo_id=event.get("repo", {}).get("id", 0),
                payload=event,
                occurred_at=occurred_at,
                processed=False,
            )
        )

    return EventsResponse(
        message="Latest events fetched successfully from GitHub",
        events=response_events,
    )


@router.get("/all", response_model=EventsResponse)
async def get_user_events(user_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Find user
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch all events for the user
    stmt = (
        select(GitHubEvents)
        .where(GitHubEvents.user_id == user.id)
        .order_by(GitHubEvents.occurred_at.desc())
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    # Map to Pydantic model
    response_events = [
        GitHubEventResponse(
            id=str(event.id),
            event_type=event.event_type,
            repo_id=event.repo_id,
            payload=event.payload,
            occurred_at=event.occurred_at,
            processed=event.processed,
        )
        for event in events
    ]

    return EventsResponse(
        message="Events retrieved successfully", events=response_events
    )


@router.get("/last", response_model=EventsResponse)
async def get_user_latest_events(
    user_id: str, limit: int = 10, db: AsyncSession = Depends(get_db_session)
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Find user
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get GitHub access token
    stmt = select(UserOAuth).where(
        UserOAuth.user_id == user.id, UserOAuth.provider == "github"
    )
    result = await db.execute(stmt)
    user_oauth = result.scalar_one_or_none()

    if not user_oauth:
        raise HTTPException(status_code=404, detail="GitHub OAuth not found for user")

    access_token = decrypt_token(user_oauth.access_token)

    # Fetch recent events from GitHub API with retry logic for rate limits
    async def fetch_with_retry(url, headers, params, retries=3, backoff=2):
        for attempt in range(retries):
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(url, headers=headers, params=params)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", backoff))
                        await asyncio.sleep(retry_after * (2**attempt))
                        continue
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    if attempt == retries - 1:
                        raise HTTPException(
                            status_code=e.response.status_code, detail=str(e)
                        )
                    await asyncio.sleep(backoff * (2**attempt))

    try:
        events = await fetch_with_retry(
            url="https://api.github.com/user/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"per_page": min(limit, 100)},  # GitHub API limit
        )
        print(events)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid GitHub token")
        raise HTTPException(
            status_code=400, detail=f"Failed to fetch GitHub events: {str(e)}"
        )

    response_events = []
    async with httpx.AsyncClient() as client:
        for event in events:
            repo_id = event.get("repo", {}).get("id")
            event_id_gh = event.get("id")

            # Check if event exists
            stmt = select(GitHubEvents).where(GitHubEvents.event_id_gh == event_id_gh)
            result = await db.execute(stmt)
            existing_event = result.scalar_one_or_none()
            if existing_event:
                response_events.append(
                    GitHubEventResponse(
                        id=str(existing_event.id),
                        event_type=existing_event.event_type,
                        repo_id=existing_event.repo_id,
                        payload=existing_event.payload,
                        occurred_at=existing_event.occurred_at,
                        processed=existing_event.processed,
                    )
                )
                continue

            # Fetch or create repository
            stmt = select(Repository).where(Repository.id == repo_id)
            result = await db.execute(stmt)
            repo = result.scalar_one_or_none()
            if not repo:
                repo_data = event.get("repo", {})
                try:
                    repo_response = await client.get(
                        f"https://api.github.com/repos/{repo_data.get('name')}",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    repo_response.raise_for_status()
                    repo_data = repo_response.json()

                    repo = Repository(
                        id=repo_data.get("id"),
                        node_id=repo_data.get("node_id"),
                        name=repo_data.get("name"),
                        full_name=repo_data.get("full_name"),
                        owner_login=repo_data.get("owner", {}).get("login"),
                        owner_type=repo_data.get("owner", {}).get("type").lower(),
                        private=repo_data.get("private", False),
                        default_branch=repo_data.get("default_branch"),
                        description=repo_data.get("description"),
                        language=repo_data.get("language"),
                        topics=repo_data.get("topics", []),
                        homepage=repo_data.get("homepage"),
                        license=repo_data.get("license"),
                        stargazers_count=repo_data.get("stargazers_count", 0),
                        forks_count=repo_data.get("forks_count", 0),
                        created_at_gh=github_ts(repo_data.get("created_at")),
                        updated_at_gh=github_ts(repo_data.get("updated_at")),
                        pushed_at_gh=github_ts(repo_data.get("pushed_at")),
                    )
                    db.add(repo)
                    await db.commit()
                except httpx.HTTPStatusError:
                    continue

            # Store event
            try:
                occurred_at = datetime.strptime(
                    event.get("created_at"), "%Y-%m-%dT%H:%M:%SZ"
                )
            except (ValueError, TypeError):
                occurred_at = datetime.utcnow()

            github_event = GitHubEvents(
                id=uuid.uuid4(),
                user_id=user.id,
                repo_id=repo_id,
                event_type=event.get("type"),
                event_id_gh=event_id_gh,
                payload=event,
                occurred_at=occurred_at,
                processed=False,
            )
            db.add(github_event)
            await db.commit()

            response_events.append(
                GitHubEventResponse(
                    id=str(github_event.id),
                    event_type=github_event.event_type,
                    repo_id=github_event.repo_id,
                    payload=github_event.payload,
                    occurred_at=github_event.occurred_at,
                    processed=github_event.processed,
                )
            )

    return EventsResponse(
        message="Latest events retrieved successfully", events=response_events
    )


@router.get("/repositories", response_model=RepositoriesResponse)
async def list_user_repositories(
    user_id: str, db: AsyncSession = Depends(get_db_session)
):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Find user
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get GitHub access token
    stmt = select(UserOAuth).where(
        UserOAuth.user_id == user.id, UserOAuth.provider == "github"
    )
    result = await db.execute(stmt)
    user_oauth = result.scalar_one_or_none()

    if not user_oauth:
        raise HTTPException(status_code=404, detail="GitHub OAuth not found for user")

    access_token = decrypt_token(user_oauth.access_token)

    # Fetch repositories from GitHub API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"per_page": 100},
            )
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid GitHub token")
            if response.status_code == 429:
                raise HTTPException(
                    status_code=429, detail="GitHub API rate limit exceeded"
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to fetch repositories"
                )
            repos = response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to fetch repositories: {str(e)}"
            )

    response_repos = []
    for repo_data in repos:
        repo_id = repo_data.get("id")
        stmt = select(Repository).where(Repository.id == repo_id)
        result = await db.execute(stmt)
        repo = result.scalar_one_or_none()
        if not repo:
            repo = Repository(
                id=repo_data.get("id"),
                node_id=repo_data.get("node_id"),
                name=repo_data.get("name"),
                full_name=repo_data.get("full_name"),
                owner_login=repo_data.get("owner", {}).get("login"),
                owner_type=repo_data.get("owner", {}).get("type").lower(),
                private=repo_data.get("private", False),
                default_branch=repo_data.get("default_branch"),
                description=repo_data.get("description"),
                language=repo_data.get("language"),
                topics=repo_data.get("topics", []),
                homepage=repo_data.get("homepage"),
                license=repo_data.get("license"),
                stargazers_count=repo_data.get("stargazers_count", 0),
                forks_count=repo_data.get("forks_count", 0),
                created_at_gh=github_ts(repo_data.get("created_at")),
                updated_at_gh=github_ts(repo_data.get("updated_at")),
                pushed_at_gh=github_ts(repo_data.get("pushed_at")),
            )
            db.add(repo)
            await db.commit()

        response_repos.append(
            RepositoryResponse(
                id=repo.id,
                node_id=repo.node_id,
                name=repo.name,
                full_name=repo.full_name,
                owner_login=repo.owner_login,
                owner_type=repo.owner_type,
                private=repo.private,
                default_branch=repo.default_branch,
                description=repo.description,
                language=repo.language,
                topics=repo.topics,
                homepage=repo.homepage,
                license=repo.license,
                stargazers_count=repo.stargazers_count,
                forks_count=repo.forks_count,
                created_at_gh=repo.created_at_gh,
                updated_at_gh=repo.updated_at_gh,
                pushed_at_gh=repo.pushed_at_gh,
            )
        )

    return RepositoriesResponse(
        message="Repositories retrieved successfully", repositories=response_repos
    )
