# src/triage_system/agents/triage_agent.py
from google.adk.tools import tool_configs
from _pytest import mark
import json
import asyncio
import contextvars
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool

APP_NAME = "triage_system"

# Context-Local Logging Pattern for thread-safe session tracing
triage_logs_var = contextvars.ContextVar("triage_logs", default=None)


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
            logs = triage_logs_var.get()
            if logs is not None:
                logs.append(
                    f"[RAGTool] Querying chroma vector database with search phrase: '{query}' (top_k={top_k})..."
                )

            matches = self.rag_tool.retrieve_relevant_departments(query, top_k=top_k)

            if logs is not None:
                if not matches:
                    logs.append("[RAGTool] Chroma vector database returned 0 results.")
                else:
                    logs.append(
                        f"[RAGTool] Chroma vector database returned {len(matches)} matching candidates:"
                    )
                    for m in matches:
                        similarity = max(0.0, 1.0 - m["distance"] / 2.0) * 100
                        logs.append(
                            f"  - {m['department_name']} (Similarity score: {similarity:.2f}%, distance: {m['distance']:.4f})"
                        )

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

    async def _run_async(
        self, user_id: str, session_id: str, prompt: str, state: PatientSessionState
    ) -> str:
        await self._session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        final_text = None
        tool_call_count = 0

        logs = triage_logs_var.get()
        if logs is not None:
            logs.append(
                f"[TriageAgent] Starting ADK Runner with instruction and prompt..."
            )

        # Set model metadata in the state
        state.ai_model_name = self._adk_agent.model
        state.prompt_tokens = 0
        state.candidate_tokens = 0

        async for event in self._runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if hasattr(event, "usage_metadata") and event.usage_metadata:
                state.prompt_tokens += getattr(event.usage_metadata, "prompt_token_count", 0)
                state.candidate_tokens += getattr(event.usage_metadata, "candidates_token_count", 0)

            if logs is not None:
                # Capture LLM thought or reasoning output
                if hasattr(event, "content") and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            # Split into lines and keep it readable
                            reasoning = part.text.strip()
                            if reasoning:
                                logs.append(
                                    f"[TriageAgent] [Model Thought] {reasoning}"
                                )

                # Capture tool call request
                if hasattr(event, "get_function_calls") and event.get_function_calls():
                    for call in event.get_function_calls():
                        logs.append(
                            f"[TriageAgent] [Tool Call] Requesting tool '{call.name}' with arguments: {call.args}"
                        )

                # Capture tool response
                if (
                    hasattr(event, "get_function_responses")
                    and event.get_function_responses()
                ):
                    for resp in event.get_function_responses():
                        logs.append(
                            f"[TriageAgent] [Tool Response] Tool '{resp.name}' returned payload."
                        )

            if (
                getattr(event, "get_function_calls", None)
                and event.get_function_calls()
            ):
                tool_call_count += 1
                if tool_call_count > self.max_tool_calls:
                    if logs is not None:
                        logs.append(
                            f"[TriageAgent] Maximum tool calls ({self.max_tool_calls}) exceeded."
                        )
                    break
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text
        return final_text or ""

    async def execute_triage(self, state: PatientSessionState) -> PatientSessionState:
        if not state.raw_symptoms:
            raise ValueError("Execution Error: Symptom list is missing.")

        if not state.trace_logs:
            state.trace_logs = {}
        state.trace_logs["initialize"] = []
        logs = state.trace_logs["initialize"]

        logs.append(
            f"[System] Intake symptoms registered for reference: '{state.raw_symptoms}'"
        )
        logs.append(
            f"[TriageAgent] Processing symptoms for Patient ID {state.patient_id}..."
        )

        print(
            f"[TriageAgent] Processing symptoms for ID {state.patient_id}: {state.raw_symptoms}"
        )

        prompt = (
            f"Patient symptoms: {state.raw_symptoms}\n"
            "Investigate using the retrieval tool, then give your final answer."
        )

        token = triage_logs_var.set(logs)
        try:
            raw_output = await self._run_async(
                user_id=str(state.patient_id),
                session_id=f"triage-{state.patient_id}",
                prompt=prompt,
                state=state,
            )
            print(f"[TriageAgent] Live ADK Agent Raw Output: '{raw_output}'")
            refined_departments = self._parse_final_answer(raw_output)
        except Exception as exc:
            logs.append(
                f"[Error] ADK agent execution failed: {exc}. Falling back to manual RAG database query."
            )
            print(
                f"[TriageAgent] ADK agent run failed ({exc}); falling back to raw retrieval."
            )
            refined_departments = []
        finally:
            triage_logs_var.reset(token)


        if not refined_departments:
            logs.append(
                f"[RAGTool] Executing fallback Chroma query directly for symptoms: '{state.raw_symptoms}'"
            )
            fallback = self.rag_tool.retrieve_relevant_departments(
                state.raw_symptoms, top_k=2
            )
            refined_departments = [m["department_name"] for m in fallback]
            for m in fallback:
                similarity = (
                    round((1.0 - m["distance"]) * 100, 1)
                    if m.get("distance") is not None
                    else 0.0
                )
                logs.append(
                    f"  - {m['department_name']} (distance: {m['distance']:.4f})"
                )

        state.recommended_departments = refined_departments
        logs.append(
            f"[System] Triage Dispatch completed. Recommended departments: {state.recommended_departments}"
        )
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
