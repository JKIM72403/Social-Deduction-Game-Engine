# Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB (or MongoDB Atlas account)

## Backend Setup

cd backend  

**Important:** Make sure your `python3` command points to **Python 3.10 or higher**. You can check this by running `python3 --version`. If it shows 3.9 or lower, you will need to install a newer version (e.g., via Homebrew) and run that specific version (like `python3.12 -m venv venv`).

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
DEBUG=True
SECRET_KEY=your-secret-key
MONGODB_URI=mongodb://localhost:27017/gameengine
