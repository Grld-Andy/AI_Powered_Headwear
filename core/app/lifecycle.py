import cv2
import time
import threading
from core.app.mode_handler import process_mode
from tensorflow.keras.models import load_model
from core.socket.socket_client import start_socket_thread
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command
from core.nlp.language import detect_or_load_language
from core.audio.audio_capture import play_audio_winsound
from config.settings import get_mode, set_mode, get_language, set_language, pc_Ip
# from core.socket.gpio_listener import button_listener_thread


# Global state variables
awaiting_command = False
wakeword_processing = False
last_frame_time = 0
last_depth_time = 0
cached_depth_vis = None
cached_depth_raw = None
AUDIO_COMMAND_MODEL = None
transcribed_text = None

# ESP32 stream URL
url = f"http://{pc_Ip}:81/stream"
frame_holder = {'frame': None}


def esp32_mjpeg_stream_thread(url, frame_holder):
    cap = cv2.VideoCapture(0)
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
    global AUDIO_COMMAND_MODEL

    # threading.Thread(target=button_listener_thread, daemon=True).start()
    play_audio_winsound("./data/custom_audio/deviceOn1.wav", True)
    set_language(detect_or_load_language())
    SELECTED_LANGUAGE = get_language()
    print("Selected language:", SELECTED_LANGUAGE)
    say_in_language("Hello", SELECTED_LANGUAGE, wait_for_completion=True)

    AUDIO_COMMAND_MODEL = load_model(f"./models/{SELECTED_LANGUAGE}/command_classifier.keras")

    print("[Main] Initialization complete.")


def run_main_loop():
    global awaiting_command, wakeword_processing, transcribed_text
    global last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw
    start_socket_thread()
    threading.Thread(target=esp32_mjpeg_stream_thread, args=(0, frame_holder), daemon=True).start()

    cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)
    frozen_frame = None
    frame_skip = 2
    frame_count = 0

    key_mode_map = {
        ord('o'): "start",
        ord('s'): "stop",
        ord('r'): "reading",
        ord('l'): "reset",
        ord('g'): "current_location",
        ord('c'): "chat",
        ord('v'): "voice",
        ord('t'): "time",
        ord('e'): "emergency_mode",
        ord('n'): "save_contact",
        ord('m'): "send_money",
        ord('q'): "shutdown",
        ord('i'): "get_device_id",
        ord('d'): "describe_scene",
    }

    while True:
        current_mode = get_mode()

        # Get latest camera frame (if using camera)
        frame = frame_holder.get('frame')
        if frame is None:
            time.sleep(0.05)
            continue

        frame = cv2.resize(frame, (640, 480))
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        # Get key input
        key = cv2.waitKey(1) & 0xFF
        if key in key_mode_map:
            new_mode = key_mode_map[key]
            print(f"[KEYBOARD] Key '{chr(key)}' pressed. Switching to mode: {new_mode}")
            set_mode(new_mode)

            if new_mode == "voice":
                got_mode, transcribed_text = handle_command(get_language())
                set_mode(got_mode)

        if key == ord('q') or current_mode == "shutdown":
            break

        # Handle mode logic
        frozen_frame, updated_mode = process_mode(
            current_mode, frame, get_language(),
            last_frame_time, last_depth_time,
            cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text
        )

        if updated_mode != current_mode:
            set_mode(updated_mode)

    cv2.destroyAllWindows()
