from typing import List
from triage_system.core.state import PatientSessionState


class ClinicalPackagesTool:
    def __init__(self):
        """
        Injects the session state so that when Gemini triggers this tool,
        the retrieved items are simultaneously tracked in our state system.
        """
        self._package_db = {
            "Cardiology": [
                "Electrocardiogram (ECG)",
                "Echocardiogram (Heart Ultrasound)",
                "Complete Blood Count (CBC)",
            ],
            "Neurology": [
                "Brain MRI Scan",
                "Electroencephalogram (EEG)",
                "Basic Metabolic Panel (BMP)",
            ],
            "Orthopedics": ["X-Ray Imaging", "Physical Joint Mobility Assessment"],
            "Gastroenterology": [
                "Abdominal Ultrasound",
                "Liver Function Panel Blood Test",
                "H. Pylori Stool Test",
            ],
            "Pulmonology": [
                "Chest X-Ray",
                "Spirometry Pulmonary Test",
                "Arterial Blood Gas",
            ],
        }

    def fetch_department_examination_packages(self, department: str) -> List[str]:
        procedures = self._package_db.get(
            department, ["Standard General Physician Consultation"]
        )

        return procedures
