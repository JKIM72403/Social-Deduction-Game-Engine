from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from django.utils import timezone

from .engine import (
    Ability,
    BlockAbility,
    DayPhase,
    DouseAbility,
    DoubleVoteAbility,
    GameEngine,
    IgniteAbility,
    ImmuneKillAbility,
    InvestigateAbility,
    JailAbility,
    KillAbility,
    LookoutAbility,
    NightPhase,
    PhaseState,
    Player,
    ProtectAbility,
    Role,
    RoleblockAbility,
    TrapAbility,
    VoteStealAbility,
    VotingPhase,
)
from .models import GameAction, GameSession


SUPPORTED_RUNTIME_MODE = "MULTIPLAYER_FULL_ENGINE"


ABILITY_BUILDERS = {
    "KILL": lambda name, phase: KillAbility(name, priority=5, phase=phase),
    "PROTECT": lambda name, phase: ProtectAbility(name, priority=1, phase=phase),
    "INVESTIGATE": lambda name, phase: InvestigateAbility(name, priority=10, phase=phase),
    "BLOCK": lambda name, phase: BlockAbility(name, priority=0, phase=phase),
    "TRAP": lambda name, phase: TrapAbility(name, priority=0, phase=phase),
    "VOTE_STEAL": lambda name, phase: VoteStealAbility(name, priority=10, phase=phase),
    "DOUBLE_VOTE": lambda name, phase: DoubleVoteAbility(name, priority=10, phase=phase),
    "ROLEBLOCK": lambda name, phase: RoleblockAbility(name, priority=0, phase=phase),
    "LOOKOUT": lambda name, phase: LookoutAbility(name, priority=10, phase=phase),
    "JAIL": lambda name, phase: JailAbility(name, priority=0, phase=phase),
    "DOUSE": lambda name, phase: DouseAbility(name, priority=5, phase=phase),
    "IGNITE": lambda name, phase: IgniteAbility(name, priority=5, phase=phase),
    "IMMUNE_KILL": lambda name, phase: ImmuneKillAbility(name, priority=5, phase=phase),
}


def _p_id(participant) -> int:
    return participant["_id"] if isinstance(participant, dict) else participant.id


def _p_attr(participant, attr: str):
    return participant[attr] if isinstance(participant, dict) else getattr(participant, attr)


def build_started_session_state(engine: GameEngine, participants) -> dict:
    """Build the durable multiplayer state from a freshly-started engine."""
    state = _build_state_from_engine(engine, participants, previous_state=None)
    return record_action_progress(state, participants, [])


def sync_state_players(state: dict, participants) -> dict:
    """Refresh public player liveness without overwriting role metadata."""
    players_by_id = {player["participant_id"]: player for player in state.get("players", [])}
    refreshed = []
    for participant in participants:
        participant_id = _p_id(participant)
        player_state = dict(players_by_id.get(participant_id) or {})
        player_state.update(
            {
                "participant_id": participant_id,
                "display_name": _p_attr(participant, "display_name"),
                "is_alive": _p_attr(participant, "is_alive"),
            }
        )
        refreshed.append(player_state)
    state["players"] = refreshed
    return state


def record_vote_progress(state: dict, submitted_participant_ids) -> dict:
    """Backward-compatible helper for older vote-only tests/callers."""
    vote_state = deepcopy(state.get("vote_state") or {})
    vote_state["submitted_participant_ids"] = list(submitted_participant_ids)
    vote_state["submitted_count"] = len(submitted_participant_ids)
    state["vote_state"] = vote_state
    return state


def record_action_progress(state: dict, participant_docs, phase_actions) -> dict:
    phase = state.get("phase")
    alive_ids = [_p_id(p) for p in participant_docs if _p_attr(p, "is_alive")]
    phase_actions = list(phase_actions)

    if phase == GameSession.PHASE_GAME_OVER:
        state["action_state"] = {
            "status": "CLOSED",
            "required_participant_ids": [],
            "submitted_participant_ids": [],
            "submitted_count": 0,
            "actions_needed": 0,
        }
        return state

    if phase == GameSession.PHASE_VOTING:
        submitted_ids = [
            action["participant_id"]
            for action in phase_actions
            if action["action_type"] == "VOTE"
        ]
        state["vote_state"] = {
            "status": "OPEN",
            "required_participant_ids": alive_ids,
            "submitted_participant_ids": submitted_ids,
            "submitted_count": len(set(submitted_ids)),
            "votes_needed": len(alive_ids),
            "last_result": (state.get("vote_state") or {}).get("last_result"),
        }
    else:
        submitted_ids = [
            action["participant_id"]
            for action in phase_actions
            if action["action_type"] in {"USE_ABILITY", "SKIP"}
        ]

    submitted_unique = sorted(set(submitted_ids))
    state["action_state"] = {
        "status": "OPEN",
        "required_participant_ids": alive_ids,
        "submitted_participant_ids": submitted_unique,
        "submitted_count": len(submitted_unique),
        "actions_needed": len(alive_ids),
    }
    return state


def phase_is_complete(state: dict, participant_docs, phase_actions) -> bool:
    phase = state.get("phase")
    if phase == GameSession.PHASE_GAME_OVER:
        return False

    alive_ids = {_p_id(p) for p in participant_docs if _p_attr(p, "is_alive")}
    if not alive_ids:
        return True

    if any(action["action_type"] == "ADVANCE_PHASE" for action in phase_actions):
        return True

    if phase == GameSession.PHASE_VOTING:
        submitted_ids = {
            action["participant_id"]
            for action in phase_actions
            if action["action_type"] == "VOTE"
        }
    else:
        submitted_ids = {
            action["participant_id"]
            for action in phase_actions
            if action["action_type"] in {"USE_ABILITY", "SKIP"}
        }

    return alive_ids.issubset(submitted_ids)


def apply_and_advance_phase(repo, session_doc: Mapping[str, Any], participant_docs: list) -> dict:
    """Apply submitted phase actions through the existing engine and advance.

    Returns a dict with:
      state: updated session state
      participant_updates: list of (participant_id, fields)
      completed: bool
      action_ids: submitted action IDs that were applied
    """
    state = deepcopy(session_doc.get("state_json") or {})
    phase = session_doc["current_phase"]
    phase_actions = repo.list_submitted_actions_for_phase(
        session_doc["_id"], session_doc["turn_number"], phase
    )
    state = record_action_progress(state, participant_docs, phase_actions)

    if not phase_is_complete(state, participant_docs, phase_actions):
        return {
            "state": state,
            "participant_updates": [],
            "completed": False,
            "resolved": False,
            "action_ids": [],
        }

    engine = _hydrate_engine_from_state(state)
    _apply_actions_to_engine(engine, participant_docs, phase_actions)

    previous_players = {
        player["participant_id"]: player for player in state.get("players", [])
    }
    previous_phase = engine.phase_state.value
    engine.advance_phase()

    new_state = _build_state_from_engine(engine, participant_docs, previous_state=state)
    if previous_phase == GameSession.PHASE_VOTING:
        _attach_vote_result(new_state, previous_players, phase_actions, engine)

    participant_updates = _participant_updates_from_engine(engine, participant_docs)
    updated_participants = _participant_docs_with_engine_liveness(engine, participant_docs)
    new_state = record_action_progress(new_state, updated_participants, [])

    return {
        "state": new_state,
        "participant_updates": participant_updates,
        "completed": engine.phase_state == PhaseState.GAME_OVER,
        "resolved": True,
        "action_ids": [action["_id"] for action in phase_actions],
    }


def evaluate_session_winner(win_conditions, participant_docs, turn_number: int):
    """Kept for compatibility with older tests; the full runtime uses GameEngine."""
    alive = [p for p in participant_docs if _p_attr(p, "is_alive")]

    if not win_conditions:
        mafia_count = sum(1 for p in alive if _p_attr(p, "role_alignment") == "MAFIA")
        town_count = sum(1 for p in alive if _p_attr(p, "role_alignment") == "TOWN")
        if mafia_count == 0:
            return "TOWN", "Town wins!"
        if mafia_count >= town_count and mafia_count > 0:
            return "MAFIA", "Mafia wins!"
        return None, ""

    for wc in win_conditions:
        met = True
        for criterion in wc.criteria:
            criterion_type = criterion.get("type")
            target = criterion.get("target")
            count = criterion.get("count", 0)
            if criterion_type == "ROLE_COUNT":
                actual_count = sum(1 for p in alive if _p_attr(p, "role_name") == target)
            elif criterion_type == "ALIGNMENT_COUNT":
                actual_count = sum(1 for p in alive if _p_attr(p, "role_alignment") == target)
            elif criterion_type == "SURVIVAL":
                actual_count = turn_number
            else:
                continue
            if actual_count != count:
                met = False
                break

        if met:
            winner_alignment = wc.winner_alignment
            if hasattr(winner_alignment, "name"):
                winner_alignment = winner_alignment.name.upper()
            elif isinstance(winner_alignment, str):
                winner_alignment = winner_alignment.upper()
            else:
                winner_alignment = str(winner_alignment).upper()
            return winner_alignment, f"WIN CONDITION MET: {wc.name}! {winner_alignment} Victory!"

    return None, ""


def resolve_voting_round(repo, session_doc, participant_docs, win_conditions):
    """Compatibility shim. New multiplayer resolution goes through apply_and_advance_phase."""
    result = apply_and_advance_phase(repo, session_doc, participant_docs)
    eliminated_id = None
    last_result = (result["state"].get("vote_state") or {}).get("last_result")
    if last_result:
        eliminated_id = last_result.get("eliminated_participant_id")
    winner = result["state"].get("winner")
    return result["state"], eliminated_id, winner


def append_event(state: dict, message: str) -> dict:
    turn_number = state.get("turn_number") or 0
    state.setdefault("events", []).append(f"[Turn {turn_number}] {message}")
    state.setdefault("logs", []).append(
        {
            "type": "system",
            "message": message,
            "turn": turn_number,
            "visible_to": "all",
        }
    )
    return state


def _build_state_from_engine(
    engine: GameEngine,
    participants,
    previous_state: dict | None,
) -> dict:
    participants_by_name = {_p_attr(p, "display_name"): p for p in participants}
    previous_by_id = {
        p["participant_id"]: p for p in (previous_state or {}).get("players", [])
    }

    players = []
    for engine_player in engine.players:
        participant = participants_by_name.get(engine_player.name)
        if participant is None:
            continue
        participant_id = _p_id(participant)
        previous_player = previous_by_id.get(participant_id) or {}
        players.append(
            {
                "participant_id": participant_id,
                "display_name": engine_player.name,
                "is_alive": engine_player.is_alive,
                "role_name": engine_player.role.name,
                "role_alignment": engine_player.role.alignment,
                "abilities": _serialize_abilities(engine_player.role.abilities),
                "status_effects": _json_safe_status_effects(engine_player.status_effects),
                "joined_at": previous_player.get("joined_at"),
            }
        )

    logs = deepcopy(engine.events)
    state = {
        "mode": SUPPORTED_RUNTIME_MODE,
        "phase": engine.phase_state.value,
        "turn_number": engine.turn_number,
        "phase_index": engine.phase_index,
        "phase_order": list(engine.phase_configs),
        "win_conditions": deepcopy(engine.win_condition_configs),
        "players": players,
        "logs": logs,
        "events": [_format_event(event) for event in logs if _is_public_event(event)],
        "doused_players": sorted(getattr(engine, "doused_players", set())),
        "last_lynched": getattr(engine, "last_lynched", None),
        "vote_state": deepcopy((previous_state or {}).get("vote_state") or {}),
        "action_state": {},
    }

    if engine.phase_state == PhaseState.GAME_OVER:
        state["winner"] = _winner_from_logs(logs)

    return state


def _hydrate_engine_from_state(state: dict) -> GameEngine:
    engine = GameEngine(
        phases=state.get("phase_order") or None,
        win_conditions=state.get("win_conditions") or [],
    )
    engine.players = []
    for player_state in state.get("players", []):
        abilities = [
            _ability_from_state(ability_state)
            for ability_state in player_state.get("abilities", [])
        ]
        player = Player(
            player_state["display_name"],
            Role(
                player_state.get("role_name") or "Unknown",
                player_state.get("role_alignment") or "UNKNOWN",
                abilities,
            ),
        )
        player.is_alive = player_state.get("is_alive", True)
        player.status_effects = {}
        engine.add_player(player)

    engine.phase_index = state.get("phase_index", 0)
    engine.phase_state = PhaseState[state.get("phase", GameSession.PHASE_WAITING)]
    engine.turn_number = state.get("turn_number", 1)
    engine.events = deepcopy(state.get("logs") or [])
    engine.doused_players = set(state.get("doused_players") or [])
    engine.last_lynched = state.get("last_lynched")
    engine._started = True
    engine.current_phase = _phase_instance(engine, engine.phase_state)
    return engine


def _phase_instance(engine: GameEngine, phase: PhaseState):
    if phase == PhaseState.DAY:
        return DayPhase(engine)
    if phase == PhaseState.VOTING:
        phase_obj = VotingPhase(engine)
        phase_obj.votes = {}
        phase_obj.pending_actions = []
        return phase_obj
    if phase == PhaseState.NIGHT:
        return NightPhase(engine)
    return None


def _apply_actions_to_engine(engine: GameEngine, participant_docs, phase_actions) -> None:
    participants_by_id = {_p_id(p): p for p in participant_docs}
    for action in phase_actions:
        participant = participants_by_id.get(action["participant_id"])
        if participant is None:
            continue
        actor_name = _p_attr(participant, "display_name")
        payload = action.get("payload") or {}
        if action["action_type"] == "USE_ABILITY":
            target_name = payload.get("target_display_name") or actor_name
            engine.handle_input(
                actor_name,
                {
                    "ability_index": payload.get("ability_index"),
                    "target": target_name,
                },
            )
        elif action["action_type"] == "VOTE":
            target_name = payload.get("target_display_name")
            engine.handle_input(
                actor_name,
                {
                    "action": "vote",
                    "target": target_name,
                },
            )


def _participant_updates_from_engine(engine: GameEngine, participant_docs) -> list[tuple[int, dict]]:
    participants_by_name = {_p_attr(p, "display_name"): p for p in participant_docs}
    updates = []
    for player in engine.players:
        participant = participants_by_name.get(player.name)
        if participant is None:
            continue
        fields = {"is_alive": player.is_alive}
        if not player.is_alive and _p_attr(participant, "is_alive"):
            fields["eliminated_at"] = timezone.now()
        updates.append((_p_id(participant), fields))
    return updates


def _participant_docs_with_engine_liveness(engine: GameEngine, participant_docs) -> list:
    players_by_name = {player.name: player for player in engine.players}
    updated = []
    for participant in participant_docs:
        copy = dict(participant)
        player = players_by_name.get(copy["display_name"])
        if player is not None:
            copy["is_alive"] = player.is_alive
        updated.append(copy)
    return updated


def _serialize_abilities(abilities) -> list[dict]:
    serialized = []
    for index, ability in enumerate(abilities):
        ability_type = getattr(ability, "ability_type", None) or _infer_ability_type(ability)
        serialized.append(
            {
                "index": index,
                "name": ability.name,
                "phase": ability.phase,
                "ability_type": ability_type,
                "target_self": getattr(ability, "target_self", False),
            }
        )
    return serialized


def _ability_from_state(ability_state: dict) -> Ability:
    ability_type = ability_state.get("ability_type") or "UNKNOWN"
    name = ability_state.get("name") or ability_type.title()
    phase = ability_state.get("phase") or GameSession.PHASE_NIGHT
    builder = ABILITY_BUILDERS.get(ability_type)
    ability = builder(name, phase) if builder else Ability(name, priority=50, phase=phase)
    ability.ability_type = ability_type
    ability.target_self = ability_state.get("target_self", getattr(ability, "target_self", False))
    return ability


def _infer_ability_type(ability: Ability) -> str:
    class_name = ability.__class__.__name__.replace("Ability", "")
    mapping = {
        "Kill": "KILL",
        "Protect": "PROTECT",
        "Investigate": "INVESTIGATE",
        "Block": "BLOCK",
        "Trap": "TRAP",
        "VoteSteal": "VOTE_STEAL",
        "DoubleVote": "DOUBLE_VOTE",
        "Roleblock": "ROLEBLOCK",
        "Lookout": "LOOKOUT",
        "Jail": "JAIL",
        "Douse": "DOUSE",
        "Ignite": "IGNITE",
        "ImmuneKill": "IMMUNE_KILL",
    }
    return mapping.get(class_name, class_name.upper())


def _json_safe_status_effects(status_effects: dict) -> dict:
    safe = {}
    for key, value in status_effects.items():
        if isinstance(value, Player):
            safe[key] = value.name
        elif isinstance(value, list):
            safe[key] = [item.name if isinstance(item, Player) else item for item in value]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
    return safe


def _format_event(event: dict) -> str:
    return f"[Turn {event.get('turn', 0)}] {event.get('message', '')}"


def _is_public_event(event: dict) -> bool:
    return event.get("visible_to", "all") == "all"


def _winner_from_logs(logs: list[dict]) -> str | None:
    for event in reversed(logs):
        if event.get("type") == "win":
            message = event.get("message", "")
            if "Town" in message or "TOWN" in message:
                return "TOWN"
            if "Mafia" in message or "MAFIA" in message:
                return "MAFIA"
            if "SERIAL KILLER" in message:
                return "SERIAL KILLER"
            if "ARSONIST" in message:
                return "ARSONIST"
            if "JESTER" in message:
                return "JESTER"
            return message
    return None


def _attach_vote_result(
    state: dict,
    previous_players: dict[int, dict],
    phase_actions,
    engine: GameEngine,
) -> None:
    players_by_name = {player.name: player for player in engine.players}
    eliminated_id = None
    eliminated_name = ""
    for participant_id, old_player in previous_players.items():
        engine_player = players_by_name.get(old_player["display_name"])
        if old_player.get("is_alive") and engine_player and not engine_player.is_alive:
            eliminated_id = participant_id
            eliminated_name = engine_player.name
            break

    counts: dict[int, dict] = {}
    for action in phase_actions:
        if action["action_type"] != "VOTE":
            continue
        payload = action.get("payload") or {}
        target_id = payload.get("target_participant_id")
        if not target_id:
            continue
        entry = counts.setdefault(
            target_id,
            {
                "target_participant_id": target_id,
                "target_display_name": payload.get("target_display_name") or "Unknown",
                "count": 0,
            },
        )
        entry["count"] += 1

    vote_counts = sorted(
        counts.values(),
        key=lambda item: (-item["count"], item["target_display_name"]),
    )
    alive_count = sum(1 for player in previous_players.values() if player.get("is_alive"))
    majority_threshold = (alive_count // 2) + 1 if alive_count > 0 else 0
    if eliminated_id:
        outcome = f"{eliminated_name} was voted out!"
    elif vote_counts:
        outcome = "No one received enough votes."
    else:
        outcome = "No votes were cast."

    state["vote_state"] = {
        "status": "RESOLVED",
        "required_participant_ids": [
            participant_id
            for participant_id, player in previous_players.items()
            if player.get("is_alive")
        ],
        "submitted_participant_ids": [
            action["participant_id"]
            for action in phase_actions
            if action["action_type"] == "VOTE"
        ],
        "submitted_count": len(
            {
                action["participant_id"]
                for action in phase_actions
                if action["action_type"] == "VOTE"
            }
        ),
        "votes_needed": alive_count,
        "last_result": {
            "turn_number": state.get("turn_number"),
            "resolved_at": timezone.now().isoformat(),
            "eliminated_participant_id": eliminated_id,
            "eliminated_display_name": eliminated_name,
            "majority_threshold": majority_threshold,
            "outcome_message": outcome,
            "vote_counts": vote_counts,
        },
    }
