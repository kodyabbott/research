#!/bin/bash
# Merge harvested pages into final deduped JSON files
set -u
cd /c/Users/kody1/claude/x-archive || exit 1

merge_data() { # $1 = glob prefix, $2 = output file
  local files=(pages/$1_p*.json)
  if [ ! -e "${files[0]}" ]; then echo "[] (no pages for $1)"; echo "[]" > "$2"; return; fi
  jq -s '[.[] | .data[]?] | unique_by(.id)' "${files[@]}" > "$2"
  echo "$2: $(jq 'length' "$2") posts from ${#files[@]} pages"
}

merge_data convA replies_2088463770318516734.json
merge_data convB replies_2088758816376807762.json
merge_data quotes_2088758816376807762 quotes_2088758816376807762.json
merge_data quotes_2088758819304443967 quotes_2088758819304443967.json
merge_data quotes_2088463770318516734 quotes_2088463770318516734.json
merge_data quotes_2088611616577253502 quotes_2088611616577253502.json

# users.json: merge includes.users from every page plus roots
jq -s '[.[] | (.includes.users[]?), (.includes_users[]?)] | unique_by(.id)' pages/*.json roots.json > users.json
echo "users.json: $(jq 'length' users.json) unique users"

# manifest
jq -n \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --slurpfile ra replies_2088463770318516734.json \
  --slurpfile rb replies_2088758816376807762.json \
  --slurpfile q1 quotes_2088758816376807762.json \
  --slurpfile q2 quotes_2088758819304443967.json \
  --slurpfile q3 quotes_2088463770318516734.json \
  --slurpfile q4 quotes_2088611616577253502.json \
  --slurpfile u users.json \
  --arg pagesA "$(ls pages/convA_p*.json 2>/dev/null | wc -l | tr -d ' ')" \
  --arg pagesB "$(ls pages/convB_p*.json 2>/dev/null | wc -l | tr -d ' ')" \
  '{
    run_timestamp_utc: $ts,
    tool: "X API v2 direct HTTP (app-only bearer), curl + jq",
    queries: [
      "GET /2/tweets/:id and /2/tweets?ids= for the 5 root/context posts",
      "GET /2/tweets/search/recent?query=conversation_id:2088463770318516734 (Sholto conversation)",
      "GET /2/tweets/search/recent?query=conversation_id:2088758816376807762 (Dario conversation)",
      "GET /2/tweets/:id/quote_tweets for 2088758816376807762, 2088758819304443967, 2088463770318516734, 2088611616577253502"
    ],
    page_counts: { convA: ($pagesA | tonumber), convB: ($pagesB | tonumber) },
    totals: {
      replies_convA_sholto: ($ra[0] | length),
      replies_convB_dario: ($rb[0] | length),
      quotes_dario_1of2: ($q1[0] | length),
      quotes_dario_2of2: ($q2[0] | length),
      quotes_sholto_root: ($q3[0] | length),
      quotes_gavin_reply: ($q4[0] | length),
      unique_users: ($u[0] | length)
    },
    scope_notes: [
      "Conversation 2088367978270142811 (All-In Podcast clip, quoted by Sholto) captured as context root only; its replies were NOT harvested.",
      "Recent search covers ~7 days; posts date from Aug 14-15 2026, harvest ran Aug 16 2026 UTC.",
      "Deleted posts and protected-account replies are invisible to the API and appear as gaps in the reply tree."
    ]
  }' > manifest.json
echo "manifest.json written"
cat manifest.json
