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
    def __init__(self, name: str, priority: int, phase: str = "NIGHT", target_self: bool = False):
        self.name = name
        self.priority = priority  # Lower number = earlier execution
        self.phase = phase # NIGHT, DAY, or VOTING
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

class BlockAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["blocked"] = True
        game.log(f"{source.name} blocked {target.name} from acting!")

class TrapAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["trapped_by"] = source
        game.log(f"{source.name} strategically placed a trap at {target.name}'s house.")

class VoteStealAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["vote_stolen"] = True
        game.log(f"{source.name} stole {target.name}'s vote!")

class DoubleVoteAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["double_vote"] = True
        game.log(f"{source.name} gave a double vote effect to {target.name}!")

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
    def __init__(self, game):
        super().__init__(game)
        self.pending_actions: List[Action] = []

    def start(self):
        self.game.log("Day breaks. Discussion begins.")
        self.pending_actions = []

    def end(self):
        self.pending_actions.sort(key=lambda a: a.ability.priority)
        for action in self.pending_actions:
            if action.source.is_alive:
                action.ability.execute(action.source, action.target, self.game)

    def handle_input(self, player_name: str, data: dict):
        if not data:
            return
        player = self.game.get_player(player_name)
        if not player or not player.is_alive:
            return

        ability_idx = data.get("ability_index")
        target_name = data.get("target")

        # It's an ability use
        if ability_idx is not None and 0 <= ability_idx < len(player.role.abilities):
            ability = player.role.abilities[ability_idx]
            if ability.phase != "DAY":
                self.game.log(f"DEBUG: {player_name} tried to use {ability.name} ({ability.phase}) during DAY phase.")
                return

            target = self.game.get_player(target_name) if target_name else player
            if target:
                self.pending_actions.append(Action(player, ability, target))
                self.game.log(f"{player_name} queued a day action.")

class VotingPhase(Phase):
    def start(self):
        self.game.log("Voting logic initiated. Players can vote for execution.")
        for p in self.game.players:
            p.votes_received = 0
            # Reset nightly statuses if they lingered from day
            p.status_effects = {}
        self.votes = {}  # voter_name -> target_name
        self.pending_actions = [] # Actions to manipulate votes before tallying

    def end(self):
        # Resolve any vote-manipulating abilities first
        self.game.log("Resolving vote manipulation abilities...")
        self.pending_actions.sort(key=lambda a: a.ability.priority)
        for action in self.pending_actions:
            if action.source.is_alive:
                action.ability.execute(action.source, action.target, self.game)

        # Tally votes
        if not self.votes:
            self.game.log("No votes cast.")
            return

        counts = {}
        missing_votes = 0
        extra_votes = 0

        for voter_name, target in self.votes.items():
            voter = self.game.get_player(voter_name)
            if voter and voter.status_effects.get("vote_stolen"):
                missing_votes += 1
                continue
                
            vote_weight = 1
            if voter and voter.status_effects.get("double_vote"):
                vote_weight = 2
                extra_votes += 1

            counts[target] = counts.get(target, 0) + vote_weight

        net_diff = extra_votes - missing_votes
        if net_diff > 0:
            self.game.log(f"{net_diff} extra vote(s) were counted!")
        elif net_diff < 0:
            self.game.log(f"{abs(net_diff)} vote(s) mysteriously went missing!")

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
        if not data:
            return
        player = self.game.get_player(player_name)
        if not player or not player.is_alive:
            return

        if data.get("action") == "vote":
            target_name = data.get("target")
            self.votes[player_name] = target_name
            self.game.log(f"{player_name} voted for {target_name}")
        
        # Also handle abilities if passed (e.g. Vote Steal, Double Vote)
        ability_idx = data.get("ability_index")
        target_name = data.get("target")
        if ability_idx is not None and 0 <= ability_idx < len(player.role.abilities):
            ability = player.role.abilities[ability_idx]
            if ability.phase != "VOTING":
                self.game.log(f"DEBUG: {player_name} tried to use {ability.name} ({ability.phase}) during VOTING phase.")
                return
            
            target = self.game.get_player(target_name) if target_name else player
            if target:
                self.pending_actions.append(Action(player, ability, target))
                self.game.log(f"{player_name} used an ability ({ability.name}).")

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
                if action.ability.priority > 0 and action.source.status_effects.get("blocked"):
                    self.game.log(f"{action.source.name} was blocked and could not perform their action.")
                    continue

                if action.ability.priority > 0 and "trapped_by" in action.target.status_effects:
                    trapper = action.target.status_effects["trapped_by"]
                    self.game.log(f"[TRAP] {trapper.name} saw {action.source.name} visit {action.target.name} and scared them off!")
                    continue

                action.ability.execute(action.source, action.target, self.game)
        
        # Reset nightly statuses
        for p in self.game.players:
            p.status_effects = {}

    def handle_input(self, player_name: str, data: dict):
        if not data:
            return
        # Expecting data={"ability_index": 0, "target": "Bob"}
        player = self.game.get_player(player_name)
        if not player or not player.is_alive:
            return

        ability_idx = data.get("ability_index")
        target_name = data.get("target")
        target = self.game.get_player(target_name)

        if ability_idx is not None and 0 <= ability_idx < len(player.role.abilities) and target:
            ability = player.role.abilities[ability_idx]
            if ability.phase != "NIGHT":
                self.game.log(f"DEBUG: {player_name} tried to use {ability.name} ({ability.phase}) during NIGHT phase.")
                return

            self.pending_actions.append(Action(player, ability, target))
            self.game.log(f"{player_name} queued an action.")


# --- Main Engine ---

class GameEngine:
    def __init__(self, phases: List[dict] = None, win_conditions: List[dict] = None):
        self.players: List[Player] = []
        self.phase_configs = phases or [
            {"name": "Night", "type": "NIGHT"},
            {"name": "Day", "type": "DAY"},
            {"name": "Voting", "type": "VOTING"},
        ]
        self.win_condition_configs = win_conditions or []
        self.phase_index = -1
        self.phase_state: PhaseState = PhaseState.WAITING
        self.current_phase: Phase = None
        self.events: List[str] = []
        self.turn_number = 1
        self._started = False

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
        self.phase_index = -1
        self.advance_phase()

    def advance_phase(self):
        self.phase_index = (self.phase_index + 1) % len(self.phase_configs)
        config = self.phase_configs[self.phase_index]
        new_state = PhaseState[config['type']]
        
        # Increment turn number when we cycle back to the first phase (index 0)
        # but only if we've already been through at least one phase (index > 0 before increment)
        # Wait, simply increment if it laps.
        if self.phase_index == 0 and hasattr(self, '_started') and self._started:
            self.turn_number += 1
        
        self._started = True
        self.transition_to(new_state, config['name'])

    def transition_to(self, new_state: PhaseState, phase_name: str = None):
        if self.current_phase:
            self.current_phase.end()
            self.check_win_conditions()
            if self.phase_state == PhaseState.GAME_OVER:
                return

        self.phase_state = new_state
        self.log(f"Entering {phase_name or new_state.value}")
        
        if new_state == PhaseState.DAY:
            self.current_phase = DayPhase(self)
        elif new_state == PhaseState.VOTING:
            self.current_phase = VotingPhase(self)
        elif new_state == PhaseState.NIGHT:
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
        
        # If no win conditions defined, use default fallback
        if not self.win_condition_configs:
            mafia_count = sum(1 for p in alive if p.role.alignment == Alignment.MAFIA)
            town_count = sum(1 for p in alive if p.role.alignment == Alignment.TOWN)
            if mafia_count == 0:
                self.log("Town wins!")
                self.phase_state = PhaseState.GAME_OVER
            elif mafia_count >= town_count:
                self.log("Mafia wins!")
                self.phase_state = PhaseState.GAME_OVER
            return

        for wc in self.win_condition_configs:
            met = True
            for criterion in wc.get('criteria', []):
                ctype = criterion.get('type')
                target = criterion.get('target')
                count = criterion.get('count', 0)
                
                if ctype == 'ROLE_COUNT':
                    actual_count = sum(1 for p in alive if p.role.name == target) # Using name for simplicity in engine
                    if actual_count != count:
                        met = False; break
                elif ctype == 'ALIGNMENT_COUNT':
                    actual_count = sum(1 for p in alive if p.role.alignment.value == target)
                    if actual_count != count:
                        met = False; break
                elif ctype == 'SURVIVAL':
                    if self.turn_number < count:
                        met = False; break
            
            if met:
                self.log(f"WIN CONDITION MET: {wc.get('name')}! {wc.get('winner_alignment')} Victory!")
                self.phase_state = PhaseState.GAME_OVER
                return

