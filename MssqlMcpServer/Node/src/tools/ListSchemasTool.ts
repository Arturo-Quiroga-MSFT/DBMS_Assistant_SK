import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export class ListSchemasTool implements Tool {
  name = "list_schemas";
  description = "Lists all schemas in the current database.";
  inputSchema = { type: "object" as const, properties: {}, required: [] } as any;

  async run(_params: any) {
    try {
      const result = await new sql.Request().query(
        `SELECT name FROM sys.schemas WHERE principal_id <> 1 ORDER BY name`
      );
      return { success: true, schemas: result.recordset.map(r => r.name) };
    } catch (error) {
      return { success: false, message: `Failed to list schemas: ${error}` };
    }
  }
}
