#!/bin/sh
set -ex

exec celery -A linuxfr worker --loglevel=info