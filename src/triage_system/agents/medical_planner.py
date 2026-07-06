from triage_system.core.state import PatientSessionState


class MedicalPlannerAgent:
    def __init__(self, clinical_tool):
        self.clinical_tool = clinical_tool

    def generate_proposals_explanation(self, state: PatientSessionState) -> str:
        dept = state.selected_department
        if not dept:
            raise ValueError(
                "State Error: Cannot propose medical plans without a selected_department."
            )
        procedures = self.clinical_tool.get_procedures_by_department(dept)

        state.proposed_procedures = procedures

        explanation = (
            f"Based on your symptoms and registration in the *{dept}* department, "
            f"the Medical Planner Agent recommends the following diagnostic items:\n"
        )

        for proc in procedures:
            explanation += f" - [ ] {proc}\n"

        explanation += (
            "\nThese specific tests help our clinical specialists construct an accurate "
            "assessment. Please confirm these items and provide your insurance details to proceed."
        )
        return explanation
