# DBMS Assistant SK

![Architecture Diagram](docs/architecture.png)

## Overview

This repository contains two main components:

1. **Legacy .NET/Semantic Kernel Agent** (in `src/`):
   - Original implementation using Microsoft Semantic Kernel and .NET for NL2SQL and database agent workflows.
2. **New Python/LangChain-LangGraph Agent** (in `dbms_agent_python/`):
   - Modern, modular Python implementation using LangChain, LangGraph, and Azure services.

---

## Python Agent (dbms_agent_python)

A modular, extensible DBMS agent solution in Python, designed for natural language to SQL (NL2SQL) workflows, leveraging Azure OpenAI, **Azure Cosmos DB (only vector/embedding store)**, and Azure SQL DB. (Azure AI Search option was evaluated but intentionally deprecated in favor of Cosmos DB for simplified dependency + unified storage.)

### Key Features
- **Semantic Model Analysis:**
  - DDL/DML analysis, schema embedding (Azure OpenAI), and storage in Cosmos DB.
- **NL2SQL Agent:**
  - Table selection, SQL generation (LLM-based), and quality filters.
- **Query Execution:**
  - Secure SQL execution on Azure SQL DB, markdown result formatting, and feedback collection.
- **Environment-based configuration** for all Azure resources.

### Directory Structure
- `dbms_agent_python/`
  - `dbms_agent/`
    - `semantic_model.py` — Schema analysis, embedding, Cosmos DB integration
    - `nl2sql.py` — NL2SQL agent logic
    - `query_execution.py` — SQL execution, formatting, feedback
    - `mcp_integration.py` — (Stub) MCP protocol integration
  - `requirements.txt` — Python dependencies
  - `README.md` — Python agent documentation
  - `RESEARCH_SUMMARY.md` — Research and architecture reference
  - `tests/` — (To be implemented)

### Setup
1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r dbms_agent_python/requirements.txt
   ```
3. Set required environment variables for Azure OpenAI, Cosmos DB, and Azure SQL DB. See the new environment templates:
  - `.env.example.shared` (top-level consolidated variables)
  - `MssqlMcpServer/Node/.env.example` (Node MCP server only)
  - `dbms_agent_python/.env.example` (Python agent only)

### Environment Variables (Summary)
| Purpose | Variable | Notes |
|---------|----------|-------|
| AAD Identity | `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` | Used by Node MCP server to obtain access tokens for Azure SQL |
| SQL Target | `SERVER_NAME`, `DATABASE_NAME` | Server FQDN + DB name |
| SQL Mode | `READONLY` | `true` restricts to read tools only |
| Connection | `TRUST_SERVER_CERTIFICATE`, `CONNECTION_TIMEOUT` | TLS trust override (keep `false` in prod) + timeout seconds |
| HTTP Bridge | `HTTP_PORT` | Enables HTTP transport for MCP server (default 8080) |
| Python Exec Mode | `USE_REMOTE_MCP`, `MCP_HTTP_BASE_URL` | Force remote tool path and target base URL |
| OpenAI Embeddings | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model `text-embedding-3-small` by default |
| Cosmos DB Vector Store | `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `COSMOS_CONTAINER` | Embedding storage (partition key `/table_name`) |
| Direct SQL Auth (optional) | `AZURE_SQL_SERVER`, `AZURE_SQL_DATABASE`, `AZURE_SQL_USER`, `AZURE_SQL_PASSWORD`, `AZURE_SQL_DRIVER` | Only if not using AAD token path |
| Future Auth | `MCP_API_KEY` | Placeholder for securing HTTP bridge |
| Logging | `LOG_LEVEL` | `info` / `debug` |

Provide real secrets via Azure Container Apps secrets, not committed `.env` files.

---

## Architecture

The solution follows the architecture below:

- **Semantic Model Analysis:** Extracts and embeds schema, stores in vector DB (Cosmos DB).
- **NL2SQL:** Uses embeddings and LLMs to select tables and generate SQL.
- **Query Execution:** Runs SQL, formats results, and collects feedback.
- **MCP Integration:** (Planned) For protocol-based integration with external tools and Azure SQL DB.

See `docs/architecture-diagram.png` for a visual overview.

---

## Next Steps
- Implement secure MCP HTTP bridge authentication (API key or AAD token validation).
- Add tests and CI workflows for the Python agent and Node MCP server (including health & tool enumeration checks).
- Expand NL2SQL logic with ranking + safety filters (SQL risk patterns detection).
- Add schema introspection + embedding refresh lifecycle (incremental updates).
- Container Apps deployment guide + optional Bicep/azd template.

---

## License
See [LICENSE.md](LICENSE.md).
