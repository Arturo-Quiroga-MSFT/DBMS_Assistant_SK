# dbms_agent/nl2sql.py

"""
NL2SQL Agent: Table selection, SQL generation, and quality filters using the semantic model.
"""


from typing import List

class NL2SQLAgent:
    def __init__(self, semantic_model_analyzer):
        self.semantic_model_analyzer = semantic_model_analyzer

    def select_tables(self, question: str) -> List[str]:
        """
        Select relevant tables for the question using schema embeddings from the semantic model.
        This is a stub: in a real implementation, use embedding similarity search.
        """
        schema = self.semantic_model_analyzer.analyze_schema()
        # Placeholder: return all table names
        return [table['name'] for table in schema]

    def generate_sql(self, question: str, tables: List[str]) -> str:
        """
        Generate SQL query from natural language question and selected tables.
        This is a stub: in a real implementation, use an LLM or prompt template.
        """
        # Placeholder: return a dummy SQL query
        if tables:
            return f"SELECT * FROM {tables[0]} LIMIT 10;"
        return "-- No tables selected"

    def apply_quality_filters(self, sql_query: str) -> bool:
        """
        Apply relevance, risk, and permission filters to the generated SQL query.
        This is a stub: always returns True (query is allowed).
        """
        return True
