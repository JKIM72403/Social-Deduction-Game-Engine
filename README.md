# Social Deduction Game Engine

A web-based game engine for creating, customizing, and playing social deduction games like Mafia and Town of Salem.

## Overview

This platform allows users to:
- Create custom social deduction games with unique roles, abilities, and win conditions
- Host game lobbies with shareable join codes
- Play games online with real-time updates
- Save and share custom game configurations

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript |
| Backend | Django, Python |
| Database | SQLite (Django ORM) |
| Real-time | WebSockets (Django Channels) |

## Project Structure

├── backend/ # Django REST API

├── frontend/ # React application

├── doc/ # Documentation

├── bin/ # Utility scripts

└── sql/ # Database schemas/migrations


## Getting Started
A live build of the project can be found here: [Live Build](https://social-deduction-game-engine.onrender.com/) or  
See [doc/setup.md](doc/setup.md) for setup instructions.

## Documentation

- [Setup Guide](doc/setup.md) - Development environment setup
- [Architecture](doc/architecture.md) - System design overview
- [API Reference](doc/api.md) - Backend API endpoints

## Known Limitations

This is a class project optimized for development and demonstration:

- **Solo Game Persistence:** Solo/demo game sessions are stored in-memory and will be lost on server restart. This is acceptable for single-player practice mode but would need Redis or database persistence for production.
- **Channel Layers:** Currently uses `InMemoryChannelLayer` which only works with a single server instance. Production deployment would require Redis-backed channel layers for horizontal scaling.
- **Database:** Uses SQLite for development. Production deployments should use PostgreSQL or another production-grade database for better performance and concurrent access.
- **Security:** Uses simplified authentication suitable for a class project. Production would need enhanced security measures.

## Team

Carter Buell, Jonathan Kim, Luke Harvison, Jacob Davey, Jake Seals
