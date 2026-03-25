import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import GameEngine, Player, Role, KillAbility, ProtectAbility, InvestigateAbility, Alignment, PhaseState
from engine import RoleblockAbility, LookoutAbility, JailAbility, DouseAbility, IgniteAbility, ImmuneKillAbility

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

def test_roleblock_scenario():
    """Test that roleblocking prevents kills."""
    print("\n=== TEST: Roleblock Scenario ===")
    
    mafia_role = Role("Mafioso", Alignment.MAFIA, [KillAbility("Hit", 5)])
    consort_role = Role("Consort", Alignment.MAFIA, [RoleblockAbility("Distract", 0)])
    villager_role = Role("Villager", Alignment.TOWN, [])
    
    engine = GameEngine()
    engine.add_player(Player("Alice (Mafia)", mafia_role))
    engine.add_player(Player("Bob (Consort)", consort_role))
    engine.add_player(Player("Charlie (Civ)", villager_role))
    
    engine.start_game()
    
    # Bob roleblocks Alice
    engine.handle_input("Bob (Consort)", {"ability_index": 0, "target": "Alice (Mafia)"})
    # Alice tries to kill Charlie
    engine.handle_input("Alice (Mafia)", {"ability_index": 0, "target": "Charlie (Civ)"})
    
    engine.transition_to(PhaseState.DAY)
    
    charlie = engine.get_player("Charlie (Civ)")
    assert charlie.is_alive, "❌ Charlie should be alive (kill was blocked)"
    print("✅ Roleblock successfully prevented kill")

def test_lookout_scenario():
    """Test that lookout sees visitors."""
    print("\n=== TEST: Lookout Scenario ===")
    
    lookout_role = Role("Lookout", Alignment.TOWN, [LookoutAbility("Watch", 10)])
    doc_role = Role("Doctor", Alignment.TOWN, [ProtectAbility("Heal", 1)])
    mafia_role = Role("Mafioso", Alignment.MAFIA, [KillAbility("Hit", 5)])
    villager_role = Role("Villager", Alignment.TOWN, [])
    
    engine = GameEngine()
    engine.add_player(Player("Alice (Lookout)", lookout_role))
    engine.add_player(Player("Bob (Doc)", doc_role))
    engine.add_player(Player("Charlie (Mafia)", mafia_role))
    engine.add_player(Player("Dave (Civ)", villager_role))
    
    engine.start_game()
    
    # Alice watches Dave
    engine.handle_input("Alice (Lookout)", {"ability_index": 0, "target": "Dave (Civ)"})
    # Bob heals Dave
    engine.handle_input("Bob (Doc)", {"ability_index": 0, "target": "Dave (Civ)"})
    # Charlie attacks Dave
    engine.handle_input("Charlie (Mafia)", {"ability_index": 0, "target": "Dave (Civ)"})
    
    engine.transition_to(PhaseState.DAY)
    
    # Check events for lookout seeing both visitors
    lookout_events = [e for e in engine.events if "Bob (Doc)" in e["message"] and "Charlie (Mafia)" in e["message"]]
    assert len(lookout_events) > 0, "❌ Lookout should have seen visitors"
    print("✅ Lookout successfully detected all visitors")

def test_arsonist_scenario():
    """Test douse + ignite combo."""
    print("\n=== TEST: Arsonist Scenario ===")
    
    arso_role = Role("Arsonist", Alignment.NEUTRAL, [DouseAbility("Douse", 5), IgniteAbility("Ignite", 5)])
    villager_role = Role("Villager", Alignment.TOWN, [])
    
    engine = GameEngine()
    engine.add_player(Player("Alice (Arso)", arso_role))
    engine.add_player(Player("Bob (Civ)", villager_role))
    engine.add_player(Player("Charlie (Civ)", villager_role))
    
    engine.start_game()
    
    # Night 1: Douse Bob
    engine.handle_input("Alice (Arso)", {"ability_index": 0, "target": "Bob (Civ)"})
    engine.transition_to(PhaseState.DAY)
    assert "Bob (Civ)" in engine.doused_players, "❌ Bob should be doused"
    
    # Skip voting
    engine.transition_to(PhaseState.VOTING)
    engine.transition_to(PhaseState.NIGHT)
    
    # Night 2: Douse Charlie
    engine.handle_input("Alice (Arso)", {"ability_index": 0, "target": "Charlie (Civ)"})
    engine.transition_to(PhaseState.DAY)
    assert len(engine.doused_players) == 2, "❌ Both should be doused"
    
    # Skip voting
    engine.transition_to(PhaseState.VOTING)
    engine.transition_to(PhaseState.NIGHT)
    
    # Night 3: IGNITE
    engine.handle_input("Alice (Arso)", {"ability_index": 1, "target": "Alice (Arso)"})
    engine.transition_to(PhaseState.DAY)
    
    bob = engine.get_player("Bob (Civ)")
    charlie = engine.get_player("Charlie (Civ)")
    assert not bob.is_alive, "❌ Bob should be dead from ignite"
    assert not charlie.is_alive, "❌ Charlie should be dead from ignite"
    assert len(engine.doused_players) == 0, "❌ Douse list should be cleared"
    print("✅ Arsonist douse + ignite combo works correctly")

def test_jester_win():
    """Test that Jester wins when lynched."""
    print("\n=== TEST: Jester Win Condition ===")
    
    jester_role = Role("Jester", Alignment.NEUTRAL, [])
    villager_role = Role("Villager", Alignment.TOWN, [])
    mafia_role = Role("Mafioso", Alignment.MAFIA, [KillAbility("Hit", 5)])
    
    engine = GameEngine()
    engine.add_player(Player("Alice (Jester)", jester_role))
    engine.add_player(Player("Bob (Civ)", villager_role))
    engine.add_player(Player("Charlie (Civ)", villager_role))
    engine.add_player(Player("Dave (Mafia)", mafia_role))
    
    engine.start_game()
    engine.transition_to(PhaseState.DAY)
    engine.transition_to(PhaseState.VOTING)
    
    # Everyone votes for Jester
    engine.handle_input("Bob (Civ)", {"action": "vote", "target": "Alice (Jester)"})
    engine.handle_input("Charlie (Civ)", {"action": "vote", "target": "Alice (Jester)"})
    engine.handle_input("Dave (Mafia)", {"action": "vote", "target": "Alice (Jester)"})
    
    engine.transition_to(PhaseState.NIGHT)
    
    assert engine.phase_state == PhaseState.GAME_OVER, "❌ Game should be over (Jester win)"
    win_events = [e for e in engine.events if "JESTER WINS" in e["message"]]
    assert len(win_events) > 0, "❌ Jester win message should appear"
    print("✅ Jester win condition triggered correctly")

def test_godfather_immunity():
    """Test that Godfather appears as TOWN when investigated."""
    print("\n=== TEST: Godfather Investigation Immunity ===")
    
    gf_role = Role("Godfather", Alignment.MAFIA, [ImmuneKillAbility("Hit", 5)])
    cop_role = Role("Sheriff", Alignment.TOWN, [InvestigateAbility("Interrogate", 10)])
    villager_role = Role("Villager", Alignment.TOWN, [])
    
    engine = GameEngine()
    engine.add_player(Player("Alice (GF)", gf_role))
    engine.add_player(Player("Bob (Cop)", cop_role))
    engine.add_player(Player("Charlie (Civ)", villager_role))
    
    engine.start_game()
    
    # Bob investigates Alice (Godfather)
    engine.handle_input("Bob (Cop)", {"ability_index": 0, "target": "Alice (GF)"})
    engine.transition_to(PhaseState.DAY)
    
    # Check investigation result
    invest_events = [e for e in engine.events if "Alice (GF)" in e["message"] and "TOWN" in e["message"]]
    assert len(invest_events) > 0, "❌ Godfather should appear as TOWN to investigator"
    print("✅ Godfather investigation immunity works")

def test_jail_protection():
    """Test that jailed players cannot be killed."""
    print("\n=== TEST: Jail Protection ===")
    
    jailor_role = Role("Jailor", Alignment.TOWN, [JailAbility("Jail", 0)])
    mafia_role = Role("Mafioso", Alignment.MAFIA, [KillAbility("Hit", 5)])
    villager_role = Role("Villager", Alignment.TOWN, [])
    
    engine = GameEngine()
    engine.add_player(Player("Alice (Jailor)", jailor_role))
    engine.add_player(Player("Bob (Mafia)", mafia_role))
    engine.add_player(Player("Charlie (Civ)", villager_role))
    
    engine.start_game()
    
    # Alice jails Charlie
    engine.handle_input("Alice (Jailor)", {"ability_index": 0, "target": "Charlie (Civ)"})
    # Bob tries to kill Charlie
    engine.handle_input("Bob (Mafia)", {"ability_index": 0, "target": "Charlie (Civ)"})
    
    engine.transition_to(PhaseState.DAY)
    
    charlie = engine.get_player("Charlie (Civ)")
    assert charlie.is_alive, "❌ Jailed player should survive attack"
    print("✅ Jail protection works correctly")

if __name__ == "__main__":
    run_demo()
    test_roleblock_scenario()
    test_lookout_scenario()
    test_arsonist_scenario()
    test_jester_win()
    test_godfather_immunity()
    test_jail_protection()
    print("\n✅✅✅ ALL TESTS PASSED ✅✅✅")
