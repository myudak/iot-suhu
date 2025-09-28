# Launch Node-RED dashboard using the local CLI.
if (-not (Get-Command node-red -ErrorAction SilentlyContinue)) {
    Write-Error "node-red CLI not found. Install it via 'npm install -g node-red'."
    exit 1
}

$root = Resolve-Path "$PSScriptRoot\.."
$env:DB_PATH = $env:DB_PATH -as [string]
if (-not $env:DB_PATH) {
    $env:DB_PATH = Join-Path $root "data/sqlite/siapsuhu.db"
}

$settingsDir = Join-Path $root "collector/node-red-data"
node-red -u $settingsDir @Args
