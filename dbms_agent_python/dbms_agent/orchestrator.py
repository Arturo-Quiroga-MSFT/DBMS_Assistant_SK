"""High-level DBMS Agent Orchestrator.

Pipeline (minimal initial implementation):
  1. Select relevant tables using semantic model (placeholder logic).
  2. Generate candidate SQL from natural language question (stub).
  3. (Optional) Allow quality filters / rewriting (stub always passes).
  4. Execute SQL either:
       a. Locally via pyodbc (QueryExecutionAgent), or
       b. Remotely via MCP HTTP bridge (if MCP_HTTP_BASE_URL set and tool exists)
  5. Return formatted markdown response + trace metadata.

Environment Variables:
  - USE_REMOTE_MCP: if set to truthy, prefer MCP HTTP even if local execution configured.
  - MCP_HTTP_BASE_URL: base URL for MCP HTTP bridge (e.g. http://host:8080)

This module deliberately keeps business logic thin until NL2SQL & semantic
retrieval are fully implemented.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

from .semantic_model import SemanticModelAnalyzer
from .nl2sql import NL2SQLAgent
from .query_execution import QueryExecutionAgent
from .http_transport import get_http_transport_from_env, MCPHttpTransport

logger = logging.getLogger(__name__)


def _is_truthy(val: Optional[str]) -> bool:
    if val is None:
        return False
    return val.lower() in {"1", "true", "yes", "on"}


class DBMSAgent:
    """Main orchestration entrypoint."""

    def __init__(
        self,
        db_connection: Any = None,
        use_remote_mcp: Optional[bool] = None,
    ) -> None:
        self.semantic = SemanticModelAnalyzer(db_connection)
        self.nl2sql = NL2SQLAgent(self.semantic)
        self.query_exec: Optional[QueryExecutionAgent] = None
        self.mcp_http: Optional[MCPHttpTransport] = None

        # Determine execution mode
        env_force_remote = _is_truthy(os.getenv("USE_REMOTE_MCP"))
        self.use_remote_mcp = use_remote_mcp if use_remote_mcp is not None else env_force_remote

        # Try local executor
        try:
            self.query_exec = QueryExecutionAgent()
            logger.debug("Initialized local QueryExecutionAgent")
        except Exception as e:  # noqa: BLE001 - surface problems but allow remote fallback
            logger.warning("Local QueryExecutionAgent unavailable: %s", e)

        # Try HTTP MCP transport if requested or local unavailable
        if self.use_remote_mcp or self.query_exec is None:
            try:
                self.mcp_http = get_http_transport_from_env()
                if not self.mcp_http.health():
                    logger.warning("MCP HTTP health check failed at %s", os.getenv("MCP_HTTP_BASE_URL"))
                else:
                    logger.debug("Connected to MCP HTTP server: tools=%s", self.mcp_http.list_tools())
            except Exception as e:  # noqa: BLE001
                logger.warning("MCP HTTP transport not available: %s", e)

    # ---- Public API ----
    def answer(self, question: str) -> Dict[str, Any]:
        """Full pipeline returning structured response.

        Returns dict with keys:
          - question
          - tables (list)
          - sql (generated SQL)
          - executed (bool)
          - rows (int | None)
          - markdown (result markdown or message)
          - mode ("local" | "remote" | "none")
          - error (optional error string)
        """
        response: Dict[str, Any] = {
            "question": question,
            "tables": [],
            "sql": None,
            "executed": False,
            "rows": None,
            "markdown": None,
            "mode": "none",
        }

        try:
            intent = self.nl2sql.classify_intent(question)
            response["intent"] = intent
            if intent == 'metadata':
                # Provide a catalog summary without generating SQL
                catalog = self.semantic.analyze_schema() or []
                if not catalog:
                    response["markdown"] = "Schema is empty or unavailable."
                    return response
                # Summarize tables/views with up to first 8 columns each
                lines = ["### Database Catalog", "", "| Object | Type | Columns (sample) |", "| --- | --- | --- |"]
                for item in catalog:
                    name = item.get('name')
                    otype = item.get('type')
                    cols = item.get('columns') or []
                    sample_cols = ", ".join(cols[:8]) + (" …" if len(cols) > 8 else "")
                    lines.append(f"| {name} | {otype} | {sample_cols} |")
                response["markdown"] = "\n".join(lines)
                response["executed"] = False
                response["mode"] = 'none'
                return response

            tables = self.nl2sql.select_tables(question)
            response["tables"] = tables
            sql = self.nl2sql.generate_sql(question, tables)
            response["sql"] = sql
            # Skip attempting execution if we have no tables or a placeholder query
            if not tables or sql.strip().startswith("-- No tables"):
                response["markdown"] = "No tables selected (schema unavailable or empty)."
                return response
            if not self.nl2sql.apply_quality_filters(sql):
                response["markdown"] = "Query rejected by quality filters." " (Filters not yet implemented.)"
                return response

            # Prefer remote if explicitly requested
            if self.mcp_http and (self.use_remote_mcp or self.query_exec is None):
                result = self._execute_remote(sql, response)
                if result:
                    return result

            # Fallback to local
            if self.query_exec:
                df = self.query_exec.execute_sql(sql)
                response["markdown"] = self.query_exec.format_response(df)
                response["rows"] = 0 if df is None else len(df.index)
                response["executed"] = True
                response["mode"] = "local"
            else:
                response["markdown"] = "No execution backend available (local + remote failed)."
        except Exception as e:  # noqa: BLE001
            logger.exception("Agent pipeline error")
            response["error"] = str(e)
            if response.get("markdown") is None:
                response["markdown"] = f"Error: {e}"
        return response

    # ---- Internals ----
    def _execute_remote(self, sql: str, base_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.mcp_http:
            return None
        try:
            tools = self.mcp_http.list_tools()
            # Explicitly prefer the read_data tool which enforces SELECT-only queries
            tool_name = None
            if 'read_data' in tools:
                tool_name = 'read_data'
            else:
                # Backward compatible fallbacks if naming differs in future
                for alt in ("execute_sql", "executeSql", "run_query", "query", "execute_sql_query"):
                    if alt in tools:
                        tool_name = alt
                        break
            if not tool_name:
                base_response["markdown"] = "Remote MCP: no suitable read/execute tool found (expected 'read_data')."
                return base_response

            # read_data expects argument key 'query'
            arguments_key = 'query' if tool_name == 'read_data' else 'sql'
            result = self.mcp_http.call_tool(tool_name, {arguments_key: sql})
            # Expect result to be either structured or simple string
            markdown = None
            rows = None
            if isinstance(result, dict):
                # Prefer returned message/data formatting
                if result.get('success') and 'data' in result:
                    # Render a lightweight markdown table for up to 20 rows
                    data_rows = result['data']
                    if isinstance(data_rows, list) and data_rows:
                        headers = list(data_rows[0].keys())
                        lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"]
                        for r in data_rows[:20]:
                            lines.append("| " + " | ".join(str(r.get(h, '')) for h in headers) + " |")
                        markdown = "\n".join(lines)
                        rows = len(data_rows)
                    else:
                        markdown = result.get('message') or 'Query returned 0 rows.'
                        rows = 0
                else:
                    markdown = result.get("markdown") or result.get("text") or result.get("message") or str(result)
                    rows = result.get("row_count") or result.get("rows") or result.get('recordCount')
            else:
                markdown = str(result)
            base_response.update({
                "markdown": markdown,
                "rows": rows,
                "executed": True,
                "mode": "remote",
            })
            return base_response
        except Exception as e:  # noqa: BLE001
            logger.warning("Remote execution failed, will try local if available: %s", e)
            return None


__all__ = ["DBMSAgent"]
