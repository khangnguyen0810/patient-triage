from sqlalchemy import text
from triage_system.db import SessionLocal


class FinanceDatabaseTool:
    def lookup_unit_price(self, service_code: str) -> float:
        with SessionLocal() as session:
            row = session.execute(
                text("SELECT unit_price FROM service_codes WHERE code = :code"),
                {"code": service_code},
            ).fetchone()
        if row:
            return float(row[0])
        fallback = session.execute(
            text("SELECT unit_price FROM service_codes WHERE code = 'SV000'")
        ).fetchone()
        return float(fallback[0])

    def lookup_insurance_coverage_rate(self, provider_name: str) -> float:
        normalized_provider = provider_name.lower().strip()
        with SessionLocal() as session:
            row = session.execute(
                text(
                    "SELECT coverage_rate FROM insurance_rules WHERE provider = :provider"
                ),
                {"provider": normalized_provider},
            ).fetchone()
        return float(row[0]) if row else 0.00
