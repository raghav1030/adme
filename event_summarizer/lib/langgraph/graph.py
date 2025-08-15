from langgraph import workflow

# Node implementations — see below!
workflow.add_node("extract_code", extract_code_blocks)
workflow.add_node("extract_meta", extract_metadata)
workflow.add_node("summary", generate_summary)
workflow.add_node("hallucination", hallucination_grader)
workflow.add_node("reflect", reflect)
workflow.add_node("retry", generate_summary)
workflow.add_node("evaluator", similarity_evaluator)

workflow.set_entry_point("extract_code")
workflow.add_edge("extract_code", "extract_meta")
workflow.add_edge("extract_meta", "summary")
workflow.add_conditional_edges(
    "summary",
    hallucination_grader_edge,
    {"grounded": "evaluator", "hallucinates": "retry"},
)
workflow.add_conditional_edges(
    "retry", max_retries, {"reflect": "reflect", "eval": "evaluator"}
)
workflow.add_edge("reflect", "summary")
workflow.add_edge("evaluator", "END")
