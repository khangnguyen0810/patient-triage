# Patient Triage & Financial Estimation System

An intelligent patient triage and medical cost estimation REST API powered by a Multi-Agent architecture (Triage Agent, Medical Planner, and Financial Estimator) combined with Retrieval-Augmented Generation (RAG).

---

## ⚙️ Tech Stack

* **Language & Package Manager:** Python 3.12+ managed via **`uv`** (`pyproject.toml`, `uv.lock`).
* **Web Framework:** **FastAPI** & **Uvicorn** serving a stateless REST API.
* **AI & Agent Framework:** **Google GenAI SDK** & **Google ADK (Agent Development Kit)**.
* **Vector Database (RAG):** **ChromaDB Cloud** (`hospital_routing` collection) for semantic symptom-to-department routing.
* **Relational Database:** **Supabase** (PostgreSQL) for managing diagnostic bundles, service codes, and insurance coverage rules.
* **State Engine:** **Pydantic** (`PatientSessionState`) for data validation and sequential pipeline tracking across endpoints.

---

## 🔄 Workflow & Pipeline Architecture

The system processes requests through a sequential state-passing pipeline:


```

[Symptom Input] ➔ [1. Triage Agent / RAG] ➔ [2. Select Dept] ➔ [3. Medical Planner] ➔ [4. Confirm Plan & Ins] ➔ [5. Financial Estimator] ➔ [6. Final Breakdown]

```

1. **Symptom Intake & Routing:** Accepts patient symptom strings and queries ChromaDB Cloud to identify top candidate departments.
2. **Department Selection:** Updates the session state with the selected hospital division.
3. **Medical Plan Proposal:** Queries Supabase procedure catalogs to recommend diagnostic packages for the target department.
4. **Plan & Insurance Confirmation:** Captures patient-confirmed diagnostic packages and active insurance details (carrier name and policy ID).
5. **Price & Coverage Resolution:** Matches items to base pricing tables in Supabase and applies network insurance carrier rules.
6. **Financial Calculation:** Outputs an itemized financial summary and total out-of-pocket cost responsibility.

---

## 📊 Environment & Database Prerequisites

Ensure database collections and tables are configured before starting the API server:

### 1. ChromaDB Cloud (Vector Store)
* Collection `hospital_routing`: Stores semantic descriptions and handled conditions per medical department.

### 2. Supabase (Relational Database)
* `departments`: Directory of medical divisions.
* `procedures`: Clinical examination packages mapped to departments.
* `service_codes`: Itemized billing codes paired with base unit rates.
* `insurance_rules`: Provider coverage tiers and reimbursement rates.

---

## 📥 Installation & Setup

### 1. Environment Synchronization
Install project dependencies locked in `uv.lock`:
```bash
uv sync

```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
CHROMADB_API_KEY=your_chromadb_api_key
CHROMADB_TENANT=your_tenant
CHROMADB_DATABASE=your_database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

```

### 3. Database Seeding

Seed department routes into ChromaDB Cloud:

```bash
uv run python src/triage_system/scripts/seed_departments.py

```

---

## 🚀 Running the API Server

Start the REST API server locally using `uv` and `uvicorn`:

```bash
uv run uvicorn triage_system.api:app --host 127.0.0.1 --port 8000 --reload

```

Once running, access the interactive Swagger documentation in your browser at:
👉 **`http://127.0.0.1:8000/docs`**

---

## 🌐 REST API Endpoints

| Endpoint | Method | Payload / Params | Description |
| --- | --- | --- | --- |
| `/api/pipeline/initialize` | `POST` | `{"raw_symptoms": ["string"]}` | Starts a session, executes Triage Agent RAG routing, and returns state with recommended departments. |
| `/api/pipeline/propose-plan` | `POST` | `PatientSessionState` | Accepts state containing `selected_department`, runs Medical Planner Agent, and populates proposed diagnostic tests. |
| `/api/pipeline/finalize-estimate` | `POST` | `PatientSessionState` | Accepts state containing `confirmed_procedures` & `insurance_details`, serializes billing, and calculates final out-of-pocket costs. |

---

## 🧪 Testing & Execution Modes

Run unit tests across agent tools:

```bash
uv run pytest

```

Run legacy CLI interactive terminal mode:

```bash
uv run python src/triage_system/main.py

```
