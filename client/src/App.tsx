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

interface PackageCategorizationItem {
  procedure_name: string;
  plain_name: string;
  simplified_explanation: string;
  exclusions_plain: string;
  priority: string;
  priority_level: number;
  justification: string;
}

interface PackageAnalysis {
  assistant_walkthrough: string;
  categorized_items: PackageCategorizationItem[];
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
  package_analysis?: PackageAnalysis | null;
  final_billing_payload: FEABillingPayload | null;
  cost_estimation_breakdown: Record<string, number>;
  final_out_of_pocket_cost: number;
  trace_logs?: Record<string, string[]>;
  ai_model_name?: string | null;
  prompt_tokens?: number;
  candidate_tokens?: number;
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
    package_analysis: null,
    final_billing_payload: null,
    cost_estimation_breakdown: {},
    final_out_of_pocket_cost: 0,
    trace_logs: {},
    ai_model_name: null,
    prompt_tokens: 0,
    candidate_tokens: 0,
  });

  // Local form states
  const [insuranceProvider, setInsuranceProvider] = useState<string>("BlueCross");
  const [insurancePolicyId, setInsurancePolicyId] = useState<string>("");

  // Trace drawer states
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [drawerTab, setDrawerTab] = useState<"initialize" | "propose-plan" | "finalize-estimate">("initialize");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const openTraceDrawer = (tab: "initialize" | "propose-plan" | "finalize-estimate") => {
    setDrawerTab(tab);
    setDrawerOpen(true);
    setSearchQuery("");
  };

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
      package_analysis: null,
      final_billing_payload: null,
      cost_estimation_breakdown: {},
      final_out_of_pocket_cost: 0,
      trace_logs: {},
      ai_model_name: null,
      prompt_tokens: 0,
      candidate_tokens: 0,
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
      <div className="mb-10">
        <div className="flex items-center justify-between">
          {steps.map((s, idx) => (
            <div key={s.num} className="flex-1 relative">
              <div className="flex flex-col items-center">
                <div className={`w-9 h-9 rounded-xl border flex items-center justify-center text-xs font-semibold transition-all duration-300 ${
                  step === s.num
                    ? 'border-[#1b6bf9] bg-[#edf4ff] text-[#1b6bf9] font-bold scale-105 shadow-xs'
                    : step > s.num
                      ? 'border-blue-200 bg-white text-[#1b6bf9]'
                      : 'border-slate-200 bg-white text-slate-400'
                }`}>
                  {s.num}
                </div>
                <span className={`mt-2.5 text-2xs uppercase tracking-wider font-medium hidden md:block transition-colors duration-300 ${
                  step === s.num
                    ? 'text-[#1b6bf9] font-semibold'
                    : 'text-slate-500'
                }`}>
                  {s.label}
                </span>
              </div>
              {idx < steps.length - 1 && (
                <div className={`absolute top-4.5 left-[calc(50%+20px)] right-[calc(-50%+20px)] h-[2px] -z-10 transition-colors duration-300 ${
                  step > s.num ? 'bg-[#1b6bf9]' : 'bg-slate-200'
                }`} />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Helper to render trace drawer
  const renderTraceDrawer = () => {
    if (!drawerOpen) return null;

    const availableTabs = [
      { id: "initialize", label: "Triage Routing" },
      { id: "propose-plan", label: "Clinical Proposal" },
      { id: "finalize-estimate", label: "Financial Estimate" }
    ] as const;

    const logs = sessionState.trace_logs?.[drawerTab] || [];
    
    // Filter logs based on search
    const filteredLogs = logs.filter(line => 
      line.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Color prefixes based on standard labels
    const formatLogLine = (line: string) => {
      const parts = line.match(/^(\[[^\]]+\])(.*)$/);
      if (!parts) {
        return (
          <span className="font-mono text-xs leading-relaxed block break-all whitespace-pre-wrap text-slate-300">
            {line}
          </span>
        );
      }
      
      const tag = parts[1];
      const content = parts[2];
      
      let tagClass = "text-slate-400 font-bold";
      if (tag.includes("RAGTool")) {
        tagClass = "text-amber-400 font-bold font-mono";
      } else if (tag.includes("TriageAgent")) {
        tagClass = "text-[#60a5fa] font-bold font-mono";
      } else if (tag.includes("ClinicalPackagesTool")) {
        tagClass = "text-emerald-400 font-bold font-mono";
      } else if (tag.includes("FinancialEstimatorAgent") || tag.includes("FEA")) {
        tagClass = "text-violet-400 font-bold font-mono";
      } else if (tag.includes("FinanceDatabaseTool")) {
        tagClass = "text-fuchsia-400 font-bold font-mono";
      } else if (tag.includes("MedicalPlannerAgent")) {
        tagClass = "text-cyan-400 font-bold font-mono";
      } else if (tag.includes("System")) {
        tagClass = "text-slate-200 font-bold font-mono";
      } else if (tag.includes("Error")) {
        tagClass = "text-rose-400 font-bold font-mono";
      }
      
      return (
        <span className="font-mono text-xs leading-relaxed block break-all whitespace-pre-wrap text-slate-300">
          <span className={tagClass}>{tag}</span>
          <span className="text-slate-200">{content}</span>
        </span>
      );
    };

    return (
      <div className="fixed inset-0 z-50 overflow-hidden flex justify-end font-sans">
        {/* Backdrop overlay */}
        <div 
          className="absolute inset-0 bg-slate-950/50 backdrop-blur-xs transition-opacity duration-300"
          onClick={() => setDrawerOpen(false)}
        />
        
        {/* Drawer container */}
        <div className="relative w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl h-full flex flex-col z-10">
          {/* Header */}
          <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950">
            <div>
              <h3 className="text-sm font-mono tracking-widest font-bold text-[#60a5fa] uppercase">
                SYSTEM_TRACE_EXPLORER
              </h3>
              <p className="text-3xs font-mono text-slate-400 uppercase tracking-widest mt-0.5">
                Session Reference: {sessionState.patient_id}
              </p>
            </div>
            <button 
              onClick={() => setDrawerOpen(false)}
              className="px-3 py-1.5 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg font-mono text-xs border border-slate-700 transition-colors cursor-pointer"
            >
              [ESC] CLOSE
            </button>
          </div>

          {/* Drawer Tabs */}
          <div className="flex bg-slate-950 border-b border-slate-800 px-3">
            {availableTabs.map(t => {
              const hasLogs = !!sessionState.trace_logs?.[t.id];
              return (
                <button
                  key={t.id}
                  disabled={!hasLogs}
                  onClick={() => setDrawerTab(t.id)}
                  className={`px-4 py-3 text-2xs font-mono uppercase tracking-widest border-b-2 transition-all font-semibold ${
                    drawerTab === t.id
                      ? "border-[#1b6bf9] text-[#60a5fa] bg-slate-900"
                      : hasLogs
                        ? "border-transparent text-slate-400 hover:text-slate-200 cursor-pointer"
                        : "border-transparent text-slate-700 cursor-not-allowed"
                  }`}
                >
                  {t.label}
                  {!hasLogs && <span className="text-3xs text-slate-600 ml-1">(LOCKED)</span>}
                </button>
              );
            })}
          </div>

          {/* Log Controls */}
          <div className="p-3 bg-slate-900/50 border-b border-slate-800/60 flex gap-2">
            <input
              type="text"
              placeholder="Search trace filters..."
              className="flex-1 bg-slate-950 text-slate-200 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-[#1b6bf9]"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button
              onClick={() => {
                const text = logs.join("\n");
                navigator.clipboard.writeText(text);
                alert("Trace logs copied to clipboard!");
              }}
              className="px-3 py-1.5 bg-slate-950 text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 rounded-lg text-xs font-mono transition-colors cursor-pointer"
            >
              COPY_ALL
            </button>
          </div>

          {/* Logs Console Pane */}
          <div className="flex-1 p-5 bg-slate-950 overflow-y-auto space-y-2 select-text font-mono text-slate-200">
            {filteredLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs">
                {logs.length === 0 ? (
                  <span>NO LOG ENTRIES RECORDED FOR THIS STAGE</span>
                ) : (
                  <span>NO LOGS MATCHING SEARCH QUERY</span>
                )}
              </div>
            ) : (
              filteredLogs.map((line, idx) => (
                <div key={idx} className="hover:bg-slate-900/40 py-0.5 px-1 rounded transition-colors">
                  {formatLogLine(line)}
                </div>
              ))
            )}
          </div>

          {/* Footer Status */}
          <div className="p-4 bg-slate-950 border-t border-slate-800 flex items-center justify-between text-3xs font-mono text-slate-500 tracking-wider">
            <span>SECURE CLEARANCE LEVEL 1</span>
            <span>SYSTEM CONSOLE v1.0.0</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#f6f4ef] text-slate-900 flex flex-col font-sans antialiased">
      {/* Header Banner */}
      <header className="border-b border-[#e5e3de] bg-white sticky top-0 z-40 shadow-2xs">
        <div className="max-w-5xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#1b6bf9] flex items-center justify-center text-white font-bold text-xs shadow-xs">
              TMA
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold text-[#1b6bf9] tracking-tight">TVA PATIENT TRIAGE</span>
              <span className="text-2xs font-medium text-slate-500 uppercase tracking-wider">TMA Virtual Assistant Builder</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {sessionState.trace_logs && Object.keys(sessionState.trace_logs).length > 0 && (
              <button
                type="button"
                onClick={() => {
                  const keys = Object.keys(sessionState.trace_logs || {});
                  if (keys.includes("finalize-estimate")) openTraceDrawer("finalize-estimate");
                  else if (keys.includes("propose-plan")) openTraceDrawer("propose-plan");
                  else openTraceDrawer("initialize");
                }}
                className="px-3 py-1.5 text-xs font-semibold tracking-wide border border-[#1b6bf9]/30 rounded-lg bg-[#edf4ff] text-[#1b6bf9] hover:bg-[#1b6bf9] hover:text-white transition-all cursor-pointer shadow-2xs"
              >
                Trace Logs
              </button>
            )}
            <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#1b6bf9] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#1b6bf9]"></span>
              </span>
              <span className="text-2xs font-medium tracking-wider text-slate-600 uppercase">
                Agent Pipeline Active
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-grow max-w-4xl w-full mx-auto px-6 py-10 flex flex-col justify-center">
        {renderStepIndicator()}

        {/* Global Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3 rounded-xl shadow-xs">
            <svg className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <span className="font-bold uppercase tracking-wider block text-xs mb-1">SYSTEM OUTAGE ALERT</span>
              {error}
            </div>
          </div>
        )}

        {/* Central Stage Wrapper */}
        <div className="bg-white border border-[#e4e2dd] rounded-2xl p-6 md:p-10 shadow-sm">
          
          {loading && (
            <div className="py-14 flex flex-col items-center justify-center gap-4">
              <div className="relative w-12 h-12">
                <div className="absolute inset-0 rounded-full border-2 border-[#1b6bf9]/20 animate-pulse"></div>
                <div className="absolute inset-0 rounded-full border-t-2 border-[#1b6bf9] animate-spin"></div>
              </div>
              <span className="text-xs font-semibold uppercase tracking-widest text-[#1b6bf9] animate-pulse">
                Consulting Agentic Pipeline...
              </span>
            </div>
          )}

          {!loading && (
            <>
              {/* STEP 1: INTAKE SCREEN */}
              {step === 1 && (
                <div className="space-y-6">
                  <div className="space-y-1.5 border-b border-slate-100 pb-5">
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                      Patient Symptom Intake
                    </h1>
                    <p className="text-sm text-slate-600">
                      Submit patient symptoms in plain language. The Triage Agent routes case profiles using dynamic RAG classification.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Symptom Description
                    </label>
                    <textarea
                      rows={5}
                      className="w-full border border-slate-200 rounded-xl bg-slate-50/50 p-4 text-sm font-sans placeholder-slate-400 focus:outline-none focus:border-[#1b6bf9] focus:bg-white focus:ring-2 focus:ring-[#1b6bf9]/20 transition-all resize-none"
                      placeholder="Enter description here (e.g. pain level, duration, compounding factors)..."
                      value={sessionState.raw_symptoms}
                      onChange={(e) => setSessionState({ ...sessionState, raw_symptoms: e.target.value })}
                    />
                  </div>

                  <div className="space-y-3">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                      Select Clinical Test Templates
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {PRESET_SYMPTOMS.map((preset) => (
                        <button
                          key={preset.label}
                          type="button"
                          className="text-left border border-slate-200 hover:border-[#1b6bf9] hover:bg-[#edf4ff]/40 bg-white p-4 rounded-xl transition-all shadow-2xs group cursor-pointer"
                          onClick={() => setSessionState({ ...sessionState, raw_symptoms: preset.desc })}
                        >
                          <span className="text-xs font-semibold text-slate-800 group-hover:text-[#1b6bf9] block transition-colors">
                            {preset.label}
                          </span>
                          <span className="text-2xs text-slate-500 line-clamp-1 mt-1 font-sans">
                            {preset.desc}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 flex justify-end border-t border-slate-100">
                    <button
                      type="button"
                      className="w-full md:w-auto px-7 py-3 bg-[#1b6bf9] hover:bg-[#1354cb] text-white rounded-xl text-sm font-semibold tracking-wide shadow-sm hover:shadow transition-all cursor-pointer"
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
                  <div className="space-y-1.5 border-b border-slate-100 pb-5">
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                      Department Dispatch Routing
                    </h1>
                    <p className="text-sm text-slate-600">
                      The Triage Agent routed the case to the following department suggestions. Verify and select the routing destination.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        RAG System Recommendations
                      </span>
                      {sessionState.trace_logs?.initialize && (
                        <button
                          type="button"
                          onClick={() => openTraceDrawer("initialize")}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#edf4ff] text-[#1b6bf9] border border-[#1b6bf9]/30 hover:bg-[#1b6bf9] hover:text-white transition-all cursor-pointer shadow-3xs inline-flex items-center gap-1.5"
                        >
                          <span className="h-2 w-2 rounded-full bg-[#1b6bf9] inline-block animate-pulse" />
                          View Triage Trace
                        </button>
                      )}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {sessionState.recommended_departments.map((dept, idx) => (
                        <button
                          key={dept}
                          type="button"
                          className={`p-5 border text-left rounded-xl transition-all cursor-pointer ${
                            sessionState.selected_department === dept
                              ? 'border-2 border-[#1b6bf9] bg-[#edf4ff] shadow-xs'
                              : 'border border-slate-200 hover:border-slate-300 bg-white'
                          }`}
                          onClick={() => setSessionState({ ...sessionState, selected_department: dept })}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold tracking-wider text-[#1b6bf9] uppercase">
                              Recommendation {idx === 0 ? "Primary" : "Secondary"}
                            </span>
                            {sessionState.selected_department === dept && (
                              <span className="w-2.5 h-2.5 rounded-full bg-[#1b6bf9]" />
                            )}
                          </div>
                          <span className="text-lg font-bold text-slate-900 block mt-2">
                            {dept}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3 border-t border-slate-100 pt-5">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                      Deviate and Dispatch Manually
                    </span>
                    <div className="flex gap-2">
                      <select
                        className="flex-1 border border-slate-200 rounded-xl bg-slate-50 p-3 text-sm focus:outline-none focus:border-[#1b6bf9] focus:bg-white"
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

                  <div className="pt-4 flex justify-between gap-4 border-t border-slate-100">
                    <button
                      type="button"
                      className="px-5 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-sm font-medium transition-all cursor-pointer"
                      onClick={() => setStep(1)}
                    >
                      Back to Intake
                    </button>
                    <button
                      type="button"
                      className="px-7 py-3 bg-[#1b6bf9] hover:bg-[#1354cb] text-white rounded-xl text-sm font-semibold tracking-wide shadow-sm hover:shadow transition-all cursor-pointer"
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
                  <div className="space-y-1.5 border-b border-slate-100 pb-5">
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                      Plan Confirmation & Coverage
                    </h1>
                    <p className="text-sm text-slate-600">
                      Verify procedure recommendations proposed by the Medical Planner Agent and input insurance details for cost calculations.
                    </p>
                  </div>

                  {/* Personal Care Assistant Walkthrough Header Box */}
                  {sessionState.package_analysis?.assistant_walkthrough && (
                    <div className="bg-[#edf4ff] border border-[#1b6bf9]/30 p-5 rounded-2xl flex items-start gap-4 shadow-2xs">
                      <div className="w-10 h-10 rounded-xl bg-[#1b6bf9] text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-xs">
                        AI
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs font-bold uppercase tracking-wider text-[#1b6bf9] block">
                          Personal Care Assistant Walkthrough
                        </span>
                        <p className="text-xs text-slate-700 leading-relaxed font-sans">
                          {sessionState.package_analysis.assistant_walkthrough}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Proposed Clinical Procedures with Simplification & Priority Categorization */}
                  <div className="space-y-5">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                        Categorized Clinical Package Recommendations
                      </span>
                      {sessionState.trace_logs?.["propose-plan"] && (
                        <button
                          type="button"
                          onClick={() => openTraceDrawer("propose-plan")}
                          className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#edf4ff] text-[#1b6bf9] border border-[#1b6bf9]/30 hover:bg-[#1b6bf9] hover:text-white transition-all cursor-pointer shadow-3xs inline-flex items-center gap-1.5"
                        >
                          <span className="h-2 w-2 rounded-full bg-[#1b6bf9] inline-block animate-pulse" />
                          View Planner Trace
                        </button>
                      )}
                    </div>

                    {/* Grouped Priorities: Level 1 (Must-Have), Level 2 (Recommended), Level 3 (Optional) */}
                    {[1, 2, 3].map((pLevel) => {
                      const analysisItems = sessionState.package_analysis?.categorized_items || [];
                      const levelItems = analysisItems.filter(item => item.priority_level === pLevel);
                      
                      // Fallback if no package analysis exists yet (legacy proposed_procedures list)
                      if (analysisItems.length === 0) {
                        if (pLevel !== 1) return null;
                        return (
                          <div key="legacy" className="space-y-3">
                            <span className="text-xs font-bold uppercase text-slate-700">Proposed Clinical Procedures</span>
                            <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white">
                              {sessionState.proposed_procedures.map((proc) => {
                                const isChecked = sessionState.confirmed_procedures.includes(proc);
                                return (
                                  <label key={proc} className="flex items-center gap-3.5 p-4 hover:bg-[#edf4ff]/30 cursor-pointer select-none">
                                    <input
                                      type="checkbox"
                                      className="w-4 h-4 accent-[#1b6bf9] rounded border-slate-300"
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
                                    <span className="text-sm font-medium text-slate-800">{proc}</span>
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        );
                      }

                      if (levelItems.length === 0) return null;

                      let badgeStyle = "bg-rose-100 text-rose-700 border-rose-200";
                      let levelTitle = "Must-Have (Priority 1)";
                      let levelSubtitle = "Mandatory coverage essential for your specific symptoms & acute risk areas.";

                      if (pLevel === 2) {
                        badgeStyle = "bg-amber-100 text-amber-800 border-amber-200";
                        levelTitle = "Recommended (Priority 2)";
                        levelSubtitle = "High-value preventive additions suited to your profile and care plan.";
                      } else if (pLevel === 3) {
                        badgeStyle = "bg-slate-100 text-slate-700 border-slate-200";
                        levelTitle = "Optional (Priority 3)";
                        levelSubtitle = "Secondary add-ons or lower-priority diagnostic coverage.";
                      }

                      return (
                        <div key={pLevel} className="space-y-3">
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                            <div>
                              <span className={`inline-block px-2.5 py-0.5 text-2xs font-bold uppercase tracking-wider rounded-md border ${badgeStyle}`}>
                                {levelTitle}
                              </span>
                              <p className="text-2xs text-slate-500 mt-1 font-sans">{levelSubtitle}</p>
                            </div>
                          </div>

                          <div className="space-y-3">
                            {levelItems.map((item) => {
                              const isChecked = sessionState.confirmed_procedures.includes(item.procedure_name);
                              return (
                                <div
                                  key={item.procedure_name}
                                  className={`border rounded-2xl p-5 transition-all bg-white shadow-2xs ${
                                    isChecked ? 'border-[#1b6bf9] ring-1 ring-[#1b6bf9]/20' : 'border-slate-200 opacity-80'
                                  }`}
                                >
                                  <div className="flex items-start gap-4">
                                    <input
                                      type="checkbox"
                                      className="w-5 h-5 accent-[#1b6bf9] rounded border-slate-300 mt-1 cursor-pointer"
                                      checked={isChecked}
                                      onChange={() => {
                                        if (isChecked) {
                                          setSessionState({
                                            ...sessionState,
                                            confirmed_procedures: sessionState.confirmed_procedures.filter((p) => p !== item.procedure_name),
                                          });
                                        } else {
                                          setSessionState({
                                            ...sessionState,
                                            confirmed_procedures: [...sessionState.confirmed_procedures, item.procedure_name],
                                          });
                                        }
                                      }}
                                    />
                                    <div className="flex-1 space-y-2">
                                      {/* Title & Technical Tag */}
                                      <div className="flex items-center justify-between flex-wrap gap-2">
                                        <h3 className="text-base font-bold text-slate-900">
                                          {item.plain_name}
                                        </h3>
                                        <span className="text-3xs font-mono bg-slate-100 text-slate-500 px-2 py-0.5 rounded border border-slate-200">
                                          {item.procedure_name}
                                        </span>
                                      </div>

                                      {/* Simplified Explanation */}
                                      <p className="text-xs text-slate-600 leading-relaxed font-sans">
                                        {item.simplified_explanation}
                                      </p>

                                      {/* Exclusions Plain */}
                                      <div className="text-2xs text-slate-400 font-mono">
                                        <span className="font-semibold text-slate-500 uppercase">Coverage Boundary: </span>
                                        {item.exclusions_plain}
                                      </div>

                                      {/* Contextual Justification Callout */}
                                      <div className="bg-[#edf4ff] border-l-3 border-[#1b6bf9] p-3 rounded-r-xl text-xs text-slate-700">
                                        <span className="font-bold text-[#1b6bf9] uppercase tracking-wider text-3xs block mb-0.5">
                                          Contextual Priority Reasoning
                                        </span>
                                        {item.justification}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div className="space-y-4 border-t border-slate-100 pt-5">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                      Insurance Policy Details
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-2xs font-semibold uppercase tracking-wider text-slate-500">
                          Insurance Provider
                        </label>
                        <select
                          className="w-full border border-slate-200 rounded-xl bg-slate-50 p-3 text-xs font-mono focus:outline-none focus:border-[#1b6bf9] focus:bg-white"
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
                        <label className="text-2xs font-semibold uppercase tracking-wider text-slate-500">
                          Policy Identifier Number
                        </label>
                        <input
                          type="text"
                          className="w-full border border-slate-200 rounded-xl bg-slate-50 p-3 text-xs font-mono focus:outline-none placeholder-slate-400 focus:border-[#1b6bf9] focus:bg-white"
                          placeholder="e.g. BC-98765-AX"
                          value={insurancePolicyId}
                          onChange={(e) => setInsurancePolicyId(e.target.value)}
                          disabled={insuranceProvider === "Self-Pay"}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 flex justify-between gap-4 border-t border-slate-100">
                    <button
                      type="button"
                      className="px-5 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-sm font-medium transition-all cursor-pointer"
                      onClick={() => setStep(2)}
                    >
                      Back to Routing
                    </button>
                    <button
                      type="button"
                      className="px-7 py-3 bg-[#1b6bf9] hover:bg-[#1354cb] text-white rounded-xl text-sm font-semibold tracking-wide shadow-sm hover:shadow transition-all cursor-pointer"
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
                  <div className="border border-slate-200 bg-[#faf8f5] p-7 rounded-2xl space-y-6 relative overflow-hidden shadow-xs">
                    <div className="absolute top-0 right-0 left-0 h-1.5 bg-[#1b6bf9]" />
                    
                    {/* Invoice Header */}
                    <div className="flex justify-between items-start flex-wrap gap-4 border-b border-slate-200 pb-4">
                      <div>
                        <h2 className="text-lg font-bold tracking-tight text-[#1b6bf9] uppercase">
                          St. Jude Health System
                        </h2>
                        <p className="text-2xs font-semibold text-slate-500 uppercase tracking-widest mt-1">
                          Preliminary Out-of-Pocket Cost Sheet
                        </p>
                      </div>
                      <div className="text-left md:text-right font-mono flex flex-col items-start md:items-end">
                        <span className="text-2xs text-slate-400 uppercase block">Case Identifier</span>
                        <span className="text-xs font-bold text-slate-900">{sessionState.patient_id}</span>
                        {sessionState.trace_logs?.["finalize-estimate"] && (
                          <button
                            type="button"
                            onClick={() => openTraceDrawer("finalize-estimate")}
                            className="mt-2 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[#edf4ff] text-[#1b6bf9] border border-[#1b6bf9]/30 hover:bg-[#1b6bf9] hover:text-white transition-all cursor-pointer shadow-3xs inline-flex items-center gap-1.5"
                          >
                            <span className="h-2 w-2 rounded-full bg-[#1b6bf9] inline-block animate-pulse" />
                            View Financial Trace
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Metadata Specs Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono border-b border-slate-200 pb-4">
                      <div>
                        <span className="text-2xs text-slate-400 uppercase block">Dispatch Dept</span>
                        <span className="font-semibold text-slate-900">{sessionState.selected_department}</span>
                      </div>
                      <div>
                        <span className="text-2xs text-slate-400 uppercase block">Insurance</span>
                        <span className="font-semibold text-slate-900">{sessionState.final_billing_payload?.insurance_provider}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-2xs text-slate-400 uppercase block">Policy reference</span>
                        <span className="font-semibold text-slate-900">{sessionState.final_billing_payload?.insurance_policy_id}</span>
                      </div>
                    </div>

                    {/* Invoice Table */}
                    <div className="space-y-2">
                      <span className="text-xs font-mono uppercase tracking-wider text-slate-500">
                        Itemized Transaction Audit
                      </span>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="border-b border-slate-200 text-slate-500 uppercase text-2xs">
                              <th className="py-2">Procedure / Code</th>
                              <th className="py-2 text-right">Standard Rate</th>
                              <th className="py-2 text-right">Co-Pay / Cover</th>
                              <th className="py-2 text-right">Out-of-Pocket</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {sessionState.final_billing_payload?.confirmed_services.map((svc) => {
                              const gross = sessionState.cost_estimation_breakdown[`${svc.procedure_name} (Gross)`] || 0;
                              const covered = sessionState.cost_estimation_breakdown[`${svc.procedure_name} (Insured Covers)`] || 0;
                              const oop = sessionState.cost_estimation_breakdown[`${svc.procedure_name} (Out-of-Pocket)`] || 0;
                              return (
                                <tr key={svc.service_code}>
                                  <td className="py-3 pr-2">
                                    <span className="font-semibold text-slate-900 block">{svc.procedure_name}</span>
                                    <span className="text-2xs text-slate-500 uppercase">{svc.service_code}</span>
                                  </td>
                                  <td className="py-3 text-right text-slate-600">${gross.toFixed(2)}</td>
                                  <td className="py-3 text-right text-[#1b6bf9] font-medium">-${covered.toFixed(2)}</td>
                                  <td className="py-3 text-right font-bold text-slate-900">${oop.toFixed(2)}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Cost Summary Box */}
                    <div className="border-t border-slate-200 pt-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div className="text-2xs text-slate-500 max-w-sm font-sans">
                        Audit Calculations finalized by Financial Estimator Agent. The estimates reflect contract agreements active under your selected policy terms.
                      </div>
                      <div className="text-left md:text-right font-mono bg-[#edf4ff] p-5 rounded-xl border border-[#1b6bf9]/30 w-full md:w-auto">
                        <span className="text-2xs text-[#1b6bf9] uppercase block tracking-wider font-bold">
                          Final Cost Responsibility
                        </span>
                        <span className="text-3xl font-extrabold text-[#1b6bf9] block mt-1">
                          ${sessionState.final_out_of_pocket_cost.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 flex justify-end">
                    <button
                      type="button"
                      className="w-full md:w-auto px-7 py-3 bg-[#1b6bf9] hover:bg-[#1354cb] text-white rounded-xl text-sm font-semibold tracking-wide shadow-sm hover:shadow transition-all cursor-pointer"
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
      <footer className="border-t border-[#e5e3de] bg-white py-6 text-center">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-mono text-slate-500">
          <span>&copy; 2026 St. Jude Healthcare Network. All Rights Reserved.</span>
          <span className="uppercase tracking-widest text-slate-500 font-semibold">TMA Virtual Assistant Clinical Suite</span>
        </div>
      </footer>
      {renderTraceDrawer()}
    </div>
  )
}