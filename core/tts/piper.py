import threading
import time
import subprocess
import queue
import tempfile
import os

# Try to import shared settings, but provide safe defaults
try:
    from config.settings import tts_lock, last_play_time
except ImportError:
    tts_lock = threading.Lock()
    last_play_time = 0

current_volume = 1.0  # 0.0 to 1.0
tts_queue = queue.PriorityQueue()  # supports priority messages

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
        priority, text, volume = tts_queue.get()
        temp_wav = None  # ensure defined for finally
        try:
            print("[Speaking (bg)]:", text)

            # Sanitize text (UTF-8 safe)
            clean_text = text.encode("utf-8", errors="ignore").decode("utf-8")

            # Temp WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                temp_wav = fp.name

            # Delete if a stale file somehow exists
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except FileNotFoundError:
                    pass

            # Generate speech (set language to English, change if needed)
            subprocess.run(['pico2wave', '-l', 'en-US', '-w', temp_wav, clean_text], check=True)

            # Play WAV file with aplay
            subprocess.run(['aplay', temp_wav], check=True)

        except Exception as e:
            print("TTS Error (background):", e)
        finally:
            # Cleanup even on error
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception as cleanup_err:
                    print("Cleanup error (background):", cleanup_err)
            tts_queue.task_done()

# Start worker thread
threading.Thread(target=_tts_worker, daemon=True).start()

# Main function to send text to TTS
def send_text_to_tts(text, wait_for_completion=False, priority=5, volume=1):
    global last_play_time

    with tts_lock:
        temp_wav = None  # ensure defined for finally if we go sync path
        try:
            if wait_for_completion:
                print("[Speaking]:", text)
                clean_text = text.encode("utf-8", errors="ignore").decode("utf-8")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
                    temp_wav = fp.name

                # Delete if a stale file somehow exists
                if os.path.exists(temp_wav):
                    try:
                        os.remove(temp_wav)
                    except FileNotFoundError:
                        pass

                subprocess.run(['pico2wave', '-l', 'en-US', '-w', temp_wav, clean_text], check=True)
                subprocess.run(['aplay', temp_wav], check=True)

                # Clean up
                if os.path.exists(temp_wav):
                    try:
                        os.remove(temp_wav)
                    except Exception as cleanup_err:
                        print("Cleanup error (sync):", cleanup_err)
            else:
                # Lower priority = play sooner
                tts_queue.put((priority, text, volume))

            last_play_time = time.time()
        except Exception as e:
            print("TTS Error:", e)
