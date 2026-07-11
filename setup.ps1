# setup.ps1
# Installation automatique de FFmpeg + dependances Python pour LAN Remote Play
# A lancer sur CHAQUE PC (serveur ET client)

Write-Host "=== LAN Remote Play - Installation automatique ===" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. Verification de Python ----------
Write-Host "[1/3] Verification de Python..." -ForegroundColor Yellow
$pythonOK = $false
try {
    $pyVersion = python --version 2>&1
    Write-Host "  Trouve : $pyVersion" -ForegroundColor Green
    $pythonOK = $true
} catch {
    Write-Host "  Python n'est pas installe ou pas dans le PATH." -ForegroundColor Red
    Write-Host "  Telecharge-le ici : https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  IMPORTANT : coche 'Add Python to PATH' pendant l'installation." -ForegroundColor Red
}

if (-not $pythonOK) {
    Write-Host ""
    Write-Host "Installe Python puis relance ce script. Arret." -ForegroundColor Red
    Read-Host "Appuie sur Entree pour fermer"
    exit 1
}

# ---------- 2. Installation de pynput ----------
Write-Host ""
Write-Host "[2/3] Installation de la librairie Python 'pynput'..." -ForegroundColor Yellow
pip install pynput --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "  pynput installe avec succes." -ForegroundColor Green
} else {
    Write-Host "  Erreur lors de l'installation de pynput." -ForegroundColor Red
}

# ---------- 3. Installation de FFmpeg ----------
Write-Host ""
Write-Host "[3/3] Verification / installation de FFmpeg..." -ForegroundColor Yellow

$ffmpegDir = "$env:USERPROFILE\ffmpeg"
$ffmpegBin = "$ffmpegDir\bin"
$ffmpegExe = "$ffmpegBin\ffmpeg.exe"

$alreadyInstalled = $false
try {
    ffmpeg -version | Out-Null
    Write-Host "  FFmpeg est deja installe et accessible dans le PATH." -ForegroundColor Green
    $alreadyInstalled = $true
} catch {
    if (Test-Path $ffmpegExe) {
        Write-Host "  FFmpeg deja telecharge dans $ffmpegBin mais pas dans le PATH, ajout en cours..." -ForegroundColor Yellow
        $alreadyInstalled = $false
    }
}

if (-not $alreadyInstalled) {
    if (-not (Test-Path $ffmpegExe)) {
        Write-Host "  Telechargement de FFmpeg (build officiel BtbN, ~100 Mo)..." -ForegroundColor Yellow
        $zipUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"
        $zipPath = "$env:TEMP\ffmpeg-download.zip"

        try {
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
            Write-Host "  Telechargement termine." -ForegroundColor Green
        } catch {
            Write-Host "  Echec du telechargement automatique." -ForegroundColor Red
            Write-Host "  Telecharge manuellement ici : https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Red
            Write-Host "  (prends 'release full'), dezippe, et ajoute le dossier bin au PATH." -ForegroundColor Red
            Read-Host "Appuie sur Entree pour fermer"
            exit 1
        }

        Write-Host "  Extraction..." -ForegroundColor Yellow
        $extractPath = "$env:TEMP\ffmpeg-extract"
        if (Test-Path $extractPath) { Remove-Item $extractPath -Recurse -Force }
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force

        # Le zip contient un dossier du style ffmpeg-master-latest-win64-gpl\bin
        $extractedBin = Get-ChildItem -Path $extractPath -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
        if ($extractedBin) {
            if (-not (Test-Path $ffmpegDir)) { New-Item -ItemType Directory -Path $ffmpegDir | Out-Null }
            if (Test-Path $ffmpegBin) { Remove-Item $ffmpegBin -Recurse -Force }
            Copy-Item -Path $extractedBin.Directory.FullName -Destination $ffmpegBin -Recurse

            Remove-Item $zipPath -Force
            Remove-Item $extractPath -Recurse -Force
            Write-Host "  FFmpeg installe dans $ffmpegBin" -ForegroundColor Green
        } else {
            Write-Host "  ffmpeg.exe introuvable dans l'archive telechargee." -ForegroundColor Red
            Read-Host "Appuie sur Entree pour fermer"
            exit 1
        }
    }

    # Ajout au PATH utilisateur (permanent)
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$ffmpegBin*") {
        Write-Host "  Ajout de $ffmpegBin au PATH utilisateur..." -ForegroundColor Yellow
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$ffmpegBin", "User")
        $env:Path += ";$ffmpegBin"
        Write-Host "  PATH mis a jour." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== Installation terminee ===" -ForegroundColor Cyan
Write-Host "Ferme et rouvre ton terminal (ou redemarre) pour que le PATH soit bien pris en compte partout." -ForegroundColor Yellow
Write-Host "Tu peux ensuite verifier avec : ffmpeg -version" -ForegroundColor Yellow
Write-Host ""
Read-Host "Appuie sur Entree pour fermer"
