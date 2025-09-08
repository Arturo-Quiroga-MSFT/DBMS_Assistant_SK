import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

export class ChangeDatabaseTool implements Tool {
  name = "change_database";
  description = "Changes the active database for the current connection/session.";
  inputSchema = {
    type: "object" as const,
    properties: {
      database: { type: "string", description: "Name of the database to switch to" }
    },
    required: ["database"]
  } as any;

  async run(params: any) {
    try {
      const { database } = params;
      if (!database || typeof database !== "string" || !/^[\w\d_]+$/.test(database)) {
        throw new Error("Invalid database name");
      }
      await new sql.Request().query(`USE [${database}]`);
      return { success: true, message: `Switched to database '${database}'` };
    } catch (error) {
      return { success: false, message: `Failed to switch database: ${error}` };
    }
  }
}
