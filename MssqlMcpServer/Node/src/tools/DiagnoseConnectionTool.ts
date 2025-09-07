import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * DiagnoseConnectionTool
 * Returns information about the current Azure AD principal context used for the SQL connection,
 * including database principal name, server/database names, roles, and a UTC timestamp.
 * Useful for verifying that the service principal has been created in the target database and
 * holds the expected role memberships.
 */
export class DiagnoseConnectionTool implements Tool {
  [key: string]: any;
  name = "diagnose_connection";
  description = "Returns current database principal info, roles, server/database, and timestamp to verify connectivity & permissions.";

  inputSchema = {
    type: "object",
    properties: {
      includeRoleMembers: {
        type: "boolean",
        description: "If true, also returns all members of each fixed database role (may be slower). Default false." 
      }
    }
  } as any;

  async run(params: any) {
    const includeRoleMembers = !!params?.includeRoleMembers;
    try {
  const request = new sql.Request();

      // Query current user, db, server, roles
      const principalQuery = `SELECT DB_NAME() AS database_name, SUSER_SNAME() AS suser_name, ORIGINAL_LOGIN() AS original_login, USER_NAME() AS user_name`;
      const roleQuery = `SELECT rp.name AS role_name
                         FROM sys.database_role_members drm
                         JOIN sys.database_principals rp ON drm.role_principal_id = rp.principal_id
                         JOIN sys.database_principals mp ON drm.member_principal_id = mp.principal_id
                         WHERE mp.name = USER_NAME()
                         ORDER BY rp.name`;
      const principalResult = await request.query(principalQuery);
      const roleResult = await new sql.Request().query(roleQuery);

      let roles: string[] = roleResult.recordset.map(r => r.role_name);

      let roleMembers: Record<string, string[]> | undefined;
      if (includeRoleMembers) {
        roleMembers = {};
        if (roles.length) {
          const rmQuery = `SELECT rp.name AS role_name, mp.name AS member_name
                           FROM sys.database_role_members drm
                           JOIN sys.database_principals rp ON drm.role_principal_id = rp.principal_id
                           JOIN sys.database_principals mp ON drm.member_principal_id = mp.principal_id`;
          const full = await new sql.Request().query(rmQuery);
          for (const row of full.recordset) {
            roleMembers[row.role_name] ||= [];
            roleMembers[row.role_name].push(row.member_name);
          }
        }
      }

      return {
        success: true,
        timestampUtc: new Date().toISOString(),
        connectionActive: true,
        principal: principalResult.recordset[0] || null,
        roles,
        roleMembers: includeRoleMembers ? roleMembers : undefined
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.message || String(error)
      };
    }
  }
}
