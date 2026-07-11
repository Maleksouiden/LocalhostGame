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
import queue
import tkinter as tk
from tkinter import ttk
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


def get_native_resolution():
    """Détecte la résolution native de l'écran du PC serveur (Windows uniquement)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return f"{w}x{h}"
    except Exception:
        return None


def select_resolution():
    """Menu interactif pour choisir la résolution du stream (capture + encodage)."""
    native = get_native_resolution()
    presets = ["1920x1080", "2560x1440", "3840x2160"]

    options = []
    if native:
        options.append(native)
    for p in presets:
        if p not in options:
            options.append(p)

    print("[SERVEUR] Configuration de la résolution du stream (capture côté serveur) :")
    for i, val in enumerate(options):
        tags = []
        if val == native:
            tags.append("résolution native détectée")
        if val == RESOLUTION:
            tags.append("actuellement configuré")
        tag_str = f"  <- {', '.join(tags)}" if tags else ""
        print(f"    [{i}] {val}{tag_str}")
    print("    [c] Résolution personnalisée (ex: 1600x900)")

    default_index = options.index(RESOLUTION) if RESOLUTION in options else None
    hint = f"(Entrée = garder {RESOLUTION})" if default_index is not None else "(tape un numéro ou 'c')"

    while True:
        choice = input(f"[SERVEUR] Choix {hint} : ").strip().lower()

        if choice == "" and default_index is not None:
            return options[default_index]
        if choice == "c":
            custom = input("[SERVEUR] Résolution personnalisée (ex: 1600x900) : ").strip()
            if "x" in custom and all(p.isdigit() for p in custom.split("x")):
                return custom
            print("[SERVEUR] Format invalide, réessaie (ex: 1600x900).")
            continue
        if choice.isdigit() and 0 <= int(choice) < len(options):
            return options[int(choice)]

        print("[SERVEUR] Choix invalide, réessaie.")


def get_dshow_audio_devices():
    """Retourne la liste des noms de périphériques audio DirectShow détectés par FFmpeg."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15,
        )
        output = result.stderr
    except Exception as e:
        print("[SERVEUR] Impossible de lister les périphériques audio:", e)
        return []

    devices = []
    in_audio_section = False
    for line in output.splitlines():
        if "DirectShow audio devices" in line:
            in_audio_section = True
            continue
        if "DirectShow video devices" in line:
            in_audio_section = False
            continue
        if in_audio_section and '"' in line:
            name = line.split('"')[1]
            devices.append(name)
    return devices


def select_audio_device(devices):
    """Affiche un menu pour choisir manuellement le périphérique audio à utiliser."""
    if not devices:
        print("[SERVEUR] Aucun périphérique audio détecté sur ce PC.")
        print("[SERVEUR] Voir le README, section 'Configuration audio' (Stereo Mix / VB-CABLE).")
        print("[SERVEUR] → Audio désactivé pour cette session.")
        return None

    print("[SERVEUR] Périphériques audio disponibles :")
    for i, d in enumerate(devices):
        marker = "  <- actuellement configuré" if d == AUDIO_DEVICE else ""
        print(f"    [{i}] {d}{marker}")
    print("    [n] Désactiver l'audio pour cette session")

    default_index = devices.index(AUDIO_DEVICE) if AUDIO_DEVICE in devices else None
    if default_index is not None:
        hint = f"(Entrée = garder \"{AUDIO_DEVICE}\", ou tape un numéro, ou 'n')"
    else:
        hint = "(tape un numéro dans la liste, ou 'n' pour désactiver l'audio)"

    while True:
        choice = input(f"[SERVEUR] Choix {hint} : ").strip().lower()

        if choice == "" and default_index is not None:
            return devices[default_index]
        if choice == "n":
            return None
        if choice.isdigit() and 0 <= int(choice) < len(devices):
            return devices[int(choice)]

        print("[SERVEUR] Choix invalide, réessaie.")


def get_local_ip():
    """Récupère l'IP locale du PC sur le réseau (celle utilisée pour sortir vers internet/LAN)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


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
    cmd += [
        "-f", "gdigrab",
        "-framerate", str(FPS),
        "-probesize", "32",
        "-i", "desktop",
    ]

    # ---- Entrée audio (optionnelle) ----
    if ENABLE_AUDIO:
        cmd += ["-f", "dshow", "-i", f"audio={AUDIO_DEVICE}"]

    # ---- Encodage vidéo ----
    native = get_native_resolution()
    if RESOLUTION != native:
        # Filtre de scale seulement si nécessaire (évite un coût de traitement inutile)
        cmd += ["-vf", f"scale={RESOLUTION}"]

    cmd += [
        "-c:v", "h264_nvenc",
        "-preset", "p1",          # p1 = plus rapide (priorité latence)
        "-tune", "ull",           # ultra low latency
        "-rc", "cbr",
        "-b:v", BITRATE,
        "-g", str(FPS),           # 1 keyframe par seconde
        "-bf", "0",                # pas de B-frames (elles retardent l'envoi)
        "-rc-lookahead", "0",      # pas de look-ahead (évite d'attendre des frames futures)
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
        "-flush_packets", "1",
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


class ServerApp:
    """Interface graphique : configuration (résolution / audio) + statut en direct,
    à la place des prompts en ligne de commande."""

    def __init__(self):
        global RESOLUTION, ENABLE_AUDIO, AUDIO_DEVICE

        self.local_ip = get_local_ip()
        self.log_queue = queue.Queue()
        self.started = False

        self.root = tk.Tk()
        self.root.title("LAN Remote Play - Serveur")
        self.root.geometry("520x520")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        FG, BG, BG2, ACCENT = "white", "#1e1e1e", "#2d2d2d", "#f07317"

        header = tk.Label(self.root, text="🖥  Configuration du serveur",
                           bg=BG, fg=FG, font=("Segoe UI", 13, "bold"))
        header.pack(pady=(15, 5))

        info = tk.Label(self.root,
                         text=f"IP : {self.local_ip}    •    Nom : {SERVER_NAME}",
                         bg=BG, fg="#aaaaaa", font=("Segoe UI", 9))
        info.pack(pady=(0, 15))

        # ---- Résolution ----
        res_frame = tk.Frame(self.root, bg=BG)
        res_frame.pack(fill="x", padx=25, pady=5)
        tk.Label(res_frame, text="Résolution du stream :", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(anchor="w")

        native = get_native_resolution()
        presets = ["1920x1080", "2560x1440", "3840x2160"]
        res_options = []
        if native:
            res_options.append(f"{native} (native)")
        for p in presets:
            if p not in [o.split(" ")[0] for o in res_options]:
                res_options.append(p)
        res_options.append("Personnalisée…")

        self.res_var = tk.StringVar(value=res_options[0])
        res_combo = ttk.Combobox(res_frame, textvariable=self.res_var,
                                  values=res_options, state="readonly", font=("Segoe UI", 10))
        res_combo.pack(fill="x", pady=5)

        self.custom_res_var = tk.StringVar(value=RESOLUTION)
        self.custom_res_entry = tk.Entry(res_frame, textvariable=self.custom_res_var,
                                          font=("Segoe UI", 10))

        def on_res_change(*_):
            if self.res_var.get() == "Personnalisée…":
                self.custom_res_entry.pack(fill="x", pady=(0, 5))
            else:
                self.custom_res_entry.pack_forget()
        res_combo.bind("<<ComboboxSelected>>", on_res_change)

        # ---- Audio ----
        audio_frame = tk.Frame(self.root, bg=BG)
        audio_frame.pack(fill="x", padx=25, pady=5)
        tk.Label(audio_frame, text="Périphérique audio :", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(anchor="w")

        self.log("[SERVEUR] Recherche des périphériques audio...")
        audio_devices = get_dshow_audio_devices() if ENABLE_AUDIO else []
        audio_options = ["Désactiver l'audio"] + audio_devices
        default_audio = AUDIO_DEVICE if AUDIO_DEVICE in audio_devices else (
            audio_devices[0] if audio_devices else "Désactiver l'audio")
        self.audio_var = tk.StringVar(value=default_audio)
        audio_combo = ttk.Combobox(audio_frame, textvariable=self.audio_var,
                                    values=audio_options, state="readonly", font=("Segoe UI", 10))
        audio_combo.pack(fill="x", pady=5)
        if not audio_devices:
            tk.Label(audio_frame, text="Aucun périphérique détecté (voir README, section audio).",
                     bg=BG, fg="#aaaaaa", font=("Segoe UI", 8)).pack(anchor="w")

        # ---- Bouton démarrer ----
        self.start_btn = tk.Button(self.root, text="▶  Démarrer le serveur",
                                    font=("Segoe UI", 11, "bold"), bg=ACCENT, fg="white",
                                    relief="flat", pady=10, command=self.on_start)
        self.start_btn.pack(fill="x", padx=25, pady=15)

        # ---- Zone de statut / logs ----
        tk.Label(self.root, text="Statut :", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=25)
        self.status_text = tk.Text(self.root, height=12, bg=BG2, fg="#dddddd",
                                    font=("Consolas", 9), relief="flat", state="disabled")
        self.status_text.pack(fill="both", expand=True, padx=25, pady=(5, 15))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(150, self.drain_log_queue)

    def log(self, msg):
        """Thread-safe : les threads réseau appellent ceci, l'UI l'affiche via la queue."""
        print(msg)
        self.log_queue.put(msg)

    def drain_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.status_text.configure(state="normal")
            self.status_text.insert("end", msg + "\n")
            self.status_text.see("end")
            self.status_text.configure(state="disabled")
        self.root.after(150, self.drain_log_queue)

    def on_start(self):
        global RESOLUTION, ENABLE_AUDIO, AUDIO_DEVICE

        if self.started:
            return
        self.started = True
        self.start_btn.configure(state="disabled", text="✅ Serveur en cours d'exécution")

        # Résolution
        if self.res_var.get() == "Personnalisée…":
            custom = self.custom_res_var.get().strip()
            if "x" in custom and all(p.isdigit() for p in custom.split("x")):
                RESOLUTION = custom
            else:
                self.log("[SERVEUR] Résolution personnalisée invalide, garde " + RESOLUTION)
        else:
            RESOLUTION = self.res_var.get().split(" ")[0]

        # Audio
        choice = self.audio_var.get()
        if choice == "Désactiver l'audio":
            ENABLE_AUDIO = False
            self.log("[SERVEUR] Audio désactivé, la vidéo seule sera streamée.")
        else:
            ENABLE_AUDIO = True
            AUDIO_DEVICE = choice
            self.log(f"[SERVEUR] Audio activé avec : \"{AUDIO_DEVICE}\"")

        self.log(f"[SERVEUR] Résolution : {RESOLUTION}")
        self.log(f"[SERVEUR] IP du serveur : {self.local_ip}  (garde-la sous la main pour une connexion manuelle)")

        threading.Thread(target=start_discovery_beacon_gui, args=(self,), daemon=True).start()
        threading.Thread(target=start_input_listener_gui, args=(self,), daemon=True).start()
        threading.Thread(target=self.serve_loop, daemon=True).start()

    def serve_loop(self):
        while True:
            client_ip = wait_for_client_gui(self)
            start_video_stream_gui(self, client_ip)
            self.log("[SERVEUR] Stream terminé, en attente d'une nouvelle connexion...")

    def on_close(self):
        # Le process ffmpeg éventuellement en cours s'arrêtera avec le process Python
        self.root.destroy()
        import os
        os._exit(0)

    def run(self):
        self.root.mainloop()


def start_discovery_beacon_gui(app):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))
    app.log(f"[SERVEUR] Beacon de découverte actif sur le port {DISCOVERY_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        if data == b"REMOTEPLAY_DISCOVER":
            reply = json.dumps({"name": SERVER_NAME}).encode("utf-8")
            sock.sendto(reply, addr)
            app.log(f"[SERVEUR] Découvert par {addr[0]}")


def wait_for_client_gui(app):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT + 1))
    app.log("[SERVEUR] En attente qu'un client clique pour se connecter...")
    while True:
        data, addr = sock.recvfrom(1024)
        if data == b"REMOTEPLAY_CONNECT":
            app.log(f"[SERVEUR] Client connecté : {addr[0]}")
            sock.close()
            return addr[0]


def start_video_stream_gui(app, client_ip):
    app.log("[SERVEUR] Démarrage du stream vidéo" + (" + audio" if ENABLE_AUDIO else "") + f" vers {client_ip}")
    start_video_stream(client_ip)


def start_input_listener_gui(app):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", INPUT_PORT))
    app.log(f"[SERVEUR] Écoute des inputs sur le port {INPUT_PORT}")
    while True:
        data, _ = sock.recvfrom(4096)
        try:
            event = json.loads(data.decode("utf-8"))
            apply_input_event(event)
        except Exception as e:
            app.log(f"[SERVEUR] Erreur input: {e}")


if __name__ == "__main__":
    app = ServerApp()
    app.run()
