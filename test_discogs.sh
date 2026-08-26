#!/bin/bash
# Test Discogs API connectivity with the provided token

TOKEN="eiYupZrrbtloPLJftLNTxsIaEgIIxFDcIQlScPXX"

echo "=== Test 1: Anonymous rate limit check ==="
curl -s -o /dev/null -w "HTTP %{http_code}\n" "https://api.discogs.com/database/search?q=test&type=release&per_page=1"

echo ""
echo "=== Test 2: Authenticated - get user identity ==="
curl -s -H "Authorization: Discogs token=$TOKEN" -H "User-Agent: MusicCollectionApp/1.0" \
  "https://api.discogs.com/oauth/identity" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
echo "=== Test 3: Authenticated - search test ==="
curl -s -H "Authorization: Discogs token=$TOKEN" -H "User-Agent: MusicCollectionApp/1.0" \
  "https://api.discogs.com/database/search?q=beatles&type=release&per_page=3" | python3 -m json.tool 2>/dev/null | head -30

echo ""
echo "=== Test 4: Check rate limits (authenticated) ==="
curl -sI -H "Authorization: Discogs token=$TOKEN" -H "User-Agent: MusicCollectionApp/1.0" \
  "https://api.discogs.com/database/search?q=test" 2>&1 | grep -i "x-discogs-ratelimit"
