# src/triage_system/core/state.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PatientSessionState(BaseModel):
    """
    The unified state contract tracking the patient's entire journey
    across the triage, planning, and billing agents.
    """

    patient_id: str = Field(
        ..., description="Unique identification string for the patient."
    )
    raw_symptoms: List[str] = Field(
        default_factory=list, description="Symptoms explicitly provided by the patient."
    )

    recommended_departments: List[str] = Field(
        default_factory=list,
        description="The top two hospital departments matched via RAG.",
    )
    selected_department: Optional[str] = Field(
        None,
        description="The specific department chosen by the patient for registration.",
    )

    proposed_procedures: List[str] = Field(
        default_factory=list,
        description="List of lab tests or scans recommended by the Medical Planner Agent.",
    )
    confirmed_procedures: List[str] = Field(
        default_factory=list,
        description="The subset of procedures approved by the patient.",
    )
    insurance_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Patient-provided insurance parameters (provider, policy number).",
    )

    cost_estimation_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Itemized price list mapped out by the Financial Agent.",
    )
    final_out_of_pocket_cost: float = Field(
        default=0.0,
        description="The final calculated cost after applying insurance coverage rules.",
    )
