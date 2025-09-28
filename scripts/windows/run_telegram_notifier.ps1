# Run the Telegram notifier worker.
$root = Resolve-Path "$PSScriptRoot\.."
Push-Location "$root\telegram-notifier"
try {
    python -m app.main @Args
}
finally {
    Pop-Location
}
