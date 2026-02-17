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

# Copy frontend build to Django static location
mkdir -p staticfiles
cp -r ../frontend/dist/* staticfiles/ 2>/dev/null || true

# Run migrations
python manage.py migrate

# Collect static files (will include frontend build)
python manage.py collectstatic --no-input --clear

# Seed initial data if needed
python manage.py shell << 'EOF'
from games.models import AbilityTemplate

# Create default abilities if none exist
if not AbilityTemplate.objects.exists():
    AbilityTemplate.objects.create(
        name="Investigate",
        description="Learn the alignment of a player"
    )
    AbilityTemplate.objects.create(
        name="Kill",
        description="Eliminate a player from the game"
    )
    AbilityTemplate.objects.create(
        name="Protect",
        description="Guard a player from being killed"
    )
    AbilityTemplate.objects.create(
        name="Block",
        description="Prevent a player from using their ability"
    )
    print("Seeded initial abilities")
else:
    print("Abilities already exist, skipping seed")
EOF