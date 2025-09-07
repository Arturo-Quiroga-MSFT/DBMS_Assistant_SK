## Azure Container Apps Deployment Guide (MSSQL MCP Server)

This guide deploys the Node-based MSSQL MCP server (with optional HTTP bridge + API key auth) to Azure Container Apps (ACA).

### Prerequisites
- Azure CLI (latest)
- Logged in: `az login`
- Existing Container Apps environment (or create one)
- Azure Container Registry (ACR) or use `az acr build` to build/push
- Service Principal (Client ID / Secret / Tenant) with access to target Azure SQL DB

### 1. Build & Push Image (ACR)
Replace placeholders (RESOURCE_GROUP, ACR_NAME, IMAGE_TAG).
```bash
az acr build \
  --resource-group <RESOURCE_GROUP> \
  --registry <ACR_NAME> \
  --image mssql-mcp-server:<IMAGE_TAG> \
  MssqlMcpServer/Node
```

Resulting image reference: `<ACR_NAME>.azurecr.io/mssql-mcp-server:<IMAGE_TAG>`

### 2. Prepare Secrets & Config
Decide an API key (optional):
```bash
API_KEY=$(openssl rand -hex 24)
```

Mandatory env values (non-secret):
```
SERVER_NAME=yourserver.database.windows.net
DATABASE_NAME=yourdb
READONLY=true
HTTP_PORT=8080
CONNECTION_TIMEOUT=30
```

Secrets (store securely):
```
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
AZURE_TENANT_ID=<tenant-id>
MCP_API_KEY=$API_KEY   # optional; include if enabling auth
```

### 3. Create or Reference Container Apps Environment
If you need to create one:
```bash
az containerapp env create \
  --name <ACA_ENV_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --location <LOCATION>
```

### 4. Deploy Container App
```bash
IMAGE="<ACR_NAME>.azurecr.io/mssql-mcp-server:<IMAGE_TAG>"
RG=<RESOURCE_GROUP>
APP_NAME=mssql-mcp-server
ENV_NAME=<ACA_ENV_NAME>

az containerapp create \
  --name $APP_NAME \
  --resource-group $RG \
  --environment $ENV_NAME \
  --image $IMAGE \
  --ingress external \
  --target-port 8080 \
  --transport auto \
  --registry-server <ACR_NAME>.azurecr.io \
  --query properties.configuration.ingress.fqdn -o tsv \
  --env-vars \
    SERVER_NAME=$SERVER_NAME \
    DATABASE_NAME=$DATABASE_NAME \
    READONLY=true \
    HTTP_PORT=8080 \
    CONNECTION_TIMEOUT=30 \
  --secrets \
    azure-client-id=AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    azure-client-secret=AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
    azure-tenant-id=AZURE_TENANT_ID=$AZURE_TENANT_ID \
    mcp-api-key=MCP_API_KEY=$MCP_API_KEY
```

If using secrets with key:value pairs isn't supported by your CLI version, set secrets separately:
```bash
az containerapp secret set \
  --name $APP_NAME \
  --resource-group $RG \
  --secrets \
    AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
    AZURE_TENANT_ID=$AZURE_TENANT_ID \
    MCP_API_KEY=$MCP_API_KEY

az containerapp update \
  --name $APP_NAME \
  --resource-group $RG \
  --set-env-vars \
    SERVER_NAME=$SERVER_NAME \
    DATABASE_NAME=$DATABASE_NAME \
    READONLY=true \
    HTTP_PORT=8080 \
    CONNECTION_TIMEOUT=30 \
    MCP_API_KEY=secretref:MCP_API_KEY \
    AZURE_CLIENT_ID=secretref:AZURE_CLIENT_ID \
    AZURE_CLIENT_SECRET=secretref:AZURE_CLIENT_SECRET \
    AZURE_TENANT_ID=secretref:AZURE_TENANT_ID
```

### 5. Test Health & Tools
After deployment, obtain FQDN:
```bash
FQDN=$(az containerapp show -n $APP_NAME -g $RG --query properties.configuration.ingress.fqdn -o tsv)
curl -s https://$FQDN/health
```

List tools (with API key if enabled):
```bash
curl -H "Authorization: Bearer $API_KEY" https://$FQDN/tools | jq
```

Call a tool (example read tool):
```bash
curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' \
  https://$FQDN/call \
  -d '{"name":"read_data","arguments":{"query":"SELECT TOP 1 * FROM sys.objects"}}'
```

### 6. Rotate Secrets
To rotate the service principal secret or API key:
```bash
NEW_KEY=$(openssl rand -hex 24)
az containerapp secret set -n $APP_NAME -g $RG --secrets MCP_API_KEY=$NEW_KEY
az containerapp revision restart -n $APP_NAME -g $RG
```

### 7. Scaling (Optional)
```bash
az containerapp update -n $APP_NAME -g $RG \
  --min-replicas 1 --max-replicas 3
```

### 8. Logs & Troubleshooting
```bash
az containerapp logs show -n $APP_NAME -g $RG --tail 50
az containerapp logs show -n $APP_NAME -g $RG --follow
```

### 9. Cleanup
```bash
az containerapp delete -n $APP_NAME -g $RG
```

---
Security Notes:
- Always enable API key or future AAD auth before exposing write capabilities.
- Keep `READONLY=true` unless you explicitly need mutation tools.
- Consider private ingress + internal consumers for production.
