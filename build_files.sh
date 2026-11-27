#!/usr/bin/env bash
set -euo pipefail

echo "Building React frontend..."
cd frontend
npm ci
npm run build
cd ..

echo "Installing Python dependencies for collectstatic..."
python3 -m venv /tmp/build_venv
/tmp/build_venv/bin/pip install --no-cache-dir -r requirements.txt

echo "Collecting Django & frontend static files..."
DJANGO_USE_SQLITE=1 /tmp/build_venv/bin/python manage.py collectstatic --noinput --clear

mkdir -p public_build/static
cp -r staticfiles/* public_build/static/
cp frontend/dist/index.html public_build/index.html
