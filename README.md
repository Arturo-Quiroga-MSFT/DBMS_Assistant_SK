# DBMS Assistant SK

![Architecture Diagram](docs/architecture-diagram.png)

## Overview

This repository contains two main components:

1. **Legacy .NET/Semantic Kernel Agent** (in `src/`):
   - Original implementation using Microsoft Semantic Kernel and .NET for NL2SQL and database agent workflows.
2. **New Python/LangChain-LangGraph Agent** (in `dbms_agent_python/`):
   - Modern, modular Python implementation using LangChain, LangGraph, and Azure services.

---

## Python Agent (dbms_agent_python)

A modular, extensible DBMS agent solution in Python, designed for natural language to SQL (NL2SQL) workflows, leveraging Azure OpenAI, Cosmos DB (as a vector store), and Azure SQL DB. 

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
3. Set required environment variables for Azure OpenAI, Cosmos DB, and Azure SQL DB.

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
- Implement MCP protocol integration for agent-to-agent and tool connectivity.
- Add tests and CI workflows for the Python agent.
- Expand NL2SQL logic with advanced LLM prompting and table selection.
- Document environment variable setup and deployment options.

---

## License
See [LICENSE.md](LICENSE.md).
