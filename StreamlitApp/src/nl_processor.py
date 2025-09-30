"""
Natural Language to SQL conversion module
"""
import re
import sqlparse
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class NLToSQLConverter:
    """Converts natural language queries to SQL statements"""
    
    def __init__(self, table_info: Optional[Dict[str, Any]] = None):
        self.table_info = table_info or {}
        self.dangerous_keywords = [
            'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'EXEC', 'EXECUTE',
            'MERGE', 'REPLACE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK',
            'TRANSACTION', 'BEGIN', 'DECLARE', 'SET', 'USE', 'BACKUP',
            'RESTORE', 'KILL', 'SHUTDOWN', 'WAITFOR', 'OPENROWSET',
            'OPENDATASOURCE', 'OPENQUERY', 'OPENXML', 'BULK'
        ]
        
        # Common query patterns
        self.query_patterns = {
            'select_all': [
                r'show (?:me )?(?:all )?(?:the )?(.+?)(?:\s+table)?(?:\s+data)?$',
                r'list (?:all )?(?:the )?(.+?)(?:\s+table)?(?:\s+data)?$',
                r'get (?:all )?(?:the )?(.+?)(?:\s+table)?(?:\s+data)?$',
                r'select (?:all )?(?:from )?(?:the )?(.+?)(?:\s+table)?$'
            ],
            'count': [
                r'(?:how many|count) (?:rows )?(?:in )?(?:the )?(.+?)(?:\s+table)?$',
                r'count (?:of )?(?:records )?(?:in )?(?:the )?(.+?)(?:\s+table)?$'
            ],
            'describe': [
                r'describe (?:the )?(.+?)(?:\s+table)?$',
                r'(?:show|get) (?:the )?schema (?:of )?(?:the )?(.+?)(?:\s+table)?$',
                r'(?:show|get) (?:the )?structure (?:of )?(?:the )?(.+?)(?:\s+table)?$',
                r'what (?:are )?(?:the )?columns (?:in )?(?:the )?(.+?)(?:\s+table)?$'
            ],
            'list_tables': [
                r'(?:show|list|get) (?:all )?(?:the )?tables$',
                r'what tables (?:are )?(?:in )?(?:the )?database$'
            ],
            'create_table': [
                r'create (?:a )?(?:new )?table (?:called )?(.+?)(?:\s+with)?(?:\s+columns?)?(?:\s+(.+))?$'
            ],
            'insert': [
                r'(?:add|insert) (?:a )?(?:new )?(?:record|row) (?:to|into) (?:the )?(.+?)(?:\s+table)?(?:\s+with)?(?:\s+(.+))?$'
            ],
            'update': [
                r'update (?:the )?(.+?)(?:\s+table)? set (.+?) where (.+)$',
                r'change (?:the )?(.+?) (?:in )?(?:the )?(.+?)(?:\s+table)? (?:to|=) (.+?) where (.+)$'
            ]
        }
    
    def clean_input(self, text: str) -> str:
        """Clean and normalize input text"""
        text = text.strip().lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def is_safe_query(self, query: str) -> Tuple[bool, str]:
        """Check if the query is safe to execute"""
        query_upper = query.upper()
        
        # Check for dangerous keywords
        for keyword in self.dangerous_keywords:
            if keyword in query_upper:
                # Allow CREATE TABLE statements
                if keyword == 'CREATE' and 'CREATE TABLE' in query_upper:
                    continue
                # Allow ALTER TABLE for column operations
                elif keyword == 'ALTER' and 'ALTER TABLE' in query_upper:
                    continue
                else:
                    return False, f"Dangerous keyword detected: {keyword}"
        
        # Check for SQL injection patterns
        dangerous_patterns = [
            r';\s*(DELETE|DROP|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)',
            r'UNION\s+(?:ALL\s+)?SELECT.*?(DELETE|DROP|UPDATE|INSERT)',
            r'--.*?(DELETE|DROP|UPDATE|INSERT)',
            r'/\*.*?(DELETE|DROP|UPDATE|INSERT).*?\*/',
            r'EXEC\s*\(',
            r'sp_',
            r'xp_'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper):
                return False, f"Potentially dangerous SQL pattern detected"
        
        return True, "Query appears safe"
    
    def extract_table_name(self, text: str) -> Optional[str]:
        """Extract table name from natural language text"""
        # Remove common words
        words = text.split()
        stop_words = {'the', 'a', 'an', 'from', 'in', 'of', 'to', 'with', 'table', 'data'}
        filtered_words = [w for w in words if w not in stop_words]
        
        if filtered_words:
            # Try to match against known tables
            potential_table = filtered_words[0]
            if self.table_info:
                for table in self.table_info.keys():
                    if potential_table.lower() in table.lower() or table.lower() in potential_table.lower():
                        return table
            return potential_table
        
        return None
    
    def convert_select_query(self, text: str) -> Optional[str]:
        """Convert natural language to SELECT query"""
        for pattern in self.query_patterns['select_all']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_name = self.extract_table_name(match.group(1))
                if table_name:
                    # Add basic WHERE clause to prevent full table scans
                    return f"SELECT TOP 100 * FROM [{table_name}]"
        
        return None
    
    def convert_count_query(self, text: str) -> Optional[str]:
        """Convert natural language to COUNT query"""
        for pattern in self.query_patterns['count']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_name = self.extract_table_name(match.group(1))
                if table_name:
                    return f"SELECT COUNT(*) as record_count FROM [{table_name}]"
        
        return None
    
    def convert_describe_query(self, text: str) -> Optional[str]:
        """Convert natural language to DESCRIBE/schema query"""
        for pattern in self.query_patterns['describe']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_name = self.extract_table_name(match.group(1))
                if table_name:
                    return f"""
                    SELECT 
                        COLUMN_NAME as column_name,
                        DATA_TYPE as data_type,
                        IS_NULLABLE as is_nullable,
                        CHARACTER_MAXIMUM_LENGTH as max_length,
                        COLUMN_DEFAULT as default_value
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = '{table_name}'
                    ORDER BY ORDINAL_POSITION
                    """
        
        return None
    
    def convert_list_tables_query(self, text: str) -> Optional[str]:
        """Convert natural language to list tables query"""
        for pattern in self.query_patterns['list_tables']:
            if re.search(pattern, text, re.IGNORECASE):
                return """
                SELECT 
                    TABLE_SCHEMA as schema_name,
                    TABLE_NAME as table_name,
                    TABLE_TYPE as table_type
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
                """
        
        return None
    
    def convert_natural_language(self, text: str) -> Dict[str, Any]:
        """Convert natural language to SQL query"""
        cleaned_text = self.clean_input(text)
        
        # Try different conversion methods
        converters = [
            ('SELECT', self.convert_select_query),
            ('COUNT', self.convert_count_query),
            ('DESCRIBE', self.convert_describe_query),
            ('LIST_TABLES', self.convert_list_tables_query)
        ]
        
        for query_type, converter in converters:
            sql_query = converter(cleaned_text)
            if sql_query:
                # Clean up the SQL query
                sql_query = sqlparse.format(sql_query.strip(), reindent=True, keyword_case='upper')
                
                # Safety check
                is_safe, safety_message = self.is_safe_query(sql_query)
                
                return {
                    'success': True,
                    'sql_query': sql_query,
                    'query_type': query_type,
                    'is_safe': is_safe,
                    'safety_message': safety_message,
                    'original_text': text
                }
        
        # If no pattern matches, return error
        return {
            'success': False,
            'error': 'Could not understand the natural language query',
            'original_text': text,
            'suggestions': [
                'Try: "Show me all customers"',
                'Try: "Count rows in loans table"',
                'Try: "Describe the company table"',
                'Try: "List all tables"'
            ]
        }
    
    def suggest_corrections(self, text: str) -> List[str]:
        """Suggest corrections for unclear queries"""
        suggestions = []
        
        if 'show' in text.lower() or 'list' in text.lower():
            suggestions.append("Try: 'Show me all [table_name]'")
            suggestions.append("Try: 'List all tables'")
        
        if 'count' in text.lower() or 'how many' in text.lower():
            suggestions.append("Try: 'Count rows in [table_name]'")
        
        if 'describe' in text.lower() or 'schema' in text.lower():
            suggestions.append("Try: 'Describe the [table_name] table'")
        
        if not suggestions:
            suggestions = [
                "Try: 'Show me all customers'",
                "Try: 'Count rows in loans'",
                "Try: 'Describe the company table'",
                "Try: 'List all tables'"
            ]
        
        return suggestions