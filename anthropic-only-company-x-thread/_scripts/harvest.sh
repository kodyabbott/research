#!/bin/bash
# X thread archive harvester -- read-only, app-only bearer auth
set -u
cd /c/Users/kody1/claude/x-archive || exit 1
mkdir -p pages
tok=$(tr -d '\r\n' < "$HOME/.x-bearer-token")
F="tweet.fields=id,text,author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets,public_metrics,note_tweet,entities&expansions=author_id,referenced_tweets.id,in_reply_to_user_id&user.fields=id,name,username,verified"

fetch_paged() {
  # $1 = base url (no pagination), $2 = file prefix, $3 = pagination param name
  local base="$1" prefix="$2" pparam="$3"
  local next="" page=0 code retries=0
  while :; do
    local url="$base"
    [ -n "$next" ] && url="$url&$pparam=$next"
    code=$(curl -s -w "%{http_code}" -o _page.json -H "Authorization: Bearer $tok" "$url")
    if [ "$code" = "429" ]; then
      retries=$((retries+1))
      if [ $retries -gt 20 ]; then echo "$prefix: too many 429s, giving up at page $page next_token=$next"; return 1; fi
      echo "$prefix: 429 at page $((page+1)), sleeping 65s (retry $retries)"
      sleep 65
      continue
    fi
    if [ "$code" != "200" ]; then
      echo "$prefix: HTTP $code at page $((page+1)), stopping. Body:"; cat _page.json; echo
      return 1
    fi
    retries=0
    page=$((page+1))
    cp _page.json "pages/${prefix}_p$(printf %03d $page).json"
    local count
    count=$(jq -r '.meta.result_count // 0' _page.json)
    next=$(jq -r '.meta.next_token // empty' _page.json)
    echo "$prefix: page $page, $count results, next=${next:+yes}${next:-no}"
    [ -z "$next" ] && break
    sleep 3
  done
  return 0
}

echo "=== replies: conversation A (Sholto) ==="
fetch_paged "https://api.x.com/2/tweets/search/recent?query=conversation_id:2088463770318516734&max_results=100&$F" "convA" "next_token"
echo "=== replies: conversation B (Dario) ==="
fetch_paged "https://api.x.com/2/tweets/search/recent?query=conversation_id:2088758816376807762&max_results=100&$F" "convB" "next_token"
echo "=== quotes: Dario 1/2 ==="
fetch_paged "https://api.x.com/2/tweets/2088758816376807762/quote_tweets?max_results=100&$F" "quotes_2088758816376807762" "pagination_token"
echo "=== quotes: Dario 2/2 ==="
fetch_paged "https://api.x.com/2/tweets/2088758819304443967/quote_tweets?max_results=100&$F" "quotes_2088758819304443967" "pagination_token"
echo "=== quotes: Sholto root ==="
fetch_paged "https://api.x.com/2/tweets/2088463770318516734/quote_tweets?max_results=100&$F" "quotes_2088463770318516734" "pagination_token"
echo "=== quotes: Gavin reply ==="
fetch_paged "https://api.x.com/2/tweets/2088611616577253502/quote_tweets?max_results=100&$F" "quotes_2088611616577253502" "pagination_token"
rm -f _page.json
echo "HARVEST DONE"
