import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import GameEngine, Player, Role, KillAbility, ProtectAbility, InvestigateAbility, Alignment, PhaseState

def run_demo():
    print("=== Starting Social Deduction Game Engine Demo ===")
    
    # 1. Setup Roles manually (simulating what engine_builder would do)
    mafia_role = Role("Godfather", Alignment.MAFIA, [KillAbility("Hit", 5)])
    doc_role = Role("Doctor", Alignment.TOWN, [ProtectAbility("Heal", 1)])
    cop_role = Role("Sheriff", Alignment.TOWN, [InvestigateAbility("Interrogate", 10)])
    villager_role = Role("Citizen", Alignment.TOWN, [])

    # 2. Setup Engine
    engine = GameEngine()
    engine.add_player(Player("Alice (Mafia)", mafia_role))
    engine.add_player(Player("Bob (Doc)", doc_role))
    engine.add_player(Player("Charlie (Cop)", cop_role))
    engine.add_player(Player("Dave (Civ)", villager_role))

    print(f"Game Initialized with {len(engine.players)} players.")
    for p in engine.players:
        print(f"  - {p}")

    # 3. Start Game
    engine.start_game()
    # Should be Night 1
    
    # --- NIGHT 1 ---
    print(f"\nCurrent Phase: {engine.current_phase.__class__.__name__}")
    
    # Alice attacks Dave
    print("ACTION: Alice tries to kill Dave")
    engine.handle_input("Alice (Mafia)", {"ability_index": 0, "target": "Dave (Civ)"})
    
    # Bob heals Dave
    print("ACTION: Bob tries to heal Dave")
    engine.handle_input("Bob (Doc)", {"ability_index": 0, "target": "Dave (Civ)"})
    
    # Charlie investigates Alice
    print("ACTION: Charlie investigates Alice")
    engine.handle_input("Charlie (Cop)", {"ability_index": 0, "target": "Alice (Mafia)"})
    
    # End Night
    engine.transition_to(PhaseState.DAY)
    
    # Check if Dave survived (should be yes, due to heal)
    dave = engine.get_player("Dave (Civ)")
    print(f"\nDEBUG: Is Dave alive? {dave.is_alive}")
    
    # --- DAY 1 ---
    engine.transition_to(PhaseState.VOTING)
    print(f"\nCurrent Phase: {engine.current_phase.__class__.__name__}")
    
    # Town gathers and suspects Alice
    print("ACTION: Everyone votes for Alice")
    engine.handle_input("Bob (Doc)", {"action": "vote", "target": "Alice (Mafia)"})
    engine.handle_input("Charlie (Cop)", {"action": "vote", "target": "Alice (Mafia)"})
    engine.handle_input("Dave (Civ)", {"action": "vote", "target": "Alice (Mafia)"})
    engine.handle_input("Alice (Mafia)", {"action": "vote", "target": "Bob (Doc)"}) # Self-preservation

    # End Voting - Alice should be eliminated
    engine.transition_to(PhaseState.NIGHT)
    
    alive_mafia = [p for p in engine.get_alive_players() if p.role.alignment == Alignment.MAFIA]
    print(f"\nDEBUG: Mafia alive count: {len(alive_mafia)}")
    
    if engine.phase_state == PhaseState.GAME_OVER:
        print("\n=== GAME OVER ===")
    else:
        print("\nGame continues...")

if __name__ == "__main__":
    run_demo()
