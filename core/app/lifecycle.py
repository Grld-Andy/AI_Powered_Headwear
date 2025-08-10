import cv2
import time
import threading
import socket
import ipaddress
import queue
import requests

from core.app.mode_handler import process_mode
from tensorflow.keras.models import load_model
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command
from core.nlp.language import detect_or_load_language
from core.audio.audio_capture import play_audio_winsound
from config.settings import get_mode, set_mode, get_language, set_language
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

# MJPEG Streamer default port
MJPEG_PORT = 8080
frame_holder = {'frame': None}


# ----------------- AUTO-DETECTION CODE -----------------
SCAN_TIMEOUT = 0.3
found_hosts = queue.Queue()

def get_local_ip():
    """Get the Raspberry Pi's local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def check_host(ip):
    """Check if MJPEG Streamer is running on this IP."""
    url = f"http://{ip}:{MJPEG_PORT}/?action=stream"
    try:
        r = requests.get(url, timeout=SCAN_TIMEOUT, stream=True)
        if r.status_code == 200:
            found_hosts.put(ip)
    except:
        pass

def find_mjpeg_host():
    """Scan the local network for an MJPEG Streamer server."""
    local_ip = get_local_ip()
    net = ipaddress.ip_network(local_ip + "/24", strict=False)
    threads = []

    print(f"🔍 Scanning network {net} for MJPEG Streamer on port {MJPEG_PORT}...")

    for ip in net.hosts():
        ip_str = str(ip)
        if ip_str == local_ip:
            continue
        t = threading.Thread(target=check_host, args=(ip_str,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if not found_hosts.empty():
        return found_hosts.get()
    return None
# -------------------------------------------------------


def esp32_mjpeg_stream_thread(frame_holder):
    host_ip = find_mjpeg_host()
    if not host_ip:
        print("❌ Could not find MJPEG Streamer on the network.")
        return

    mpeg_url = f"http://{host_ip}:{MJPEG_PORT}/?action=stream"
    print(f"✅ Found MJPEG Streamer: {mpeg_url}")

    cap = cv2.VideoCapture(mpeg_url)
    if not cap.isOpened():
        print(f"[ESP32 Camera Thread] Failed to open stream: {mpeg_url}")
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

    threading.Thread(target=esp32_mjpeg_stream_thread, args=(frame_holder,), daemon=True).start()

    cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)
    frozen_frame = None
    frame_skip = 2
    frame_count = 0

    key_mode_map = {
        ord('v'): "voice",
        ord('r'): "reading",
        ord('o'): "start",
        ord('s'): "stop",
        ord('l'): "reset",
        ord('q'): "shutdown"
    }

    while True:
        current_mode = get_mode()

        # Get latest camera frame
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
                print("Awaiting your command")
                say_in_language("Hello, how may I help you?", get_language(), priority=1, wait_for_completion=True)
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
