class TriageService:
    def __init__(self):
        pass

    def evaluate_priority(self, conditions: list[str]) -> str:
        if "chest_pain" in conditions:
            return "RED"
        return "GREEN"
