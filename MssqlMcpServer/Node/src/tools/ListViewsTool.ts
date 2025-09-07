import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * list_views
 * Lists (non-system) views with optional schema filtering.
 */
export class ListViewsTool implements Tool {
  [key: string]: any;
  name = "list_views";
  description = "Lists user views with schema/view breakdown; optionally filter by schema list; can include column samples";
  inputSchema = {
    type: "object",
    properties: {
      parameters: {
        type: "array",
        description: "Optional array of schema names to include (e.g. ['dbo'])",
        items: { type: "string" },
        minItems: 0
      },
      includeColumns: {
        type: "boolean",
        description: "If true, returns up to first N columns (see columnSampleLimit) for each view",
        default: false
      },
      columnSampleLimit: {
        type: "number",
        description: "Max columns to include per view when includeColumns=true (default 10)",
        default: 10,
        minimum: 1,
        maximum: 100
      }
    },
    required: []
  } as any;

  async run(params: any) {
    const request = new sql.Request();
    try {
  const raw = params?.parameters || [];
      const schemas: string[] = Array.isArray(raw) ? raw : [];
  const includeColumns: boolean = !!params?.includeColumns;
  const columnSampleLimit: number = Math.min(Math.max(parseInt(params?.columnSampleLimit, 10) || 10, 1), 100);
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

      let items: any[] = [];
      if (includeColumns) {
        const query = `WITH base AS (
            SELECT v.TABLE_SCHEMA, v.TABLE_NAME
            FROM INFORMATION_SCHEMA.VIEWS v
            WHERE 1=1 ${schemaPredicate} ${systemExclusion}
        ), cols AS (
            SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME,
                   ROW_NUMBER() OVER (PARTITION BY c.TABLE_SCHEMA, c.TABLE_NAME ORDER BY c.ORDINAL_POSITION) AS rn,
                   COUNT(1) OVER (PARTITION BY c.TABLE_SCHEMA, c.TABLE_NAME) AS total_cols
            FROM INFORMATION_SCHEMA.COLUMNS c
            INNER JOIN base b ON b.TABLE_SCHEMA = c.TABLE_SCHEMA AND b.TABLE_NAME = c.TABLE_NAME
        )
        SELECT b.TABLE_SCHEMA AS [schema], b.TABLE_NAME AS [view], b.TABLE_SCHEMA + '.' + b.TABLE_NAME AS qualified,
               STRING_AGG(CASE WHEN cols.rn <= @colLimit THEN cols.COLUMN_NAME ELSE NULL END, ', ') WITHIN GROUP (ORDER BY cols.rn) AS column_sample,
               MAX(cols.total_cols) AS total_columns
        FROM base b
        LEFT JOIN cols ON cols.TABLE_SCHEMA = b.TABLE_SCHEMA AND cols.TABLE_NAME = b.TABLE_NAME
        GROUP BY b.TABLE_SCHEMA, b.TABLE_NAME
        ORDER BY b.TABLE_SCHEMA, b.TABLE_NAME;`;
        request.input('colLimit', sql.Int, columnSampleLimit);
        const result = await request.query(query);
        items = result.recordset.map(r => ({
          schema: r.schema,
          view: r.view,
          qualified: r.qualified,
          columns: (r.column_sample ? String(r.column_sample).split(/\s*,\s*/) : []),
          totalColumns: Number(r.total_columns) || 0
        }));
      } else {
        const query = `SELECT v.TABLE_SCHEMA AS [schema], v.TABLE_NAME AS [view], 
          v.TABLE_SCHEMA + '.' + v.TABLE_NAME AS qualified
          FROM INFORMATION_SCHEMA.VIEWS v
          WHERE 1=1 ${schemaPredicate} ${systemExclusion}
          ORDER BY v.TABLE_SCHEMA, v.TABLE_NAME`;
        const result = await request.query(query);
        items = result.recordset;
      }
      return {
        success: true,
        filteredSchemas: validSchemas,
        message: `Retrieved ${items.length} view(s)` + (validSchemas.length ? ' (filtered)' : ''),
        includeColumns,
        columnSampleLimit: includeColumns ? columnSampleLimit : undefined,
        items
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
