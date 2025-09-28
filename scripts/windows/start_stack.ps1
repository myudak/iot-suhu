param(
    [string]$EnvFile = ".env",
    [switch]$SkipMosquitto,
    [switch]$SkipNodeRed,
    [switch]$SkipInsight,
    [switch]$SkipTelegram
)

function Import-EnvFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Warning "Env file '$Path' tidak ditemukan. Melewati pemuatan variabel lingkungan."
        return
    }

    Get-Content $Path | ForEach-Object {
        if ($_ -match '^[ \t]*#') { return }
        if ($_ -match '^[ \t]*$') { return }
        if ($_ -match '^[ \t]*([^=]+)=(.*)$') {
            $name = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            Set-Item -Path ("Env:{0}" -f $name) -Value $value
        }
    }
}

function Ensure-Venv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        Write-Host "Membuat virtualenv di $Path" -ForegroundColor Cyan
        python -m venv $Path
    }
}

function Install-Requirements {
    param([string]$PythonExe, [string]$RequirementsPath)

    if (-not (Test-Path $RequirementsPath)) {
        throw "File requirements '$RequirementsPath' tidak ditemukan."
    }

    Write-Host "Menginstal dependensi dari $RequirementsPath" -ForegroundColor Cyan
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r $RequirementsPath
}

function Start-BackgroundProcess {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$Name
    )

    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -NoNewWindow -PassThru
    Write-Host "Menjalankan $Name (PID $($process.Id))" -ForegroundColor Green
    return $process
}

Write-Host "=== Siap Suhu Windows Starter ===" -ForegroundColor Yellow

Import-EnvFile $EnvFile

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot

$venvPath = Join-Path $repoRoot ".venv"
Ensure-Venv $venvPath

$pythonExe = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "python.exe tidak ditemukan di $pythonExe. Pastikan Python 3.11 terpasang."
}

Install-Requirements $pythonExe (Join-Path $repoRoot "llm-insight-service\requirements.txt")
Install-Requirements $pythonExe (Join-Path $repoRoot "telegram-notifier\requirements.txt")

$processes = @()

if (-not $SkipMosquitto) {
    $mosquittoCmd = Get-Command mosquitto.exe -ErrorAction SilentlyContinue
    if ($mosquittoCmd) {
        $configPath = Resolve-Path (Join-Path $repoRoot "broker\mosquitto.conf")
        $processes += Start-BackgroundProcess -FilePath $mosquittoCmd.Source -Arguments @("-c", $configPath) -WorkingDirectory $repoRoot -Name "Mosquitto"
    } else {
        Write-Warning "mosquitto.exe tidak ditemukan dalam PATH. Instal Mosquitto untuk Windows lalu jalankan ulang script, atau start broker secara manual dengan: mosquitto -c broker\\mosquitto.conf"
    }
}

if (-not $SkipNodeRed) {
    $nodeRedCmd = Get-Command node-red.cmd -ErrorAction SilentlyContinue
    $npxCmd = Get-Command npx.cmd -ErrorAction SilentlyContinue
    $flowFile = Resolve-Path (Join-Path $repoRoot "collector\node-red-data\flows.json")
    $userDir = Resolve-Path (Join-Path $repoRoot "collector\node-red-data")

    if ($nodeRedCmd) {
        $processes += Start-BackgroundProcess -FilePath $nodeRedCmd.Source -Arguments @("--userDir", $userDir, "--flowFile", $flowFile) -WorkingDirectory $repoRoot -Name "Node-RED"
    } elseif ($npxCmd) {
        $processes += Start-BackgroundProcess -FilePath $npxCmd.Source -Arguments @("node-red", "--userDir", $userDir, "--flowFile", $flowFile) -WorkingDirectory $repoRoot -Name "Node-RED (npx)"
    } else {
        Write-Warning "Tidak ditemukan node-red atau npx. Instal Node.js dan jalankan 'npm install -g node-red' atau gunakan npx."
    }
}

if (-not $SkipInsight) {
    $processes += Start-BackgroundProcess -FilePath $pythonExe -Arguments @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000") -WorkingDirectory (Resolve-Path (Join-Path $repoRoot "llm-insight-service")) -Name "LLM Insight"
}

if (-not $SkipTelegram) {
    $processes += Start-BackgroundProcess -FilePath $pythonExe -Arguments @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080") -WorkingDirectory (Resolve-Path (Join-Path $repoRoot "telegram-notifier")) -Name "Telegram Notifier"
}

Write-Host "\nProses aktif:" -ForegroundColor Yellow
foreach ($proc in $processes) {
    Write-Host (" - {0} (PID {1})" -f $proc.StartInfo.FileName, $proc.Id)
}

Write-Host "\nGunakan 'Stop-Process -Id <PID>' untuk menghentikan layanan individual." -ForegroundColor Yellow
