import threading
import time
import heapq
import pyttsx3
from config.settings import tts_lock, last_play_time

# Initialize TTS
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)

# Global volume tracking
current_volume = 1.0
tts_engine.setProperty('volume', current_volume)

# Priority queue and control structures
tts_queue = []
queue_lock = threading.Lock()
queue_not_empty = threading.Condition(queue_lock)


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


def _tts_worker():
    global last_play_time
    while True:
        with queue_not_empty:
            while not tts_queue:
                queue_not_empty.wait()
            priority, timestamp, text, volume = heapq.heappop(tts_queue)

        with tts_lock:
            try:
                tts_engine.setProperty('volume', volume)
                print(f"[Speaking] (priority={priority}):", text)
                tts_engine.say(text)
                tts_engine.runAndWait()
                last_play_time = time.time()
            except Exception as e:
                print("TTS Error:", e)


def send_text_to_tts(text, wait_for_completion=False, priority=0, volume=1.0):
    global last_play_time

    if wait_for_completion:
        with tts_lock:
            try:
                tts_engine.setProperty('volume', volume)
                print(f"[Speaking (sync)] (priority={priority}):", text)
                tts_engine.say(text)
                tts_engine.runAndWait()
                last_play_time = time.time()
            except Exception as e:
                print("TTS Error (sync):", e)
    else:
        with queue_not_empty:
            # Use timestamp for FIFO among same-priority items
            heapq.heappush(tts_queue, (priority, time.time(), text, volume))
            queue_not_empty.notify()


# Start the TTS processing thread
tts_thread = threading.Thread(target=_tts_worker, daemon=True)
tts_thread.start()
