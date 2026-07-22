#!/bin/sh
#  entrypoint for nas-reader
#  1. run database migrations
#  2. start uvicorn (exec replaces shell so signals work correctly)

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
