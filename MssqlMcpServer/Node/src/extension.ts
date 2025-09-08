import * as vscode from 'vscode';
import * as cp from 'child_process';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('mssql-mcp-server.startServer', () => {
        const terminal = vscode.window.createTerminal('MSSQL MCP Server');
        terminal.sendText('node dist/index.js');
        terminal.show();
        vscode.window.showInformationMessage('MSSQL MCP Server started!');
    });
    context.subscriptions.push(disposable);
}

export function deactivate() {}
