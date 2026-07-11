# install_client_moonlight.ps1
# Installe Moonlight (le client de streaming, cote PC "client" / controle)
# Alternative recommandee au script Python maison, plus robuste et optimisee.

Write-Host "=== Installation de Moonlight (cote CLIENT) ===" -ForegroundColor Cyan
Write-Host ""

$installed = $false

# ---------- 1. Essai via winget (le plus simple, integre a Windows 10/11) ----------
$wingetOK = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetOK) {
    Write-Host "[1/1] Installation de Moonlight via winget..." -ForegroundColor Yellow
    winget install --id MoonlightGameStreamingProject.Moonlight -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        $installed = $true
        Write-Host "  Moonlight installe avec succes via winget." -ForegroundColor Green
    } else {
        Write-Host "  winget a echoue, tentative de telechargement direct..." -ForegroundColor Yellow
    }
} else {
    Write-Host "winget n'est pas disponible sur ce PC, telechargement direct depuis GitHub..." -ForegroundColor Yellow
}

# ---------- 2. Repli : telechargement direct depuis GitHub Releases ----------
if (-not $installed) {
    try {
        Write-Host "Recherche de la derniere version sur GitHub..." -ForegroundColor Yellow
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/moonlight-stream/moonlight-qt/releases/latest" -UseBasicParsing
        $asset = $release.assets | Where-Object {
            $_.name -match "(?i)MoonlightSetup.*x64.*\.exe$"
        } | Select-Object -First 1

        if (-not $asset) {
            throw "Aucun installeur Windows trouve dans la derniere release."
        }

        $installerPath = "$env:TEMP\$($asset.name)"
        Write-Host "  Telechargement de $($asset.name)..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $installerPath -UseBasicParsing
        Write-Host "  Lancement de l'installeur (suis les etapes a l'ecran)..." -ForegroundColor Yellow
        Start-Process -FilePath $installerPath -Wait
        $installed = $true
        Write-Host "  Installation terminee." -ForegroundColor Green
    } catch {
        Write-Host "  Echec du telechargement automatique : $_" -ForegroundColor Red
        Write-Host "  Telecharge et installe manuellement depuis : https://github.com/moonlight-stream/moonlight-qt/releases/latest" -ForegroundColor Red
        Read-Host "Appuie sur Entree pour fermer"
        exit 1
    }
}

Write-Host ""
Write-Host "=== Moonlight est installe ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prochaines etapes :" -ForegroundColor Yellow
Write-Host "  1. Assure-toi que Sunshine tourne sur le PC serveur (voir install_server_sunshine.bat)." -ForegroundColor White
Write-Host "  2. Lance Moonlight : le PC serveur devrait apparaitre automatiquement (meme reseau)." -ForegroundColor White
Write-Host "     Sinon, clique sur '+ Add PC manually' et entre l'IP du serveur." -ForegroundColor White
Write-Host "  3. Un code PIN s'affiche dans Moonlight : entre-le dans l'interface web Sunshine" -ForegroundColor White
Write-Host "     (https://localhost:47990 sur le PC serveur, onglet PIN) pour appairer les deux PC." -ForegroundColor White
Write-Host "  4. Une fois apparie, double-clique sur le PC dans Moonlight pour demarrer le stream." -ForegroundColor White
Write-Host ""
Read-Host "Appuie sur Entree pour fermer"
