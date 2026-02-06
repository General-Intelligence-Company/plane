#!/bin/bash
set -e

python manage.py wait_for_db
python manage.py migrate

# Run the processes
celery -A plane worker -l info
