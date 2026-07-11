"""
client.py - A lancer sur le PC "client" (celui depuis lequel tu vas jouer)

Ce script :
  1. Scanne le réseau local pour trouver les PC "serveur" disponibles (broadcast)
  2. Affiche une fenêtre avec la liste des PC trouvés -> clique dessus pour te connecter
  3. Lance ffplay pour recevoir et afficher le flux vidéo en basse latence
  4. Capture ta souris/clavier et envoie les événements au serveur en UDP

Prérequis :
  - FFmpeg installé et accessible dans le PATH (ffplay est inclus avec ffmpeg)
  - pip install pynput
  - tkinter (inclus avec Python sous Windows par défaut)
"""

import subprocess
import socket
import json
import threading
import time
import tkinter as tk
from pynput import mouse, keyboard

# ==================== CONFIGURATION ====================
DISCOVERY_PORT = 5002
CONNECT_PORT = 5003
VIDEO_PORT = 5000
INPUT_PORT = 5001
RESOLUTION = "1920x1080"
SCAN_TIMEOUT = 2.0
# =========================================================

SCREEN_W, SCREEN_H = map(int, RESOLUTION.split("x"))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SERVER_IP = None


def send_event(event: dict):
    try:
        sock.sendto(json.dumps(event).encode("utf-8"), (SERVER_IP, INPUT_PORT))
    except Exception as e:
        print("[CLIENT] Erreur envoi input:", e)


def start_video_player():
    """Lance ffplay en mode basse latence pour afficher le flux reçu."""
    cmd = [
        "ffplay",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-framedrop",
        "-probesize", "32",
        "-analyzeduration", "0",
        "-sync", "ext",
        "-f", "mpegts",
        f"udp://0.0.0.0:{VIDEO_PORT}",
    ]
    print("[CLIENT] Ouverture du flux vidéo...")
    subprocess.Popen(cmd)


# ---------------- Souris ----------------
def on_move(x, y):
    # x,y sont relatifs à la fenêtre ffplay ; ici on envoie tel quel
    # (fonctionne bien si ffplay est en plein écran sur un écran de même résolution)
    send_event({"type": "mouse_move", "x": x, "y": y})


def on_click(x, y, button, pressed):
    send_event({"type": "mouse_click", "button": button.name, "pressed": pressed})


def on_scroll(x, y, dx, dy):
    send_event({"type": "mouse_scroll", "dx": dx, "dy": dy})


# ---------------- Clavier ----------------
def on_press(key):
    send_event({"type": "key", "key": _key_to_str(key), "pressed": True})


def on_release(key):
    send_event({"type": "key", "key": _key_to_str(key), "pressed": False})
    if key == keyboard.Key.esc and _esc_hold.is_set():
        return False  # double-échap pour quitter proprement, voir note ci-dessous


def _key_to_str(key):
    if hasattr(key, "char") and key.char is not None:
        return key.char
    return str(key).replace("Key.", "")


_esc_hold = threading.Event()


# ---------------- Découverte réseau ----------------
def scan_for_servers(timeout=SCAN_TIMEOUT):
    """Envoie un broadcast et collecte les réponses des serveurs disponibles."""
    disc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    disc_sock.settimeout(0.3)

    found = {}
    disc_sock.sendto(b"REMOTEPLAY_DISCOVER", ("255.255.255.255", DISCOVERY_PORT))

    start = time.time()
    while time.time() - start < timeout:
        try:
            data, addr = disc_sock.recvfrom(1024)
            info = json.loads(data.decode("utf-8"))
            found[addr[0]] = info.get("name", addr[0])
        except socket.timeout:
            continue
        except Exception:
            continue

    disc_sock.close()
    return found  # {ip: nom}


def connect_to_server(ip):
    """Envoie le signal de connexion au serveur choisi puis démarre le stream."""
    global SERVER_IP
    SERVER_IP = ip

    connect_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    connect_sock.sendto(b"REMOTEPLAY_CONNECT", (ip, CONNECT_PORT))
    connect_sock.close()

    print(f"[CLIENT] Connexion à {ip}...")
    start_video_player()

    m_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    k_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    m_listener.start()
    k_listener.start()


def show_server_picker():
    """Fenêtre avec la liste des serveurs trouvés, cliquables pour se connecter."""
    root = tk.Tk()
    root.title("Remote Play - Choisir un PC")
    root.geometry("400x350")
    root.configure(bg="#1e1e1e")

    title = tk.Label(root, text="Recherche des PC disponibles...",
                      bg="#1e1e1e", fg="white", font=("Segoe UI", 12, "bold"))
    title.pack(pady=15)

    list_frame = tk.Frame(root, bg="#1e1e1e")
    list_frame.pack(fill="both", expand=True, padx=20)

    def refresh():
        for widget in list_frame.winfo_children():
            widget.destroy()
        title.config(text="Recherche en cours...")
        root.update()

        servers = scan_for_servers()

        if not servers:
            title.config(text="Aucun PC trouvé sur le réseau")
            no_result = tk.Label(list_frame, text="Vérifie que server.py tourne sur l'autre PC,\net que les deux PC sont sur le même réseau.",
                                  bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9))
            no_result.pack(pady=10)
        else:
            title.config(text=f"{len(servers)} PC trouvé(s) - clique pour te connecter")
            for ip, name in servers.items():
                btn = tk.Button(
                    list_frame, text=f"🖥  {name}  ({ip})",
                    font=("Segoe UI", 11), bg="#2d2d2d", fg="white",
                    activebackground="#0a2b59", activeforeground="white",
                    relief="flat", pady=10,
                    command=lambda ip=ip: on_server_clicked(ip, root)
                )
                btn.pack(fill="x", pady=5)

    def on_server_clicked(ip, root):
        root.destroy()
        connect_to_server(ip)

    refresh_btn = tk.Button(root, text="🔄 Rescanner", font=("Segoe UI", 9),
                             bg="#f07317", fg="white", relief="flat",
                             command=refresh)
    refresh_btn.pack(pady=10)

    root.after(100, refresh)
    root.mainloop()


if __name__ == "__main__":
    show_server_picker()

    print("[CLIENT] Capture des inputs en cours. Ferme la fenêtre ffplay ou Ctrl+C pour arrêter.")
    # Garde le programme en vie tant que la connexion est active
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
