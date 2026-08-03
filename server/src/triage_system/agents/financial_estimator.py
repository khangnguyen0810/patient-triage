# src/triage_system/agents/financial_estimator.py
from triage_system.core.state import PatientSessionState
from triage_system.tools.finance_tool import FinanceDatabaseTool


class FinancialEstimatorAgent:
    def __init__(self, finance_db_tool: FinanceDatabaseTool):
        self.finance_db_tool = finance_db_tool

    def calculate_cost_estimate(
        self, state: PatientSessionState
    ) -> PatientSessionState:
        """
        Steps 8 & 9: Ingests the validated billing payload, queries rules matrices,
        executes cost breakdown arithmetic, and hydrates final tracking context.
        """
        payload = state.final_billing_payload
        if not payload:
            raise ValueError(
                "State Error: Cannot calculate billing estimation without a final_billing_payload."
            )

        if not state.trace_logs:
            state.trace_logs = {}
        if "finalize-estimate" not in state.trace_logs:
            state.trace_logs["finalize-estimate"] = []
        logs = state.trace_logs["finalize-estimate"]

        logs.append("[FinancialEstimatorAgent] Ingesting validated billing payload...")
        logs.append(
            f"[FinancialEstimatorAgent] Initiating cost calculation for Insurance: '{payload.insurance_provider}'"
        )

        print(
            f"[FEA] Initiating calculation logic for Insurance: '{payload.insurance_provider}'..."
        )

        # 1. Resolve insurance parameters
        logs.append(
            f"[FinanceDatabaseTool] Querying contract coverage rate for provider '{payload.insurance_provider}'..."
        )
        coverage_rate = self.finance_db_tool.lookup_insurance_coverage_rate(
            payload.insurance_provider
        )
        logs.append(
            f"[FinanceDatabaseTool] Provider coverage rate resolved to: {coverage_rate * 100:.1f}%"
        )

        itemized_breakdown: dict[str, float] = {}
        total_gross = 0.0
        total_covered = 0.0

        # 2. Loop through confirmed services and apply line-item arithmetic
        logs.append(
            "[FinancialEstimatorAgent] Running cost arithmetic calculations on confirmed items:"
        )
        for service in payload.confirmed_services:
            logs.append(
                f"[FinanceDatabaseTool] Querying standard unit price for service code '{service.service_code}'..."
            )
            gross_price = self.finance_db_tool.lookup_unit_price(service.service_code)
            logs.append(
                f"[FinanceDatabaseTool] Unit standard rate resolved: ${gross_price:.2f}"
            )

            # Math operations: Covered Amount vs Patient Responsibility
            covered_amount = round(gross_price * coverage_rate, 2)
            patient_responsibility = round(gross_price - covered_amount, 2)

            logs.append(
                f"[FinancialEstimatorAgent] Cost breakdown calculated for '{service.procedure_name}':"
            )
            logs.append(f"  - Gross Rate: ${gross_price:.2f}")
            logs.append(
                f"  - Insurer Portion ({coverage_rate * 100:.1f}%): -${covered_amount:.2f}"
            )
            logs.append(f"  - Out-of-Pocket Cost: ${patient_responsibility:.2f}")

            # Log itemized summary descriptive tracking metrics
            itemized_breakdown[f"{service.procedure_name} (Gross)"] = gross_price
            itemized_breakdown[f"{service.procedure_name} (Insured Covers)"] = (
                covered_amount
            )
            itemized_breakdown[f"{service.procedure_name} (Out-of-Pocket)"] = (
                patient_responsibility
            )

            total_gross += gross_price
            total_covered += covered_amount

        # 3. Compile total calculations
        final_out_of_pocket = round(total_gross - total_covered, 2)
        logs.append("[FinancialEstimatorAgent] Compiling overall transaction totals:")
        logs.append(f"  - Total Gross Rate: ${total_gross:.2f}")
        logs.append(f"  - Total Insurer Coverage: -${total_covered:.2f}")
        logs.append(f"  - Net Out-of-Pocket Cost: ${final_out_of_pocket:.2f}")

        # AI Model Billing & Token Audit
        if state.ai_model_name:
            prompt_cost = state.prompt_tokens * 0.000000075
            candidate_cost = state.candidate_tokens * 0.000000300
            total_ai_cost = prompt_cost + candidate_cost
            
            logs.append("[FinancialEstimatorAgent] Performing LLM Token & Billing Audit:")
            logs.append(f"  - AI Model Evaluated: {state.ai_model_name}")
            logs.append(f"  - Prompt (Input) Tokens: {state.prompt_tokens} (Rate: $0.075 / 1M) -> ${prompt_cost:.6f}")
            logs.append(f"  - Candidate (Output) Tokens: {state.candidate_tokens} (Rate: $0.300 / 1M) -> ${candidate_cost:.6f}")
            logs.append(f"  - Total Calculated Billing Cost: ${total_ai_cost:.6f}")
        else:
            logs.append("[FinancialEstimatorAgent] LLM Token & Billing Audit: No model invocation tracked (fallback direct DB routing was used).")

        # 4. Save results back into our central state tracking machine contract
        state.cost_estimation_breakdown = itemized_breakdown
        state.final_out_of_pocket_cost = final_out_of_pocket

        logs.append(
            "[System] Billing out-of-pocket calculation complete and transaction receipt finalized."
        )

        print(
            f"[FEA] Calculation locked. Final Patient Cost Responsibility: ${state.final_out_of_pocket_cost}"
        )
        return state
