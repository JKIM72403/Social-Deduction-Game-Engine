from __future__ import annotations

from copy import deepcopy
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

    viewer_actions: list[dict[str, Any]] = []
    if viewer_user_id is not None and session_doc["current_phase"] == "VOTING":
        viewer_participant = next(
            (p for p in participant_docs if p["user_id"] == viewer_user_id), None
        )
        if viewer_participant is not None:
            viewer_actions = [
                action
                for action in repo.list_submitted_actions_for_phase(
                    session_id,
                    session_doc["turn_number"],
                    session_doc["current_phase"],
                )
                if action["participant_id"] == viewer_participant["_id"]
            ]
    elif viewer_user_id is not None and session_doc["status"] == "IN_PROGRESS":
        viewer_participant = next(
            (p for p in participant_docs if p["user_id"] == viewer_user_id), None
        )
        if viewer_participant is not None:
            viewer_actions = [
                action
                for action in repo.list_submitted_actions_for_phase(
                    session_id,
                    session_doc["turn_number"],
                    session_doc["current_phase"],
                )
                if action["participant_id"] == viewer_participant["_id"]
            ]

    phase_actions = []
    if session_doc["status"] == "IN_PROGRESS":
        phase_actions = repo.list_submitted_actions_for_phase(
            session_id,
            session_doc["turn_number"],
            session_doc["current_phase"],
        )

    return _build_snapshot_from_docs(
        session_doc, participant_docs, viewer_user_id, viewer_actions, phase_actions
    )


def _visible_runtime_state(
    session_doc: dict,
    participant_docs: list,
    viewer_user_id: Optional[int],
) -> dict:
    state = deepcopy(session_doc["state_json"] or {})
    participant_by_id = {p["_id"]: p for p in participant_docs}

    visible_logs = []
    for event in state.get("logs") or []:
        visible_to = event.get("visible_to", "all")
        if visible_to == "all":
            visible_logs.append(event)
            continue

        if viewer_user_id is None:
            continue

        viewer_participant = next(
            (p for p in participant_docs if p["user_id"] == viewer_user_id), None
        )
        if viewer_participant and viewer_participant["display_name"] in visible_to:
            visible_logs.append(event)

    state["logs"] = visible_logs
    state["events"] = [
        f"[Turn {event.get('turn', 0)}] {event.get('message', '')}"
        for event in visible_logs
        if event.get("visible_to", "all") == "all"
    ]
    state["players"] = [
        {
            "participant_id": player["participant_id"],
            "display_name": player["display_name"],
            "is_alive": player["is_alive"],
            "role_name": player.get("role_name", "")
            if _can_view_role(
                session_doc,
                participant_by_id.get(player["participant_id"], {}),
                viewer_user_id,
            )
            else "",
            "role_alignment": player.get("role_alignment", "")
            if _can_view_role(
                session_doc,
                participant_by_id.get(player["participant_id"], {}),
                viewer_user_id,
            )
            else "",
        }
        for player in state.get("players", [])
    ]
    return state


def _build_snapshot_from_docs(
    session_doc: dict,
    participant_docs: list,
    viewer_user_id: Optional[int] = None,
    viewer_actions: Optional[list[dict[str, Any]]] = None,
    phase_actions: Optional[list[dict[str, Any]]] = None,
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
        "me": _build_viewer_state(
            session_doc,
            viewer_participant,
            viewer_actions or [],
            phase_actions or [],
            participant_docs,
        ),
        "state": _visible_runtime_state(session_doc, participant_docs, viewer_user_id),
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
    if not participant_doc:
        return False

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
    viewer_actions: list[dict[str, Any]],
    phase_actions: list[dict[str, Any]],
    participant_docs: list,
) -> Optional[dict]:
    if viewer_participant is None:
        return None

    has_submitted_vote = False
    current_vote_target_id = None
    has_submitted_action = False
    has_submitted_ability = False
    current_ability_target_id = None
    for action in viewer_actions:
        payload = action.get("payload") or {}
        if action["action_type"] == "VOTE":
            current_vote_target_id = payload.get("target_participant_id")
            has_submitted_vote = current_vote_target_id is not None
        if action["action_type"] in {"USE_ABILITY", "SKIP"}:
            has_submitted_action = True
        if action["action_type"] == "USE_ABILITY":
            has_submitted_ability = True
            current_ability_target_id = payload.get("target_participant_id")

    available_vote_target_ids: list[int] = []
    available_ability_target_ids: list[int] = []
    if (
        session_doc["status"] == "IN_PROGRESS"
        and session_doc["current_phase"] == "VOTING"
        and viewer_participant["is_alive"]
    ):
        available_vote_target_ids = [p["_id"] for p in participant_docs if p["is_alive"]]
    if session_doc["status"] == "IN_PROGRESS" and viewer_participant["is_alive"]:
        available_ability_target_ids = [p["_id"] for p in participant_docs if p["is_alive"]]

    runtime_player = _runtime_player_for_participant(
        session_doc["state_json"], viewer_participant["_id"]
    )
    abilities = runtime_player.get("abilities", []) if runtime_player else []
    phase_abilities = [
        ability
        for ability in abilities
        if ability.get("phase") == session_doc["current_phase"]
    ]

    required_ids = (
        (session_doc["state_json"].get("action_state") or {}).get("required_participant_ids")
        or []
    )
    action_required = viewer_participant["_id"] in required_ids

    return {
        "participant_id": viewer_participant["_id"],
        "display_name": viewer_participant["display_name"],
        "is_alive": viewer_participant["is_alive"],
        "role_name": viewer_participant["role_name"],
        "role_alignment": viewer_participant["role_alignment"],
        "abilities": abilities,
        "phase_abilities": phase_abilities,
        "has_submitted_action": has_submitted_action,
        "has_submitted_ability": has_submitted_ability,
        "has_submitted_vote": has_submitted_vote,
        "current_ability_target_id": current_ability_target_id,
        "current_vote_target_id": current_vote_target_id,
        "available_ability_target_ids": available_ability_target_ids,
        "available_vote_target_ids": available_vote_target_ids,
        "action_required": action_required,
    }


def _runtime_player_for_participant(state_json: dict, participant_id: int) -> Optional[dict]:
    for player in (state_json or {}).get("players", []):
        if player.get("participant_id") == participant_id:
            return player
    return None
