import os
import json
import asyncio
import re
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from triage_system.core.state import PatientSessionState, FEABillingPayload, ServiceItem
from triage_system.tools.clinical_tool import ClinicalPackagesTool

APP_NAME = "triage_system"

# Ensure API Key environment variables are synced
if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]


PROCEDURE_METADATA_MAP = {
    "Electrocardiogram (ECG)": {
        "plain_name": "Heart Electrical Rhythm Test",
        "simplified_explanation": "A 5-minute, non-invasive test using small chest sensors to record electrical waves through your heart muscle.",
        "exclusions_plain": "Covers standard 12-lead resting ECG tracing. Excludes continuous 24-hour Holter monitoring or invasive catheterization.",
        "priority_1_keywords": ["chest pain", "heart", "beating fast", "palpitations", "cardiac", "arm pain"],
        "clinical_rationale": "Directly targets reported complaints of chest pain, rapid pulse, or arm tightness to assess electrical conductivity in real-time.",
        "what_it_detects": "Rules out acute heart attacks (STEMI/NSTEMI), dangerous arrhythmias (atrial fibrillation), ischemia, or electrolyte imbalance.",
        "risk_if_omitted": "Critical risk: Omitting an ECG during acute chest pain leaves life-threatening heart muscle ischemia undetected.",
        "patient_prep_comfort": "100% painless and non-invasive. Takes ~5 minutes. No fasting required; avoid applying heavy chest creams beforehand.",
    },
    "Echocardiogram (Heart Ultrasound)": {
        "plain_name": "Heart Ultrasound Imaging",
        "simplified_explanation": "A non-invasive soundwave scan generating live moving 3D pictures of your heart valves, chambers, and pumping action.",
        "exclusions_plain": "Standard transthoracic ultrasound included. Transesophageal endoscopic probes or contrast dye require separate authorization.",
        "priority_1_keywords": ["chest pain", "short of breath", "breath", "valve", "heart failure"],
        "clinical_rationale": "Evaluates mechanical heart pump efficiency and valve motion following complaints of shortness of breath or chest pressure.",
        "what_it_detects": "Measures ejection fraction (pump strength), detects leaky/stiff heart valves, pericardial fluid buildup, or heart muscle thickening.",
        "risk_if_omitted": "Moderate-to-high risk: Without ultrasound imaging, structural heart failure or valve dysfunction cannot be visually evaluated.",
        "patient_prep_comfort": "Painless soundwave gel scan. Takes 20-30 minutes. Lie comfortably on your side; no needles, radiation, or fasting required.",
    },
    "Complete Blood Count (CBC)": {
        "plain_name": "Comprehensive Blood Health Panel",
        "simplified_explanation": "A routine blood sample analysis measuring red blood cells, white blood cells, and platelets.",
        "exclusions_plain": "Covers standard cell counts and hemoglobin. Advanced genetic biomarker panels or specialized clotting assays excluded.",
        "priority_1_keywords": ["fever", "infection", "bleeding", "fatigue"],
        "clinical_rationale": "Provides essential baseline screening to rule out systemic infection, internal blood loss, or anemia contributing to weakness or cardiorespiratory strain.",
        "what_it_detects": "Identifies elevated white blood cells (infection/inflammation), low red blood cells (anemia), or low platelets (bleeding risk).",
        "risk_if_omitted": "Low-to-moderate risk: Missing hidden systemic infection or severe anemia can delay essential supportive therapy.",
        "patient_prep_comfort": "Quick 2-minute routine blood draw from your arm. Minimal discomfort (brief pinch). Stay well hydrated before your test.",
    },
    "MRI Brain Scan": {
        "plain_name": "High-Detail Brain Tissue Scan",
        "simplified_explanation": "Uses magnetic fields and radio waves to take high-resolution cross-section 3D images of brain tissue, nerves, and blood vessels.",
        "exclusions_plain": "Covers non-contrast brain MRI. Intravenous gadolinium contrast agents or functional neuro-imaging require secondary copay clearance.",
        "priority_1_keywords": ["headache", "throbbing", "migraine", "stiffness", "numbness", "vision"],
        "clinical_rationale": "Indicated for severe, persistent headaches, neck stiffness, or neurological symptoms to rule out structural brain anomalies.",
        "what_it_detects": "Rules out brain tumors, vascular malformations, multiple sclerosis lesions, acoustic neuromas, or deep nerve compression.",
        "risk_if_omitted": "High risk for chronic neurological symptoms: Delaying MRI can miss early-stage structural lesions or nerve impingement.",
        "patient_prep_comfort": "Non-invasive and painless scan lasting 30-45 minutes. Requires lying still in a magnetic tube. Earplugs provided for machine noise.",
    },
    "CT Head Scan": {
        "plain_name": "Fast Computerized Head X-Ray",
        "simplified_explanation": "A rapid, 5-minute computer-guided X-ray scan that captures cross-sectional images of the skull and brain tissue.",
        "exclusions_plain": "Covers acute head CT without contrast. Angiography vascular reconstruction or repeated follow-up scans require secondary review.",
        "priority_1_keywords": ["trauma", "fall", "bleeding", "stroke", "sudden"],
        "clinical_rationale": "Essential emergency diagnostic for sudden severe headache, head trauma, or acute neurological deficits requiring immediate triage.",
        "what_it_detects": "Rapidly detects acute intracranial hemorrhage (brain bleeding), skull fractures, brain swelling, or acute ischemic stroke.",
        "risk_if_omitted": "Critical risk in acute trauma/stroke: Missing internal brain bleeding or acute swelling can lead to permanent neurological damage.",
        "patient_prep_comfort": "Painless and extremely fast (under 5 minutes). Lie flat on an open motorized table; remove metal jewelry or hairpins before entering.",
    },
    "Neurological Exam": {
        "plain_name": "Nerve & Reflex Clinical Assessment",
        "simplified_explanation": "A comprehensive physical evaluation by a clinical neurologist testing motor control, sensation, reflexes, and balance.",
        "exclusions_plain": "Includes 45-minute clinical physical exam. Nerve conduction velocity (NCV) or needle electromyography (EMG) testing excluded.",
        "priority_1_keywords": ["light sensitivity", "neck", "dizziness", "balance", "tingling"],
        "clinical_rationale": "Directly maps neurological complaints (dizziness, light sensitivity, tingling, or neck stiffness) to specific cranial or peripheral nerve pathways.",
        "what_it_detects": "Pinpoints cranial nerve deficits, sensory nerve impairment, cerebellar gait ataxia, or meningeal irritation signs.",
        "risk_if_omitted": "Moderate risk: Skipping physical nerve testing makes it difficult to localize sensory/reflex abnormalities before ordering expensive scans.",
        "patient_prep_comfort": "Completely non-invasive physical exam lasting 30-40 minutes. Involves light reflex hammer taps, vision tests, and guided movements.",
    },
    "Abdominal Ultrasound": {
        "plain_name": "Stomach & Organ Soundwave Scan",
        "simplified_explanation": "A gentle ultrasound scan examining your stomach, liver, gallbladder, pancreas, and kidneys using harmless soundwaves.",
        "exclusions_plain": "Covers upper abdominal organ screening. Pelvic organs or interventional biopsy guidance require dedicated ordering.",
        "priority_1_keywords": ["cramps", "abdominal", "bloating", "nausea", "stomach", "pain"],
        "clinical_rationale": "Primary diagnostic investigation for abdominal cramps, bloating, nausea, or upper stomach pain.",
        "what_it_detects": "Detects gallstones, cholecystitis (gallbladder inflammation), fatty liver disease, kidney stones, or fluid accumulation (ascites).",
        "risk_if_omitted": "Moderate risk: Omitting an abdominal scan can cause painful gallstone blockages or organ inflammation to go undiagnosed.",
        "patient_prep_comfort": "Painless gel scan lasting 15-20 minutes. Fasting required for 6-8 hours prior so your gallbladder remains clear and visible.",
    },
    "Endoscopy (EGD)": {
        "plain_name": "Upper Digestive Tract Visual Exam",
        "simplified_explanation": "Uses a thin, flexible tube with a HD camera to inspect the inner lining of your esophagus, stomach, and upper small intestine.",
        "exclusions_plain": "Includes diagnostic mucosal inspection. Tissue biopsy pathology fees or therapeutic polyp removal billed as surgical add-ons.",
        "priority_1_keywords": ["ulcer", "vomiting", "severe cramps", "reflux", "swallowing"],
        "clinical_rationale": "Recommended for severe abdominal pain, persistent acid reflux, difficulty swallowing, or suspected stomach lining ulcers.",
        "what_it_detects": "Visually diagnoses peptic ulcers, gastritis, H. pylori infection, esophagus irritation, or abnormal mucosal growths.",
        "risk_if_omitted": "High risk for persistent digestive pain: Without visual endoscopy, deep stomach ulcers or esophageal lesions cannot be evaluated.",
        "patient_prep_comfort": "Performed under mild, comfortable throat numbing or light sedation. Fasting required 8 hours prior. Takes 15-20 minutes.",
    },
    "Stool Analysis & Culture": {
        "plain_name": "Digestive Infection & Flora Test",
        "simplified_explanation": "Laboratory evaluation of digestive samples to check for bacterial pathogens, parasitic infections, or hidden blood loss.",
        "exclusions_plain": "Covers standard pathogen culture. Comprehensive gut microbiome DNA sequencing or rare parasite panels are excluded.",
        "priority_1_keywords": ["diarrhea", "food poisoning", "fever", "nausea"],
        "clinical_rationale": "Evaluates gastrointestinal symptoms accompanied by fever, diarrhea, severe bloating, or suspected foodborne illness.",
        "what_it_detects": "Identifies bacterial gastroenteritis (Salmonella, E. coli, C. diff), intestinal parasites, or microscopic occult blood loss.",
        "risk_if_omitted": "Low-to-moderate risk: Missing active bacterial or parasitic infection can lead to prolonged dehydration or spread.",
        "patient_prep_comfort": "Simple non-invasive sample collection at home or clinic using a sterile kit. No fasting or needles required.",
    },
    "Chest X-Ray": {
        "plain_name": "Lung & Chest Cavity Imaging",
        "simplified_explanation": "A quick low-dose X-ray image visualizing your lungs, airway passages, diaphragm, and chest wall.",
        "exclusions_plain": "Includes 2-view chest radiography. High-resolution thoracic CT scans or nuclear lung perfusion scans are excluded.",
        "priority_1_keywords": ["cough", "wheezing", "short of breath", "chest tightness", "phlegm"],
        "clinical_rationale": "First-line diagnostic test for respiratory symptoms including persistent cough, wheezing, breathlessness, or chest tightness.",
        "what_it_detects": "Detects pneumonia, pulmonary congestion, lung fluid, enlarged heart shadow, pneumothorax (collapsed lung), or rib fractures.",
        "risk_if_omitted": "High risk for lung complaints: Delaying chest X-ray can allow severe pulmonary infection (pneumonia) or fluid buildup to worsen.",
        "patient_prep_comfort": "Fast 2-minute scan. Stand against an X-ray plate, take a deep breath, and hold for 3 seconds. No fasting; completely painless.",
    },
    "Spirometry (Pulmonary Function Test)": {
        "plain_name": "Breathing Airflow & Capacity Test",
        "simplified_explanation": "Measures how much air you can blow out and how fast, assessing bronchial airway tightness and lung expansion.",
        "exclusions_plain": "Covers baseline flow-volume loops. Post-bronchodilator challenge testing or body plethysmography are billed as separate codes.",
        "priority_1_keywords": ["wheezing", "asthma", "tightness", "night cough"],
        "clinical_rationale": "Essential evaluation for chronic wheezing, asthma symptoms, occupational lung exposure, or chronic obstructive bronchitis.",
        "what_it_detects": "Measures FEV1 and FVC airflow ratios to diagnose asthma, COPD, bronchial obstruction, or restrictive lung disease.",
        "risk_if_omitted": "Moderate risk: Without airflow measurement, asthma or COPD severity cannot be accurately staged for proper inhaler prescription.",
        "patient_prep_comfort": "Painless 15-minute breathing test. Sit comfortably and blow into a mouthpiece connected to a monitor. Avoid heavy meals 2 hours prior.",
    },
    "Arterial Blood Gas (ABG)": {
        "plain_name": "Blood Oxygen & Gas Exchange Test",
        "simplified_explanation": "Directly measures oxygen, carbon dioxide, and acidity (pH) levels in arterial blood to verify lung oxygenation efficiency.",
        "exclusions_plain": "Covers single blood gas analysis. Continuous arterial line placement or ICU blood monitoring are separate.",
        "priority_1_keywords": ["hypoxia", "severe breathlessness", "cyanosis", "drowning"],
        "clinical_rationale": "Indicated for severe breathlessness, low oxygen saturation, or acute respiratory insufficiency.",
        "what_it_detects": "Measures PaO2 (oxygen pressure), PaCO2 (carbon dioxide retention), and blood pH to detect respiratory failure or metabolic acidosis.",
        "risk_if_omitted": "High risk in acute distress: Missing dangerous carbon dioxide buildup or low oxygen levels can jeopardize organ oxygenation.",
        "patient_prep_comfort": "Small blood sample taken from the wrist artery (radial pulse). Brief firm pressure applied for 5 minutes afterward.",
    },
    "X-Ray Joint/Spine": {
        "plain_name": "Bone & Joint Structural X-Ray",
        "simplified_explanation": "Captures clear 2D structural images of your bones and joints to evaluate alignment, bone density, and joint spacing.",
        "exclusions_plain": "Includes standard bone X-rays. Soft tissue ligament scans or contrast arthrograms are excluded.",
        "priority_1_keywords": ["joint", "bone", "spine", "fracture", "stiffness"],
        "clinical_rationale": "Primary imaging test for joint pain, spinal stiffness, traumatic impact, or suspected bone fractures.",
        "what_it_detects": "Identifies bone fractures, joint space narrowing (osteoarthritis), bone spurs, spine disc space loss, or bone dislocation.",
        "risk_if_omitted": "Moderate risk: Skipping bone X-rays can cause hairline fractures or progressive joint degeneration to go untreated.",
        "patient_prep_comfort": "Quick 5-minute painless scan. Position your arm, leg, or back against the detector plate; no needles or fasting.",
    },
    "MRI Musculoskeletal": {
        "plain_name": "Soft Tissue & Ligament MRI Scan",
        "simplified_explanation": "High-definition magnetic scan detailing joint cartilage, tendons, ligaments, and deep muscle tissues.",
        "exclusions_plain": "Covers single non-contrast joint MRI. Joint injection contrast or multi-region spine scans are separate.",
        "priority_1_keywords": ["tear", "swelling", "ligament", "sprain", "dislocation"],
        "clinical_rationale": "Recommended for severe joint swelling, persistent joint instability, suspected tendon/ligament tears, or deep soft tissue pain.",
        "what_it_detects": "Diagnoses ACL/MCL knee ligament tears, rotator cuff tendon tears, meniscus tears, spinal herniated discs, or bone marrow edema.",
        "risk_if_omitted": "High risk for joint injuries: Ligament or tendon tears cannot be seen on regular X-rays and require MRI for surgical or rehab planning.",
        "patient_prep_comfort": "Non-invasive 30-minute scan inside a comfortable MRI tube. Completely painless; earplugs provided for soft humming sound.",
    },
    "Physical Therapy Evaluation": {
        "plain_name": "Mobility & Strength Physical Assessment",
        "simplified_explanation": "A hands-on consultation with a licensed physical therapist to evaluate joint flexibility, muscle strength, posture, and movement patterns.",
        "exclusions_plain": "Covers initial 45-minute clinical assessment. Follow-up rehabilitation sessions are billed per session under therapy benefits.",
        "priority_1_keywords": ["rehab", "exercise", "posture", "recovery", "flexibility"],
        "clinical_rationale": "Complements diagnostic imaging by assessing how joint or muscular pain impacts your daily mobility and functional recovery.",
        "what_it_detects": "Identifies muscle imbalances, restricted range of motion, postural compensation, nerve entrapment triggers, and gait abnormalities.",
        "risk_if_omitted": "Low-to-moderate risk: Without physical therapy guidance, recovery from joint or muscle pain can be prolonged with improper movement.",
        "patient_prep_comfort": "Interactive, supportive 45-minute session. Wear comfortable, loose-fitting clothing that allows easy movement and stretching.",
    },
}


from pydantic import BaseModel, Field
from typing import List

class JustificationSchema(BaseModel):
    clinical_rationale: str = Field(description="Detailed explanation of why this test is necessary for their specific symptoms")
    what_it_detects: str = Field(description="Detailed diagnostic scope of what acute or chronic conditions it detects or rules out")
    risk_if_omitted: str = Field(description="Clinical risk or diagnostic gap if skipped/omitted")
    patient_prep_comfort: str = Field(description="Patient expectations regarding pain level, duration, and preparation")

class CategorizedItemSchema(BaseModel):
    procedure_name: str = Field(description="Exact Procedure Name from database list")
    plain_name: str = Field(description="Plain, ordinary human-language title")
    simplified_explanation: str = Field(description="Simple explanation of what this test is about in ordinary language")
    exclusions_plain: str = Field(description="Plain language coverage boundaries or exclusions")
    priority: str = Field(description="Must-Have (Priority 1) | Recommended (Priority 2) | Optional (Priority 3)")
    priority_level: int = Field(description="1 for Must-Have, 2 for Recommended, 3 for Optional")
    justification: JustificationSchema

class PackageAnalysisSchema(BaseModel):
    assistant_walkthrough: str = Field(description="A warm, personal human assistant walkthrough message greeting the patient and guiding them through their options")
    categorized_items: List[CategorizedItemSchema]


class MedicalPlannerAgent:
    def __init__(self, clinical_tool: ClinicalPackagesTool):
        self.clinical_tool = clinical_tool
        
        self._adk_agent = Agent(
            model="gemini-3.1-flash-lite",
            name="medical_planner_agent",
            description="Analyzes database proposed procedures alongside patient symptoms to provide plain human-language translations, priorities, and comprehensive contextual justifications.",
            instruction=(
                "You are an empathetic, expert clinical planning assistant. "
                "You will receive a patient's reported symptoms, their assigned hospital department, "
                "and a list of clinical procedures queried from the hospital database.\n\n"
                "Your objective is to:\n"
                "1. Translate each procedure name into plain, ordinary human language that any patient can easily understand.\n"
                "2. Provide a clear, patient-friendly explanation of what the test is about in ordinary language.\n"
                "3. Summarize coverage boundaries or exclusions in simple terms.\n"
                "4. Categorize each procedure into one of three priority tiers:\n"
                "   - 'Must-Have (Priority 1)' (priority_level: 1): Mandatory essential tests for their chief complaints and acute risks.\n"
                "   - 'Recommended (Priority 2)' (priority_level: 2): High-value preventive additions suited to their health profile.\n"
                "   - 'Optional (Priority 3)' (priority_level: 3): Secondary add-ons or lower-priority coverage.\n"
                "5. Provide a thorough, comprehensive justification object for each procedure containing:\n"
                "   - 'clinical_rationale': Detailed explanation of why this test is necessary for their specific symptoms\n"
                "   - 'what_it_detects': Detailed diagnostic scope of what acute or chronic conditions it detects or rules out\n"
                "   - 'risk_if_omitted': Clinical risk or diagnostic gap if skipped/omitted\n"
                "   - 'patient_prep_comfort': Patient expectations regarding pain level, duration, and preparation\n"
                "6. Write a warm, personal 'assistant_walkthrough' message greeting the patient and guiding them through their options."
            ),
            output_schema=PackageAnalysisSchema,
        )
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._adk_agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )

    async def propose_medical_plan(self, state: PatientSessionState) -> PatientSessionState:
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

        # 1. Fetch procedures from database
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

        # 2. Invoke ADK AI Agent to analyze database output alongside patient symptoms
        logs.append(
            f"[MedicalPlannerAgent] Initiating ADK AI Agent (model: {self._adk_agent.model}) to analyze database procedures alongside patient symptoms..."
        )

        user_id = str(state.patient_id)
        session_id = f"planner-{state.patient_id}"

        # Clean session setup
        try:
            existing = await self._session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            if existing:
                await self._session_service.delete_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            await self._session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        except Exception:
            pass

        prompt = (
            f"Patient Symptoms: {state.raw_symptoms}\n"
            f"Selected Department: {state.selected_department}\n"
            f"Proposed Procedures from Database: {json.dumps(state.proposed_procedures)}\n\n"
            "Analyze these database procedures specifically for this patient's intake profile and return a JSON object matching this exact schema:\n"
            "{\n"
            '  "assistant_walkthrough": "A warm, personal human assistant walkthrough message...",\n'
            '  "categorized_items": [\n'
            "    {\n"
            '      "procedure_name": "Exact Procedure Name from database list",\n'
            '      "plain_name": "Plain, ordinary human-language title",\n'
            '      "simplified_explanation": "Simple explanation of what this test is about in ordinary language",\n'
            '      "exclusions_plain": "Plain language coverage boundaries or exclusions",\n'
            '      "priority": "Must-Have (Priority 1) | Recommended (Priority 2) | Optional (Priority 3)",\n'
            '      "priority_level": 1 | 2 | 3,\n'
            '      "justification": {\n'
            '        "clinical_rationale": "Detailed explanation of why this test is necessary for their specific symptoms",\n'
            '        "what_it_detects": "Detailed diagnostic scope of what it detects or rules out",\n'
            '        "risk_if_omitted": "Clinical risk or diagnostic gap if skipped/omitted",\n'
            '        "patient_prep_comfort": "Patient expectations regarding pain level, duration, and preparation"\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        content = types.Content(role="user", parts=[types.Part(text=prompt)])
        state.ai_model_name = self._adk_agent.model

        raw_llm_text = ""
        try:
            async for event in self._runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                if hasattr(event, "usage_metadata") and event.usage_metadata:
                    state.prompt_tokens += getattr(event.usage_metadata, "prompt_token_count", 0)
                    state.candidate_tokens += getattr(event.usage_metadata, "candidates_token_count", 0)

                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            text_snippet = part.text.strip()
                            if text_snippet:
                                raw_llm_text += part.text
                                # Log reasoning snippet
                                if not text_snippet.startswith("{") and not text_snippet.startswith("["):
                                    logs.append(f"[MedicalPlannerAgent] [Model Thought] {text_snippet}")

            # Parse JSON
            clean_text = raw_llm_text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```")[1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:].strip()
            
            parsed_analysis = json.loads(clean_text)
            state.package_analysis = parsed_analysis
            
            logs.append(
                "[MedicalPlannerAgent] ADK AI Agent successfully analyzed procedures and generated plain-language care plan."
            )
            for item in parsed_analysis.get("categorized_items", []):
                p_title = item.get("plain_name", item.get("procedure_name"))
                p_level = item.get("priority", "Priority")
                logs.append(
                    f"  - [{p_level}] {item.get('procedure_name')} -> Plain: '{p_title}'"
                )

        except Exception as exc:
            logs.append(
                f"[Error] MedicalPlannerAgent AI run encountered error: {exc}. Utilizing robust fallback simplification."
            )
            # Fallback parsing/generation
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
                        "clinical_rationale": f"Evaluates your chief complaints for department {state.selected_department}.",
                        "what_it_detects": f"Rules out structural anomalies associated with {proc}.",
                        "risk_if_omitted": "Omitting this test creates a diagnostic gap for symptom evaluation.",
                        "patient_prep_comfort": "Painless diagnostic test. No special preparation required unless instructed.",
                    },
                )
                matched_kw = [kw for kw in meta["priority_1_keywords"] if kw in symptoms_lower]
                if matched_kw or (idx == 0 and must_have_count == 0):
                    priority = "Must-Have (Priority 1)"
                    priority_level = 1
                    must_have_count += 1
                    reason = matched_kw[0] if matched_kw else "primary clinical protocol"
                    clinical_rationale = f"Mandatory essential test: Directly targets your reported symptoms of '{reason}' to evaluate acute underlying conditions."
                elif idx == 1 or "blood" in proc.lower() or "exam" in proc.lower():
                    priority = "Recommended (Priority 2)"
                    priority_level = 2
                    clinical_rationale = f"High-value diagnostic: Evaluates contributing systemic factors (e.g. inflammation or systemic response) to support your primary care plan."
                else:
                    priority = "Optional (Priority 3)"
                    priority_level = 3
                    clinical_rationale = f"Secondary add-on: Supplementary evaluation to consider if initial findings warrant broader organ system investigation."

                categorized_items.append({
                    "procedure_name": proc,
                    "plain_name": meta["plain_name"],
                    "simplified_explanation": meta["simplified_explanation"],
                    "exclusions_plain": meta["exclusions_plain"],
                    "priority": priority,
                    "priority_level": priority_level,
                    "justification": {
                        "clinical_rationale": clinical_rationale,
                        "what_it_detects": meta.get("what_it_detects", "Rules out underlying pathology."),
                        "risk_if_omitted": meta.get("risk_if_omitted", "May leave diagnostic gaps."),
                        "patient_prep_comfort": meta.get("patient_prep_comfort", "Painless clinical test."),
                    },
                })

            state.package_analysis = {
                "assistant_walkthrough": f"Hello! Based on your reported symptoms of '{state.raw_symptoms}', I have structured your care plan for the {state.selected_department} department with plain language translations and prioritized recommendations.",
                "categorized_items": categorized_items,
            }

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
