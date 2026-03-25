from copy import deepcopy

from django.utils import timezone

from .models import GameAction, GameParticipant, GameSession


SUPPORTED_RUNTIME_MODE = "MULTIPLAYER_VOTING_DEMO"


def build_started_session_state(engine, participants) -> dict:
    state = {
        "mode": SUPPORTED_RUNTIME_MODE,
        "phase": engine.phase_state.value,
        "turn_number": engine.turn_number,
        "phase_index": engine.phase_index,
        "phase_order": list(engine.phase_configs),
        "events": [f"[Turn {engine.turn_number}] Multiplayer session started."],
        "players": [],
        "vote_state": {},
    }
    sync_state_players(state, participants)
    return move_to_open_voting_round(state, participants)


def sync_state_players(state: dict, participants) -> dict:
    state["players"] = [
        {
            "participant_id": participant.id,
            "display_name": participant.display_name,
            "is_alive": participant.is_alive,
        }
        for participant in participants
    ]
    return state


def move_to_open_voting_round(state: dict, participants) -> dict:
    phase_order = state.get("phase_order") or [{"name": "Voting", "type": "VOTING"}]
    if not any(phase.get("type") == GameSession.PHASE_VOTING for phase in phase_order):
        raise ValueError("Templates used for multiplayer sessions must include a voting phase.")

    current_index = state.get("phase_index", 0)
    if 0 <= current_index < len(phase_order) and phase_order[current_index].get("type") == GameSession.PHASE_VOTING:
        return _open_voting_round(state, participants)

    next_index = current_index
    turn_number = state.get("turn_number", 1) or 1

    for _ in range(len(phase_order) * 2):
        next_index = (next_index + 1) % len(phase_order)
        if next_index == 0:
            turn_number += 1

        phase = phase_order[next_index]
        phase_name = phase.get("name") or phase.get("type") or "phase"
        if phase.get("type") == GameSession.PHASE_VOTING:
            state["phase_index"] = next_index
            state["turn_number"] = turn_number
            state["phase"] = GameSession.PHASE_VOTING
            append_event(state, f"Entering {phase_name}. Cast your votes.")
            return _open_voting_round(state, participants)

        append_event(state, f"Skipping {phase_name} in the multiplayer voting demo.")

    raise ValueError("Unable to find the next voting phase for this session.")


def record_vote_progress(state: dict, submitted_participant_ids) -> dict:
    vote_state = deepcopy(state.get("vote_state") or {})
    vote_state["submitted_participant_ids"] = list(submitted_participant_ids)
    vote_state["submitted_count"] = len(submitted_participant_ids)
    state["vote_state"] = vote_state
    return state


def build_vote_result(vote_actions, alive_count: int) -> dict:
    counts = {}
    for action in vote_actions:
        target_id = action.payload.get("target_participant_id")
        target_name = action.payload.get("target_display_name")
        if not target_id:
            continue

        entry = counts.setdefault(
            target_id,
            {
                "target_participant_id": target_id,
                "target_display_name": target_name or "Unknown",
                "count": 0,
            },
        )
        entry["count"] += 1

    vote_counts = sorted(
        counts.values(),
        key=lambda item: (-item["count"], item["target_display_name"]),
    )
    if not vote_counts:
        return {
            "vote_counts": [],
            "majority_threshold": (alive_count // 2) + 1 if alive_count > 0 else 0,
            "eliminated_participant_id": None,
            "eliminated_display_name": "",
            "outcome_message": "No votes were cast.",
        }

    max_votes = vote_counts[0]["count"]
    top_targets = [
        entry for entry in vote_counts if entry["count"] == max_votes
    ]
    majority_threshold = (alive_count // 2) + 1 if alive_count > 0 else 0

    if len(top_targets) == 1 and max_votes >= majority_threshold:
        return {
            "vote_counts": vote_counts,
            "majority_threshold": majority_threshold,
            "eliminated_participant_id": top_targets[0]["target_participant_id"],
            "eliminated_display_name": top_targets[0]["target_display_name"],
            "outcome_message": f"{top_targets[0]['target_display_name']} was voted out!",
        }

    return {
        "vote_counts": vote_counts,
        "majority_threshold": majority_threshold,
        "eliminated_participant_id": None,
        "eliminated_display_name": "",
        "outcome_message": "No one received enough votes.",
    }


def evaluate_session_winner(session: GameSession, participants, turn_number: int):
    alive_participants = [participant for participant in participants if participant.is_alive]
    win_conditions = list(session.template.win_conditions.all().order_by("order"))

    if not win_conditions:
        mafia_count = sum(
            1 for participant in alive_participants if participant.role_alignment == "MAFIA"
        )
        town_count = sum(
            1 for participant in alive_participants if participant.role_alignment == "TOWN"
        )
        if mafia_count == 0:
            return "TOWN", "Town wins!"
        if mafia_count >= town_count and mafia_count > 0:
            return "MAFIA", "Mafia wins!"
        return None, ""

    for win_condition in win_conditions:
        met = True
        for criterion in win_condition.criteria:
            criterion_type = criterion.get("type")
            target = criterion.get("target")
            count = criterion.get("count", 0)

            if criterion_type == "ROLE_COUNT":
                actual_count = sum(
                    1
                    for participant in alive_participants
                    if participant.role_name == target
                )
                if actual_count != count:
                    met = False
                    break
            elif criterion_type == "ALIGNMENT_COUNT":
                actual_count = sum(
                    1
                    for participant in alive_participants
                    if participant.role_alignment == target
                )
                if actual_count != count:
                    met = False
                    break
            elif criterion_type == "SURVIVAL":
                if turn_number < count:
                    met = False
                    break

        if met:
            return (
                win_condition.winner_alignment,
                f"WIN CONDITION MET: {win_condition.name}! {win_condition.winner_alignment} Victory!",
            )

    return None, ""


def resolve_voting_round(session: GameSession, participants):
    alive_participants = [participant for participant in participants if participant.is_alive]
    vote_actions = list(
        session.actions.select_related("participant")
        .filter(
            phase=GameSession.PHASE_VOTING,
            action_type="VOTE",
            status=GameAction.STATUS_SUBMITTED,
            turn_number=session.turn_number,
        )
        .order_by("submitted_at", "id")
    )

    state = deepcopy(session.state_json or {})
    result = build_vote_result(vote_actions, len(alive_participants))
    result["turn_number"] = session.turn_number
    result["resolved_at"] = timezone.now().isoformat()

    eliminated_participant = None
    if result["eliminated_participant_id"] is not None:
        for participant in participants:
            if participant.id == result["eliminated_participant_id"]:
                participant.is_alive = False
                participant.eliminated_at = timezone.now()
                eliminated_participant = participant
                break

    for action in vote_actions:
        action.status = GameAction.STATUS_APPLIED
        action.resolved_at = timezone.now()

    if vote_actions:
        GameAction.objects.bulk_update(vote_actions, ["status", "resolved_at"])

    sync_state_players(state, participants)
    vote_state = deepcopy(state.get("vote_state") or {})
    vote_state.update(
        {
            "status": "RESOLVED",
            "submitted_participant_ids": [action.participant_id for action in vote_actions],
            "submitted_count": len(vote_actions),
            "last_result": result,
        }
    )
    state["vote_state"] = vote_state
    append_event(state, result["outcome_message"])

    winner_alignment, winner_message = evaluate_session_winner(
        session,
        participants,
        turn_number=state.get("turn_number", session.turn_number),
    )
    if winner_alignment:
        state["phase"] = GameSession.PHASE_GAME_OVER
        append_event(state, winner_message)
        return state, eliminated_participant, winner_alignment

    next_state = move_to_open_voting_round(state, participants)
    return next_state, eliminated_participant, None


def append_event(state: dict, message: str) -> dict:
    turn_number = state.get("turn_number") or 0
    state.setdefault("events", []).append(f"[Turn {turn_number}] {message}")
    return state


def _open_voting_round(state: dict, participants) -> dict:
    alive_participant_ids = [
        participant.id for participant in participants if participant.is_alive
    ]
    last_result = (state.get("vote_state") or {}).get("last_result")
    state["phase"] = GameSession.PHASE_VOTING
    sync_state_players(state, participants)
    state["vote_state"] = {
        "status": "OPEN",
        "required_participant_ids": alive_participant_ids,
        "submitted_participant_ids": [],
        "submitted_count": 0,
        "votes_needed": len(alive_participant_ids),
        "last_result": last_result,
    }
    return state
