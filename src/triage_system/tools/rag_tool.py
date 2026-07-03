from typing import List

class DepartmentRAGTool:
    def __init__(self):
        self._knowledge_base = {
            "Cardiology": ["chest pain", "heart palpitations", "shortness of breath", "high blood pressure"],
            "Neurology": ["severe headache", "dizziness", "numbness", "blurred vision", "seizures"],
            "Orthopedics": ["joint pain", "broken bone", "fracture", "back ache", "sprain"],
            "Gastroenterology": ["stomach pain", "nausea", "acid reflux", "vomiting"],
            "Pulmonology": ["chronic cough", "wheezing", "asthma", "lung congestion"]
        }

    def retrieve_relevant_departments(self, patient_symptoms: List[str], top_k: int = 2) -> List[str]:
        scores = {}
        normalized_symptoms = [s.lower().strip() for s in patient_symptoms]

        for dept, keywords in self._knowledge_base.items():
            matches = sum(1 for symptom in normalized_symptoms if any(kw in symptom for kw in keywords))
            scores[dept] = matches

        sorted_depts = sorted(scores.keys(), key=lambda x: (-scores[x], x))
        
        return sorted_depts[:top_k]