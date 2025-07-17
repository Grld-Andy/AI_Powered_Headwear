from config.settings import set_mode, wakeword_detected
import socket
import threading

def handle_client(conn, addr):
    print(f"[ESP32] Connected from {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break

            command = data.decode().strip().upper()
            print(f"[ESP32] Received: {command}")

            if command == "MODE_VOICE":
                wakeword_detected.set()

            elif command == "MODE_OCR":
                set_mode("reading")  # Set directly to OCR mode

            elif command == "MODE_OBJECT":
                set_mode("count")  # Set directly to object detection

        except Exception as e:
            print(f"[ESP32] Error: {e}")
            break
    conn.close()

def start_esp32_listener(host="0.0.0.0", port=5678):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"[ESP32] Listener started on {host}:{port}")

    def accept_connections():
        while True:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket, addr)).start()

    threading.Thread(target=accept_connections, daemon=True).start()
