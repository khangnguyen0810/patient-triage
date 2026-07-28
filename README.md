# Patient Triage & Financial Estimation System

An intelligent patient triage and automated medical cost estimation system. It leverages a Multi-Agent architecture (Triage Agent, Medical Planner, Financial Estimator) combined with a Retrieval-Augmented Generation (RAG) mechanism to optimize patient routing and bring transparency to healthcare financing.

---

## ⚙️ Tech Stack

Based on the project's codebase, the core technologies include:
*   **Language & Package Management:** Python 3.12+, using the **`uv`** tool to manage virtual environments and dependencies (`pyproject.toml`, `uv.lock`).
*   **AI & Agent Framework:** Google GenAI SDK & Google ADK (Agent Development Kit) to construct the Multi-Agent system and define clinical and financial tools.
*   **Vector Database (RAG):** **ChromaDB Cloud** for storing embeddings and performing semantic search across hospital departments.
*   **Primary Database:** **Supabase** for managing relational database structures (examination package information, insurance codes, and pricing tables).

---

## 📊 Prerequisites (Data Setup)

To ensure correct system operation, data must be prepared and synchronized across two storage platforms:

### 1. On ChromaDB Cloud (Vector Database)
*   **Collection `hospital_routing`**: A vector space storing semantic descriptions for each department (detailed symptom lists and medical conditions handled by that division). This data feeds the RAG mechanism, allowing the `Triage Agent` to make highly precise routing decisions.

### 2. On Supabase (Relational Database)
*   `departments`: Administrative directory of hospital departments/divisions.
*   `procedures`: List of examination packages and clinical services mapped to each department.
*   `service_codes`: Service billing codes paired with base prices for each diagnostic item.
*   `insurance_rules`: Coverage policies, rules, and reimbursement rates for different insurance carriers.

---

## 🔄 Workflow

The system operates in a strict sequential pipeline through the following steps:


```

[Symptom Intake] ➔ [RAG Routing] ➔ [Select Dept] ➔ [Fetch Packages] ➔ [Confirm Plan & Ins] ➔ [Resolve Costs] ➔ [Output Summary]

```

1.  **Symptom Intake:** The user inputs a description of the patient's current health status or symptoms.
2.  **Automated Routing (RAG):** The `Triage Agent` activates the RAG tool connected to ChromaDB Cloud, running a semantic query against the `hospital_routing` collection to identify the **2 most relevant departments**.
3.  **Department Selection:** The user selects the exact department they wish to register for from the 2 system recommendations.
4.  **Package Retrieval:** The system accesses the database's `procedures` table to pull all available diagnostic bundles/procedures for the chosen department.
5.  **Plan Confirmation & Insurance:** The user selects their desired examination packages and inputs their health insurance details (provider name and policy ID).
6.  **Price Resolution:** The system matches data between `service_codes` (to fetch base unit prices) and `insurance_rules` (to evaluate specific network coverage rates).
7.  **Financial Calculation:** The Financial Agent executes itemized arithmetic calculations, applying insurance rules to generate a final out-of-pocket cost summary that the patient is responsible for.

---

## 📥 System Inputs & Outputs

*   **Inputs:**
    *   Raw patient symptom description string.
    *   Target department selection.
    *   List of chosen clinical packages/procedures.
    *   Patient-provided insurance details (carrier name, policy ID).
*   **Outputs:**
    *   Itemized cost breakdown and final out-of-pocket expenditure (adjusted for active insurance coverage rules).

---

## 🚀 Installation & Quick Start

Since the project integrates the high-performance `uv` package manager, setting up the environment is exceptionally fast.

### 1. Environment Synchronization
Install all project dependencies locked in `uv.lock`:
```bash
uv sync

```

### 2. Database Seeding

Run the data setup script to seed department routes directly into ChromaDB Cloud:

```bash
uv run python src/triage_system/scripts/seed_departments.py

```

### 3. Running the Application

Execute the main entry point to initiate the patient triage pipeline:

```bash
uv run python src/triage_system/main.py

```

### 4. Running Tests

If you want to verify the system integrity across your medical and financial agents:

```bash
uv run pytest

```
