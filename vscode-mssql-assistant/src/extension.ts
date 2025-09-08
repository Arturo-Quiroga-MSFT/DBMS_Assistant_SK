import * as vscode from 'vscode';
import path from 'path';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

// Simple MCP client wrapper (minimal for listing and calling tools)
class McpClient {
  private transport: StdioClientTransport | null = null;
  private client: Client | null = null;
  private toolNames: string[] = [];
  constructor(private command: string, private args: string[], private cwd?: string, private env?: NodeJS.ProcessEnv) {}

  async start(): Promise<void> {
    if (this.client) return;
    // Normalize env so all values are strings (drop undefined)
    const normEnv: Record<string,string> | undefined = this.env ? Object.fromEntries(Object.entries(this.env).filter(([_,v]) => typeof v === 'string') as [string,string][]) : undefined;
    this.transport = new StdioClientTransport({
      command: this.command,
      args: this.args,
      cwd: this.cwd,
      env: normEnv,
      stderr: 'pipe'
    });
    await this.transport.start();
    // Surface server stderr to output channel if desired later; for now log to debug console.
    this.transport.stderr?.on('data', (chunk: Buffer) => {
      const msg = chunk.toString();
      console.log('[mcp-server]', msg.trim());
    });
    this.client = new Client({ name: 'vscode-mssql-assistant', version: '0.0.1' }, { capabilities: { tools: {} } });
    await this.client.connect(this.transport as any);
  const listed = await this.client.listTools({});
  this.toolNames = listed.tools.map((t: any) => t.name);
  }

  async listTools(): Promise<string[]> {
    if (!this.client) throw new Error('Not started');
    return this.toolNames.slice();
  }

  async refreshTools(): Promise<void> {
    if (!this.client) return;
  const listed = await this.client.listTools({});
  this.toolNames = listed.tools.map((t: any) => t.name);
  }

  async callTool(name: string, args: any): Promise<any> {
    if (!this.client) throw new Error('Not started');
    const result = await this.client.callTool({ name, arguments: args });
    return result;
  }

  dispose() {
    try { this.transport?.close(); } catch {}
    this.transport = null;
    this.client = null;
  }
}

class TablesProvider implements vscode.TreeDataProvider<TableItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<TableItem | undefined | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
  private tables: string[] = [];

  setTables(names: string[]) { this.tables = names; this._onDidChangeTreeData.fire(); }

  getTreeItem(element: TableItem): vscode.TreeItem { return element; }

  getChildren(): Thenable<TableItem[]> {
    return Promise.resolve(this.tables.map(t => new TableItem(t)));
  }
}

class TableItem extends vscode.TreeItem {
  constructor(label: string) { super(label, vscode.TreeItemCollapsibleState.None); this.contextValue = 'table'; }
}

let client: McpClient | null = null;

export async function activate(context: vscode.ExtensionContext) {
  const tablesProvider = new TablesProvider();
  vscode.window.registerTreeDataProvider('mssqlAssistant.tables', tablesProvider);

  const startCmd = vscode.commands.registerCommand('mssqlAssistant.start', async () => {
    if (client) { vscode.window.showInformationMessage('MCP server already started'); return; }
    const serverDir = path.join(context.extensionPath, '..', 'MssqlMcpServer', 'Node');
    const serverEntry = path.join(serverDir, 'dist', 'index.js');
    client = new McpClient('node', [serverEntry], serverDir);
    try {
      await client.start();
      vscode.window.showInformationMessage('MSSQL MCP server connected');
      await tryPopulateTables(client, tablesProvider);
    } catch (e: any) {
      vscode.window.showErrorMessage('Failed to start MCP server: ' + e.message);
      client = null;
    }
  });

  const refreshCmd = vscode.commands.registerCommand('mssqlAssistant.refreshTables', async () => {
    if (!client) return vscode.window.showWarningMessage('Start the server first');
    await tryPopulateTables(client, tablesProvider, true);
  });

  const runToolCmd = vscode.commands.registerCommand('mssqlAssistant.runTool', async () => {
    if (!client) return vscode.window.showWarningMessage('Start the server first');
    await client.refreshTools();
    const tools = await client.listTools();
    if (!tools.length) return vscode.window.showWarningMessage('No tools available');
    const toolName = await vscode.window.showQuickPick(tools, { placeHolder: 'Select a tool to run' });
    if (!toolName) return;    
    const argJson = await vscode.window.showInputBox({ prompt: 'Arguments JSON (optional)' });
    let args: any = {};
    if (argJson) {
      try { args = JSON.parse(argJson); } catch { vscode.window.showErrorMessage('Invalid JSON'); return; }
    }
    const result = await client.callTool(toolName, args);
    vscode.workspace.openTextDocument({ content: JSON.stringify(result, null, 2), language: 'json' })
      .then(doc => vscode.window.showTextDocument(doc, { preview: false }));
  });

  context.subscriptions.push(startCmd, refreshCmd, runToolCmd, { dispose: () => client?.dispose() });
}

export function deactivate() {
  client?.dispose();
}

async function tryPopulateTables(client: McpClient, provider: TablesProvider, showErrors = false) {
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
  } catch (err: any) {
    if (showErrors) vscode.window.showErrorMessage('Failed to load tables: ' + (err?.message || String(err)));
    provider.setTables(['(error loading tables)']);
  }
}

function extractTableNames(result: any): string[] {
  if (!result) return [];
  // If server returns structured content
  if (Array.isArray(result.structuredContent)) {
    for (const item of result.structuredContent) {
      if (item && typeof item === 'object' && Array.isArray((item as any).tables)) {
        return (item as any).tables.filter((t: any) => typeof t === 'string');
      }
    }
  }
  // If server returns content array with text JSON string
  if (Array.isArray(result.content)) {
    for (const c of result.content) {
      if (c?.type === 'text' && typeof c.text === 'string') {
        try {
          const parsed = JSON.parse(c.text);
          if (Array.isArray(parsed)) return parsed.filter(t => typeof t === 'string');
          if (Array.isArray(parsed?.tables)) return parsed.tables.filter((t: any) => typeof t === 'string');
        } catch { /* ignore */ }
      }
    }
  }
  // Fallback: if result.result?.tables etc.
  const possible = result?.result || result;
  if (Array.isArray(possible?.tables)) return possible.tables.filter((t: any) => typeof t === 'string');
  return [];
}
