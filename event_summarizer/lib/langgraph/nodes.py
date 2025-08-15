from langgraph.state import EventGraphState


def extract_code_blocks(state: EventGraphState) -> EventGraphState:
    # Traverse event_payload, extract code diffs or patches from each commit/file
    code_blocks = []
    for commit in state["event_payload"].get("essential_data", {}).get("commits", []):
        for file in commit.get("files", []):
            patch = file.get("patch")
            if patch:
                code_blocks.append(patch)
    state["code_blocks"] = code_blocks
    return state


def extract_metadata(state: EventGraphState) -> EventGraphState:
    # Pull author, filenames, ref, PR state, etc.
    meta = {}
    ep = state["event_payload"]["essential_data"]
    meta["actor"] = ep.get("actor_login")
    meta["files"] = (
        [
            f["filename"]
            for commit in ep.get("commits", [])
            for f in commit.get("files", [])
        ]
        if "commits" in ep
        else []
    )
    meta["pr_state"] = ep.get("pr_state")
    meta["branch"] = ep.get("ref")
    state["metadata"] = meta
    return state


def generate_summary(state: EventGraphState) -> EventGraphState:
    # LLM call using event message, meta, code blocks as context
    context = (
        f"Commit messages: {[c.get('message') for c in state['event_payload']['essential_data'].get('commits',[])]}\n"
        f"Code changes: {state.get('code_blocks')}\n"
        f"Metadata: {state.get('metadata')}"
    )
    # Plug into LLM: result = llama3_client.complete(prompt=context) or similar
    result = fake_llm_generate(context)  # replace with real LLM call
    state["summary"] = result["summary"]
    return state


def hallucination_grader_edge(state: EventGraphState):
    # Use a separate LLM or logic to verify faithfulness
    score = hallucination_grader(
        {"summary": state["summary"], "context": state["event_payload"]}
    )
    return "grounded" if score["is_grounded"] else "hallucinates"


def reflect(state: EventGraphState) -> EventGraphState:
    # Adds an instruction for retry and increases the reflection count
    state["retries"] = state.get("retries", 0) + 1
    if not state["reflections"]:
        state["reflections"] = []
    state["reflections"].append(f"Retry prompted at attempt {state['retries']}")
    return state


def max_retries(state: EventGraphState):
    return "eval" if state["retries"] >= 3 else "reflect"


def similarity_evaluator(state: EventGraphState) -> EventGraphState:
    # Optionally retrieve ground truth and compute similarity (embeddings similarity, etc)
    summary = state["summary"]
    # ... get similar summaries, compute embedding similarity ...
    # state['similar_summary'] = ...
    # state['similarity_score'] = ...
    return state
