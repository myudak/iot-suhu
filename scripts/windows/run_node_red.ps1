# Start Node-RED dashboard together with Mosquitto.
$root = Resolve-Path "$PSScriptRoot\.."
Push-Location $root
try {
    docker compose up mosquitto nodered @Args
}
finally {
    Pop-Location
}
