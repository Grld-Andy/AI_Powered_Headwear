import threading
import time
import subprocess
import queue
from config.settings import tts_lock, last_play_time
import tempfile
import os

current_volume = 1.0  # 0.0 to 1.0
tts_queue = queue.Queue()

def get_volume():
    return current_volume

def set_volume(vol):
    global current_volume
    current_volume = max(0.0, min(vol, 1.0))
    print(f"[Volume Set To]: {current_volume:.1f}")

def increase_volume():
    set_volume(current_volume + 0.1)
    send_text_to_tts("Volume increased.", wait_for_completion=False)

def decrease_volume():
    set_volume(current_volume - 0.1)
    send_text_to_tts("Volume decreased.", wait_for_completion=False)

# Worker function to process TTS queue
def _tts_worker():
    while True:
        text, volume = tts_queue.get()
        try:
            print("[Speaking (bg)]:", text)
            # Map volume 0.0-1.0 to 0-100 scale for Pico TTS
            amplitude = int(volume * 100)

            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                temp_wav = fp.name

            # Generate speech
            subprocess.run(['pico2wave', '-w', temp_wav, text], check=True)

            # Play WAV file with aplay
            subprocess.run(['aplay', temp_wav], check=True)

            # Remove temporary file
            os.remove(temp_wav)

        except Exception as e:
            print("TTS Error (background):", e)
        finally:
            tts_queue.task_done()

# Start worker thread
threading.Thread(target=_tts_worker, daemon=True).start()

# Main function to send text to TTS
def send_text_to_tts(text, wait_for_completion=False, priority=0, volume=1):
    global last_play_time

    with tts_lock:
        try:
            if wait_for_completion:
                print("[Speaking]:", text)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    temp_wav = fp.name
                subprocess.run(['pico2wave', '-w', temp_wav, text], check=True)
                subprocess.run(['aplay', temp_wav], check=True)
                os.remove(temp_wav)
            else:
                tts_queue.put((text, volume))

            last_play_time = time.time()
        except Exception as e:
            print("TTS Error:", e)
