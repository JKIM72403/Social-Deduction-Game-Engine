from abc import ABC, abstractmethod
from enum import Enum, auto
import logging
import random
from typing import List, Dict, Optional, Type

logger = logging.getLogger(__name__)

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
            game.log(f"{target.name} was attacked but survived!", "protect", "all")
        else:
            target.is_alive = False
            game.log(f"{target.name} was killed!", "kill", "all")

class ProtectAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["protected"] = True
        game.log(f"{target.name} is protected.", "protect", [source.name])

class InvestigateAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        # Check if target has investigation-immune ability
        is_immune = any(getattr(ab, 'investigation_immune', False) for ab in target.role.abilities)
        if is_immune:
            # Godfather shows as TOWN
            game.log(f"You investigated {target.name}: TOWN", "investigate", [source.name])
        else:
            game.log(f"You investigated {target.name}: {target.role.alignment.value}", "investigate", [source.name])

class BlockAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["blocked"] = True
        game.log(f"You blocked {target.name} from acting!", "ability", [source.name])

class TrapAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["trapped_by"] = source
        game.log(f"You placed a trap at {target.name}'s house.", "ability", [source.name])

class VoteStealAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["vote_stolen"] = True
        game.log(f"You stole {target.name}'s vote!", "ability", [source.name])

class DoubleVoteAbility(Ability):
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["double_vote"] = True
        game.log(f"You gave a double vote effect to {target.name}!", "ability", [source.name])

class RoleblockAbility(Ability):
    def __init__(self, name: str, priority: int = 0, phase: str = "NIGHT"):
        super().__init__(name, priority, phase)
    
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["roleblocked"] = True
        game.log(f"You roleblocked {target.name}!", "ability", [source.name])

class LookoutAbility(Ability):
    def __init__(self, name: str, priority: int = 10, phase: str = "NIGHT"):
        super().__init__(name, priority, phase)
    
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        visitors = target.status_effects.get("visited_by", [])
        if visitors:
            visitor_names = ", ".join([v.name for v in visitors])
            game.log(f"You watched {target.name}. Visitors: {visitor_names}", "ability", [source.name])
        else:
            game.log(f"You watched {target.name}. No visitors.", "ability", [source.name])

class JailAbility(Ability):
    def __init__(self, name: str, priority: int = 0, phase: str = "NIGHT"):
        super().__init__(name, priority, phase)
    
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        target.status_effects["jailed"] = True
        target.status_effects["roleblocked"] = True
        target.status_effects["protected"] = True
        game.log(f"You jailed {target.name}!", "ability", [source.name])
        game.log("You were jailed! You cannot act or be targeted.", "system", [target.name])

class DouseAbility(Ability):
    def __init__(self, name: str, priority: int = 5, phase: str = "NIGHT"):
        super().__init__(name, priority, phase)
    
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        if not hasattr(game, 'doused_players'):
            game.doused_players = set()
        game.doused_players.add(target.name)
        game.log(f"You doused {target.name} in gasoline.", "ability", [source.name])

class IgniteAbility(Ability):
    def __init__(self, name: str, priority: int = 5, phase: str = "NIGHT"):
        super().__init__(name, priority, phase)
        self.target_self = True
    
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        if not hasattr(game, 'doused_players'):
            game.doused_players = set()
        
        if not game.doused_players:
            game.log("No one was doused. The ignition fizzles.", "ability", [source.name])
            return
        
        killed = []
        for player_name in list(game.doused_players):
            player = game.get_player(player_name)
            if player and player.is_alive and not player.status_effects.get("protected"):
                player.is_alive = False
                killed.append(player_name)
        
        game.doused_players.clear()
        if killed:
            killed_str = ", ".join(killed)
            game.log(f"The arsonist ignited their targets! {killed_str} burned!", "kill", "all")
        else:
            game.log("The ignition failed - all targets were protected!", "ability", [source.name])

class ImmuneKillAbility(Ability):
    def __init__(self, name: str, priority: int = 5, phase: str = "NIGHT"):
        super().__init__(name, priority, phase)
        self.investigation_immune = True
    
    def execute(self, source: 'Player', target: 'Player', game: 'GameEngine'):
        if target.status_effects.get("protected") or target.status_effects.get("jailed"):
            game.log(f"{target.name} was attacked but survived!", "protect", "all")
        else:
            target.is_alive = False
            game.log(f"{target.name} was killed!", "kill", "all")

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
        self.game.log("Day breaks. Discussion begins.", "phase_change")
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
                self.game.log(f"Cannot use {ability.name} during DAY phase.", "system", [player_name])
                return

            target = self.game.get_player(target_name) if target_name else player
            if target:
                self.pending_actions.append(Action(player, ability, target))
                self.game.log("You queued a day action.", "ability", [player_name])

class VotingPhase(Phase):
    def start(self):
        self.game.log("Voting has begun. Vote for who to eliminate.", "phase_change")
        for p in self.game.players:
            p.votes_received = 0
            # Reset nightly statuses if they lingered from day
            p.status_effects = {}
        self.votes = {}  # voter_name -> target_name
        self.pending_actions = [] # Actions to manipulate votes before tallying

    def end(self):
        # Resolve any vote-manipulating abilities first
        self.game.log("Resolving vote manipulation abilities...", "system")
        self.pending_actions.sort(key=lambda a: a.ability.priority)
        for action in self.pending_actions:
            if action.source.is_alive:
                action.ability.execute(action.source, action.target, self.game)

        # Tally votes
        if not self.votes:
            self.game.log("No votes cast.", "vote")
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
            self.game.log(f"{net_diff} extra vote(s) were counted!", "vote")
        elif net_diff < 0:
            self.game.log(f"{abs(net_diff)} vote(s) mysteriously went missing!", "vote")

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
                self.game.log(f"{target_player.name} was voted out!", "kill")
                target_player.is_alive = False
                self.game.last_lynched = target_player.name
        else:
            self.game.log("No one received enough votes.", "vote")

    def handle_input(self, player_name: str, data: dict):
        if not data:
            return
        player = self.game.get_player(player_name)
        if not player or not player.is_alive:
            return

        if data.get("action") == "vote":
            target_name = data.get("target")
            self.votes[player_name] = target_name
            self.game.log(f"{player_name} voted for {target_name}.", "vote")

        # Also handle abilities if passed (e.g. Vote Steal, Double Vote)
        ability_idx = data.get("ability_index")
        target_name = data.get("target")
        if ability_idx is not None and 0 <= ability_idx < len(player.role.abilities):
            ability = player.role.abilities[ability_idx]
            if ability.phase != "VOTING":
                self.game.log(f"Cannot use {ability.name} during VOTING phase.", "system", [player_name])
                return

            target = self.game.get_player(target_name) if target_name else player
            if target:
                self.pending_actions.append(Action(player, ability, target))
                self.game.log(f"You used {ability.name}.", "ability", [player_name])

class NightPhase(Phase):
    def __init__(self, game):
        super().__init__(game)
        self.pending_actions: List[Action] = []

    def start(self):
        self.game.log("Night falls. Roles with abilities may act.", "phase_change")
        self.pending_actions = []

    def end(self):
        self.game.log("Night actions are resolving...", "system")
        # Sort by priority
        self.pending_actions.sort(key=lambda a: a.ability.priority)

        # Initialize visit tracking for this night
        for p in self.game.players:
            p.status_effects["visited_by"] = []

        for action in self.pending_actions:
            if not action.source.is_alive:
                continue
            
            # Track visits BEFORE checking blocks (for lookout to see blocked visitors)
            if action.target != action.source:  # Don't track self-visits
                if "visited_by" not in action.target.status_effects:
                    action.target.status_effects["visited_by"] = []
                action.target.status_effects["visited_by"].append(action.source)
            
            # Jailed targets cannot be visited (except by jailor)
            if action.target.status_effects.get("jailed") and action.source != action.target:
                jailed_by_source = False
                # Check if source is the jailor who jailed this target
                for other_action in self.pending_actions:
                    if other_action.source == action.source and isinstance(other_action.ability, JailAbility) and other_action.target == action.target:
                        jailed_by_source = True
                        break
                if not jailed_by_source:
                    continue
            
            # Check if source is roleblocked
            if action.ability.priority > 0 and action.source.status_effects.get("roleblocked"):
                self.game.log("You were blocked and could not perform your action.", "ability", [action.source.name])
                continue

            # Check traps
            if action.ability.priority > 0 and "trapped_by" in action.target.status_effects:
                trapper = action.target.status_effects["trapped_by"]
                self.game.log(f"Your trap caught {action.source.name} visiting {action.target.name}!", "ability", [trapper.name])
                # Continue execution - trap doesn't stop the action, just reveals it

            action.ability.execute(action.source, action.target, self.game)

        # Reset nightly statuses (except doused, which persists on engine)
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
                self.game.log(f"Cannot use {ability.name} during NIGHT phase.", "system", [player_name])
                return

            self.pending_actions.append(Action(player, ability, target))
            self.game.log("You queued a night action.", "ability", [player_name])


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
        self.events: List[dict] = []
        self.turn_number = 1
        self._started = False
        self.doused_players = set()
        self.last_lynched = None

    def add_player(self, player: Player):
        self.players.append(player)

    def get_player(self, name: str) -> Optional[Player]:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def get_alive_players(self) -> List[Player]:
        return [p for p in self.players if p.is_alive]

    def log(self, message: str, event_type: str = "system", visible_to="all"):
        event = {
            "type": event_type,
            "message": message,
            "turn": self.turn_number,
            "visible_to": visible_to,
        }
        self.events.append(event)
        logger.info(f"[Turn {self.turn_number}] [{event_type}] {message}")

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
        self.log(f"Entering {phase_name or new_state.value}", "phase_change")

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
        
        # CHECK NEUTRAL WINS FIRST (higher priority than faction wins)
        
        # Jester win: was lynched (eliminated during voting phase)
        if hasattr(self, 'last_lynched') and self.last_lynched:
            lynched_player = self.get_player(self.last_lynched)
            if lynched_player and lynched_player.role.name == "Jester":
                self.log(f"JESTER WINS! {self.last_lynched} was lynched and achieves their goal!", "win")
                self.phase_state = PhaseState.GAME_OVER
                return
            self.last_lynched = None  # Reset after checking
        
        # Serial Killer win: last one standing
        sk_alive = [p for p in alive if p.role.name == "Serial Killer"]
        if sk_alive and len(alive) == 1:
            self.log("SERIAL KILLER WINS! Only chaos remains.", "win")
            self.phase_state = PhaseState.GAME_OVER
            return
        
        # Arsonist win: last one standing
        arso_alive = [p for p in alive if p.role.name == "Arsonist"]
        if arso_alive and len(alive) == 1:
            self.log("ARSONIST WINS! The town burns to ashes.", "win")
            self.phase_state = PhaseState.GAME_OVER
            return
        
        # THEN CHECK ALIGNMENT-BASED WINS

        # If no win conditions defined, use default fallback
        if not self.win_condition_configs:
            mafia_count = sum(1 for p in alive if p.role.alignment == Alignment.MAFIA)
            town_count = sum(1 for p in alive if p.role.alignment == Alignment.TOWN)
            if mafia_count == 0:
                self.log("Town wins!", "win")
                self.phase_state = PhaseState.GAME_OVER
            elif mafia_count >= town_count:
                self.log("Mafia wins!", "win")
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
                self.log(f"WIN CONDITION MET: {wc.get('name')}! {wc.get('winner_alignment')} Victory!", "win")
                self.phase_state = PhaseState.GAME_OVER
                return

