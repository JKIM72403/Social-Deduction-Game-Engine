# API Reference

## Base URL

Development: http://localhost:8000/api

## Authentication

### POST /auth/signup
Create a new user account.

### POST /auth/login
Authenticate and receive a token.

### GET /auth/me
Get current user profile.

## Users

### GET /users/{id}
Get user profile by ID.

## Games

### POST /games
Create a new custom game configuration.

### GET /games/{id}
Get game configuration by ID.

### GET /games/user/{userId}
Get all games created by a user.

### PUT /games/{id}
Update a game configuration.

### DELETE /games/{id}
Delete a game configuration.

## Lobby

### POST /lobby
Create a new game lobby.

### GET /lobby/{code}
Get lobby by join code.

### POST /lobby/{code}/join
Join an existing lobby.

### DELETE /lobby/{code}/leave
Leave a lobby.

## WebSocket Events

### Connection

**URL:** `ws://localhost:8000/ws/session/{session_id}/`

**Authentication:** Token-based via query parameter or cookies. The user must be either the host or a participant in the session.

**Connection Flow:**
1. Client connects to WebSocket endpoint
2. Server validates authentication and session access
3. Server sends initial `session.snapshot` with full game state
4. Server broadcasts `session.event` to all connected clients

### Client → Server Events

#### ping
Keep-alive heartbeat.
```json
{
  "type": "ping"
}
```
Response:
```json
{
  "type": "pong"
}
```

#### session.request_snapshot
Request current game state snapshot.
```json
{
  "type": "session.request_snapshot"
}
```
Response: `session.snapshot` event

### Server → Client Events

#### session.snapshot
Full game state update.
```json
{
  "type": "session.snapshot",
  "reason": "connection.accepted" | "manual_refresh" | "participant.connected" | "participant.disconnected" | "game_action",
  "snapshot": {
    "id": 1,
    "host": {...},
    "template": {...},
    "participants": [...],
    "state_json": {...},
    "current_phase": "NIGHT",
    "game_started": true,
    "game_over": false
  }
}
```

#### error
Error message for invalid requests.
```json
{
  "type": "error",
  "message": "Error description"
}
```

### Connection Close Codes

- `4401`: Unauthorized (not authenticated)
- `4404`: Not Found (session doesn't exist or user has no access)
