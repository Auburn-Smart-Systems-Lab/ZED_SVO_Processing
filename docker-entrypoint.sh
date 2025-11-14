#!/bin/bash
set -e

echo "Waiting for database to be ready..."
sleep 5

echo "Running migrations..."
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput

echo "Creating superuser if it doesn't exist..."
python3 manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
END

echo "Starting application..."
exec "$@"