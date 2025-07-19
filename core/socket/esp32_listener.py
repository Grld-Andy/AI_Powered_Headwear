# esp32_listener.py
from core.app.command_handler import handle_command
from utils.say_in_language import say_in_language
import socket
import threading
import wave
import speech_recognition as sr
from config.settings import get_language, set_mode, get_mode

clients = set()
clients_lock = threading.Lock()

# ---- AUDIO CONTEXT HANDLING ----
recording_context = None

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

def send_command_to_esp32(command):
    with clients_lock:
        for conn in list(clients):
            try:
                conn.sendall((command + "\n").encode("utf-8"))
                print(f"[ESP32] Sent command: {command}")
                return True
            except Exception as e:
                print(f"[ESP32] Failed to send command: {e}")
                clients.discard(conn)
    return False

def wait_for_audio_stream(timeout=10):
    import time
    start_time = time.time()
    buffer = bytearray()
    print("[ESP32] Waiting for audio data stream...")

    while time.time() - start_time < timeout:
        with clients_lock:
            for conn in list(clients):
                try:
                    conn.settimeout(0.5)
                    chunk = conn.recv(4096)
                    if not chunk:
                        continue

                    buffer.extend(chunk)

                    if b"AUDIO_SENT" in buffer:
                        print("[ESP32] AUDIO_SENT detected")
                        idx = buffer.index(b"AUDIO_SENT")
                        return buffer[:idx]

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ESP32] Error while receiving audio: {e}")
                    continue

    print("[ESP32] ❌ Timeout: Audio not received.")
    return None

# ---- MAIN CLIENT HANDLER ----

def handle_client(conn, addr):
    global recording_context

    print(f"[ESP32] Connected from {addr}")
    with clients_lock:
        clients.add(conn)

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            lines = data.decode(errors="ignore").splitlines()

            for line in lines:
                command = line.strip()
                if not command:
                    continue

                print(f"[ESP32] Received: {command}")

                if command.upper() == "GET_MODE":
                    _send_to_client(conn, f"CURRENT_MODE:{get_mode()}")

                elif command.upper().startswith("RECORD_TYPE:"):
                    recording_context = command.split(":", 1)[1].strip().lower()
                    print(f"[ESP32] Recording context set: {recording_context}")

                elif command.upper() == "BEGIN_RECORDING":
                    audio_data = wait_for_audio_stream()
                    if not audio_data:
                        print("[ESP32] ❌ No audio received.")
                        return

                    print("[ESP32] ✅ Audio received. Handling context...")
                    threading.Thread(
                        target=handle_audio_context, 
                        args=(audio_data, recording_context), 
                        daemon=True
                    ).start()

                elif command.upper() == "MODE_VOICE":
                    threading.Thread(
                        target=handle_voice_interaction, 
                        args=(conn,), 
                        daemon=True
                    ).start()

                elif command.upper() == "MODE_LANGUAGE":
                    set_mode("language")
                    broadcast_mode_update("language")

                    say_in_language("Please say your preferred language", get_language(), wait_for_completion=True)
                    _send_to_client(conn, "VOICE_PROMPT_DONE")

                elif command.upper() == "MODE_OCR":
                    set_mode("reading")
                    broadcast_mode_update("reading")

                elif command.upper() == "MODE_OBJECT":
                    set_mode("start")
                    broadcast_mode_update("start")

                elif command.upper() == "MODE_STOP":
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


# ---- HANDLE AUDIO BY CONTEXT ----

def handle_audio_context(audio_data, context):
    if context == "language":
        process_language_audio(audio_data)
    elif context == "voice":
        transcribe_audio(audio_data)
    else:
        print(f"[ESP32] Unknown context: {context}")

def handle_voice_interaction(conn):
    try:
        set_mode("voice")
        broadcast_mode_update("voice")

        say_in_language("Hello, how may I help you?", get_language(), wait_for_completion=True)
        print("[ESP32] 🔊 Prompt done. Requesting ESP32 to begin recording...")

        _send_to_client(conn, "RECORD_TYPE:voice")
        _send_to_client(conn, "BEGIN_RECORDING")
    except Exception as e:
        print(f"[VOICE] Prompt error: {e}")

def process_language_audio(pcm_data, sample_rate=16000):
    try:
        audio_path = "audio_capture/lang_detect.wav"
        with wave.open(audio_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

        from core.audio.audio_capture import predict_audio
        from config import load_models as load_models_config
        from config.settings import LANGUAGES
        from core.database.database import save_language

        lang, confidence = predict_audio(audio_path, load_models_config, LANGUAGES, duration=2)
        print(f'[LANG] You said: {lang} with {confidence*100:.1f}% confidence')

        if lang in ('english', 'twi'):
            say_in_language(f"You chose {lang}", lang)
        else:
            lang = 'twi'
            say_in_language("Could not detect. Defaulting to Twi.", lang)

        save_language(lang)
        set_mode(lang)
        broadcast_mode_update(lang)
    except Exception as e:
        print(f"[LANG] Error processing language: {e}")

def transcribe_audio(pcm_data, sample_rate=16000):
    try:
        wav_path = "audio_capture/user_command.wav"
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

        print("handling command")
        command, text = handle_command(get_language())

        set_mode(command)
        broadcast_mode_update(command)
        print(f"[VOICE] Final Command: {command} | Transcribed: {text}")
        return command
    except Exception as e:
        print(f"[VOICE] Error transcribing: {e}")
        return "background"

# ---- START LISTENER ----

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
