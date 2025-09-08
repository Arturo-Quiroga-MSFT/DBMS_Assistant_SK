#!/usr/bin/env node
// Ensure the real branded icon is copied from the MCP server location into extension resources.
import { writeFileSync, existsSync, readFileSync } from 'fs';
import { join } from 'path';

const destIconPath = join(process.cwd(), 'resources', 'database.png');
// Absolute path to source logo within the monorepo
const sourceIconPath = join(process.cwd(), '..', 'MssqlMcpServer', 'Node', 'src', 'img', 'logo.png');

try {
  if (existsSync(sourceIconPath)) {
    const buf = readFileSync(sourceIconPath);
    writeFileSync(destIconPath, buf);
    console.log('[ensure-icon] Copied branded logo from MCP server to resources/database.png');
  } else if (!existsSync(destIconPath)) {
    // Fallback tiny transparent png if source missing
    const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAFgwJ/lP2BTwAAAABJRU5ErkJggg==';
    writeFileSync(destIconPath, Buffer.from(pngBase64, 'base64'));
    console.log('[ensure-icon] Created placeholder icon (source logo not found)');
  }
} catch (e) {
  console.error('[ensure-icon] Failed updating icon:', e);
}
