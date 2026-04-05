"""
main.py — FastAPI NL2SQL Clinic API
"""

import re, sqlite3, time, uuid
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from vanna_setup import get_agent
from vanna.core.user import RequestContext
from vanna.core.user.models import User
from vanna.core.tool import ToolContext

app = FastAPI(title="NL2SQL Clinic API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = "clinic.db"
_rate: dict[str, list[float]] = {}
_cache: dict[str, dict] = {}

# ── Rate limit ────────────────────────────────────────────────────────────────
def check_rate(ip):
    now = time.time()
    hits = [t for t in _rate.get(ip,[]) if now-t < 60]
    if len(hits) >= 20:
        raise HTTPException(429, "Rate limit exceeded.")
    hits.append(now); _rate[ip] = hits

# ── SQL validation ────────────────────────────────────────────────────────────
BLOCKED = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|EXECUTE|GRANT|REVOKE|SHUTDOWN|"
    r"xp_|sp_|sqlite_master|sqlite_sequence)\b", re.IGNORECASE)

def validate_sql(sql):
    s = sql.strip().lstrip(";").strip()
    if not s.upper().startswith("SELECT"):
        return False, "Only SELECT queries are allowed."
    m = BLOCKED.search(s)
    if m: return False, f"Blocked keyword: '{m.group()}'"
    return True, "ok"

# ── Models ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    @validator("question")
    def check(cls, v):
        v = v.strip()
        if not v: raise ValueError("Empty question.")
        if len(v) > 500: raise ValueError("Too long.")
        return v

class ChatResponse(BaseModel):
    message:   str
    sql_query: str | None = None
    columns:   list[str] | None = None
    rows:      list[list[Any]] | None = None
    row_count: int | None = None
    cached:    bool = False

# ── Helpers ───────────────────────────────────────────────────────────────────
def run_sql(sql):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [list(r) for r in cur.fetchall()]
    finally:
        conn.close()

def extract_sql(text):
    # Try fenced block first
    m = re.search(r"```(?:sql)?\s*(SELECT[\s\S]+?)```", text, re.IGNORECASE)
    if m: return m.group(1).strip()
    # Bare SELECT
    m = re.search(r"(SELECT\b[\s\S]+?)(?:;|$)", text, re.IGNORECASE)
    if m: return m.group(1).strip()
    return None

def clean_message(raw: str) -> str:
    """Extract only the plain text from Vanna's streaming component objects."""
    # Pull out simple_component=None... text='...' patterns
    matches = re.findall(r"simple_component=\w+\s*['\"]?([^'\"<>]+)['\"]?", raw)
    if matches:
        clean = " ".join(m.strip() for m in matches if len(m.strip()) > 5)
        if clean:
            return clean

    # Try to find quoted human-readable sentences
    sentences = re.findall(r"[A-Z][^<>{}=\[\]]{15,}[.!?]", raw)
    if sentences:
        return " ".join(sentences[:3])

    # Fallback — strip all component noise
    clean = re.sub(r"\w+=<[^>]+>", "", raw)
    clean = re.sub(r"\w+=\w+\([^)]*\)", "", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    return clean[:300] if clean else "Query processed."

# ── /chat ─────────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    check_rate(request.client.host)
    q = body.question

    if q in _cache:
        return {**_cache[q], "cached": True}

    agent   = get_agent()
    req_ctx = RequestContext(headers={}, conversation_id=str(uuid.uuid4()))

    raw_response = ""
    try:
        async for chunk in agent.send_message(request_context=req_ctx, message=q):
            if hasattr(chunk, "simple_component") and chunk.simple_component:
                t = getattr(chunk.simple_component, "text", None)
                if t: raw_response += str(t)
            elif hasattr(chunk, "text") and chunk.text:
                raw_response += str(chunk.text)
            else:
                raw_response += str(chunk)
    except Exception as e:
        raise HTTPException(500, f"Agent error: {e}")

    # Try to extract SQL from the full raw response
    sql = extract_sql(raw_response)

    if not sql:
        return ChatResponse(message=clean_message(raw_response) or "Could not generate SQL. Try rephrasing.")

    ok, reason = validate_sql(sql)
    if not ok:
        return ChatResponse(message=f"Query blocked: {reason}", sql_query=sql)

    try:
        columns, rows = run_sql(sql)
    except Exception as e:
        return ChatResponse(message=f"Query failed: {e}", sql_query=sql)

    if not rows:
        return ChatResponse(message="No data found.", sql_query=sql, columns=columns, rows=[], row_count=0)

    summary = f"Result: {rows[0][0]}" if len(columns)==1 and len(rows)==1 else f"Found {len(rows)} result(s)."
    result  = dict(message=summary, sql_query=sql, columns=columns, rows=rows[:100], row_count=len(rows), cached=False)
    _cache[q] = result
    return result

# ── /health ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    db_ok = "connected"
    try:
        c = sqlite3.connect(DB_PATH); c.execute("SELECT 1"); c.close()
    except Exception:
        db_ok = "error"

    mem_count = 0
    try:
        mem = get_agent().agent_memory
        for attr in ("_memories","_items","_store","memories","items"):
            val = getattr(mem, attr, None)
            if val is not None:
                mem_count = len(val); break
    except Exception:
        pass

    return {"status":"ok","database":db_ok,"agent_memory_items":mem_count}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)