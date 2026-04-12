#!/usr/bin/env bash
# Render build script for Django backend + React frontend

set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Validate MongoDB connectivity when migration mode is enabled.
if [ "${USE_MONGODB}" = "True" ] || [ "${USE_MONGODB}" = "true" ]; then
    echo "USE_MONGODB enabled. Validating MongoDB connectivity..."
    python manage.py check_mongodb --require-replica-set
    echo "Bootstrapping MongoDB indexes..."
    python manage.py create_mongo_indexes
fi

# Build React frontend
cd ../frontend
npm install
npm run build
cd ../backend

# Run migrations
python manage.py migrate

# Collect static files (will include frontend build)
python manage.py collectstatic --no-input --clear

# Seed default roles, abilities, and alignments
python manage.py seed_defaults