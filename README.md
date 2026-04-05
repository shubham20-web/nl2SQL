# NL2SQL Clinic API

An AI-powered Natural Language to SQL system built with **Vanna AI 2.0**, **FastAPI**, and **SQLite**.  
Ask questions in plain English — get SQL results from a clinic database instantly.

---

## LLM Provider

**Google Gemini** (`gemini-2.5-flash`) via Google AI Studio free tier.

---

## Project Structure

```
nl2sql-clinic/
├── setup_database.py   # Creates clinic.db with schema + dummy data
├── seed_memory.py      # Seeds agent memory with 15 Q&A pairs
├── vanna_setup.py      # Vanna 2.0 Agent initialisation
├── main.py             # FastAPI application
├── requirements.txt    # All dependencies
├── .env                # API key (not committed to git)
├── clinic.db           # Generated SQLite database
├── README.md
└── RESULTS.md          # Test results for 20 questions
```

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd nl2sql-clinic
```

### 2. Create and activate a virtual environment (recommended)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your API key
Create a `.env` file in the project root:
```
GOOGLE_API_KEY=your-gemini-api-key-here
```
Get a free key at: https://aistudio.google.com/apikey

### 5. Create the database
```bash
python setup_database.py
```
This creates `clinic.db` and prints a summary of inserted records.

### 6. Seed agent memory
```bash
python seed_memory.py
```
This pre-loads 15 question→SQL pairs so the agent performs well from the start.

### 7. Start the API server
```bash
uvicorn main:app --port 8000 --reload
```

Or run everything in one command:
```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

---

## API Documentation

### POST `/chat`
Ask a natural language question about the clinic.

**Request:**
```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

**Response:**
```json
{
  "message": "Found 5 result(s).",
  "sql_query": "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM invoices i JOIN patients p ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [["John", "Smith", 4500.0], ["Jane", "Doe", 3200.0]],
  "row_count": 5,
  "cached": false
}
```

### GET `/health`
Returns system status.

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15
}
```

---

## Architecture Overview

```
User Question (English)
        |
        v
   FastAPI /chat endpoint
        |
        v
   Input Validation (length, empty check)
        |
        v
   Vanna 2.0 Agent
   (GeminiLlmService + DemoAgentMemory + Tools)
        |
        v
   SQL Extraction from agent response
        |
        v
   SQL Validation (SELECT only, no dangerous keywords)
        |
        v
   SQLite Execution (clinic.db)
        |
        v
   JSON Response (message + sql + columns + rows)
```

---

## SQL Safety

All generated SQL is validated before execution:
- Only `SELECT` statements are allowed
- Blocked keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `EXEC`, `GRANT`, `REVOKE`, `SHUTDOWN`, `xp_`, `sp_`
- System tables (`sqlite_master`) are blocked

---

## Bonus Features Implemented

- ✅ Input validation (empty check, max 500 chars)
- ✅ Query caching (repeated questions skip the LLM)
- ✅ Rate limiting (20 requests/minute per IP)
- ✅ CORS enabled for browser-based testing
