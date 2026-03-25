from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from config.asgi import application

from .models import (
    GameAction,
    GameParticipant,
    GameRoleSlot,
    GameSession,
    GameTemplate,
    RoleTemplate,
)


User = get_user_model()


class GameSessionModelTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username="host_player",
            password="super-secret-pass",
        )
        self.template = GameTemplate.objects.create(
            name="Network Test Template",
            min_players=2,
            max_players=8,
            creator=self.host,
        )

    def test_game_session_generates_join_code_and_defaults(self):
        session = GameSession.objects.create(
            template=self.template,
            host=self.host,
        )

        self.assertEqual(len(session.join_code), GameSession.JOIN_CODE_LENGTH)
        self.assertEqual(session.status, GameSession.STATUS_LOBBY)
        self.assertEqual(session.current_phase, GameSession.PHASE_WAITING)
        self.assertEqual(session.turn_number, 0)
        self.assertEqual(session.state_json, {})

    def test_game_participant_is_unique_per_user_in_session(self):
        session = GameSession.objects.create(
            template=self.template,
            host=self.host,
        )

        GameParticipant.objects.create(
            session=session,
            user=self.host,
            display_name="Host Player",
            seat_order=0,
        )

        with self.assertRaises(IntegrityError):
            GameParticipant.objects.create(
                session=session,
                user=self.host,
                display_name="Host Player 2",
                seat_order=1,
            )

    def test_game_action_defaults_to_submitted_status(self):
        session = GameSession.objects.create(
            template=self.template,
            host=self.host,
        )
        participant = GameParticipant.objects.create(
            session=session,
            user=self.host,
            display_name="Host Player",
            seat_order=0,
        )

        action = GameAction.objects.create(
            session=session,
            participant=participant,
            phase=GameSession.PHASE_VOTING,
            action_type="VOTE",
            payload={"target": "Player B"},
        )

        self.assertEqual(action.status, GameAction.STATUS_SUBMITTED)
        self.assertEqual(action.payload["target"], "Player B")


class NetworkSessionApiTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username="api_host",
            password="super-secret-pass",
        )
        self.guest = User.objects.create_user(
            username="api_guest",
            password="super-secret-pass",
        )
        self.template = self._build_template(self.host)

        self.host_client = APIClient()
        self.host_client.force_authenticate(user=self.host)

        self.guest_client = APIClient()
        self.guest_client.force_authenticate(user=self.guest)

    def test_create_network_session_creates_host_participant(self):
        response = self.host_client.post(
            "/api/sessions/",
            {"template_id": self.template.id, "display_name": "Captain Host"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["session"]["status"], GameSession.STATUS_LOBBY)
        self.assertEqual(response.data["participants"][0]["display_name"], "Captain Host")
        self.assertEqual(GameSession.objects.count(), 1)
        self.assertEqual(GameParticipant.objects.count(), 1)

    def test_join_ready_and_start_flow_returns_viewer_specific_snapshot(self):
        create_response = self.host_client.post(
            "/api/sessions/",
            {"template_id": self.template.id, "display_name": "Captain Host"},
            format="json",
        )
        session_id = create_response.data["session"]["id"]
        join_code = create_response.data["session"]["join_code"]

        join_response = self.guest_client.post(
            "/api/sessions/join/",
            {"join_code": join_code, "display_name": "Guest Scout"},
            format="json",
        )
        self.assertEqual(join_response.status_code, 200)
        self.assertEqual(join_response.data["session"]["participant_count"], 2)

        self.host_client.post(
            f"/api/sessions/{session_id}/ready/",
            {"is_ready": True},
            format="json",
        )
        self.guest_client.post(
            f"/api/sessions/{session_id}/ready/",
            {"is_ready": True},
            format="json",
        )

        start_response = self.host_client.post(
            f"/api/sessions/{session_id}/start/",
            {},
            format="json",
        )

        self.assertEqual(start_response.status_code, 200)
        self.assertEqual(start_response.data["session"]["status"], GameSession.STATUS_IN_PROGRESS)
        self.assertEqual(start_response.data["session"]["current_phase"], "NIGHT")
        self.assertEqual(start_response.data["state"]["phase"], "NIGHT")

        host_snapshot = self.host_client.get(f"/api/sessions/{session_id}/snapshot/")
        guest_snapshot = self.guest_client.get(f"/api/sessions/{session_id}/snapshot/")

        self.assertEqual(host_snapshot.status_code, 200)
        self.assertEqual(guest_snapshot.status_code, 200)

        host_participants = {
            participant["username"]: participant
            for participant in host_snapshot.data["participants"]
        }
        guest_participants = {
            participant["username"]: participant
            for participant in guest_snapshot.data["participants"]
        }

        self.assertTrue(host_participants["api_host"]["role_name"])
        self.assertEqual(host_participants["api_guest"]["role_name"], "")
        self.assertTrue(guest_participants["api_guest"]["role_name"])
        self.assertEqual(guest_participants["api_host"]["role_name"], "")

    def _build_template(self, creator):
        template = GameTemplate.objects.create(
            name="API Session Template",
            min_players=2,
            max_players=4,
            creator=creator,
        )
        town_role = RoleTemplate.objects.create(
            name="Villager",
            alignment="TOWN",
            description="Basic town role",
        )
        mafia_role = RoleTemplate.objects.create(
            name="Mafioso",
            alignment="MAFIA",
            description="Basic mafia role",
        )
        GameRoleSlot.objects.create(game_template=template, role=town_role, count=1)
        GameRoleSlot.objects.create(game_template=template, role=mafia_role, count=1)
        return template


class GameSessionWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username="socket_host",
            password="super-secret-pass",
        )
        self.guest = User.objects.create_user(
            username="socket_guest",
            password="super-secret-pass",
        )
        self.outsider = User.objects.create_user(
            username="socket_outsider",
            password="super-secret-pass",
        )
        self.template = GameTemplate.objects.create(
            name="Socket Template",
            min_players=2,
            max_players=8,
            creator=self.host,
        )
        self.session = GameSession.objects.create(
            template=self.template,
            host=self.host,
        )
        GameParticipant.objects.create(
            session=self.session,
            user=self.host,
            display_name="Host Player",
            seat_order=0,
        )
        GameParticipant.objects.create(
            session=self.session,
            user=self.guest,
            display_name="Guest Player",
            seat_order=1,
        )
        self.host_token = Token.objects.create(user=self.host)
        self.guest_token = Token.objects.create(user=self.guest)
        self.outsider_token = Token.objects.create(user=self.outsider)

        self.guest_client = APIClient()
        self.guest_client.force_authenticate(user=self.guest)

    def test_authenticated_participant_can_connect_and_receive_snapshot(self):
        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session.id}/?token={self.guest_token.key}",
            )

            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            payload = await communicator.receive_json_from()
            self.assertEqual(payload["type"], "session.snapshot")
            self.assertEqual(payload["reason"], "connection.accepted")
            self.assertEqual(payload["snapshot"]["session"]["id"], self.session.id)

            await communicator.disconnect()

        async_to_sync(run_test)()

    def test_unauthenticated_websocket_connection_is_rejected(self):
        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session.id}/",
            )

            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(run_test)()

    def test_authenticated_non_member_is_rejected(self):
        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session.id}/?token={self.outsider_token.key}",
            )

            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(run_test)()

    def test_ready_endpoint_broadcasts_snapshot_to_connected_members(self):
        async def run_test():
            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{self.session.id}/?token={self.host_token.key}",
            )

            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            initial_payload = await communicator.receive_json_from()
            self.assertEqual(initial_payload["reason"], "connection.accepted")

            # Consume the host's own presence-broadcast snapshot.
            await communicator.receive_json_from()

            response = await sync_to_async(
                self.guest_client.post,
                thread_sensitive=True,
            )(
                f"/api/sessions/{self.session.id}/ready/",
                {"is_ready": True},
                format="json",
            )
            self.assertEqual(response.status_code, 200)

            broadcast_payload = await communicator.receive_json_from()
            self.assertEqual(broadcast_payload["type"], "session.snapshot")
            self.assertEqual(broadcast_payload["reason"], "participant.ready_changed")
            guest_entry = next(
                participant
                for participant in broadcast_payload["snapshot"]["participants"]
                if participant["username"] == "socket_guest"
            )
            self.assertTrue(guest_entry["is_ready"])

            await communicator.disconnect()

        async_to_sync(run_test)()
