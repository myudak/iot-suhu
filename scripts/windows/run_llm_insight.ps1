param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

# Launch the LLM Insight Service with uvicorn.
$root = Resolve-Path "$PSScriptRoot\.."
Push-Location "$root\llm-insight-service"
try {
    python -m uvicorn app.main:app --reload --host $Host --port $Port @Args
}
finally {
    Pop-Location
}
