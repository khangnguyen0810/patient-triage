from typing import Dict, Any

class FinanceDatabaseTool:
    def __init__(self):
        # Simulated hospital chargemaster price list index lookup
        self._price_list: Dict[str, float] = {
            "SV001": 150.00,  # Complete Blood Count (CBC)
            "SV002": 350.00,  # Echocardiogram / Ultrasound
            "SV003": 600.00,  # X-Ray / Advanced Imaging
            "SV000": 100.00   # General Consultation / Standard Line Item
        }

        # Simulated insurance policy coverage rules engine matrix
        # Structure maps: Provider -> Coinsurance Coverage % (e.g., 0.80 means insurance pays 80%)
        self._insurance_rules: Dict[str, float] = {
            "bluecross": 0.80,
            "aetna": 0.70,
            "healthcorp": 0.90,
            "self-pay": 0.00
        }

    def lookup_unit_price(self, service_code: str) -> float:
        """Retrieves the gross base charge for a given service code."""
        return self._price_list.get(service_code, self._price_list["SV000"])

    def lookup_insurance_coverage_rate(self, provider_name: str) -> float:
        """Retrieves the coverage matrix calculation value for a provider."""
        normalized_provider = provider_name.lower().strip()
        return self._insurance_rules.get(normalized_provider, 0.00)