import cv2
import time
import threading
from tensorflow.keras.models import load_model
from config.settings import wakeword_detected, esp32_connected  # <-- Add esp32_connected
from core.audio.audio_capture import play_audio_winsound
from core.nlp.language import detect_or_load_language
from core.app.command_handler import handle_command
from core.app.mode_handler import process_mode
from utils.say_in_language import say_in_language

# Global state variables
awaiting_command = False
current_mode = "start"
wakeword_processing = False
last_frame_time = 0
last_depth_time = 0
cached_depth_vis = None
cached_depth_raw = None
cap = None
SELECTED_LANGUAGE = None
AUDIO_COMMAND_MODEL = None
transcribed_text = None
url = "http://10.156.184.165:81/stream"

def initialize_app():
    global SELECTED_LANGUAGE, AUDIO_COMMAND_MODEL, cap

    play_audio_winsound("./data/custom_audio/deviceOn1.wav", True)
    SELECTED_LANGUAGE = detect_or_load_language()
    print("Selected language:", SELECTED_LANGUAGE)
    say_in_language("Hello", SELECTED_LANGUAGE, wait_for_completion=True)

    AUDIO_COMMAND_MODEL = load_model(f"./models/{SELECTED_LANGUAGE}/command_classifier.keras")

    # You can use USB webcam, default cam, or ESP32 stream
    cap = cv2.VideoCapture(0)
    # cap = cv2.VideoCapture(url)

    print("[Main] Initialization complete.")


def run_main_loop():
    global awaiting_command, current_mode, wakeword_processing, transcribed_text
    global last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw, cap

    cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)
    frozen_frame = None
    frame_skip = 2
    frame_count = 0
    last_status_print = 0

    while True:
        now = time.time()
        if now - last_status_print > 5:  # Print every 5 seconds
            if esp32_connected.is_set():
                print("✅ ESP32 microphone is connected.")
            else:
                print("❌ ESP32 microphone is not connected.")
            last_status_print = now

        if wakeword_detected.is_set() and not awaiting_command:
            awaiting_command = True
            current_mode, transcribed_text = handle_command(SELECTED_LANGUAGE)
            awaiting_command = False
            wakeword_detected.clear()

        ret, frame = cap.read()
        if not ret or frame is None:
            print("Warning: Could not read from camera. Reinitializing...")
            cap.release()
            time.sleep(0.5)
            cap = cv2.VideoCapture(0)
            continue

        frame = cv2.resize(frame, (640, 480))
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or current_mode == "shutdown":
            break

        frozen_frame, current_mode = process_mode(
            current_mode, frame, SELECTED_LANGUAGE,
            last_frame_time, last_depth_time,
            cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text
        )

    cap.release()
    cv2.destroyAllWindows()
