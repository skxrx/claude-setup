#!/usr/bin/env bash
# Restore a memory DB dump on this machine (e.g. after moving to a new laptop).
#   ./restore.sh harness-memory-YYYYMMDD.sql.gz
set -euo pipefail
[ -f "${1:-}" ] || { echo "usage: ./restore.sh <dump.sql.gz>"; exit 1; }
gunzip -c "$1" | docker exec -i harness-memory-db psql -U harness -d harness_memory -q
echo "restored from $1"
docker exec harness-memory-db psql -U harness -d harness_memory -t -A -c \
  "SELECT 'memories: '||count(*) FROM memories" -c "SELECT 'flows: '||count(*) FROM flows"
