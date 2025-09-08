# MSSQL RDBMS Assistant (VS Code Extension)

Early scaffold extension that launches the existing MSSQL MCP Server (found in `../MssqlMcpServer/Node`) and provides:

- Command: `MSSQL Assistant: Start / Connect`
- Command: `MSSQL Assistant: Refresh Tables`
- Command: `MSSQL Assistant: Run Tool`
- Tree View: `MSSQL Tables` (placeholder data for now)

## Usage

### 1. Install the Extension
Install from the packaged VSIX:

1. Open VS Code Command Palette: `Extensions: Install from VSIX...`
2. Select the generated file `vscode-mssql-assistant-<version>.vsix`.

### 2. Configure Connection Settings
Open Settings (UI or `settings.json`) and set the following under `mssqlAssistant`:

| Setting | Key | Description | Required |
|---------|-----|-------------|----------|
| Server | `mssqlAssistant.server` | SQL Server hostname (e.g. `myserver.database.windows.net`) | Yes |
| Database | `mssqlAssistant.database` | Default database to connect to | Yes |
| Azure AD Client ID | `mssqlAssistant.clientId` | For Managed Identity (user‑assigned) or Service Principal | Optional (needed for SP or user-assigned MI) |
| Azure AD Client Secret | `mssqlAssistant.clientSecret` | Service Principal secret (omit for Managed Identity) | Optional |
| Azure AD Tenant ID | `mssqlAssistant.tenantId` | Tenant GUID (required for Service Principal) | Optional for MI |

Authentication Modes:
- Managed Identity / Default Azure Credential path: leave `clientSecret` empty. If a user-assigned identity is attached in Azure, set `clientId` to its Client ID.
- Service Principal: set `clientId`, `clientSecret`, and `tenantId`.

Environment variables passed to the MCP server:
```
SERVER_NAME -> mssqlAssistant.server
DATABASE_NAME -> mssqlAssistant.database
AZURE_CLIENT_ID -> mssqlAssistant.clientId
AZURE_CLIENT_SECRET -> mssqlAssistant.clientSecret
AZURE_TENANT_ID -> mssqlAssistant.tenantId
```

### 3. Start the Server
Use the command: `MSSQL Assistant: Start / Connect`.

If successful you will see a toast: `MSSQL MCP server connected` and the `MSSQL Tables` view will attempt to populate by invoking the server's table-listing tool.

### 4. Explore Tools
Run `MSSQL Assistant: Run Tool` to:
1. Fetch the current tool list from the MCP server.
2. Select a tool (e.g., `list_table`, `describe_table`, `read_data`).
3. Provide optional JSON arguments. Results open in a temporary JSON editor.

### 5. Refresh Tables
Use `MSSQL Assistant: Refresh Tables` to re-query for tables (heuristic parser from the tool output).

### 6. Security Notes
| Capability | Safeguard |
|------------|-----------|
| SELECT queries | Restricted to single `SELECT` via `read_data` tool (blocks destructive statements) |
| Insert/Update | Parameterized values; `update_data` requires explicit WHERE clause |
| DDL (create/drop) | Requires appropriate DB roles (e.g. `db_ddladmin`) |
| Identity Diagnostics | `diagnose_connection` reveals current user & role memberships |

### 7. Typical Troubleshooting
| Symptom | Hint |
|---------|------|
| Login failed / principal not found | Ensure Azure AD contained user was created in the target DB (`CREATE USER [Display Name] FROM EXTERNAL PROVIDER;`) |
| Tables view empty | Confirm `list_table` tool exists (run `Run Tool` command). |
| Timeout on start | Verify `SERVER_NAME` and network/firewall settings; test with a local `sqlcmd` or Azure Data Studio. |

### 8. Uninstall / Cleanup
Simply uninstall the extension; no local state beyond standard VS Code storage is persisted.

## Screenshots & Demo

> NOTE: The images below are placeholders. Replace them with real captures after installing and connecting.

| Feature | Image |
|---------|-------|
| Start / Connect Command | ![Start Command](resources/screenshots/start-connect.png) |
| Table Explorer Populated | ![Tables View](resources/screenshots/tables-view.png) |
| Run Tool Quick Pick | ![Run Tool](resources/screenshots/run-tool.png) |
| Describe Table Result | ![Describe Table](resources/screenshots/describe-table.png) |
| Read Data (SELECT) Output | ![Read Data](resources/screenshots/read-data.png) |

### Creating a GIF (Optional)

1. Record a short screen segment (10–15s) showing: Start → Tables populated → Run Tool → JSON result.
2. On macOS you can record screen with QuickTime or use `ffmpeg`:
	```bash
	# Capture a region (adjust -video_size and -i 1 for display index)
	ffmpeg -y -f avfoundation -framerate 30 -i 1 -video_size 1440x900 demo.mov
	# Convert to optimized GIF
	ffmpeg -i demo.mov -vf "fps=12,scale=960:-1:flags=lanczos" -loop 0 demo.gif
	# (Optional) further optimize
	gifsicle -O3 demo.gif -o demo.gif
	```
3. Place `demo.gif` at `resources/screenshots/demo.gif` and reference it in this README:
	```markdown
	![Demo](resources/screenshots/demo.gif)
	```

### Screenshot Guidelines
* Use a neutral VS Code theme (e.g. Dark+).
* Crop to the interaction area (avoid entire desktop).
* Keep consistent width (≈1200px) for clarity.
* Anonymize sensitive server names or database identifiers if needed.

---

## Next Steps / TODO

1. Implement proper MCP client requests for `ListTools` and `CallTool` once a stable client helper is available.
2. Add a tool selection quick pick that enumerates the tools exposed by the server.
3. Implement table listing by calling the `list_tables` tool and refreshing the tree.
4. Add inline actions (context menu) for table: Describe, Read Top N, Drop (if not read-only).
5. Add configuration settings (e.g., environment variables, server path override, readonly flag).
6. Surface server logs in an output channel instead of console.
7. Provide result webview with richer formatting for query results.

## Development

Install dependencies and compile:

```
npm install
npm run build
```

Press F5 to launch the extension host.

## Packaging

```
npm run package
```

(This uses `vsce` – ensure you are logged in / have a publisher configured.)
