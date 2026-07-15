# src/triage_system/main.py
import os
from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from triage_system.tools.finance_tool import FinanceDatabaseTool
from triage_system.agents.triage_agent import TriageAgent
from triage_system.agents.medical_planner import MedicalPlannerAgent
from dotenv import load_dotenv
from triage_system.agents.financial_estimator import FinancialEstimatorAgent

load_dotenv()


def run_pipeline():
    print("=== STARTING AGENTIC TRIAGE & MEDICAL PLANNING DEMO ===\n")

    # 1. Initialize Root Tracking State (Step 1)
    session_state = PatientSessionState(
        patient_id="PT-2026-X",
        raw_symptoms=["c"],  # type: ignore
    )

    # 2. Wire Infrastructure & Inject Stateful Tools
    rag_tool = DepartmentRAGTool()
    clinical_tool = ClinicalPackagesTool()
    finance_db = FinanceDatabaseTool()

    triage_agent = TriageAgent(rag_tool=rag_tool)
    medical_planner = MedicalPlannerAgent(clinical_tool=clinical_tool)
    financial_estimator = FinancialEstimatorAgent(finance_db_tool=finance_db)

    # 3. Step 2: Run Triage Agent
    print(f"[Step 1 & 2] Running Triage Agent RAG Routing...")
    session_state = triage_agent.execute_triage(session_state)

    # 4. Step 3: Human-in-the-Loop Interruption Simulation
    print(f"Recommended Departments: {session_state.recommended_departments}")

    print("Enter the department you wish to register for:")
    selected_dept = input(">> ").strip()

    session_state.selected_department = selected_dept
    print(
        f"\n[Step 3] Choice Locked. State updated: selected_department = '{session_state.selected_department}'"
    )

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

    print(f"DISPLAY ON PATIENT SCREEN (PROPOSED PLAN): {explanation}")

    print("[Step 6] USER INTERACTION FIELD")
    print("Please type the tests you want to confirm (separated by commas):")

    user_confirmation = input(">> ").strip()

    selected_indices = [
        int(i.strip()) for i in user_confirmation.split(",") if i.strip().isdigit()
    ]

    session_state.confirmed_procedures = [
        session_state.proposed_procedures[i - 1]
        for i in selected_indices
        if 1 <= i <= len(session_state.proposed_procedures)
    ]

    print("Enter your Insurance Provider Name (e.g., BlueCross):")
    ins_provider = input(">> ").strip()
    print("Enter your Alphanumeric Insurance Policy Number:")
    ins_id = input(">> ").strip()

    session_state.insurance_details = {"provider": ins_provider, "policy_id": ins_id}

    print(
        "\n[Step 7] Passing confirmed choices to MPA AI Agent for strict billing serialization..."
    )
    session_state = medical_planner.serialize_billing_payload(session_state)

    print("\n========================================================")
    print("FINAL STRUCTURED TARGET OBJECT READY FOR TRANSMISSION TO FEA:")
    print("========================================================")
    print(session_state.final_billing_payload.model_dump_json(indent=2))  # type: ignore
    print("========================================================")

    print("\n========================================================")
    print("[Step 8 + 9 + 10] PATIENT RECEIPT AND FINAL COST ESTIMATE SUMMARY]")
    print("========================================================")
    print(f"Patient Tracking Reference: {session_state.patient_id}")
    print(f"Target Department:          {session_state.selected_department}")
    print(
        f"Carrier Network:            {session_state.final_billing_payload.insurance_provider if session_state.final_billing_payload else 'N/A'}"
    )
    print("--------------------------------------------------------")
    session_state = financial_estimator.calculate_cost_estimate(session_state)
    print("Itemized Financial Breakdown Details:")
    if session_state.cost_estimation_breakdown:
        for (
            transaction_item,
            dollar_value,
        ) in session_state.cost_estimation_breakdown.items():
            print(f"  {transaction_item:<40}: ${dollar_value:>8.2f}")
    print("--------------------------------------------------------")
    print(
        f"FINAL PATIENT OUT-OF-POCKET ESTIMATE:        ${session_state.final_out_of_pocket_cost:>8.2f}"
    )
    print("========================================================")


if __name__ == "__main__":
    run_pipeline()
