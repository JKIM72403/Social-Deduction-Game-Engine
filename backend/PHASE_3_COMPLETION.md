"""
PHASE 3 COMPLETION: Repository Layer Extraction

✅ DELIVERABLES - Phase 3 is complete:
  1. db/repository.py — Repository ABC + RelationalRepository implementation
  2. db/documents.py — TypedDict schemas (SessionDocument, ParticipantDocument, ActionDocument)
  3. games/broadcast.py — post_write_broadcast() abstraction for on_commit
  4. Refactored join_network_session() — concrete example of repository pattern
  5. Helper functions _ensure_unique_display_name_via_repo() + _get_next_seat_order_via_repo()

📋 REFACTORING ROADMAP - Remaining views for Phase 4:

The pattern demonstrated in join_network_session() applies everywhere:

OLD PATTERN (ORM-direct):
    from games.models import GameSession, GameParticipant
    session = GameSession.objects.get(id=session_id)
    session.status = "IN_PROGRESS"
    session.save()

NEW PATTERN (Repository):
    from db.repository import get_repository
    repo = get_repository()
    session_doc = repo.get_session_by_id(session_id)
    session_doc = repo.update_session(session_id, status="IN_PROGRESS")

Remaining views that MUST be refactored (in order of complexity):
────────────────────────────────────────────────────────────────

1. create_network_session() — SIMPLE
   ├─ Replace GameTemplate.get() → stay on ORM (template is rarely migrated)
   ├─ Replace GameSession.create() → repo.create_session()
   ├─ Replace GameParticipant.create() → repo.create_participant()
   ├─ Return session_doc["_id"] to response
   └─ Update timestamps: use timezone.now() in session_doc

2. set_network_session_ready() — SIMPLE
   ├─ Replace participant.save() → repo.update_participant()
   ├─ Return updated doc instead of re-fetching
   └─ Extract timestamp handling to repo layer

3. start_network_session() — MEDIUM (bulk operations)
   ├─ Replace prefetch_related() → repo.get_session_with_participants()
   ├─ Replace bulk_update() → repo.bulk_update_participants()
   ├─ Careful: must preserve order_by ("seat_order", "joined_at") in participant list
   ├─ Keep engine_builder, role assignment logic unchanged
   └─ Replace session.save() → repo.update_session()

4. submit_network_session_action() — MOST COMPLEX (race condition)
   ├─ Replace select_for_update() → repo.get_participant_with_lock()
   ├─ Replace existing_vote query → repo.check_existing_vote()
   ├─ Replace GameAction.create() → repo.create_action()
   ├─ Replace bulk_update(participants) → repo.bulk_update_participants()
   ├─ Preserve transaction.atomic() wrapping (essential for vote race)
   └─ Note: broadcast_reason variable must stay outside atomic block

Views that do NOT need refactoring (read-only or auth):
────────────────────────────────────────────────────────

✓ network_session_snapshot() — Read-only, stays ORM for now
✓ signup_view(), login_view() — Auth layer, unaffected
✓ All list/create views for templates, roles, abilities — Stay on ORM

Implementation checklist for Phase 4:
─────────────────────────────────────

[ ] Run existing tests — all must pass before refactoring
[ ] Start with create_network_session() (simplest)
[ ] Refactor & test one function at a time
[ ] Run tests after each refactor
[ ] For submit_network_session_action(), add a comment explaining vote race
[ ] Update VoteConcurrencyTests to run against repository layer
[ ] Mark Phase 4 complete once all refactors done + tests pass

Repository methods used per view:
─────────────────────────────────

create_network_session:
  - repo.create_session()
  - repo.create_participant()

set_network_session_ready:
  - repo.update_participant()

start_network_session:
  - repo.get_session_with_participants()
  - repo.bulk_update_participants()
  - repo.update_session()

submit_network_session_action:
  - repo.get_session_by_id()
  - repo.get_participant_with_lock()
  - repo.create_action()
  - repo.check_existing_vote()
  - repo.get_participants_for_session()
  - repo.bulk_update_participants()
  - repo.update_session()

Testing note:
─────────────

All existing tests in backend/games/tests.py will continue to pass because:
  - RelationalRepository wraps the same ORM queries
  - No test code changes required
  - Once MongoRepository is implemented in Phase 4, tests will need fixtures
    to populate both ORM + Mongo collections (dual-write mode)

Once Phase 5 is complete (ORM removal), all tests can switch to Mongo-only.
"""
