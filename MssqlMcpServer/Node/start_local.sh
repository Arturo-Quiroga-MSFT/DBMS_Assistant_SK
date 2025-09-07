#!/usr/bin/env bash
set -euo pipefail

# Convenience script: run the MCP MSSQL server locally over HTTP for interactive testing.
# It will:
#  1. Load .env if present (so credentials aren't retyped).
#  2. Ensure TypeScript build output exists (build if needed or if sources newer).
#  3. Export sensible defaults (HTTP_PORT=8080, PRE_FLIGHT=false unless overridden).
#  4. Launch the server (node dist/index.js) so the Python agent can call HTTP endpoints.
#
# Usage:
#   ./start_local.sh              # uses .env + defaults
#   HTTP_PORT=8090 ./start_local.sh
#   DEBUG_STARTUP=true READONLY=true ./start_local.sh
#
# After startup test:
#   curl -s http://localhost:${HTTP_PORT}/health
#   curl -s http://localhost:${HTTP_PORT}/ready
#   curl -s -H "X-API-Key: $MCP_API_KEY" http://localhost:${HTTP_PORT}/tools
#
# Python agent (from repo root):
#   USE_REMOTE_MCP=1 MCP_HTTP_BASE_URL=http://localhost:${HTTP_PORT} MCP_HTTP_API_KEY=$MCP_API_KEY \
#     python dbms_agent_python/run_example.py "What tables exist?"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f .env ]]; then
  echo "[startup] Loading .env" >&2
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | grep -E '^[A-Za-z0-9_]+=' | xargs -0 printf "%s\n" 2>/dev/null || true)
fi

# Defaults (allow override)
: "${HTTP_PORT:=8080}"      # HTTP port for bridge
: "${PRE_FLIGHT:=false}"    # Skip preflight locally (faster dev loop)
: "${DO_NOT_EXIT_ON_PREFLIGHT_FAIL:=true}"  # Keep alive even if first query fails
: "${PREFERRED_SQL_AUTH:=sp-secret}"        # Use SP secret unless token flow configured
: "${READONLY:=false}"

export HTTP_PORT PRE_FLIGHT DO_NOT_EXIT_ON_PREFLIGHT_FAIL PREFERRED_SQL_AUTH READONLY

echo "[startup] HTTP_PORT=$HTTP_PORT READONLY=$READONLY PRE_FLIGHT=$PRE_FLIGHT" >&2

if ! command -v node >/dev/null; then
  echo "[error] Node.js not found in PATH" >&2
  exit 1
fi

# Decide whether to rebuild: if dist missing or any .ts newer than dist timestamp
needs_build=false
if [[ ! -d dist ]]; then
  needs_build=true
else
  newest_src=$(find src -type f -name '*.ts' -print0 | xargs -0 stat -f %m 2>/dev/null | sort -nr | head -1 || echo 0)
  dist_mtime=$(find dist -type f -name '*.js' -print0 2>/dev/null | xargs -0 stat -f %m 2>/dev/null | sort -nr | head -1 || echo 0)
  if [[ "$newest_src" -gt "$dist_mtime" ]]; then
    needs_build=true
  fi
fi

if $needs_build; then
  echo "[build] Compiling TypeScript..." >&2
  npm run build --silent
else
  echo "[build] Using existing dist output (no newer sources)." >&2
fi

echo "[run] Starting server (Ctrl+C to stop)..." >&2
exec node dist/index.js
