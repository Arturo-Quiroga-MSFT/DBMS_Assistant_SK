import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * list_views
 * Lists (non-system) views with optional schema filtering.
 */
export class ListViewsTool implements Tool {
  [key: string]: any;
  name = "list_views";
  description = "Lists user views with schema/view breakdown; optionally filter by schema list";
  inputSchema = {
    type: "object",
    properties: {
      parameters: {
        type: "array",
        description: "Optional array of schema names to include (e.g. ['dbo'])",
        items: { type: "string" },
        minItems: 0
      }
    },
    required: []
  } as any;

  async run(params: any) {
    const request = new sql.Request();
    try {
      const raw = params?.parameters || [];
      const schemas: string[] = Array.isArray(raw) ? raw : [];
      const validSchemas = schemas
        .map(s => (typeof s === 'string' ? s.trim() : ''))
        .filter(s => s.length > 0 && /^[A-Za-z0-9_]+$/.test(s));

      let schemaPredicate = '';
      if (validSchemas.length > 0) {
        const inParams: string[] = [];
        validSchemas.forEach((schema, idx) => {
          const paramName = `schema${idx}`;
          request.input(paramName, sql.NVarChar, schema);
          inParams.push(`@${paramName}`);
        });
        schemaPredicate = `AND v.TABLE_SCHEMA IN (${inParams.join(',')})`;
      }

      // Exclude system schemas if not explicitly requested
      const systemSchemas = ["sys", "INFORMATION_SCHEMA"];
      let systemExclusion = '';
      if (validSchemas.length === 0) {
        systemSchemas.forEach((s, i) => {
          const p = `sysEx${i}`;
            request.input(p, sql.NVarChar, s);
            systemExclusion += (i === 0 ? 'AND ' : ' AND ') + `v.TABLE_SCHEMA <> @${p}`;
        });
      }

      const query = `SELECT v.TABLE_SCHEMA AS [schema], v.TABLE_NAME AS [view], 
        v.TABLE_SCHEMA + '.' + v.TABLE_NAME AS qualified
        FROM INFORMATION_SCHEMA.VIEWS v
        WHERE 1=1 ${schemaPredicate} ${systemExclusion}
        ORDER BY v.TABLE_SCHEMA, v.TABLE_NAME`;

      const result = await request.query(query);
      return {
        success: true,
        filteredSchemas: validSchemas,
        message: `Retrieved ${result.recordset.length} view(s)` + (validSchemas.length ? ' (filtered)' : ''),
        items: result.recordset
      };
    } catch (error: any) {
      console.error('Error listing views:', error);
      return {
        success: false,
        message: `Failed to list views: ${error?.message || error}`
      };
    }
  }
}
