#!/bin/sh
set -e

# Схему ведёт alembic; накатываем миграции перед стартом приложения.
alembic upgrade head

exec "$@"
