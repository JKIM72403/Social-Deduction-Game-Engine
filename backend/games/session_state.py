from .models import GameSession


def build_session_snapshot(session: GameSession) -> dict:
    participants = session.participants.select_related("user").order_by("seat_order", "joined_at")

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
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
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
                "role_name": participant.role_name,
                "role_alignment": participant.role_alignment,
                "joined_at": participant.joined_at.isoformat(),
                "last_seen_at": participant.last_seen_at.isoformat(),
            }
            for participant in participants
        ],
        "state": session.state_json,
    }
