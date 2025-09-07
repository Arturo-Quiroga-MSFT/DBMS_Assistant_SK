# dbms_agent/semantic_model.py

"""
Semantic Model Analysis: DDL/DML analysis, schema embedding, and vector store integration.

Note: Azure Cosmos DB is the selected and only backend for embedding storage (Azure AI Search option deprecated).
"""



import os
import logging
from typing import List, Dict, Any
import requests
from azure.cosmos import CosmosClient, PartitionKey

try:
    # Optional: only needed if remote transport available
    from .http_transport import get_http_transport_from_env, MCPHttpTransport  # type: ignore
except Exception:  # noqa: BLE001
    MCPHttpTransport = None  # type: ignore
    get_http_transport_from_env = None  # type: ignore

logger = logging.getLogger(__name__)

class SemanticModelAnalyzer:
    def __init__(self, db_connection):
        self.db_connection = db_connection
        # Cosmos DB config from environment variables (lazy init)
        self.cosmos_endpoint = os.getenv('COSMOS_ENDPOINT')
        self.cosmos_key = os.getenv('COSMOS_KEY')
        self.cosmos_db = os.getenv('COSMOS_DATABASE', 'dbms_agent')
        self.cosmos_container = os.getenv('COSMOS_CONTAINER', 'schema_vectors')
        self._cosmos_initialized = False
        self.client = None
        self.database = None
        self.container = None

    def _ensure_cosmos(self):
        if self._cosmos_initialized:
            return
        if not self.cosmos_endpoint or not self.cosmos_key:
            raise ValueError("COSMOS_ENDPOINT and COSMOS_KEY must be set for embedding storage.")
        self.client = CosmosClient(self.cosmos_endpoint, self.cosmos_key)
        self.database = self.client.create_database_if_not_exists(self.cosmos_db)
        self.container = self.database.create_container_if_not_exists(
            id=self.cosmos_container,
            partition_key=PartitionKey(path="/table_name")
        )
        self._cosmos_initialized = True

    def analyze_schema(self) -> List[Dict[str, Any]]:
        """Collect schema metadata.

        Resolution strategy:
          1. Try remote MCP tools (list_table, list_views) if MCP HTTP config present.
          2. (TODO) Fallback to direct DB introspection via db_connection.
          3. Return list of { name: str, type: 'table'|'view', columns: [str], schema?: str }.
        """
        # Attempt remote MCP if transport env present
        mcp_schema: List[Dict[str, Any]] = []
        if os.getenv('MCP_HTTP_BASE_URL'):
            try:
                transport = get_http_transport_from_env() if get_http_transport_from_env else None
                if transport and transport.health():
                    tools = transport.list_tools()
                    # list_table tool contract (from server enhancement): returns array of objects
                    if 'list_table' in tools:
                        try:
                            raw_tables = transport.call_tool('list_table', { 'includeColumns': True, 'columnSampleLimit': 50 }) or []
                            if isinstance(raw_tables, dict) and 'items' in raw_tables:
                                raw_tables = raw_tables.get('items') or []
                            for item in raw_tables:
                                if isinstance(item, dict) and item.get('qualified'):
                                    cols = item.get('columns') or []
                                    mcp_schema.append({
                                        'name': item.get('qualified'),
                                        'type': 'table',
                                        'schema': item.get('schema'),
                                        'table': item.get('table'),
                                        'columns': cols,
                                    })
                        except Exception as e:  # noqa: BLE001
                            logger.warning('Failed retrieving tables via list_table: %s', e)
                    if 'list_views' in tools:
                        try:
                            raw_views = transport.call_tool('list_views', {}) or []
                            if isinstance(raw_views, dict) and 'items' in raw_views:
                                raw_views = raw_views.get('items') or []
                            for item in raw_views:
                                if isinstance(item, dict) and item.get('qualified'):
                                    cols = item.get('columns') or []
                                    mcp_schema.append({
                                        'name': item.get('qualified'),
                                        'type': 'view',
                                        'schema': item.get('schema'),
                                        'table': item.get('view') or item.get('table'),
                                        'columns': cols,
                                    })
                        except Exception as e:  # noqa: BLE001
                            logger.warning('Failed retrieving views via list_views: %s', e)
                else:
                    logger.debug('MCP transport not healthy or unavailable for schema retrieval.')
            except Exception as e:  # noqa: BLE001
                logger.debug('Remote MCP schema retrieval skipped: %s', e)
        if mcp_schema:
            # Opportunistic enrichment: if any table has empty columns, try describe_table tool
            try:
                if any((not t.get('columns')) for t in mcp_schema):
                    transport = get_http_transport_from_env() if get_http_transport_from_env else None
                    if transport and transport.health() and 'describe_table' in transport.list_tools():
                        for t in mcp_schema:
                            if t.get('columns'):
                                continue
                            try:
                                result = transport.call_tool('describe_table', { 'tableName': t['name'] })
                                if isinstance(result, dict) and result.get('columns'):
                                    t['columns'] = [c.get('name') for c in result.get('columns') if isinstance(c, dict) and c.get('name')]
                            except Exception as inner_e:  # noqa: BLE001
                                logger.debug('describe_table enrichment failed for %s: %s', t.get('name'), inner_e)
            except Exception as e:  # noqa: BLE001
                logger.debug('describe_table enrichment skipped: %s', e)
            return mcp_schema
        # Local DB introspection fallback (pyodbc style connection)
        local_schema: List[Dict[str, Any]] = []
        if self.db_connection is not None:
            try:
                cursor = self.db_connection.cursor()
                # Gather tables
                cursor.execute("""
                    SELECT TABLE_SCHEMA, TABLE_NAME, 'table' AS OBJ_TYPE
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_TYPE='BASE TABLE'
                    UNION ALL
                    SELECT TABLE_SCHEMA, TABLE_NAME, 'view' AS OBJ_TYPE
                    FROM INFORMATION_SCHEMA.VIEWS
                """)
                rows = cursor.fetchall()
                # Build a map to attach columns
                for r in rows:
                    schema_name = r[0]
                    table_name = r[1]
                    obj_type = r[2]
                    qualified = f"{schema_name}.{table_name}" if schema_name else table_name
                    local_schema.append({
                        'name': qualified,
                        'schema': schema_name,
                        'table': table_name,
                        'type': obj_type,
                        'columns': []
                    })
                # Fetch columns
                cursor.execute("""
                    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    ORDER BY ORDINAL_POSITION
                """)
                col_rows = cursor.fetchall()
                index_map = { (item['schema'], item['table']): item for item in local_schema }
                for cr in col_rows:
                    schema_name = cr[0]
                    table_name = cr[1]
                    col_name = cr[2]
                    key = (schema_name, table_name)
                    if key in index_map:
                        index_map[key]['columns'].append(col_name)
            except Exception as e:  # noqa: BLE001
                logger.debug('Local DB introspection failed: %s', e)
        return local_schema

    def embed_schema(self, schema=None):
        """Generate and store schema embeddings in Cosmos DB as a vector store."""
        if schema is None:
            schema = self.analyze_schema()
        # Placeholder: generate embeddings for each table/column
        self._ensure_cosmos()
        for table in schema:
            embedding = self._generate_embedding(table)
            item = {
                'id': table['name'],
                'table_name': table['name'],
                'embedding': embedding,
                'metadata': table
            }
            self.container.upsert_item(item)

    def _generate_embedding(self, table):
        """
        Generate embedding for a table using Azure OpenAI text-embedding-3-small model.
        """
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
        if not endpoint or not api_key:
            raise ValueError("Azure OpenAI endpoint and API key must be set in environment variables.")
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version=2024-02-15-preview"
        # Use table name and columns as embedding input
        text = f"Table: {table['name']}, Columns: {', '.join(table.get('columns', []))}"
        data = {"input": text}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        embedding = response.json()["data"][0]["embedding"]
        return embedding
