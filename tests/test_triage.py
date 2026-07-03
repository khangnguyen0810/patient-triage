from src.triage_system.triage.service import TriageService


def test_triage_priority_calculation():
    service = TriageService()

    assert service.evaluate_priority(["chest_pain"]) == "RED"

    assert service.evaluate_priority(["stubbed_toe"]) == "GREEN"
