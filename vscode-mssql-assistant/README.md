# MSSQL RDBMS Assistant (VS Code Extension)

Early scaffold extension that launches the existing MSSQL MCP Server (found in `../MssqlMcpServer/Node`) and provides:

- Command: `MSSQL Assistant: Start / Connect`
- Command: `MSSQL Assistant: Refresh Tables`
- Command: `MSSQL Assistant: Run Tool`
- Tree View: `MSSQL Tables` (placeholder data for now)

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
