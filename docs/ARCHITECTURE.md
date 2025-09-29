# DBMS Assistant Architecture

## Overview
The DBMS Assistant is a natural language to SQL system that can understand user queries in plain English and execute corresponding DDL (Data Definition Language) and DML (Data Manipulation Language) operations on various database systems.

## Core Components

### 1. Natural Language Processor (NLP Engine)
- **Query Parser**: Tokenizes and analyzes natural language input
- **Intent Classifier**: Determines the type of operation (DDL, DML, Admin)
- **Entity Extractor**: Identifies database objects (tables, columns, values)
- **Query Validator**: Validates logical consistency of parsed queries

### 2. SQL Generation Engine
- **Template Manager**: Maintains SQL templates for different operations
- **Query Builder**: Constructs SQL from parsed NL components
- **Dialect Adapter**: Adapts SQL for different DBMS (PostgreSQL, MySQL, SQL Server, SQLite)
- **Optimization Engine**: Applies basic query optimizations

### 3. Database Connector Framework
- **Connection Manager**: Handles database connections and pooling
- **Transaction Manager**: Manages database transactions
- **Result Processor**: Formats and processes query results
- **Schema Inspector**: Retrieves database schema information

### 4. Safety and Validation Layer
- **SQL Injection Prevention**: Sanitizes and validates inputs
- **Operation Validator**: Checks for dangerous operations
- **Permission Manager**: Validates user permissions
- **Confirmation Handler**: Prompts for destructive operations

### 5. User Interface Layer
- **CLI Interface**: Command-line interaction
- **Query History**: Maintains session history
- **Result Formatter**: Pretty-prints results
- **Help System**: Provides usage guidance

### 6. Monitoring and Logging
- **Query Logger**: Logs all executed queries
- **Performance Monitor**: Tracks execution times
- **Error Handler**: Manages and logs errors
- **Audit Trail**: Maintains operation history

## Data Flow

1. **Input Processing**: User enters natural language query
2. **NL Analysis**: Query is parsed and intent is classified
3. **SQL Generation**: Appropriate SQL is generated based on analysis
4. **Safety Check**: Generated SQL is validated for safety
5. **Database Execution**: SQL is executed on target database
6. **Result Processing**: Results are formatted and returned to user
7. **Logging**: All operations are logged for audit purposes

## Supported Operations

### DDL Operations
- CREATE TABLE/INDEX/VIEW
- ALTER TABLE (add/drop/modify columns)
- DROP TABLE/INDEX/VIEW
- CREATE/DROP DATABASE

### DML Operations  
- SELECT queries with WHERE, JOIN, GROUP BY, ORDER BY
- INSERT statements
- UPDATE statements
- DELETE statements

### Administrative Operations
- Show database schema
- List tables/indexes
- Show table structure
- Database statistics

## Security Features

- SQL injection prevention through parameterized queries
- Whitelist-based operation validation
- User confirmation for destructive operations
- Comprehensive audit logging
- Connection-level security

## Technology Stack

- **Python 3.9+**: Core language
- **spaCy/NLTK**: Natural language processing
- **SQLAlchemy**: Database abstraction
- **Click**: CLI framework
- **Rich**: Terminal formatting
- **Pydantic**: Data validation
- **Pytest**: Testing framework