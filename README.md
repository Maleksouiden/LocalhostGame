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

Sur le PC **client**, autorise ces ports UDP en entrée :
```
netsh advfirewall firewall add rule name="RemotePlayVideo" dir=in action=allow protocol=UDP localport=5000
netsh advfirewall firewall add rule name="RemotePlayDiscoveryReply" dir=in action=allow protocol=UDP localport=5004
```
(à lancer dans un `cmd` en mode Administrateur, sur les deux PC)

> **Note Boot Camp (Mac) :** Windows sous Boot Camp classe souvent le réseau WiFi en profil "Public" par défaut, qui est plus restrictif. Vérifie dans Paramètres → Réseau et Internet → WiFi → propriétés de la connexion, que le type de réseau est bien sur **"Privé"**. Les règles `netsh` ci-dessus s'appliquent normalement à tous les profils par défaut, mais ça vaut le coup de vérifier si le souci persiste malgré les règles pare-feu.

## Lancement

1. Sur le PC **serveur** (gaming) : `python server.py`
   → Une fenêtre s'ouvre pour choisir la résolution et le périphérique audio, puis clique sur **"▶ Démarrer le serveur"**.
   → Le statut (découverte, connexion client, stream) s'affiche en direct dans cette même fenêtre.

2. Sur le PC **client** (contrôle) : `python client.py`
   → Une fenêtre s'ouvre, scanne le réseau, et affiche la liste des PC serveurs trouvés
   → Clique sur le PC voulu → la connexion et le stream démarrent automatiquement

Une fenêtre `ffplay` s'ouvre ensuite avec le flux vidéo. Passe-la en plein écran (Alt+Entrée dans ffplay) pour une meilleure expérience et pour que les coordonnées souris correspondent bien à l'écran distant.

Si aucun PC n'apparaît dans la liste : vérifie que `server.py` tourne bien, que les deux PC sont sur le même réseau WiFi/LAN, et que le pare-feu autorise le port 5002 (découverte) sur le serveur.

### Si la connexion se fait (la souris bouge sur le serveur) mais que l'image ne s'affiche pas

C'est presque toujours l'un de ces deux cas :

1. **Le port vidéo UDP 5000 est bloqué en entrée sur le PC client.** Le clic/découverte utilisent d'autres ports (5002-5004), donc ils peuvent fonctionner pendant que 5000 reste bloqué. Vérifie la règle pare-feu client (voir section "Pare-feu Windows" ci-dessus), en particulier sur Mac/Boot Camp où le réseau WiFi est parfois classé en profil "Public".
2. **Message `Circular buffer overrun` dans la console du client.** Ça veut dire que le buffer de réception UDP d'`ffplay` déborde (flux trop rapide pour le buffer par défaut de Windows). `client.py` configure déjà un buffer de réception élargi (64 Mo) pour éviter ça — si le message persiste, essaie de baisser `BITRATE` dans `server.py` (ex: `"8M"`) ou de passer en Ethernet.

## Réglages perf

- `server.py` → `BITRATE = "15M"` : monte à `"25M"` ou `"30M"` si tu es en Ethernet et que le réseau tient (meilleure qualité d'image)
- `server.py` → `"preset", "p1"` : `p1` = plus rapide/moins latence, `p4`-`p7` = meilleure qualité mais plus de latence d'encodage
- Privilégie le **câble Ethernet** entre les deux PC si possible (même sur le même WiFi, la latence WiFi ajoute du jitter)

## Réduire la latence

Le script est déjà réglé pour la latence minimale côté encodage (NVENC ultra low latency, pas de B-frames, pas de look-ahead). Si tu ressens encore de la latence, dans l'ordre d'impact :

1. **Câble Ethernet plutôt que WiFi** — de loin le facteur le plus important. Le WiFi ajoute plusieurs dizaines de ms de latence variable (jitter) même en LAN, un câble direct entre les deux PC (ou via un switch/routeur filaire) élimine ce problème.
2. **Bande 5GHz si WiFi obligatoire** — nettement moins de congestion/latence que la 2.4GHz.
3. **Baisse la résolution du stream** (`select_resolution()` au démarrage) si ton réseau WiFi n'a pas assez de débit pour absorber le bitrate configuré — un stream qui sature la bande passante WiFi crée de la latence par accumulation de paquets.
4. **Baisse le bitrate** (`BITRATE` dans `server.py`) si le réseau n'encaisse pas — un bitrate trop élevé pour la bande passante dispo cause du buffering réseau, donc de la latence, même si la source (NVENC) n'ajoute aucun délai.
5. Vérifie qu'aucune app gourmande en bande passante ne tourne en fond sur les deux PC (mises à jour Windows, cloud sync, etc.)

Sur un LAN filaire avec du NVENC comme ici, on doit pouvoir descendre sous les 15-20ms de latence totale (capture + encodage + réseau + décodage + affichage). Au-delà de 50-60ms perçus, le goulot est presque toujours le réseau (WiFi), pas le script.

## Configuration de la résolution

Le script te demande interactivement, au démarrage, la résolution à utiliser pour la capture/l'encodage (indépendante de l'écran du PC client — le flux s'affiche automatiquement à la bonne taille dans la fenêtre `ffplay`, peu importe si ton Mac est en 2K et le PC serveur en 1080p). Options : résolution native détectée automatiquement, presets courants, ou résolution personnalisée.



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


