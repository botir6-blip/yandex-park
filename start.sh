#!/usr/bin/env bash
set -e

SERVICE_TYPE="${SERVICE_TYPE:-admin}"

if [ "$SERVICE_TYPE" = "bot" ]; then
  exec python run_bot.py
else
  exec gunicorn run_admin:app --bind 0.0.0.0:${PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120}
fi
