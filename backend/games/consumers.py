from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import GameParticipant, GameSession
from .session_state import build_session_snapshot


@database_sync_to_async
def get_accessible_session(session_id: int, user_id: int):
    try:
        session = (
            GameSession.objects.select_related("template", "host")
            .get(id=session_id)
        )
    except GameSession.DoesNotExist:
        return None

    is_host = session.host_id == user_id
    is_participant = session.participants.filter(user_id=user_id).exists()
    if not is_host and not is_participant:
        return None

    return session


@database_sync_to_async
def get_participant_id(session_id: int, user_id: int):
    return (
        GameParticipant.objects.filter(session_id=session_id, user_id=user_id)
        .values_list("id", flat=True)
        .first()
    )


@database_sync_to_async
def set_participant_connection_state(participant_id: int | None, is_connected: bool):
    if participant_id is None:
        return
    GameParticipant.objects.filter(id=participant_id).update(is_connected=is_connected)


@database_sync_to_async
def get_snapshot(session_id: int):
    session = (
        GameSession.objects.select_related("template", "host")
        .prefetch_related("participants__user")
        .get(id=session_id)
    )
    return build_session_snapshot(session)


class GameSessionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.session_id = int(self.scope["url_route"]["kwargs"]["session_id"])
        session = await get_accessible_session(self.session_id, user.id)
        if session is None:
            await self.close(code=4404)
            return

        self.group_name = f"session_{self.session_id}"
        self.participant_id = await get_participant_id(self.session_id, user.id)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await set_participant_connection_state(self.participant_id, True)
        snapshot = await get_snapshot(self.session_id)

        await self.accept()
        await self.send_json(
            {
                "type": "session.snapshot",
                "reason": "connection.accepted",
                "snapshot": snapshot,
            }
        )

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if not group_name:
            return

        await set_participant_connection_state(getattr(self, "participant_id", None), False)
        await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")

        if message_type == "ping":
            await self.send_json({"type": "pong"})
            return

        if message_type == "session.request_snapshot":
            await self.send_json(
                {
                    "type": "session.snapshot",
                    "reason": "manual_refresh",
                    "snapshot": await get_snapshot(self.session_id),
                }
            )
            return

        await self.send_json(
            {
                "type": "error",
                "message": f"Unsupported websocket message type: {message_type!r}",
            }
        )
