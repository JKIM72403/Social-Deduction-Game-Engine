from .models import RoleTemplate, AbilityTemplate, GameTemplate
from .engine import (
    Role, Ability, KillAbility, ProtectAbility, InvestigateAbility, 
    Alignment, GameEngine, Player
)

def build_ability(ability_template: AbilityTemplate):
    """Factory function to create the correct Ability subclass."""
    atype = ability_template.ability_type
    name = ability_template.name
    
    # Simple mapping based on type
    if atype == "KILL":
        return KillAbility(name, priority=5)
    elif atype == "PROTECT":
        return ProtectAbility(name, priority=1)
    elif atype == "INVESTIGATE":
        return InvestigateAbility(name, priority=10)
    else:
        return Ability(name, priority=50)

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
    engine = GameEngine()
    
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

