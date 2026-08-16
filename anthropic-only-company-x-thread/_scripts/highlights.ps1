# Build thread-highlights.md SECTIONS 1-3 from x-archive raw JSON.
# NOTE: this generates thread-highlights-gen.md only. The shipped thread-highlights.md
# is that output spliced with hand-curated content (the timeline line, the section-3
# LeCun note, and all of section 4, which came from browser capture) -- see README
# "Reproduction". Re-running this script does NOT regenerate the shipped file.
$dir = Split-Path $PSScriptRoot -Parent
$roots   = Get-Content "$dir\roots.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$replies = Get-Content "$dir\replies_2088463770318516734.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$users   = Get-Content "$dir\users.json" -Raw -Encoding UTF8 | ConvertFrom-Json

$notable = @('DarioAmodei','GavinSBaker','_sholtodouglas','elonmusk','ylecun','theallinpod','tszzl','yacineMTB','TheStalwart','ericjang11','anselmlevskaya')

$userById = @{}; foreach ($u in $users) { $userById[$u.id] = $u }
$notableIds = @{}; foreach ($u in $users) { if ($notable -contains $u.username) { $notableIds[$u.id] = $true } }
$postById = @{}; foreach ($p in $replies) { $postById[$p.id] = $p }

$children = @{}
foreach ($p in $replies) {
    $parentRef = $p.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1
    $parentId = if ($parentRef) { $parentRef.id } else { '_none' }
    if (-not $children.ContainsKey($parentId)) { $children[$parentId] = New-Object System.Collections.ArrayList }
    [void]$children[$parentId].Add($p)
}

# keep set: posts by notables + all ancestors (context)
$keep = @{}
foreach ($p in $replies) {
    if (-not $notableIds.ContainsKey($p.author_id)) { continue }
    $cur = $p
    while ($cur) {
        if ($keep.ContainsKey($cur.id)) { break }
        $keep[$cur.id] = $true
        $parentRef = $cur.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1
        $cur = if ($parentRef -and $postById.ContainsKey($parentRef.id)) { $postById[$parentRef.id] } else { $null }
    }
}

function Get-FullText($p) { if ($p.note_tweet -and $p.note_tweet.text) { $p.note_tweet.text } else { $p.text } }
function Fmt-Num($n) { if ($null -eq $n) { return "0" }; if ($n -ge 1000000) { return "{0:N1}M" -f ($n/1000000) }; if ($n -ge 10000) { return "{0:N0}k" -f ($n/1000) }; return "$n" }

$sb = New-Object System.Text.StringBuilder
function Out-Line($s) { [void]$script:sb.AppendLine($s) }

function Out-Post($p, $depth) {
    $q = '>' * [Math]::Min($depth, 8)
    if ($q) { $q = "$q " }
    $u = $script:userById[$p.author_id]
    $who = if ($u) { "**$($u.name)** (@$($u.username))" } else { "**Unknown**" }
    $ctx = if ($u -and -not ($script:notable -contains $u.username)) { " *(context)*" } else { "" }
    $ts = ([datetime]::Parse($p.created_at, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal)).ToString("MMM d HH:mm 'UTC'")
    $m = $p.public_metrics
    $handle = if ($u) { $u.username } else { 'i' }
    $link = "[post](https://x.com/$handle/status/$($p.id))"
    Out-Line "$q$who$ctx | $ts | $(Fmt-Num $m.like_count) likes | $(Fmt-Num $m.impression_count) views | $link"
    foreach ($line in ((Get-FullText $p) -split "`n")) { Out-Line "$q$line" }
    Out-Line ""
}

function Out-Tree($parentId, $depth) {
    if (-not $script:children.ContainsKey($parentId)) { return }
    $kids = @($script:children[$parentId] | Where-Object { $script:keep.ContainsKey($_.id) } | Sort-Object { -[int]$_.public_metrics.like_count })
    foreach ($k in $kids) {
        Out-Post $k $depth
        Out-Tree $k.id ($depth + 1)
    }
}

$rootById = @{}; foreach ($p in $roots.posts) { $rootById[$p.id] = $p }
$keptCount = $keep.Keys.Count

Out-Line "# Highlights: the Anthropic 'only company left' exchange -- high-profile thread"
Out-Line ""
Out-Line "The conversation pruned to posts by: Dario Amodei, Gavin Baker, Sholto Douglas, Elon Musk, Yann LeCun, All-In Podcast, roon, kache, Joe Weisenthal, Eric Jang, Anselm Levskaya -- plus parent posts kept for context ($keptCount reply-tree posts of the 1,111 captured replies). Section 4 adds the high-profile reaction to Dario's posts, captured via browser on Aug 16 between the two API runs; most of these posts were later also captured in the raw JSON (see the note in section 4). Full archive: ``thread-digest.md``."
Out-Line ""
Out-Line "Timeline: All-In clip (Aug 14) -> Sholto's rebuttal (Aug 15 03:12) -> Gavin's long reply (12:59) -> Sholto's response (15:28) -> Dario's 2-post reply quoting Gavin (22:44)."
Out-Line ""
Out-Line "---"
Out-Line ""
Out-Line "## 1. The All-In clip that started it (Aug 14)"
Out-Line ""
Out-Post $rootById['2088367978270142811'] 0
Out-Line "---"
Out-Line ""
Out-Line "## 2. Sholto's conversation (root + high-profile branches)"
Out-Line ""
Out-Post $rootById['2088463770318516734'] 0
Out-Tree '2088463770318516734' 1

# kept posts whose parent chain broke (parent not captured)
$rendered = @{}
function Mark-Rendered($parentId) {
    if (-not $script:children.ContainsKey($parentId)) { return }
    foreach ($k in @($script:children[$parentId] | Where-Object { $script:keep.ContainsKey($_.id) })) {
        $script:rendered[$k.id] = $true; Mark-Rendered $k.id
    }
}
Mark-Rendered '2088463770318516734'
$detached = @($replies | Where-Object { $keep.ContainsKey($_.id) -and -not $rendered.ContainsKey($_.id) } | Sort-Object created_at)
if ($detached.Count -gt 0) {
    Out-Line "### Detached high-profile posts (parent not captured)"
    Out-Line ""
    $detachedRoots = @($detached | Where-Object {
        $pr = ($_.referenced_tweets | Where-Object { $_.type -eq 'replied_to' } | Select-Object -First 1)
        (-not $pr) -or (-not $script:postById.ContainsKey($pr.id)) -or (-not $script:keep.ContainsKey($pr.id))
    })
    foreach ($d in $detachedRoots) {
        Out-Post $d 1
        Out-Tree $d.id 2
    }
}

Out-Line "---"
Out-Line ""
Out-Line "## 3. Dario's reply to Gavin (separate conversation, Aug 15 22:44)"
Out-Line ""
Out-Post $rootById['2088758816376807762'] 0
Out-Post $rootById['2088758819304443967'] 0
Out-Line "*(Section 4 -- the browser-captured reaction to Dario -- is hand-curated and spliced in after this generated output; see README Reproduction.)*"

[System.IO.File]::WriteAllText("$dir\thread-highlights-gen.md", $sb.ToString(), (New-Object System.Text.UTF8Encoding $false))
"highlights written: $((Get-Item "$dir\thread-highlights-gen.md").Length) bytes, kept $keptCount tree posts"
