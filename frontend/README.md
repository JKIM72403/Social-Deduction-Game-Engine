# Social Deduction Game Engine - Frontend

React-based frontend for creating, configuring, and playing social deduction games.

## Features

- **Game Creation:** Visual editor for creating custom game templates with roles, abilities, phases, and win conditions
- **Role Management:** Create and customize roles with unique abilities and alignments
- **Multiplayer Lobbies:** Real-time game sessions with join codes
- **Solo Practice Mode:** Play against AI bots to test game configurations
- **Live Gameplay:** Real-time updates via WebSocket connections

## Tech Stack

- **React 19** with TypeScript
- **Vite** for fast development and building
- **Material-UI (MUI)** for UI components
- **React Router** for navigation
- **WebSocket** for real-time game updates

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Environment Variables

Create a `.env` file in the frontend directory:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Project Structure

```
src/
├── components/     # Reusable UI components
├── contexts/       # React Context providers (Auth, etc.)
├── layouts/        # Page layout components
├── pages/          # Route pages
├── services/       # API service functions
├── types.ts        # TypeScript type definitions
└── utils.ts        # Utility functions
```

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
