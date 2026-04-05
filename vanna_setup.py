"""
vanna_setup.py
Vanna 2.0 Agent using Groq with clinic DB schema in system prompt.
Schema is injected by prepending a system message to every LLM request.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from openai import AsyncOpenAI
from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.llm import LlmService, LlmRequest, LlmResponse
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory

DB_PATH = "clinic.db"
_agent  = None

# ── Clinic schema injected into every LLM call ───────────────────────────────
SYSTEM_PROMPT = """You are an expert SQL assistant for a clinic management system.
You have access to a SQLite database (clinic.db) with these exact tables:

TABLE patients (id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
TABLE doctors (id, name, specialization, department, phone)
TABLE appointments (id, patient_id, doctor_id, appointment_date, status, notes)
  -- status values: 'Scheduled', 'Completed', 'Cancelled', 'No-Show'
TABLE treatments (id, appointment_id, treatment_name, cost, duration_minutes)
TABLE invoices (id, patient_id, invoice_date, total_amount, paid_amount, status)
  -- status values: 'Paid', 'Pending', 'Overdue'

SQLite date functions: DATE('now','-30 days'), STRFTIME('%Y-%m', date_col)

When the user asks a question, use the run_sql tool to query this database and return real data.
Always generate a SELECT query and call the run_sql tool. Never say you don't have access to data.
"""


# ── Groq LLM Service ──────────────────────────────────────────────────────────
class GroqLlmService(LlmService):

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.model   = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    def _build_messages(self, request: LlmRequest) -> list:
        msgs = [{"role": m.role, "content": m.content} for m in request.messages]
        # Inject schema as system message if not already present
        if not msgs or msgs[0].get("role") != "system":
            msgs.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        else:
            # Append schema to existing system message
            msgs[0]["content"] = SYSTEM_PROMPT + "\n\n" + msgs[0]["content"]
        return msgs

    async def send_request(self, request: LlmRequest) -> LlmResponse:
        resp  = await self._client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(request),
            stream=False,
        )
        usage = resp.usage
        return LlmResponse(
            content=resp.choices[0].message.content,
            model=self.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
        )

    async def stream_request(self, request: LlmRequest):
        try:
            from vanna.core.llm import LlmStreamChunk
            use_chunk = True
        except ImportError:
            use_chunk = False

        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(request),
            stream=True,
        )

        tool_calls_acc = []
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue
            if delta.content:
                yield LlmStreamChunk(content=delta.content) if use_chunk else delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    while len(tool_calls_acc) <= idx:
                        tool_calls_acc.append({"id":"","name":"","arguments":""})
                    if tc.id: tool_calls_acc[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:      tool_calls_acc[idx]["name"]      += tc.function.name
                        if tc.function.arguments: tool_calls_acc[idx]["arguments"] += tc.function.arguments

        if tool_calls_acc and use_chunk:
            try:
                from vanna.core.llm import LlmStreamChunk
                yield LlmStreamChunk(content=None, tool_calls=tool_calls_acc)
            except Exception:
                pass

    def validate_tools(self, tools: list) -> list:
        return tools


# ── User Resolver ─────────────────────────────────────────────────────────────
class DefaultUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="default", name="Clinic User", group_memberships=["user","admin"])


# ── Agent factory ─────────────────────────────────────────────────────────────
def get_agent() -> Agent:
    global _agent
    if _agent is not None:
        return _agent

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not found in .env file.")

    db_tool      = RunSqlTool(sql_runner=SqliteRunner(database_path=DB_PATH))
    agent_memory = DemoAgentMemory(max_items=1000)

    tools = ToolRegistry()
    tools.register_local_tool(db_tool,                          access_groups=["user","admin"])
    tools.register_local_tool(VisualizeDataTool(),              access_groups=["user","admin"])
    tools.register_local_tool(SaveQuestionToolArgsTool(),       access_groups=["admin"])
    tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["user","admin"])

    _agent = Agent(
        llm_service=GroqLlmService(api_key=api_key),
        tool_registry=tools,
        user_resolver=DefaultUserResolver(),
        agent_memory=agent_memory,
        config=AgentConfig(),
    )
    print("✅ Vanna 2.0 Agent initialised with Groq + clinic schema.")
    return _agent


if __name__ == "__main__":
    print("Agent ready:", get_agent())