# dbms_agent/nl2sql.py

"""
NL2SQL Agent: Table selection, SQL generation, and quality filters using the semantic model.
"""


from typing import List, Dict, Any
import re


KEYWORD_SPLIT_RE = re.compile(r"[^A-Za-z0-9_]+")

class NL2SQLAgent:
    def __init__(self, semantic_model_analyzer):
        self.semantic_model_analyzer = semantic_model_analyzer

    # ---- Intent Classification ----
    def classify_intent(self, question: str) -> str:
        """Classify user question intent.

        Returns:
          - 'metadata' for schema exploration (list tables/views, columns)
          - 'data' for data retrieval queries (default)

        Heuristics (cheap + deterministic):
          * Presence of keywords strongly indicating a catalog request.
          * Avoid treating questions with comparative / aggregate verbs as metadata.
        """
        q = question.lower()
        meta_keywords = [
            'what tables', 'list tables', 'show tables', 'tables exist', 'available tables',
            'what views', 'list views', 'show views', 'schema', 'database schema', 'list schema',
            'describe tables', 'table names'
        ]
        # If it explicitly asks for columns of a specific table we still treat as metadata
        if any(k in q for k in meta_keywords):
            return 'metadata'
        # generic single word queries
        if q.strip() in { 'tables', 'views', 'schema' }:
            return 'metadata'
        return 'data'

    def select_tables(self, question: str) -> List[str]:
        """Naive heuristic table selection.

        Current strategy (incremental improvement over pure stub):
          1. Fetch schema (tables with optional columns) from semantic_model_analyzer.
          2. Tokenize question into lowercase keywords (deduped, length >= 3).
          3. Score each table:
               +2 if table name token appears
               +1 per matching column token (cap at +5)
          4. Return tables with score > 0 sorted by score desc, fallback to top N.

        If no matches found, return up to 3 tables (to constrain LLM surface area).
        """
        schema: List[Dict[str, Any]] = self.semantic_model_analyzer.analyze_schema()
        if not schema:
            return []
        tokens = [t for t in {tok.lower() for tok in KEYWORD_SPLIT_RE.split(question) if len(tok) >= 3}]
        scores: Dict[str, int] = {}
        for table in schema:
            name = table.get('name') or table.get('table') or ''
            cols = table.get('columns') or []
            lname = name.lower()
            table_score = 0
            if lname in tokens:
                table_score += 2
            col_hits = 0
            for c in cols:
                lc = c.lower()
                if lc in tokens:
                    col_hits += 1
                    if col_hits >= 5:  # cap contribution
                        break
            table_score += col_hits
            if table_score > 0:
                scores[name] = table_score
        if scores:
            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            return [t for t, _ in ranked]
        # Fallback: first 3 tables to keep context minimal
        return [t.get('name') for t in schema[:3] if t.get('name')]

    def generate_sql(self, question: str, tables: List[str]) -> str:
        """
        Generate SQL query from natural language question and selected tables.
        This is a stub: in a real implementation, use an LLM or prompt template.
        """
        if not tables:
            return "-- No tables selected"

        table = tables[0]
        q_lower = question.lower()
        # Fetch full schema for column normalization
        schema = { (t.get('name') or '').lower(): t for t in self.semantic_model_analyzer.analyze_schema() }
        table_columns = []
        if table.lower() in schema:
            table_columns = schema[table.lower()].get('columns') or []
        # Build a case-insensitive lookup map for columns
        col_lookup = { c.lower(): c for c in table_columns }

        # Extract row limit patterns: "first 10", "top 5", "first ten" (basic digits only for now)
        limit = 10
        m_limit = re.search(r"\b(first|top)\s+(\d{1,4})\b", q_lower)
        if m_limit:
            try:
                limit = int(m_limit.group(2))
            except ValueError:
                pass

        # Extract simple ORDER BY pattern: "order(ed)? by <identifier list>"
        order_clause = ''
        m_order = re.search(r"order(?:ed)?\s+by\s+([A-Za-z0-9_.,\s]+)", q_lower)
        if m_order:
            raw_cols = m_order.group(1).strip()
            # Stop at words that likely start a new clause
            raw_cols = re.split(r"\b(limit|top|where|group by|having)\b", raw_cols)[0].strip()
            # Split columns by comma or whitespace sequence
            cols = [c.strip() for c in re.split(r",|\s+", raw_cols) if c.strip()]
            # Basic sanitization (alphanumeric + underscore + dot)
            safe_cols = []
            for c in cols:
                if not re.match(r"^[A-Za-z0-9_.]+$", c):
                    continue
                normalized = col_lookup.get(c.lower(), c)
                safe_cols.append(normalized)
            # If we failed to normalize (all lower) and we have remote describe_table available via semantic analyzer enrichment
            if safe_cols and table_columns and all(sc.lower() == sc for sc in safe_cols):
                # Retry by refreshing schema (maybe enrichment not done yet) — gentle attempt
                schema = { (t.get('name') or '').lower(): t for t in self.semantic_model_analyzer.analyze_schema() }
                if table.lower() in schema:
                    ref_cols = schema[table.lower()].get('columns') or []
                    ref_lookup = { c.lower(): c for c in ref_cols }
                    safe_cols = [ref_lookup.get(c.lower(), c) for c in safe_cols]
            if safe_cols:
                order_clause = " ORDER BY " + ", ".join(safe_cols)

        return f"SELECT TOP ({limit}) * FROM {table}{order_clause};"
        

    def apply_quality_filters(self, sql_query: str) -> bool:
        """
        Apply relevance, risk, and permission filters to the generated SQL query.
        This is a stub: always returns True (query is allowed).
        """
        return True
