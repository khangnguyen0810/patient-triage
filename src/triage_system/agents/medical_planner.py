from triage_system.core.state import PatientSessionState
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from google import genai
from google.genai import types


class MedicalPlannerAgent:
    def __init__(self, clinical_tool: ClinicalPackagesTool):
        self.clinical_tool = clinical_tool

    def propose_medical_plan(self, state: PatientSessionState) -> PatientSessionState:
        if not state.selected_department:
            raise ValueError("State Error: Cannot execute planner without a selected_department.")
        state.proposed_procedures = self.clinical_tool.fetch_department_examination_packages(state.selected_department)
        

        
        return state
        

