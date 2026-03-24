from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from rest_framework.authtoken.models import Token

from config.asgi import application

from .models import GameAction, GameParticipant, GameSession, GameTemplate


User = get_user_model()


class GameSessionModelTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username="host_player",
            password="super-secret-pass",
        )
        self.template = GameTemplate.objects.create(
            name="Network Test Template",
            min_players=4,
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
            min_players=4,
            max_players=8,
            creator=self.host,
        )
        self.session = GameSession.objects.create(
            template=self.template,
            host=self.host,
        )
        self.participant = GameParticipant.objects.create(
            session=self.session,
            user=self.guest,
            display_name="Guest Player",
            seat_order=0,
        )
        self.guest_token = Token.objects.create(user=self.guest)
        self.outsider_token = Token.objects.create(user=self.outsider)

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
            self.assertEqual(
                payload["snapshot"]["participants"][0]["display_name"],
                "Guest Player",
            )

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
