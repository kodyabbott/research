#!/bin/bash
# Resume X archive harvest after credit top-up.
# Picks up convA from the saved next_token, then convB and all quotes from scratch.
set -u
cd /c/Users/kody1/claude/x-archive || exit 1
mkdir -p pages
tok=$(tr -d '\r\n' < "$HOME/.x-bearer-token")
F="tweet.fields=id,text,author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets,public_metrics,note_tweet,entities&expansions=author_id,referenced_tweets.id,in_reply_to_user_id&user.fields=id,name,username,verified"

fetch_paged() {
  # $1 base url, $2 prefix, $3 pagination param, $4 start page number, $5 initial token ("" = none)
  local base="$1" prefix="$2" pparam="$3" page="$4" next="$5" code retries=0
  while :; do
    local url="$base"
    [ -n "$next" ] && url="$url&$pparam=$next"
    code=$(curl -s -w "%{http_code}" -o _page.json -H "Authorization: Bearer $tok" "$url")
    if [ "$code" = "429" ]; then
      retries=$((retries+1)); [ $retries -gt 20 ] && { echo "$prefix: too many 429s, stopped. next_token=$next"; return 1; }
      echo "$prefix: 429, sleeping 65s (retry $retries)"; sleep 65; continue
    fi
    if [ "$code" != "200" ]; then
      echo "$prefix: HTTP $code, stopping. next_token=$next Body:"; cat _page.json; echo; return 1
    fi
    retries=0; page=$((page+1))
    cp _page.json "pages/${prefix}_p$(printf %03d $page).json"
    next=$(jq -r '.meta.next_token // empty' _page.json)
    echo "$prefix: page $page, $(jq -r '.meta.result_count // 0' _page.json) results"
    [ -z "$next" ] && break
    sleep 3
  done
}

echo "=== resume convA (from saved token, starting at page 12) ==="
fetch_paged "https://api.x.com/2/tweets/search/recent?query=conversation_id:2088463770318516734&max_results=100&$F" "convA" "next_token" 11 "b26v89c19zqg8o3juewj0yyvcgwap1i09u3zjod70441p"
echo "=== convB (Dario) replies ==="
fetch_paged "https://api.x.com/2/tweets/search/recent?query=conversation_id:2088758816376807762&max_results=100&$F" "convB" "next_token" 0 ""
echo "=== quotes ==="
fetch_paged "https://api.x.com/2/tweets/2088758816376807762/quote_tweets?max_results=100&$F" "quotes_2088758816376807762" "pagination_token" 0 ""
fetch_paged "https://api.x.com/2/tweets/2088758819304443967/quote_tweets?max_results=100&$F" "quotes_2088758819304443967" "pagination_token" 0 ""
fetch_paged "https://api.x.com/2/tweets/2088463770318516734/quote_tweets?max_results=100&$F" "quotes_2088463770318516734" "pagination_token" 0 ""
fetch_paged "https://api.x.com/2/tweets/2088611616577253502/quote_tweets?max_results=100&$F" "quotes_2088611616577253502" "pagination_token" 0 ""
rm -f _page.json
echo "RESUME HARVEST DONE"
