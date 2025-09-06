# MSSQL MCP (Node) – VS Code Wrapper

This VS Code extension helps you:
- Build the Node-based MSSQL MCP server in `MssqlMcpServer/Node`
- Configure VS Code MCP settings to run it via `node dist/index.js`

## Requirements
- Node.js 18+
- VS Code 1.90+
- VS Code Agent extension (to consume MCP servers)

## Commands
- MSSQL MCP (Node): Build Server — runs `npm install` (optional) and `npm run build` in `MssqlMcpServer/Node`
- MSSQL MCP (Node): Configure MCP Settings — writes to your global `mcp.servers` in VS Code settings to point at the built entry

## Settings
- `mssqlMcpNode.nodeProjectPath` — absolute path to the Node project (default points to your repo path)
- `mssqlMcpNode.serverId` — key under `mcp.servers` (default: `mssql-nodejs`)
- `mssqlMcpNode.installDependencies` — run `npm install` before build (default: true)
- `mssqlMcpNode.serverName` — env SERVER_NAME
- `mssqlMcpNode.databaseName` — env DATABASE_NAME
- `mssqlMcpNode.readOnly` — env READONLY (true/false)
- `mssqlMcpNode.connectionTimeout` — env CONNECTION_TIMEOUT (seconds)
- `mssqlMcpNode.trustServerCertificate` — env TRUST_SERVER_CERTIFICATE (true/false)

## Build & Package
From this folder (`vscode-extension-node`):

```bash
npm install
npm run compile
npx @vscode/vsce package
```

This generates a `.vsix` file like `mssql-mcp-node-wrapper-0.1.0.vsix`.

## Install the VSIX
- Open VS Code → Cmd+Shift+P → “Extensions: Install from VSIX…”
- Select the generated `.vsix`

Then:
1) Run “MSSQL MCP (Node): Build Server”
2) Run “MSSQL MCP (Node): Configure MCP Settings”
3) Verify your global settings contain something like:

```json
{
  "mcp": {
    "servers": {
      "mssql-nodejs": {
        "type": "stdio",
        "command": "node",
        "args": [
          "/Users/arturoquiroga/GITHUB/MCP-SQL-DEMO/MssqlMcpServer/Node/dist/index.js"
        ],
        "env": {
          "SERVER_NAME": "your-server-name.database.windows.net",
          "DATABASE_NAME": "your-database-name",
          "READONLY": "false",
          "CONNECTION_TIMEOUT": "30",
          "TRUST_SERVER_CERTIFICATE": "false"
        }
      }
    }
  }
}
```

Notes
- Ensure the Node project path is correct for your machine.
- Build the Node project (`npm run build`) so `dist/index.js` exists before configuration.
- You can adjust environment variables in the extension settings or after configuration, directly in your VS Code Settings JSON.
