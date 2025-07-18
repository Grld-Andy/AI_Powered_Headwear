import cv2
import time
import threading
import numpy as np

from core.app.mode_handler import process_mode
from tensorflow.keras.models import load_model
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command
from core.nlp.language import detect_or_load_language
from core.audio.audio_capture import play_audio_winsound
from config.settings import wakeword_detected, get_mode, set_mode
from core.socket.esp32_listener import start_esp32_listener, broadcast_mode_update

# Global state variables
awaiting_command = False
wakeword_processing = False
last_frame_time = 0
last_depth_time = 0
cached_depth_vis = None
cached_depth_raw = None
SELECTED_LANGUAGE = None
AUDIO_COMMAND_MODEL = None
transcribed_text = None

# ESP32 stream URL
url = "http://10.156.184.165:81/stream"
frame_holder = {'frame': None}


def esp32_mjpeg_stream_thread(url, frame_holder):
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print(f"[ESP32 Camera Thread] Failed to open stream: {url}")
        return

    while True:
        ret, frame = cap.read()
        if ret and frame is not None:
            frame_holder['frame'] = frame
        else:
            print("[ESP32 Camera Thread] Failed to read frame. Retrying...")
            time.sleep(0.1)


def initialize_app():
    global SELECTED_LANGUAGE, AUDIO_COMMAND_MODEL

    start_esp32_listener()
    play_audio_winsound("./data/custom_audio/deviceOn1.wav", True)
    SELECTED_LANGUAGE = detect_or_load_language()
    print("Selected language:", SELECTED_LANGUAGE)
    say_in_language("Hello", SELECTED_LANGUAGE, wait_for_completion=True)

    AUDIO_COMMAND_MODEL = load_model(f"./models/{SELECTED_LANGUAGE}/command_classifier.keras")

    # Start the ESP32 camera streaming thread
    threading.Thread(target=esp32_mjpeg_stream_thread, args=(url, frame_holder), daemon=True).start()

    print("[Main] Initialization complete.")


def run_main_loop():
    global awaiting_command, wakeword_processing, transcribed_text
    global last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw

    cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)
    frozen_frame = None
    frame_skip = 2
    frame_count = 0

    while True:
        current_mode = get_mode()  # Always get the latest mode

        # Wake word triggered
        if wakeword_detected.is_set() and not awaiting_command:
            awaiting_command = True
            new_mode, transcribed_text = handle_command(SELECTED_LANGUAGE)
            set_mode(new_mode)
            broadcast_mode_update(new_mode)
            awaiting_command = False
            wakeword_detected.clear()

        # Get the latest frame from ESP32
        frame = frame_holder.get('frame')
        if frame is None:
            print("Waiting for ESP32 frame...")
            time.sleep(0.05)
            continue

        frame = cv2.resize(frame, (640, 480))
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or current_mode == "shutdown":
            break

        # Handle mode logic
        frozen_frame, updated_mode = process_mode(
            current_mode, frame, SELECTED_LANGUAGE,
            last_frame_time, last_depth_time,
            cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text
        )

        if updated_mode != current_mode:
            set_mode(updated_mode)

    cv2.destroyAllWindows()
