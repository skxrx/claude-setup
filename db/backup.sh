#!/usr/bin/env bash
# Dump the memory DB to a portable file (schema + data).
#   ./backup.sh [out.sql.gz]   default: harness-memory-YYYYMMDD.sql.gz
set -euo pipefail
OUT="${1:-harness-memory-$(date +%Y%m%d).sql.gz}"
docker exec harness-memory-db pg_dump -U harness -d harness_memory --no-owner | gzip > "$OUT"
echo "dumped -> $OUT ($(du -h "$OUT" | cut -f1))"
