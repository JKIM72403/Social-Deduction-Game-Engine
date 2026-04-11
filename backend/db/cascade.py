"""
Explicit CASCADE delete handlers for MongoDB.

Django's ORM provides automatic cascading deletes via ``on_delete=CASCADE``.
MongoDB has no equivalent — when a session or participant document is removed,
related documents in other collections must be cleaned up explicitly.

These functions should be called in place of (or alongside) the Django ORM
``delete()`` calls once the repository layer is fully migrated to Mongo.
They are safe to call in relational mode too: the Mongo operations are
no-ops when ``USE_MONGODB=False`` because `get_db()` won't be connected.

Cascade graph
-------------
sessions
  └─ participants  (session_id FK → sessions._id)
  └─ actions       (session_id FK → sessions._id)

participants
  └─ actions       (participant_id FK → participants._id)

Usage
-----
Phase 3 will introduce a proper repository layer that calls these helpers
automatically.  Until then, call them directly from any view or management
command that deletes sessions or participants.
"""

from __future__ import annotations

from django.conf import settings


def delete_session(session_id: int) -> dict[str, int]:
    """Delete a session document and all of its participants and actions.

    Returns a dict of deleted counts per collection.
    """
    if not getattr(settings, "USE_MONGODB", False):
        return {}

    from db.mongo import get_db
    db = get_db()

    actions_result = db["actions"].delete_many({"session_id": session_id})
    participants_result = db["participants"].delete_many({"session_id": session_id})
    sessions_result = db["sessions"].delete_one({"_id": session_id})

    return {
        "sessions": sessions_result.deleted_count,
        "participants": participants_result.deleted_count,
        "actions": actions_result.deleted_count,
    }


def delete_participant(participant_id: int) -> dict[str, int]:
    """Delete a participant document and all of their actions.

    Returns a dict of deleted counts per collection.
    """
    if not getattr(settings, "USE_MONGODB", False):
        return {}

    from db.mongo import get_db
    db = get_db()

    actions_result = db["actions"].delete_many({"participant_id": participant_id})
    participants_result = db["participants"].delete_one({"_id": participant_id})

    return {
        "participants": participants_result.deleted_count,
        "actions": actions_result.deleted_count,
    }
