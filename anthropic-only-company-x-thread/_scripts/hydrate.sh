#!/bin/bash
# Rehydrate the IDs-only archive into full post objects via the X API v2.
# Usage: bash hydrate.sh ../ids/replies_2088463770318516734.ids.json > replies.json
# Requires a bearer token in ~/.x-bearer-token. Reads are billed per post on
# pay-per-use (~$5/1k at the rates observed Aug 2026). Deleted/protected posts
# hydrate as errors entries -- that loss over time is inherent to the IDs-only model.
set -u
ids_file="$1"
tok=$(tr -d '\r\n' < "$HOME/.x-bearer-token")
F="tweet.fields=id,text,author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets,public_metrics,note_tweet,entities&expansions=author_id,referenced_tweets.id,in_reply_to_user_id&user.fields=id,name,username,verified"
jq -r '.[]' "$ids_file" | paste -sd' ' - | tr ' ' '\n' | awk 'NR%100==1{if(batch)print batch; batch=$0; next}{batch=batch","$0}END{if(batch)print batch}' | while read -r batch; do
  curl -s -H "Authorization: Bearer $tok" "https://api.x.com/2/tweets?ids=$batch&$F"
  echo
  sleep 2
done | jq -s '{data: ([.[].data // []] | add), includes_users: ([.[].includes.users // []] | add | unique_by(.id)), errors: ([.[].errors // []] | add)}'
