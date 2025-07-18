from core.app.command_handler import handle_command
from utils.say_in_language import say_in_language

# core/socket/esp32_listener.py

import socket
import threading
import io
import wave
import speech_recognition as sr
from config.settings import get_language, set_mode, get_mode
from core.tts.piper import send_text_to_tts

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
            data = conn.recv(4096)
            if not data:
                break

            lines = data.decode(errors="ignore").splitlines()

            for line in lines:
                command = line.strip().upper()
                if not command:
                    continue

                print(f"[ESP32] Received: {command}")

                if command == "GET_MODE":
                    _send_to_client(conn, f"CURRENT_MODE:{get_mode()}")

                elif command == "MODE_VOICE":
                    threading.Thread(target=handle_voice_interaction, args=(conn,), daemon=True).start()

                elif command == "MODE_OCR":
                    set_mode("reading")
                    broadcast_mode_update("reading")

                elif command == "MODE_OBJECT":
                    set_mode("start")
                    broadcast_mode_update("start")

                elif command == "MODE_STOP":
                    set_mode("stop")
                    broadcast_mode_update("stop")

                elif command == "AUDIO_START":
                    audio_data = receive_audio_stream(conn)
                    if audio_data:
                        threading.Thread(target=transcribe_audio, args=(audio_data,), daemon=True).start()

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


def handle_voice_interaction(conn):
    try:
        set_mode("voice")
        broadcast_mode_update("voice")

        text = "Hello, how may I help you?"
        say_in_language("Hello, how may I help you?", get_language(), wait_for_completion=True, priority=1)
        send_text_to_tts(text, True, priority=1)

        _send_to_client(conn, "VOICE_PROMPT_DONE")
        print("[VOICE] Prompt sent. Waiting for audio...")
    except Exception as e:
        print(f"[VOICE] TTS or prompt error: {e}")


def receive_audio_stream(conn):
    buffer = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break

        if b"AUDIO_END" in chunk:
            end_index = chunk.index(b"AUDIO_END")
            buffer.extend(chunk[:end_index])
            break

        buffer.extend(chunk)

    print(f"[AUDIO] Received {len(buffer)} bytes.")
    return bytes(buffer)


def transcribe_audio(pcm_data, sample_rate=16000):
    try:
        # Save PCM as WAV for command handler
        import wave, io
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        wav_io.seek(0)

        # Save to file
        with open("audio_capture/user_command.wav", "wb") as f:
            f.write(wav_io.read())

        command, text = handle_command(get_language())
        print(f"[VOICE] Final Command: {command} | Transcribed: {text}")
        return command

    except Exception as e:
        print(f"[VOICE] Error processing audio: {e}")
        return "background"


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
