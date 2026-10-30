$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$credentialFile = Join-Path $projectRoot 'docker-data\superadmin-credentials.txt'

Push-Location $projectRoot
try {
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host 'Docker Compose failed. Initialization logs:' -ForegroundColor Red
        docker compose logs --no-color init
        throw 'Docker Compose failed to start.'
    }

    Write-Host ''
    if (Test-Path -LiteralPath $credentialFile) {
        Write-Host 'Default administrator credentials:' -ForegroundColor Cyan
        Get-Content -LiteralPath $credentialFile
        Remove-Item -LiteralPath $credentialFile -Force
        Write-Host 'The one-time credential file has been removed.' -ForegroundColor DarkGray
    }
    else {
        Write-Host 'Default superadmin already exists; its password was not changed.' -ForegroundColor Yellow
    }

    $portOutput = docker compose port web 8000 | Select-Object -First 1
    $port = if ($portOutput) { ($portOutput -split ':')[-1] } else { '8000' }
    Write-Host ''
    Write-Host "Homepage: http://127.0.0.1:$port/en/"
    Write-Host "Administration: http://127.0.0.1:$port/en/admin/"
}
finally {
    Pop-Location
}
