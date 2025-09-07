# dbms_agent/__init__.py

"""Core modules for the DBMS agent solution.

Automatically loads a sibling `.env` file (if present) to simplify local
development. In production, prefer environment variables / secret stores.
"""

from pathlib import Path
from dotenv import load_dotenv  # type: ignore

# Attempt to load ../.env (one level above this package directory)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():  # pragma: no cover - convenience side effect
	load_dotenv(dotenv_path=_env_path, override=False)

from .orchestrator import DBMSAgent  # noqa: E402,F401  (import after dotenv load)

__all__ = ["DBMSAgent"]

