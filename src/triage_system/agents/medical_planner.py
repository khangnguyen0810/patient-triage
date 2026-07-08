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
        """
        Task 2 (Step 7): Deterministic Data Transformation.
        Maps raw procedure selections to static code structures with no AI overhead.
        """
        if not state.confirmed_procedures:
            raise ValueError(
                "Execution Error: Cannot serialize an empty procedure checklist."
            )

        # Hardcoded deterministic corporate mapping index registry
        CODE_REGISTRY = {
            "blood": "SV001",
            "cbc": "SV001",
            "ultrasound": "SV002",
            "echocardiogram": "SV002",
            "x-ray": "SV003",
            "mri": "SV003",
            "imaging": "SV003",
        }

        compiled_services = []

        for procedure in state.confirmed_procedures:
            normalized_name = procedure.lower()
            matched_code = "SV000"

            for keyword, code in CODE_REGISTRY.items():
                if keyword in normalized_name:
                    matched_code = code
                    break

            compiled_services.append(
                ServiceItem(service_code=matched_code, procedure_name=procedure)
            )

        structured_payload = FEABillingPayload(
            registered_department=state.selected_department or "Unknown",
            confirmed_services=compiled_services,
            insurance_provider=state.insurance_details.get("provider", "Self-Pay"),
            insurance_policy_id=state.insurance_details.get("policy_id", "NONE"),
        )

        # Synchronize our primary application state machine contract
        state.final_billing_payload = structured_payload
        return state
