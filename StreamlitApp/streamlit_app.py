"""
CONTOSO-FI DBMS Assistant - Streamlit Application
A standalone web interface for natural language database management
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys
from typing import Dict, Any, List

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database import AzureSQLConnection
from src.nl_processor import NLToSQLConverter

# Page configuration
st.set_page_config(
    page_title="CONTOSO-FI DBMS Assistant",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .query-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_database_connection():
    """Get cached database connection"""
    return AzureSQLConnection()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_table_list():
    """Get cached list of tables"""
    try:
        db = get_database_connection()
        return db.get_tables()
    except Exception as e:
        st.error(f"Failed to get table list: {str(e)}")
        return []

@st.cache_data(ttl=300)
def get_database_info():
    """Get cached database information"""
    try:
        db = get_database_connection()
        return db.get_database_info()
    except Exception as e:
        st.error(f"Failed to get database info: {str(e)}")
        return {}

def display_header():
    """Display the application header"""
    st.markdown('<div class="main-header">🗄️ CONTOSO-FI DBMS Assistant</div>', unsafe_allow_html=True)
    st.markdown("### Natural Language Database Management Interface")
    st.markdown("---")

def display_sidebar():
    """Display the sidebar with database information and quick actions"""
    st.sidebar.markdown("## 📊 Database Overview")
    
    # Database connection status
    try:
        db = get_database_connection()
        connection_status = db.test_connection()
        
        if connection_status['status'] == 'success':
            st.sidebar.success("✅ Connected to CONTOSO-FI")
            
            # Database info
            db_info = connection_status.get('database_info', {})
            st.sidebar.markdown(f"**Database:** {db_info.get('database_name', 'N/A')}")
            st.sidebar.markdown(f"**Tables:** {connection_status.get('table_count', 0)}")
            
        else:
            st.sidebar.error("❌ Connection Failed")
            st.sidebar.error(connection_status.get('message', 'Unknown error'))
            
    except Exception as e:
        st.sidebar.error(f"❌ Error: {str(e)}")
    
    st.sidebar.markdown("---")
    
    # Quick actions
    st.sidebar.markdown("## ⚡ Quick Actions")
    
    if st.sidebar.button("📋 List All Tables"):
        st.session_state.quick_query = "list all tables"
    
    if st.sidebar.button("📊 Database Statistics"):
        st.session_state.quick_query = "show database statistics"
    
    # Table selector
    tables = get_table_list()
    if tables:
        st.sidebar.markdown("## 📑 Quick Table Access")
        selected_table = st.sidebar.selectbox(
            "Select a table:",
            options=[f"{t['schema_name']}.{t['table_name']}" for t in tables],
            index=None,
            placeholder="Choose a table..."
        )
        
        if selected_table:
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("👁️ View", key=f"view_{selected_table}"):
                    st.session_state.quick_query = f"show me {selected_table}"
            with col2:
                if st.button("📋 Schema", key=f"schema_{selected_table}"):
                    st.session_state.quick_query = f"describe {selected_table}"

def execute_query(nl_query: str) -> Dict[str, Any]:
    """Execute a natural language query"""
    try:
        # Get database connection and table info
        db = get_database_connection()
        tables = get_table_list()
        table_info = {f"{t['schema_name']}.{t['table_name']}": t for t in tables}
        
        # Initialize NL processor
        nl_processor = NLToSQLConverter(table_info)
        
        # Convert natural language to SQL
        conversion_result = nl_processor.convert_natural_language(nl_query)
        
        if not conversion_result['success']:
            return conversion_result
        
        sql_query = conversion_result['sql_query']
        
        # Safety check
        if not conversion_result['is_safe']:
            return {
                'success': False,
                'error': f"Query rejected for safety: {conversion_result['safety_message']}",
                'sql_query': sql_query
            }
        
        # Execute the query
        if conversion_result['query_type'] in ['SELECT', 'COUNT', 'DESCRIBE', 'LIST_TABLES', 'DATABASE_SCHEMA']:
            # Read query
            result_df = db.execute_query(sql_query)
            return {
                'success': True,
                'query_type': conversion_result['query_type'],
                'sql_query': sql_query,
                'result': result_df,
                'rows_affected': len(result_df)
            }
        else:
            # Write query
            rows_affected = db.execute_non_query(sql_query)
            return {
                'success': True,
                'query_type': conversion_result['query_type'],
                'sql_query': sql_query,
                'rows_affected': rows_affected,
                'message': f'Query executed successfully. {rows_affected} rows affected.'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def display_query_result(result: Dict[str, Any]):
    """Display query execution results"""
    if result['success']:
        # Show generated SQL
        st.markdown("#### 🔍 Generated SQL Query:")
        st.markdown(f'<div class="query-box">{result["sql_query"]}</div>', unsafe_allow_html=True)
        
        # Show results
        if 'result' in result and not result['result'].empty:
            st.markdown("#### 📊 Query Results:")
            
            # Display data
            st.dataframe(result['result'], use_container_width=True)
            
            # Show summary
            st.markdown(f"**Rows returned:** {len(result['result'])}")
            
            # Export options
            col1, col2 = st.columns(2)
            with col1:
                csv = result['result'].to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            # Create visualizations for certain query types
            if result.get('query_type') == 'COUNT' and len(result['result']) == 1:
                # Display count as a metric
                count_value = result['result'].iloc[0, 0]
                st.metric("Record Count", count_value)
                
        elif 'message' in result:
            st.markdown(f'<div class="success-box">{result["message"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Query executed successfully with no results to display.")
            
    else:
        # Show error
        st.markdown(f'<div class="error-box">❌ Error: {result["error"]}</div>', unsafe_allow_html=True)
        
        if 'sql_query' in result:
            st.markdown("#### Generated SQL (for reference):")
            st.code(result['sql_query'], language='sql')
        
        if 'suggestions' in result:
            st.markdown("#### 💡 Suggestions:")
            for suggestion in result['suggestions']:
                st.markdown(f"- {suggestion}")

def main():
    """Main application function"""
    display_header()
    
    # Sidebar
    display_sidebar()
    
    # Main content area
    st.markdown("## 💬 Natural Language Query Interface")
    st.markdown("Ask questions about your database in plain English!")
    
    # Example queries
    with st.expander("💡 Example Queries"):
        st.markdown("""
        - **"Show me the schema of the database"** - Display all tables with column counts (database overview)
        - **"Show me all companies"** - Display all records from the Company table
        - **"Count rows in loans"** - Get the number of records in the Loan table
        - **"Describe the customer table"** - Show the schema of the CustomerProfile table
        - **"List all tables"** - Display all tables in the database
        - **"Show me loans where amount > 100000"** - Filter loans by amount (advanced)
        """)
    
    # Query input
    query_input = st.text_area(
        "🔍 Enter your question:",
        height=100,
        placeholder="e.g., Show me all companies with their addresses",
        help="Type your question in natural language"
    )
    
    # Handle quick queries from sidebar
    if hasattr(st.session_state, 'quick_query') and st.session_state.quick_query:
        query_input = st.session_state.quick_query
        st.session_state.quick_query = ""
    
    # Execute button
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        execute_button = st.button("🚀 Execute Query", type="primary")
    with col2:
        clear_button = st.button("🗑️ Clear")
    
    if clear_button:
        st.rerun()
    
    # Execute query
    if execute_button and query_input.strip():
        with st.spinner("Processing your query..."):
            result = execute_query(query_input.strip())
            display_query_result(result)
    elif execute_button:
        st.warning("Please enter a query first.")
    
    # Footer
    st.markdown("---")
    st.markdown("### 🛡️ Security Features")
    st.markdown("""
    - **SQL Injection Protection** - All queries are validated for dangerous patterns
    - **Read Limit Protection** - SELECT queries are limited to prevent large data dumps
    - **Safe Operations Only** - Only approved operations are allowed by default
    """)

if __name__ == "__main__":
    main()