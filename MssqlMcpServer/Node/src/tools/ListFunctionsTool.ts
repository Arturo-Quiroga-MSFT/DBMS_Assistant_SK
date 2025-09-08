import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export class ListFunctionsTool implements Tool {
  name = "list_functions";
  description = "Lists all user-defined functions in the current database, including schema, name, and type.";
  inputSchema = { type: "object" as const, properties: {}, required: [] } as any;

  async run(_params: any) {
    try {
      const query = `SELECT s.name AS schema, o.name AS function, o.type_desc AS type
        FROM sys.objects o
        JOIN sys.schemas s ON o.schema_id = s.schema_id
        WHERE o.type IN ('FN','IF','TF')
        ORDER BY s.name, o.name`;
      const result = await new sql.Request().query(query);
      return { success: true, functions: result.recordset };
    } catch (error) {
      return { success: false, message: `Failed to list functions: ${error}` };
    }
  }
}
