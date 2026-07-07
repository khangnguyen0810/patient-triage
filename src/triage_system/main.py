# src/triage_system/main.py
import os
from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from triage_system.agents.triage_agent import TriageAgent
from triage_system.agents.medical_planner import MedicalPlannerAgent
from dotenv import load_dotenv

load_dotenv()

def run_pipeline():
    print("=== STARTING AGENTIC TRIAGE & MEDICAL PLANNING DEMO ===\n")
    
    # 1. Initialize Root Tracking State (Step 1)
    session_state = PatientSessionState(
        patient_id="PT-2026-X",
        raw_symptoms=["I have persistent stomach pain, severe cramps, and I feel nauseous after eating."]
    )
    
    # 2. Wire Infrastructure & Inject Stateful Tools
    rag_tool = DepartmentRAGTool()
    clinical_tool = ClinicalPackagesTool(state=session_state) # Injected Session State Reference
    
    triage_agent = TriageAgent(rag_tool=rag_tool)
    medical_planner = MedicalPlannerAgent(clinical_tool=clinical_tool)
    
    # 3. Step 2: Run Triage Agent
    print(f"[Step 1 & 2] Running Triage Agent RAG Routing...")
    session_state = triage_agent.execute_triage(session_state)
    
    # 4. Step 3: Human-in-the-Loop Interruption Simulation
    print("\n--------------------------------------------------")
    print(f"DISPLAY ON PATIENT SCREEN: Recommended Departments: {session_state.recommended_departments}")
    print("--------------------------------------------------")
    
    # Accept user command-line input to simulate clicking a UI element
    print("Enter the department you wish to register for:")
    selected_dept = input(">> ").strip()
    
    # Save the human choice to our unified state architecture
    session_state.selected_department = selected_dept
    print(f"\n[Step 3] Choice Locked. State updated: selected_department = '{session_state.selected_department}'")
    
    # 5. Steps 4 & 5: Run Medical Planner Agent
    print(f"\n[Step 4 & 5] Activating Medical Planner Agent...")
    explanation = (
            f"Based on your symptoms and registration in the *{session_state.selected_department}* department, "
            f"the Medical Planner Agent recommends the following diagnostic items:\n"
        )
    session_state = medical_planner.propose_medical_plan(session_state)

    for proc in session_state.proposed_procedures:
            explanation += f" - [ ] {proc}\n"

    explanation += (
            "\nThese specific tests help our clinical specialists construct an accurate "
            "assessment. Please confirm these items and provide your insurance details to proceed."
        )
    
    print("\n--------------------------------------------------")
    print("DISPLAY ON PATIENT SCREEN (PROPOSED PLAN):")
    print(explanation)
    print("--------------------------------------------------")
    
if __name__ == "__main__":
    run_pipeline()