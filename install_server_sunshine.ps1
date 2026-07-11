# install_server_sunshine.ps1
# Installe Sunshine (l'hote de streaming, cote PC "serveur" / gaming)
# Alternative recommandee au script Python maison, plus robuste et optimisee.

Write-Host "=== Installation de Sunshine (cote SERVEUR) ===" -ForegroundColor Cyan
Write-Host ""

$installed = $false

# ---------- 1. Essai via winget (le plus simple, integre a Windows 10/11) ----------
$wingetOK = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetOK) {
    Write-Host "[1/1] Installation de Sunshine via winget..." -ForegroundColor Yellow
    winget install --id LizardByte.Sunshine -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) {
        $installed = $true
        Write-Host "  Sunshine installe avec succes via winget." -ForegroundColor Green
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
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/LizardByte/Sunshine/releases/latest" -UseBasicParsing
        $asset = $release.assets | Where-Object {
            $_.name -match "(?i)windows.*(amd64.*installer|installer).*\.exe$" -and $_.name -notmatch "(?i)arm64"
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
        Write-Host "  Telecharge et installe manuellement depuis : https://github.com/LizardByte/Sunshine/releases/latest" -ForegroundColor Red
        Read-Host "Appuie sur Entree pour fermer"
        exit 1
    }
}

Write-Host ""
Write-Host "=== Sunshine est installe ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Prochaines etapes :" -ForegroundColor Yellow
Write-Host "  1. Sunshine devrait se lancer automatiquement (icone dans la barre des taches)." -ForegroundColor White
Write-Host "  2. Ouvre https://localhost:47990 dans ton navigateur pour la configuration initiale" -ForegroundColor White
Write-Host "     (accepte l'avertissement de certificat, c'est normal en local)." -ForegroundColor White
Write-Host "  3. Cree un compte admin Sunshine (nom d'utilisateur + mot de passe)." -ForegroundColor White
Write-Host "  4. Depuis Moonlight sur le PC client, ajoute ce PC (par IP si la decouverte" -ForegroundColor White
Write-Host "     automatique ne le trouve pas) et entre le code PIN affiche par Moonlight" -ForegroundColor White
Write-Host "     dans l'onglet 'PIN' de l'interface web Sunshine." -ForegroundColor White
Write-Host ""
Write-Host "  Pare-feu : l'installeur Sunshine ajoute normalement les regles necessaires" -ForegroundColor White
Write-Host "  automatiquement. Si la decouverte/connexion echoue, verifie que le profil" -ForegroundColor White
Write-Host "  reseau est en 'Prive' (Parametres > Reseau et Internet)." -ForegroundColor White
Write-Host ""
Read-Host "Appuie sur Entree pour fermer"
