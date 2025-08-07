import threading
from config.settings import set_language
from core.app.modes.currency_mode import handle_currency_mode
from core.app.modes.current_time_mode import get_current_time
from core.app.modes.digital_services_mode.mobile_network import (
    handle_save_contact_mode,
    handle_send_money_mode,
    handle_get_contact_mode
)
from core.app.modes.passive_camera_mode import handle_stop_mode
from core.app.modes.vision_mode import handle_vision_mode, run_background_vision, stop_vision, VisionState
from core.app.modes.reading_mode import handle_reading_mode
from core.nlp.language import set_preferred_language
from core.nlp.llm_handler import handle_chat_mode
from core.tts.piper import decrease_volume, increase_volume
from core.tts.python_ttsx3 import speak
from utils.say_in_language import say_in_language

vision_thread = None
vision_state = VisionState()


def process_mode(current_mode, frame, language, last_frame_time, last_depth_time,
                 cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text):
    global vision_thread, vision_state

    latest = {'frame': frame, 'language': language}

    def get_frame():
        return latest.get('frame')

    def get_language():
        return latest.get('language')

    # Update latest inputs
    latest['frame'] = frame
    latest['language'] = language

    # ACTIVE vision mode ("start")
    if current_mode == "start":
        stop_vision.set()
        if vision_thread and vision_thread.is_alive():
            vision_thread.join()
        vis, raw, lt, dt = handle_vision_mode(frame, language, vision_state, passive=False)
        vision_state.cached_depth_vis = vis
        vision_state.cached_depth_raw = raw
        vision_state.last_frame_time = lt
        vision_state.last_depth_time = dt
        return frame, current_mode

    # STOP vision mode
    elif current_mode == "stop":
        stop_vision.set()
        if vision_thread and vision_thread.is_alive():
            vision_thread.join()
        return handle_stop_mode(frame), current_mode

    # Background vision thread (for passive modes)
    if vision_thread is None or not vision_thread.is_alive():
        stop_vision.clear()
        vision_thread = threading.Thread(
            target=run_background_vision,
            args=(get_frame, get_language, vision_state),
            daemon=True
        )
        vision_thread.start()

    # Other command modes
    if current_mode == "count":
        return handle_currency_mode(frame, language), "start"

    elif current_mode == "reading":
        valid_frozen_frame = frozen_frame if frozen_frame is not None else frame
        return handle_reading_mode(frame, language, valid_frozen_frame), "start"

    elif current_mode == "reset":
        set_language(set_preferred_language())
        return frame, "start"

    elif current_mode == "location":
        return frame, "start"

    elif current_mode == "chat":
        handle_chat_mode()
        return frame, "chat"

    elif current_mode == "time":
        get_current_time(language)
        return frame, "start"

    elif current_mode == "save_contact":
        handle_save_contact_mode(transcribed_text, language)
        return frame, "start"

    elif current_mode == "get_contact":
        handle_get_contact_mode(language)
        return frame, "start"

    elif current_mode == "send_money":
        handle_send_money_mode(transcribed_text, language)
        return frame, "start"

    elif current_mode == "shutdown":
        say_in_language("Turning off", language, wait_for_completion=True, priority=1)
        speak("Shutting down the device now.")
        return frozen_frame, "shutdown"

    elif current_mode == "volume_up":
        increase_volume()
        return frozen_frame, "start"

    elif current_mode == "volume_down":
        decrease_volume()
        return frozen_frame, "start"

    return frozen_frame, current_mode
