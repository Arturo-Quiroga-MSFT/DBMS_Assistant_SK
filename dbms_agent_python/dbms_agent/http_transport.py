import os
import json
import time
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

class MCPHttpTransport:
    """Simple HTTP transport for the MSSQL MCP server HTTP bridge.

    Endpoints expected:
      GET  /health -> { status: "ok" }
      GET  /tools  -> { tools: [{ name: str }] }
      POST /call   -> { result: any } | { error: str }
    """

    def __init__(self, base_url: str, timeout: float = 15.0, max_retries: int = 3, backoff: float = 0.75):
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._tool_cache: List[str] = []

    def _request(self, method: str, path: str, *, json_body: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if method == 'GET':
                    resp = requests.get(url, timeout=self.timeout)
                else:
                    resp = requests.post(url, json=json_body, timeout=self.timeout)
                if resp.status_code >= 500:
                    raise RuntimeError(f"Server error {resp.status_code}: {resp.text[:200]}")
                if resp.status_code == 404:
                    return {"error": "not_found", "status": 404}
                resp.raise_for_status()
                return resp.json()
            except Exception as e:  # broad catch for retry path
                last_exc = e
                if attempt == self.max_retries:
                    logger.error("HTTP request failed after %s attempts: %s", attempt, e)
                    raise
                sleep_for = self.backoff * attempt
                logger.warning("HTTP request error (attempt %s/%s): %s; retrying in %.2fs", attempt, self.max_retries, e, sleep_for)
                time.sleep(sleep_for)
        raise RuntimeError(f"Unreachable code, last exception: {last_exc}")

    def health(self) -> bool:
        try:
            data = self._request('GET', '/health')
            return data.get('status') == 'ok'
        except Exception:
            return False

    def list_tools(self, force_refresh: bool = False) -> List[str]:
        if self._tool_cache and not force_refresh:
            return self._tool_cache
        data = self._request('GET', '/tools')
        tools = [t.get('name') for t in data.get('tools', []) if isinstance(t, dict) and 'name' in t]
        self._tool_cache = tools
        return tools

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        payload = {"name": name, "arguments": arguments or {}}
        data = self._request('POST', '/call', json_body=payload)
        if 'error' in data:
            raise RuntimeError(f"Tool call failed: {data['error']}")
        return data.get('result')

# Convenience factory using environment variable MCP_HTTP_BASE_URL

def get_http_transport_from_env() -> MCPHttpTransport:
    base = os.getenv('MCP_HTTP_BASE_URL')
    if not base:
        raise ValueError("MCP_HTTP_BASE_URL environment variable not set")
    return MCPHttpTransport(base)
