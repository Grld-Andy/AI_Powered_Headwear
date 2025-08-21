import datetime
import threading
import os
from time import time
import cv2
from config.settings import set_language
from core.app.modes.currency_mode import handle_currency_mode
from core.app.modes.current_time_mode import get_current_time
from core.app.modes.digital_services_mode.gps import reverse_geocode_coordinates
from core.app.modes.digital_services_mode.mobile_network import (
    handle_save_contact_mode,
    handle_send_money_mode,
    handle_get_contact_mode
)
from core.app.modes.emergency_mode import trigger_emergency_mode
from core.app.modes.passive_camera_mode import handle_stop_mode
from core.app.modes.vision_mode import handle_vision_mode, run_background_vision, stop_vision, VisionState
from core.app.modes.reading_mode import handle_reading_mode
from core.audio.audio_capture import listen_and_save
from core.database.database import get_device_id
from core.nlp.language import set_preferred_language
from core.nlp.llm_handler import handle_chat_mode
from core.nlp.llm_together_ai import describe_scene_with_gemini
from core.socket.socket_client import send_emergency_alert, send_payment_to_server
from core.tts.piper import decrease_volume, increase_volume
from core.tts.python_ttsx3 import speak
from utils.say_in_language import say_in_language

vision_thread = None
vision_state = VisionState()
current_time = datetime.datetime.now().strftime("%I:%M %p")

# -------------------- Mode Handlers -------------------- #

def handle_start_mode(frame, language):
    global vision_thread, vision_state
    stop_vision.set()
    if vision_thread and vision_thread.is_alive():
        vision_thread.join()
    vis, raw, lt, dt = handle_vision_mode(frame, language, vision_state, passive=False)
    vision_state.cached_depth_vis = vis
    vision_state.cached_depth_raw = raw
    vision_state.last_frame_time = lt
    vision_state.last_depth_time = dt
    return frame, "start"

def handle_stop_vision_mode(frame):
    stop_vision.set()
    if vision_thread and vision_thread.is_alive():
        vision_thread.join()
    return handle_stop_mode(frame), "stop"

def handle_describe_scene_mode(frame, language):
    image_path = os.path.join("data", "captured_image.png")
    os.makedirs("data", exist_ok=True)
    cv2.imwrite(image_path, frame)
    description = describe_scene_with_gemini(image_path)
    say_in_language(f"Scene description: {description}. That is all.", language, wait_for_completion=True)
    return frame, "stop"

# -------------------- Main Dispatcher -------------------- #

def process_mode(current_mode, frame, language, last_frame_time, last_depth_time,
                 cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text):
    if current_mode == "start":
        return handle_start_mode(frame, language)

    elif current_mode == "stop":
        return handle_stop_vision_mode(frame)

    elif current_mode == "count":
        return handle_currency_mode(frame, language), "stop"

    elif current_mode == "reading":
        valid_frozen_frame = frozen_frame if frozen_frame is not None else frame
        return handle_reading_mode(frame, language, valid_frozen_frame), "stop"

    elif current_mode == "reset":
        set_language(set_preferred_language())
        return frame, "stop"

    elif current_mode == "current_location":
        say_in_language(f"Your current location is {reverse_geocode_coordinates(5.304704,-2.002229)}", language, wait_for_completion=True)
        return frame, "stop"

    elif current_mode == "chat":
        handle_chat_mode()
        return frame, "chat"

    elif current_mode == "time":
        get_current_time(language)
        return frame, "stop"

    elif current_mode == "emergency_mode":
        audio_path = "./data/audio_capture/emergency_audio.wav"
        say_in_language("Emergency mode activated. Please describe the situation.", language, wait_for_completion=True)
        listen_and_save(audio_path, duration=5)
        send_emergency_alert(
            device_id=get_device_id(),
            alert_type="Emergency",
            severity="critical",
            latitude=5.304704,
            longitude=-2.002229,
            message=f"Fall detected at {current_time}",
            audio_path=audio_path
        )
        return frame, "stop"

    elif current_mode == "save_contact":
        handle_save_contact_mode(transcribed_text, language)
        return frame, "stop"

    elif current_mode == "get_contact":
        handle_get_contact_mode(language)
        return frame, "stop"

    elif current_mode == "send_money":
        send_payment_to_server(50, "Eno Rice", "0509895421")
        # handle_send_money_mode(transcribed_text, language)
        return frame, "stop"

    elif current_mode == "shutdown":
        time.sleep(3)
        say_in_language("Turning off", language, wait_for_completion=True, priority=1)
        return frozen_frame, "shutdown"

    elif current_mode == "volume_up":
        increase_volume()
        return frozen_frame, "stop"

    elif current_mode == "volume_down":
        decrease_volume()
        return frozen_frame, "stop"

    elif current_mode == "get_device_id":
        device_id = get_device_id()
        say_in_language(f"Your device ID is {device_id}", language, wait_for_completion=True)
        return frozen_frame, "stop"

    elif current_mode == "describe_scene":
        return handle_describe_scene_mode(frame, language)

    return frozen_frame, current_mode
