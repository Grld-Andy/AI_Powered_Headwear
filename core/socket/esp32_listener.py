# core/socket/esp32_listener.py

import socket
import threading
from config.settings import set_mode, get_mode, wakeword_detected

# Shared list of connected clients
clients = set()
clients_lock = threading.Lock()


def _send_to_client(conn, message):
    try:
        conn.sendall((message + "\n").encode("utf-8"))
    except Exception as e:
        print(f"[ESP32] Send failed: {e}")
        try:
            conn.close()
        except:
            pass
        with clients_lock:
            clients.discard(conn)


def broadcast_mode_update(mode=None):
    """Notify all ESP32 clients of the current mode."""
    if mode is None:
        mode = get_mode()

    message = f"MODE_UPDATE:{mode}"
    with clients_lock:
        dead_clients = []
        for conn in clients:
            try:
                _send_to_client(conn, message)
            except:
                dead_clients.append(conn)
        for dead in dead_clients:
            clients.discard(dead)

    print(f"[ESP32] Broadcasted mode: {mode} to {len(clients)} clients")


def handle_client(conn, addr):
    print(f"[ESP32] Connected from {addr}")
    with clients_lock:
        clients.add(conn)

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break

            lines = data.decode(errors="ignore").splitlines()
            for line in lines:
                command = line.strip().upper()
                if not command:
                    continue

                print(f"[ESP32] Received: {command}")

                # Respond to client-specific request
                if command == "GET_MODE":
                    _send_to_client(conn, f"CURRENT_MODE:{get_mode()}")

                elif command == "MODE_VOICE":
                    wakeword_detected.set()

                elif command == "MODE_OCR":
                    set_mode("reading")
                    broadcast_mode_update("reading")

                elif command == "MODE_OBJECT":
                    set_mode("start")
                    broadcast_mode_update("start")

                elif command == "MODE_STOP":
                    set_mode("stop")
                    broadcast_mode_update("stop")

    except Exception as e:
        print(f"[ESP32] Error: {e}")

    finally:
        print(f"[ESP32] Disconnected: {addr}")
        with clients_lock:
            clients.discard(conn)
        try:
            conn.close()
        except:
            pass


def start_esp32_listener(host="0.0.0.0", port=5678):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[ESP32] Listener started on {host}:{port}")

    def accept_connections():
        while True:
            try:
                conn, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[ESP32] Accept error: {e}")

    threading.Thread(target=accept_connections, daemon=True).start()
