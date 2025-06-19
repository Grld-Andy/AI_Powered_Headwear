import threading
from core.app.modes.currency_mode import handle_currency_mode
from core.app.modes.current_time_mode import get_current_time
from core.app.modes.digital_services_mode.mobile_network import handle_save_contact_mode, handle_send_money_mode, \
    handle_get_contact_mode
from core.app.modes.passive_camera_mode import handle_stop_mode
from core.app.modes.vision_mode import handle_vision_mode, run_background_vision, stop_vision
from core.app.modes.reading_mode import handle_reading_mode
from core.app.modes.volume_control_mode import increase_volume, decrease_volume
from core.nlp.language import set_preferred_language
from core.nlp.llm_handler import handle_chat_mode
from core.tts.python_ttsx3 import speak

vision_thread = None


def process_mode(current_mode, frame, language, last_frame_time, last_depth_time,
                 cached_depth_vis, cached_depth_raw, frozen_frame, transcribed_text):
    global vision_thread

    # Skip starting vision thread if in 'start' or 'stop' mode
    if current_mode in ("start", "stop"):
        if vision_thread and vision_thread.is_alive():
            stop_vision.set()
            vision_thread.join()
        if current_mode == "start":
            return handle_vision_mode(frame, language, last_frame_time, last_depth_time,
                                      cached_depth_vis, cached_depth_raw, volume=1.0), current_mode
        elif current_mode == "stop":
            return handle_stop_mode(frame), current_mode

    # --- Everything else continues below ---

    # Helpers to safely pass latest frame and language to background vision
    latest = {'frame': frame, 'language': language}

    def get_frame():
        return latest.get('frame')

    def get_language():
        return latest.get('language')

    # Update latest inputs
    latest['frame'] = frame
    latest['language'] = language

    # Start vision background mode (only for other modes)
    if vision_thread is None or not vision_thread.is_alive():
        stop_vision.clear()
        vision_thread = threading.Thread(
            target=run_background_vision,
            args=(get_frame, get_language, last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw),
            daemon=True
        )
        vision_thread.start()

    # Handle other modes
    if current_mode == "count":
        return handle_currency_mode(frame, language), "start"

    elif current_mode == "reading":
        return handle_reading_mode(frame, language, frozen_frame), "start"

    elif current_mode == "reset":
        language = set_preferred_language()
        return frame, "start"

    elif current_mode == "location":
        return frame, "start"

    elif current_mode == "chat":
        handle_chat_mode()
        return frame, "chat"

    elif current_mode == "time":
        get_current_time()
        return frame, "start"

    elif current_mode == "save_contact":
        handle_save_contact_mode(transcribed_text)
        return frame, "start"

    elif current_mode == 'get_contact':
        handle_get_contact_mode()
        return frame, "start"

    elif current_mode == "send_money":
        handle_send_money_mode(transcribed_text)
        return frame, "start"

    elif current_mode == "shutdown":
        speak("Shutting down the device now.")
        # os.system("sudo shutdown now")
        return frozen_frame, "shutdown"

    elif current_mode == "volume_up":
        increase_volume()
        return frozen_frame, "start"

    elif current_mode == "volume_down":
        decrease_volume()
        return frozen_frame, "start"

    return frozen_frame, current_mode
