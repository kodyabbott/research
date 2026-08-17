# Source verification report -- anthropic-only-company-x-thread

> **Scope note (added after data reduction):** this verification ran against the project as first published, including the full-object JSON files later removed per the X Developer Policy (see README "Data, licensing, and takedown"). It is retained as the audit trail showing the reports were verified against the raw capture before the data was reduced to IDs.

Verification conducted 2026-08-16 by the source-verifier agent (Claude Code, Fable 5). Scope: `README.md`, `notes.md`, `thread-highlights.md` verified against the raw JSON archive (roots.json, replies_*.json, quotes_*.json, users.json, manifest.json, pages-raw.zip) plus spot-checks of `thread-digest.md`. Method: a scripted jq verification pass that parsed every post entry in thread-highlights.md (62 post headers) and compared ID, author, permalink username, timestamp, like/view counts, and full text against the JSON. No research files were modified.

## ✅ Verified claims

**Quotes and text (the strongest result):**

- All four principal long-form posts are **verbatim** against `note_tweet.text` in the JSON: the All-In clip, Sholto's root (including the "competetive" typo, which is authentic), Dario 1/2 and 2/2.
- All 37 reply-tree posts in highlights sections 1-3 match the JSON on author, permalink username, timestamp, like count, view count, and text -- including Musk's reply (4,481 likes, 206k views), Gavin's long reply (3,080 likes / 2.9M views), Sholto's 15:28 response, all 5 LeCun replies, the Gavin/Sholto gin-and-tonic exchange, roon, kache, Weisenthal, the Levskaya sub-thread, and the Eric Jang detached branch. Every one: exact match.
- 10 section-4 posts that turn out to exist in the JSON also verify: Gavin's "Many thoughts." reply, signüll, Sholto's self-quote, altcap, JTLonsdale, willdepue are verbatim; stevesi reply 1, lulumeservey, and kache's quote post are exact prefixes of the JSON text, with the cut honestly marked "[truncated in capture]".
- Structural attributions in section 4 are all correct per `referenced_tweets`: Gavin "Many thoughts" is a reply to 2/2; stevesi #1 to 1/2; stevesi #2 to 2/2; signüll to 1/2; all six in-JSON quote posts genuinely quote 1/2.

**Counts and numbers:**

- README raw-data table: 1,112 / 2,474 / 1,445 / 999 / 4,372 / 5 roots -- all match `jq length` exactly, and match manifest.json totals. All IDs unique within each file; every entry carries the correct `conversation_id`.
- Known-gaps "~130 posts": manifest's ~64 + ~69 = 133, and roots.json's own `quote_count` metrics are exactly 64 (Sholto root) and 69 (Gavin reply).
- Cost math: 6,020 × ~$5.00/1k ≈ $30.10 vs claimed $30.12 total -- consistent; run wall times match "under 10 minutes."
- `pages-raw.zip`: exactly 91 files, 8,459,408 bytes uncompressed (= "8.4MB"), 1.9MB zipped. Pages: convA 12, convB 26, quotes-1/2 42, quotes-2/2 11 = 91; 91 pages + root/user lookups ≈ the claimed 97 API requests.
- Highlights header "37 reply-tree posts": 41 section-1-3 entries minus 4 roots = 37; the 11 notable authors listed are exactly the non-*(context)* authors present.

**Event timeline:** All-In clip Aug 14 20:51 UTC; Sholto root Aug 15 03:12:19 quote-posting the clip; Gavin reply 12:59:48 inside Sholto's conversation; Sholto response 15:28; Dario 1/2 22:44:43 quote-posting Gavin's reply, 2/2 as reply to 1/2. All confirmed per `referenced_tweets` and `created_at`.

**notes.md claims verified in data:** Dario authored nothing in his conversation besides 1/2 and 2/2; LeCun has exactly 5 replies, all in Sholto's conversation, 0 replies in Dario's (but see the retweet finding below); Sinofsky's two replies; the UI-reply-counter footgun (Sholto root shows `reply_count` 154 vs 1,112 captured; Dario 850+877 vs 2,474); digest summary stats recomputed exactly.

## ⚠️ Paraphrases presented as quotes

Only two, both micro-level, both in browser-captured transcriptions in section 4:

1. stevesi reply 2 (quoting Dario's 60 Minutes line): highlights has "in the next 1-5 years" where the JSON post text has an en dash ("1–5 years"). Everything else in that ~3,300-char post is character-exact.
2. altcap: highlights "back & forth" vs JSON "back &amp; forth" -- the markdown correctly decodes the API's HTML entity; not an error, noted for completeness.

No substantive paraphrase-as-quote was found anywhere.

## ❌ Claims that don't match their source

(These match the adversarial review's findings C1, C2, I1-I4, I6 in `review-findings.md`; both agents converged independently.)

1. Quotes of Dario 2/2 are substantially incomplete (spans only Aug 16 08:58-19:13 UTC; ~347 of ~500 quote posts missing per roots.json's `quote_count`, including Elon's quote post -- whose ID appears 259 times inside the file as a retweet target, so the API demonstrably could see it), while manifest/README/notes called the capture complete.
2. "Quote posts" counts include retweets: composition is 1/2 → 604 quoted / 841 retweeted; 2/2 → 153 quoted / 846 retweeted.
3. thread-highlights.md carried stale pre-run-2 statements ("1,086", "Not in the raw JSON archive" -- 10 of 21 section-4 posts ARE in the JSON).
4. "Several the API could not see at any price" -- overstated; Elon's quote post was API-visible.
5. README listed "Dario's response" as browser-captured section-4 material; it is in section 3, captured via the API.
6. notes.md "Verified LeCun ... never on Dario's posts" -- the quotes files show LeCun retweeted two quote posts of Dario's posts (Aug 16 07:01 and 15:15 UTC).
7. thread-digest.md header referenced a nonexistent `./x-archive/` path.
8. Reply files include their conversation roots, so "All 1,112 replies" / "All 2,474 replies" each overcounted actual replies slightly (1,111 / 2,472).

## 🔍 Claims that couldn't be verified

- The 11 genuinely browser-only section-4 posts (Elon, Gavin's "Yes!" and self-quote, Beff Jezos, Anish Acharya, the Sasha de Marigny posts, Gary Marcus, Gavin's S-1 reply): x.com returns HTTP 403 to unauthenticated fetches. Their internal presentation is consistent (permalink IDs fall in plausible snowflake ranges; the Sasha/Elon posts are corroborated by references inside the JSON).
- X Developer Console figures (6,020 billed reads, 97 requests, $30.12, payments): external dashboard; archive totals are consistent with them. Cent-level wrinkle: $5.00 + $25.00 - $30.12 = -$0.12, not the displayed -$0.13 (likely rounding of $30.125).
- Timezone label: the data is self-consistent only under UTC-7, but Mountain Time in August is UTC-6 -- either the machine clock or the "Mountain Time" label was off by an hour. (Fixed by restating run times in UTC.)
- Unfalsifiable-from-archive figures: section-4 post count ("~25" -- actual 21), "19 permalinks resolved" (21 present), browser operation counts and durations, and affiliation labels (will depue "OpenAI", Anish Acharya "a16z", Sasha de Marigny "Anthropic comms") -- plausible, no in-repo source.
- "(complete)" for the two reply sets: consistent with the API reporting no next_token, but completeness against X's true reply universe cannot be proven from the archive itself (deleted/protected posts are invisible).

## Bottom line

The quotes, attributions, metrics, timeline, and counts in the human-readable files are exceptionally faithful to the raw JSON -- every API-sourced quote checked was verbatim or an honestly-marked truncation. The real findings are documentation-level and are addressed in the fix commits following this report.
