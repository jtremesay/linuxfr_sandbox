#!/bin/sh
set -ex

exec docker compose up --remove-orphans --build --watch