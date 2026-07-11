# LAN Remote Play (Python + FFmpeg/NVENC)

Stream ton écran (60 FPS, 1080p, encodage GPU Nvidia) vers un autre PC sur le même réseau WiFi/LAN, avec contrôle clavier/souris à distance.

## ⚠️ Avant de commencer

Ce script fait le travail à la main avec Python + FFmpeg. Il fonctionne bien, mais reste **moins optimisé et moins robuste** que des solutions dédiées comme **Sunshine + Moonlight** (gratuites, open-source, faites exactement pour ce cas d'usage). Si jamais tu rencontres trop de friction avec ce script (latence input, jeux qui ignorent les clics simulés, coupures réseau...), Sunshine/Moonlight reste la solution de repli recommandée.

## ⚡ Installation automatique (recommandé)

Sur **chaque PC** (serveur et client), après avoir installé Python (voir ci-dessous) :

1. Double-clique sur **`setup.bat`**
2. Le script vérifie Python, installe `pynput`, télécharge et configure FFmpeg automatiquement (ajout au PATH)
3. Ferme et rouvre ton terminal une fois terminé

Ça remplace toute l'installation manuelle de FFmpeg décrite plus bas.

## Installation manuelle (si setup.bat ne fonctionne pas)

1. **FFmpeg** : télécharge la version "full" ici → https://www.gyan.dev/ffmpeg/builds/
   - Dézippe, puis ajoute le dossier `bin` au PATH Windows (Paramètres → Variables d'environnement)
   - Vérifie avec `ffmpeg -version` et `ffplay -version` dans un terminal

2. **Python 3.10+** si pas déjà installé

3. **Dépendances Python** :
   ```
   pip install pynput
   ```

## Configuration

Aucune IP à configurer manuellement : le client découvre automatiquement les PC serveurs disponibles sur le réseau local.

## Pare-feu Windows

Sur le PC **serveur**, autorise les ports nécessaires (entrée) :
```
netsh advfirewall firewall add rule name="RemotePlayInput" dir=in action=allow protocol=UDP localport=5001
netsh advfirewall firewall add rule name="RemotePlayDiscovery" dir=in action=allow protocol=UDP localport=5002
netsh advfirewall firewall add rule name="RemotePlayConnect" dir=in action=allow protocol=UDP localport=5003
```

Sur le PC **client**, autorise le port UDP `5000` en entrée (pour recevoir la vidéo) :
```
netsh advfirewall firewall add rule name="RemotePlayVideo" dir=in action=allow protocol=UDP localport=5000
```
(à lancer dans un `cmd` en mode Administrateur, sur les deux PC)

## Lancement

1. Sur le PC **serveur** (gaming) : `python server.py`
   → Il tourne en arrière-plan et attend qu'un client se connecte.

2. Sur le PC **client** (contrôle) : `python client.py`
   → Une fenêtre s'ouvre, scanne le réseau, et affiche la liste des PC serveurs trouvés
   → Clique sur le PC voulu → la connexion et le stream démarrent automatiquement

Une fenêtre `ffplay` s'ouvre ensuite avec le flux vidéo. Passe-la en plein écran (Alt+Entrée dans ffplay) pour une meilleure expérience et pour que les coordonnées souris correspondent bien à l'écran distant.

Si aucun PC n'apparaît dans la liste : vérifie que `server.py` tourne bien, que les deux PC sont sur le même réseau WiFi/LAN, et que le pare-feu autorise le port 5002 (découverte) sur le serveur.

## Réglages perf

- `server.py` → `BITRATE = "15M"` : monte à `"25M"` ou `"30M"` si tu es en Ethernet et que le réseau tient (meilleure qualité d'image)
- `server.py` → `"preset", "p1"` : `p1` = plus rapide/moins latence, `p4`-`p7` = meilleure qualité mais plus de latence d'encodage
- Privilégie le **câble Ethernet** entre les deux PC si possible (même sur le même WiFi, la latence WiFi ajoute du jitter)

## Configuration audio (son du jeu inclus dans le stream)

Par défaut, `ENABLE_AUDIO = True` dans `server.py`. FFmpeg a besoin d'une source audio "loopback" (le son qui sort de tes enceintes/casque) pour pouvoir le capturer et l'envoyer au client. Deux options :

**Option A — Stereo Mix (gratuit, intégré à Windows, marche avec la plupart des cartes Realtek)**
1. Clique droit sur l'icône son (barre des tâches) → "Sons" → onglet "Enregistrement"
2. Clique droit dans la liste → coche "Afficher les périphériques désactivés"
3. Si "Stereo Mix" (ou "Mixage stéréo") apparaît → clic droit → "Activer"
4. Si ça n'apparaît pas du tout, ta carte son ne le supporte pas → utilise l'option B

**Option B — VB-CABLE (si Stereo Mix n'existe pas)**
1. Télécharge VB-CABLE (gratuit) : https://vb-audio.com/Cable/
2. Installe-le, redémarre
3. Dans les paramètres son Windows, mets "CABLE Input" comme périphérique de sortie par défaut
   (astuce : active "Écouter ce périphérique" sur "CABLE Output" dans l'onglet Enregistrement si tu veux continuer à entendre le son localement aussi)

**Trouver le nom exact du périphérique à mettre dans `server.py` :**
```
ffmpeg -list_devices true -f dshow -i dummy
```
Cherche la ligne audio correspondante (ex: `"Stereo Mix (Realtek High Definition Audio)"` ou `"CABLE Output (VB-Audio Virtual Cable)"`), et colle-la exactement dans :
```python
AUDIO_DEVICE = "Stereo Mix (Realtek High Definition Audio)"
```

Si tu ne veux pas d'audio du tout, mets simplement `ENABLE_AUDIO = False` dans `server.py`.

## Limitations connues

- Les mouvements souris sont envoyés en position absolue → fonctionne bien en plein écran avec la même résolution des deux côtés ; certains jeux qui utilisent le mouvement relatif "raw input" (FPS notamment) peuvent moins bien réagir
- Pas de gestion automatique de la perte de paquets UDP (au-delà du réseau local, ce ne serait pas adapté)


