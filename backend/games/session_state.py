from __future__ import annotations

from typing import Any, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def load_session_snapshot(session_id: int, viewer_user_id: Optional[int] = None) -> dict:
    """Load a full session snapshot using the repository — no direct ORM."""
    from db.repository import get_repository

    repo = get_repository()
    result = repo.get_session_with_participants(session_id)
    if result is None:
        raise ValueError(f"Session {session_id} not found")
    session_doc, participant_docs = result

    viewer_vote_payload: Optional[dict[str, Any]] = None
    if viewer_user_id is not None and session_doc["current_phase"] == "VOTING":
        viewer_participant = next(
            (p for p in participant_docs if p["user_id"] == viewer_user_id), None
        )
        if viewer_participant is not None:
            vote_action = repo.check_existing_vote(
                session_id, viewer_participant["_id"], session_doc["turn_number"]
            )
            viewer_vote_payload = vote_action["payload"] if vote_action else None

    return _build_snapshot_from_docs(
        session_doc, participant_docs, viewer_user_id, viewer_vote_payload
    )


def _build_snapshot_from_docs(
    session_doc: dict,
    participant_docs: list,
    viewer_user_id: Optional[int] = None,
    viewer_vote_payload: Optional[dict[str, Any]] = None,
) -> dict:
    """Build a session snapshot dict entirely from repository documents."""
    ready_count = sum(1 for p in participant_docs if p["is_ready"])
    participant_count = len(participant_docs)

    viewer_participant = (
        next((p for p in participant_docs if p["user_id"] == viewer_user_id), None)
        if viewer_user_id is not None
        else None
    )

    return {
        "session": {
            "id": session_doc["_id"],
            "join_code": session_doc["join_code"],
            "status": session_doc["status"],
            "current_phase": session_doc["current_phase"],
            "turn_number": session_doc["turn_number"],
            "template_id": session_doc["template_id"],
            "template_name": session_doc["template_name"],
            "host_user_id": session_doc["host_user_id"],
            "host_username": session_doc["host_username"],
            "participant_count": participant_count,
            "ready_count": ready_count,
            "all_ready": participant_count > 0 and ready_count == participant_count,
            "created_at": session_doc["created_at"].isoformat(),
            "updated_at": session_doc["updated_at"].isoformat(),
            "started_at": session_doc["started_at"].isoformat() if session_doc["started_at"] else None,
            "ended_at": session_doc["ended_at"].isoformat() if session_doc["ended_at"] else None,
        },
        "participants": [
            {
                "id": p["_id"],
                "user_id": p["user_id"],
                "username": p["username"],
                "display_name": p["display_name"],
                "seat_order": p["seat_order"],
                "is_ready": p["is_ready"],
                "is_connected": p["is_connected"],
                "is_alive": p["is_alive"],
                "role_name": p["role_name"] if _can_view_role(session_doc, p, viewer_user_id) else "",
                "role_alignment": p["role_alignment"] if _can_view_role(session_doc, p, viewer_user_id) else "",
                "joined_at": p["joined_at"].isoformat(),
                "last_seen_at": p["last_seen_at"].isoformat(),
                "eliminated_at": p["eliminated_at"].isoformat() if p.get("eliminated_at") else None,
            }
            for p in participant_docs
        ],
        "me": _build_viewer_state(session_doc, viewer_participant, viewer_vote_payload, participant_docs),
        "state": session_doc["state_json"],
    }


def broadcast_session_event(session_id: int, reason: str):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"session_{session_id}",
        {
            "type": "session.event",
            "reason": reason,
        },
    )


def _can_view_role(session_doc: dict, participant_doc: dict, viewer_user_id: Optional[int]) -> bool:
    if not participant_doc["role_name"]:
        return False

    if viewer_user_id == participant_doc["user_id"]:
        return True

    if not participant_doc["is_alive"]:
        return True

    if session_doc["status"] in {"COMPLETED", "CANCELLED"}:
        return True

    return False


def _build_viewer_state(
    session_doc: dict,
    viewer_participant: Optional[dict],
    viewer_vote_payload: Optional[dict[str, Any]],
    participant_docs: list,
) -> Optional[dict]:
    if viewer_participant is None:
        return None

    has_submitted_vote = False
    current_vote_target_id = None
    if viewer_vote_payload:
        current_vote_target_id = viewer_vote_payload.get("target_participant_id")
        has_submitted_vote = current_vote_target_id is not None

    available_vote_target_ids: list[int] = []
    if (
        session_doc["status"] == "IN_PROGRESS"
        and session_doc["current_phase"] == "VOTING"
        and viewer_participant["is_alive"]
    ):
        available_vote_target_ids = [p["_id"] for p in participant_docs if p["is_alive"]]

    return {
        "participant_id": viewer_participant["_id"],
        "display_name": viewer_participant["display_name"],
        "is_alive": viewer_participant["is_alive"],
        "role_name": viewer_participant["role_name"],
        "role_alignment": viewer_participant["role_alignment"],
        "has_submitted_vote": has_submitted_vote,
        "current_vote_target_id": current_vote_target_id,
        "available_vote_target_ids": available_vote_target_ids,
    }
