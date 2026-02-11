#!/bin/bash
set -e

echo "Starting Plane API entrypoint script..."

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

# Collect system information for machine signature
HOSTNAME=$(hostname)
MAC_ADDRESS=$(ip link show | awk '/ether/ {print $2}' | head -n 1)
CPU_INFO=$(cat /proc/cpuinfo)
MEMORY_INFO=$(free -h)
DISK_INFO=$(df -h)

# Concatenate information and compute SHA-256 hash
SIGNATURE=$(echo "$HOSTNAME$MAC_ADDRESS$CPU_INFO$MEMORY_INFO$DISK_INFO" | sha256sum | awk '{print $1}')

# Export the variables
export MACHINE_SIGNATURE=$SIGNATURE

# Register instance
python manage.py register_instance "$MACHINE_SIGNATURE"

# Load the configuration variable
python manage.py configure_instance

# Create the default bucket
python manage.py create_bucket

# Clear Cache before starting to remove stale values
python manage.py clear_cache

# Collect static files
python manage.py collectstatic --noinput

echo "Starting gunicorn server..."
exec gunicorn -w "$GUNICORN_WORKERS" -k uvicorn.workers.UvicornWorker plane.asgi:application --bind 0.0.0.0:"${PORT:-8000}" --max-requests 1200 --max-requests-jitter 1000 --access-logfile -
