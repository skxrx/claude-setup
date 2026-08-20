#!/usr/bin/env bash
# SessionStart hook: inject memory relevant to THIS repo and work track.
# Silent when the DB is down or empty — never blocks a session.
set -u
DB_CONTAINER=harness-memory-db

repo=$(git rev-parse --show-toplevel 2>/dev/null | xargs basename 2>/dev/null \
       | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9._-')
branch=$(git branch --show-current 2>/dev/null | tr -cd 'a-zA-Z0-9._/-')
case "$branch" in
  *opensource*) track=opensource ;;
  "")           track= ;;
  *)            track=roadmap ;;
esac

if [ -n "$repo" ]; then
  scope="AND project = '$repo'"
  header="[harness-memory] $repo${track:+ / $track}${branch:+ @$branch}"
  hint="use project='$repo'${track:+, track='$track'} with remember/recall"
else
  scope=""
  header="[harness-memory] recent"
  hint="pass project/track when the work belongs to a repo"
fi

psql() { docker exec "$DB_CONTAINER" psql -U harness -d harness_memory -t -A "$@" 2>/dev/null; }

mem=$(psql -c "SELECT '• ['||coalesce(track, topic)||'] '||left(content, 110)
               FROM memories WHERE superseded_by IS NULL $scope
               ORDER BY created_at DESC LIMIT 6")
cases=$(psql -c "SELECT '• case ['||status||'] '||slug||': '||title
                 FROM investigations WHERE status = 'open'
                 ORDER BY updated_at DESC LIMIT 3")

if [ -n "$mem$cases" ]; then
  echo "$header — $hint"
  [ -n "$mem" ] && echo "$mem"
  [ -n "$cases" ] && echo "$cases"
fi
exit 0
