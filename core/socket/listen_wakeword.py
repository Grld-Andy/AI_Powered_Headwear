import socket
from config.settings import HOST, PORT, wakeword_detected


def listen_wakeword_socket():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        buffer = b""
        while True:
            data = s.recv(1024)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = line.decode().strip()
                if msg == "WAKEWORD" and not wakeword_detected.is_set():
                    wakeword_detected.set()
