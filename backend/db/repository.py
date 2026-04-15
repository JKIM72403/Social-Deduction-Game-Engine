"""
Repository layer — abstract data access for relation/document modes.

This module provides a `Repository` abstract base class that defines all
data operations (reads, writes, deletes, constraint checks) for the three
core collections: sessions, participants, actions.

During the migration (Phases 3–4) both ``RelationalRepository`` (ORM)
and ``MongoRepository`` (pymongo) implement this interface.  Views use
the repository via ``get_repository()`` and never directly touch ORM or
Mongo driver code.

Once Phase 5+ is complete and the ORM is removed, only ``MongoRepository``
will remain — a drop-in replacement requiring zero view changes.

Philosophy
----------
* Repository methods return typed dicts (from ``db.documents``) consistently
  on both backends, eliminating view-level ORM-vs-Mongo branching logic.

* Atomic transactions are wrapped at the repository layer.  Views call
  ``transaction.atomic()`` normally; the repository detects ``USE_MONGODB``
  setting and uses either ``transaction.atomic()`` or synchronous writes
  (Mongo w:majority is synchronous by default).

* Repository methods are intentionally synchronous to match Django request
  handling.  Async wrappers will be added in Phase 5 if needed.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping

from django.conf import settings
from django.db import models
from django.utils import timezone

from .documents import (
    ActionDocument,
    ParticipantDocument,
    SessionDocument,
    action_from_orm,
    participant_from_orm,
    session_from_orm,
)

logger = logging.getLogger(__name__)



class Repository(ABC):
    """Abstract base class for data access on sessions, participants, actions."""

    # --- Session reads ---

    @abstractmethod
    def get_session_by_id(self, session_id: int) -> SessionDocument | None:
        """Fetch a single session by ID."""
        pass

    @abstractmethod
    def get_session_by_join_code(self, join_code: str) -> SessionDocument | None:
        """Fetch a single session by join code."""
        pass

    @abstractmethod
    def get_session_with_participants(
        self, session_id: int
    ) -> tuple[SessionDocument, list[ParticipantDocument]] | None:
        """Fetch a session and all of its participants in one operation.
        Returns None if session not found."""
        pass

    # --- Session writes ---

    @abstractmethod
    def create_session(
        self,
        template_id: int,
        host_user_id: int,
    ) -> SessionDocument:
        """Create and return a new session with a generated join_code."""
        pass

    @abstractmethod
    def update_session(self, session_id: int, **fields) -> SessionDocument | None:
        """Update specific fields on a session document. Returns updated doc or None."""
        pass

    # --- Participant reads ---

    @abstractmethod
    def get_participant_by_session_and_user(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        """Fetch a single participant by session + user."""
        pass

    @abstractmethod
    def get_participants_for_session(
        self, session_id: int, order_by: str = "seat_order"
    ) -> list[ParticipantDocument]:
        """Fetch all participants for a session."""
        pass

    @abstractmethod
    def get_participant_by_id(self, participant_id: int) -> ParticipantDocument | None:
        """Fetch a single participant by primary key."""
        pass

    @abstractmethod
    def get_participant_with_lock(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        """Fetch with an exclusive lock (select_for_update in SQL mode).
        Only valid inside a transaction.atomic() block."""
        pass

    # --- Participant writes ---

    @abstractmethod
    def create_participant(
        self,
        session_id: int,
        user_id: int,
        display_name: str,
        seat_order: int,
    ) -> ParticipantDocument:
        """Create and return a new participant."""
        pass

    @abstractmethod
    def bulk_update_participants(
        self,
        participant_ids: list[int],
        **fields,
    ) -> int:
        """Update multiple participants. Returns count updated."""
        pass

    @abstractmethod
    def update_participant(self, participant_id: int, **fields) -> ParticipantDocument | None:
        """Update specific fields on a participant document. Returns updated doc or None."""
        pass

    # --- Action writes ---

    @abstractmethod
    def create_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
        payload: dict[str, Any],
    ) -> ActionDocument:
        """Create and return a new action."""
        pass

    @abstractmethod
    def bulk_update_actions(self, action_ids: list[int], **fields) -> int:
        """Bulk-update multiple action documents. Returns count updated."""
        pass

    # --- Query helpers ---

    @abstractmethod
    def check_existing_vote(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
    ) -> ActionDocument | None:
        """Check if a participant already voted this turn. Returns the vote or None."""
        pass

    @abstractmethod
    def list_actions_for_vote_resolution(
        self, session_id: int, turn_number: int
    ) -> list[ActionDocument]:
        """Fetch all VOTE actions for a given session + turn. For vote resolution."""
        pass

    @abstractmethod
    def check_existing_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
    ) -> ActionDocument | None:
        """Check if a participant already submitted this action type for a phase."""
        pass

    @abstractmethod
    def list_submitted_actions_for_phase(
        self,
        session_id: int,
        turn_number: int,
        phase: str,
    ) -> list[ActionDocument]:
        """Fetch all submitted actions for a session turn and phase."""
        pass

    # --- Constraint checks ---

    @abstractmethod
    def check_unique_display_name(
        self, session_id: int, display_name: str, exclude_user_id: int | None = None
    ) -> bool:
        """Return True if display_name is available, False if already taken."""
        pass

    @abstractmethod
    def check_unique_seat_order(
        self, session_id: int, seat_order: int
    ) -> bool:
        """Return True if seat_order is available, False if taken."""
        pass

    # --- Deletes ---

    @abstractmethod
    def delete_session(self, session_id: int) -> dict[str, int]:
        """Delete a session and cascade to participants + actions.
        Returns {collection: count_deleted}."""
        pass

    @abstractmethod
    def delete_participant(self, participant_id: int) -> dict[str, int]:
        """Delete a participant and cascade to actions.
        Returns {collection: count_deleted}."""
        pass


# --- Relational implementation (Django ORM) ---


class RelationalRepository(Repository):
    """Repository backed by Django ORM.  Used in default/relational mode."""

    def get_session_by_id(self, session_id: int) -> SessionDocument | None:
        from games.models import GameSession

        session = (
            GameSession.objects.select_related("template", "host")
            .filter(id=session_id)
            .first()
        )
        return session_from_orm(session) if session else None

    def get_session_by_join_code(self, join_code: str) -> SessionDocument | None:
        from games.models import GameSession

        session = (
            GameSession.objects.select_related("template", "host")
            .filter(join_code=join_code.strip().upper())
            .first()
        )
        return session_from_orm(session) if session else None

    def get_session_with_participants(
        self, session_id: int
    ) -> tuple[SessionDocument, list[ParticipantDocument]] | None:
        from games.models import GameSession

        session = (
            GameSession.objects.select_related("template", "host")
            .prefetch_related("participants__user")
            .filter(id=session_id)
            .first()
        )
        if not session:
            return None

        participants = list(session.participants.select_related("user").order_by("seat_order", "joined_at"))
        return session_from_orm(session), [participant_from_orm(p) for p in participants]

    def create_session(self, template_id: int, host_user_id: int) -> SessionDocument:
        from games.models import GameSession, GameTemplate
        from django.contrib.auth import get_user_model

        template = GameTemplate.objects.get(id=template_id)
        host = get_user_model().objects.get(id=host_user_id)

        session = GameSession.objects.create(
            template=template,
            host=host,
        )
        return session_from_orm(session)

    def update_session(self, session_id: int, **fields) -> SessionDocument | None:
        from games.models import GameSession

        session = (
            GameSession.objects
            .select_related("template", "host")
            .filter(id=session_id)
            .first()
        )
        if not session:
            return None

        for key, value in fields.items():
            setattr(session, key, value)
        session.save()
        return session_from_orm(session)

    def get_participant_by_session_and_user(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        from games.models import GameParticipant

        participant = GameParticipant.objects.select_related("user").filter(
            session_id=session_id, user_id=user_id
        ).first()
        return participant_from_orm(participant) if participant else None

    def get_participants_for_session(
        self, session_id: int, order_by: str = "seat_order"
    ) -> list[ParticipantDocument]:
        from games.models import GameParticipant

        if order_by == "seat_order":
            participants = list(
                GameParticipant.objects.select_related("user")
                .filter(session_id=session_id)
                .order_by("seat_order", "joined_at")
            )
        else:
            participants = list(GameParticipant.objects.select_related("user").filter(session_id=session_id))

        return [participant_from_orm(p) for p in participants]

    def get_participant_by_id(self, participant_id: int) -> ParticipantDocument | None:
        from games.models import GameParticipant

        participant = GameParticipant.objects.select_related("user").filter(id=participant_id).first()
        return participant_from_orm(participant) if participant else None

    def get_participant_with_lock(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        from games.models import GameParticipant

        participant = (
            GameParticipant.objects.select_for_update()
            .select_related("user")
            .filter(session_id=session_id, user_id=user_id)
            .first()
        )
        return participant_from_orm(participant) if participant else None

    def create_participant(
        self,
        session_id: int,
        user_id: int,
        display_name: str,
        seat_order: int,
    ) -> ParticipantDocument:
        from games.models import GameParticipant, GameSession
        from django.contrib.auth import get_user_model

        session = GameSession.objects.get(id=session_id)
        user = get_user_model().objects.get(id=user_id)

        participant = GameParticipant.objects.create(
            session=session,
            user=user,
            display_name=display_name,
            seat_order=seat_order,
            is_connected=True,
        )
        return participant_from_orm(participant)

    def bulk_update_participants(
        self,
        participant_ids: list[int],
        **fields,
    ) -> int:
        from games.models import GameParticipant

        participants = list(GameParticipant.objects.filter(id__in=participant_ids))
        for participant in participants:
            for key, value in fields.items():
                setattr(participant, key, value)

        GameParticipant.objects.bulk_update(
            participants,
            list(fields.keys()),
        )
        return len(participants)

    def update_participant(self, participant_id: int, **fields) -> ParticipantDocument | None:
        from games.models import GameParticipant

        participant = GameParticipant.objects.select_related("user").filter(
            id=participant_id
        ).first()
        if not participant:
            return None

        for key, value in fields.items():
            setattr(participant, key, value)
        participant.save()
        return participant_from_orm(participant)

    def create_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
        payload: dict[str, Any],
    ) -> ActionDocument:
        from games.models import GameAction, GameSession, GameParticipant

        session = GameSession.objects.get(id=session_id)
        participant = GameParticipant.objects.get(id=participant_id)

        action = GameAction.objects.create(
            session=session,
            participant=participant,
            turn_number=turn_number,
            phase=phase,
            action_type=action_type,
            payload=payload,
        )
        return action_from_orm(action)

    def bulk_update_actions(self, action_ids: list[int], **fields) -> int:
        from games.models import GameAction

        if not action_ids:
            return 0
        actions = list(GameAction.objects.filter(id__in=action_ids))
        for action in actions:
            for k, v in fields.items():
                setattr(action, k, v)
        if actions:
            GameAction.objects.bulk_update(actions, list(fields.keys()))
        return len(actions)

    def check_existing_vote(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
    ) -> ActionDocument | None:
        from games.models import GameAction, GameSession

        action = GameAction.objects.filter(
            session_id=session_id,
            participant_id=participant_id,
            phase=GameSession.PHASE_VOTING,
            action_type="VOTE",
            status=GameAction.STATUS_SUBMITTED,
            turn_number=turn_number,
        ).first()
        return action_from_orm(action) if action else None

    def list_actions_for_vote_resolution(
        self, session_id: int, turn_number: int
    ) -> list[ActionDocument]:
        from games.models import GameAction, GameSession

        actions = list(
            GameAction.objects.filter(
                session_id=session_id,
                turn_number=turn_number,
                phase=GameSession.PHASE_VOTING,
                action_type="VOTE",
                status=GameAction.STATUS_SUBMITTED,
            )
        )
        return [action_from_orm(a) for a in actions]

    def check_existing_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
    ) -> ActionDocument | None:
        from games.models import GameAction

        action = GameAction.objects.filter(
            session_id=session_id,
            participant_id=participant_id,
            turn_number=turn_number,
            phase=phase,
            action_type=action_type,
            status=GameAction.STATUS_SUBMITTED,
        ).first()
        return action_from_orm(action) if action else None

    def list_submitted_actions_for_phase(
        self,
        session_id: int,
        turn_number: int,
        phase: str,
    ) -> list[ActionDocument]:
        from games.models import GameAction

        actions = list(
            GameAction.objects.filter(
                session_id=session_id,
                turn_number=turn_number,
                phase=phase,
                status=GameAction.STATUS_SUBMITTED,
            ).order_by("submitted_at", "id")
        )
        return [action_from_orm(a) for a in actions]

    def check_unique_display_name(
        self, session_id: int, display_name: str, exclude_user_id: int | None = None
    ) -> bool:
        from games.models import GameParticipant

        qs = GameParticipant.objects.filter(session_id=session_id, display_name=display_name)
        if exclude_user_id is not None:
            qs = qs.exclude(user_id=exclude_user_id)
        return not qs.exists()

    def check_unique_seat_order(self, session_id: int, seat_order: int) -> bool:
        from games.models import GameParticipant

        return not GameParticipant.objects.filter(
            session_id=session_id,
            seat_order=seat_order,
        ).exists()

    def delete_session(self, session_id: int) -> dict[str, int]:
        from games.models import GameSession, GameParticipant, GameAction

        session = GameSession.objects.get(id=session_id)
        actions_count, _ = GameAction.objects.filter(session=session).delete()
        participants_count, _ = GameParticipant.objects.filter(session=session).delete()
        session_count, _ = session.delete()

        return {
            "sessions": session_count,
            "participants": participants_count,
            "actions": actions_count,
        }

    def delete_participant(self, participant_id: int) -> dict[str, int]:
        from games.models import GameParticipant, GameAction

        participant = GameParticipant.objects.get(id=participant_id)
        actions_count, _ = GameAction.objects.filter(participant=participant).delete()
        participant_count, _ = participant.delete()

        return {
            "participants": participant_count,
            "actions": actions_count,
        }


# --- Factory ---


def get_repository() -> Repository:
    """Return the appropriate repository implementation based on settings.

    Priority:
      1. USE_MONGODB=True   → MongoRepository (pure Mongo mode)
      2. USE_DUAL_WRITE=True → DualWriteRepository (shadow-write for validation)
      3. Default             → RelationalRepository (ORM mode)
    """
    if getattr(settings, "USE_MONGODB", False):
        return MongoRepository()
    if getattr(settings, "USE_DUAL_WRITE", False):
        return DualWriteRepository()
    return RelationalRepository()


# --- Stub for MongoDB (Phase 4) ---


class MongoRepository(Repository):
    """Repository backed by MongoDB (pymongo driver).
    
    Implements all CRUD operations on the three runtime collections:
    sessions, participants, actions.  Uses replica-set transactions for
    multi-document atomicity when needed (e.g., vote submission).
    """

    def __init__(self):
        from .mongo import get_db
        self.db = get_db()

    def _next_id(self, collection_name: str) -> int:
        """Allocate the next integer _id for a Mongo collection.

        This preserves API compatibility with existing integer IDs used by
        URL routes and frontend payloads.
        """
        from pymongo import ReturnDocument
        from pymongo.errors import DuplicateKeyError

        counters = self.db["counters"]
        counter = counters.find_one({"_id": collection_name})

        if counter is None:
            max_doc = self.db[collection_name].find_one(
                projection={"_id": 1},
                sort=[("_id", -1)],
            )
            start = int(max_doc["_id"]) if max_doc and max_doc.get("_id") is not None else 0
            try:
                counters.insert_one({"_id": collection_name, "seq": start})
            except DuplicateKeyError:
                # Another request initialized the counter first.
                pass

        updated = counters.find_one_and_update(
            {"_id": collection_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if updated is None or updated.get("seq") is None:
            raise RuntimeError(f"Failed to allocate Mongo integer _id for '{collection_name}'.")
        return int(updated["seq"])

    def get_session_by_id(self, session_id: int) -> SessionDocument | None:
        doc = self.db["sessions"].find_one({"_id": session_id})
        return SessionDocument(**doc) if doc else None

    def get_session_by_join_code(self, join_code: str) -> SessionDocument | None:
        doc = self.db["sessions"].find_one({"join_code": join_code.strip().upper()})
        return SessionDocument(**doc) if doc else None

    def get_session_with_participants(
        self, session_id: int
    ) -> tuple[SessionDocument, list[ParticipantDocument]] | None:
        session_doc = self.db["sessions"].find_one({"_id": session_id})
        if not session_doc:
            return None

        participants = list(
            self.db["participants"]
            .find({"session_id": session_id})
            .sort([("seat_order", 1), ("joined_at", 1)])
        )
        return (
            SessionDocument(**session_doc),
            [ParticipantDocument(**p) for p in participants],
        )

    def create_session(self, template_id: int, host_user_id: int) -> SessionDocument:
        """Create a new session with a generated unique join_code."""
        from games.models import GameSession
        
        # Generate unique join code using Django logic
        code = GameSession.generate_join_code()
        for _ in range(20):
            if not self.db["sessions"].find_one({"join_code": code}):
                break
            code = GameSession.generate_join_code()
        else:
            raise RuntimeError("Unable to generate unique join code")

        from games.models import GameTemplate as _GT
        from django.contrib.auth import get_user_model as _gum
        _template_name = _GT.objects.values_list("name", flat=True).filter(id=template_id).first()
        if _template_name is None:
            raise ValueError(f"Template {template_id} does not exist.")
        _host_username = _gum().objects.values_list("username", flat=True).filter(id=host_user_id).first()

        now = timezone.now()
        session_id = self._next_id("sessions")
        session_dict = {
            "_id": session_id,
            "template_id": template_id,
            "template_name": _template_name,
            "host_user_id": host_user_id,
            "host_username": _host_username,
            "join_code": code,
            "status": GameSession.STATUS_LOBBY,
            "current_phase": GameSession.PHASE_WAITING,
            "turn_number": 0,
            "state_json": {},
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "ended_at": None,
        }
        self.db["sessions"].insert_one(session_dict)
        return SessionDocument(**session_dict)

    def update_session(self, session_id: int, **fields) -> SessionDocument | None:
        """Update specific fields on a session. Returns updated doc or None."""
        fields["updated_at"] = timezone.now()
        result = self.db["sessions"].find_one_and_update(
            {"_id": session_id},
            {"$set": fields},
            return_document=True,
        )
        return SessionDocument(**result) if result else None

    def get_participant_by_session_and_user(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        doc = self.db["participants"].find_one(
            {"session_id": session_id, "user_id": user_id}
        )
        return ParticipantDocument(**doc) if doc else None

    def get_participants_for_session(
        self, session_id: int, order_by: str = "seat_order"
    ) -> list[ParticipantDocument]:
        if order_by == "seat_order":
            cursor = self.db["participants"].find({"session_id": session_id}).sort(
                [("seat_order", 1), ("joined_at", 1)]
            )
        else:
            cursor = self.db["participants"].find({"session_id": session_id})

        return [ParticipantDocument(**doc) for doc in cursor]

    def get_participant_by_id(self, participant_id: int) -> ParticipantDocument | None:
        doc = self.db["participants"].find_one({"_id": participant_id})
        return ParticipantDocument(**doc) if doc else None

    def get_participant_with_lock(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        """Best-effort participant fetch for parity with SQL repository.

        MongoDB does not expose a row-level lock primitive analogous to
        ``select_for_update``. Duplicate vote protection in Mongo mode relies on
        unique indexes + duplicate-key handling in ``create_action``.
        """
        doc = self.db["participants"].find_one(
            {"session_id": session_id, "user_id": user_id}
        )
        return ParticipantDocument(**doc) if doc else None

    def create_participant(
        self,
        session_id: int,
        user_id: int,
        display_name: str,
        seat_order: int,
    ) -> ParticipantDocument:
        from django.contrib.auth import get_user_model as _gum
        _username = _gum().objects.values_list("username", flat=True).filter(id=user_id).first()
        if _username is None:
            raise ValueError(f"User {user_id} does not exist.")

        now = timezone.now()
        participant_id = self._next_id("participants")
        participant_dict = {
            "_id": participant_id,
            "session_id": session_id,
            "user_id": user_id,
            "username": _username,
            "display_name": display_name,
            "seat_order": seat_order,
            "is_ready": False,
            "is_connected": True,
            "is_alive": True,
            "role_name": "",
            "role_alignment": "",
            "joined_at": now,
            "last_seen_at": now,
            "eliminated_at": None,
        }
        self.db["participants"].insert_one(participant_dict)
        return ParticipantDocument(**participant_dict)

    def bulk_update_participants(
        self,
        participant_ids: list[int],
        **fields,
    ) -> int:
        """Update multiple participants. Returns count updated."""
        fields["last_seen_at"] = timezone.now()
        result = self.db["participants"].update_many(
            {"_id": {"$in": participant_ids}},
            {"$set": fields},
        )
        return result.modified_count

    def update_participant(self, participant_id: int, **fields) -> ParticipantDocument | None:
        """Update specific fields on a participant. Returns updated doc or None."""
        fields["last_seen_at"] = timezone.now()
        result = self.db["participants"].find_one_and_update(
            {"_id": participant_id},
            {"$set": fields},
            return_document=True,
        )
        return ParticipantDocument(**result) if result else None

    def create_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
        payload: dict[str, Any],
    ) -> ActionDocument:
        now = timezone.now()
        from pymongo.errors import DuplicateKeyError
        from games.models import GameAction as _GA  # noqa: PLC0415 — constant only
        action_id = self._next_id("actions")
        action_dict = {
            "_id": action_id,
            "session_id": session_id,
            "participant_id": participant_id,
            "turn_number": turn_number,
            "phase": phase,
            "action_type": action_type,
            "payload": payload or {},
            "status": _GA.STATUS_SUBMITTED,
            "submitted_at": now,
            "resolved_at": None,
        }
        try:
            self.db["actions"].insert_one(action_dict)
        except DuplicateKeyError as exc:
            raise ValueError("You have already locked in your vote for this round") from exc
        return ActionDocument(**action_dict)

    def bulk_update_actions(self, action_ids: list[int], **fields) -> int:
        if not action_ids:
            return 0
        result = self.db["actions"].update_many(
            {"_id": {"$in": action_ids}},
            {"$set": fields},
        )
        return result.modified_count

    def check_existing_vote(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
    ) -> ActionDocument | None:
        from games.models import GameAction, GameSession
        
        doc = self.db["actions"].find_one(
            {
                "session_id": session_id,
                "participant_id": participant_id,
                "turn_number": turn_number,
                "phase": GameSession.PHASE_VOTING,
                "action_type": "VOTE",
                "status": GameAction.STATUS_SUBMITTED,
            }
        )
        return ActionDocument(**doc) if doc else None

    def list_actions_for_vote_resolution(
        self, session_id: int, turn_number: int
    ) -> list[ActionDocument]:
        from games.models import GameAction, GameSession
        
        cursor = self.db["actions"].find(
            {
                "session_id": session_id,
                "turn_number": turn_number,
                "phase": GameSession.PHASE_VOTING,
                "action_type": "VOTE",
                "status": GameAction.STATUS_SUBMITTED,
            }
        )
        return [ActionDocument(**doc) for doc in cursor]

    def check_existing_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
    ) -> ActionDocument | None:
        from games.models import GameAction

        doc = self.db["actions"].find_one(
            {
                "session_id": session_id,
                "participant_id": participant_id,
                "turn_number": turn_number,
                "phase": phase,
                "action_type": action_type,
                "status": GameAction.STATUS_SUBMITTED,
            }
        )
        return ActionDocument(**doc) if doc else None

    def list_submitted_actions_for_phase(
        self,
        session_id: int,
        turn_number: int,
        phase: str,
    ) -> list[ActionDocument]:
        from games.models import GameAction

        cursor = (
            self.db["actions"]
            .find(
                {
                    "session_id": session_id,
                    "turn_number": turn_number,
                    "phase": phase,
                    "status": GameAction.STATUS_SUBMITTED,
                }
            )
            .sort([("submitted_at", 1), ("_id", 1)])
        )
        return [ActionDocument(**doc) for doc in cursor]

    def check_unique_display_name(
        self, session_id: int, display_name: str, exclude_user_id: int | None = None
    ) -> bool:
        """Return True if display_name is available, False if taken."""
        query = {"session_id": session_id, "display_name": display_name}
        if exclude_user_id is not None:
            query["user_id"] = {"$ne": exclude_user_id}
        return not self.db["participants"].find_one(query)

    def check_unique_seat_order(self, session_id: int, seat_order: int) -> bool:
        """Return True if seat_order is available, False if taken."""
        return not self.db["participants"].find_one(
            {"session_id": session_id, "seat_order": seat_order}
        )

    def delete_session(self, session_id: int) -> dict[str, int]:
        """Delete a session and cascade to participants + actions."""
        actions_result = self.db["actions"].delete_many({"session_id": session_id})
        participants_result = self.db["participants"].delete_many(
            {"session_id": session_id}
        )
        sessions_result = self.db["sessions"].delete_one({"_id": session_id})

        return {
            "sessions": sessions_result.deleted_count,
            "participants": participants_result.deleted_count,
            "actions": actions_result.deleted_count,
        }

    def delete_participant(self, participant_id: int) -> dict[str, int]:
        """Delete a participant and cascade to actions."""
        actions_result = self.db["actions"].delete_many(
            {"participant_id": participant_id}
        )
        participants_result = self.db["participants"].delete_one(
            {"_id": participant_id}
        )

        return {
            "participants": participants_result.deleted_count,
            "actions": actions_result.deleted_count,
        }

    # --- Mirror helpers for dual-write ---

    def mirror_document(self, collection: str, doc: Mapping[str, Any]) -> None:
        """Upsert a document into a collection by its _id.
        Used by DualWriteRepository to keep Mongo in sync with the ORM primary."""
        self.db[collection].replace_one({"_id": doc["_id"]}, dict(doc), upsert=True)


# --- Dual-write implementation ---


class DualWriteRepository(Repository):
    """Shadow-write repository: ORM is primary, MongoDB is shadow.

    All reads come from the relational primary.  Writes are sent to both
    backends simultaneously: ORM first (the result is authoritative), then
    MongoDB is updated with the exact document returned by the ORM write.
    MongoDB write failures are caught, logged, and **never** propagate — the
    relational write always succeeds regardless of Mongo availability.

    This mode is controlled by ``USE_DUAL_WRITE=True`` in settings.  It is
    designed to run during Phase 6 of the migration to validate that MongoDB
    stays consistent with the ORM before the full cutover (Phase 7).
    """

    def __init__(self):
        self._primary = RelationalRepository()
        self._mongo: MongoRepository | None = None

    def _get_mongo(self) -> MongoRepository:
        """Lazy-initialize the Mongo shadow. First access triggers the connection."""
        if self._mongo is None:
            self._mongo = MongoRepository()
        return self._mongo

    def _try_mirror(self, collection: str, doc: Mapping[str, Any]) -> None:
        """Mirror a document to MongoDB by upserting with the exact primary doc."""
        try:
            self._get_mongo().mirror_document(collection, dict(doc))
        except Exception as exc:
            logger.warning(
                "DualWrite: mirror to '%s' failed: %s",
                collection,
                exc,
                exc_info=True,
            )

    # --- Session reads — always from primary ---

    def get_session_by_id(self, session_id: int) -> SessionDocument | None:
        return self._primary.get_session_by_id(session_id)

    def get_session_by_join_code(self, join_code: str) -> SessionDocument | None:
        return self._primary.get_session_by_join_code(join_code)

    def get_session_with_participants(
        self, session_id: int
    ) -> tuple[SessionDocument, list[ParticipantDocument]] | None:
        return self._primary.get_session_with_participants(session_id)

    # --- Session writes — primary first, then mirror to Mongo ---

    def create_session(self, template_id: int, host_user_id: int) -> SessionDocument:
        result = self._primary.create_session(template_id, host_user_id)
        self._try_mirror("sessions", result)
        return result

    def update_session(self, session_id: int, **fields) -> SessionDocument | None:
        result = self._primary.update_session(session_id, **fields)
        if result is not None:
            self._try_mirror("sessions", result)
        return result

    # --- Participant reads — always from primary ---

    def get_participant_by_session_and_user(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        return self._primary.get_participant_by_session_and_user(session_id, user_id)

    def get_participants_for_session(
        self, session_id: int, order_by: str = "seat_order"
    ) -> list[ParticipantDocument]:
        return self._primary.get_participants_for_session(session_id, order_by)

    def get_participant_by_id(self, participant_id: int) -> ParticipantDocument | None:
        return self._primary.get_participant_by_id(participant_id)

    def get_participant_with_lock(
        self, session_id: int, user_id: int
    ) -> ParticipantDocument | None:
        return self._primary.get_participant_with_lock(session_id, user_id)

    # --- Participant writes --- primary first, then mirror ---

    def create_participant(
        self,
        session_id: int,
        user_id: int,
        display_name: str,
        seat_order: int,
    ) -> ParticipantDocument:
        result = self._primary.create_participant(session_id, user_id, display_name, seat_order)
        self._try_mirror("participants", result)
        return result

    def bulk_update_participants(self, participant_ids: list[int], **fields) -> int:
        count = self._primary.bulk_update_participants(participant_ids, **fields)
        # Re-fetch updated docs and mirror each one
        try:
            for pid in participant_ids:
                doc = self._primary.get_participant_by_id(pid)
                if doc is not None:
                    self._try_mirror("participants", doc)
        except Exception as exc:
            logger.warning("DualWrite: bulk mirror participants failed: %s", exc, exc_info=True)
        return count

    def update_participant(self, participant_id: int, **fields) -> ParticipantDocument | None:
        result = self._primary.update_participant(participant_id, **fields)
        if result is not None:
            self._try_mirror("participants", result)
        return result

    # --- Action writes ---

    def create_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
        payload: dict[str, Any],
    ) -> ActionDocument:
        result = self._primary.create_action(
            session_id, participant_id, turn_number, phase, action_type, payload
        )
        self._try_mirror("actions", result)
        return result

    def bulk_update_actions(self, action_ids: list[int], **fields) -> int:
        count = self._primary.bulk_update_actions(action_ids, **fields)
        try:
            self._get_mongo().bulk_update_actions(action_ids, **fields)
        except Exception as exc:
            logger.warning(
                "DualWrite: shadow bulk_update_actions failed: %s", exc, exc_info=True
            )
        return count

    # --- Query helpers — always from primary ---

    def check_existing_vote(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
    ) -> ActionDocument | None:
        return self._primary.check_existing_vote(session_id, participant_id, turn_number)

    def list_actions_for_vote_resolution(
        self, session_id: int, turn_number: int
    ) -> list[ActionDocument]:
        return self._primary.list_actions_for_vote_resolution(session_id, turn_number)

    def check_existing_action(
        self,
        session_id: int,
        participant_id: int,
        turn_number: int,
        phase: str,
        action_type: str,
    ) -> ActionDocument | None:
        return self._primary.check_existing_action(
            session_id, participant_id, turn_number, phase, action_type
        )

    def list_submitted_actions_for_phase(
        self,
        session_id: int,
        turn_number: int,
        phase: str,
    ) -> list[ActionDocument]:
        return self._primary.list_submitted_actions_for_phase(
            session_id, turn_number, phase
        )

    # --- Constraint checks — always from primary ---

    def check_unique_display_name(
        self, session_id: int, display_name: str, exclude_user_id: int | None = None
    ) -> bool:
        return self._primary.check_unique_display_name(session_id, display_name, exclude_user_id)

    def check_unique_seat_order(self, session_id: int, seat_order: int) -> bool:
        return self._primary.check_unique_seat_order(session_id, seat_order)

    # --- Deletes --- primary first, then mirror deletions to Mongo ---

    def delete_session(self, session_id: int) -> dict[str, int]:
        result = self._primary.delete_session(session_id)
        try:
            self._get_mongo().delete_session(session_id)
        except Exception as exc:
            logger.warning("DualWrite: shadow delete_session failed: %s", exc, exc_info=True)
        return result

    def delete_participant(self, participant_id: int) -> dict[str, int]:
        result = self._primary.delete_participant(participant_id)
        try:
            self._get_mongo().delete_participant(participant_id)
        except Exception as exc:
            logger.warning("DualWrite: shadow delete_participant failed: %s", exc, exc_info=True)
        return result

