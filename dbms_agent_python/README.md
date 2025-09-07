# DBMS Agent (Python, LangChain/LangGraph)

This directory contains the Python implementation of a Database Management System (DBMS) agent leveraging LangChain and LangGraph. The agent enables natural language (NL2SQL) interaction with SQL databases (with a focus on Azure SQL DB), following the architecture and research outlined in the included `RESEARCH_SUMMARY.md`.

## Structure

- `dbms_agent/` — Core agent modules (semantic model analysis, NL2SQL, query execution, MCP integration)
- `tests/` — Unit and integration tests
- `RESEARCH_SUMMARY.md` — Research and architecture reference

## Setup

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `../.env.example.shared` or `./.env.example` to `.env` and populate required values (Cosmos + OpenAI + execution flags). Use a secrets manager or Azure Container Apps secrets in production.

### Environment Variables (Agent-Focused)
| Variable | Purpose |
|----------|---------|
| `USE_REMOTE_MCP` | Prefer remote MCP tool execution over local pyodbc |
| `MCP_HTTP_BASE_URL` | Base URL of deployed MCP HTTP bridge (e.g. `https://yourapp.region.azurecontainerapps.io`) |
| `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding generation |
| `COSMOS_ENDPOINT` / `COSMOS_KEY` / `COSMOS_DATABASE` / `COSMOS_CONTAINER` | Vector store for schema embeddings |
| `AZURE_SQL_SERVER` / `AZURE_SQL_DATABASE` / `AZURE_SQL_USER` / `AZURE_SQL_PASSWORD` | Optional local SQL auth fallback |
| `AZURE_SQL_DRIVER` | ODBC driver name (default `ODBC Driver 18 for SQL Server`) |
| `MCP_API_KEY` | (Planned) HTTP bridge auth header token |

### Orchestrator
Instantiate and query:
```python
from dbms_agent import DBMSAgent
agent = DBMSAgent()
resp = agent.answer("List top customers by revenue")
print(resp["markdown"])
```

### Current Limitations
- Table selection & NL2SQL generation use placeholder logic.
- No authentication yet on HTTP bridge.
- No incremental schema refresh implemented.

### Planned Enhancements
- Embedding similarity search for table ranking.
- Risk filtering (detect destructive statements).
- API key / AAD auth enforcement for remote calls.
- Integration tests using a containerized MSSQL sample DB.

## Development Plan

See `RESEARCH_SUMMARY.md` for the high-level plan and architecture.

---
