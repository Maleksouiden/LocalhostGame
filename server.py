"""
server.py - A lancer sur le PC "serveur" (celui qui a le GPU Nvidia et fait tourner le jeu)

Ce script :
  1. Répond aux requêtes de découverte envoyées en broadcast par un client
  2. Capture l'écran et l'encode en H.264 via NVENC (GPU Nvidia) avec FFmpeg, envoie
     le flux vidéo en UDP vers le client qui s'est connecté
  3. Écoute les commandes clavier/souris envoyées par le client et les rejoue localement

Prérequis :
  - FFmpeg installé et accessible dans le PATH (https://www.gyan.dev/ffmpeg/builds/ -> version "full")
  - pip install pynput
"""

import subprocess
import socket
import json
import threading
import platform
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key, KeyCode

# ==================== CONFIGURATION ====================
DISCOVERY_PORT = 5002
VIDEO_PORT = 5000
INPUT_PORT = 5001
RESOLUTION = "1920x1080"
FPS = 60
BITRATE = "15M"              # 15 Mbps, tu peux monter à 25-30M en LAN filaire
SERVER_NAME = platform.node()  # nom de la machine (affiché côté client)

ENABLE_AUDIO = True
# Nom exact du périphérique audio "loopback" (le son qui sort de tes enceintes/casque).
# Pour le trouver, lance dans un terminal :
#   ffmpeg -list_devices true -f dshow -i dummy
# et cherche la ligne du type "Stereo Mix (Realtek High Definition Audio)"
# ou "CABLE Output (VB-Audio Virtual Cable)" si tu utilises VB-CABLE.
AUDIO_DEVICE = "Stereo Mix (Realtek High Definition Audio)"
# =========================================================

mouse = MouseController()
keyboard = KeyboardController()

SCREEN_W, SCREEN_H = map(int, RESOLUTION.split("x"))


def start_discovery_beacon():
    """Écoute les requêtes de découverte broadcast et répond avec son IP/nom."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))
    print(f"[SERVEUR] Beacon de découverte actif sur le port {DISCOVERY_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        if data == b"REMOTEPLAY_DISCOVER":
            reply = json.dumps({"name": SERVER_NAME}).encode("utf-8")
            sock.sendto(reply, addr)
            print(f"[SERVEUR] Découvert par {addr[0]}")


def wait_for_client():
    """Attend qu'un client envoie un signal 'CONNECT' pour récupérer son IP automatiquement."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT + 1))
    print("[SERVEUR] En attente qu'un client clique pour se connecter...")
    while True:
        data, addr = sock.recvfrom(1024)
        if data == b"REMOTEPLAY_CONNECT":
            print(f"[SERVEUR] Client connecté : {addr[0]}")
            sock.close()
            return addr[0]


def start_video_stream(client_ip):
    """Capture l'écran (+ audio si activé) et encode en H.264/AAC puis envoie en UDP au client."""
    cmd = ["ffmpeg"]

    # ---- Entrée vidéo ----
    cmd += ["-f", "gdigrab", "-framerate", str(FPS), "-i", "desktop"]

    # ---- Entrée audio (optionnelle) ----
    if ENABLE_AUDIO:
        cmd += ["-f", "dshow", "-i", f"audio={AUDIO_DEVICE}"]

    # ---- Encodage vidéo ----
    cmd += [
        "-vf", f"scale={RESOLUTION}",
        "-c:v", "h264_nvenc",
        "-preset", "p1",          # p1 = plus rapide (priorité latence)
        "-tune", "ull",           # ultra low latency
        "-rc", "cbr",
        "-b:v", BITRATE,
        "-g", str(FPS),           # 1 keyframe par seconde
        "-pix_fmt", "yuv420p",
    ]

    # ---- Encodage audio (optionnel) ----
    if ENABLE_AUDIO:
        cmd += [
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "48000",
            "-ac", "2",
        ]
    else:
        cmd += ["-an"]  # pas de piste audio

    cmd += [
        "-f", "mpegts",
        f"udp://{client_ip}:{VIDEO_PORT}?pkt_size=1316",
    ]

    print("[SERVEUR] Démarrage du stream vidéo" + (" + audio" if ENABLE_AUDIO else "") + " vers", client_ip)
    subprocess.run(cmd)


def apply_input_event(event):
    """Rejoue localement un événement clavier/souris reçu du client."""
    etype = event.get("type")

    if etype == "mouse_move":
        mouse.position = (event["x"], event["y"])

    elif etype == "mouse_click":
        btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}[event["button"]]
        if event["pressed"]:
            mouse.press(btn)
        else:
            mouse.release(btn)

    elif etype == "mouse_scroll":
        mouse.scroll(event["dx"], event["dy"])

    elif etype == "key":
        key = event["key"]
        try:
            k = Key[key] if key.startswith("Key.") is False and hasattr(Key, key) else KeyCode.from_char(key)
        except Exception:
            k = KeyCode.from_char(key) if len(key) == 1 else None
        if k is not None:
            if event["pressed"]:
                keyboard.press(k)
            else:
                keyboard.release(k)


def start_input_listener():
    """Écoute les paquets d'input envoyés par le client et les applique."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", INPUT_PORT))
    print(f"[SERVEUR] Écoute des inputs sur le port {INPUT_PORT}")
    while True:
        data, _ = sock.recvfrom(4096)
        try:
            event = json.loads(data.decode("utf-8"))
            apply_input_event(event)
        except Exception as e:
            print("[SERVEUR] Erreur input:", e)


if __name__ == "__main__":
    # Beacon de découverte tourne en permanence en arrière-plan
    threading.Thread(target=start_discovery_beacon, daemon=True).start()

    # Écoute des inputs tourne aussi en permanence
    threading.Thread(target=start_input_listener, daemon=True).start()

    # On attend qu'un client clique dessus pour connaître son IP, puis on stream
    while True:
        client_ip = wait_for_client()
        start_video_stream(client_ip)
        print("[SERVEUR] Stream terminé, en attente d'une nouvelle connexion...")
