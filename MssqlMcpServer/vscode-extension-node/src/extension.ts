import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

function execAsync(cmd: string, opts: { cwd?: string } = {}) {
  return new Promise<{ stdout: string; stderr: string }>((resolve, reject) => {
    exec(
      cmd,
      { cwd: opts.cwd, env: process.env },
      (err: Error | null, stdout: string, stderr: string) => {
        if (err) return reject(new Error(stderr || err.message));
        resolve({ stdout, stderr });
      }
    );
  });
}

async function buildNodeProject() {
  const cfg = vscode.workspace.getConfiguration('mssqlMcpNode');
  const projectPath = cfg.get<string>('nodeProjectPath')!;
  const doInstall = cfg.get<boolean>('installDependencies') ?? true;

  if (!fs.existsSync(projectPath)) {
    vscode.window.showErrorMessage(`mssqlMcpNode.nodeProjectPath does not exist: ${projectPath}`);
    return;
  }

  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: 'Building MSSQL MCP (Node)', cancellable: false },
    async () => {
      if (doInstall) {
        await execAsync('npm install', { cwd: projectPath });
      }
      await execAsync('npm run build', { cwd: projectPath });
    }
  );

  vscode.window.showInformationMessage('MSSQL MCP (Node) build succeeded.');
}

async function configureMcpSettings() {
  const cfg = vscode.workspace.getConfiguration('mssqlMcpNode');
  const projectPath = cfg.get<string>('nodeProjectPath')!;
  const serverId = cfg.get<string>('serverId') || 'mssql-nodejs';

  const serverName = cfg.get<string>('serverName') || '';
  const databaseName = cfg.get<string>('databaseName') || '';
  const readOnly = cfg.get<boolean>('readOnly') ?? false;
  const connectionTimeout = cfg.get<number>('connectionTimeout') ?? 30;
  const trustServerCertificate = cfg.get<boolean>('trustServerCertificate') ?? false;

  const entry = path.join(projectPath, 'dist', 'index.js');
  if (!fs.existsSync(entry)) {
    vscode.window.showWarningMessage(`Could not find ${entry}. Try running “MSSQL MCP (Node): Build Server” first.`);
  }

  // Merge into user-level mcp settings
  const settings = vscode.workspace.getConfiguration(undefined, null);
  const currentMcp = settings.get<any>('mcp') || {};
  const servers = currentMcp.servers ?? {};

  servers[serverId] = {
    type: 'stdio',
    command: 'node',
    args: [entry],
    env: {
      SERVER_NAME: serverName,
      DATABASE_NAME: databaseName,
      READONLY: String(readOnly),
      CONNECTION_TIMEOUT: String(connectionTimeout),
      TRUST_SERVER_CERTIFICATE: String(trustServerCertificate)
    }
  };

  const newMcp = { ...currentMcp, servers };
  await settings.update('mcp', newMcp, vscode.ConfigurationTarget.Global);
  vscode.window.showInformationMessage(`Configured MCP server “${serverId}” to run: node ${entry}`);
}

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand('mssqlMcpNode.build', buildNodeProject),
    vscode.commands.registerCommand('mssqlMcpNode.configure', configureMcpSettings)
  );
}

export function deactivate() {}
