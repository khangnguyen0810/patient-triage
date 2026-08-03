import pytest
from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool
from triage_system.agents.triage_agent import TriageAgent


@pytest.mark.anyio
async def test_triage_agent_successfully_recommends_departments():
    initial_state = PatientSessionState(
        patient_id="PT-2026-X",
        raw_symptoms="I have sharp chest pain and my heart is beating fast",
        selected_department=None,
    )
    rag_tool = DepartmentRAGTool()
    agent = TriageAgent(rag_tool=rag_tool)

    updated_state = await agent.execute_triage(initial_state)

    assert len(updated_state.recommended_departments) == 2
    assert "Cardiology" in updated_state.recommended_departments
    assert updated_state.patient_id == "PT-2026-X"
    assert updated_state.ai_model_name is not None
    assert updated_state.ai_model_name.startswith("gemini-")
    assert updated_state.prompt_tokens > 0
    assert updated_state.candidate_tokens > 0


