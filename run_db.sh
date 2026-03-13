#!/bin/sh
set -e

docker run \
  -e POSTGRES_DB=linuxfr \
  -e POSTGRES_USER=linuxfr \
  -e POSTGRES_PASSWORD=linuxfr \
  -v linuxfr_pgvector_db:/var/lib/postgresql \
  -p 5432:5432 pgvector/pgvector:pg18-trixie