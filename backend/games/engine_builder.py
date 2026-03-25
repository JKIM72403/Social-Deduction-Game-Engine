from .models import RoleTemplate, AbilityTemplate, GameTemplate
from .engine import (
    Role, Ability, KillAbility, ProtectAbility, InvestigateAbility, 
    TrapAbility, VoteStealAbility, DoubleVoteAbility, BlockAbility,
    RoleblockAbility, LookoutAbility, JailAbility, DouseAbility, IgniteAbility, ImmuneKillAbility,
    Alignment, GameEngine, Player
)

def build_ability(ability_template: AbilityTemplate):
    """Factory function to create the correct Ability subclass."""
    atype = ability_template.ability_type
    name = ability_template.name
    
    # Simple mapping based on type
    if atype == "KILL":
        return KillAbility(name, priority=5, phase=ability_template.phase)
    elif atype == "PROTECT":
        return ProtectAbility(name, priority=1, phase=ability_template.phase)
    elif atype == "INVESTIGATE":
        return InvestigateAbility(name, priority=10, phase=ability_template.phase)
    elif atype == "TRAP":
        return TrapAbility(name, priority=0, phase=ability_template.phase)
    elif atype == "BLOCK":
        return BlockAbility(name, priority=0, phase=ability_template.phase)
    elif atype == "VOTE_STEAL":
        return VoteStealAbility(name, priority=10, phase=ability_template.phase)
    elif atype == "DOUBLE_VOTE":
        return DoubleVoteAbility(name, priority=10, phase=ability_template.phase)
    elif atype == "ROLEBLOCK":
        return RoleblockAbility(name, priority=0, phase=ability_template.phase)
    elif atype == "LOOKOUT":
        return LookoutAbility(name, priority=10, phase=ability_template.phase)
    elif atype == "JAIL":
        return JailAbility(name, priority=0, phase=ability_template.phase)
    elif atype == "DOUSE":
        return DouseAbility(name, priority=5, phase=ability_template.phase)
    elif atype == "IGNITE":
        return IgniteAbility(name, priority=5, phase=ability_template.phase)
    elif atype == "IMMUNE_KILL":
        return ImmuneKillAbility(name, priority=5, phase=ability_template.phase)
    else:
        return Ability(name, priority=50, phase=ability_template.phase)

def build_role(role_template: RoleTemplate) -> Role:
    abilities = []
    for ra in role_template.abilities.all():
        abilities.append(build_ability(ra.ability))
    
    # Map alignment string to Enum
    try:
        alignment = Alignment(role_template.alignment)
    except ValueError:
        alignment = Alignment.NEUTRAL
        
    return Role(role_template.name, alignment, abilities)

def build_game_engine(game_template: GameTemplate, player_names: list) -> GameEngine:
    phases = [
        {"name": p.name, "type": p.phase_type}
        for p in game_template.phases.all().order_by('order')
    ]
    
    win_conditions = [
        {
            "name": wc.name,
            "winner_alignment": wc.winner_alignment,
            "criteria": wc.criteria
        }
        for wc in game_template.win_conditions.all()
    ]
    
    engine = GameEngine(phases=phases, win_conditions=win_conditions)
    
    # Collect all roles defined in the template
    available_roles = []
    for slot in game_template.role_slots.all():
        for _ in range(slot.count):
            available_roles.append(build_role(slot.role))
            
    # Assign roles to players (simple shuffle)
    import random
    random.shuffle(available_roles)
    
    # Ensure enough roles
    if len(player_names) > len(available_roles):
        raise ValueError("Not enough roles configured for the number of players.")
        
    for name, role in zip(player_names, available_roles):
        engine.add_player(Player(name, role))
        
    return engine

