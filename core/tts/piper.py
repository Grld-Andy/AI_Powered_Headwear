import threading
import time
import pyttsx3
from config.settings import tts_lock, last_play_time

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)
tts_engine.setProperty('volume', 1.0)

def _speak_background(text):
    try:
        print("[Speaking]: ", text)
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print("TTS Error (background):", e)

def send_text_to_tts(text, wait_for_completion=False, priority=0, volume=1):
    global last_play_time

    tts_lock.acquire()  # Remove blocking check for now

    try:
        tts_engine.setProperty('volume', volume)

        if wait_for_completion:
            print("[Speaking]: ", text)
            tts_engine.say(text)
            tts_engine.runAndWait()
        else:
            threading.Thread(target=_speak_background, args=(text,), daemon=True).start()

        last_play_time = time.time()
    except Exception as e:
        print("TTS Error:", e)
    finally:
        tts_lock.release()
