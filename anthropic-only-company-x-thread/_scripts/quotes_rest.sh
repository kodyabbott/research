#!/bin/bash
set -u
cd /c/Users/kody1/claude/x-archive || exit 1
tok=$(tr -d '\r\n' < "$HOME/.x-bearer-token")
F="tweet.fields=id,text,author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets,public_metrics,note_tweet,entities&expansions=author_id,referenced_tweets.id,in_reply_to_user_id&user.fields=id,name,username,verified"
fetch_paged() {
  local base="$1" prefix="$2" page=0 next="" code retries=0 count
  while :; do
    local url="$base"
    [ -n "$next" ] && url="$url&pagination_token=$next"
    code=$(curl -s -w "%{http_code}" -o _page.json -H "Authorization: Bearer $tok" "$url")
    if [ "$code" = "429" ]; then
      retries=$((retries+1)); [ $retries -gt 20 ] && return 1
      echo "$prefix: 429, sleeping 65s"; sleep 65; continue
    fi
    [ "$code" != "200" ] && { echo "$prefix: HTTP $code, stop"; cat _page.json; echo; return 1; }
    retries=0; page=$((page+1))
    cp _page.json "pages/${prefix}_p$(printf %03d $page).json"
    count=$(jq -r '.meta.result_count // 0' _page.json)
    next=$(jq -r '.meta.next_token // empty' _page.json)
    echo "$prefix: page $page, $count results"
    # stop when pagination degrades to trickle pages
    [ "$count" -le 2 ] && { echo "$prefix: trickle tail, stopping"; break; }
    [ -z "$next" ] && break
    sleep 3
  done
}
fetch_paged "https://api.x.com/2/tweets/2088758819304443967/quote_tweets?max_results=100&$F" "quotes_2088758819304443967"
fetch_paged "https://api.x.com/2/tweets/2088463770318516734/quote_tweets?max_results=100&$F" "quotes_2088463770318516734"
fetch_paged "https://api.x.com/2/tweets/2088611616577253502/quote_tweets?max_results=100&$F" "quotes_2088611616577253502"
rm -f _page.json
echo "QUOTES DONE"
