import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * list_table
 * Returns all base tables in the database with structured metadata:
 *   schema, table, qualified (schema.table)
 * Optional filter: parameters (array of schema names) — backward compatible.
 * Security: validates schema tokens and parameterizes the IN clause to avoid injection.
 */
export class ListTableTool implements Tool {
  [key: string]: any;
  name = "list_table";
  description = "Lists base tables with schema/table breakdown; optionally filter by schema list";
  inputSchema = {
    type: "object",
    properties: {
      parameters: {
        type: "array",
        description: "Optional array of schema names to include (e.g. ['dbo','sales'])",
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

      // Validate schema tokens (alphanumeric + underscore allowed)
      const validSchemas = schemas
        .map(s => (typeof s === 'string' ? s.trim() : ''))
        .filter(s => s.length > 0 && /^[A-Za-z0-9_]+$/.test(s));

      let whereExtra = '';
      if (validSchemas.length > 0) {
        const inParams: string[] = [];
        validSchemas.forEach((schema, idx) => {
          const paramName = `schema${idx}`;
          request.input(paramName, sql.NVarChar, schema);
          inParams.push(`@${paramName}`);
        });
        whereExtra = `AND TABLE_SCHEMA IN (${inParams.join(',')})`;
      }

      const query = `SELECT TABLE_SCHEMA AS [schema], TABLE_NAME AS [table], 
        TABLE_SCHEMA + '.' + TABLE_NAME AS qualified
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE' ${whereExtra}
        ORDER BY TABLE_SCHEMA, TABLE_NAME`;

      const result = await request.query(query);
      return {
        success: true,
        filteredSchemas: validSchemas,
        message: `Retrieved ${result.recordset.length} table(s)` + (validSchemas.length ? ` (filtered)` : ''),
        items: result.recordset
      };
    } catch (error: any) {
      console.error("Error listing tables:", error);
      return {
        success: false,
        message: `Failed to list tables: ${error?.message || error}`
      };
    }
  }
}
