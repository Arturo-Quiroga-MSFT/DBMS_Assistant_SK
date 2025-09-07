# dbms_agent/query_execution.py

"""
Query Execution Agent: SQL execution, result formatting, and feedback collection.
"""


import os
import pyodbc
import pandas as pd

class QueryExecutionAgent:
    def __init__(self):
        # Azure SQL DB config from environment variables
        self.sql_server = os.getenv('AZURE_SQL_SERVER')
        self.sql_db = os.getenv('AZURE_SQL_DATABASE')
        self.sql_user = os.getenv('AZURE_SQL_USER')
        self.sql_password = os.getenv('AZURE_SQL_PASSWORD')
        self.sql_driver = os.getenv('AZURE_SQL_DRIVER', 'ODBC Driver 18 for SQL Server')
        self.conn_str = (
            f"DRIVER={{{self.sql_driver}}};"
            f"SERVER={self.sql_server};"
            f"DATABASE={self.sql_db};"
            f"UID={self.sql_user};"
            f"PWD={self.sql_password};"
            "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        self.connection = pyodbc.connect(self.conn_str)

    def execute_sql(self, sql_query):
        """Execute SQL query and return results as a pandas DataFrame."""
        with self.connection.cursor() as cursor:
            cursor.execute(sql_query)
            # If the statement produced no result set (e.g., comment or DDL),
            # cursor.description will be None — return empty DataFrame gracefully.
            if cursor.description is None:
                return pd.DataFrame()
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame.from_records(rows, columns=columns)

    def format_response(self, results):
        """Format results for user consumption (e.g., markdown table)."""
        if results.empty:
            return "No results found."
        return results.to_markdown(index=False)

    def collect_feedback(self, question, sql_query, results):
        """Collect and store feedback/metrics (stub: print to console)."""
        print("Feedback:")
        print(f"Question: {question}")
        print(f"SQL Query: {sql_query}")
        print(f"Results: {results.shape[0]} rows")
