import threading
import time
import pyttsx3
from config.settings import tts_lock, last_play_time

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

current_volume = 1.0
tts_engine.setProperty('volume', current_volume)

def get_volume():
    return current_volume


def set_volume(vol):
    global current_volume
    current_volume = max(0.0, min(vol, 1.0))
    tts_engine.setProperty('volume', current_volume)
    print(f"[Volume Set To]: {current_volume:.1f}")


def increase_volume():
    set_volume(current_volume + 0.1)
    send_text_to_tts("Volume increased.", wait_for_completion=False)


def decrease_volume():
    set_volume(current_volume - 0.1)
    send_text_to_tts("Volume decreased.", wait_for_completion=False)


def _speak_background(text):
    try:
        print("[Speaking (bg)]:", text)
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        print("TTS Error (background):", e)


def send_text_to_tts(text, wait_for_completion=False, volume=1.0):
    global last_play_time

    with tts_lock:
        try:
            tts_engine.setProperty('volume', volume)

            if wait_for_completion:
                print("[Speaking]:", text)
                tts_engine.say(text)
                tts_engine.runAndWait()
            else:
                threading.Thread(target=_speak_background, args=(text,), daemon=True).start()

            last_play_time = time.time()
        except Exception as e:
            print("TTS Error:", e)
