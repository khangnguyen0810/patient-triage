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

        if not state.trace_logs:
            state.trace_logs = {}
        state.trace_logs["propose-plan"] = []
        logs = state.trace_logs["propose-plan"]

        logs.append(
            f"[MedicalPlannerAgent] Proposing clinical plan for department: '{state.selected_department}'"
        )
        logs.append(
            f"[ClinicalPackagesTool] Querying SQL database for clinical packages..."
        )

        state.proposed_procedures = (
            self.clinical_tool.fetch_department_examination_packages(
                state.selected_department
            )
        )

        logs.append(
            f"[ClinicalPackagesTool] Database query resolved. Found {len(state.proposed_procedures)} medical package(s):"
        )
        for proc in state.proposed_procedures:
            logs.append(f"  - {proc}")

        logs.append(
            "[MedicalPlannerAgent] Recommendations successfully saved to active session state."
        )
        return state

    def serialize_billing_payload(
        self, state: PatientSessionState
    ) -> PatientSessionState:
        if not state.confirmed_procedures:
            raise ValueError(
                "Execution Error: Cannot serialize an empty procedure checklist."
            )

        if not state.trace_logs:
            state.trace_logs = {}
        state.trace_logs["finalize-estimate"] = []
        logs = state.trace_logs["finalize-estimate"]

        logs.append(
            "[MedicalPlannerAgent] Serializing clinic procedures into FEABillingPayload..."
        )
        logs.append(
            f"[MedicalPlannerAgent] Ingested procedures for serialization: {state.confirmed_procedures}"
        )

        logs.append(
            "[ClinicalPackagesTool] Resolving billing service codes via dictionary lookup:"
        )
        for proc in state.confirmed_procedures:
            code = self.clinical_tool.get_service_code(proc)
            logs.append(f"  - {proc} -> Service Code: {code}")

        structured_payload = self.clinical_tool.build_json_payload(state)

        logs.append(f"[MedicalPlannerAgent] FEABillingPayload generated successfully:")
        logs.append(
            f"  - Registered Department: {structured_payload.registered_department}"
        )
        logs.append(f"  - Insurance Carrier: {structured_payload.insurance_provider}")
        logs.append(f"  - Policy Identifier: {structured_payload.insurance_policy_id}")

        state.final_billing_payload = structured_payload
        return state
