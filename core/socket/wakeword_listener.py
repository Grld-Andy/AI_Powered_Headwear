import socket
import threading
from config.settings import wakeword_detected

def start_wakeword_listener():
    HOST = '127.0.0.1'
    PORT = 5050

    def handle_connection(conn):
        try:
            data = conn.recv(1024).decode().strip()
            if "WAKEWORD" in data:
                print("[Listener] Wake word received.")
                wakeword_detected.set()
        except Exception as e:
            print(f"[Listener] Error: {e}")
        finally:
            conn.close()

    def listener_thread():
        print(f"[Listener] Wake word listener running on {HOST}:{PORT}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(5)
            while True:
                conn, _ = server.accept()
                threading.Thread(target=handle_connection, args=(conn,), daemon=True).start()

    threading.Thread(target=listener_thread, daemon=True).start()
