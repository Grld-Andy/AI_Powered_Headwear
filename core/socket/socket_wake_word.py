import socket
import threading
import time
import numpy as np
import sounddevice as sd
import librosa
from collections import deque
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Constants
HOST = 'localhost'
FS = 44100
PORT = 1234
WINDOW_DURATION = 2  # seconds
STRIDE_DURATION = 0.5  # seconds
BUFFER_DURATION = 5  # seconds
N_MFCC = 40
MAX_TIMESTEPS = 100
WAKE_CONFIDENCE_THRESHOLD = 0.95
COOLDOWN_SECS = 3
MODEL_PATH = "../../models/WWD.keras"
CLASS_NAMES = ["Wake Word NOT Detected", "Wake Word Detected"]

# Global audio buffer
audio_buffer = deque(maxlen=int(FS * BUFFER_DURATION))

# Load model once
model = load_model(MODEL_PATH)


# Audio stream callback
def audio_callback(indata, frames, time_info, status):
    if status:
        print("[Audio] Status:", status)
    audio_buffer.extend(indata[:, 0])  # Mono channel


# Start audio input stream once
stream = sd.InputStream(callback=audio_callback, channels=1, samplerate=FS)
stream.start()


# Detection logic per client
def wake_word_detection(model, client_socket, stop_event):
    print("[WakeWord Server] Started wake word detection for client.")
    stride_samples = int(FS * STRIDE_DURATION)
    window_samples = int(FS * WINDOW_DURATION)
    last_detected_time = 0
    i = 0

    while not stop_event.is_set():
        if len(audio_buffer) >= window_samples:
            # Get latest audio window
            audio_segment = np.array(list(audio_buffer)[-window_samples:])
            mfcc = librosa.feature.mfcc(y=audio_segment, sr=FS, n_mfcc=N_MFCC).T
            mfcc_padded = pad_sequences([mfcc], maxlen=MAX_TIMESTEPS, dtype='float32', padding='post',
                                        truncating='post')

            prediction = model.predict(mfcc_padded, verbose=0)
            pred_class = np.argmax(prediction)
            confidence = prediction[0][pred_class]

            if pred_class == 1 and confidence > WAKE_CONFIDENCE_THRESHOLD:
                now = time.time()
                if now - last_detected_time > COOLDOWN_SECS:
                    last_detected_time = now
                    print(f"✅ Wake Word Detected ({i}) - Confidence: {confidence:.4f}")
                    i += 1
                    try:
                        client_socket.sendall(b"WAKEWORD\n")
                    except (BrokenPipeError, ConnectionResetError):
                        print("[WakeWord Server] Client disconnected during send.")
                        stop_event.set()
                        break
            else:
                print(f"❌ Wake Word NOT Detected - Confidence: {confidence:.4f}")

        time.sleep(STRIDE_DURATION)

    print("[WakeWord Server] Stopped detection thread for client.")


# Handle individual client connection
def handle_client(conn, addr):
    print(f"[WakeWord Server] Client connected from {addr}")
    stop_event = threading.Event()
    try:
        detect_thread = threading.Thread(target=wake_word_detection, args=(model, conn, stop_event), daemon=True)
        detect_thread.start()
        while not stop_event.is_set():
            time.sleep(1)  # Could receive commands here
    except Exception as e:
        print(f"[WakeWord Server] Exception: {e}")
    finally:
        stop_event.set()
        conn.close()
        print(f"[WakeWord Server] Client {addr} disconnected.")


# Main server loop
def run_server():
    print("[WakeWord Server] Model loaded. Ready for connections.")
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
            print("\n[WakeWord Server] Shutting down.")
        finally:
            stream.stop()
            stream.close()


if __name__ == "__main__":
    run_server()
