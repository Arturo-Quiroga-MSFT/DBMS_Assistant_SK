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
            tables = self.nl2sql.select_tables(question)
            response["tables"] = tables
            sql = self.nl2sql.generate_sql(question, tables)
            response["sql"] = sql
            if not self.nl2sql.apply_quality_filters(sql):
                response["markdown"] = "Query rejected by quality filters."\
                    " (Filters not yet implemented.)"
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
            # Naive tool selection: look for a generic execution tool
            candidate_names = [
                "execute_sql", "executeSql", "run_query", "query", "execute_sql_query"
            ]
            tool_name = None
            for c in candidate_names:
                if c in tools:
                    tool_name = c
                    break
            if not tool_name:
                # Fallback: first tool if any
                if tools:
                    tool_name = tools[0]
                else:
                    base_response["markdown"] = "Remote MCP has no tools to execute SQL."
                    return base_response

            result = self.mcp_http.call_tool(tool_name, {"sql": sql})
            # Expect result to be either structured or simple string
            markdown = None
            rows = None
            if isinstance(result, dict):
                markdown = result.get("markdown") or result.get("text") or str(result)
                rows = result.get("row_count") or result.get("rows")
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
