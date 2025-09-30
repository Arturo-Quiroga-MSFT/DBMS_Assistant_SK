"""
Security and configuration utilities
"""
import os
import re
import logging
from typing import List, Dict, Any, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

class SecurityManager:
    """Manages security policies and query validation"""
    
    def __init__(self):
        self.blocked_keywords = [
            'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'EXEC', 'EXECUTE',
            'MERGE', 'REPLACE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK',
            'TRANSACTION', 'BEGIN', 'DECLARE', 'SET', 'USE', 'BACKUP',
            'RESTORE', 'KILL', 'SHUTDOWN', 'WAITFOR', 'OPENROWSET',
            'OPENDATASOURCE', 'OPENQUERY', 'OPENXML', 'BULK',
            'sp_', 'xp_'
        ]
        
        self.allowed_ddl = ['CREATE TABLE', 'CREATE INDEX'] if os.getenv('ALLOW_DDL', 'false').lower() == 'true' else []
        self.max_result_rows = int(os.getenv('MAX_RESULT_ROWS', '1000'))
        self.query_timeout = int(os.getenv('QUERY_TIMEOUT', '30'))
        
    def validate_query(self, query: str) -> Tuple[bool, str, List[str]]:
        """
        Validate if a query is safe to execute
        Returns: (is_valid, reason, warnings)
        """
        warnings = []
        query_upper = query.upper().strip()
        
        # Remove comments
        query_clean = re.sub(r'--.*$', '', query_upper, flags=re.MULTILINE)
        query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)
        
        # Check for blocked keywords
        for keyword in self.blocked_keywords:
            if keyword in query_clean:
                # Allow specific DDL operations if enabled
                if keyword in ['CREATE', 'ALTER'] and any(ddl in query_clean for ddl in self.allowed_ddl):
                    warnings.append(f"DDL operation detected: {keyword}")
                    continue
                else:
                    return False, f"Blocked keyword detected: {keyword}", warnings
        
        # Check for dangerous patterns
        dangerous_patterns = [
            (r';\s*(DELETE|DROP|UPDATE|INSERT|TRUNCATE)', "Multiple statements with dangerous operations"),
            (r'UNION.*SELECT.*\(', "Potential UNION injection"),
            (r'1\s*=\s*1', "Potential tautology injection"),
            (r"'\s*OR\s*'", "Potential OR injection"),
            (r'EXEC\s*\(', "Dynamic SQL execution"),
        ]
        
        for pattern, reason in dangerous_patterns:
            if re.search(pattern, query_clean):
                return False, reason, warnings
        
        # Check if query is a SELECT and add row limits if needed
        if query_clean.startswith('SELECT') and 'TOP' not in query_clean and 'LIMIT' not in query_clean:
            if 'COUNT(' not in query_clean:
                warnings.append(f"Query will be limited to {self.max_result_rows} rows")
        
        # Check for potentially expensive operations
        expensive_patterns = [
            (r'SELECT\s+\*\s+FROM\s+\w+\s*$', "Full table scan without WHERE clause"),
            (r'LIKE\s+\'%.*%\'', "Full-text search pattern"),
            (r'ORDER\s+BY.*NEWID\(\)', "Random ordering (expensive)"),
        ]
        
        for pattern, warning in expensive_patterns:
            if re.search(pattern, query_clean):
                warnings.append(f"Performance warning: {warning}")
        
        return True, "Query validation passed", warnings
    
    def sanitize_query(self, query: str) -> str:
        """Sanitize and modify query for safety"""
        query = query.strip()
        query_upper = query.upper()
        
        # Add TOP clause to SELECT statements without it
        if query_upper.startswith('SELECT') and 'TOP' not in query_upper and 'COUNT(' not in query_upper:
            # Insert TOP clause after SELECT
            query = re.sub(r'^SELECT\s+', f'SELECT TOP {self.max_result_rows} ', query, flags=re.IGNORECASE)
        
        return query
    
    def log_query_execution(self, query: str, user_input: str, success: bool, error: str = None):
        """Log query execution for audit purposes"""
        log_entry = {
            'timestamp': logger.handlers[0].formatter.formatTime(logging.LogRecord('', 0, '', 0, '', (), None)),
            'user_input': user_input[:500],  # Truncate long inputs
            'generated_query': query[:1000],  # Truncate long queries
            'success': success,
            'error': error[:500] if error else None
        }
        
        if success:
            logger.info(f"Query executed successfully: {log_entry}")
        else:
            logger.error(f"Query execution failed: {log_entry}")

def rate_limit(max_calls: int = 10, window_seconds: int = 60):
    """Decorator for rate limiting function calls"""
    call_times = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            now = time.time()
            
            # Remove old calls outside the window
            while call_times and call_times[0] <= now - window_seconds:
                call_times.pop(0)
            
            # Check if we've exceeded the limit
            if len(call_times) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {window_seconds} seconds")
            
            # Record this call
            call_times.append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'app_title': os.getenv('APP_TITLE', 'DBMS Assistant'),
            'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true',
            'max_result_rows': int(os.getenv('MAX_RESULT_ROWS', '1000')),
            'query_timeout': int(os.getenv('QUERY_TIMEOUT', '30')),
            'allow_ddl': os.getenv('ALLOW_DDL', 'false').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO').upper(),
            'cache_ttl': int(os.getenv('CACHE_TTL', '300')),  # 5 minutes
            'rate_limit_calls': int(os.getenv('RATE_LIMIT_CALLS', '10')),
            'rate_limit_window': int(os.getenv('RATE_LIMIT_WINDOW', '60')),
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled"""
        return self.config.get('debug_mode', False)
    
    def get_security_settings(self) -> Dict[str, Any]:
        """Get security-related settings"""
        return {
            'max_result_rows': self.config.get('max_result_rows', 1000),
            'query_timeout': self.config.get('query_timeout', 30),
            'allow_ddl': self.config.get('allow_ddl', False),
            'rate_limit_calls': self.config.get('rate_limit_calls', 10),
            'rate_limit_window': self.config.get('rate_limit_window', 60),
        }

# Global instances
security_manager = SecurityManager()
config_manager = ConfigManager()

def setup_logging():
    """Setup application logging"""
    log_level = config_manager.get('log_level', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('dbms_assistant.log'),
            logging.StreamHandler()
        ]
    )

# Initialize logging
setup_logging()