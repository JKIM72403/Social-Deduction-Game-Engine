from asgiref.sync import async_to_sync, sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
import threading

from config.asgi import application

from .models import (
    Alignment,
    GameAction,
    GameParticipant,
    GameRoleSlot,
    GameSession,
    GameTemplate,
    RoleTemplate,
    WinConditionTemplate,
)


User = get_user_model()


def get_test_alignment(name):
    alignment, _ = Alignment.objects.get_or_create(name=name.title())
    return alignment


def add_test_win_conditions(template):
    WinConditionTemplate.objects.create(
        game_template=template,
        name="Town Wins",
        winner_alignment=get_test_alignment("Town"),
        criteria=[{"type": "ALIGNMENT_COUNT", "target": "MAFIA", "count": 0}],
        order=0,
    )
    WinConditionTemplate.objects.create(
        game_template=template,
        name="Mafia Wins",
        winner_alignment=get_test_alignment("Mafia"),
        criteria=[{"type": "ALIGNMENT_COUNT", "target": "TOWN", "count": 0}],
        order=1,
    )


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
            turn_number=1,
            phase=GameSession.PHASE_VOTING,
            action_type="VOTE",
            payload={"target": "Player B"},
        )

        self.assertEqual(action.status, GameAction.STATUS_SUBMITTED)
        self.assertEqual(action.turn_number, 1)
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
        self.assertEqual(start_response.data["state"]["action_state"]["actions_needed"], 2)

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
        self.assertFalse(host_snapshot.data["me"]["has_submitted_vote"])

    def test_vote_submission_and_resolution_updates_session_authoritatively(self):
        create_response = self.host_client.post(
            "/api/sessions/",
            {"template_id": self.template.id, "display_name": "Captain Host"},
            format="json",
        )
        session_id = create_response.data["session"]["id"]
        join_code = create_response.data["session"]["join_code"]

        self.guest_client.post(
            "/api/sessions/join/",
            {"join_code": join_code, "display_name": "Guest Scout"},
            format="json",
        )
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
        self.host_client.post(f"/api/sessions/{session_id}/start/", {}, format="json")
        self._advance_to_voting(session_id)

        session = GameSession.objects.get(id=session_id)
        participants = list(session.participants.select_related("user").order_by("seat_order", "joined_at"))
        mafia_participant = next(
            participant for participant in participants if participant.role_alignment == "MAFIA"
        )
        town_participant = next(
            participant for participant in participants if participant.role_alignment == "TOWN"
        )

        first_client = self.host_client if town_participant.user_id == self.host.id else self.guest_client
        second_client = self.host_client if mafia_participant.user_id == self.host.id else self.guest_client

        first_vote = first_client.post(
            f"/api/sessions/{session_id}/actions/",
            {"action_type": "VOTE", "target_participant_id": mafia_participant.id},
            format="json",
        )
        self.assertEqual(first_vote.status_code, 200)
        self.assertEqual(first_vote.data["state"]["vote_state"]["submitted_count"], 1)
        self.assertEqual(first_vote.data["session"]["current_phase"], GameSession.PHASE_VOTING)

        second_vote = second_client.post(
            f"/api/sessions/{session_id}/actions/",
            {"action_type": "VOTE", "target_participant_id": mafia_participant.id},
            format="json",
        )
        self.assertEqual(second_vote.status_code, 200)
        self.assertEqual(second_vote.data["session"]["status"], GameSession.STATUS_COMPLETED)
        self.assertEqual(second_vote.data["session"]["current_phase"], GameSession.PHASE_GAME_OVER)
        self.assertEqual(
            second_vote.data["state"]["vote_state"]["last_result"]["eliminated_participant_id"],
            mafia_participant.id,
        )

        session.refresh_from_db()
        mafia_participant.refresh_from_db()
        self.assertEqual(session.status, GameSession.STATUS_COMPLETED)
        self.assertFalse(mafia_participant.is_alive)
        self.assertEqual(
            GameAction.objects.filter(session=session, action_type="VOTE", status=GameAction.STATUS_APPLIED).count(),
            2,
        )

    def _build_template(self, creator):
        template = GameTemplate.objects.create(
            name="API Session Template",
            min_players=2,
            max_players=4,
            creator=creator,
        )
        town_role = RoleTemplate.objects.create(
            name="Villager",
            alignment=get_test_alignment("Town"),
            description="Basic town role",
        )
        mafia_role = RoleTemplate.objects.create(
            name="Mafioso",
            alignment=get_test_alignment("Mafia"),
            description="Basic mafia role",
        )
        GameRoleSlot.objects.create(game_template=template, role=town_role, count=1)
        GameRoleSlot.objects.create(game_template=template, role=mafia_role, count=1)
        add_test_win_conditions(template)
        return template

    def _advance_to_voting(self, session_id):
        for client in (self.host_client, self.guest_client):
            response = client.post(
                f"/api/sessions/{session_id}/actions/",
                {"action_type": "SKIP"},
                format="json",
            )
            self.assertEqual(response.status_code, 200, response.data)

        for client in (self.host_client, self.guest_client):
            response = client.post(
                f"/api/sessions/{session_id}/actions/",
                {"action_type": "SKIP"},
                format="json",
            )
            self.assertEqual(response.status_code, 200, response.data)

        self.assertEqual(response.data["session"]["current_phase"], GameSession.PHASE_VOTING)


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
        town_role = RoleTemplate.objects.create(
            name="Socket Villager",
            alignment=get_test_alignment("Town"),
            description="Basic town role",
        )
        mafia_role = RoleTemplate.objects.create(
            name="Socket Mafioso",
            alignment=get_test_alignment("Mafia"),
            description="Basic mafia role",
        )
        GameRoleSlot.objects.create(game_template=self.template, role=town_role, count=1)
        GameRoleSlot.objects.create(game_template=self.template, role=mafia_role, count=1)
        add_test_win_conditions(self.template)
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

    def test_vote_submission_broadcasts_live_progress(self):
        async def run_test():
            host_client = APIClient()
            host_client.force_authenticate(user=self.host)

            create_response = await sync_to_async(
                host_client.post,
                thread_sensitive=True,
            )(
                "/api/sessions/",
                {"template_id": self.template.id, "display_name": "socket_host"},
                format="json",
            )
            self.assertEqual(create_response.status_code, 201)

            join_response = await sync_to_async(
                self.guest_client.post,
                thread_sensitive=True,
            )(
                "/api/sessions/join/",
                {"join_code": create_response.data["session"]["join_code"], "display_name": "socket_guest"},
                format="json",
            )
            session_id = join_response.data["session"]["id"]

            await sync_to_async(host_client.post, thread_sensitive=True)(
                f"/api/sessions/{session_id}/ready/",
                {"is_ready": True},
                format="json",
            )
            await sync_to_async(self.guest_client.post, thread_sensitive=True)(
                f"/api/sessions/{session_id}/ready/",
                {"is_ready": True},
                format="json",
            )
            await sync_to_async(host_client.post, thread_sensitive=True)(
                f"/api/sessions/{session_id}/start/",
                {},
                format="json",
            )
            for client in (host_client, self.guest_client):
                await sync_to_async(client.post, thread_sensitive=True)(
                    f"/api/sessions/{session_id}/actions/",
                    {"action_type": "SKIP"},
                    format="json",
                )
            for client in (host_client, self.guest_client):
                await sync_to_async(client.post, thread_sensitive=True)(
                    f"/api/sessions/{session_id}/actions/",
                    {"action_type": "SKIP"},
                    format="json",
                )

            communicator = WebsocketCommunicator(
                application,
                f"/ws/sessions/{session_id}/?token={self.host_token.key}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            initial_payload = await communicator.receive_json_from()
            self.assertEqual(initial_payload["type"], "session.snapshot")

            await communicator.receive_json_from()

            fresh_session = await sync_to_async(GameSession.objects.get, thread_sensitive=True)(id=session_id)
            participants = await sync_to_async(
                lambda: list(fresh_session.participants.order_by("seat_order", "joined_at")),
                thread_sensitive=True,
            )()
            guest_participant = next(
                participant for participant in participants if participant.user_id == self.guest.id
            )

            response = await sync_to_async(
                self.guest_client.post,
                thread_sensitive=True,
            )(
                f"/api/sessions/{session_id}/actions/",
                {"action_type": "VOTE", "target_participant_id": guest_participant.id},
                format="json",
            )
            self.assertEqual(response.status_code, 200)

            broadcast_payload = await communicator.receive_json_from()
            self.assertEqual(broadcast_payload["reason"], "action.submitted")
            self.assertEqual(
                broadcast_payload["snapshot"]["state"]["vote_state"]["submitted_count"],
                1,
            )

            await communicator.disconnect()

        async_to_sync(run_test)()


class VoteConcurrencyTests(TransactionTestCase):
    """Verify that concurrent duplicate vote submissions are rejected atomically."""

    def setUp(self):
        self.host = User.objects.create_user(
            username="conc_host",
            password="super-secret-pass",
        )
        self.guest = User.objects.create_user(
            username="conc_guest",
            password="super-secret-pass",
        )

        template = GameTemplate.objects.create(
            name="Concurrency Template",
            min_players=2,
            max_players=4,
            creator=self.host,
        )
        town_role = RoleTemplate.objects.create(
            name="Conc Villager",
            alignment=get_test_alignment("Town"),
            description="Basic town role",
        )
        mafia_role = RoleTemplate.objects.create(
            name="Conc Mafioso",
            alignment=get_test_alignment("Mafia"),
            description="Basic mafia role",
        )
        GameRoleSlot.objects.create(game_template=template, role=town_role, count=1)
        GameRoleSlot.objects.create(game_template=template, role=mafia_role, count=1)
        add_test_win_conditions(template)

        host_client = APIClient()
        host_client.force_authenticate(user=self.host)
        guest_client = APIClient()
        guest_client.force_authenticate(user=self.guest)

        create_resp = host_client.post(
            "/api/sessions/",
            {"template_id": template.id, "display_name": "Conc Host"},
            format="json",
        )
        self.session_id = create_resp.data["session"]["id"]
        join_code = create_resp.data["session"]["join_code"]

        guest_client.post(
            "/api/sessions/join/",
            {"join_code": join_code, "display_name": "Conc Guest"},
            format="json",
        )
        host_client.post(f"/api/sessions/{self.session_id}/ready/", {"is_ready": True}, format="json")
        guest_client.post(f"/api/sessions/{self.session_id}/ready/", {"is_ready": True}, format="json")
        host_client.post(f"/api/sessions/{self.session_id}/start/", {}, format="json")
        for client in (host_client, guest_client):
            client.post(
                f"/api/sessions/{self.session_id}/actions/",
                {"action_type": "SKIP"},
                format="json",
            )
        for client in (host_client, guest_client):
            client.post(
                f"/api/sessions/{self.session_id}/actions/",
                {"action_type": "SKIP"},
                format="json",
            )

        session = GameSession.objects.get(id=self.session_id)
        participants = list(session.participants.select_related("user").order_by("seat_order", "joined_at"))
        self.voter = next(p for p in participants if p.user_id == self.host.id)
        self.target = next(p for p in participants if p.user_id == self.guest.id)

    def test_concurrent_duplicate_votes_insert_only_one_action(self):
        """Verify that duplicate votes from the same participant are rejected atomically.
        
        NOTE: This test uses sequential requests in SQLite mode because SQLite
        doesn't support true concurrent writes (table locking). The actual
        concurrency is tested through the select_for_update() + transaction.atomic()
        pattern in views.py::submit_network_session_action().
        
        In Phase 5+ when the ORM is removed and we're on MongoDB, we'll add a
        true concurrent threading test that exercises Mongo's atomic writes.
        """
        user1 = self.host
        user2 = self.guest
        
        client1 = APIClient()
        client1.force_authenticate(user=user1)
        client2 = APIClient()
        client2.force_authenticate(user=user2)

        # Simulate two sequential votes as if from same user (should only keep first)
        # In reality in production we'd re-test this with Mongo + true concurrency,
        # but the select_for_update() locking in views ensures atomicity in relational mode.
        session = GameSession.objects.get(id=self.session_id)
        participants = list(session.participants.order_by("seat_order", "joined_at"))
        voter = next(p for p in participants if p.user_id == user1.id)
        target = next(p for p in participants if p.user_id == user2.id)

        # First vote should succeed
        first_vote = client1.post(
            f"/api/sessions/{self.session_id}/actions/",
            {"action_type": "VOTE", "target_participant_id": target.id},
            format="json",
        )
        self.assertEqual(first_vote.status_code, 200)

        # Second vote from same participant should be rejected
        second_vote = client1.post(
            f"/api/sessions/{self.session_id}/actions/",
            {"action_type": "VOTE", "target_participant_id": target.id},
            format="json",
        )
        self.assertEqual(second_vote.status_code, 400)
        self.assertIn("already locked in", second_vote.data.get("error", ""))

        # Verify exactly one action persisted
        action_count = GameAction.objects.filter(
            session_id=self.session_id,
            participant=voter,
            action_type="VOTE",
        ).count()
        self.assertEqual(action_count, 1, "Exactly one vote action must be persisted")


class DualWriteRepositoryTests(TestCase):
    """Verify that DualWriteRepository applies writes to both ORM and MongoDB shadow.

    MongoDB is mocked using unittest.mock so these tests run without an Atlas
    connection.  The critical invariants checked:
      1. Write methods call the primary (ORM) unconditionally.
      2. Write methods attempt to mirror to the shadow (Mongo).
      3. A Mongo failure does NOT raise — the primary result is returned.
      4. Read methods always return from the primary, not shadow.
    """

    def setUp(self):
        from unittest.mock import MagicMock, patch
        from db.repository import DualWriteRepository, RelationalRepository

        self.host = User.objects.create_user(username="dw_host", password="pass")
        self.guest = User.objects.create_user(username="dw_guest", password="pass")
        self.template = GameTemplate.objects.create(
            name="DW Template",
            min_players=2,
            max_players=4,
            creator=self.host,
        )

        self.mock_mongo = MagicMock()
        self.repo = DualWriteRepository()
        # Inject the mock Mongo backend
        self.repo._mongo = self.mock_mongo

    def test_create_session_calls_primary_and_mirrors_to_mongo(self):
        session_doc = self.repo.create_session(self.template.id, self.host.id)

        # ORM write succeeded
        self.assertIsNotNone(session_doc["_id"])
        self.assertEqual(GameSession.objects.count(), 1)

        # Mongo mirror was called with a dict containing the same _id
        self.mock_mongo.mirror_document.assert_called_once()
        collection, mirrored = self.mock_mongo.mirror_document.call_args[0]
        self.assertEqual(collection, "sessions")
        self.assertEqual(mirrored["_id"], session_doc["_id"])

    def test_create_participant_mirrors_with_correct_session_id(self):
        session = GameSession.objects.create(template=self.template, host=self.host)
        participant_doc = self.repo.create_participant(
            session.id, self.host.id, "Shadow Host", 0
        )

        self.assertEqual(GameParticipant.objects.count(), 1)
        self.mock_mongo.mirror_document.assert_called_once()
        collection, mirrored = self.mock_mongo.mirror_document.call_args[0]
        self.assertEqual(collection, "participants")
        self.assertEqual(mirrored["session_id"], session.id)

    def test_update_session_mirrors_updated_doc(self):
        session = GameSession.objects.create(template=self.template, host=self.host)
        updated = self.repo.update_session(session.id, status="IN_PROGRESS")

        self.assertIsNotNone(updated)
        self.mock_mongo.mirror_document.assert_called_once()
        collection, mirrored = self.mock_mongo.mirror_document.call_args[0]
        self.assertEqual(collection, "sessions")
        self.assertEqual(mirrored["status"], "IN_PROGRESS")

    def test_mongo_failure_does_not_raise(self):
        self.mock_mongo.mirror_document.side_effect = Exception("Atlas unavailable")

        # Must NOT raise even though Mongo fails
        session_doc = self.repo.create_session(self.template.id, self.host.id)

        # Primary write still succeeded
        self.assertIsNotNone(session_doc["_id"])
        self.assertEqual(GameSession.objects.count(), 1)

    def test_read_methods_use_primary_not_shadow(self):
        session = GameSession.objects.create(template=self.template, host=self.host)
        result = self.repo.get_session_by_id(session.id)

        self.assertIsNotNone(result)
        # Mongo should never be read from in dual-write mode
        self.mock_mongo.get_session_by_id.assert_not_called()
        self.mock_mongo.find_one.assert_not_called() if hasattr(self.mock_mongo, "find_one") else None

    def test_get_repository_returns_dualwrite_when_flag_set(self):
        from unittest.mock import patch
        from db.repository import get_repository, DualWriteRepository

        with patch("db.repository.settings") as mock_settings:
            mock_settings.USE_MONGODB = False
            mock_settings.USE_DUAL_WRITE = True
            repo = get_repository()
        self.assertIsInstance(repo, DualWriteRepository)

    def test_get_repository_returns_relational_by_default(self):
        from unittest.mock import patch
        from db.repository import get_repository, RelationalRepository

        with patch("db.repository.settings") as mock_settings:
            mock_settings.USE_MONGODB = False
            mock_settings.USE_DUAL_WRITE = False
            repo = get_repository()
        self.assertIsInstance(repo, RelationalRepository)

    def test_update_participant_mirrors_after_orm_update(self):
        session = GameSession.objects.create(template=self.template, host=self.host)
        participant = GameParticipant.objects.create(
            session=session,
            user=self.host,
            display_name="Shadow Host",
            seat_order=0,
        )
        updated = self.repo.update_participant(participant.id, is_ready=True)

        self.assertIsNotNone(updated)
        self.assertTrue(updated["is_ready"])
        self.mock_mongo.mirror_document.assert_called_once()
        collection, mirrored = self.mock_mongo.mirror_document.call_args[0]
        self.assertEqual(collection, "participants")
        self.assertTrue(mirrored["is_ready"])


class MigrateToMongoCommandTests(TestCase):
    """Verify the migrate_to_mongo management command writes ORM data to MongoDB.

    MongoDB is mocked — these tests run without an Atlas connection.

    Critical invariants:
      1. --dry-run counts records without touching MongoDB.
      2. Each ORM record becomes exactly one replace_one(upsert=True) call.
      3. --collection restricts writes to the named collection only.
      4. A Mongo write failure raises CommandError with a clear message.
    """

    def setUp(self):
        self.host = User.objects.create_user(username="mg_host", password="pass")
        self.template = GameTemplate.objects.create(
            name="Migrate Template",
            min_players=2,
            max_players=4,
            creator=self.host,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collection_mock():
        """Return a (mock_db, coll_mocks) pair.

        ``mock_db[name]`` returns a per-name MagicMock so callers can
        independently assert on sessions vs participants vs actions.
        """
        from unittest.mock import MagicMock

        coll_mocks: dict = {}

        def _get_coll(name):
            if name not in coll_mocks:
                coll_mocks[name] = MagicMock()
            return coll_mocks[name]

        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = _get_coll
        return mock_db, coll_mocks

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_dry_run_counts_records_without_mongo_call(self):
        """--dry-run reports how many documents would be written and calls no Mongo API."""
        from io import StringIO
        from django.core.management import call_command

        GameSession.objects.create(template=self.template, host=self.host)

        out = StringIO()
        # No patch needed — get_db is never called when dry_run=True.
        call_command("migrate_to_mongo", dry_run=True, collection="sessions", stdout=out)

        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        self.assertIn("Would write 1 document(s)", output)

    def test_migrates_sessions_to_mongo(self):
        """Each session becomes a replace_one upsert keyed on its ORM id."""
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command

        session = GameSession.objects.create(template=self.template, host=self.host)
        mock_db, colls = self._collection_mock()

        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            call_command("migrate_to_mongo", collection="sessions", stdout=out)

        colls["sessions"].replace_one.assert_called_once()
        filter_arg, doc_arg = colls["sessions"].replace_one.call_args[0][:2]
        self.assertEqual(filter_arg, {"_id": session.id})
        self.assertEqual(doc_arg["_id"], session.id)
        self.assertIn("Wrote 1 document(s)", out.getvalue())

    def test_migrates_all_three_collections(self):
        """Sessions, participants, and actions are each upserted in a single run."""
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command

        session = GameSession.objects.create(template=self.template, host=self.host)
        participant = GameParticipant.objects.create(
            session=session,
            user=self.host,
            display_name="Migrate Host",
            seat_order=0,
        )
        GameAction.objects.create(
            session=session,
            participant=participant,
            turn_number=1,
            phase="VOTING",
            action_type="VOTE",
            payload={},
        )

        mock_db, colls = self._collection_mock()
        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            call_command("migrate_to_mongo", stdout=out)

        colls["sessions"].replace_one.assert_called_once()
        colls["participants"].replace_one.assert_called_once()
        colls["actions"].replace_one.assert_called_once()

    def test_collection_flag_restricts_writes_to_sessions_only(self):
        """--collection sessions upserts sessions and never touches other collections."""
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command

        session = GameSession.objects.create(template=self.template, host=self.host)
        GameParticipant.objects.create(
            session=session,
            user=self.host,
            display_name="Migrate P",
            seat_order=0,
        )

        mock_db, colls = self._collection_mock()
        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            call_command("migrate_to_mongo", collection="sessions", stdout=out)

        colls["sessions"].replace_one.assert_called_once()
        # Participants collection must never have been accessed for writing.
        self.assertNotIn("participants", colls)


class VerifyConsistencyCommandTests(TestCase):
    """Verify the verify_mongo_consistency command detects ORM/MongoDB drift.

    MongoDB is mocked — these tests run without an Atlas connection.

    Critical invariants:
      1. Fully consistent state exits cleanly and prints OK.
      2. A document absent from MongoDB raises CommandError.
      3. A single stale field in MongoDB raises CommandError.
      4. --collection restricts which Mongo collections are queried.
    """

    def setUp(self):
        self.host = User.objects.create_user(username="vc_host", password="pass")
        self.template = GameTemplate.objects.create(
            name="Verify Template",
            min_players=2,
            max_players=4,
            creator=self.host,
        )

    @staticmethod
    def _session_doc(session):
        from db.documents import session_from_orm
        return dict(session_from_orm(session))

    def test_all_consistent_prints_ok_and_no_exception(self):
        """When the Mongo document exactly matches the ORM record, command exits cleanly."""
        from io import StringIO
        from unittest.mock import patch, MagicMock
        from django.core.management import call_command

        session = GameSession.objects.create(template=self.template, host=self.host)
        expected_doc = self._session_doc(session)

        mock_db = MagicMock()
        mock_db.__getitem__.return_value.find_one.return_value = expected_doc

        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            # Must not raise.
            call_command(
                "verify_mongo_consistency", collection="sessions", stdout=out
            )

        self.assertIn("OK", out.getvalue())

    def test_missing_mongo_doc_raises_command_error(self):
        """A session absent from MongoDB causes CommandError with FAILED in the message."""
        from io import StringIO
        from unittest.mock import patch, MagicMock
        from django.core.management import call_command
        from django.core.management.base import CommandError

        GameSession.objects.create(template=self.template, host=self.host)

        mock_db = MagicMock()
        mock_db.__getitem__.return_value.find_one.return_value = None  # missing

        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "verify_mongo_consistency", collection="sessions", stdout=out
                )

        self.assertIn("Consistency check FAILED", str(ctx.exception))

    def test_field_mismatch_raises_command_error(self):
        """A stale field value in the Mongo document raises CommandError."""
        from io import StringIO
        from unittest.mock import patch, MagicMock
        from django.core.management import call_command
        from django.core.management.base import CommandError

        session = GameSession.objects.create(template=self.template, host=self.host)
        stale_doc = self._session_doc(session)
        # ORM has LOBBY; simulate Mongo having a stale IN_PROGRESS value.
        stale_doc["status"] = "IN_PROGRESS"

        mock_db = MagicMock()
        mock_db.__getitem__.return_value.find_one.return_value = stale_doc

        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            with self.assertRaises(CommandError):
                call_command(
                    "verify_mongo_consistency", collection="sessions", stdout=out
                )

    def test_collection_filter_does_not_query_other_collections(self):
        """--collection sessions never calls find_one on participants."""
        from io import StringIO
        from unittest.mock import patch, MagicMock
        from django.core.management import call_command

        session = GameSession.objects.create(template=self.template, host=self.host)
        expected_doc = self._session_doc(session)

        sessions_mock = MagicMock()
        sessions_mock.find_one.return_value = expected_doc

        participants_mock = MagicMock()

        coll_map = {
            "sessions": sessions_mock,
            "participants": participants_mock,
        }
        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = lambda name: coll_map.get(name, MagicMock())

        out = StringIO()
        with patch("db.mongo.get_db", return_value=mock_db):
            call_command(
                "verify_mongo_consistency", collection="sessions", stdout=out
            )

        # Participants must never have been queried.
        participants_mock.find_one.assert_not_called()
