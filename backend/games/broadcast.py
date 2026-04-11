"""
WebSocket broadcast helpers.

``post_write_broadcast`` abstracts the ``transaction.on_commit`` pattern used
throughout views.py.  The problem with ``on_commit`` in a MongoDB world is
that MongoDB writes are not wrapped in a Django-managed SQL transaction, so
``on_commit`` callbacks never fire once the ORM is removed.

Strategy
--------
* While ``USE_MONGODB=False`` (default / relational mode):
  wraps the broadcast in ``transaction.on_commit`` so it fires only after the
  SQL commit, preventing stale reads by WebSocket clients.

* While ``USE_MONGODB=True`` (migration / Mongo mode):
  calls the broadcast immediately after the write returns.  MongoDB Atlas
  replica-set writes with the default ``w:majority`` concern are durable by
  the time the driver call returns, so the broadcast timing is safe.

Usage
-----
Replace every::

    transaction.on_commit(
        lambda session_id=session.id: broadcast_session_event(session_id, reason)
    )

with::

    post_write_broadcast(session.id, reason)

The call must be made AFTER the ``with transaction.atomic()`` block exits
(or directly in non-atomic view code), exactly where ``on_commit`` lambdas
currently live.
"""

from django.conf import settings
from django.db import transaction

from .session_state import broadcast_session_event


def post_write_broadcast(session_id: int, reason: str) -> None:
    """Fire a session broadcast after the current write has been committed.

    In relational mode the broadcast is deferred via ``transaction.on_commit``
    so clients never read uncommitted data.  In MongoDB mode the broadcast is
    immediate because there is no enclosing SQL transaction.
    """
    if getattr(settings, "USE_MONGODB", False):
        broadcast_session_event(session_id, reason)
    else:
        transaction.on_commit(
            lambda: broadcast_session_event(session_id, reason)
        )
