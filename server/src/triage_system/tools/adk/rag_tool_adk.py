# src/triage_system/tools/rag_tool_adk.py
from triage_system.tools.rag_tool import DepartmentRAGTool

_rag_tool_instance = DepartmentRAGTool()


def retrieve_relevant_departments(query: str, top_k: int = 5) -> dict:
    """Searches the hospital department knowledge base for departments relevant
    to a symptom description. Call this with a focused symptom phrase. If results
    look weak or symptoms span multiple systems, call again with a reformulated
    or more specific query (e.g. separate calls for 'chest pain' and 'numbness in arm').

    Args:
        query: A symptom-focused search phrase.
        top_k: Number of candidate departments to retrieve (default 5).

    Returns:
        A dict with a "status" key and a "results" list of
        {"department_name": str, "distance": float} matches, ordered by relevance
        (lower distance = better match).
    """
    matches = _rag_tool_instance.retrieve_relevant_departments(query, top_k=top_k)
    if not matches:
        return {"status": "no_results", "results": []}
    return {"status": "success", "results": matches}
