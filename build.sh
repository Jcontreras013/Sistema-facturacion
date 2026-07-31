#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py ensure_admin

if [ "$SEED_DEMO" = "true" ]; then
    python manage.py seed_demo
fi
