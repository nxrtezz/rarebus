#!/bin/sh

echo "Running migrations..."
python manage.py migrate

echo "Creating admin user..."
python manage.py bootstrap_app

echo "Starting Django..."
exec python manage.py runserver 0.0.0.0:8000