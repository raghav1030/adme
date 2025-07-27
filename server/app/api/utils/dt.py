from datetime import datetime, timezone


def github_ts(dt_str: str | None) -> datetime | None:
    """GitHub ISO-8601 string -> naive UTC datetime."""
    if not dt_str:
        return None
    try:
        # Parse then strip tzinfo to stay naive
        return (
            datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            .replace(tzinfo=None)  # ← make it naive
        )
    except ValueError:
        return None
