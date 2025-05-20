#!/bin/bash
set -e

# When running inside the postgres container,
# we can just use the postgres command directly
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE orders'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'orders')\gexec
EOSQL