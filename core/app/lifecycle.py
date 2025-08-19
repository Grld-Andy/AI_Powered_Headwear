import cv2
import time
import queue
import socket
import requests
import ipaddress
import threading
from core.app.mode_handler import process_mode
from tensorflow.keras.models import load_model
from core.socket.socket_client import start_socket_thread
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command
from core.nlp.language import detect_or_load_language
from core.audio.audio_capture import play_audio_winsound
from config.settings import get_mode, set_mode, get_language, set_language, pc_Ip
from core.socket.gpio_listener import button_listener_thread


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
MJPEG_PORT = 8080
url = f"http://{pc_Ip}:{MJPEG_PORT}/stream"
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
    MJPEG_URL = None
    cap = None
    fail_count = 0

    while True:
        if MJPEG_URL is None:
            host_ip = find_mjpeg_host()
            if host_ip:
                MJPEG_URL = f"http://{host_ip}:{MJPEG_PORT}/?action=stream"
                print(f"✅ Found MJPEG Streamer: {MJPEG_URL}")
                cap = cv2.VideoCapture(MJPEG_URL)
                fail_count = 0
            else:
                time.sleep(2)
                continue

        if cap is not None and cap.isOpened():
            ret, frame = cap.read()

            if ret and frame is not None:
                frame_holder['frame'] = frame
                fail_count = 0
            else:
                fail_count += 1
                print(f"[ESP32 Camera Thread] Failed to read frame ({fail_count}).")

                # force reconnect if too many failures in a row
                if fail_count >= 5:
                    print("[ESP32 Camera Thread] Stream error, reconnecting...")
                    cap.release()
                    cap = None
                    MJPEG_URL = None
                    fail_count = 0

            time.sleep(0.05)
        else:
            MJPEG_URL = None
            time.sleep(1)


def initialize_app():
    global AUDIO_COMMAND_MODEL

    threading.Thread(target=button_listener_thread, daemon=True).start()
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
