# LAN Remote Play (Python + FFmpeg/NVENC)

Stream ton écran (60 FPS, 1080p, encodage GPU Nvidia) vers un autre PC sur le même réseau WiFi/LAN, avec contrôle clavier/souris à distance.

## ⚠️ Avant de commencer

Ce script fait le travail à la main avec Python + FFmpeg. Il fonctionne bien, mais reste **moins optimisé et moins robuste** que des solutions dédiées comme **Sunshine + Moonlight** (gratuites, open-source, faites exactement pour ce cas d'usage). Si jamais tu rencontres trop de friction avec ce script (latence input, jeux qui ignorent les clics simulés, coupures réseau...), Sunshine/Moonlight reste la solution de repli recommandée.

## Installation (sur les DEUX PC)

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

## Limitations connues

- Pas d'audio inclus dans cette version (peut être ajouté avec un flux FFmpeg séparé si besoin)
- Les mouvements souris sont envoyés en position absolue → fonctionne bien en plein écran avec la même résolution des deux côtés ; certains jeux qui utilisent le mouvement relatif "raw input" (FPS notamment) peuvent moins bien réagir
- Pas de gestion automatique de la perte de paquets UDP (au-delà du réseau local, ce ne serait pas adapté)
