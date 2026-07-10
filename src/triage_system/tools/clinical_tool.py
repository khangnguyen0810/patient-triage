from typing import List
from triage_system.core.state import PatientSessionState, FEABillingPayload, ServiceItem


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

    def get_service_code(self):
        CODE_REGISTRY = {
            "blood": "SV001",
            "cbc": "SV001",
            "ultrasound": "SV002",
            "echocardiogram": "SV002",
            "x-ray": "SV003",
            "mri": "SV003",
            "imaging": "SV003",
        }
        return CODE_REGISTRY

    def build_json_payload(self, state: PatientSessionState) -> FEABillingPayload:
        CODE_REGISTRY = self.get_service_code()
        compiled_services = []

        for procedure in state.confirmed_procedures:
            normalized_name = procedure.lower()
            matched_code = "SV000"

            for keyword, code in CODE_REGISTRY.items():
                if keyword in normalized_name:
                    matched_code = code
                    break

            compiled_services.append(
                ServiceItem(service_code=matched_code, procedure_name=procedure)
            )

        structured_payload = FEABillingPayload(
            registered_department=state.selected_department or "Unknown",
            confirmed_services=compiled_services,
            insurance_provider=state.insurance_details.get("provider", "Self-Pay"),
            insurance_policy_id=state.insurance_details.get("policy_id", "NONE"),
        )

        return structured_payload
