#!/usr/bin/env bash
# Check the health of the MCADV bot server.
set -euo pipefail

BOT_URL="${BOT_URL:-http://localhost:5000}"
HEALTH_URL="$BOT_URL/api/health"

echo "Checking bot health at: $HEALTH_URL"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$HEALTH_URL")

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "✓ Bot server is healthy (HTTP $HTTP_CODE)"
  exit 0
else
  echo "✗ Bot server returned HTTP $HTTP_CODE (or is unreachable)"
  exit 1
fi
