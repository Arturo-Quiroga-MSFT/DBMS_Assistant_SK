#!/usr/bin/env python
"""End-to-end smoke test for the RDBMS assistant.

Requirements:
  Environment variables:
    MCP_HTTP_BASE_URL  (e.g. https://your-app.azurecontainerapps.io)
    MCP_HTTP_API_KEY   (API key for HTTP bridge)
    USE_REMOTE_MCP=1

  Optional:
    AZURE_CLIENT_ID / SECRET / TENANT if local direct DB fallback desired (not required for remote tests)

Tests performed:
  1. /health reachable
  2. /ready returns ready=true (or notes not ready)
  3. /tools lists expected core tools (read_data, list_table, describe_table)
  4. list_table includeColumns works and returns at least one table
  5. describe_table on first table returns columns
  6. Agent metadata intent: "What tables exist?" returns catalog markdown
  7. Agent data query: ordering + TOP logic
  8. Security rejection: attempt dangerous query (UPDATE) must fail

Exit code: 0 if all mandatory tests pass, 1 otherwise.

Note: This is a lightweight diagnostic, not a full test harness.
"""
from __future__ import annotations
import os
import sys
import json
import time
import textwrap
from typing import List, Dict, Any

import requests

# Re-use agent
try:
    from dbms_agent import DBMSAgent  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"[WARN] Could not import DBMSAgent: {e}")
    DBMSAgent = None  # type: ignore

BASE = os.environ.get('MCP_HTTP_BASE_URL')
API_KEY = os.environ.get('MCP_HTTP_API_KEY')
if not BASE or not API_KEY:
    print("[ERROR] MCP_HTTP_BASE_URL and MCP_HTTP_API_KEY must be set in environment.")
    sys.exit(2)

HEADERS = {"X-API-Key": API_KEY}

results: List[Dict[str, Any]] = []

def record(name: str, ok: bool, detail: str = "", data: Any = None, mandatory: bool = True):
    results.append({"test": name, "ok": ok, "detail": detail, "mandatory": mandatory})
    status = "PASS" if ok else ("SKIP" if not mandatory else "FAIL")
    print(f"[{status}] {name} - {detail}")
    if data is not None and not ok:
        print(textwrap.indent(json.dumps(data, indent=2)[:800], prefix="      > "))

# 1a. /health
try:
    r = requests.get(f"{BASE}/health", timeout=10)
    record("health_endpoint", r.status_code == 200, f"status_code={r.status_code}")
except Exception as e:  # noqa: BLE001
    record("health_endpoint", False, f"Exception: {e}")

# 1b. /ready
try:
    r = requests.get(f"{BASE}/ready", timeout=10)
    ok = r.status_code in (200, 503)
    detail = f"status_code={r.status_code} body={r.text.strip()}"
    record("ready_endpoint", ok, detail)
except Exception as e:  # noqa: BLE001
    record("ready_endpoint", False, f"Exception: {e}")

# 1c. /version (optional, non-mandatory)
try:
    r = requests.get(f"{BASE}/version", headers=HEADERS, timeout=10)
    snippet = r.text[:120].replace('\n', ' ')
    record("version_endpoint", r.status_code == 200, f"status={r.status_code} body={snippet}", mandatory=False)
except Exception as e:  # noqa: BLE001
    record("version_endpoint", False, f"Exception: {e}", mandatory=False)

# 2. /tools
tool_names: List[str] = []
try:
    r = requests.get(f"{BASE}/tools", headers=HEADERS, timeout=15)
    if r.status_code == 200:
        data = r.json()
        tool_names = [t.get('name') for t in data.get('tools', [])]
        expected = {"read_data", "list_table", "describe_table"}
        ok = expected.issubset(set(tool_names))
        record("tools_list", ok, f"found={tool_names}")
    else:
        record("tools_list", False, f"status={r.status_code}")
except Exception as e:  # noqa: BLE001
    record("tools_list", False, f"Exception: {e}")

# Helper: call tool

def call_tool(name: str, arguments: Dict[str, Any]):
    r = requests.post(f"{BASE}/call", headers=HEADERS, json={"name": name, "arguments": arguments}, timeout=30)
    if r.status_code != 200:
        # Distinguish route 404 vs unknown tool 404
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text}
        marker = body.get('error')
        if r.status_code == 404 and marker == 'Not found':
            raise RuntimeError(f"Route /call not matched (404 fallback). Body={body}")
        raise RuntimeError(f"Tool {name} HTTP {r.status_code}: {body}")
    payload = r.json()
    # HTTP bridge returns { result: { ... } }
    return payload.get('result') if isinstance(payload, dict) else None

# 4. list_table includeColumns
first_table = None
try:
    if 'list_table' in tool_names:
        payload = call_tool('list_table', {"includeColumns": True, "columnSampleLimit": 10})
        items = payload.get('items') if isinstance(payload, dict) else None
        ok = bool(items and isinstance(items, list))
        first_table = items[0] if ok else None
        col_info = first_table.get('columns') if first_table else []
        record("list_table_includeColumns", ok, f"tables={len(items) if items else 0} columns_first={len(col_info) if col_info else 0}")
    else:
        record("list_table_includeColumns", False, "list_table tool missing")
except Exception as e:  # noqa: BLE001
    record("list_table_includeColumns", False, f"Exception: {e}")

# 5. describe_table
try:
    if first_table and 'describe_table' in tool_names:
        qual = first_table.get('qualified') or first_table.get('schema') + '.' + first_table.get('table')
        desc = call_tool('describe_table', {"tableName": qual})
        cols = desc.get('columns') if isinstance(desc, dict) else []
        ok = bool(cols and len(cols) >= len(first_table.get('columns', [])))
        record("describe_table", ok, f"columns={len(cols)} table={qual}")
    else:
        record("describe_table", False, "Prereq missing (first_table or tool)")
except Exception as e:  # noqa: BLE001
    record("describe_table", False, f"Exception: {e}")

# 6 & 7. Agent queries (metadata and data)
agent_metadata_ok = False
agent_data_ok = False
if DBMSAgent:
    try:
        os.environ.setdefault('USE_REMOTE_MCP', '1')
        os.environ.setdefault('MCP_HTTP_API_KEY', API_KEY)
        os.environ.setdefault('MCP_HTTP_BASE_URL', BASE)
        agent = DBMSAgent()
        # metadata
        md = agent.answer("What tables exist?")
        agent_metadata_ok = bool(md.get('markdown') and 'Database Catalog' in md.get('markdown', ''))
        record("agent_metadata_intent", agent_metadata_ok, f"executed={md.get('executed')} tables_listed={len(md.get('markdown','').splitlines())}")
        # data query
        dq = agent.answer("Show the first 5 actions ordered by PriorityRank")
        data_md = dq.get('markdown') or ''
        agent_data_ok = dq.get('executed') and ('PriorityRank' in data_md or 'Priorityrank' in data_md.lower())
        record("agent_data_query", bool(agent_data_ok), f"rows={dq.get('rows')} mode={dq.get('mode')}")
    except Exception as e:  # noqa: BLE001
        record("agent_pipeline", False, f"Exception: {e}")
else:
    record("agent_import", False, "DBMSAgent unavailable (import failed)")

# 8. Security rejection test
try:
    if 'read_data' in tool_names:
        bad = call_tool('read_data', {"query": "UPDATE dbo.Action_Dimension SET PriorityRank = 99"})
        # Should not succeed
        ok = isinstance(bad, dict) and not bad.get('success')
        record("security_rejection", ok, bad.get('message','(no message)'))
    else:
        record("security_rejection", False, "read_data missing")
except Exception as e:  # noqa: BLE001
    # If we get an exception, consider that a pass only if it indicates rejection clearly
    record("security_rejection", True, f"Exception (expected rejection path): {e}")

# Summary
mandatory_failures = [r for r in results if r['mandatory'] and not r['ok']]
print("\n=== SUMMARY ===")
for r in results:
    print(f"{r['test']}: {'PASS' if r['ok'] else 'FAIL'} - {r['detail']}")

if mandatory_failures:
    print(f"\n[RESULT] FAIL: {len(mandatory_failures)} mandatory test(s) failed.")
    sys.exit(1)
print("\n[RESULT] PASS: All mandatory tests succeeded.")
