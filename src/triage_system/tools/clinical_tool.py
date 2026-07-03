from typing import List

class ClinicalPackagesTool:
    def __init__(self):
        self._db = {
            "Cardiology": ["Electrocardiogram (ECG)", "Echocardiogram (Ultrasound)", "Complete Blood Count (CBC)"],
            "Neurology": ["Brain MRI Scan", "Electroencephalogram (EEG)", "Basic Metabolic Panel (BMP)"],
            "Orthopedics": ["X-Ray Imaging", "Physical Joint Assessment"],
            "Gastroenterology": ["Abdominal Ultrasound", "Liver Function Panel Blood Test"],
            "Pulmonology": ["Chest X-Ray", "Spirometry Pulmonary Test", "Arterial Blood Gas"]
        }

    def get_procedures_by_department(self, department: str) -> List[str]:
        return self._db.get(department, ["Standard Physician Consultation"])