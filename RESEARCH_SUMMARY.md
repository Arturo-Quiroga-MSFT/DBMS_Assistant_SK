# ![DBMS Agent Architecture](./architecture-diagram.png)
# Research Summary: SemanticKernel.Agents.DatabaseAgent

## What is this Repository?

This repository provides a Database Management System (DBMS) agent for the [Microsoft Semantic Kernel](https://github.com/microsoft/semantic-kernel) ecosystem. The agent enables natural language (NL2SQL) interaction with SQL databases, allowing users (such as DBAs) to manage, query, and analyze databases using natural language prompts. It leverages large language models (LLMs) and vector memory to understand schema, generate SQL, and ensure safe query execution.

## Key Features

  - Users can issue database management and query commands in natural language, which are translated into SQL queries by the agent.
  - Supports SQLite, SQL Server, MySQL, PostgreSQL, Oracle, OLEDB, and ODBC providers.
  - Built-in filters (e.g., Query Relevancy Filter) use LLMs to ensure only relevant and safe queries are executed, reducing risk of data exposure or inefficient queries.
  - Custom filters can be implemented for additional safety or compliance needs.
  - The agent memorizes database schema and relationships using vector embeddings, improving query accuracy and context awareness.
  - Can be run as a Docker container (MCP Server), making deployment and integration easy.
  - Designed to work as a plugin/agent within the Semantic Kernel framework, supporting advanced AI-driven workflows.

## How Does it Work?

1. **Agent Initialization:**
   - The agent connects to the target database and fetches schema information (tables, columns, relationships).
   - It generates vector embeddings for schema elements and stores them for fast retrieval and context.
2. **User Query Flow:**
   - User submits a natural language prompt (e.g., "Show me all orders from last month").
   - The agent uses LLMs to:
     - Generate an embedding for the prompt.
     - Retrieve relevant tables and schema context.
     - Generate a SQL query matching the intent.
     - Optionally filter or block unsafe/irrelevant queries.
   - Executes the SQL query and returns results in markdown format.
3. **Quality Assurance:**
   - Filters (e.g., Query Relevancy Filter) compare the user prompt and generated query for intent match and safety.
   - Custom filters can be added by implementing the `IQueryExecutionFilter` interface.

## Example Use Cases


## Security and Safety


## Deployment



## Steps to Test the Database Agent

1. **Clone the Repository**
  ```bash
  git clone https://github.com/kbeaugrand/SemanticKernel.Agents.DatabaseAgent.git
  cd SemanticKernel.Agents.DatabaseAgent
  ```
2. **Ensure Prerequisites**
  - [.NET 8.0 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
  - Docker installed (for containerized testing)
  - (Optional) Access to an Azure OpenAI or OpenAI API key for LLM features
3. **Build the Solution (Optional for Local Run)**
  ```bash
  dotnet build src/SemanticKernel.Plugins.DatabaseAgent.sln
  ```
4. **Run the MCP Server with Docker**
  - Example for SQLite (using the provided `northwind.db`):
  ```bash
  docker run -it --rm \
    -p 8080:5000 \
    -e AGENT__TRANSPORT__KIND=Sse \
    -e ASPNETCORE_URLS=http://+:5000 \
    -e DATABASE_PROVIDER=sqlite \
    -e DATABASE_CONNECTION_STRING="Data Source=northwind.db;Mode=ReadWrite" \
    -e MEMORY_KIND=Volatile \
    -e KERNEL_COMPLETION=gpt4omini \
    -e KERNEL_EMBEDDING=textembeddingada002 \
    -e SERVICES_GPT4OMINI_TYPE=AzureOpenAI \
    -e SERVICES_GPT4OMINI_ENDPOINT=https://xxx.openai.azure.com/ \
    -e SERVICES_GPT4OMINI_AUTH=APIKey \
    ...
  ```
  - Adjust environment variables for your DBMS and LLM provider as needed.
5. **Connect to the Agent**
  - Use HTTP/SSE/WebSocket endpoints as documented to send natural language queries.
  - Example: POST a prompt like "Show all customers from Germany" to the agent endpoint.
6. **Review Results**
  - The agent will return SQL results in markdown format.
  - Review logs and outputs for errors or blocked queries (quality assurance in action).
7. **(Optional) Test Quality Assurance**
  - Try sending ambiguous or unsafe queries to see how the agent filters or blocks them.
  - Implement a custom filter if needed by following the `IQueryExecutionFilter` interface.
8. **(Optional) Run Unit Tests**
  ```bash
  dotnet test tests/SemanticKernel.Agents.DatabaseAgent.Tests
  ```

## Conclusion

This solution enables AI-powered, natural language database management and analytics, making it easier for DBAs and other users to interact with SQL databases securely and efficiently. It is extensible, supports multiple DBMS backends, and is designed for integration with modern AI workflows.


*This file summarizes the findings from research into the SemanticKernel.Agents.DatabaseAgent repository as of September 2025.*
## RESEARCH_SUMMARY.md has been moved to the new dbms_agent_python directory.
