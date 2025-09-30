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
            'database_schema': [
                r'(?:show|get|display) (?:me )?(?:the )?(?:database|db) schema$',
                r'(?:show|get|display) (?:me )?(?:the )?schema (?:of )?(?:the )?(?:database|db)$',
                r'what (?:is|are) (?:the )?(?:database|db) schema$',
                r'(?:database|db) (?:schema|structure|overview)$'
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
        """Extract table name from natural language text with improved matching"""
        # Remove common words
        words = text.split()
        stop_words = {'the', 'a', 'an', 'from', 'in', 'of', 'to', 'with', 'table', 'data', 'rows', 'records'}
        filtered_words = [w for w in words if w.lower() not in stop_words]
        
        if not filtered_words:
            return None
        
        # Try to match against known tables with fuzzy matching
        if self.table_info:
            # Extract just table names without schema
            available_tables = []
            for full_table_name in self.table_info.keys():
                if '.' in full_table_name:
                    table_name = full_table_name.split('.')[-1]  # Get table name without schema
                else:
                    table_name = full_table_name
                available_tables.append((table_name, full_table_name))
            
            # Try each filtered word
            for word in filtered_words:
                word_lower = word.lower()
                
                # Exact match first
                for table_name, full_name in available_tables:
                    if word_lower == table_name.lower():
                        return full_name
                
                # Plural/singular matching
                word_singular = word_lower.rstrip('s') if word_lower.endswith('s') else word_lower
                word_plural = word_lower + 's' if not word_lower.endswith('s') else word_lower
                
                for table_name, full_name in available_tables:
                    table_lower = table_name.lower()
                    if (word_singular == table_lower or 
                        word_plural == table_lower or
                        word_lower in table_lower or 
                        table_lower in word_lower):
                        return full_name
                
                # Substring matching for common variations
                # e.g., "companies" -> "Company", "loans" -> "Loan"
                for table_name, full_name in available_tables:
                    if (word_lower.startswith(table_name.lower()[:3]) and len(table_name) >= 3) or \
                       (table_name.lower().startswith(word_lower[:3]) and len(word_lower) >= 3):
                        return full_name
        
        # If no match found, return the first filtered word as fallback
        return filtered_words[0]
    
    def convert_select_query(self, text: str) -> Optional[str]:
        """Convert natural language to SELECT query"""
        for pattern in self.query_patterns['select_all']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_name = self.extract_table_name(match.group(1))
                if table_name:
                    # Handle schema.table format properly
                    if '.' in table_name:
                        # Already has schema
                        formatted_table = f"[{table_name.split('.')[0]}].[{table_name.split('.')[1]}]"
                    else:
                        # Add default schema if needed
                        formatted_table = f"[dbo].[{table_name}]"
                    
                    return f"SELECT TOP 100 * FROM {formatted_table}"
        
        return None
    
    def convert_count_query(self, text: str) -> Optional[str]:
        """Convert natural language to COUNT query"""
        for pattern in self.query_patterns['count']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_name = self.extract_table_name(match.group(1))
                if table_name:
                    # Handle schema.table format properly
                    if '.' in table_name:
                        formatted_table = f"[{table_name.split('.')[0]}].[{table_name.split('.')[1]}]"
                    else:
                        formatted_table = f"[dbo].[{table_name}]"
                    
                    return f"SELECT COUNT(*) as record_count FROM {formatted_table}"
        
        return None
    
    def convert_describe_query(self, text: str) -> Optional[str]:
        """Convert natural language to DESCRIBE/schema query"""
        for pattern in self.query_patterns['describe']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                table_name = self.extract_table_name(match.group(1))
                if table_name:
                    # Extract just the table name without schema for INFORMATION_SCHEMA query
                    if '.' in table_name:
                        schema_name, actual_table_name = table_name.split('.', 1)
                    else:
                        schema_name = 'dbo'
                        actual_table_name = table_name
                    
                    return f"""
                    SELECT 
                        COLUMN_NAME as column_name,
                        DATA_TYPE as data_type,
                        IS_NULLABLE as is_nullable,
                        CHARACTER_MAXIMUM_LENGTH as max_length,
                        COLUMN_DEFAULT as default_value
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = '{actual_table_name}' AND TABLE_SCHEMA = '{schema_name}'
                    ORDER BY ORDINAL_POSITION
                    """
        
        return None
    
    def convert_database_schema_query(self, text: str) -> Optional[str]:
        """Convert natural language to database schema overview query"""
        for pattern in self.query_patterns['database_schema']:
            if re.search(pattern, text, re.IGNORECASE):
                return """
                SELECT 
                    t.TABLE_SCHEMA as schema_name,
                    t.TABLE_NAME as table_name,
                    COUNT(c.COLUMN_NAME) as column_count,
                    t.TABLE_TYPE as table_type
                FROM INFORMATION_SCHEMA.TABLES t
                LEFT JOIN INFORMATION_SCHEMA.COLUMNS c 
                    ON t.TABLE_SCHEMA = c.TABLE_SCHEMA 
                    AND t.TABLE_NAME = c.TABLE_NAME
                WHERE t.TABLE_TYPE = 'BASE TABLE'
                GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME, t.TABLE_TYPE
                ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME
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
        
        # Check for "database schema" first - highest priority
        if re.search(r'(?:database|db)\s+schema|schema\s+(?:of\s+)?(?:the\s+)?(?:database|db)', cleaned_text, re.IGNORECASE):
            sql_query = self.convert_database_schema_query(cleaned_text)
            if sql_query:
                sql_query = sqlparse.format(sql_query.strip(), reindent=True, keyword_case='upper')
                is_safe, safety_message = self.is_safe_query(sql_query)
                return {
                    'success': True,
                    'sql_query': sql_query,
                    'query_type': 'DATABASE_SCHEMA',
                    'is_safe': is_safe,
                    'safety_message': safety_message,
                    'original_text': text
                }
        
        # Check for "list tables" - second priority
        if re.search(r'(?:show|list|get) (?:all )?(?:the )?tables', cleaned_text, re.IGNORECASE):
            sql_query = self.convert_list_tables_query(cleaned_text)
            if sql_query:
                sql_query = sqlparse.format(sql_query.strip(), reindent=True, keyword_case='upper')
                is_safe, safety_message = self.is_safe_query(sql_query)
                return {
                    'success': True,
                    'sql_query': sql_query,
                    'query_type': 'LIST_TABLES', 
                    'is_safe': is_safe,
                    'safety_message': safety_message,
                    'original_text': text
                }
        
        # Try different conversion methods in order
        converters = [
            ('DESCRIBE', self.convert_describe_query),
            ('COUNT', self.convert_count_query),
            ('SELECT', self.convert_select_query)
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