#!/usr/bin/env bash
# ==============================================================================
# Render Build Script — Django ERP
# ==============================================================================
# This script is executed by Render during every deploy.
# It installs dependencies, collects static files, and runs migrations.
# ==============================================================================

set -o errexit  # Exit on any error

echo ">>> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Collecting static files..."
python manage.py collectstatic --no-input

echo ">>> Running database migrations..."
python manage.py migrate --no-input

echo ">>> Build complete ✓"
