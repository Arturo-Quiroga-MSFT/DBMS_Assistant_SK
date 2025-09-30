#!/usr/bin/env python3

import sys
sys.path.append('src')

from src.database import AzureSQLConnection
from src.nl_processor import NLToSQLConverter

def test_connection_and_queries():
    """Test the improved database connection and natural language processing"""
    
    print("🔍 Testing improved database connection...")
    
    # Test database connection
    db = AzureSQLConnection()
    connection_test = db.test_connection()
    
    if connection_test['status'] != 'success':
        print(f"❌ Connection failed: {connection_test['message']}")
        return
    
    print("✅ Database connection successful!")
    print(f"   Database: {connection_test['database_info']['database_name']}")
    print(f"   Tables found: {connection_test['table_count']}")
    
    # Get table list for NL processor
    tables = db.get_tables()
    table_info = {f"{t['schema_name']}.{t['table_name']}": t for t in tables}
    
    print("\n📋 Available tables:")
    for i, table in enumerate(tables[:10]):  # Show first 10 tables
        print(f"   {i+1}. {table['schema_name']}.{table['table_name']}")
    if len(tables) > 10:
        print(f"   ... and {len(tables) - 10} more tables")
    
    # Test natural language processing
    print("\n🗣️ Testing natural language processing...")
    
    nl_processor = NLToSQLConverter(table_info)
    
    # Test queries
    test_queries = [
        "show me the schema of the database",
        "show me all companies",
        "count rows in company table", 
        "list all tables",
        "describe the loan table"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        result = nl_processor.convert_natural_language(query)
        
        if result['success']:
            print(f"✅ Generated SQL: {result['sql_query'].strip()}")
            print(f"   Query Type: {result['query_type']}")
            print(f"   Safe: {result['is_safe']}")
            
            # Try to execute the query
            try:
                if result['query_type'] in ['SELECT', 'COUNT', 'DESCRIBE', 'LIST_TABLES']:
                    df = db.execute_query(result['sql_query'])
                    print(f"   Result: {len(df)} rows returned")
                    if len(df) > 0:
                        print(f"   Columns: {list(df.columns)}")
            except Exception as e:
                print(f"   ❌ Execution error: {str(e)}")
        else:
            print(f"❌ Conversion failed: {result['error']}")
    
    print("\n🎉 Testing completed!")
    db.close()

if __name__ == "__main__":
    test_connection_and_queries()