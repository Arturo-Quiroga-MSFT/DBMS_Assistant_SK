# CONTOSO-FI DBMS Assistant 🗄️

A standalone web application for natural language database management with Azure SQL Database. This Streamlit-based application provides an intuitive interface to interact with your SQL database using plain English queries.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![Azure SQL](https://img.shields.io/badge/Azure%20SQL-Database-blue.svg)

## ✨ Features

### 🗣️ Natural Language Interface
- **Plain English Queries**: Ask questions like "Show me all companies" or "Count rows in loans table"
- **Intelligent SQL Generation**: Automatic conversion from natural language to SQL
- **Query Suggestions**: Built-in examples and suggestions for common operations

### 🛡️ Security & Safety
- **SQL Injection Protection**: Advanced pattern detection and prevention
- **Query Validation**: Multi-layer security checks before execution
- **Result Limits**: Automatic pagination to prevent large data dumps
- **Audit Logging**: Complete query execution logging for compliance

### 📊 Rich Data Visualization
- **Interactive Tables**: Browse and filter query results
- **Export Capabilities**: Download results as CSV files
- **Real-time Metrics**: Instant database statistics and counts
- **Schema Browser**: Explore table structures and relationships

### 🚀 Easy Management
- **Database Overview**: Real-time connection status and statistics
- **Quick Actions**: One-click access to common operations
- **Table Explorer**: Browse all tables with quick view/describe options
- **Error Handling**: User-friendly error messages with suggestions

## 🏗️ Architecture

```
StreamlitApp/
├── streamlit_app.py          # Main Streamlit application
├── src/
│   ├── database.py           # Azure SQL connection management
│   ├── nl_processor.py       # Natural language to SQL conversion
│   └── security.py           # Security validation and configuration
├── config/
├── requirements.txt          # Python dependencies
├── .env                      # Database configuration
├── setup.sh                  # Automated setup script
└── start.sh                  # Quick start script
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- ODBC Driver 17 for SQL Server
- Access to Azure SQL Database

### 1. Automatic Setup
```bash
# Clone or navigate to the StreamlitApp directory
cd /path/to/StreamlitApp

# Run the automated setup script
./setup.sh
```

### 2. Manual Setup (if needed)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install ODBC Driver (macOS with Homebrew)
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
HOMEBREW_NO_ENV_FILTERING=1 ACCEPT_EULA=Y brew install msodbcsql17
```

### 3. Configure Database Connection
Update the `.env` file with your Azure SQL Database credentials:
```env
SERVER_NAME=aqsqlserver001.database.windows.net
DATABASE_NAME=CONTOSO-FI
SQL_USER=arturoqu
SQL_PASSWORD=Porkinos.72848677
```

### 4. Start the Application
```bash
# Quick start
./start.sh

# Or manually
source venv/bin/activate
streamlit run streamlit_app.py
```

### 5. Access the Application
Open your browser and navigate to: http://localhost:8501

## 💬 Usage Examples

Once the application is running, you can use natural language queries like:

### Basic Data Retrieval
- **"Show me all companies"** → `SELECT TOP 100 * FROM [Company]`
- **"List all tables"** → Shows all database tables
- **"Count rows in loans"** → `SELECT COUNT(*) FROM [Loan]`

### Schema Exploration
- **"Describe the customer table"** → Shows table schema and column details
- **"What columns are in the company table?"** → Lists all columns with data types

### Advanced Queries
- **"Show me companies in New York"** → Filtered results with WHERE clauses
- **"Get loan payments from last month"** → Date-based filtering
- **"Find customers with high risk scores"** → Conditional queries

## 🛡️ Security Features

### Query Validation
- **Keyword Blocking**: Prevents dangerous SQL operations
- **Pattern Detection**: Identifies potential SQL injection attempts
- **Safe Operations Only**: Restricts to approved query types

### Data Protection
- **Result Limits**: Automatic TOP clauses to prevent large dumps
- **Connection Security**: Encrypted connections to Azure SQL
- **Audit Logging**: Complete query execution history

### Access Control
- **Rate Limiting**: Prevents abuse with configurable limits
- **Error Sanitization**: Safe error messages without sensitive data
- **Configuration Security**: Environment-based sensitive data storage

## ⚙️ Configuration

### Environment Variables
```env
# Database Connection
SERVER_NAME=your-server.database.windows.net
DATABASE_NAME=your-database-name
SQL_USER=your-username
SQL_PASSWORD=your-password

# Security Settings
TRUST_SERVER_CERTIFICATE=false
CONNECTION_TIMEOUT=30
MAX_RESULT_ROWS=1000

# Application Settings
APP_TITLE=CONTOSO-FI DBMS Assistant
DEBUG_MODE=false
ALLOW_DDL=false

# Rate Limiting
RATE_LIMIT_CALLS=10
RATE_LIMIT_WINDOW=60
```

### Advanced Configuration
- **DDL Operations**: Set `ALLOW_DDL=true` to enable CREATE TABLE operations
- **Debug Mode**: Set `DEBUG_MODE=true` for verbose logging
- **Custom Limits**: Adjust `MAX_RESULT_ROWS` for larger result sets

## 🔧 Troubleshooting

### Common Issues

#### Connection Failures
```bash
# Test database connection
python3 -c "from src.database import AzureSQLConnection; print(AzureSQLConnection().test_connection())"
```

#### ODBC Driver Issues
- **macOS**: Install via Homebrew or Microsoft's official installer
- **Verify Installation**: `odbcinst -q -d | grep "ODBC Driver 17"`

#### Permission Problems
- Ensure your SQL user has appropriate database permissions
- Check firewall rules for Azure SQL Database
- Verify your IP is whitelisted in Azure

#### Python Environment
```bash
# Verify Python version
python3 --version  # Should be 3.8+

# Check installed packages
pip list | grep streamlit
```

### Logging
The application creates detailed logs in `dbms_assistant.log`:
```bash
# View recent logs
tail -f dbms_assistant.log

# Search for errors
grep "ERROR" dbms_assistant.log
```

## 🚀 Deployment Options

### Local Development
- Default configuration for local testing and development
- Uses SQLite for lightweight operation

### Production Deployment
- Set `DEBUG_MODE=false`
- Configure proper logging levels
- Use environment variables for secrets
- Consider reverse proxy (nginx) for HTTPS

### Docker Deployment (Future)
```dockerfile
# Example Dockerfile structure
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py"]
```

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest tests/

# Format code
black src/ streamlit_app.py

# Lint code
flake8 src/ streamlit_app.py
```

### Adding New Features
1. **NL Patterns**: Add new patterns to `nl_processor.py`
2. **Security Rules**: Update validation in `security.py`
3. **UI Components**: Extend Streamlit interface in `streamlit_app.py`

## 📋 Supported Query Types

| Query Type | Example | Generated SQL |
|------------|---------|---------------|
| **Select Data** | "Show me all loans" | `SELECT TOP 100 * FROM [Loan]` |
| **Count Records** | "Count companies" | `SELECT COUNT(*) FROM [Company]` |
| **Describe Schema** | "Describe loans table" | `SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS...` |
| **List Tables** | "Show all tables" | `SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES...` |
| **Filtered Queries** | "Loans over 100000" | `SELECT * FROM [Loan] WHERE amount > 100000` |

## 📚 Database Schema (CONTOSO-FI)

The application is configured for the CONTOSO-FI database with tables including:
- **Company**: Company information and profiles
- **Loan**: Loan records and details
- **CustomerProfile**: Customer data and demographics
- **PaymentEvent**: Payment transactions and history
- **Collateral**: Loan collateral information
- And 17+ additional tables for comprehensive financial data

## 🔒 License

This project is proprietary to CONTOSO-FI. All rights reserved.

## 📞 Support

For issues, questions, or feature requests:
- **Internal**: Contact the development team
- **Logs**: Check `dbms_assistant.log` for detailed error information
- **Documentation**: Refer to this README and inline code comments

---

**CONTOSO-FI DBMS Assistant** - Making database management as easy as asking a question! 🚀