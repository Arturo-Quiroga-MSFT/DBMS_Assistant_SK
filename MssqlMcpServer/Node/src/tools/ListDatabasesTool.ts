import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export class ListDatabasesTool implements Tool {
  name = "list_databases";
  description = "Lists all accessible databases on the server.";
  inputSchema = { type: "object" as const, properties: {}, required: [] } as any;

  async run(_params: any) {
    try {
      const result = await new sql.Request().query(
        `SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name`
      );
      return { success: true, databases: result.recordset.map(r => r.name) };
    } catch (error) {
      return { success: false, message: `Failed to list databases: ${error}` };
    }
  }
}
