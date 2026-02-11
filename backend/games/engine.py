from abc import ABC, abstractmethod
from enum import Enum, auto
import random
from typing import List, Dict, Optional, Type

# --- Enums ---

class Alignment(Enum):
    TOWN = "TOWN"
    MAFIA = "MAFIA"
    NEUTRAL = "NEUTRAL"

class PhaseState(Enum):
    WAITING = "WAITING"
    DAY = "DAY"
    VOTING = "VOTING"
    NIGHT = "NIGHT"
    GAME_OVER = "GAME_OVER"

# --- Core Data Classes ---

class Ability:
    def __init__(self, name: str, priority: int, target_self: bool = False):
        self.name = name
        self.priority = priority  # Lower number = earlier execution
        self.target_self = target_self

    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        """Override this for specific ability logic."""
        pass

class KillAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        if target.status_effects.get("protected"):
            game.log(f"{target.name} was attacked but survived!")
        else:
            target.is_alive = False
            game.log(f"{target.name} was killed!")

class ProtectAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["protected"] = True
        game.log(f"{target.name} is protected.")

class InvestigateAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        # In a real game, this info would be sent privately to the source
        game.log(f"{source.name} investigated {target.name}: {target.role.alignment.value}")

class Role:
    def __init__(self, name: str, alignment: Alignment, abilities: List[Ability] = None):
        self.name = name
        self.alignment = alignment
        self.abilities = abilities or []

class Player:
    def __init__(self, name: str, role: Role):
        self.name = name
        self.role = role
        self.is_alive = True
        self.votes_received = 0
        self.status_effects = {}  # e.g., {"protected": True, "framed": False}

    def __str__(self):
        return f"{self.name} ({self.role.name})"

class Action:
    def __init__(self, source: Player, ability: Ability, target: Player):
        self.source = source
        self.ability = ability
        self.target = target

# --- Phase System ---

class Phase(ABC):
    def __init__(self, game: 'GameEngine'):
        self.game = game

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def end(self):
        pass

    @abstractmethod
    def handle_input(self, player_name: str, data: dict):
        pass

class DayPhase(Phase):
    def start(self):
        self.game.log("Day breaks. Discussion begins.")

    def end(self):
        pass

    def handle_input(self, player_name: str, data: dict):
        # Mostly for chat in a real app
        pass

class VotingPhase(Phase):
    def start(self):
        self.game.log("Voting logic initiated. Players can vote for execution.")
        for p in self.game.players:
            p.votes_received = 0
        self.votes = {}  # voter_name -> target_name

    def end(self):
        # Tally votes
        if not self.votes:
            self.game.log("No votes cast.")
            return

        # Simple majority calculation
        counts = {}
        for target in self.votes.values():
            counts[target] = counts.get(target, 0) + 1
        
        # Find max
        max_votes = 0
        candidate = None
        for target, count in counts.items():
            if count > max_votes:
                max_votes = count
                candidate = target
        
        if candidate and max_votes > len(self.game.get_alive_players()) // 2:
            target_player = self.game.get_player(candidate)
            if target_player:
                self.game.log(f"{target_player.name} was voted out!")
                target_player.is_alive = False
        else:
            self.game.log("No one received enough votes.")

    def handle_input(self, player_name: str, data: dict):
        if data.get("action") == "vote":
            target_name = data.get("target")
            self.votes[player_name] = target_name
            self.game.log(f"{player_name} voted for {target_name}")

class NightPhase(Phase):
    def __init__(self, game):
        super().__init__(game)
        self.pending_actions: List[Action] = []

    def start(self):
        self.game.log("Night falls. Roles with abilities may act.")
        self.pending_actions = []

    def end(self):
        self.game.log("Night actions are resolving...")
        # Sort by priority
        self.pending_actions.sort(key=lambda a: a.ability.priority)
        
        for action in self.pending_actions:
            if action.source.is_alive: # Ensure killer didn't die mid-resolution
                action.ability.execute(action.source, action.target, self.game)
        
        # Reset nightly statuses
        for p in self.game.players:
            p.status_effects = {}

    def handle_input(self, player_name: str, data: dict):
        # Expecting data={"ability_index": 0, "target": "Bob"}
        player = self.game.get_player(player_name)
        if not player or not player.is_alive:
            return

        ability_idx = data.get("ability_index")
        target_name = data.get("target")
        target = self.game.get_player(target_name)

        if ability_idx is not None and 0 <= ability_idx < len(player.role.abilities) and target:
            ability = player.role.abilities[ability_idx]
            self.pending_actions.append(Action(player, ability, target))
            self.game.log(f"{player_name} queued an action.")


# --- Main Engine ---

class GameEngine:
    def __init__(self):
        self.players: List[Player] = []
        self.phase_state: PhaseState = PhaseState.WAITING
        self.current_phase: Phase = None
        self.events: List[str] = []
        self.turn_number = 0

    def add_player(self, player: Player):
        self.players.append(player)

    def get_player(self, name: str) -> Optional[Player]:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def get_alive_players(self) -> List[Player]:
        return [p for p in self.players if p.is_alive]

    def log(self, message: str):
        self.events.append(f"[Turn {self.turn_number}] {message}")
        print(f"[Turn {self.turn_number}] {message}")

    def start_game(self):
        self.turn_number = 1
        self.transition_to(PhaseState.NIGHT)

    def transition_to(self, new_state: PhaseState):
        if self.current_phase:
            self.current_phase.end()
            self.check_win_conditions()
            if self.phase_state == PhaseState.GAME_OVER:
                return

        self.phase_state = new_state
        
        if new_state == PhaseState.DAY:
            self.current_phase = DayPhase(self)
        elif new_state == PhaseState.VOTING:
            self.current_phase = VotingPhase(self)
        elif new_state == PhaseState.NIGHT:
            self.turn_number += 1
            self.current_phase = NightPhase(self)
        elif new_state == PhaseState.GAME_OVER:
            self.current_phase = None
            return

        if self.current_phase:
            self.current_phase.start()

    def handle_input(self, player_name: str, data: dict):
        if self.current_phase:
            self.current_phase.handle_input(player_name, data)

    def check_win_conditions(self):
        alive = self.get_alive_players()
        mafia_count = sum(1 for p in alive if p.role.alignment == Alignment.MAFIA)
        town_count = sum(1 for p in alive if p.role.alignment == Alignment.TOWN)
        
        if mafia_count == 0:
            self.log("Town wins!")
            self.phase_state = PhaseState.GAME_OVER
        elif mafia_count >= town_count:
            self.log("Mafia wins!")
            self.phase_state = PhaseState.GAME_OVER

