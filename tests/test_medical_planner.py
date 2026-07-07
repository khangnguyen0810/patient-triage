from triage_system.agents.medical_planner import MedicalPlannerAgent
from triage_system.core.state import PatientSessionState
from triage_system.tools.clinical_tool import ClinicalPackagesTool

def test_medical_planner_successfully_fetch_packages():
    initial_state = PatientSessionState(
        patient_id="PT-2026",
        raw_symptoms=["I have sharp chest pain and my heart is beating fast"],
        selected_department="Cardiology",
    ) # type: ignore

    clinical_tool = ClinicalPackagesTool(state=initial_state)
    medical_planner = MedicalPlannerAgent(clinical_tool=clinical_tool)
    updated_state = medical_planner.propose_medical_plan(initial_state)
    assert len(updated_state.selected_department) == 3
    assert initial_state.proposed_procedures == ['Electrocardiogram (ECG)', 'Echocardiogram (Heart Ultrasound)', 'Complete Blood Count (CBC)']