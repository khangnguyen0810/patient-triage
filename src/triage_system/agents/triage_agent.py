from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool


class TriageAgent:
    def __init__(self, rag_tool: DepartmentRAGTool):
        self.rag_tool = rag_tool

    def execute_triage(self, state: PatientSessionState) -> PatientSessionState:
        if not state.raw_symptoms:
            raise ValueError(
                "Cannot execute triage pipeline: Patient symptoms list is empty."
            )

        print(
            f"[TriageAgent] Processing symptoms for ID {state.patient_id}: {state.raw_symptoms}"
        )

        matched_departments = self.rag_tool.retrieve_relevant_departments(
            state.raw_symptoms
        )

        state.recommended_departments = matched_departments

        print(f"[TriageAgent] Recommended Departments: {state.recommended_departments}")
        return state
