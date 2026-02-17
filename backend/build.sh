#!/usr/bin/env bash
# Render build script for Django backend + React frontend

set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Build React frontend
cd ../frontend
npm install
npm run build
cd ../backend

# Collect static files and migrate database
python manage.py collectstatic --no-input
python manage.py migrate
