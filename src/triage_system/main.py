import sys
from triage_system.triage.service import TriageService


class TriageController:
    def __init__(self, triage_service: TriageService):
        self.triage_service = triage_service

    def process_incoming_patient(self, patient_name: str, symptoms: list[str]) -> dict:
        print(f"[Core Engine] Beginning ingestion for candidate: {patient_name}...")

        priority = self.triage_service.evaluate_priority(symptoms)

        print(f"[Core Engine] Sorting logic locked. Tier set to: {priority}")
        return {"patient": patient_name, "tier": priority, "status": "PROCESSED"}


def run_pipeline():
    triage_engine = TriageService()
    orchestrator = TriageController(triage_service=triage_engine)

    result = orchestrator.process_incoming_patient(
        patient_name="John Doe", symptoms=["chest_pain", "shortness_of_breath"]
    )
    print(f"[Output Result Summary]: {result}")


if __name__ == "__main__":
    run_pipeline()
