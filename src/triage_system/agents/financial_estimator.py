# src/triage_system/agents/financial_estimator.py
from triage_system.core.state import PatientSessionState
from triage_system.tools.finance_tool import FinanceDatabaseTool

class FinancialEstimatorAgent:
    def __init__(self, finance_db_tool: FinanceDatabaseTool):
        self.finance_db_tool = finance_db_tool

    def calculate_cost_estimate(self, state: PatientSessionState) -> PatientSessionState:
        """
        Steps 8 & 9: Ingests the validated billing payload, queries rules matrices,
        executes cost breakdown arithmetic, and hydrates final tracking context.
        """
        payload = state.final_billing_payload
        if not payload:
            raise ValueError("State Error: Cannot calculate billing estimation without a final_billing_payload.")

        print(f"[FEA] Initiating calculation logic for Insurance: '{payload.insurance_provider}'...")

        # 1. Resolve insurance parameters
        coverage_rate = self.finance_db_tool.lookup_insurance_coverage_rate(payload.insurance_provider)
        
        itemized_breakdown: dict[str, float] = {}
        total_gross = 0.0
        total_covered = 0.0

        # 2. Loop through confirmed services and apply line-item arithmetic
        for service in payload.confirmed_services:
            gross_price = self.finance_db_tool.lookup_unit_price(service.service_code)
            
            # Math operations: Covered Amount vs Patient Responsibility
            covered_amount = round(gross_price * coverage_rate, 2)
            patient_responsibility = round(gross_price - covered_amount, 2)

            # Log itemized summary descriptive tracking metrics
            itemized_breakdown[f"{service.procedure_name} (Gross)"] = gross_price
            itemized_breakdown[f"{service.procedure_name} (Insured Covers)"] = covered_amount
            itemized_breakdown[f"{service.procedure_name} (Out-of-Pocket)"] = patient_responsibility

            total_gross += gross_price
            total_covered += covered_amount

        # 3. Compile total calculations
        final_out_of_pocket = round(total_gross - total_covered, 2)

        # 4. Save results back into our central state tracking machine contract
        state.cost_estimation_breakdown = itemized_breakdown
        state.final_out_of_pocket_cost = final_out_of_pocket

        print(f"[FEA] Calculation locked. Final Patient Cost Responsibility: ${state.final_out_of_pocket_cost}")
        return state