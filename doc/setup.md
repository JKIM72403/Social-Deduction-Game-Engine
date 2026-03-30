# Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+

## Backend Setup

**Important:** Python 3.10+ is required because the project uses structural pattern matching (`match`/`case` statements) and other features introduced in Python 3.10.

Check your Python version:
```bash
python3 --version
```

If it shows 3.9 or lower, install a newer version (e.g., Python 3.12) and use it explicitly:

```bash
cd backend

python3 -m venv venv  
source venv/bin/activate  
pip install -r requirements.txt  
python manage.py migrate  
python manage.py runserver

## Frontend Setup

cd frontend  
nvm use <!-- Only if using nvm -->  
npm i  
npm run dev  

## Environment Variables

Copy the example environment file `.env.example` to create your `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
```

Edit the `.env` file and set your desired values:

```bash
DEBUG=True
SECRET_KEY=your-secret-key-here
```

## Troubleshooting

### Backend Issues

**Problem:** `ModuleNotFoundError` when running Django
**Solution:** Make sure the virtual environment is activated:
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

**Problem:** Database migration errors
**Solution:** Delete `db.sqlite3` and re-run migrations:
```bash
rm db.sqlite3
python manage.py migrate
```

**Problem:** Port 8000 already in use
**Solution:** Either kill the process using port 8000 or run Django on a different port:
```bash
python manage.py runserver 8001
```

### Frontend Issues

**Problem:** `Cannot find module` errors
**Solution:** Delete `node_modules` and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

**Problem:** Port 5173 already in use
**Solution:** Vite will automatically try the next available port, or specify one:
```bash
npm run dev -- --port 3000
```

**Problem:** API connection refused
**Solution:** Ensure backend is running on the correct port and update `VITE_API_URL` in `.env` if needed.

### WebSocket Issues

**Problem:** WebSocket connection fails
**Solution:** 
1. Verify backend is running
2. Check that you're authenticated (logged in)
3. Ensure you're a participant or host of the session
4. Check browser console for specific error codes (4401 = unauthorized, 4404 = not found)
