from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import GameAction
from .models import GameSession


def build_started_session_state(engine) -> dict:
    return {
        "phase": engine.phase_state.value,
        "turn_number": engine.turn_number,
        "phase_index": engine.phase_index,
        "phase_order": list(engine.phase_configs),
        "events": list(engine.events),
        "players": [
            {
                "display_name": player.name,
                "is_alive": player.is_alive,
            }
            for player in engine.players
        ],
    }


def build_session_snapshot(session: GameSession, viewer_user_id: int | None = None) -> dict:
    participants = list(
        session.participants.select_related("user").order_by("seat_order", "joined_at")
    )
    viewer_participant = next(
        (participant for participant in participants if participant.user_id == viewer_user_id),
        None,
    )
    ready_count = sum(1 for participant in participants if participant.is_ready)
    participant_count = len(participants)
    viewer_pending_vote = None

    if viewer_participant and session.current_phase == GameSession.PHASE_VOTING:
        viewer_pending_vote = (
            session.actions.filter(
                participant=viewer_participant,
                phase=GameSession.PHASE_VOTING,
                action_type="VOTE",
                status=GameAction.STATUS_SUBMITTED,
                turn_number=session.turn_number,
            )
            .values("payload")
            .first()
        )

    return {
        "session": {
            "id": session.id,
            "join_code": session.join_code,
            "status": session.status,
            "current_phase": session.current_phase,
            "turn_number": session.turn_number,
            "template_id": session.template_id,
            "template_name": session.template.name,
            "host_user_id": session.host_id,
            "host_username": session.host.username if session.host else None,
            "participant_count": participant_count,
            "ready_count": ready_count,
            "all_ready": participant_count > 0 and ready_count == participant_count,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        },
        "participants": [
            {
                "id": participant.id,
                "user_id": participant.user_id,
                "username": participant.user.username,
                "display_name": participant.display_name,
                "seat_order": participant.seat_order,
                "is_ready": participant.is_ready,
                "is_connected": participant.is_connected,
                "is_alive": participant.is_alive,
                "role_name": participant.role_name
                if _can_view_role(session, participant, viewer_user_id)
                else "",
                "role_alignment": participant.role_alignment
                if _can_view_role(session, participant, viewer_user_id)
                else "",
                "joined_at": participant.joined_at.isoformat(),
                "last_seen_at": participant.last_seen_at.isoformat(),
            }
            for participant in participants
        ],
        "me": _build_viewer_state(session, viewer_participant, viewer_pending_vote),
        "state": session.state_json,
    }


def load_session_snapshot(session_id: int, viewer_user_id: int | None = None) -> dict:
    session = (
        GameSession.objects.select_related("template", "host")
        .prefetch_related("participants__user")
        .get(id=session_id)
    )
    return build_session_snapshot(session, viewer_user_id=viewer_user_id)


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


def _can_view_role(session: GameSession, participant, viewer_user_id: int | None) -> bool:
    if not participant.role_name:
        return False

    if viewer_user_id == participant.user_id:
        return True

    if not participant.is_alive:
        return True

    if session.status in {GameSession.STATUS_COMPLETED, GameSession.STATUS_CANCELLED}:
        return True

    return False


def _build_viewer_state(session: GameSession, viewer_participant, viewer_pending_vote):
    if viewer_participant is None:
        return None

    has_submitted_vote = False
    current_vote_target_id = None
    if viewer_pending_vote:
        payload = viewer_pending_vote.get("payload") or {}
        current_vote_target_id = payload.get("target_participant_id")
        has_submitted_vote = current_vote_target_id is not None

    available_vote_target_ids = []
    if (
        session.status == GameSession.STATUS_IN_PROGRESS
        and session.current_phase == GameSession.PHASE_VOTING
        and viewer_participant.is_alive
    ):
        available_vote_target_ids = [
            participant.id
            for participant in session.participants.all().order_by("seat_order", "joined_at")
            if participant.is_alive
        ]

    return {
        "participant_id": viewer_participant.id,
        "display_name": viewer_participant.display_name,
        "is_alive": viewer_participant.is_alive,
        "role_name": viewer_participant.role_name,
        "role_alignment": viewer_participant.role_alignment,
        "has_submitted_vote": has_submitted_vote,
        "current_vote_target_id": current_vote_target_id,
        "available_vote_target_ids": available_vote_target_ids,
    }
