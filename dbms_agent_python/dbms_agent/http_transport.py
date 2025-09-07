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

    Authentication:
      /tools and /call are protected by an API key header (x-api-key) if the
      server was started with an API key. Health/ready endpoints remain public.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff: float = 0.75,
        api_key: Optional[str] = None,
    ):
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.api_key = api_key or os.getenv("MCP_HTTP_API_KEY")
        self._tool_cache: List[str] = []

    # ---- Internal HTTP helper with retries ----
    def _request(self, method: str, path: str, *, json_body: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        headers = {}
        # Only attach API key for non-public endpoints
        if self.api_key and path not in {"/health", "/ready"}:
            headers["x-api-key"] = self.api_key
        for attempt in range(1, self.max_retries + 1):
            try:
                if method == 'GET':
                    resp = requests.get(url, headers=headers, timeout=self.timeout)
                else:
                    resp = requests.post(url, headers=headers, json=json_body, timeout=self.timeout)
                if resp.status_code >= 500:
                    raise RuntimeError(f"Server error {resp.status_code}: {resp.text[:200]}")
                if resp.status_code == 401:
                    raise PermissionError("Unauthorized (401) calling MCP HTTP endpoint. Check MCP_HTTP_API_KEY.")
                if resp.status_code == 404:
                    return {"error": "not_found", "status": 404}
                resp.raise_for_status()
                # Some endpoints might return empty body (should not) – guard
                if not resp.text.strip():
                    return {}
                return resp.json()
            except Exception as e:  # noqa: BLE001 (retry path)
                last_exc = e
                if attempt == self.max_retries:
                    logger.error("HTTP request failed after %s attempts: %s", attempt, e)
                    raise
                sleep_for = self.backoff * attempt
                logger.warning(
                    "HTTP request error (attempt %s/%s) to %s: %s; retrying in %.2fs",
                    attempt,
                    self.max_retries,
                    path,
                    e,
                    sleep_for,
                )
                time.sleep(sleep_for)
        raise RuntimeError(f"Unreachable code, last exception: {last_exc}")

    # ---- Public API ----
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
        # Debug: if structure unexpected, log it (without raising) for troubleshooting
        if not isinstance(data, dict):  # pragma: no cover
            logger.warning("/tools response not a dict: %s", type(data))
        # Support either { tools: [{ name: str }]} or raw list
        raw = data.get('tools', data)
        tools = []
        if isinstance(raw, list):
            for t in raw:
                if isinstance(t, dict) and 'name' in t:
                    tools.append(t['name'])
                elif isinstance(t, str):
                    tools.append(t)
        self._tool_cache = tools
        return tools

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        payload = {"name": name, "arguments": arguments or {}}
        data = self._request('POST', '/call', json_body=payload)
        if 'error' in data:
            raise RuntimeError(f"Tool call failed: {data['error']}")
        return data.get('result')


# Convenience factory using environment variables
def get_http_transport_from_env() -> MCPHttpTransport:
    base = os.getenv('MCP_HTTP_BASE_URL')
    if not base:
        raise ValueError("MCP_HTTP_BASE_URL environment variable not set")
    # If user configured http:// but server redirects to https://, normalize here
    if base.startswith('http://') and 'azurecontainerapps.io' in base:
        base = 'https://' + base[len('http://'):]
    api_key = os.getenv('MCP_HTTP_API_KEY')
    return MCPHttpTransport(base, api_key=api_key)
