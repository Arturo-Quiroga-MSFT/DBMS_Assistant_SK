import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export class ShowSchemaTool implements Tool {
  name = "show_schema";
  description = "Shows all tables, views, columns, and types in the current database.";
  inputSchema = { type: "object" as const, properties: {}, required: [] } as any;

  async run(_params: any) {
    try {
      const query = `SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION`;
      const result = await new sql.Request().query(query);
      return { success: true, columns: result.recordset };
    } catch (error) {
      return { success: false, message: `Failed to show schema: ${error}` };
    }
  }
}
