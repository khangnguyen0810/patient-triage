from triage_system.agents.medical_planner import MedicalPlannerAgent
from triage_system.core.state import PatientSessionState
from triage_system.tools.clinical_tool import ClinicalPackagesTool


def test_medical_planner_successfully_fetch_packages():
    initial_state = PatientSessionState(
        patient_id="PT-2026",
        raw_symptoms=["I have sharp chest pain and my heart is beating fast"],
        selected_department="Cardiology",
    )  # type: ignore

    clinical_tool = ClinicalPackagesTool(state=initial_state)
    medical_planner = MedicalPlannerAgent(clinical_tool=clinical_tool)
    updated_state = medical_planner.propose_medical_plan(initial_state)
    assert len(updated_state.proposed_procedures) == 3
    assert initial_state.proposed_procedures == [
        "Electrocardiogram (ECG)",
        "Echocardiogram (Heart Ultrasound)",
        "Complete Blood Count (CBC)",
    ]


# tests/test_medical_planner.py
from triage_system.core.state import PatientSessionState
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from triage_system.agents.medical_planner import MedicalPlannerAgent


def test_mpa_transforms_billing_payload_deterministically():
    # Arrange
    initial_state = PatientSessionState(
        patient_id="PT-2026-X",
        raw_symptoms=[
            "I have persistent stomach pain, severe cramps, and I feel nauseous after eating."
        ],  # type: ignore
    )
    tool = ClinicalPackagesTool(state=initial_state)
    agent = MedicalPlannerAgent(clinical_tool=tool)

    state = PatientSessionState(patient_id="PT-MOCK")  # type: ignore
    state.selected_department = "Gastroenterology"
    state.confirmed_procedures = ["Abdominal Ultrasound", "Complete Blood Count (CBC)"]
    state.insurance_details = {"provider": "Aetna", "policy_id": "AE-992"}

    # Act
    payload = agent.serialize_billing_payload(state)

    # Assert
    assert payload.registered_department == "Gastroenterology"
    assert payload.insurance_provider == "Aetna"
    assert len(payload.confirmed_services) == 2

    # Verify deterministic code lookup accuracy
    assert payload.confirmed_services[0].service_code == "SV002"  # Ultrasound
    assert payload.confirmed_services[1].service_code == "SV001"  # CBC
