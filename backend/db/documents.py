"""
MongoDB document schemas for the three runtime collections.

ID Strategy
-----------
During the dual-write migration phase (Phases 2–4) every Mongo document uses
the Django ORM integer primary key as its ``_id``.  This keeps the frontend
contract unchanged (all IDs remain integers) and lets us query either store
with the same identifier.

Once the Django ORM is fully removed (Phase 5+) these will be migrated to
BSON ObjectId, but that change is isolated to this module and the repository
layer — no view or serializer code will need updating.

Document Boundaries
-------------------
``sessions``    — One document per GameSession.  ``state_json`` is stored as
                  an embedded sub-document.  Template/user data is referenced
                  by integer FK; joined on read from the relational store (or
                  later from a ``game_templates`` Mongo collection).

``participants`` — Separate collection (not embedded in the session document)
                  because participants are updated independently and frequently
                  (is_alive changes, vote tracking, WebSocket presence).
                  Compound unique indexes on (session_id, user_id),
                  (session_id, display_name), and (session_id, seat_order)
                  enforce the same constraints as the SQL UniqueConstraints.

``actions``     — Separate collection.  Written once per vote; bulk-read only
                  during vote resolution.  High write volume makes them
                  unsuitable for embedding.

Constraint Map (SQL → Mongo)
-----------------------------
SQL UniqueConstraint                       Mongo unique index
-----------------------------------------  ----------------------------------------
unique_session_participant_user            {session_id:1, user_id:1} unique
unique_session_participant_display_name    {session_id:1, display_name:1} unique
unique_session_participant_seat_order      {session_id:1, seat_order:1} unique

SQL CASCADE (on_delete)                    Explicit handler
-----------------------------------------  ----------------------------------------
GameParticipant → GameSession (CASCADE)    cascade.delete_session()
GameAction → GameSession (CASCADE)         cascade.delete_session()
GameAction → GameParticipant (CASCADE)     cascade.delete_participant()
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------

class SessionDocument(TypedDict):
    """Shape of a document in the ``sessions`` collection."""
    _id: int                    # = GameSession.id  (Django PK)
    template_id: int
    template_name: str          # denormalised — set at create-time, never changes
    host_user_id: int | None
    host_username: str | None   # denormalised — set at create-time
    join_code: str
    status: str                 # LOBBY | IN_PROGRESS | COMPLETED | CANCELLED
    current_phase: str
    turn_number: int
    state_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


def session_from_orm(session) -> SessionDocument:
    """Build a ``SessionDocument`` from a Django ``GameSession`` ORM instance.

    The caller must have loaded ``template`` and ``host`` via
    ``select_related('template', 'host')`` (or equivalent) before calling
    this function — both ``template.name`` and ``host.username`` are read.
    """
    return SessionDocument(
        _id=session.id,
        template_id=session.template_id,
        template_name=session.template.name,
        host_user_id=session.host_id,
        host_username=session.host.username if session.host else None,
        join_code=session.join_code,
        status=session.status,
        current_phase=session.current_phase,
        turn_number=session.turn_number,
        state_json=session.state_json or {},
        created_at=session.created_at,
        updated_at=session.updated_at,
        started_at=session.started_at,
        ended_at=session.ended_at,
    )


# ---------------------------------------------------------------------------
# participants
# ---------------------------------------------------------------------------

class ParticipantDocument(TypedDict):
    """Shape of a document in the ``participants`` collection."""
    _id: int                    # = GameParticipant.id  (Django PK)
    session_id: int
    user_id: int
    username: str               # denormalised — set at create-time
    display_name: str
    seat_order: int
    is_ready: bool
    is_connected: bool
    is_alive: bool
    role_name: str
    role_alignment: str         # TOWN | MAFIA | NEUTRAL | ""
    joined_at: datetime
    last_seen_at: datetime
    eliminated_at: datetime | None


def participant_from_orm(participant) -> ParticipantDocument:
    """Build a ``ParticipantDocument`` from a Django ``GameParticipant`` ORM instance.

    The caller must have loaded ``user`` via ``select_related('user')`` before
    calling this function — ``user.username`` is read directly.
    """
    return ParticipantDocument(
        _id=participant.id,
        session_id=participant.session_id,
        user_id=participant.user_id,
        username=participant.user.username,
        display_name=participant.display_name,
        seat_order=participant.seat_order,
        is_ready=participant.is_ready,
        is_connected=participant.is_connected,
        is_alive=participant.is_alive,
        role_name=participant.role_name,
        role_alignment=participant.role_alignment,
        joined_at=participant.joined_at,
        last_seen_at=participant.last_seen_at,
        eliminated_at=participant.eliminated_at,
    )


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

class ActionDocument(TypedDict):
    """Shape of a document in the ``actions`` collection."""
    _id: int                    # = GameAction.id  (Django PK)
    session_id: int
    participant_id: int
    turn_number: int
    phase: str
    action_type: str
    payload: dict[str, Any]
    status: str                 # SUBMITTED | APPLIED | REJECTED
    submitted_at: datetime
    resolved_at: datetime | None


def action_from_orm(action) -> ActionDocument:
    """Build an ``ActionDocument`` from a Django ``GameAction`` ORM instance."""
    return ActionDocument(
        _id=action.id,
        session_id=action.session_id,
        participant_id=action.participant_id,
        turn_number=action.turn_number,
        phase=action.phase,
        action_type=action.action_type,
        payload=action.payload or {},
        status=action.status,
        submitted_at=action.submitted_at,
        resolved_at=action.resolved_at,
    )
