import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";


export class DescribeTableTool implements Tool {
  [key: string]: any;
  name = "describe_table";
  description = "Describes the schema (columns and types) of a specified MSSQL Database table (supports schema-qualified names).";
  inputSchema = {
    type: "object",
    properties: {
      tableName: { type: "string", description: "Name of the table to describe" },
    },
    required: ["tableName"],
  } as any;

  async run(params: { tableName: string }) {
    try {
      const { tableName } = params;
      const request = new sql.Request();
      // Support schema-qualified names
      let schema: string | null = null;
      let pureTable = tableName;
      if (tableName.includes('.')) {
        const parts = tableName.split('.');
        if (parts.length === 2) {
          schema = parts[0];
          pureTable = parts[1];
        }
      }
      request.input('tableName', sql.NVarChar, pureTable);
      if (schema) {
        request.input('schemaName', sql.NVarChar, schema);
      }
      const query = `SELECT COLUMN_NAME as name, DATA_TYPE as type, ORDINAL_POSITION as ordinal
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = @tableName ${schema ? 'AND TABLE_SCHEMA = @schemaName' : ''}
        ORDER BY ORDINAL_POSITION`;
      const result = await request.query(query);
      return {
        success: true,
        table: schema ? `${schema}.${pureTable}` : pureTable,
        columns: result.recordset,
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to describe table: ${error}`,
      };
    }
  }
}
