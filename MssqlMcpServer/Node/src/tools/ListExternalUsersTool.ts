import sql from "mssql";
import { Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * ListExternalUsersTool
 * Lists Azure AD / External users & groups (service principals, groups, users) present
 * as contained database principals, along with their role memberships.
 */
export class ListExternalUsersTool implements Tool {
  [key: string]: any;
  name = "list_external_users";
  description = "Lists external (Azure AD) database principals and their role memberships.";

  inputSchema = {
    type: "object",
    properties: {
      nameFilter: {
        type: "string",
        description: "Optional substring filter applied to principal name (case-insensitive)."
      }
    }
  } as any;

  async run(params: any) {
    const nameFilter = (params?.nameFilter || "").trim();
    try {
      const request = new sql.Request();
      const filterClause = nameFilter ? `AND p.name LIKE '%' + @nameFilter + '%'` : "";
      if (nameFilter) request.input('nameFilter', sql.NVarChar, nameFilter);

      const query = `;WITH ext AS (
  SELECT principal_id, name, type_desc, authentication_type_desc, create_date, modify_date
  FROM sys.database_principals p
  WHERE authentication_type_desc = 'EXTERNAL'
    AND type_desc IN ('EXTERNAL_USER','EXTERNAL_GROUP')
    AND name NOT LIKE '##%' -- exclude internal
    ${filterClause}
)
SELECT e.name,
       e.type_desc,
       e.authentication_type_desc,
       e.create_date,
       e.modify_date,
       r.name AS role_name
FROM ext e
LEFT JOIN sys.database_role_members drm ON e.principal_id = drm.member_principal_id
LEFT JOIN sys.database_principals r ON drm.role_principal_id = r.principal_id
ORDER BY e.name, r.name;`;

      const result = await request.query(query);

      // Aggregate roles
      const map: Record<string, any> = {};
      for (const row of result.recordset) {
        const entry = map[row.name] || (map[row.name] = {
          name: row.name,
          type: row.type_desc,
            authentication: row.authentication_type_desc,
            createDate: row.create_date,
            modifyDate: row.modify_date,
            roles: [] as string[]
        });
        if (row.role_name && !entry.roles.includes(row.role_name)) entry.roles.push(row.role_name);
      }

      const items = Object.values(map).sort((a: any, b: any) => a.name.localeCompare(b.name));

      return {
        success: true,
        count: items.length,
        items
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.message || String(error)
      };
    }
  }
}
