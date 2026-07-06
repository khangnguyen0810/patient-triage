# src/triage_system/main.py
import sys
from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from triage_system.agents.triage_agent import TriageAgent
from triage_system.agents.medical_planner import MedicalPlannerAgent


def run_interactive_demo():
    print("=== STARTING PATIENT TRIAGE POE ORCHESTRATOR ===")

    rag_tool = DepartmentRAGTool()
    clinical_tool = ClinicalPackagesTool()

    triage_agent = TriageAgent(rag_tool=rag_tool)
    medical_planner = MedicalPlannerAgent(clinical_tool=clinical_tool)

    print("\n[Step 1] Ingesting patient parameters...")
    session_state = PatientSessionState(
        patient_id="PT-7721",
        raw_symptoms=[
            "I have sharp chest pain spreading to my arm, and I am feeling very dizzy."
        ],
    )  # type: ignore

    print("\n[Step 2] Triggering Triage Agent RAG evaluations...")
    session_state = triage_agent.execute_triage(session_state)

    print(f"\n--- [Step 3: HUMAN INTERRUPT GATEWAY] ---")
    print(f"Recommended Departments on Screen: {session_state.recommended_departments}")

    print("Please type one of the recommended departments to choose it:")
    user_choice = input(">> ").strip()

    session_state.selected_department = user_choice
    print(
        f"State successfully mutated. 'selected_department' locked to: {session_state.selected_department}"
    )

    print("\n[Step 4 & 5] Activating Medical Planner Agent (Conversational Mode)...")
    screen_output = medical_planner.generate_proposals_explanation(session_state)

    print("\n=== PATIENT SCREEN DISPLAY OUTPUT ===")
    print(screen_output)
    print("=======================================")


if __name__ == "__main__":
    run_interactive_demo()
