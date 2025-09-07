import os
import sys
import pathlib
import pytest

# Ensure project root (parent of dbms_agent_python) is on sys.path when running from tests dir
_here = pathlib.Path(__file__).resolve()
project_root = _here.parents[2]
if str(project_root) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(project_root))

from dbms_agent import DBMSAgent

def test_agent_smoke():
    question = "List all tables"
    agent = DBMSAgent()
    resp = agent.answer(question)
    print("Response:", resp)
    # Ensure we always get a structured response with markdown text
    assert "markdown" in resp
    assert isinstance(resp["markdown"], str)
    # If schema unavailable, executed may be False; that's acceptable
    if resp["executed"]:
        assert resp["mode"] in ("remote", "local")
    else:
        # Expect a clear message explaining why not executed
        assert "No tables selected" in resp["markdown"] or resp.get("error")
