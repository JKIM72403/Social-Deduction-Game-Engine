# MongoDB Migration Backlog

## Scope

Migrate backend persistence from Django ORM/sqlite to MongoDB while preserving gameplay correctness, websocket consistency, and frontend API contracts.

## Connection Baseline

MongoDB URI template: mongodb+srv://<db_username>:<db_password>@socialdeductiongameengi.fp9bqe.mongodb.net/

Runtime env var: MONGODB_URI

Database name env var: MONGODB_DB_NAME

## Executed Now

| Item | Status | Notes |
| --- | --- | --- |
| Mongo env wiring in settings | DONE | Added USE_MONGODB, MONGODB_URI, MONGODB_DB_NAME, MONGODB_REQUIRE_REPLICA_SET |
| Mongo env template values | DONE | Added to backend/.env.example with provided Atlas URI template |
| Connectivity validator command | DONE | Added python manage.py check_mongodb --require-replica-set |
| Build-time validation gate | DONE | backend/build.sh runs check_mongodb when USE_MONGODB=True |

## Backlog Tickets

| Phase | Ticket | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Phase 2: Data Model Redesign | ID strategy decision | TODO | Canonical string ID strategy chosen and frontend types aligned |
| Phase 2: Data Model Redesign | Document boundary redesign | TODO | Embed/reference map defined for templates, roles, abilities, sessions, participants, actions |
| Phase 2: Data Model Redesign | Constraint map | TODO | Every relational uniqueness rule mapped to Mongo index and app behavior |
| Phase 3: Repository Layer | Repository interface extraction | TODO | Views/session runtime use storage interfaces rather than direct ORM calls |
| Phase 3: Repository Layer | Mongo repository implementation | TODO | CRUD + session/vote operations implemented with duplicate-key handling |
| Phase 3: Repository Layer | Feature-flag backend switch | TODO | USE_MONGODB switches provider without API contract breakage |
| Phase 4: Consistency | Atomic vote submission | TODO | Single vote per participant/turn under concurrency with deterministic errors |
| Phase 4: Consistency | Atomic vote resolution | TODO | State, participant elimination, and action transitions commit as one logical unit |
| Phase 4: Consistency | Event publish reliability | TODO | Explicit publish model replaces implicit transaction.on_commit assumptions |
| Phase 5: Performance | Index bootstrap command | TODO | Idempotent index creation command for all hot paths |
| Phase 5: Performance | Remove N+1 role/template fanout | TODO | Serialization paths avoid join-heavy query patterns |
| Phase 6: Contract and Security | API payload parity | TODO | Snapshot fields and error format are frontend-compatible and stable |
| Phase 6: Contract and Security | WebSocket auth hardening | TODO | Reduce token-in-query risk and document supported auth path |
| Phase 7: Tooling and Cutover | Data export/import pipeline | TODO | Dry-run migration path with invariant checks and rollback plan |
| Phase 7: Tooling and Cutover | Mongo seeding rewrite | TODO | Idempotent default seed behavior without duplicates |
| Phase 7: Tooling and Cutover | Cutover playbook | TODO | Staging rehearsal + production checklist approved |
| Phase 8: Testing and CI | Concurrency test suite | TODO | Race-condition tests cover vote submit/resolve paths |
| Phase 8: Testing and CI | WebSocket ordering tests | TODO | Out-of-order snapshot handling validated |
| Phase 8: Testing and CI | CI matrix for Mongo mode | TODO | Pipeline validates Mongo mode, connectivity, and index prerequisites |

## Recommended Immediate Next Execution

| Priority | Task | Outcome |
| --- | --- | --- |
| 1 | Extract repository interfaces for sessions/participants/actions and refactor submit_network_session_action path | Enables non-ORM backend implementation behind stable endpoint behavior |
| 2 | Add Mongo unique index bootstrap command and wire into deploy/build | Prevents duplicate join codes and participant/session uniqueness violations |
| 3 | Add race-condition tests for duplicate vote submissions | Protects correctness before persistence rewrite |
