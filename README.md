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
2. Install dependencies (to be defined in `requirements.txt`)

## Development Plan

See `RESEARCH_SUMMARY.md` for the high-level plan and architecture.

---
