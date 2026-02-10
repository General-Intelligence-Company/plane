#!/bin/bash
# Railway-specific API entrypoint that runs migrations directly on startup.
# Unlike the standard entrypoint which waits for a separate migrator service,
# this entrypoint runs migrations itself since Railway doesn't have a separate
# migration service in its deployment architecture.
set -e

# Default GUNICORN_WORKERS if not set
export GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"

# Wait for database to be available
python manage.py wait_for_db

# Run migrations directly (instead of waiting for a separate migrator service)
python manage.py migrate

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

exec gunicorn -w "$GUNICORN_WORKERS" -k uvicorn.workers.UvicornWorker plane.asgi:application --bind 0.0.0.0:"${PORT:-8000}" --max-requests 1200 --max-requests-jitter 1000 --access-logfile -
