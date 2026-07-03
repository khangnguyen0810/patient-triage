from src.triage_system.core.state import PatientSessionState
from src.triage_system.tools.rag_tool import DepartmentRAGTool
from src.triage_system.agents.triage_agent import TriageAgent


def test_triage_agent_successfully_recommends_departments():
    initial_state = PatientSessionState(
        patient_id="PT-2026",
        raw_symptoms=["I have sharp chest pain and my heart is beating fast"],
        selected_department=None,
    )
    rag_tool = DepartmentRAGTool()
    agent = TriageAgent(rag_tool=rag_tool)

    updated_state = agent.execute_triage(initial_state)

    assert len(updated_state.recommended_departments) == 2
    assert "Cardiology" in updated_state.recommended_departments
    assert updated_state.patient_id == "PT-2026"
