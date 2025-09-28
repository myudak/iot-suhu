# Launch a local Mosquitto broker without Docker.
if (-not (Get-Command mosquitto -ErrorAction SilentlyContinue)) {
    Write-Error "mosquitto binary not found. Install Mosquitto from https://mosquitto.org/download/."
    exit 1
}

$root = Resolve-Path "$PSScriptRoot\.."
$stateDir = Join-Path $root "data/mosquitto"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

$tempConfig = New-TemporaryFile
@"
persistence true
persistence_location $stateDir/

listener 1883
allow_anonymous true

listener 9001
protocol websockets

log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
"@ | Set-Content -NoNewline -Path $tempConfig.FullName

try {
    mosquitto -c $tempConfig.FullName @Args
}
finally {
    Remove-Item $tempConfig.FullName -ErrorAction SilentlyContinue
}
