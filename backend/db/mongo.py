"""
Thread-safe MongoDB client singleton.

Usage:
    from db.mongo import get_db

    db = get_db()
    doc = db["sessions"].find_one({"join_code": "ABC123"})

The client is created once per process, on first call.  It reads connection
parameters from Django settings so that tests, management commands, and the
application all see a consistent configuration.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from pymongo import MongoClient
    from pymongo.database import Database

_lock = threading.Lock()
_client: "MongoClient | None" = None


def get_client() -> "MongoClient":
    """Return the shared MongoClient, creating it on first call."""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                from pymongo import MongoClient as _MongoClient

                uri = getattr(settings, "MONGODB_URI", None)
                if not uri:
                    raise RuntimeError(
                        "MONGODB_URI is not configured. "
                        "Set it in backend/.env or as an environment variable."
                    )
                if "<db_username>" in uri or "<db_password>" in uri:
                    raise RuntimeError(
                        "MONGODB_URI still contains placeholder credentials. "
                        "Replace <db_username> and <db_password> in backend/.env."
                    )
                _client = _MongoClient(
                    uri,
                    serverSelectionTimeoutMS=8_000,
                    # Keep alive / pool — sensible defaults for a web app.
                    maxPoolSize=50,
                    minPoolSize=5,
                )
    return _client


def get_db() -> "Database":
    """Return the application database from the shared client."""
    db_name = getattr(settings, "MONGODB_DB_NAME", "socialdeduction")
    return get_client()[db_name]


def close_client() -> None:
    """Close the client and reset the singleton (useful in tests)."""
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None
