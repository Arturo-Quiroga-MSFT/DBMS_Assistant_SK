#!/usr/bin/env python
"""Quick interactive example for the DBMSAgent.

Usage (ensure virtualenv + .env loaded or auto-load in package works):
  python run_example.py "What tables exist?"
  python run_example.py "Show the first 5 rows from dbo.Categories"

If no argument is supplied, defaults to a metadata question.
"""
from __future__ import annotations

import sys
from dbms_agent import DBMSAgent


def main():
    question = "What tables exist?" if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    agent = DBMSAgent()
    resp = agent.answer(question)
    print("Question:", question)
    print("Mode:", resp.get("mode"))
    print("Intent:", resp.get("intent"))
    print("Tables selected:", resp.get("tables"))
    print("SQL Generated:", resp.get("sql"))
    print("Executed:", resp.get("executed"))
    if resp.get("error"):
        print("Error:", resp.get("error"))
    print("--- Markdown Result ---")
    print(resp.get("markdown"))


if __name__ == "__main__":  # pragma: no cover
    main()
