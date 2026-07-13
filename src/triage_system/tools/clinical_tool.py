from typing import List
from sqlalchemy import text
from triage_system.db import SessionLocal
from triage_system.core.state import PatientSessionState, FEABillingPayload, ServiceItem


class ClinicalPackagesTool:
    def fetch_department_examination_packages(self, department: str) -> List[str]:
        with SessionLocal() as session:
            rows = session.execute(
                text("""
                    SELECT p.name
                    FROM procedures p
                    JOIN departments d ON p.department_id = d.id
                    WHERE d.name = :department
                """),
                {"department": department},
            ).fetchall()

        if not rows:
            return ["Standard General Physician Consultation"]
        return [row[0] for row in rows]

    def get_service_code(self, procedure_name: str) -> str:
        with SessionLocal() as session:
            row = session.execute(
                text("SELECT service_code FROM procedures WHERE name = :name"),
                {"name": procedure_name},
            ).fetchone()
        return row[0] if row else "SV000"

    def build_json_payload(self, state: PatientSessionState) -> FEABillingPayload:
        compiled_services = [
            ServiceItem(
                service_code=self.get_service_code(procedure),
                procedure_name=procedure,
            )
            for procedure in state.confirmed_procedures
        ]

        return FEABillingPayload(
            registered_department=state.selected_department or "Unknown",
            confirmed_services=compiled_services,
            insurance_provider=state.insurance_details.get("provider", "Self-Pay"),
            insurance_policy_id=state.insurance_details.get("policy_id", "NONE"),
        )
