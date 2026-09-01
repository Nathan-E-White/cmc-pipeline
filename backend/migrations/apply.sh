#!/usr/bin/env sh
set -eu

# Baseline legacy databases that predate schema_migrations without replaying 0001.
export PGPASSWORD="${POSTGRES_PASSWORD}"
psql_base="psql -v ON_ERROR_STOP=1 -h ${POSTGRES_HOST} -U ${POSTGRES_USER} -d ${POSTGRES_DB}"
sh -c "${psql_base} -c 'CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())'"

for migration in /migrations/[0-9]*.sql; do
  filename=$(basename "${migration}")
  if ! sh -c "${psql_base} -tAc \"SELECT 1 FROM schema_migrations WHERE filename = '${filename}'\"" | grep -q 1; then
    if [ "${filename}" = "0001_run_mirror.sql" ] && sh -c "${psql_base} -tAc \"SELECT to_regclass('public.case_cards')\"" | grep -q case_cards; then
      sh -c "${psql_base} -c \"INSERT INTO schema_migrations (filename) VALUES ('${filename}')\""
      continue
    fi
    sh -c "${psql_base} -f '${migration}'"
    sh -c "${psql_base} -c \"INSERT INTO schema_migrations (filename) VALUES ('${filename}')\""
  fi
done
