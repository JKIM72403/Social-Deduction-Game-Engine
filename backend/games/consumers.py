from typing import Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from db.repository import get_repository
from .session_state import load_session_snapshot


@database_sync_to_async
def get_accessible_session(session_id: int, user_id: int):
    """Return the session document if ``user_id`` is the host or a participant."""
    repo = get_repository()
    session_doc = repo.get_session_by_id(session_id)
    if session_doc is None:
        return None
    is_host = session_doc["host_user_id"] == user_id
    if is_host:
        return session_doc
    participant = repo.get_participant_by_session_and_user(session_id, user_id)
    return session_doc if participant is not None else None


@database_sync_to_async
def get_participant_id(session_id: int, user_id: int):
    repo = get_repository()
    participant = repo.get_participant_by_session_and_user(session_id, user_id)
    return participant["_id"] if participant is not None else None


@database_sync_to_async
def set_participant_connection_state(participant_id: Optional[int], is_connected: bool):
    if participant_id is None:
        return
    repo = get_repository()
    repo.update_participant(participant_id, is_connected=is_connected)


@database_sync_to_async
def get_snapshot(session_id: int, viewer_user_id: int):
    return load_session_snapshot(session_id, viewer_user_id=viewer_user_id)


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
        snapshot = await get_snapshot(self.session_id, user.id)

        await self.accept()
        await self.send_json(
            {
                "type": "session.snapshot",
                "reason": "connection.accepted",
                "snapshot": snapshot,
            }
        )
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "session.event",
                "reason": "participant.connected",
            },
        )

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if not group_name:
            return

        await set_participant_connection_state(getattr(self, "participant_id", None), False)
        await self.channel_layer.group_discard(group_name, self.channel_name)
        await self.channel_layer.group_send(
            group_name,
            {
                "type": "session.event",
                "reason": "participant.disconnected",
            },
        )

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
                    "snapshot": await get_snapshot(self.session_id, self.scope["user"].id),
                }
            )
            return

        await self.send_json(
            {
                "type": "error",
                "message": f"Unsupported websocket message type: {message_type!r}",
            }
        )

    async def session_event(self, event):
        await self.send_json(
            {
                "type": "session.snapshot",
                "reason": event["reason"],
                "snapshot": await get_snapshot(self.session_id, self.scope["user"].id),
            }
        )
