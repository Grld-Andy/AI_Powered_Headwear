import os
import time
import requests
from config.settings import tts_lock, last_play_time
from core.audio.audio_capture import play_audio_winsound


def send_text_to_tts(text, wait_for_completion=False, priority=0, volume=1):
    global last_play_time
    if not tts_lock.acquire(blocking=False):
        if not priority:
            return
        # high-priority: try again after a brief wait or force reset
        tts_lock.acquire()
    current_time = time.time()

    if priority == 0 and (current_time - last_play_time < 1.5):
        tts_lock.release()
        return

    url = 'http://localhost:5000'
    outputFilename = 'audio_capture/output.wav'
    payload = {'text': text}

    try:
        response = requests.get(url, params=payload)
        os.makedirs(os.path.dirname(outputFilename), exist_ok=True)
        with open(outputFilename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=128):
                f.write(chunk)
        play_audio_winsound(outputFilename, wait_for_completion)
        last_play_time = time.time()
    except Exception as e:
        print("Exception: ", e)
    finally:
        tts_lock.release()
