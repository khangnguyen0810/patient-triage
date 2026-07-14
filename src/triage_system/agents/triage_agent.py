# src/triage_system/agents/triage_agent.py
import json
import asyncio
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool

APP_NAME = "triage_system"


class TriageAgent:
    def __init__(self, rag_tool: DepartmentRAGTool, max_tool_calls: int = 4):
        self.rag_tool = rag_tool
        self.max_tool_calls = max_tool_calls

        # Closes over self.rag_tool so ADK calls the *same* DB-backed instance
        # main.py already constructed, rather than spinning up a second one.
        def retrieve_relevant_departments(query: str, top_k: int = 5) -> dict:
            """Searches the hospital department knowledge base for departments
            relevant to a symptom description. Call this with a focused symptom
            phrase. If results look weak or symptoms span multiple systems, call
            again with a reformulated or more specific query (e.g. separate calls
            for 'chest pain' and 'numbness in arm').

            Args:
                query: A symptom-focused search phrase.
                top_k: Number of candidate departments to retrieve (default 5).

            Returns:
                A dict with a "status" key and a "results" list of
                {"department_name": str, "distance": float} matches, ordered by
                relevance (lower distance = better match).
            """
            matches = self.rag_tool.retrieve_relevant_departments(query, top_k=top_k)
            if not matches:
                return {"status": "no_results", "results": []}
            return {"status": "success", "results": matches}

        self._adk_agent = Agent(
            model="gemini-3.1-flash-lite",
            name="triage_agent",
            description="Routes a patient's described symptoms to the two most relevant hospital departments.",
            instruction=(
                "You are an advanced hospital routing coordinator. Use the "
                "retrieve_relevant_departments tool to search the department knowledge "
                "base — call it as many times as needed, reformulating the query for "
                "distinct symptom clusters, until you are confident in your routing "
                "decision. Once confident, respond with ONLY a JSON array of exactly "
                'two department names, e.g. ["Cardiology", "Pulmonology"], using the '
                "exact spelling returned by the tool. Never invent a department name "
                "that the tool did not return."
            ),
            tools=[retrieve_relevant_departments],
        )

        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._adk_agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )

    async def _run_async(self, user_id: str, session_id: str, prompt: str) -> str:
        await self._session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        final_text = None
        tool_call_count = 0
        async for event in self._runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if (
                getattr(event, "get_function_calls", None)
                and event.get_function_calls()
            ):
                tool_call_count += 1
                if tool_call_count > self.max_tool_calls:
                    break
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
        return final_text or ""

    async def execute_triage(self, state: PatientSessionState) -> PatientSessionState:
        if not state.raw_symptoms:
            raise ValueError("Execution Error: Symptom list is missing.")

        print(
            f"[TriageAgent] Processing symptoms for ID {state.patient_id}: {state.raw_symptoms}"
        )

        full_symptom_description = " ".join(state.raw_symptoms)
        prompt = (
            f"Patient symptoms: {full_symptom_description}\n"
            "Investigate using the retrieval tool, then give your final answer."
        )

        try:
            raw_output = await self._run_async(
                user_id=str(state.patient_id),
                session_id=f"triage-{state.patient_id}",
                prompt=prompt,
            )
            print(f"[TriageAgent] Live ADK Agent Raw Output: '{raw_output}'")
            refined_departments = self._parse_final_answer(raw_output)
        except Exception as exc:
            print(
                f"[TriageAgent] ADK agent run failed ({exc}); falling back to raw retrieval."
            )
            refined_departments = []

        if not refined_departments:
            fallback = self.rag_tool.retrieve_relevant_departments(
                full_symptom_description, top_k=2
            )
            refined_departments = [m["department_name"] for m in fallback]

        state.recommended_departments = refined_departments
        return state

    @staticmethod
    def _parse_final_answer(text: str) -> list:
        text = (text or "").strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            pass
        return [d.strip() for d in text.split(",") if d.strip()]
