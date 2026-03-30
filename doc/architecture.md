# System Architecture

## Application Type

Web application (browser-based for both hosts and players)

## Component Overview

+------------------+         +------------------+
|    Frontend      |  REST   |    Backend       |
|  React + TS      |<------->|    Django        |
|                  |   API   |                  |
+------------------+         +--------+---------+
                                      |
                             +--------v---------+
                             |    SQLite DB     |
                             |  (Django ORM)    |
                             +------------------+

## Frontend Responsibilities

- Game creation UI (drag-and-drop role editor)
- Lobby interface
- In-game UI (voting, chat, phase displays)
- Real-time updates via WebSockets

## Backend Responsibilities

- User authentication
- Game logic enforcement
- Game state management
- Custom game configuration storage
- WebSocket connections for real-time gameplay

## Communication Protocol

| Use Case | Protocol |
|----------|----------|
| Authentication | REST API |
| Game creation/saving | REST API |
| Lobby updates | WebSockets |
| Gameplay events | WebSockets |

## Game Modes

The engine supports two distinct gameplay modes:

### Solo Mode (Demo Sessions)
- **Purpose:** Single-player practice with AI bots
- **Storage:** In-memory (ephemeral, not persisted)
- **API Endpoints:** `/api/game-sessions/`
- **Limitations:** Games lost on server restart
- **Use Case:** Testing game configurations, learning roles

### Multiplayer Mode (Network Sessions)
- **Purpose:** Real-time multiplayer with human players
- **Storage:** Database-persisted (GameSession.state_json)
- **API Endpoints:** `/api/sessions/`
- **Real-time:** WebSocket connections for live gameplay
- **Use Case:** Actual gameplay with friends

## Deployment

- Frontend: TBD (AWS Amplify, Vercel, etc.)
- Backend: TBD (AWS EC2, Heroku, etc.)
- Database: SQLite (development), PostgreSQL recommended for production
