#!/bin/bash
# Alert trigger: registers a throwaway user at the app address and tries to create 2 artworks.
# With the fault switch on (ARTMNEME_FAULT=artwork-creation), both fail on the server side and
# "Artwork creations are failing" fires within about 2 minutes. Usage: deploy/trigger-alert.sh [URL]
set -euo pipefail
url=${1:-http://localhost:8000}
email="alert-trigger-$(date +%s)@example.com"
cookie=$(curl -fsS -D - -o /dev/null -H 'Content-Type: application/json' \
  -d "{\"email\": \"$email\", \"password\": \"alert-trigger-1\"}" "$url/api/auth/register" | grep -io 'session=[^;]*')
for attempt in 1 2; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Cookie: $cookie" \
    -F 'artwork={"title": "Alert trigger"}' -F state=WATCHLIST "$url/api/artworks")
  echo "Creation $attempt: HTTP $code"
  [ "$code" = 500 ] || echo "  Not a server error: is the fault switch on? (the alert counts only server-side failures)"
done
