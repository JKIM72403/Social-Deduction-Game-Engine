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

[To be documented when implemented]

- lobby:player_joined
- lobby:player_left
- game:phase_change
- game:vote_cast
- game:action_performed
