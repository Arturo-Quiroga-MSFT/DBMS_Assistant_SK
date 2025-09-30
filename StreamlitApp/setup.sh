#!/bin/bash

# CONTOSO-FI DBMS Assistant Setup Script
# This script installs dependencies and sets up the Streamlit application

echo "🚀 Setting up CONTOSO-FI DBMS Assistant..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing Python packages..."
pip install -r requirements.txt

# Install ODBC Driver for SQL Server (macOS)
echo "🔧 Checking ODBC Driver for SQL Server..."
if ! odbcinst -q -d | grep -q "ODBC Driver 17 for SQL Server"; then
    echo "⚠️  ODBC Driver 17 for SQL Server not found."
    echo "Please install it manually:"
    echo "1. Visit: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
    echo "2. Download and install the ODBC Driver 17 for SQL Server for macOS"
    echo "3. Run this setup script again after installation"
    
    # Try to install via Homebrew if available
    if command -v brew &> /dev/null; then
        echo "🍺 Attempting to install via Homebrew..."
        brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
        brew update
        HOMEBREW_NO_ENV_FILTERING=1 ACCEPT_EULA=Y brew install msodbcsql17 mssql-tools
    fi
else
    echo "✅ ODBC Driver 17 for SQL Server found"
fi

# Test database connection
echo "🔍 Testing database connection..."
python3 -c "
import sys
sys.path.append('src')
from src.database import AzureSQLConnection
try:
    db = AzureSQLConnection()
    result = db.test_connection()
    if result['status'] == 'success':
        print('✅ Database connection successful!')
        print(f'   Database: {result[\"database_info\"][\"database_name\"]}')
        print(f'   Tables: {result[\"table_count\"]}')
    else:
        print('❌ Database connection failed:')
        print(f'   {result[\"message\"]}')
        sys.exit(1)
except Exception as e:
    print(f'❌ Connection test error: {str(e)}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "🚀 To start the application, run:"
    echo "   source venv/bin/activate"
    echo "   streamlit run streamlit_app.py"
    echo ""
    echo "📱 The app will be available at: http://localhost:8501"
    echo ""
else
    echo ""
    echo "❌ Setup encountered issues. Please check the error messages above."
    echo "📋 Common issues:"
    echo "   1. Missing ODBC driver - install ODBC Driver 17 for SQL Server"
    echo "   2. Incorrect database credentials in .env file"
    echo "   3. Network connectivity issues"
    exit 1
fi