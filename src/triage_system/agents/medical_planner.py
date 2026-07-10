from triage_system.core.state import PatientSessionState, FEABillingPayload, ServiceItem
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from google import genai
from google.genai import types


class MedicalPlannerAgent:
    def __init__(self, clinical_tool: ClinicalPackagesTool):
        self.clinical_tool = clinical_tool

    def propose_medical_plan(self, state: PatientSessionState) -> PatientSessionState:
        if not state.selected_department:
            raise ValueError(
                "State Error: Cannot execute planner without a selected_department."
            )
        state.proposed_procedures = (
            self.clinical_tool.fetch_department_examination_packages(
                state.selected_department
            )
        )

        return state

    def serialize_billing_payload(
        self, state: PatientSessionState
    ) -> PatientSessionState:
        if not state.confirmed_procedures:
            raise ValueError(
                "Execution Error: Cannot serialize an empty procedure checklist."
            )

        CODE_REGISTRY = self.clinical_tool.get_service_code()

        structured_payload = self.clinical_tool.build_json_payload(state)

        state.final_billing_payload = structured_payload
        return state
