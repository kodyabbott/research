# Build complete thread-digest.md from x-archive raw JSON (both conversations + quotes)
$dir = Split-Path $PSScriptRoot -Parent
$roots    = Get-Content "$dir\roots.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$repliesA = Get-Content "$dir\replies_2088463770318516734.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$repliesB = Get-Content "$dir\replies_2088758816376807762.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$users    = Get-Content "$dir\users.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$quoteFiles = @('quotes_2088758816376807762','quotes_2088758819304443967') | Where-Object { Test-Path "$dir\$_.json" }
$quoteOf = @{ 'quotes_2088758816376807762' = "Dario 1/2"; 'quotes_2088758819304443967' = "Dario 2/2" }

$userById = @{}; foreach ($u in $users) { $userById[$u.id] = $u }
# The conversation search returns the conversation roots too; exclude the posts rendered
# as section roots (Sholto's root, Dario 1/2 + 2/2) from the reply set so counts and
# top-10 lists describe actual replies. Gavin's reply stays: it is a reply in conv A.
$rootIds = @('2088463770318516734','2088758816376807762','2088758819304443967')
$repliesA = @($repliesA | Where-Object { $rootIds -notcontains $_.id })
$repliesB = @($repliesB | Where-Object { $rootIds -notcontains $_.id })
$allReplies = @($repliesA) + @($repliesB)
$postById = @{}; foreach ($p in $allReplies) { $postById[$p.id] = $p }
$rootById = @{}; foreach ($p in $roots.posts) { $rootById[$p.id] = $p }

$children = @{}
foreach ($p in $allReplies) {
    $parentRef = $p.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1
    $parentId = if ($parentRef) { $parentRef.id } else { '_none' }
    if (-not $children.ContainsKey($parentId)) { $children[$parentId] = New-Object System.Collections.ArrayList }
    [void]$children[$parentId].Add($p)
}

function Get-FullText($p) { if ($p.note_tweet -and $p.note_tweet.text) { $p.note_tweet.text } else { $p.text } }
function Fmt-Num($n) { if ($null -eq $n) { return "0" }; if ($n -ge 1000000) { return "{0:N1}M" -f ($n/1000000) }; if ($n -ge 10000) { return "{0:N0}k" -f ($n/1000) }; return "$n" }

$sb = New-Object System.Text.StringBuilder
function Out-Line($s) { [void]$script:sb.AppendLine($s) }

function Out-Post($p, $depth) {
    $q = '>' * [Math]::Min($depth, 6)
    if ($q) { $q = "$q " }
    $capped = $depth -gt 6
    $u = $script:userById[$p.author_id]
    $who = if ($u) { "**$($u.name)** (@$($u.username))" } else { "**Unknown** (author_id $($p.author_id))" }
    $handle = if ($u) { $u.username } else { 'i' }
    $ts = ([datetime]::Parse($p.created_at, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal)).ToString("yyyy-MM-dd HH:mm 'UTC'")
    $m = $p.public_metrics
    $stats = "$(Fmt-Num $m.like_count) likes | $(Fmt-Num $m.retweet_count) reposts | $(Fmt-Num $m.reply_count) replies | $(Fmt-Num $m.impression_count) views"
    $hdr = "$who | $ts | $stats | [post](https://x.com/$handle/status/$($p.id))"
    if ($capped) {
        $parentRef = ($p.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1).id
        $pp = $script:postById[$parentRef]
        $ph = if ($pp -and $script:userById[$pp.author_id]) { "@" + $script:userById[$pp.author_id].username } else { "unknown" }
        $hdr = "$hdr | depth $depth, replying to $ph"
    }
    Out-Line "$q$hdr"
    foreach ($line in ((Get-FullText $p) -split "`n")) { Out-Line "$q$line" }
    Out-Line ""
}

$rendered = @{}
function Out-Tree($parentId, $depth, $exclude) {
    if (-not $script:children.ContainsKey($parentId)) { return }
    $kids = @($script:children[$parentId] | Where-Object { -not ($exclude -contains $_.id) } | Sort-Object { -[int]$_.public_metrics.like_count })
    foreach ($k in $kids) {
        $script:rendered[$k.id] = $true
        Out-Post $k $depth
        Out-Tree $k.id ($depth + 1) $exclude
    }
}

# ---- header + stats ----
$uniqueAuthors = ($allReplies | Select-Object -ExpandProperty author_id -Unique).Count
$top10 = $allReplies | Sort-Object { -[int]$_.public_metrics.like_count } | Select-Object -First 10
# The quote_tweets endpoint returns retweets-of-the-post as truncated "RT @..." stubs
# alongside actual quote posts. Separate them: only true quote posts are listed below.
$allQuotes = @()
$rtStubCount = 0
foreach ($qf in $quoteFiles) {
    $qs = Get-Content "$dir\$qf.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($q in @($qs)) {
        if (-not $q) { continue }
        $isRT = @($q.referenced_tweets | Where-Object { $_.type -eq 'retweeted' }).Count -gt 0
        if ($isRT) { $rtStubCount++ } else { $allQuotes += [pscustomobject]@{ post = $q; of = $quoteOf[$qf] } }
    }
}

Out-Line "# Thread digest: Gavin Baker / Sholto Douglas / Dario Amodei -- Anthropic 'only company left' exchange"
Out-Line ""
Out-Line "Archived 2026-08-16 via X API v2 (read-only), completed after credit top-up. Raw data sits in this folder. Curated version: ``thread-highlights.md``."
Out-Line ""
Out-Line "## Summary stats"
Out-Line ""
Out-Line "- Replies captured: $($allReplies.Count) ($($repliesA.Count) in Sholto's conversation, $($repliesB.Count) in Dario's), not counting the root posts themselves"
Out-Line "- True quote posts captured: $($allQuotes.Count), all of Dario's two posts (the same endpoint also returned $rtStubCount truncated retweet stubs, excluded from the lists below; quote capture for 2/2 is truncated and quotes of Sholto's root and Gavin's reply were not captured -- see README Known gaps)"
Out-Line "- Unique reply authors: $uniqueAuthors"
Out-Line ""
Out-Line "### Top 10 most-liked replies (both conversations)"
Out-Line ""
$i = 1
foreach ($t in $top10) {
    $u = $userById[$t.author_id]
    $handle = if ($u) { "@$($u.username)" } else { $t.author_id }
    $txt = ((Get-FullText $t) -replace "`n", " ")
    if ($txt.Length -gt 140) { $txt = $txt.Substring(0, 140) + "..." }
    Out-Line "$i. $handle ($(Fmt-Num $t.public_metrics.like_count) likes): $txt"
    $i++
}
Out-Line ""

# ---- context ----
Out-Line "---"
Out-Line ""
Out-Line "## Context: the clip that started it"
Out-Line ""
Out-Post $rootById['2088367978270142811'] 0
Out-Line "*(Replies to this post were not harvested -- out of scope.)*"
Out-Line ""

# ---- conversation A ----
Out-Line "---"
Out-Line ""
Out-Line "## Conversation 1 (id 2088463770318516734): Sholto Douglas responds"
Out-Line ""
Out-Post $rootById['2088463770318516734'] 0
Out-Line "### Reply tree ($($repliesA.Count) replies)"
Out-Line ""
Out-Tree '2088463770318516734' 1 @()

$orphansA = @($repliesA | Where-Object { -not $rendered.ContainsKey($_.id) })
if ($orphansA.Count -gt 0) {
    Out-Line "### Detached replies (parent deleted, protected, or outside capture): $($orphansA.Count)"
    Out-Line ""
    $detRootsA = @($orphansA | Where-Object {
        $pr = ($_.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1)
        (-not $pr) -or (-not $script:postById.ContainsKey($pr.id))
    } | Sort-Object { -[int]$_.public_metrics.like_count })
    foreach ($d in $detRootsA) { $rendered[$d.id] = $true; Out-Post $d 1; Out-Tree $d.id 2 @() }
}

# ---- conversation B ----
Out-Line "---"
Out-Line ""
Out-Line "## Conversation 2 (id 2088758816376807762): Dario Amodei responds to Gavin"
Out-Line ""
Out-Line "Dario's post quotes Gavin's reply (which sits inside Conversation 1 above)."
Out-Line ""
Out-Post $rootById['2088758816376807762'] 0
Out-Post $rootById['2088758819304443967'] 0
Out-Line "### Replies to 1/2 ($($repliesB.Count) replies total in conversation)"
Out-Line ""
Out-Tree '2088758816376807762' 1 @('2088758819304443967')
Out-Line "### Replies to 2/2"
Out-Line ""
$rendered['2088758819304443967'] = $true
Out-Tree '2088758819304443967' 1 @()

$orphansB = @($repliesB | Where-Object { -not $rendered.ContainsKey($_.id) })
if ($orphansB.Count -gt 0) {
    Out-Line "### Detached replies (parent deleted, protected, or outside capture): $($orphansB.Count)"
    Out-Line ""
    $detRootsB = @($orphansB | Where-Object {
        $pr = ($_.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1)
        (-not $pr) -or (-not $script:postById.ContainsKey($pr.id))
    } | Sort-Object { -[int]$_.public_metrics.like_count })
    foreach ($d in $detRootsB) { $rendered[$d.id] = $true; Out-Post $d 1; Out-Tree $d.id 2 @() }
}

# ---- quotes ----
Out-Line "---"
Out-Line ""
Out-Line "## Quote posts (top 30 of $($allQuotes.Count) by likes)"
Out-Line ""
$topQ = $allQuotes | Sort-Object { -[int]$_.post.public_metrics.like_count } | Select-Object -First 30
foreach ($qe in $topQ) {
    $q = $qe.post
    $u = $userById[$q.author_id]
    $who = if ($u) { "**$($u.name)** (@$($u.username))" } else { "**Unknown**" }
    $handle = if ($u) { $u.username } else { 'i' }
    $ts = ([datetime]::Parse($q.created_at, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal)).ToString("yyyy-MM-dd HH:mm 'UTC'")
    $m = $q.public_metrics
    Out-Line "$who | quotes $($qe.of) | $ts | $(Fmt-Num $m.like_count) likes | $(Fmt-Num $m.impression_count) views | [post](https://x.com/$handle/status/$($q.id))"
    $txt = ((Get-FullText $q) -replace "`n", " ")
    if ($txt.Length -gt 500) { $txt = $txt.Substring(0, 500) + "..." }
    Out-Line ""
    Out-Line "> $txt"
    Out-Line ""
}

[System.IO.File]::WriteAllText("$dir\thread-digest.md", $sb.ToString(), (New-Object System.Text.UTF8Encoding $false))
"digest written: $((Get-Item "$dir\thread-digest.md").Length) bytes; replies A=$($repliesA.Count) B=$($repliesB.Count) quotes=$($allQuotes.Count)"
