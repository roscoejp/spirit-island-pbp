#!/bin/sh
export PYTHONUNBUFFERED=TRUE
PATH=/home/ubuntu/.local/bin:$PATH
poetry --version
poetry install --no-root
poetry run python3 ./manage.py collectstatic --noinput
poetry run python3 ./manage.py migrate
exec poetry run gunicorn island.wsgi
