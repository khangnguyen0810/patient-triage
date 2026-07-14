import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import your exact tools, agents, and state model verbatim
from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from triage_system.tools.finance_tool import FinanceDatabaseTool
from triage_system.agents.triage_agent import TriageAgent
from triage_system.agents.medical_planner import MedicalPlannerAgent
from triage_system.agents.financial_estimator import FinancialEstimatorAgent

load_dotenv()

app = FastAPI(
    title="Patient Triage API",
    description="State-passing REST wrapper for agentic pipeline",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your front-end URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Initialize tools and agents globally once when server starts
rag_tool = DepartmentRAGTool()
clinical_tool = ClinicalPackagesTool()
finance_db = FinanceDatabaseTool()

triage_agent = TriageAgent(rag_tool=rag_tool)
medical_planner = MedicalPlannerAgent(clinical_tool=clinical_tool)
financial_estimator = FinancialEstimatorAgent(finance_db_tool=finance_db)


# --- API ENDPOINTS ---


@app.post("/api/pipeline/initialize", response_model=PatientSessionState)
async def initialize_pipeline(raw_symptoms: str = Body(...)):
    """
    Step 1 & 2: Initiates a brand new session state and runs the Triage Agent.
    """
    try:
        # Create a fresh state with a unique identifier
        session_state = PatientSessionState(
            patient_id="PT-2026-X",  # You can generate dynamic IDs here later
            raw_symptoms=raw_symptoms,
        )  # type: ignore
        # Execute triage agent
        updated_state = await triage_agent.execute_triage(session_state)
        return updated_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/propose-plan", response_model=PatientSessionState)
async def propose_plan(state: PatientSessionState):
    """
    Steps 4 & 5: Accepts the state (which now contains frontend-selected department),
    and runs the Medical Planner Agent to populate proposed procedures.
    """
    try:
        if not state.selected_department:
            raise HTTPException(
                status_code=400,
                detail="selected_department must be set in the state before this step.",
            )

        updated_state = medical_planner.propose_medical_plan(state)
        return updated_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/finalize-estimate", response_model=PatientSessionState)
async def finalize_estimate(state: PatientSessionState):
    """
    Steps 7, 8, 9 & 10: Accepts the state (which now contains confirmed procedures
    and insurance details from frontend), runs serialization and financial estimation.
    """
    try:
        if not state.confirmed_procedures or not state.insurance_details:
            raise HTTPException(
                status_code=400,
                detail="Confirmed procedures and insurance details must be filled.",
            )

        # Serialize billing payload
        state = medical_planner.serialize_billing_payload(state)
        # Calculate final cost breakdowns
        final_state = financial_estimator.calculate_cost_estimate(state)

        return final_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
