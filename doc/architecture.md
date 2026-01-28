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
                             |    MongoDB       |
                             |                  |
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

## Deployment

- Frontend: TBD (AWS Amplify, Vercel, etc.)
- Backend: TBD (AWS EC2, Heroku, etc.)
- Database: MongoDB Atlas
