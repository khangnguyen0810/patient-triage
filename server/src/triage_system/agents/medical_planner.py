from triage_system.core.state import PatientSessionState, FEABillingPayload, ServiceItem
from triage_system.tools.clinical_tool import ClinicalPackagesTool
from google import genai
from google.genai import types


PROCEDURE_METADATA_MAP = {
    "Electrocardiogram (ECG)": {
        "plain_name": "Heart Electrical Rhythm Test",
        "simplified_explanation": "A quick, painless test using small sensors on your chest to record your heart's electrical pulses and detect irregular beats or acute cardiac stress.",
        "exclusions_plain": "Covers basic 12-lead electrical tracing. Does not cover continuous Holter monitoring or invasive cardiac catheterization.",
        "priority_1_keywords": ["chest pain", "heart", "beating fast", "palpitations", "cardiac", "arm pain"],
    },
    "Echocardiogram (Heart Ultrasound)": {
        "plain_name": "Heart Ultrasound Imaging",
        "simplified_explanation": "A non-invasive soundwave scan creating live 3D moving pictures of your heart's valves and chambers to evaluate pumping strength and structural flow.",
        "exclusions_plain": "Standard transthoracic ultrasound included. Transesophageal endoscopic probes or contrast dye injections require separate pre-authorization.",
        "priority_1_keywords": ["chest pain", "short of breath", "breath", "valve", "heart failure"],
    },
    "Complete Blood Count (CBC)": {
        "plain_name": "Comprehensive Blood Health Panel",
        "simplified_explanation": "Measures red blood cells, white blood cells, and platelets to check for hidden infections, systemic inflammation, or anemia compounding your symptoms.",
        "exclusions_plain": "Covers standard blood cell counts. Advanced genetic biomarker panels or specialized clotting factor assays are excluded.",
        "priority_1_keywords": ["fever", "infection", "bleeding", "fatigue"],
    },
    "MRI Brain Scan": {
        "plain_name": "High-Detail Brain Tissue Scan",
        "simplified_explanation": "Uses magnetic fields and radio waves to take high-resolution cross-section images of brain tissue, ruling out structural lesions or vascular nerve compression.",
        "exclusions_plain": "Covers non-contrast brain MRI. Intravenous gadolinium contrast agents or functional neuro-imaging require additional copay clearance.",
        "priority_1_keywords": ["headache", "throbbing", "migraine", "stiffness", "numbness", "vision"],
    },
    "CT Head Scan": {
        "plain_name": "Fast Computerized Head X-Ray",
        "simplified_explanation": "A rapid computer-guided X-ray scan that detects internal skull bleeding, acute fluid buildup, or tissue swelling in emergency scenarios.",
        "exclusions_plain": "Covers acute head CT without contrast. Angiography vascular reconstruction or repeated follow-up scans require secondary review.",
        "priority_1_keywords": ["trauma", "fall", "bleeding", "stroke", "sudden"],
    },
    "Neurological Exam": {
        "plain_name": "Nerve & Reflex Assessment",
        "simplified_explanation": "A physical evaluation by a specialist testing your nerve reflexes, muscle strength, eye movement, and sensory response to pinpoint neurological triggers.",
        "exclusions_plain": "Includes clinical physical exam. Specialized nerve conduction velocity (NCV) or electromyography (EMG) needle testing is excluded.",
        "priority_1_keywords": ["light sensitivity", "neck", "dizziness", "balance", "tingling"],
    },
    "Abdominal Ultrasound": {
        "plain_name": "Stomach & Organ Soundwave Scan",
        "simplified_explanation": "A gentle ultrasound scan examining your stomach, liver, gallbladder, and kidneys to identify gallstones, organ swelling, or abdominal fluid.",
        "exclusions_plain": "Covers upper abdominal organ screening. Pelvic organs or interventional biopsy guidance require dedicated ordering.",
        "priority_1_keywords": ["cramps", "abdominal", "bloating", "nausea", "stomach", "pain"],
    },
    "Endoscopy (EGD)": {
        "plain_name": "Upper Digestive Tract Visual Exam",
        "simplified_explanation": "Uses a tiny camera on a flexible tube to inspect the lining of your food pipe, stomach, and upper intestine for ulcers or tissue irritation.",
        "exclusions_plain": "Includes diagnostic mucosal inspection. Tissue biopsy pathology fees or therapeutic polyp removal are billed under surgical add-ons.",
        "priority_1_keywords": ["ulcer", "vomiting", "severe cramps", "reflux", "swallowing"],
    },
    "Stool Analysis & Culture": {
        "plain_name": "Digestive Infection & Flora Test",
        "simplified_explanation": "Lab testing of digestive samples to check for harmful bacterial infections, parasitic activity, or microscopic digestive blood loss.",
        "exclusions_plain": "Covers standard pathogen culture. Comprehensive gut microbiome DNA sequencing or rare parasite panels are excluded.",
        "priority_1_keywords": ["diarrhea", "food poisoning", "fever", "nausea"],
    },
    "Chest X-Ray": {
        "plain_name": "Lung & Chest Cavity Imaging",
        "simplified_explanation": "A quick low-dose X-ray image showing your lung tissue, bronchial airways, and ribs to check for pneumonia, congestion, or fluid.",
        "exclusions_plain": "Includes 2-view chest radiography. High-resolution thoracic CT scans or nuclear lung perfusion scans are excluded.",
        "priority_1_keywords": ["cough", "wheezing", "short of breath", "chest tightness", "phlegm"],
    },
    "Spirometry (Pulmonary Function Test)": {
        "plain_name": "Breathing Airflow & Capacity Test",
        "simplified_explanation": "Measures how much air you can inhale and how forcefully you can exhale to evaluate airway tightness and asthma or bronchitis severity.",
        "exclusions_plain": "Covers baseline flow-volume loops. Post-bronchodilator challenge testing or body plethysmography are billed as separate codes.",
        "priority_1_keywords": ["wheezing", "asthma", "tightness", "night cough"],
    },
    "Arterial Blood Gas (ABG)": {
        "plain_name": "Blood Oxygen & Gas Exchange Test",
        "simplified_explanation": "Directly measures oxygen, carbon dioxide, and acid-base levels in arterial blood to verify how efficiently your lungs transfer oxygen.",
        "exclusions_plain": "Covers single blood gas analysis. Continuous arterial line placement or ICU blood monitoring are separate.",
        "priority_1_keywords": ["hypoxia", "severe breathlessness", "cyanosis", "drowning"],
    },
    "X-Ray Joint/Spine": {
        "plain_name": "Bone & Joint Structural X-Ray",
        "simplified_explanation": "Captures clear bone structure images to check joint alignment, bone density, spine curvature, or subtle fractures.",
        "exclusions_plain": "Includes standard bone X-rays. Soft tissue ligament scans or contrast arthrograms are excluded.",
        "priority_1_keywords": ["joint", "bone", "spine", "fracture", "stiffness"],
    },
    "MRI Musculoskeletal": {
        "plain_name": "Soft Tissue & Ligament MRI Scan",
        "simplified_explanation": "High-definition magnetic scan detailing muscles, cartilage, tendons, and ligaments to detect tears, sprains, or deep joint inflammation.",
        "exclusions_plain": "Covers single non-contrast joint MRI. Joint injection contrast or multi-region spine scans are separate.",
        "priority_1_keywords": ["tear", "swelling", "ligament", "sprain", "dislocation"],
    },
    "Physical Therapy Evaluation": {
        "plain_name": "Mobility & Strength Physical Assessment",
        "simplified_explanation": "A hands-on consultation with a licensed physical therapist to measure movement range, muscle balance, and design a personalized recovery plan.",
        "exclusions_plain": "Covers initial 45-minute clinical assessment. Follow-up rehabilitation sessions are billed per session under therapy benefits.",
        "priority_1_keywords": ["rehab", "exercise", "posture", "recovery", "flexibility"],
    },
}


class MedicalPlannerAgent:
    def __init__(self, clinical_tool: ClinicalPackagesTool):
        self.clinical_tool = clinical_tool

    def propose_medical_plan(self, state: PatientSessionState) -> PatientSessionState:
        if not state.selected_department:
            raise ValueError(
                "State Error: Cannot execute planner without a selected_department."
            )

        if not state.trace_logs:
            state.trace_logs = {}
        state.trace_logs["propose-plan"] = []
        logs = state.trace_logs["propose-plan"]

        logs.append(
            f"[MedicalPlannerAgent] Proposing clinical plan for department: '{state.selected_department}'"
        )
        logs.append(
            f"[ClinicalPackagesTool] Querying SQL database for clinical packages..."
        )

        state.proposed_procedures = (
            self.clinical_tool.fetch_department_examination_packages(
                state.selected_department
            )
        )

        logs.append(
            f"[ClinicalPackagesTool] Database query resolved. Found {len(state.proposed_procedures)} medical package(s):"
        )
        for proc in state.proposed_procedures:
            logs.append(f"  - {proc}")

        # Deep analysis & simplification
        symptoms_lower = (state.raw_symptoms or "").lower()
        categorized_items = []

        must_have_count = 0
        for idx, proc in enumerate(state.proposed_procedures):
            meta = PROCEDURE_METADATA_MAP.get(
                proc,
                {
                    "plain_name": proc,
                    "simplified_explanation": f"Diagnostic evaluation package for {proc}.",
                    "exclusions_plain": "Standard diagnostic coverage rules apply.",
                    "priority_1_keywords": [],
                },
            )

            # Determine priority category
            matched_kw = [kw for kw in meta["priority_1_keywords"] if kw in symptoms_lower]
            
            if matched_kw or (idx == 0 and must_have_count == 0):
                priority = "Must-Have (Priority 1)"
                priority_level = 1
                must_have_count += 1
                reason = matched_kw[0] if matched_kw else "primary diagnostic protocol"
                justification = f"Mandatory essential test: Directly targets your reported symptoms of '{reason}' to rule out acute underlying conditions."
            elif idx == 1 or "blood" in proc.lower() or "exam" in proc.lower():
                priority = "Recommended (Priority 2)"
                priority_level = 2
                justification = f"High-value diagnostic: Evaluates contributing systemic factors (e.g. inflammation or blood cell markers) to support your primary care plan."
            else:
                priority = "Optional (Priority 3)"
                priority_level = 3
                justification = f"Secondary add-on: Supplementary evaluation to consider if initial findings warrant broader organ system investigation."

            categorized_items.append({
                "procedure_name": proc,
                "plain_name": meta["plain_name"],
                "simplified_explanation": meta["simplified_explanation"],
                "exclusions_plain": meta["exclusions_plain"],
                "priority": priority,
                "priority_level": priority_level,
                "justification": justification,
            })

        assistant_walkthrough = (
            f"Hello! Based on your reported symptoms of '{state.raw_symptoms}', I have carefully structured your care plan for the {state.selected_department} department. "
            "To walk you through your treatment journey like a personal care assistant, I have translated technical medical terms into plain language and categorized your recommendations into Must-Have mandatory essentials, Recommended preventive diagnostics, and Optional secondary add-ons."
        )

        state.package_analysis = {
            "assistant_walkthrough": assistant_walkthrough,
            "categorized_items": categorized_items,
        }

        logs.append(
            "[MedicalPlannerAgent] Executing deep package simplification & priority categorization:"
        )
        for item in categorized_items:
            logs.append(
                f"  - [{item['priority']}] {item['procedure_name']} -> Plain: '{item['plain_name']}' | Justification: {item['justification']}"
            )

        logs.append(
            "[MedicalPlannerAgent] Categorized recommendations & patient walkthrough successfully saved to active session state."
        )
        return state

    def serialize_billing_payload(
        self, state: PatientSessionState
    ) -> PatientSessionState:
        if not state.confirmed_procedures:
            raise ValueError(
                "Execution Error: Cannot serialize an empty procedure checklist."
            )

        if not state.trace_logs:
            state.trace_logs = {}
        state.trace_logs["finalize-estimate"] = []
        logs = state.trace_logs["finalize-estimate"]

        logs.append(
            "[MedicalPlannerAgent] Serializing clinic procedures into FEABillingPayload..."
        )
        logs.append(
            f"[MedicalPlannerAgent] Ingested procedures for serialization: {state.confirmed_procedures}"
        )

        logs.append(
            "[ClinicalPackagesTool] Resolving billing service codes via dictionary lookup:"
        )
        for proc in state.confirmed_procedures:
            code = self.clinical_tool.get_service_code(proc)
            logs.append(f"  - {proc} -> Service Code: {code}")

        structured_payload = self.clinical_tool.build_json_payload(state)

        logs.append(f"[MedicalPlannerAgent] FEABillingPayload generated successfully:")
        logs.append(
            f"  - Registered Department: {structured_payload.registered_department}"
        )
        logs.append(f"  - Insurance Carrier: {structured_payload.insurance_provider}")
        logs.append(f"  - Policy Identifier: {structured_payload.insurance_policy_id}")

        state.final_billing_payload = structured_payload
        return state
