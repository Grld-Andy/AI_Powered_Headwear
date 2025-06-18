import cv2
import time
import threading
from tensorflow.keras.models import load_model
from config.settings import wakeword_detected
from core.audio.audio_capture import play_audio_winsound
from core.nlp.language import detect_or_load_language
from core.socket.listen_wakeword import listen_wakeword_socket
from core.app.command_handler import handle_command
from core.app.mode_handler import process_mode
from core.tts.python_ttsx3 import speak
from twi_stuff.translate_and_say import translate_and_play

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


def initialize_app():
    global SELECTED_LANGUAGE, AUDIO_COMMAND_MODEL, cap
    play_audio_winsound("./data/custom_audio/deviceOn1.wav", True)
    SELECTED_LANGUAGE = detect_or_load_language()
    print("Selected language:", SELECTED_LANGUAGE)
    if SELECTED_LANGUAGE == "english":
        speak("Hello")
    elif SELECTED_LANGUAGE == "twi":
        translate_and_play("Hello", wait_for_completion=True)

    AUDIO_COMMAND_MODEL = load_model(f"./models/{SELECTED_LANGUAGE}/command_classifier.keras")
    cap = cv2.VideoCapture(0)
    threading.Thread(target=listen_wakeword_socket, daemon=True).start()


def run_main_loop():
    global awaiting_command, current_mode, wakeword_processing, transcribed_text
    global last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw, cap

    cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)
    frozen_frame = None
    frame_skip = 2
    frame_count = 0

    while True:
        if wakeword_detected.is_set() and not awaiting_command:
            awaiting_command = True
            current_mode, transcribed_text = handle_command(SELECTED_LANGUAGE)
            awaiting_command = False
            wakeword_detected.clear()

        ret, frame = cap.read()
        frame = cv2.resize(frame, (640, 480))
        if not ret:
            break

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
    return
