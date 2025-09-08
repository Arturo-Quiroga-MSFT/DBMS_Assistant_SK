#!/usr/bin/env node
// Simple helper to ensure a placeholder icon exists if user forgot to add database.png
import { writeFileSync, existsSync } from 'fs';
import { join } from 'path';

const iconPath = join(process.cwd(), 'resources', 'database.png');
if (!existsSync(iconPath)) {
  // Tiny 1x1 transparent PNG (base64) as fallback; user should replace with actual asset.
  const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAFgwJ/lP2BTwAAAABJRU5ErkJggg==';
  writeFileSync(iconPath, Buffer.from(pngBase64, 'base64'));
  console.log('[ensure-icon] Created placeholder resources/database.png');
}
