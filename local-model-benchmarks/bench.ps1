<#
.SYNOPSIS
  Nightly local-model benchmark harness for sheila-6000.

.DESCRIPTION
  Two modes, both emitting JSON to stdout so the calling agent can reason over results.

    -Discover              Poll HuggingFace trending, diff against state\seen.json, classify what fits this box.
    -Benchmark <tag>       Run the standard battery against an installed Ollama model.

  Deterministic work lives here. Judgment -- what to download, what is worth writing up --
  belongs to the agent that calls this.

.NOTES
  Never deletes a model. Never pulls anything on its own. Discovery is read-only.
#>
[CmdletBinding(DefaultParameterSetName = 'Discover')]
param(
    [Parameter(ParameterSetName = 'Discover')]
    [switch]$Discover,

    [Parameter(ParameterSetName = 'Benchmark', Mandatory = $true)]
    [string]$Benchmark,

    [Parameter(ParameterSetName = 'Benchmark')]
    [string]$ImagePath,

    [int]$TopN = 25,

    # Total VRAM in GB. Anything whose BF16 footprint exceeds this is flagged as needing a quant.
    [int]$VramGB = 96,

    # VRAM + system RAM. The ceiling for anything with CPU offload.
    [int]$CombinedGB = 224,

    # Per-model detail lookups are one request each; cap them so a busy night stays bounded.
    [int]$DetailLookupCap = 40
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$stateDir = Join-Path $root 'state'
$seenPath = Join-Path $stateDir 'seen.json'

function Get-Trending {
    param([int]$Limit)
    $tags = @('text-generation', 'image-text-to-text', 'text-to-image',
              'image-to-video', 'text-to-speech', 'text-to-audio')
    $all = @()
    foreach ($tag in $tags) {
        $url = "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=$Limit&pipeline_tag=$tag"
        try {
            $all += Invoke-RestMethod $url -TimeoutSec 30
        } catch {
            Write-Warning "trending query failed for ${tag}: $($_.Exception.Message)"
        }
    }
    # A model can chart under more than one tag; keep the best trending rank, not alphabetical order.
    $all | Sort-Object modelId -Unique | Sort-Object -Property trendingScore -Descending
}

function Get-ModelDetail {
    # The list endpoint omits parameter counts even with full=true -- only the
    # per-model endpoint carries safetensors. Called for new models only.
    param([string]$ModelId)
    try {
        Invoke-RestMethod "https://huggingface.co/api/models/$ModelId" -TimeoutSec 20
    } catch {
        $null
    }
}

function Get-Fit {
    <#
      Rough triage, not gospel. Param counts come from the safetensors index when the
      repo publishes one; plenty of repos don't, and those come back as 'unknown'.
    #>
    param($Model)

    $params = $null
    if ($Model.PSObject.Properties.Name -contains 'safetensors' -and $Model.safetensors) {
        if ($Model.safetensors.PSObject.Properties.Name -contains 'total') {
            $params = $Model.safetensors.total
        }
    }

    if ($null -eq $params) {
        return [pscustomobject]@{ verdict = 'unknown'; paramsB = $null; bf16GB = $null }
    }

    $paramsB = [math]::Round($params / 1e9, 1)
    $bf16GB = [math]::Round(($params * 2) / 1GB, 1)
    $q4GB = [math]::Round(($params * 0.55) / 1GB, 1)

    $verdict = 'api-only'
    if ($bf16GB -le $VramGB) {
        $verdict = 'fits-bf16'
    } elseif ($q4GB -le $VramGB) {
        $verdict = 'fits-quantized'
    } elseif ($q4GB -le $CombinedGB) {
        $verdict = 'fits-with-cpu-offload'
    }

    [pscustomobject]@{ verdict = $verdict; paramsB = $paramsB; bf16GB = $bf16GB; q4GB = $q4GB }
}

function Invoke-Discover {
    if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Force $stateDir | Out-Null }

    $seen = @{}
    if (Test-Path $seenPath) {
        $raw = Get-Content $seenPath -Raw | ConvertFrom-Json
        foreach ($p in $raw.PSObject.Properties) { $seen[$p.Name] = $p.Value }
    }

    $trending = Get-Trending -Limit $TopN
    $new = @()
    $looked = 0

    foreach ($m in $trending) {
        if ($seen.ContainsKey($m.modelId)) { continue }

        # Detail lookups cost a request each. Bounded so a first run, or a wild
        # night on the trending page, can't turn into hundreds of calls.
        $detail = $null
        if ($looked -lt $DetailLookupCap) {
            $detail = Get-ModelDetail -ModelId $m.modelId
            $looked++
        }

        $fit = Get-Fit -Model $detail
        $gated = $false
        if ($m.PSObject.Properties.Name -contains 'gated' -and $m.gated) { $gated = $true }

        $new += [pscustomobject]@{
            modelId       = $m.modelId
            pipeline      = $m.pipeline_tag
            trendingScore = $m.trendingScore
            downloads     = $m.downloads
            likes         = $m.likes
            gated         = $gated
            lastModified  = $m.lastModified
            paramsB       = $fit.paramsB
            bf16GB        = $fit.bf16GB
            verdict       = $fit.verdict
        }
    }

    # Only record what we actually saw this run; the file is the memory of past nights.
    $stamp = (Get-Date).ToString('yyyy-MM-dd')
    foreach ($m in $trending) {
        if (-not $seen.ContainsKey($m.modelId)) { $seen[$m.modelId] = $stamp }
    }
    $seen | ConvertTo-Json -Depth 3 | Set-Content $seenPath -Encoding utf8

    [pscustomobject]@{
        date         = $stamp
        trendingSeen = $trending.Count
        newCount     = $new.Count
        new          = $new
    } | ConvertTo-Json -Depth 5
}

function Invoke-Chat {
    param([string]$Model, [string]$Prompt, [switch]$NoThink, [string]$Image)

    $msg = @{ role = 'user'; content = $Prompt }
    if ($Image) {
        $bytes = [System.IO.File]::ReadAllBytes($Image)
        $msg['images'] = @([Convert]::ToBase64String($bytes))
    }

    $body = @{ model = $Model; messages = @($msg); stream = $false }
    if ($NoThink) { $body['think'] = $false }

    $json = $body | ConvertTo-Json -Depth 6
    Invoke-RestMethod 'http://127.0.0.1:11434/api/chat' -Method Post -Body $json -TimeoutSec 900
}

function Invoke-Benchmark {
    param([string]$Model, [string]$Image)

    $result = [ordered]@{
        model = $Model
        date  = (Get-Date).ToString('yyyy-MM-dd HH:mm')
        host  = 'sheila-6000 / RTX PRO 6000 Blackwell 96GB'
    }

    # --- throughput on a fixed short prompt -------------------------------
    $r = Invoke-Chat -Model $Model -Prompt 'Write a 100 word description of the Rocky Mountains.'
    $result['loadMs'] = [math]::Round($r.load_duration / 1e6)
    $result['genTokPerSec'] = [math]::Round($r.eval_count / ($r.eval_duration / 1e9), 1)
    # Tokens spent to satisfy a ~100-word request. High numbers mean heavy reasoning overhead.
    $result['tokensFor100Words'] = $r.eval_count

    # --- prompt ingest at a realistic context length -----------------------
    # A 20-token prompt tells you nothing about ingest speed; this is ~4K tokens.
    $filler = ('The quick brown fox jumps over the lazy dog. ' * 700)
    $r2 = Invoke-Chat -Model $Model -Prompt "$filler`n`nReply with the single word: acknowledged." -NoThink
    $result['promptTokens'] = $r2.prompt_eval_count
    if ($r2.prompt_eval_duration -gt 0) {
        $result['promptTokPerSec'] = [math]::Round($r2.prompt_eval_count / ($r2.prompt_eval_duration / 1e9), 1)
    }

    # --- functional code test ---------------------------------------------
    # Not "does it look right" -- the command is executed and the output checked.
    $codePrompt = 'Output only a single PowerShell one-liner, no explanation and no code fences, ' +
                  'that prints the numbers 1 through 5 each on its own line.'
    $r3 = Invoke-Chat -Model $Model -Prompt $codePrompt -NoThink
    $cmd = $r3.message.content.Trim() -replace '^```[a-z]*\s*', '' -replace '\s*```$', ''
    $result['codeWritten'] = $cmd
    try {
        $out = & powershell.exe -NoProfile -NonInteractive -Command $cmd 2>$null
        $nums = @($out | Where-Object { $_ -match '^\s*[1-5]\s*$' })
        $result['codeExecutes'] = ($nums.Count -eq 5)
    } catch {
        $result['codeExecutes'] = $false
    }

    # --- vision, only when an image is supplied ---------------------------
    # Caller passes a neutral filename so the model can't read the answer off the path.
    if ($Image -and (Test-Path $Image)) {
        $r4 = Invoke-Chat -Model $Model -Prompt 'Describe this image in one sentence.' -Image $Image -NoThink
        $result['visionAnswer'] = $r4.message.content.Trim()
    }

    [pscustomobject]$result | ConvertTo-Json -Depth 4
}

if ($PSCmdlet.ParameterSetName -eq 'Benchmark') {
    Invoke-Benchmark -Model $Benchmark -Image $ImagePath
} else {
    Invoke-Discover
}
