#!/usr/bin/env node


// External imports
import * as dotenv from "dotenv";
// Load .env early for local development (no effect in Azure where env vars are injected)
dotenv.config();
import sql from "mssql";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import http from "http";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Internal imports
import { UpdateDataTool } from "./tools/UpdateDataTool.js";
import { InsertDataTool } from "./tools/InsertDataTool.js";
import { ReadDataTool } from "./tools/ReadDataTool.js";
import { CreateTableTool } from "./tools/CreateTableTool.js";
import { CreateIndexTool } from "./tools/CreateIndexTool.js";
import { ListTableTool } from "./tools/ListTableTool.js";
import { DropTableTool } from "./tools/DropTableTool.js";
import { ClientSecretCredential } from "@azure/identity";
import { DescribeTableTool } from "./tools/DescribeTableTool.js";
import { DiagnoseConnectionTool } from "./tools/DiagnoseConnectionTool.js";
import { ListExternalUsersTool } from "./tools/ListExternalUsersTool.js";
// Import newly added ListViewsTool (TypeScript will emit ListViewsTool.js on build)
import { ListViewsTool } from "./tools/ListViewsTool.js";

// MSSQL Database connection configuration
// const credential = new DefaultAzureCredential();

// Globals for connection and token reuse
let globalSqlPool: sql.ConnectionPool | null = null;
let globalAccessToken: string | null = null;
let globalTokenExpiresOn: Date | null = null;
let firstSuccessfulDbCheck = false; // readiness flag

function markReady() {
  if (!firstSuccessfulDbCheck) {
    firstSuccessfulDbCheck = true;
    if (process.env.DEBUG_STARTUP?.toLowerCase() === 'true') {
      console.error('[ready] Database connectivity established. Readiness state = true');
    }
  }
}


// Function to create SQL config with fresh access token, returns token and expiry
export async function createSqlConfig(): Promise<{ config: sql.config, token: string, expiresOn: Date }> {
  // Read Azure service principal credentials from environment
  const clientId = process.env.AZURE_CLIENT_ID;
  const clientSecret = process.env.AZURE_CLIENT_SECRET;
  const tenantId = process.env.AZURE_TENANT_ID;
  if (!clientId || !clientSecret || !tenantId) {
    throw new Error('Missing AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, or AZURE_TENANT_ID environment variables.');
  }
  const credential = new ClientSecretCredential(tenantId, clientId, clientSecret);
  const accessToken = await credential.getToken('https://database.windows.net/.default');
  if (process.env.DEBUG_STARTUP?.toLowerCase() === 'true') {
    console.error('[token] acquired Azure SQL access token', {
      expires: accessToken?.expiresOnTimestamp ? new Date(accessToken.expiresOnTimestamp).toISOString() : undefined,
      length: accessToken?.token?.length,
      preview: accessToken?.token?.slice(0, 20) + '…'
    });
  }

  const trustServerCertificate = process.env.TRUST_SERVER_CERTIFICATE?.toLowerCase() === 'true';
  const connectionTimeout = process.env.CONNECTION_TIMEOUT ? parseInt(process.env.CONNECTION_TIMEOUT, 10) : 30;

  return {
    config: ((): sql.config => {
      const authMode = (process.env.PREFERRED_SQL_AUTH || 'access-token').toLowerCase();
      const common: any = {
        server: process.env.SERVER_NAME!,
        database: process.env.DATABASE_NAME!,
        port: 1433,
        options: { encrypt: true, trustServerCertificate, enableArithAbort: true },
        connectionTimeout: connectionTimeout * 1000,
      };
      if (authMode === 'sp-secret') {
        if (process.env.DEBUG_STARTUP?.toLowerCase() === 'true') {
          console.error('[auth] Using primary auth mode: service-principal-secret');
        }
        common.authentication = {
          type: 'azure-active-directory-service-principal-secret',
          options: { clientId, clientSecret, tenantId }
        };
      } else {
        if (process.env.DEBUG_STARTUP?.toLowerCase() === 'true') {
          console.error('[auth] Using primary auth mode: access-token');
        }
        common.authentication = {
          type: 'azure-active-directory-access-token',
          options: { token: accessToken?.token! }
        };
      }
      return common as sql.config;
    })(),
    token: accessToken?.token!,
    expiresOn: accessToken?.expiresOnTimestamp ? new Date(accessToken.expiresOnTimestamp) : new Date(Date.now() + 30 * 60 * 1000)
  };
}


const updateDataTool = new UpdateDataTool();
const insertDataTool = new InsertDataTool();
const readDataTool = new ReadDataTool();
const createTableTool = new CreateTableTool();
const createIndexTool = new CreateIndexTool();
const listTableTool = new ListTableTool();
const dropTableTool = new DropTableTool();
const describeTableTool = new DescribeTableTool();
const diagnoseConnectionTool = new DiagnoseConnectionTool();
const listExternalUsersTool = new ListExternalUsersTool();
const listViewsTool = new ListViewsTool();

const server = new Server(
  {
    name: "mssql-mcp-server",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

// Read READONLY env variable
const isReadOnly = process.env.READONLY === "true";

// Optional startup diagnostics (avoid logging secrets). Enable with DEBUG_STARTUP=true
function startupDiagnostics() {
  if (process.env.DEBUG_STARTUP?.toLowerCase() !== 'true') return;
  const redacted = (val?: string) => val ? `${val.slice(0,4)}…` : undefined;
  const requiredForSql = ["AZURE_CLIENT_ID","AZURE_CLIENT_SECRET","AZURE_TENANT_ID","SERVER_NAME","DATABASE_NAME"];
  const missing = requiredForSql.filter(k => !process.env[k]);
  console.error("[startup] Environment summary", {
    NODE_ENV: process.env.NODE_ENV,
    HTTP_PORT: process.env.HTTP_PORT || process.env.PORT,
    READONLY: process.env.READONLY,
    SERVER_NAME: process.env.SERVER_NAME,
    DATABASE_NAME: process.env.DATABASE_NAME,
    AZURE_CLIENT_ID: redacted(process.env.AZURE_CLIENT_ID),
    AZURE_CLIENT_SECRET: process.env.AZURE_CLIENT_SECRET ? '***redacted***' : undefined,
    AZURE_TENANT_ID: redacted(process.env.AZURE_TENANT_ID),
    TRUST_SERVER_CERTIFICATE: process.env.TRUST_SERVER_CERTIFICATE,
    CONNECTION_TIMEOUT: process.env.CONNECTION_TIMEOUT,
    MCP_API_KEY_PRESENT: !!process.env.MCP_API_KEY,
    missingRequiredForSql: missing
  });
  if (!process.env.HTTP_PORT && !process.env.PORT) {
    console.error("[startup] NOTE: No HTTP_PORT/PORT set. Only stdio transport will start; in headless container this may exit immediately. Set HTTP_PORT to keep process alive.");
  }
}
startupDiagnostics();

// Optional pre-flight: attempt early SQL connection & simple query so container fails fast if misconfigured.
async function preFlightIfEnabled() {
  if (process.env.PRE_FLIGHT?.toLowerCase() !== 'true') return;
  console.error('[preflight] Starting pre-flight SQL connectivity test...');
  try {
    await ensureSqlConnection();
    if (!globalSqlPool) throw new Error('Pool not initialized after ensureSqlConnection');
    const r = await globalSqlPool.request().query('SELECT 1 AS one');
    if (r?.recordset?.[0]?.one === 1) {
      console.error('[preflight] Success: SQL connectivity verified.');
      markReady();
    } else {
      console.error('[preflight] Unexpected query result', r?.recordset);
    }
  } catch (err: any) {
    const msg = err?.message || String(err);
    console.error('[preflight] FAILED:', msg);
    // Attempt to decode token claims for debugging (appid/objectId)
    try {
      if (globalAccessToken) {
        const parts = globalAccessToken.split('.');
        if (parts.length >= 2) {
          const payloadRaw = parts[1].replace(/-/g, '+').replace(/_/g, '/');
          const pad = '='.repeat((4 - (payloadRaw.length % 4)) % 4);
          const jsonStr = Buffer.from(payloadRaw + pad, 'base64').toString('utf8');
          const claims = JSON.parse(jsonStr);
          console.error('[preflight] token.claims summary', {
            appid: claims.appid,
            oid: claims.oid,
            tid: claims.tid,
            upn: claims.upn,
            roles: claims.roles,
            scp: claims.scp
          });
          console.error('[preflight] HINT: For a service principal you must create the DB user with the SERVICE PRINCIPAL DISPLAY NAME (not AppId).');
          console.error('[preflight] HINT: Find display name: az ad sp show --id ' + claims.appid + ' --query displayName -o tsv');
          console.error('[preflight] HINT: Then run (in target DB as Azure AD admin):');
          console.error('  CREATE USER [' + '<ServicePrincipalDisplayName>' + '] FROM EXTERNAL PROVIDER;');
          console.error('  ALTER ROLE db_datareader ADD MEMBER [' + '<ServicePrincipalDisplayName>' + '];');
          console.error('  ALTER ROLE db_datawriter ADD MEMBER [' + '<ServicePrincipalDisplayName>' + '];');
          console.error('  -- Optional for DDL: ALTER ROLE db_ddladmin ADD MEMBER [' + '<ServicePrincipalDisplayName>' + '];');
        }
      }
    } catch {}
    if (/Login failed for user '\?'<token-identified principal>\?'/.test(msg) || /token-identified principal/i.test(msg)) {
      console.error('[preflight] HINT: The Azure AD service principal is NOT yet created as a contained user in database ' + process.env.DATABASE_NAME + '.');
      console.error('[preflight] QUICK CHECK (run inside the DB): SELECT name, authentication_type_desc FROM sys.database_principals WHERE name = N"<ServicePrincipalDisplayName>";');
    }
    const allowContinue = process.env.DO_NOT_EXIT_ON_PREFLIGHT_FAIL?.toLowerCase() === 'true';
    if (allowContinue) {
      console.error('[preflight] Continuing startup despite failure because DO_NOT_EXIT_ON_PREFLIGHT_FAIL=true');
    } else {
      // Exit with non-zero so container shows failure
      process.exit(1);
    }
  }
}
preFlightIfEnabled();

// Request handlers

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: isReadOnly
    ? [listTableTool, listViewsTool, readDataTool, describeTableTool, diagnoseConnectionTool, listExternalUsersTool]
    : [insertDataTool, readDataTool, describeTableTool, updateDataTool, createTableTool, createIndexTool, dropTableTool, listTableTool, listViewsTool, diagnoseConnectionTool, listExternalUsersTool],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    let result;
    switch (name) {
      case insertDataTool.name:
        result = await insertDataTool.run(args);
        break;
      case readDataTool.name:
        result = await readDataTool.run(args);
        break;
      case updateDataTool.name:
        result = await updateDataTool.run(args);
        break;
      case createTableTool.name:
        result = await createTableTool.run(args);
        break;
      case createIndexTool.name:
        result = await createIndexTool.run(args);
        break;
      case listTableTool.name:
        result = await listTableTool.run(args);
        break;
      case listViewsTool.name:
        result = await listViewsTool.run(args);
        break;
      case dropTableTool.name:
        result = await dropTableTool.run(args);
        break;
      case describeTableTool.name:
        if (!args || typeof args.tableName !== "string") {
          return {
            content: [{ type: "text", text: `Missing or invalid 'tableName' argument for describe_table tool.` }],
            isError: true,
          };
        }
        result = await describeTableTool.run(args as { tableName: string });
        break;
      case diagnoseConnectionTool.name:
        result = await diagnoseConnectionTool.run(args || {});
        break;
      case listExternalUsersTool.name:
        result = await listExternalUsersTool.run(args || {});
        break;
      default:
        return {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error occurred: ${error}` }],
      isError: true,
    };
  }
});

// Server startup
async function runServer() {
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
  } catch (error) {
    console.error("Fatal error running server:", error);
    process.exit(1);
  }
}

runServer().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});

// Connect to SQL only when handling a request

// Deep error logger to surface driver-level fields (useful for 18456 state analysis)
function logDetailedSqlError(prefix: string, err: any) {
  const original = err?.originalError || err?.precedingErrors?.[0];
  const info = original?.info || original;
  const details: any = {
    code: err?.code,
    number: info?.number,
    state: info?.state,
    class: info?.class,
    lineNumber: info?.lineNumber,
    serverName: info?.serverName,
    name: err?.name,
  };
  console.error(prefix, details);
}

async function ensureSqlConnection() {
  // If we have a pool and it's connected, and the token is still valid, reuse it
  if (
    globalSqlPool &&
    globalSqlPool.connected &&
    globalAccessToken &&
    globalTokenExpiresOn &&
    globalTokenExpiresOn > new Date(Date.now() + 2 * 60 * 1000) // 2 min buffer
  ) {
    return;
  }

  // Otherwise, get a new token and reconnect
  const { config, token, expiresOn } = await createSqlConfig();
  globalAccessToken = token;
  globalTokenExpiresOn = expiresOn;

  // Close old pool if exists
  if (globalSqlPool && globalSqlPool.connected) {
    await globalSqlPool.close();
  }

  try {
    globalSqlPool = await sql.connect(config);
    markReady();
  } catch (err: any) {
    const msg = err?.message || String(err);
    console.error('[connect] Primary auth failed:', msg);
    logDetailedSqlError('[connect] Primary error detail', err);
    if (process.env.DEBUG_STARTUP?.toLowerCase() === 'true') {
      console.error('[connect] Stack:', err?.stack);
    }

    // Optional diagnostic: attempt master connection (helps distinguish missing contained user vs. principal not recognized at server)
    if (process.env.DIAG_TRY_MASTER?.toLowerCase() === 'true') {
      try {
        console.error('[connect][diag] Attempting master DB connection for diagnostics...');
        const authMode = (process.env.PREFERRED_SQL_AUTH || 'access-token').toLowerCase();
        let masterAuth: any;
        if (authMode === 'sp-secret') {
          masterAuth = {
            type: 'azure-active-directory-service-principal-secret',
            options: { clientId: process.env.AZURE_CLIENT_ID, clientSecret: process.env.AZURE_CLIENT_SECRET, tenantId: process.env.AZURE_TENANT_ID }
          };
        } else {
          masterAuth = {
            type: 'azure-active-directory-access-token',
            options: { token: globalAccessToken }
          };
        }
        const masterPool = await sql.connect({
          server: process.env.SERVER_NAME!,
          database: 'master',
          port: 1433,
          options: { encrypt: true, trustServerCertificate: process.env.TRUST_SERVER_CERTIFICATE?.toLowerCase() === 'true', enableArithAbort: true },
          authentication: masterAuth
        } as any);
        console.error('[connect][diag] Master DB connection SUCCEEDED. Checking target database existence...');
        try {
          const targetDb = process.env.DATABASE_NAME;
          if (targetDb) {
            const rs = await masterPool.request().input('db', sql.NVarChar, targetDb)
              .query('SELECT name, collation_name FROM sys.databases WHERE name = @db');
            if (rs.recordset.length === 0) {
              console.error('[connect][diag] WARNING: Target database "' + targetDb + '" does NOT exist.');
              console.error('[connect][diag] HINT: Check spelling (dimensional vs dimentional).');
              const sample = await masterPool.request().query('SELECT TOP (10) name FROM sys.databases ORDER BY name');
              console.error('[connect][diag] Existing databases:', sample.recordset.map(r => r.name).join(', '));
            } else {
              console.error('[connect][diag] Target database exists. Likely missing contained user principal inside that database.');
            }
          }
        } catch (dbExistErr: any) {
          console.error('[connect][diag] Database existence check failed:', dbExistErr?.message || dbExistErr);
        }
        console.error('[connect][diag] Master DB connection SUCCEEDED. This strongly indicates the service principal exists at server level but the contained user is missing in database: ' + process.env.DATABASE_NAME);
      } catch (masterErr: any) {
        console.error('[connect][diag] Master DB connection failed as well:', masterErr?.message || masterErr);
        logDetailedSqlError('[connect][diag] Master error detail', masterErr);
      }
    }

    const fallbackDisabled = process.env.DISABLE_AAD_FALLBACK?.toLowerCase() === 'true';
    if (fallbackDisabled) throw err;
    // Always attempt fallback if not already using sp-secret and credentials exist
    const usingSecretPrimary = (process.env.PREFERRED_SQL_AUTH || 'access-token').toLowerCase() === 'sp-secret';
    const clientId = process.env.AZURE_CLIENT_ID;
    const clientSecret = process.env.AZURE_CLIENT_SECRET;
    const tenantId = process.env.AZURE_TENANT_ID;
    if (!usingSecretPrimary && clientId && clientSecret && tenantId) {
      console.error('[connect] Attempting fallback auth: service-principal-secret');
      const fallbackConfig: sql.config = {
        server: process.env.SERVER_NAME!,
        database: process.env.DATABASE_NAME!,
        port: 1433,
        options: { encrypt: true, trustServerCertificate: process.env.TRUST_SERVER_CERTIFICATE?.toLowerCase() === 'true', enableArithAbort: true },
        authentication: {
          type: 'azure-active-directory-service-principal-secret',
          options: { clientId, clientSecret, tenantId }
        }
      } as any;
      try {
        globalSqlPool = await sql.connect(fallbackConfig);
        console.error('[connect] Fallback succeeded.');
        markReady();
      } catch (fallbackErr: any) {
        console.error('[connect] Fallback failed:', fallbackErr?.message || fallbackErr);
        logDetailedSqlError('[connect] Fallback error detail', fallbackErr);
        throw err;
      }
    } else {
      throw err;
    }
  }
}

// Patch all tool handlers to ensure SQL connection before running
function wrapToolRun(tool: { run: (...args: any[]) => Promise<any> }) {
  const originalRun = tool.run.bind(tool);
  tool.run = async function (...args: any[]) {
    await ensureSqlConnection();
    return originalRun(...args);
  };
}

[insertDataTool, readDataTool, updateDataTool, createTableTool, createIndexTool, dropTableTool, listTableTool, listViewsTool, describeTableTool, diagnoseConnectionTool, listExternalUsersTool].forEach(wrapToolRun);

// -----------------------
// Optional HTTP bridge
// -----------------------
// Provides a simple JSON HTTP interface for environments (e.g. Azure Container Apps)
// where stdio MCP transport is not practical for remote invocation.
// Enable by setting HTTP_PORT (or PORT) environment variable.

interface HttpJsonBody {
  name?: string;
  arguments?: any;
}

function startHttpBridge() {
  const port = parseInt(process.env.HTTP_PORT || process.env.PORT || "", 10);
  if (!port || Number.isNaN(port)) {
    console.error('[startup] HTTP bridge not started: set HTTP_PORT (e.g. 8080) to enable HTTP interface and keep the process alive in container environments.');
    return; // bridge not enabled
  }

  // Support seamless rotation: allow either single MCP_API_KEY or comma-separated MCP_API_KEYS
  let apiKeys: string[] = [];
  if (process.env.MCP_API_KEYS) {
    apiKeys = process.env.MCP_API_KEYS.split(',').map(k => k.trim()).filter(k => k.length > 0);
  } else if (process.env.MCP_API_KEY) {
    apiKeys = [process.env.MCP_API_KEY.trim()];
  }
  const expectingApiKeyAuth = apiKeys.length > 0;

  const toolMap = new Map<string, { run: (args: any) => Promise<any> }>();
  const allTools = isReadOnly
    ? [listTableTool, listViewsTool, readDataTool, describeTableTool, diagnoseConnectionTool, listExternalUsersTool]
    : [insertDataTool, readDataTool, describeTableTool, updateDataTool, createTableTool, createIndexTool, dropTableTool, listTableTool, listViewsTool, diagnoseConnectionTool, listExternalUsersTool];
  allTools.forEach(t => toolMap.set(t.name, t as any));

  const serverHttp = http.createServer(async (req, res) => {
    // Basic CORS + JSON headers (safe defaults)
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type,Authorization,X-API-Key");
    res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
    if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }
    try {
      // Public (unauthenticated) endpoints: /health and /ready
      if (req.url === "/health" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ status: "ok" }));
      }
      if (req.url === "/ready" && req.method === "GET") {
        const ready = firstSuccessfulDbCheck;
        res.writeHead(ready ? 200 : 503, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ ready, status: ready ? 'ready' : 'starting' }));
      }

      // API Key auth (optional) for all remaining endpoints.
      // Accept either:
      //  - Header: Authorization: Bearer <key>
      //  - Header: X-API-Key: <key>
      if (expectingApiKeyAuth) {
        const authHeader = req.headers["authorization"]; // e.g. Bearer <token>
        const apiKeyHeader = req.headers["x-api-key"]; // raw key
        let provided: string | undefined;
        if (typeof authHeader === "string" && authHeader.toLowerCase().startsWith("bearer ")) {
          provided = authHeader.slice(7).trim();
        } else if (typeof apiKeyHeader === "string") {
          provided = apiKeyHeader.trim();
        }
        if (!provided || !apiKeys.includes(provided)) {
          res.writeHead(401, { "Content-Type": "application/json" });
          return res.end(JSON.stringify({ error: "Unauthorized" }));
        }
      }

      if (req.url === "/tools" && req.method === "GET") {
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ tools: allTools.map(t => ({ name: t.name })) }));
      }
      if (req.url === "/call" && req.method === "POST") {
        let body = "";
        req.on("data", chunk => { body += chunk; if (body.length > 1_000_000) req.destroy(); });
        req.on("end", async () => {
          try {
            const parsed: HttpJsonBody = body ? JSON.parse(body) : {};
            if (!parsed.name) {
              res.writeHead(400, { "Content-Type": "application/json" });
              return res.end(JSON.stringify({ error: "Missing 'name' field" }));
            }
            const tool = toolMap.get(parsed.name);
            if (!tool) {
              res.writeHead(404, { "Content-Type": "application/json" });
              return res.end(JSON.stringify({ error: `Unknown tool: ${parsed.name}` }));
            }
            await ensureSqlConnection();
            const result = await tool.run(parsed.arguments || {});
            res.writeHead(200, { "Content-Type": "application/json" });
            return res.end(JSON.stringify({ result }));
          } catch (e: any) {
            res.writeHead(500, { "Content-Type": "application/json" });
            return res.end(JSON.stringify({ error: e?.message || String(e) }));
          }
        });
        return;
      }
            // (Master DB diagnostic moved into ensureSqlConnection catch block)
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "Not found" }));
    } catch (err: any) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: err?.message || String(err) }));
    }
  });

  serverHttp.listen(port, () => {
    console.error(`HTTP bridge listening on :${port}${expectingApiKeyAuth ? " (API key auth enabled)" : ""}`); // stderr so logs surface in container
  });
}

startHttpBridge();