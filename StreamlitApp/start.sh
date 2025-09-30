#!/bin/bash

# Quick start script for CONTOSO-FI DBMS Assistant
# Activates virtual environment and starts the Streamlit app

echo "🚀 Starting CONTOSO-FI DBMS Assistant..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not found. Please run setup.sh first."
    exit 1
fi

# Start the application
echo "🌐 Starting Streamlit application..."
echo "📱 The app will be available at: http://localhost:8501"
echo "🛑 Press Ctrl+C to stop the application"
echo ""

streamlit run streamlit_app.py