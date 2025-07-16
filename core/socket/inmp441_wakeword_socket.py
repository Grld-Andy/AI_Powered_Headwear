import threading
import socket
import time
import numpy as np
import librosa
from collections import deque
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from config.settings import wakeword_detected, esp32_connected  # shared Event flags

# Constants
HOST = '0.0.0.0'
PORT = 1234
FS = 44100
WINDOW_DURATION = 2
STRIDE_DURATION = 0.5
BUFFER_DURATION = 5
N_MFCC = 40
MAX_TIMESTEPS = 100
WAKE_CONFIDENCE_THRESHOLD = 0.95
COOLDOWN_SECS = 3
MODEL_PATH = "../../models/WWD.keras"

# Global audio buffer
audio_buffer = deque(maxlen=int(FS * BUFFER_DURATION))
model = load_model(MODEL_PATH)

def audio_receiver(sock, stop_event):
    bytes_per_sample = 2
    chunk_duration = 0.1
    chunk_size = int(FS * chunk_duration) * bytes_per_sample

    try:
        while not stop_event.is_set():
            data = sock.recv(chunk_size)
            if not data:
                stop_event.set()
                break
            if len(data) < chunk_size:
                continue
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_buffer.extend(samples)
    except Exception as e:
        print(f"[Receiver] Error: {e}")
        stop_event.set()


def wake_word_detection(model, stop_event):
    window_samples = int(FS * WINDOW_DURATION)
    last_detected_time = 0

    while not stop_event.is_set():
        if len(audio_buffer) >= window_samples:
            try:
                audio_segment = np.array(list(audio_buffer)[-window_samples:])
                mfcc = librosa.feature.mfcc(y=audio_segment, sr=FS, n_mfcc=N_MFCC).T
                mfcc_padded = pad_sequences([mfcc], maxlen=MAX_TIMESTEPS, dtype='float32',
                                            padding='post', truncating='post')
                prediction = model.predict(mfcc_padded, verbose=0)
                pred_class = np.argmax(prediction)
                confidence = prediction[0][pred_class]

                if pred_class == 1 and confidence > WAKE_CONFIDENCE_THRESHOLD:
                    now = time.time()
                    if now - last_detected_time > COOLDOWN_SECS:
                        last_detected_time = now
                        print(f"✅ Wake Word Detected - Confidence: {confidence:.4f}")
                        wakeword_detected.set()
                else:
                    print(f"❌ Wake Word NOT Detected - Confidence: {confidence:.4f}")
            except Exception as e:
                print(f"[Detection] Error: {e}")

        time.sleep(STRIDE_DURATION)


def handle_client(conn, addr):
    print(f"[WakeWord Server] 📡 ESP32 connected from {addr}")
    esp32_connected.set()
    stop_event = threading.Event()

    try:
        recv_thread = threading.Thread(target=audio_receiver, args=(conn, stop_event), daemon=True)
        detect_thread = threading.Thread(target=wake_word_detection, args=(model, stop_event), daemon=True)
        recv_thread.start()
        detect_thread.start()

        while not stop_event.is_set():
            time.sleep(1)

    except Exception as e:
        print(f"[Client Handler] Error: {e}")

    finally:
        stop_event.set()
        conn.close()
        esp32_connected.clear()
        print(f"[WakeWord Server] ❌ ESP32 disconnected")


def listen_wakeword_socket():
    print("[WakeWord Server] Starting socket server...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print(f"[WakeWord Server] Listening on {HOST}:{PORT}")

        try:
            while True:
                conn, addr = server_socket.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("[WakeWord Server] Shutdown requested.")


if __name__ == "__main__":
    listen_wakeword_socket()
