#!/bin/sh
set -ex

until getent hosts db > /dev/null 2>&1; do
  echo "Waiting for db DNS resolution..."
  sleep 1
done

uv run ./manage.py migrate
exec uv run $@ 