# Multiplayer Networking Roadmap

## Current State

The project already has the foundation for multiplayer networking:

- Authenticated lobby creation and joining through `/api/sessions/`.
- Session snapshots through `/api/sessions/{id}/snapshot/`.
- Ready/start controls for hosted sessions.
- Token-authenticated WebSocket connections at `/ws/sessions/{id}/`.
- Broadcast snapshots after session, participant, and vote writes.
- Persistent session, participant, and action records behind the repository layer.
- A multiplayer UI at `SessionLobby.tsx`.

The current multiplayer runtime is intentionally narrow. It is marked as
`MULTIPLAYER_VOTING_DEMO` and starts sessions by skipping directly to voting.
The only network action accepted by the backend is `VOTE`.

The solo/demo path has richer social deduction behavior:

- Night, day, and voting phase classes.
- Role abilities such as kill, protect, investigate, block, trap, double vote,
  vote steal, jail, lookout, douse, ignite, and immune kill.
- Phase advancement and win-condition checks.
- Viewer-specific event visibility.

That solo behavior is not yet persisted or network-authoritative for real
multiplayer.

## Immediate Health Blockers

1. Fix backend test fixtures for alignment IDs.

   The model now stores `RoleTemplate.alignment` as an `Alignment` foreign key,
   but multiple tests still create roles with string values such as `"TOWN"` and
   `"MAFIA"`. The backend test suite currently discovers 28 tests and errors in
   9 of them before multiplayer assertions can run.

2. Confirm frontend build health in the local environment.

   `npm.cmd run build` reaches the Vite config load step but fails with
   `spawn EPERM` when esbuild starts. This looks environmental, not a TypeScript
   contract failure, but it still blocks normal build verification on this
   machine.

3. Decide the source of truth for multiplayer game logic.

   The current solo `GameEngine` mutates in-memory Python objects. Multiplayer
   needs deterministic, persisted, server-authoritative state that can survive
   disconnects, refreshes, and concurrent submissions. The clean path is to move
   the engine semantics into a serializable runtime state instead of trying to
   keep live `GameEngine` objects in memory.

## Definition of Done

Networking is finished when a multiplayer session can:

- Create and join a lobby with a stable join code.
- Track ready, connected, disconnected, eliminated, and observing players.
- Start only with valid player counts and valid role slots.
- Assign roles privately and reveal them only when rules allow.
- Run the configured phase order, not only voting.
- Accept every relevant player action for the current phase.
- Persist pending actions until phase resolution.
- Resolve actions once the phase is complete.
- Broadcast viewer-specific state updates in real time.
- Handle reconnects without losing private role info, submitted actions, phase
  progress, or logs.
- Enforce all rules on the server.
- Resolve win conditions and end the game consistently for every client.
- Pass REST, WebSocket, concurrency, and end-to-end gameplay tests.

## Phase 1: Stabilize Current Multiplayer MVP

Goal: make the existing lobby plus live voting implementation trustworthy before
expanding its scope.

Tasks:

- Update backend tests to create `Alignment` rows and pass FK instances/IDs.
- Add a small test factory layer for alignments, roles, templates, sessions, and
  participants to avoid fixture drift.
- Add or verify database constraints for one submitted action per
  participant/session/turn/phase/action type where needed.
- Ensure stale documentation is updated where it says repository refactors are
  still pending.
- Add a snapshot schema regression test for lobby, in-progress, eliminated, and
  completed states.
- Verify frontend type checks separately from Vite if local esbuild remains
  blocked.

Acceptance criteria:

- Backend tests pass locally.
- Multiplayer voting can be created, joined, started, voted, resolved, and
  completed through REST and WebSocket snapshots.
- No roadmap item depends on ambiguous current-state behavior.

## Phase 2: Design the Network Game State Contract

Goal: define the persisted state shape that replaces the voting-only runtime.

Tasks:

- Extend `GameSession.state_json` beyond `vote_state` to include:
  - `phase`.
  - `phase_index`.
  - `turn_number`.
  - `phase_order`.
  - `players`.
  - `pending_actions`.
  - `resolved_actions`.
  - `status_effects`.
  - `private_logs`.
  - `public_logs`.
  - `last_resolution`.
  - `winner`.
- Decide how to store role data at session start:
  - Snapshot role name, alignment, and abilities onto each participant for
    stable gameplay even if templates are edited later.
  - Store ability identifiers and resolved runtime behavior in state/action
    payloads.
- Define viewer-specific snapshot rules:
  - Own role and ability list visible to self.
  - Other living roles hidden unless rule allows faction knowledge.
  - Eliminated roles revealed based on game rules.
  - Private ability results visible only to intended viewers.
- Version the runtime shape with a `mode` or `schema_version` field.

Acceptance criteria:

- The frontend has a single typed `SessionSnapshot` contract that can drive
  lobby, action, phase, log, and game-over UI.
- The backend can build the same snapshot after a refresh or reconnect without
  relying on in-memory engine objects.

## Phase 3: Generalize Multiplayer Actions

Goal: replace `VOTE`-only network actions with a server-authoritative action
submission protocol.

Tasks:

- Replace or extend `SubmitSessionActionSerializer` with fields such as:
  - `action_type`.
  - `ability_id` or `ability_index`.
  - `target_participant_id`.
  - optional metadata for skip, abstain, or host phase controls.
- Support action types:
  - `USE_ABILITY`.
  - `VOTE`.
  - `SKIP`.
  - `ABSTAIN` if desired.
  - `HOST_ADVANCE` only for moderator-style flows if the rules allow it.
- Validate every action against:
  - session status.
  - current phase.
  - participant membership.
  - alive/dead state.
  - ability ownership.
  - ability phase.
  - target validity.
  - duplicate submission rules.
- Persist submitted actions without immediately mutating game state unless the
  action is meant to be immediate.
- Track per-viewer action status:
  - no action needed.
  - waiting for submission.
  - submitted and locked.
  - phase resolved.

Acceptance criteria:

- The backend rejects impossible or out-of-phase actions.
- The frontend can render an action panel from snapshot metadata instead of
  hard-coded voting-only assumptions.
- Reconnecting clients see whether they already submitted an action.

## Phase 4: Build a Persistent Phase Resolver

Goal: make night/day/voting resolution work for real multiplayer.

Tasks:

- Create a multiplayer runtime/resolver module that can consume persisted
  session state plus submitted `GameAction` rows.
- Port solo engine semantics into pure functions that operate on serializable
  state:
  - start phase.
  - submit action.
  - check phase completion.
  - resolve phase.
  - advance phase.
  - check win conditions.
- Implement phase completion policies:
  - all living players submit required actions.
  - all actionable players submit, others auto-skip.
  - host/moderator advances after discussion phases.
  - optional timeout support later.
- Port ability resolution:
  - priority ordering.
  - kill/protect.
  - investigate.
  - roleblock/block.
  - lookout/visitor tracking.
  - jail.
  - trap.
  - vote steal/double vote.
  - douse/ignite.
  - immune kill/investigation immunity.
- Preserve private/public logs and visibility.
- Update participants after eliminations and deaths.
- Mark actions as applied or rejected with resolution timestamps.

Acceptance criteria:

- A full Night -> Day -> Voting cycle works in multiplayer.
- All mutations happen inside one logical transaction per submission or phase
  resolution.
- Every broadcast snapshot is generated after durable state is written.

## Phase 5: Frontend Multiplayer Play Experience

Goal: make `SessionLobby` become the real multiplayer play screen, or split it
into lobby and game screens using the same session snapshot.

Tasks:

- Render lobby controls only while status is `LOBBY`.
- Render private player panel once status is `IN_PROGRESS`:
  - role.
  - alignment.
  - abilities.
  - alive/eliminated state.
  - submitted action state.
- Render phase-specific controls:
  - night ability selection.
  - day discussion/ready/advance controls.
  - voting ability controls if supported.
  - final vote controls.
  - skip/no-action controls.
- Render public and private logs separately enough to avoid leaking secrets.
- Prevent frontend-only assumptions about action legality. The UI should guide,
  but the backend must still enforce.
- Add reconnect behavior:
  - open socket.
  - request snapshot after reconnect.
  - show stale/disconnected indicator.
  - avoid clearing user selections unnecessarily.

Acceptance criteria:

- Multiple real users can play from lobby through game over in browsers.
- A refresh mid-game restores the player to the correct private state.
- Dead players become observers without being able to submit live actions.

## Phase 6: WebSocket Protocol Hardening

Goal: move from snapshot-only broadcasts to a robust real-time protocol while
keeping snapshots as the recovery path.

Tasks:

- Keep `session.snapshot` for full refresh and recovery.
- Add optional lighter events for responsiveness:
  - `participant.connected`.
  - `participant.disconnected`.
  - `action.submitted`.
  - `phase.changed`.
  - `game.ended`.
- Include a monotonically increasing `revision` or `updated_at` value in
  snapshots so clients can ignore stale/out-of-order messages.
- Add client heartbeat/reconnect strategy.
- Move production channel layer from `InMemoryChannelLayer` to Redis.
- Revisit token-in-query WebSocket auth and document or harden it.

Acceptance criteria:

- Two or more server workers can broadcast to the same room.
- Clients do not regress if WebSocket messages arrive late or are missed.
- REST snapshot fetch remains the canonical recovery mechanism.

## Phase 7: Multiplayer Rule Completeness

Goal: support enough social deduction mechanics to match the template creator
and solo engine.

Tasks:

- Confirm every `AbilityTemplate.ABILITY_TYPES` entry has multiplayer behavior.
- Decide which abilities are MVP-required and which can be disabled in
  multiplayer until implemented.
- Add ability metadata:
  - target rules.
  - self-target allowed.
  - can target dead players.
  - required/optional.
  - priority.
  - phase.
- Improve win-condition evaluation:
  - alignment count.
  - role count.
  - survival.
  - neutral/special role wins such as jester, serial killer, and arsonist if
    those are expected in multiplayer templates.
- Make role/faction information rules explicit:
  - mafia teammates visible to mafia.
  - dead chat or observer behavior if desired.
  - final reveal rules.

Acceptance criteria:

- Templates that can be created in the UI either work in multiplayer or are
  clearly marked unsupported before launch.
- Win/loss state is deterministic and consistent across all clients.

## Phase 8: Concurrency, Recovery, and Production Readiness

Goal: make multiplayer robust under real usage.

Tasks:

- Add tests for concurrent submissions:
  - duplicate action from same participant.
  - last two players submitting simultaneously.
  - vote resolution racing against reconnect.
  - host starting while a participant toggles ready.
- Add Mongo-mode/dual-write tests if Mongo remains part of the deployment plan.
- Add integration tests with two WebSocket clients and one REST actor.
- Add end-to-end browser tests for:
  - host creates lobby.
  - guest joins.
  - both ready.
  - host starts.
  - players submit night actions.
  - players vote.
  - game ends.
- Add operational cleanup:
  - cancel stale lobbies.
  - leave/kick support if needed.
  - host transfer or session cancellation on host disconnect.
  - retention policy for completed sessions.

Acceptance criteria:

- Multiplayer test coverage exercises complete games, not just isolated votes.
- Production deployment uses Redis channel layer or an equivalent shared layer.
- The app tolerates refreshes, reconnects, and common concurrent actions.

## Recommended Implementation Order

1. Fix test fixture alignment breakage.
2. Add factories and snapshot contract tests.
3. Define the multiplayer state schema and snapshot visibility rules.
4. Generalize action submission beyond `VOTE`.
5. Implement persistent phase resolution for one full cycle:
   `NIGHT -> DAY -> VOTING`.
6. Port core abilities in priority order: kill, protect, investigate, vote.
7. Update `SessionLobby` into a full in-game UI.
8. Add WebSocket revision/reconnect handling.
9. Port remaining abilities and special win conditions.
10. Add concurrency and end-to-end multiplayer tests.
11. Switch production channel layer to Redis before any multi-worker deploy.

## Practical MVP Slice

If time is tight, finish this vertical slice first:

- Two to six players.
- Lobby, ready, start, reconnect.
- Private role assignment.
- Night phase with kill/protect/investigate.
- Day phase as discussion plus host/all-ready advance.
- Voting phase with majority elimination.
- Town and Mafia win conditions.
- Full WebSocket snapshots after every state change.
- Backend tests plus one browser flow.

That slice would be a real multiplayer social deduction game. The remaining
abilities and special neutral roles can then be layered onto a working network
runtime instead of stretching the voting demo sideways.
