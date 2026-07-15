import { useState } from 'react'
import './App.css'

// ==========================================
// TYPES & SCHEMAS (Co-located for simplicity)
// ==========================================
interface ServiceItem {
  service_code: string;
  procedure_name: string;
}

interface FEABillingPayload {
  registered_department: string;
  confirmed_services: ServiceItem[];
  insurance_provider: string;
  insurance_policy_id: string;
}

interface PatientSessionState {
  patient_id: string;
  raw_symptoms: string;
  recommended_departments: string[];
  selected_department: string | null;
  proposed_procedures: string[];
  confirmed_procedures: string[];
  insurance_details: {
    provider?: string;
    policy_id?: string;
    [key: string]: any;
  };
  final_billing_payload: FEABillingPayload | null;
  cost_estimation_breakdown: Record<string, number>;
  final_out_of_pocket_cost: number;
}

// Preset symptom descriptions for easy user testing
const PRESET_SYMPTOMS = [
  {
    label: "Cardiovascular Symptoms",
    desc: "I have a sharp pain in my chest, it radiates down my left arm, and I feel very short of breath.",
  },
  {
    label: "Neurological Symptoms",
    desc: "I have had a severe, throbbing headache for 3 days with intense light sensitivity and stiffness in my neck.",
  },
  {
    label: "Gastrointestinal Symptoms",
    desc: "I have been experiencing persistent, severe abdominal cramps, bloating, and nausea after eating.",
  },
  {
    label: "Respiratory Symptoms",
    desc: "I have chronic wheezing, chest tightness, and a persistent deep cough that worsens at night.",
  }
];

const GENERAL_DEPARTMENTS = [
  "Cardiology",
  "Neurology",
  "Orthopedics",
  "Gastroenterology",
  "Pulmonology"
];

const API_BASE = "http://localhost:8000/api/pipeline";

export default function App() {
  // Wizard flow step: 1 (Intake), 2 (Routing), 3 (Procedures/Insurance), 4 (Receipt)
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Central state matching the backend's state contract
  const [sessionState, setSessionState] = useState<PatientSessionState>({
    patient_id: "PT-2026-X",
    raw_symptoms: "",
    recommended_departments: [],
    selected_department: null,
    proposed_procedures: [],
    confirmed_procedures: [],
    insurance_details: {},
    final_billing_payload: null,
    cost_estimation_breakdown: {},
    final_out_of_pocket_cost: 0,
  });

  // Local form states
  const [insuranceProvider, setInsuranceProvider] = useState<string>("BlueCross");
  const [insurancePolicyId, setInsurancePolicyId] = useState<string>("");

  // ==========================================
  // API SERVICE HANDLERS
  // ==========================================
  
  // Step 1: Initialize Triage and get recommended departments
  const handleInitializeTriage = async (symptomText: string) => {
    if (!symptomText.trim()) {
      setError("Please describe symptoms or select a template.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/initialize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(symptomText),
      });

      if (!response.ok) {
        throw new Error("Failed to process symptom triage. Please check backend status.");
      }

      const data: PatientSessionState = await response.json();
      setSessionState(data);
      // Auto-select first recommended department if available
      const firstDept = data.recommended_departments?.[0] || null;
      setSessionState({
        ...data,
        selected_department: firstDept
      });
      setStep(2);
    } catch (err: any) {
      setError(err.message || "An unexpected network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Propose plan for selected department
  const handleProposePlan = async (department: string) => {
    if (!department) {
      setError("Please select a target department.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const updatedState: PatientSessionState = {
        ...sessionState,
        selected_department: department
      };

      const response = await fetch(`${API_BASE}/propose-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedState),
      });

      if (!response.ok) {
        throw new Error("Failed to propose medical procedures plan.");
      }

      const data: PatientSessionState = await response.json();
      setSessionState(data);
      // Confirm all procedures by default
      setSessionState({
        ...data,
        confirmed_procedures: data.proposed_procedures
      });
      setStep(3);
    } catch (err: any) {
      setError(err.message || "An unexpected network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Finalize estimate and calculate out-of-pocket costs
  const handleFinalizeEstimate = async (confirmedProcs: string[]) => {
    if (confirmedProcs.length === 0) {
      setError("Please confirm at least one procedure to calculate estimate.");
      return;
    }
    if (!insuranceProvider) {
      setError("Please input an insurance carrier or select Self-Pay.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const updatedState: PatientSessionState = {
        ...sessionState,
        confirmed_procedures: confirmedProcs,
        insurance_details: {
          provider: insuranceProvider,
          policy_id: insurancePolicyId || "NONE"
        }
      };

      const response = await fetch(`${API_BASE}/finalize-estimate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedState),
      });

      if (!response.ok) {
        const errDetail = await response.json().catch(() => ({}));
        throw new Error(errDetail.detail || "Failed to calculate out-of-pocket estimate.");
      }

      const data: PatientSessionState = await response.json();
      setSessionState(data);
      setStep(4);
    } catch (err: any) {
      setError(err.message || "An unexpected network error occurred.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSessionState({
      patient_id: "PT-2026-X",
      raw_symptoms: "",
      recommended_departments: [],
      selected_department: null,
      proposed_procedures: [],
      confirmed_procedures: [],
      insurance_details: {},
      final_billing_payload: null,
      cost_estimation_breakdown: {},
      final_out_of_pocket_cost: 0,
    });
    setInsurancePolicyId("");
    setError(null);
    setStep(1);
  };

  // ==========================================
  // HELPER RENDERS (Inline micro-components)
  // ==========================================
  const renderStepIndicator = () => {
    const steps = [
      { num: 1, label: "Symptom Intake" },
      { num: 2, label: "Dept Routing" },
      { num: 3, label: "Clinical Plan" },
      { num: 4, label: "Financial Estimate" }
    ];
    return (
      <div className="mb-12">
        <div className="flex items-center justify-between">
          {steps.map((s, idx) => (
            <div key={s.num} className="flex-1 relative">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center text-xs font-mono transition-all duration-300 ${
                  step === s.num
                    ? 'border-teal-500 bg-teal-500/10 text-teal-600 dark:text-teal-400 font-bold scale-110 shadow-sm'
                    : step > s.num
                      ? 'border-slate-400 bg-slate-100 dark:bg-slate-800 text-slate-500'
                      : 'border-slate-200 dark:border-slate-800 text-slate-300 dark:text-slate-700'
                }`}>
                  {s.num}
                </div>
                <span className={`mt-2 text-2xs uppercase tracking-widest font-mono hidden md:block transition-colors duration-300 ${
                  step === s.num
                    ? 'text-slate-800 dark:text-slate-200 font-medium'
                    : 'text-slate-400 dark:text-slate-600'
                }`}>
                  {s.label}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div className="absolute top-4 left-[calc(50%+16px)] right-[calc(-50%+16px)] h-[1px] bg-slate-200 dark:bg-slate-800 -z-10" />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans antialiased">
      {/* Header Banner */}
      <header className="border-b border-slate-200 dark:border-slate-900 bg-white dark:bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex flex-col">
            <span className="text-sm font-mono tracking-widest text-teal-600 dark:text-teal-400 font-bold">ST. JUDE CLINICS</span>
            <span className="text-xs font-mono text-slate-400 tracking-wider">TRIAGE DISPATCH SYSTEM</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
            </span>
            <span className="text-2xs font-mono tracking-widest text-slate-500 dark:text-slate-400 uppercase">
              Agent Pipeline Active
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow max-w-3xl w-full mx-auto px-6 py-10 flex flex-col justify-center">
        {renderStepIndicator()}

        {/* Global Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-sm font-mono flex items-start gap-3 rounded">
            <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <span className="font-bold uppercase tracking-wider block text-xs mb-1">SYSTEM OUTAGE ALERT</span>
              {error}
            </div>
          </div>
        )}

        {/* Central Stage Wrapper */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-900 rounded-lg p-6 md:p-8 shadow-sm">
          
          {loading && (
            <div className="py-12 flex flex-col items-center justify-center gap-4">
              <div className="relative w-12 h-12">
                <div className="absolute inset-0 rounded-full border-2 border-teal-500/20 animate-pulse"></div>
                <div className="absolute inset-0 rounded-full border-t-2 border-teal-500 animate-spin"></div>
              </div>
              <span className="text-xs font-mono uppercase tracking-widest text-teal-600 dark:text-teal-400 animate-pulse">
                Consulting Agentic Pipeline...
              </span>
            </div>
          )}

          {!loading && (
            <>
              {/* STEP 1: INTAKE SCREEN */}
              {step === 1 && (
                <div className="space-y-6">
                  <div className="space-y-2 border-b border-slate-100 dark:border-slate-800 pb-4">
                    <h1 className="text-xl font-medium tracking-tight text-slate-950 dark:text-white">
                      Patient Symptom Intake
                    </h1>
                    <p className="text-sm text-slate-500">
                      Submit patient symptoms in plain language. The Triage Agent routes case profiles using dynamic RAG classification.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-mono uppercase tracking-wider text-slate-400">
                      Symptom Description
                    </label>
                    <textarea
                      rows={5}
                      className="w-full border border-slate-200 dark:border-slate-800 rounded bg-slate-50/50 dark:bg-slate-950 p-4 text-sm font-sans placeholder-slate-400 focus:outline-none focus:border-teal-500 focus:bg-white dark:focus:bg-slate-950 transition-colors resize-none"
                      placeholder="Enter description here (e.g. pain level, duration, compounding factors)..."
                      value={sessionState.raw_symptoms}
                      onChange={(e) => setSessionState({ ...sessionState, raw_symptoms: e.target.value })}
                    />
                  </div>

                  <div className="space-y-3">
                    <span className="text-xs font-mono uppercase tracking-wider text-slate-400 block">
                      Select Clinical Test Templates
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {PRESET_SYMPTOMS.map((preset) => (
                        <button
                          key={preset.label}
                          type="button"
                          className="text-left border border-slate-200 dark:border-slate-800 hover:border-teal-500/50 hover:bg-slate-50 dark:hover:bg-slate-950/50 p-3 rounded transition-all group"
                          onClick={() => setSessionState({ ...sessionState, raw_symptoms: preset.desc })}
                        >
                          <span className="text-xs font-mono font-medium text-slate-800 dark:text-slate-200 group-hover:text-teal-600 dark:group-hover:text-teal-400 block transition-colors">
                            {preset.label}
                          </span>
                          <span className="text-2xs text-slate-400 line-clamp-1 mt-1 font-sans">
                            {preset.desc}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 flex justify-end">
                    <button
                      type="button"
                      className="w-full md:w-auto px-6 py-2.5 bg-teal-600 dark:bg-teal-500 text-white rounded text-xs font-mono uppercase tracking-widest hover:bg-teal-700 dark:hover:bg-teal-600 transition-colors"
                      onClick={() => handleInitializeTriage(sessionState.raw_symptoms)}
                    >
                      Initialize Triage Dispatch
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 2: DEPARTMENT SELECTION SCREEN */}
              {step === 2 && (
                <div className="space-y-6">
                  <div className="space-y-2 border-b border-slate-100 dark:border-slate-800 pb-4">
                    <h1 className="text-xl font-medium tracking-tight text-slate-950 dark:text-white">
                      Department Dispatch Routing
                    </h1>
                    <p className="text-sm text-slate-500">
                      The Triage Agent routed the case to the following department suggestions. Verify and select the routing destination.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                      RAG System Recommendations
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {sessionState.recommended_departments.map((dept, idx) => (
                        <button
                          key={dept}
                          type="button"
                          className={`p-4 border text-left rounded transition-all ${
                            sessionState.selected_department === dept
                              ? 'border-teal-500 bg-teal-500/5 dark:bg-teal-500/10 shadow-sm'
                              : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                          }`}
                          onClick={() => setSessionState({ ...sessionState, selected_department: dept })}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-mono tracking-wider text-slate-400 uppercase">
                              Recommendation {idx === 0 ? "Primary" : "Secondary"}
                            </span>
                            {sessionState.selected_department === dept && (
                              <span className="w-2 h-2 rounded-full bg-teal-500" />
                            )}
                          </div>
                          <span className="text-lg font-medium text-slate-900 dark:text-white block mt-2">
                            {dept}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3 border-t border-slate-100 dark:border-slate-800 pt-4">
                    <span className="text-xs font-mono uppercase tracking-wider text-slate-400 block">
                      Deviate and Dispatch Manually
                    </span>
                    <div className="flex gap-2">
                      <select
                        className="flex-1 border border-slate-200 dark:border-slate-800 rounded bg-slate-50 dark:bg-slate-950 p-2.5 text-xs font-mono focus:outline-none"
                        value={sessionState.selected_department || ""}
                        onChange={(e) => setSessionState({ ...sessionState, selected_department: e.target.value })}
                      >
                        <option value="" disabled>-- Override Department Selection --</option>
                        {GENERAL_DEPARTMENTS.map((dept) => (
                          <option key={dept} value={dept}>
                            {dept}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="pt-4 flex justify-between gap-4 border-t border-slate-100 dark:border-slate-800">
                    <button
                      type="button"
                      className="px-4 py-2 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-950 text-slate-600 dark:text-slate-400 rounded text-xs font-mono uppercase tracking-widest transition-colors"
                      onClick={() => setStep(1)}
                    >
                      Back to Intake
                    </button>
                    <button
                      type="button"
                      className="px-6 py-2.5 bg-teal-600 dark:bg-teal-500 text-white rounded text-xs font-mono uppercase tracking-widest hover:bg-teal-700 dark:hover:bg-teal-600 transition-colors"
                      onClick={() => handleProposePlan(sessionState.selected_department || "")}
                    >
                      Propose Treatment Plan
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 3: PROCEDURES & INSURANCE FORM */}
              {step === 3 && (
                <div className="space-y-6">
                  <div className="space-y-2 border-b border-slate-100 dark:border-slate-800 pb-4">
                    <h1 className="text-xl font-medium tracking-tight text-slate-950 dark:text-white">
                      Plan Confirmation & Coverage
                    </h1>
                    <p className="text-sm text-slate-500">
                      Verify procedure recommendations proposed by the Medical Planner Agent and input insurance details for cost calculations.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <span className="text-xs font-mono uppercase tracking-wider text-slate-400 block">
                      Proposed Clinical Procedures
                    </span>
                    <div className="border border-slate-200 dark:border-slate-800 rounded divide-y divide-slate-200 dark:divide-slate-800">
                      {sessionState.proposed_procedures.map((proc) => {
                        const isChecked = sessionState.confirmed_procedures.includes(proc);
                        return (
                          <label
                            key={proc}
                            className="flex items-center gap-3 p-4 hover:bg-slate-50/50 dark:hover:bg-slate-950/50 cursor-pointer select-none"
                          >
                            <input
                              type="checkbox"
                              className="w-4 h-4 accent-teal-500 rounded border-slate-300 text-teal-600 focus:ring-teal-500 focus:ring-offset-0"
                              checked={isChecked}
                              onChange={() => {
                                if (isChecked) {
                                  setSessionState({
                                    ...sessionState,
                                    confirmed_procedures: sessionState.confirmed_procedures.filter((p) => p !== proc),
                                  });
                                } else {
                                  setSessionState({
                                    ...sessionState,
                                    confirmed_procedures: [...sessionState.confirmed_procedures, proc],
                                  });
                                }
                              }}
                            />
                            <span className="text-sm text-slate-800 dark:text-slate-200 font-sans font-medium">
                              {proc}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  <div className="space-y-4 border-t border-slate-100 dark:border-slate-800 pt-4">
                    <span className="text-xs font-mono uppercase tracking-wider text-slate-400 block">
                      Insurance Policy Details
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-2xs font-mono uppercase tracking-wider text-slate-400">
                          Insurance Provider
                        </label>
                        <select
                          className="w-full border border-slate-200 dark:border-slate-800 rounded bg-slate-50 dark:bg-slate-950 p-2.5 text-xs font-mono focus:outline-none"
                          value={insuranceProvider}
                          onChange={(e) => setInsuranceProvider(e.target.value)}
                        >
                          <option value="BlueCross">BlueCross (80% Cover)</option>
                          <option value="UnitedHealth">UnitedHealth (75% Cover)</option>
                          <option value="Cigna">Cigna (85% Cover)</option>
                          <option value="Aetna">Aetna (70% Cover)</option>
                          <option value="Self-Pay">Self-Pay / None</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <label className="text-2xs font-mono uppercase tracking-wider text-slate-400">
                          Policy Identifier Number
                        </label>
                        <input
                          type="text"
                          className="w-full border border-slate-200 dark:border-slate-800 rounded bg-slate-50 dark:bg-slate-950 p-2 text-xs font-mono focus:outline-none placeholder-slate-400 focus:bg-white dark:focus:bg-slate-950"
                          placeholder="e.g. BC-98765-AX"
                          value={insurancePolicyId}
                          onChange={(e) => setInsurancePolicyId(e.target.value)}
                          disabled={insuranceProvider === "Self-Pay"}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 flex justify-between gap-4 border-t border-slate-100 dark:border-slate-800">
                    <button
                      type="button"
                      className="px-4 py-2 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-950 text-slate-600 dark:text-slate-400 rounded text-xs font-mono uppercase tracking-widest transition-colors"
                      onClick={() => setStep(2)}
                    >
                      Back to Routing
                    </button>
                    <button
                      type="button"
                      className="px-6 py-2.5 bg-teal-600 dark:bg-teal-500 text-white rounded text-xs font-mono uppercase tracking-widest hover:bg-teal-700 dark:hover:bg-teal-600 transition-colors"
                      onClick={() => handleFinalizeEstimate(sessionState.confirmed_procedures)}
                    >
                      Calculate Out-of-Pocket
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 4: FINANCIAL ESTIMATION SUMMARY */}
              {step === 4 && (
                <div className="space-y-6">
                  {/* Premium Clinical Receipt */}
                  <div className="border border-dashed border-slate-300 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 p-6 rounded-md space-y-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 left-0 h-1 bg-teal-500" />
                    
                    {/* Invoice Header */}
                    <div className="flex justify-between items-start flex-wrap gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                      <div>
                        <h2 className="text-md font-mono font-bold tracking-wider text-slate-950 dark:text-white uppercase">
                          St. Jude Health System
                        </h2>
                        <p className="text-2xs font-mono text-slate-400 uppercase tracking-widest mt-1">
                          Preliminary Out-of-Pocket Cost Sheet
                        </p>
                      </div>
                      <div className="text-left md:text-right font-mono">
                        <span className="text-2xs text-slate-400 uppercase block">Case Identifier</span>
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200">{sessionState.patient_id}</span>
                      </div>
                    </div>

                    {/* Metadata Specs Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono border-b border-slate-200 dark:border-slate-800 pb-4">
                      <div>
                        <span className="text-2xs text-slate-400 uppercase block">Dispatch Dept</span>
                        <span className="font-medium text-slate-800 dark:text-slate-200">{sessionState.selected_department}</span>
                      </div>
                      <div>
                        <span className="text-2xs text-slate-400 uppercase block">Insurance</span>
                        <span className="font-medium text-slate-800 dark:text-slate-200">{sessionState.final_billing_payload?.insurance_provider}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-2xs text-slate-400 uppercase block">Policy reference</span>
                        <span className="font-medium text-slate-800 dark:text-slate-200">{sessionState.final_billing_payload?.insurance_policy_id}</span>
                      </div>
                    </div>

                    {/* Invoice Table */}
                    <div className="space-y-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                        Itemized Transaction Audit
                      </span>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 uppercase text-2xs">
                              <th className="py-2">Procedure / Code</th>
                              <th className="py-2 text-right">Standard Rate</th>
                              <th className="py-2 text-right">Co-Pay / Cover</th>
                              <th className="py-2 text-right">Out-of-Pocket</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-slate-900">
                            {sessionState.final_billing_payload?.confirmed_services.map((svc) => {
                              const gross = sessionState.cost_estimation_breakdown[`${svc.procedure_name} (Gross)`] || 0;
                              const covered = sessionState.cost_estimation_breakdown[`${svc.procedure_name} (Insured Covers)`] || 0;
                              const oop = sessionState.cost_estimation_breakdown[`${svc.procedure_name} (Out-of-Pocket)`] || 0;
                              return (
                                <tr key={svc.service_code}>
                                  <td className="py-3 pr-2">
                                    <span className="font-medium text-slate-800 dark:text-slate-200 block">{svc.procedure_name}</span>
                                    <span className="text-2xs text-slate-400 uppercase">{svc.service_code}</span>
                                  </td>
                                  <td className="py-3 text-right text-slate-600 dark:text-slate-400">${gross.toFixed(2)}</td>
                                  <td className="py-3 text-right text-teal-600 dark:text-teal-400">-${covered.toFixed(2)}</td>
                                  <td className="py-3 text-right font-medium text-slate-800 dark:text-slate-200">${oop.toFixed(2)}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Cost Summary Box */}
                    <div className="border-t border-slate-200 dark:border-slate-800 pt-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div className="text-2xs text-slate-400 max-w-sm font-sans">
                        Audit Calculations finalized by Financial Estimator Agent. The estimates reflect contract agreements active under your selected policy terms.
                      </div>
                      <div className="text-left md:text-right font-mono bg-teal-500/10 dark:bg-teal-500/5 p-4 rounded border border-teal-500/20 w-full md:w-auto">
                        <span className="text-2xs text-teal-600 dark:text-teal-400 uppercase block tracking-wider font-bold">
                          Final Cost Responsibility
                        </span>
                        <span className="text-2xl font-bold text-teal-700 dark:text-teal-400 block mt-1">
                          ${sessionState.final_out_of_pocket_cost.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 flex justify-end">
                    <button
                      type="button"
                      className="w-full md:w-auto px-6 py-2.5 bg-teal-600 dark:bg-teal-500 text-white rounded text-xs font-mono uppercase tracking-widest hover:bg-teal-700 dark:hover:bg-teal-600 transition-colors"
                      onClick={handleReset}
                    >
                      New Triage Session
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-900 bg-white dark:bg-slate-900/50 py-6 text-center">
        <div className="max-w-4xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-mono text-slate-400">
          <span>&copy; 2026 St. Jude Healthcare Network. All Rights Reserved.</span>
          <span className="uppercase tracking-widest text-slate-500">Security Clearance Level 1</span>
        </div>
      </footer>
    </div>
  )
}