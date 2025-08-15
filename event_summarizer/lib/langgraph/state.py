from typing import TypedDict, Optional, List, Dict, Any


class EventGraphState(TypedDict):
    summary: str  # Generated summary text
    event_payload: dict  # The full GitHub event (already cleaned/enriched)
    code_blocks: Optional[List[str]]  # Extracted code blocks (diffs, patches)
    metadata: Optional[
        Dict[str, Any]
    ]  # Extra event metadata (files changed, PR state, etc.)
    similar_summary: Optional[
        str
    ]  # Nearest retrieved known summary (optional, for eval)
    similar_id: Optional[str]
    retries: int
    reflections: Optional[List[str]]
    similarity_score: Optional[float]
