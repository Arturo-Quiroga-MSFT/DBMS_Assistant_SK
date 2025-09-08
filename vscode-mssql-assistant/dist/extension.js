"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path_1 = __importDefault(require("path"));
const stdio_js_1 = require("@modelcontextprotocol/sdk/client/stdio.js");
const index_js_1 = require("@modelcontextprotocol/sdk/client/index.js");
// Simple MCP client wrapper (minimal for listing and calling tools)
class McpClient {
    command;
    args;
    cwd;
    env;
    transport = null;
    client = null;
    toolNames = [];
    constructor(command, args, cwd, env) {
        this.command = command;
        this.args = args;
        this.cwd = cwd;
        this.env = env;
    }
    async start() {
        if (this.client)
            return;
        // Normalize env so all values are strings (drop undefined)
        const normEnv = this.env ? Object.fromEntries(Object.entries(this.env).filter(([_, v]) => typeof v === 'string')) : undefined;
        this.transport = new stdio_js_1.StdioClientTransport({
            command: this.command,
            args: this.args,
            cwd: this.cwd,
            env: normEnv,
            stderr: 'pipe'
        });
        await this.transport.start();
        // Surface server stderr to output channel if desired later; for now log to debug console.
        this.transport.stderr?.on('data', (chunk) => {
            const msg = chunk.toString();
            console.log('[mcp-server]', msg.trim());
        });
        this.client = new index_js_1.Client({ name: 'vscode-mssql-assistant', version: '0.0.1' }, { capabilities: { tools: {} } });
        await this.client.connect(this.transport);
        const listed = await this.client.listTools({});
        this.toolNames = listed.tools.map((t) => t.name);
    }
    async listTools() {
        if (!this.client)
            throw new Error('Not started');
        return this.toolNames.slice();
    }
    async refreshTools() {
        if (!this.client)
            return;
        const listed = await this.client.listTools({});
        this.toolNames = listed.tools.map((t) => t.name);
    }
    async callTool(name, args) {
        if (!this.client)
            throw new Error('Not started');
        const result = await this.client.callTool({ name, arguments: args });
        return result;
    }
    dispose() {
        try {
            this.transport?.close();
        }
        catch { }
        this.transport = null;
        this.client = null;
    }
}
class TablesProvider {
    _onDidChangeTreeData = new vscode.EventEmitter();
    onDidChangeTreeData = this._onDidChangeTreeData.event;
    tables = [];
    setTables(names) { this.tables = names; this._onDidChangeTreeData.fire(); }
    getTreeItem(element) { return element; }
    getChildren() {
        return Promise.resolve(this.tables.map(t => new TableItem(t)));
    }
}
class TableItem extends vscode.TreeItem {
    constructor(label) { super(label, vscode.TreeItemCollapsibleState.None); this.contextValue = 'table'; }
}
let client = null;
async function activate(context) {
    const tablesProvider = new TablesProvider();
    vscode.window.registerTreeDataProvider('mssqlAssistant.tables', tablesProvider);
    const startCmd = vscode.commands.registerCommand('mssqlAssistant.start', async () => {
        if (client) {
            vscode.window.showInformationMessage('MCP server already started');
            return;
        }
        const serverDir = path_1.default.join(context.extensionPath, '..', 'MssqlMcpServer', 'Node');
        const serverEntry = path_1.default.join(serverDir, 'dist', 'index.js');
        client = new McpClient('node', [serverEntry], serverDir);
        try {
            await client.start();
            vscode.window.showInformationMessage('MSSQL MCP server connected');
            await tryPopulateTables(client, tablesProvider);
        }
        catch (e) {
            vscode.window.showErrorMessage('Failed to start MCP server: ' + e.message);
            client = null;
        }
    });
    const refreshCmd = vscode.commands.registerCommand('mssqlAssistant.refreshTables', async () => {
        if (!client)
            return vscode.window.showWarningMessage('Start the server first');
        await tryPopulateTables(client, tablesProvider, true);
    });
    const runToolCmd = vscode.commands.registerCommand('mssqlAssistant.runTool', async () => {
        if (!client)
            return vscode.window.showWarningMessage('Start the server first');
        await client.refreshTools();
        const tools = await client.listTools();
        if (!tools.length)
            return vscode.window.showWarningMessage('No tools available');
        const toolName = await vscode.window.showQuickPick(tools, { placeHolder: 'Select a tool to run' });
        if (!toolName)
            return;
        const argJson = await vscode.window.showInputBox({ prompt: 'Arguments JSON (optional)' });
        let args = {};
        if (argJson) {
            try {
                args = JSON.parse(argJson);
            }
            catch {
                vscode.window.showErrorMessage('Invalid JSON');
                return;
            }
        }
        const result = await client.callTool(toolName, args);
        vscode.workspace.openTextDocument({ content: JSON.stringify(result, null, 2), language: 'json' })
            .then(doc => vscode.window.showTextDocument(doc, { preview: false }));
    });
    context.subscriptions.push(startCmd, refreshCmd, runToolCmd, { dispose: () => client?.dispose() });
}
function deactivate() {
    client?.dispose();
}
async function tryPopulateTables(client, provider, showErrors = false) {
    try {
        // Refresh tool list first so we know available names.
        await client.refreshTools();
        const tools = await client.listTools();
        // Find plausible list tables tool name among variants.
        const candidate = tools.find(t => /list.*table/i.test(t));
        if (!candidate) {
            provider.setTables(['(no list tables tool exposed)']);
            return;
        }
        const result = await client.callTool(candidate, {});
        // Result content may be in different shapes depending on server implementation; parse heuristically.
        const tables = extractTableNames(result);
        provider.setTables(tables.length ? tables : ['(no tables returned)']);
    }
    catch (err) {
        if (showErrors)
            vscode.window.showErrorMessage('Failed to load tables: ' + (err?.message || String(err)));
        provider.setTables(['(error loading tables)']);
    }
}
function extractTableNames(result) {
    if (!result)
        return [];
    // If server returns structured content
    if (Array.isArray(result.structuredContent)) {
        for (const item of result.structuredContent) {
            if (item && typeof item === 'object' && Array.isArray(item.tables)) {
                return item.tables.filter((t) => typeof t === 'string');
            }
        }
    }
    // If server returns content array with text JSON string
    if (Array.isArray(result.content)) {
        for (const c of result.content) {
            if (c?.type === 'text' && typeof c.text === 'string') {
                try {
                    const parsed = JSON.parse(c.text);
                    if (Array.isArray(parsed))
                        return parsed.filter(t => typeof t === 'string');
                    if (Array.isArray(parsed?.tables))
                        return parsed.tables.filter((t) => typeof t === 'string');
                }
                catch { /* ignore */ }
            }
        }
    }
    // Fallback: if result.result?.tables etc.
    const possible = result?.result || result;
    if (Array.isArray(possible?.tables))
        return possible.tables.filter((t) => typeof t === 'string');
    return [];
}
//# sourceMappingURL=extension.js.map