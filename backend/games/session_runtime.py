from copy import deepcopy
from typing import Any, Mapping

from django.utils import timezone

# Models imported for string constants only — no ORM queries in this module.
from .models import GameAction, GameSession


SUPPORTED_RUNTIME_MODE = "MULTIPLAYER_VOTING_DEMO"


# ---------------------------------------------------------------------------
# Duck-typing helpers: accept both ParticipantDocument dicts and ORM objects.
# ---------------------------------------------------------------------------

def _p_id(participant) -> int:
    return participant["_id"] if isinstance(participant, dict) else participant.id


def _p_attr(participant, attr: str):
    return participant[attr] if isinstance(participant, dict) else getattr(participant, attr)


# ---------------------------------------------------------------------------
# State builders
# ---------------------------------------------------------------------------

def build_started_session_state(engine, participants) -> dict:
    """Build initial session state after game starts.

    ``participants`` may be either ParticipantDocument dicts or ORM objects \u2014
    the ``_p_id``/``_p_attr`` helpers normalise both forms.
    """
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
            "participant_id": _p_id(p),
            "display_name": _p_attr(p, "display_name"),
            "is_alive": _p_attr(p, "is_alive"),
        }
        for p in participants
    ]
    return state


def move_to_open_voting_round(state: dict, participants) -> dict:
    phase_order = state.get("phase_order") or [{"name": "Voting", "type": "VOTING"}]
    if not any(phase.get("type") == GameSession.PHASE_VOTING for phase in phase_order):
        raise ValueError("Templates used for multiplayer sessions must include a voting phase.")

    current_index = state.get("phase_index", 0)
    if (
        0 <= current_index < len(phase_order)
        and phase_order[current_index].get("type") == GameSession.PHASE_VOTING
    ):
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

        append_event(state, f"Skipping {phase_name}")

    raise ValueError("Unable to find the next voting phase for this session.")


def record_vote_progress(state: dict, submitted_participant_ids) -> dict:
    vote_state = deepcopy(state.get("vote_state") or {})
    vote_state["submitted_participant_ids"] = list(submitted_participant_ids)
    vote_state["submitted_count"] = len(submitted_participant_ids)
    state["vote_state"] = vote_state
    return state


def build_vote_result(vote_actions, alive_count: int) -> dict:
    counts: dict = {}
    for action in vote_actions:
        # Support both ActionDocument dicts and ORM action objects.
        payload = action["payload"] if isinstance(action, dict) else action.payload
        target_id = payload.get("target_participant_id")
        target_name = payload.get("target_display_name")
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
    top_targets = [entry for entry in vote_counts if entry["count"] == max_votes]
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


def evaluate_session_winner(win_conditions, participant_docs, turn_number: int):
    """Determine if any win condition is met.

    ``win_conditions`` \u2014 iterable of WinConditionTemplate ORM objects (template
    configuration, loaded by caller).  No DB queries are performed here.
    ``participant_docs`` \u2014 list of ParticipantDocument dicts (or duck-typed objects).
    """
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
                actual_count = sum(
                    1 for p in alive if _p_attr(p, "role_name") == target
                )
                if actual_count != count:
                    met = False
                    break
            elif criterion_type == "ALIGNMENT_COUNT":
                actual_count = sum(
                    1 for p in alive if _p_attr(p, "role_alignment") == target
                )
                if actual_count != count:
                    met = False
                    break
            elif criterion_type == "SURVIVAL":
                if turn_number < count:
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

            return (
                winner_alignment,
                f"WIN CONDITION MET: {wc.name}! {winner_alignment} Victory!",
            )

    return None, ""


def resolve_voting_round(
    repo,
    session_doc: Mapping[str, Any],
    participant_docs: list,
    win_conditions,
) -> tuple:
    """Resolve a completed voting round using the repository + document dicts.

    Returns ``(new_state, eliminated_participant_id, winner_alignment)``.
    ``winner_alignment`` is ``None`` if the game continues.
    ``eliminated_participant_id`` is ``None`` if no elimination occurred.
    """
    alive_participant_docs = [p for p in participant_docs if _p_attr(p, "is_alive")]
    vote_actions = repo.list_actions_for_vote_resolution(
        session_doc["_id"], session_doc["turn_number"]
    )

    state = deepcopy(session_doc.get("state_json") or {})
    result = build_vote_result(vote_actions, len(alive_participant_docs))
    result["turn_number"] = session_doc["turn_number"]
    result["resolved_at"] = timezone.now().isoformat()

    eliminated_participant_id = result.get("eliminated_participant_id")

    # Mark all vote actions as APPLIED via the repository.
    action_ids = [
        (a["_id"] if isinstance(a, dict) else a.id) for a in vote_actions
    ]
    if action_ids:
        repo.bulk_update_actions(
            action_ids,
            status=GameAction.STATUS_APPLIED,
            resolved_at=timezone.now(),
        )

    # Build updated participant list reflecting any elimination.
    updated_participant_docs = []
    for p in participant_docs:
        if eliminated_participant_id is not None and _p_id(p) == eliminated_participant_id:
            copy = dict(p)
            copy["is_alive"] = False
            updated_participant_docs.append(copy)
        else:
            updated_participant_docs.append(p)

    sync_state_players(state, updated_participant_docs)
    vote_state = deepcopy(state.get("vote_state") or {})
    vote_state.update(
        {
            "status": "RESOLVED",
            "submitted_participant_ids": [
                (a["participant_id"] if isinstance(a, dict) else a.participant_id)
                for a in vote_actions
            ],
            "submitted_count": len(vote_actions),
            "last_result": result,
        }
    )
    state["vote_state"] = vote_state
    append_event(state, result["outcome_message"])

    winner_alignment, winner_message = evaluate_session_winner(
        win_conditions,
        updated_participant_docs,
        turn_number=state.get("turn_number", session_doc["turn_number"]),
    )
    if winner_alignment:
        state["phase"] = GameSession.PHASE_GAME_OVER
        append_event(state, winner_message)
        return state, eliminated_participant_id, winner_alignment

    next_state = move_to_open_voting_round(state, updated_participant_docs)
    return next_state, eliminated_participant_id, None


def append_event(state: dict, message: str) -> dict:
    turn_number = state.get("turn_number") or 0
    state.setdefault("events", []).append(f"[Turn {turn_number}] {message}")
    return state


def _open_voting_round(state: dict, participants) -> dict:
    alive_participant_ids = [_p_id(p) for p in participants if _p_attr(p, "is_alive")]
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

