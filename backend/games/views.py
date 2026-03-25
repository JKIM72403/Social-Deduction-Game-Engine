import random
import uuid

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .engine import Alignment, PhaseState
from .engine_builder import build_game_engine
from .models import (
    AbilityTemplate,
    GameAction,
    GameParticipant,
    GameSession,
    GameTemplate,
    PhaseTemplate,
    RoleTemplate,
    WinConditionTemplate,
)
from .serializers import (
    AbilityTemplateSerializer,
    CreateSessionSerializer,
    GameTemplateSerializer,
    JoinSessionSerializer,
    LoginSerializer,
    PhaseTemplateSerializer,
    RoleTemplateSerializer,
    SessionReadySerializer,
    SignupSerializer,
    SubmitSessionActionSerializer,
    UserSerializer,
    WinConditionTemplateSerializer,
)
from .session_runtime import build_started_session_state, record_vote_progress, resolve_voting_round
from .session_state import (
    broadcast_session_event,
    load_session_snapshot,
)


# --- Auth Views ---

@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {"token": token.key, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if not user:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


class AbilityTemplateViewSet(viewsets.ModelViewSet):
    queryset = AbilityTemplate.objects.all()
    serializer_class = AbilityTemplateSerializer


class RoleTemplateViewSet(viewsets.ModelViewSet):
    queryset = RoleTemplate.objects.all()
    serializer_class = RoleTemplateSerializer


class PhaseTemplateViewSet(viewsets.ModelViewSet):
    queryset = PhaseTemplate.objects.all()
    serializer_class = PhaseTemplateSerializer


class WinConditionTemplateViewSet(viewsets.ModelViewSet):
    queryset = WinConditionTemplate.objects.all()
    serializer_class = WinConditionTemplateSerializer


class GameTemplateViewSet(viewsets.ModelViewSet):
    queryset = GameTemplate.objects.all()
    serializer_class = GameTemplateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return GameTemplate.objects.filter(Q(is_public=True) | Q(creator=user)).distinct()
        return GameTemplate.objects.filter(is_public=True)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator and instance.creator != request.user:
            return Response({"error": "Not the owner"}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator and instance.creator != request.user:
            return Response({"error": "Not the owner"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


# --- Persistent Multiplayer Session Views ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_network_session(request):
    serializer = CreateSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    template = _get_accessible_template(
        serializer.validated_data["template_id"],
        request.user,
    )
    if template is None:
        return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

    requested_name = serializer.validated_data.get("display_name", "")

    with transaction.atomic():
        session = GameSession.objects.create(
            template=template,
            host=request.user,
        )
        GameParticipant.objects.create(
            session=session,
            user=request.user,
            display_name=_ensure_unique_display_name(
                session,
                requested_name,
                request.user.username,
            ),
            seat_order=0,
            is_connected=True,
        )
        transaction.on_commit(
            lambda session_id=session.id: broadcast_session_event(
                session_id,
                "session.created",
            )
        )

    return Response(
        load_session_snapshot(session.id, viewer_user_id=request.user.id),
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_network_session(request):
    serializer = JoinSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    join_code = serializer.validated_data["join_code"].strip().upper()
    requested_name = serializer.validated_data.get("display_name", "")

    try:
        session = GameSession.objects.select_related("template", "host").get(join_code=join_code)
    except GameSession.DoesNotExist:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    existing_participant = session.participants.filter(user=request.user).first()
    if existing_participant:
        existing_participant.is_connected = True
        existing_participant.save(update_fields=["is_connected", "last_seen_at"])
        transaction.on_commit(
            lambda session_id=session.id: broadcast_session_event(
                session_id,
                "participant.rejoined",
            )
        )
        return Response(load_session_snapshot(session.id, viewer_user_id=request.user.id))

    if session.status != GameSession.STATUS_LOBBY:
        return Response(
            {"error": "Session is no longer accepting new players"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    participant_count = session.participants.count()
    if participant_count >= session.template.max_players:
        return Response({"error": "Session is full"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        participant = GameParticipant.objects.create(
            session=session,
            user=request.user,
            display_name=_ensure_unique_display_name(
                session,
                requested_name,
                request.user.username,
            ),
            seat_order=_get_next_seat_order(session),
            is_connected=True,
        )
        transaction.on_commit(
            lambda session_id=session.id: broadcast_session_event(
                session_id,
                "participant.joined",
            )
        )

    return Response(
        load_session_snapshot(participant.session_id, viewer_user_id=request.user.id),
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def network_session_snapshot(request, session_id):
    session = _get_session_for_user(session_id, request.user)
    if session is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(load_session_snapshot(session.id, viewer_user_id=request.user.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_network_session_ready(request, session_id):
    serializer = SessionReadySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    session = _get_session_for_user(session_id, request.user)
    if session is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session.status != GameSession.STATUS_LOBBY:
        return Response(
            {"error": "Ready state can only be changed while the session is in the lobby"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    participant = session.participants.filter(user=request.user).first()
    if participant is None:
        return Response({"error": "Not a session participant"}, status=status.HTTP_403_FORBIDDEN)

    participant.is_ready = serializer.validated_data.get("is_ready", not participant.is_ready)
    participant.save(update_fields=["is_ready", "last_seen_at"])
    transaction.on_commit(
        lambda session_id=session.id: broadcast_session_event(
            session_id,
            "participant.ready_changed",
        )
    )

    return Response(load_session_snapshot(session.id, viewer_user_id=request.user.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_network_session(request, session_id):
    session = (
        GameSession.objects.select_related("template", "host")
        .prefetch_related("participants__user", "template__phases", "template__win_conditions", "template__role_slots__role__abilities__ability")
        .filter(id=session_id)
        .first()
    )
    if session is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session.host_id != request.user.id:
        return Response({"error": "Only the host can start the session"}, status=status.HTTP_403_FORBIDDEN)

    if session.status != GameSession.STATUS_LOBBY:
        return Response({"error": "Session has already started"}, status=status.HTTP_400_BAD_REQUEST)

    participants = list(session.participants.select_related("user").order_by("seat_order", "joined_at"))
    if len(participants) < session.template.min_players:
        return Response(
            {"error": f"Need at least {session.template.min_players} players to start"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(participants) > session.template.max_players:
        return Response(
            {"error": f"Session exceeds max player count of {session.template.max_players}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if any(not participant.is_ready for participant in participants):
        return Response(
            {"error": "All participants must be ready before the game can start"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        engine = build_game_engine(
            session.template,
            [participant.display_name for participant in participants],
        )
        engine.start_game()
        started_state = build_started_session_state(engine, participants)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    players_by_name = {player.name: player for player in engine.players}
    for participant in participants:
        player = players_by_name[participant.display_name]
        participant.role_name = player.role.name
        participant.role_alignment = player.role.alignment.value
        participant.is_alive = player.is_alive
        participant.is_ready = False

    with transaction.atomic():
        GameParticipant.objects.bulk_update(
            participants,
            ["role_name", "role_alignment", "is_alive", "is_ready", "last_seen_at"],
        )
        session.status = GameSession.STATUS_IN_PROGRESS
        session.current_phase = engine.phase_state.value
        session.turn_number = started_state["turn_number"]
        session.started_at = timezone.now()
        session.state_json = started_state
        session.current_phase = started_state["phase"]
        session.save(
            update_fields=[
                "status",
                "current_phase",
                "turn_number",
                "started_at",
                "state_json",
                "updated_at",
            ]
        )
        transaction.on_commit(
            lambda session_id=session.id: broadcast_session_event(
                session_id,
                "session.started",
            )
        )

    return Response(load_session_snapshot(session.id, viewer_user_id=request.user.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_network_session_action(request, session_id):
    serializer = SubmitSessionActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    session = (
        GameSession.objects.select_related("template", "host")
        .prefetch_related("participants__user", "template__win_conditions")
        .filter(id=session_id)
        .first()
    )
    if session is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    participant = session.participants.filter(user=request.user).first()
    if participant is None:
        return Response({"error": "Not a session participant"}, status=status.HTTP_403_FORBIDDEN)

    if session.status != GameSession.STATUS_IN_PROGRESS:
        return Response(
            {"error": "The session is not currently in progress"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session.current_phase != GameSession.PHASE_VOTING:
        return Response(
            {"error": "Votes can only be submitted during the voting phase"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not participant.is_alive:
        return Response(
            {"error": "Eliminated participants cannot vote"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_participant = session.participants.filter(
        id=serializer.validated_data["target_participant_id"]
    ).first()
    if target_participant is None:
        return Response({"error": "Vote target not found"}, status=status.HTTP_404_NOT_FOUND)

    if not target_participant.is_alive:
        return Response(
            {"error": "You can only vote for living participants"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing_vote = session.actions.filter(
        participant=participant,
        phase=GameSession.PHASE_VOTING,
        action_type="VOTE",
        status=GameAction.STATUS_SUBMITTED,
        turn_number=session.turn_number,
    ).first()
    if existing_vote is not None:
        return Response(
            {"error": "You have already locked in your vote for this round"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        GameAction.objects.create(
            session=session,
            participant=participant,
            turn_number=session.turn_number,
            phase=GameSession.PHASE_VOTING,
            action_type="VOTE",
            payload={
                "target_participant_id": target_participant.id,
                "target_display_name": target_participant.display_name,
            },
        )

        state = dict(session.state_json or {})
        vote_state = dict(state.get("vote_state") or {})
        submitted_participant_ids = list(vote_state.get("submitted_participant_ids") or [])
        if participant.id not in submitted_participant_ids:
            submitted_participant_ids.append(participant.id)
        state = record_vote_progress(state, submitted_participant_ids)

        alive_participant_count = session.participants.filter(is_alive=True).count()
        all_votes_submitted = len(submitted_participant_ids) >= alive_participant_count

        participants = list(session.participants.order_by("seat_order", "joined_at"))
        session.state_json = state
        broadcast_reason = "vote.submitted"

        if all_votes_submitted:
            next_state, eliminated_participant, winner_alignment = resolve_voting_round(
                session,
                participants,
            )
            session.state_json = next_state
            session.turn_number = next_state["turn_number"]
            session.current_phase = next_state["phase"]
            update_fields = ["state_json", "turn_number", "current_phase", "updated_at"]

            if eliminated_participant is not None:
                GameParticipant.objects.bulk_update(
                    [participant for participant in participants if participant.id == eliminated_participant.id],
                    ["is_alive", "eliminated_at", "last_seen_at"],
                )

            if winner_alignment:
                session.status = GameSession.STATUS_COMPLETED
                session.ended_at = timezone.now()
                update_fields.extend(["status", "ended_at"])

            session.save(update_fields=update_fields)
            broadcast_reason = "vote.resolved"
        else:
            session.save(update_fields=["state_json", "updated_at"])

        transaction.on_commit(
            lambda session_id=session.id, reason=broadcast_reason: broadcast_session_event(
                session_id,
                reason,
            )
        )

    return Response(load_session_snapshot(session.id, viewer_user_id=request.user.id))


# --- Existing Single-Player Demo Session Views ---

# In-memory store for active demo game sessions
ACTIVE_GAMES = {}


def serialize_game_state(session_id, engine, user_name):
    user_player = engine.get_player(user_name)

    players = []
    for player in engine.players:
        # In the solo demo, roles stay hidden mid-game unless you're viewing your own.
        reveal_role = player.name == user_name or engine.phase_state == PhaseState.GAME_OVER
        players.append(
            {
                "name": player.name,
                "is_alive": player.is_alive,
                "role": player.role.name if reveal_role else "Unknown",
                "alignment": player.role.alignment.value if reveal_role else "Unknown",
            }
        )

    abilities = []
    if user_player and user_player.is_alive and user_player.role.abilities:
        for index, ability in enumerate(user_player.role.abilities):
            abilities.append({"index": index, "name": ability.name, "phase": ability.phase})

    return {
        "session_id": session_id,
        "phase": engine.phase_state.value,
        "turn": engine.turn_number,
        "players": players,
        "me": {
            "name": user_name,
            "is_alive": user_player.is_alive if user_player else False,
            "role": user_player.role.name if user_player else "Observer",
            "alignment": user_player.role.alignment.value if user_player else "Unknown",
            "abilities": abilities,
        },
        "logs": [
            {"type": e["type"], "message": e["message"], "turn": e["turn"]}
            for e in engine.events
            if e["visible_to"] == "all" or user_name in e["visible_to"]
        ],
    }


@api_view(["POST"])
def start_game_session(request):
    template_id = request.data.get("template_id")
    user_name = request.data.get("user_name", "You")

    template = _get_accessible_template(template_id, request.user)
    if template is None:
        return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

    total_slots = sum(slot.count for slot in template.role_slots.all())
    if total_slots < 1:
        return Response({"error": "Template has no roles"}, status=status.HTTP_400_BAD_REQUEST)

    player_names = [user_name] + [f"Bot {index}" for index in range(1, total_slots)]

    engine = build_game_engine(template, player_names)
    engine.start_game()

    session_id = str(uuid.uuid4())
    ACTIVE_GAMES[session_id] = engine

    return Response(serialize_game_state(session_id, engine, user_name))


@api_view(["POST"])
def game_session_action(request, session_id):
    if session_id not in ACTIVE_GAMES:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    engine = ACTIVE_GAMES[session_id]
    user_name = request.data.get("user_name", "You")
    action_data = request.data.get("action", {})
    current_phase = engine.phase_state

    if current_phase == PhaseState.GAME_OVER:
        return Response(serialize_game_state(session_id, engine, user_name))

    user_player = engine.get_player(user_name)
    user_performed_vote = False

    if user_player and user_player.is_alive:
        if action_data:
            if current_phase == PhaseState.VOTING and action_data.get("action") == "vote":
                user_performed_vote = True
            engine.handle_input(user_player.name, action_data)
        elif action_data is None and current_phase == PhaseState.VOTING:
            user_performed_vote = True

    alive_players = engine.get_alive_players()
    should_advance = True

    if current_phase == PhaseState.VOTING:
        if action_data and action_data.get("ability_index") is not None and not user_performed_vote:
            should_advance = False

    if should_advance:
        for bot in alive_players:
            if bot.name == user_name:
                continue

            if current_phase == PhaseState.NIGHT:
                night_abilities = [
                    (index, ability)
                    for index, ability in enumerate(bot.role.abilities)
                    if ability.phase == "NIGHT"
                ]
                if night_abilities:
                    ability_index, _ = night_abilities[0]
                    target = random.choice(alive_players)
                    engine.handle_input(
                        bot.name,
                        {"ability_index": ability_index, "target": target.name},
                    )
            elif current_phase == PhaseState.VOTING:
                voting_abilities = [
                    (index, ability)
                    for index, ability in enumerate(bot.role.abilities)
                    if ability.phase == "VOTING"
                ]
                if voting_abilities:
                    ability_index, _ = voting_abilities[0]
                    target = random.choice(alive_players)
                    engine.handle_input(
                        bot.name,
                        {"ability_index": ability_index, "target": target.name},
                    )

                target = random.choice(alive_players)
                engine.handle_input(
                    bot.name,
                    {"action": "vote", "target": target.name},
                )

        engine.advance_phase()

    return Response(serialize_game_state(session_id, engine, user_name))


def _get_accessible_template(template_id, user):
    try:
        template = GameTemplate.objects.get(id=template_id)
    except GameTemplate.DoesNotExist:
        return None

    if template.is_public:
        return template

    if user.is_authenticated and template.creator_id == user.id:
        return template

    return None


def _get_session_for_user(session_id, user):
    session = (
        GameSession.objects.select_related("template", "host")
        .prefetch_related("participants__user")
        .filter(id=session_id)
        .first()
    )
    if session is None:
        return None

    if session.host_id == user.id:
        return session

    if session.participants.filter(user_id=user.id).exists():
        return session

    return None


def _ensure_unique_display_name(session, requested_name, fallback_name):
    base_name = (requested_name or fallback_name or "Player").strip()[:100]
    base_name = base_name or "Player"

    existing_names = set(
        session.participants.values_list("display_name", flat=True)
    )
    if base_name not in existing_names:
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name[:96]}-{suffix}"
        if candidate not in existing_names:
            return candidate
        suffix += 1


def _get_next_seat_order(session):
    max_value = session.participants.aggregate(max_value=Max("seat_order"))["max_value"]
    return 0 if max_value is None else max_value + 1
