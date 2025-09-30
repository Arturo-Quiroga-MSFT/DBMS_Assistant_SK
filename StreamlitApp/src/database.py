"""
Database connection module for Azure SQL Database
"""
import os
import pyodbc
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
import logging
from urllib.parse import quote_plus
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureSQLConnection:
    """Manages connections to Azure SQL Database"""
    
    def __init__(self):
        load_dotenv()
        self.connection: Optional[pyodbc.Connection] = None
        self.engine = None
        self.connection_string = self._build_connection_string()
        self._connection_active = False
        
    def _build_connection_string(self) -> str:
        """Build connection string from environment variables"""
        server = os.getenv('SERVER_NAME')
        database = os.getenv('DATABASE_NAME')
        username = os.getenv('SQL_USER')
        password = os.getenv('SQL_PASSWORD')
        trust_cert = os.getenv('TRUST_SERVER_CERTIFICATE', 'false').lower() == 'true'
        timeout = os.getenv('CONNECTION_TIMEOUT', '30')
        
        if not all([server, database, username, password]):
            raise ValueError("Missing required database connection parameters")
        
        # Build connection string for SQL Server authentication
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate={'yes' if trust_cert else 'no'};"
            f"Connection Timeout={timeout};"
        )
        
        return conn_str
    
    def _get_sqlalchemy_engine(self):
        """Get or create SQLAlchemy engine for better pandas integration"""
        if not SQLALCHEMY_AVAILABLE:
            return None
            
        if self.engine is None:
            server = os.getenv('SERVER_NAME')
            database = os.getenv('DATABASE_NAME')
            username = os.getenv('SQL_USER')
            password = os.getenv('SQL_PASSWORD')
            
            # URL encode password to handle special characters
            password_encoded = quote_plus(password)
            
            # Create SQLAlchemy connection string
            connection_string = f"mssql+pyodbc://{username}:{password_encoded}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
            
            self.engine = create_engine(
                connection_string,
                poolclass=StaticPool,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
        
        return self.engine
    
    def connect(self) -> bool:
        """Establish connection to the database"""
        try:
            # Try SQLAlchemy first for better pandas integration
            engine = self._get_sqlalchemy_engine()
            if engine:
                # Test the connection
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to Azure SQL Database (SQLAlchemy)")
                self._connection_active = True
                return True
            
            # Fallback to pyodbc
            if self.connection and not self._connection_active:
                self.close()
            
            if not self.connection:
                self.connection = pyodbc.connect(self.connection_string)
                logger.info("Successfully connected to Azure SQL Database (pyodbc)")
                self._connection_active = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            self._connection_active = False
            return False
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            self.connection = None
        
        if self.engine:
            try:
                self.engine.dispose()
            except:
                pass
            self.engine = None
            
        self._connection_active = False
        logger.info("Database connection closed")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame"""
        if not self._connection_active:
            if not self.connect():
                raise Exception("Unable to establish database connection")
        
        try:
            # Use SQLAlchemy engine if available for better pandas integration
            engine = self._get_sqlalchemy_engine()
            if engine:
                if params:
                    df = pd.read_sql(text(query), engine, params=params)
                else:
                    df = pd.read_sql(text(query), engine)
                return df
            
            # Fallback to pyodbc connection
            if not self.connection:
                if not self.connect():
                    raise Exception("Unable to establish database connection")
            
            if params:
                df = pd.read_sql(query, self.connection, params=params)
            else:
                df = pd.read_sql(query, self.connection)
            return df
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            # Try to reconnect on failure
            self._connection_active = False
            raise
    
    def execute_non_query(self, query: str, params: Optional[Tuple] = None) -> int:
        """Execute INSERT, UPDATE, DELETE, or DDL statements"""
        if not self._connection_active:
            if not self.connect():
                raise Exception("Unable to establish database connection")
        
        try:
            # Use SQLAlchemy engine if available
            engine = self._get_sqlalchemy_engine()
            if engine:
                with engine.connect() as conn:
                    if params:
                        result = conn.execute(text(query), params)
                    else:
                        result = conn.execute(text(query))
                    conn.commit()
                    rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0
                    logger.info(f"Query executed successfully. Rows affected: {rows_affected}")
                    return rows_affected
            
            # Fallback to pyodbc
            if not self.connection:
                if not self.connect():
                    raise Exception("Unable to establish database connection")
            
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows_affected = cursor.rowcount
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Query executed successfully. Rows affected: {rows_affected}")
            return rows_affected
            
        except Exception as e:
            try:
                if self.connection:
                    self.connection.rollback()
            except:
                pass
            logger.error(f"Query execution failed: {str(e)}")
            self._connection_active = False
            raise
    
    def get_tables(self) -> List[Dict[str, str]]:
        """Get list of all tables in the database"""
        query = """
        SELECT 
            TABLE_SCHEMA as schema_name,
            TABLE_NAME as table_name,
            TABLE_TYPE as table_type
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        
        df = self.execute_query(query)
        return df.to_dict('records')
    
    def get_table_schema(self, table_name: str, schema_name: str = 'dbo') -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        query = """
        SELECT 
            COLUMN_NAME as column_name,
            DATA_TYPE as data_type,
            IS_NULLABLE as is_nullable,
            CHARACTER_MAXIMUM_LENGTH as max_length,
            NUMERIC_PRECISION as precision,
            NUMERIC_SCALE as scale,
            COLUMN_DEFAULT as default_value,
            ORDINAL_POSITION as position
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = ? AND TABLE_SCHEMA = ?
        ORDER BY ORDINAL_POSITION
        """
        
        df = self.execute_query(query, (table_name, schema_name))
        return df.to_dict('records')
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get general database information"""
        queries = {
            'version': "SELECT @@VERSION as version",
            'database_name': "SELECT DB_NAME() as database_name",
            'table_count': "SELECT COUNT(*) as table_count FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'",
            'view_count': "SELECT COUNT(*) as view_count FROM INFORMATION_SCHEMA.VIEWS"
        }
        
        info = {}
        for key, query in queries.items():
            try:
                result = self.execute_query(query)
                info[key] = result.iloc[0, 0] if not result.empty else None
            except Exception as e:
                info[key] = f"Error: {str(e)}"
        
        return info
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the database connection and return status"""
        try:
            if self.connect():
                info = self.get_database_info()
                tables = self.get_tables()
                
                return {
                    'status': 'success',
                    'message': 'Connection successful',
                    'database_info': info,
                    'table_count': len(tables),
                    'tables': tables[:10]  # Return first 10 tables
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Failed to establish connection'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection test failed: {str(e)}'
            }
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()