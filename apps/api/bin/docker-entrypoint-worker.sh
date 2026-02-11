#!/bin/bash
set -e

python manage.py wait_for_db

# For Railway PR environments, run migrations directly instead of waiting
# This is because PR environments may not have a separate migration job
if [[ "$RAILWAY_ENVIRONMENT_NAME" == *"pr-"* ]]; then
    echo "PR environment detected ($RAILWAY_ENVIRONMENT_NAME). Running migrations directly..."
    python manage.py migrate --noinput
else
    # Wait for migrations (production uses separate migrator service)
    python manage.py wait_for_migrations
fi

# Run the processes
celery -A plane worker -l info