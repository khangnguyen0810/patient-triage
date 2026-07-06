# src/triage_system/agents/triage_agent.py
from google import genai
from google.genai import types
from triage_system.core.state import PatientSessionState
from triage_system.tools.rag_tool import DepartmentRAGTool
import json


class TriageAgent:
    def __init__(self, rag_tool: DepartmentRAGTool, max_tool_calls: int = 4):
        self.rag_tool = rag_tool
        self.ai_client = genai.Client()
        self.model_name = "gemini-3.1-flash-lite"
        self.max_tool_calls = (
            max_tool_calls  # safety cap on agent loop, not on retrieval
        )

        self.tool_declaration = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="retrieve_relevant_departments",
                    description=(
                        "Semantic search over the hospital department knowledge base. "
                        "Call this with a focused symptom description to get candidate "
                        "departments with similarity distances. Call it again with a "
                        "reformulated query if results seem weak or symptoms span "
                        "multiple systems (e.g. search separately for 'chest pain' vs "
                        "'numbness in arm')."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Symptom-focused search text.",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of candidates to retrieve (default 5).",
                            },
                        },
                        "required": ["query"],
                    },
                )
            ]
        )

    def _dispatch_tool_call(self, function_call) -> dict:
        args = function_call.args or {}
        query = args.get("query", "")
        top_k = int(args.get("top_k", 5))
        results = self.rag_tool.retrieve_relevant_departments(query, top_k=top_k)
        return {"results": results}

    def execute_triage(self, state: PatientSessionState) -> PatientSessionState:
        if not state.raw_symptoms:
            raise ValueError("Execution Error: Symptom list is missing.")

        full_symptom_description = " ".join(state.raw_symptoms)

        system_instruction = (
            "You are an advanced hospital routing coordinator. You have access to a "
            "retrieve_relevant_departments tool that searches a vector database of "
            "hospital departments. Use it as many times as you need — reformulating "
            "your query, or issuing separate searches for distinct symptom clusters — "
            "until you're confident in your routing decision. Once confident, respond "
            "with ONLY a JSON array of exactly two department names, e.g. "
            '["Cardiology", "Pulmonology"], using the exact spelling returned by the tool. '
            "Do not invent department names that were never returned by the tool."
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=f"Patient symptoms: {full_symptom_description}\n"
                        "Investigate using the retrieval tool, then give your final answer."
                    )
                ],
            )
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            tools=[self.tool_declaration],
        )

        final_departments = None

        for turn in range(self.max_tool_calls):
            response = self.ai_client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            print(response.text)
            candidate = response.candidates[0]
            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if getattr(part, "function_call", None)
            ]

            if not function_calls:
                # Model decided it's done — parse final answer
                final_departments = self._parse_final_answer(response.text)
                break

            # Append model's turn (including its tool call requests)
            contents.append(candidate.content)

            # Execute each requested tool call and feed results back
            tool_response_parts = []
            for fc in function_calls:
                tool_result = self._dispatch_tool_call(fc)
                tool_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name, response=tool_result
                        )
                    )
                )
            contents.append(types.Content(role="user", parts=tool_response_parts))

        if final_departments is None:
            # Loop exhausted without a clean answer — fail safe, don't crash
            fallback = self.rag_tool.retrieve_relevant_departments(
                full_symptom_description, top_k=2
            )
            final_departments = [m["department_name"] for m in fallback]

        state.recommended_departments = final_departments
        return state

    def _parse_final_answer(self, text: str) -> list:
        text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            pass
        # Fallback: comma-split, for models that ignore JSON instruction
        return [d.strip() for d in text.split(",") if d.strip()]
