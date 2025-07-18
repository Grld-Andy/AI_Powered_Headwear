import cv2
import time
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
cap = None
SELECTED_LANGUAGE = None
AUDIO_COMMAND_MODEL = None
transcribed_text = None

url = "http://10.156.184.165:81/stream"


def initialize_app():
    global SELECTED_LANGUAGE, AUDIO_COMMAND_MODEL, cap

    start_esp32_listener()
    play_audio_winsound("./data/custom_audio/deviceOn1.wav", True)
    SELECTED_LANGUAGE = detect_or_load_language()
    print("Selected language:", SELECTED_LANGUAGE)
    say_in_language("Hello", SELECTED_LANGUAGE, wait_for_completion=True)

    AUDIO_COMMAND_MODEL = load_model(f"./models/{SELECTED_LANGUAGE}/command_classifier.keras")

    # Use default webcam (or ESP32 stream by replacing below)
    # cap = cv2.VideoCapture(0)
    cap = cv2.VideoCapture(url)

    print("[Main] Initialization complete.")


def run_main_loop():
    global awaiting_command, wakeword_processing, transcribed_text
    global last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw, cap

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
            
            set_mode(new_mode)  # Update global mode
            broadcast_mode_update(new_mode)

            awaiting_command = False
            wakeword_detected.clear()

        # Read from camera
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

        # Handle mode logic
        frozen_frame, updated_mode = process_mode(
            current_mode, frame, SELECTED_LANGUAGE,
            last_frame_time, last_depth_time,
            cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text
        )

        # Update global mode if it changed
        if updated_mode != current_mode:
            set_mode(updated_mode)

    cap.release()
    cv2.destroyAllWindows()
