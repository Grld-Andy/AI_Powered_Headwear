from core.audio.audio_capture import predict_audio
import config.settings as settings
from config.settings import LANG_AUDIO_FILE, LANGUAGES
import config.load_models as load_models_config
from core.database.database import setup_db, get_saved_language, save_language
from twi_stuff.translate_and_say import translate_and_play
from utils.say_in_language import say_in_language

from core.socket.esp32_listener import clients, _send_to_client, receive_audio_stream


def detect_or_load_language():
    setup_db()
    lang = get_saved_language()
    return lang if lang else set_preferred_language()


def set_preferred_language():
    # Step 1: Prompt the user to speak their preferred language
    if not settings.get_language():
        say_in_language("Please say your preferred language.", 'english', wait_for_completion=True, priority=1)
        say_in_language("Please, what language do you prefer", 'twi', wait_for_completion=True, priority=1)
    else:
        if settings.get_language() == 'twi':
            say_in_language("Please, what language do you prefer", 'twi', wait_for_completion=True, priority=1)
        else:
            say_in_language("Please say your preferred language.", 'english', wait_for_completion=True, priority=1)

    # Step 2: Send voice prompt request to ESP32
    for conn in list(clients):
        try:
            _send_to_client(conn, "VOICE_PROMPT_DONE")
            print("[LANG] Waiting for ESP32 audio...")

            audio_data = receive_audio_stream(conn)
            if audio_data:
                with open(LANG_AUDIO_FILE, "wb") as f:
                    f.write(audio_data)

                # Step 4: Predict language from audio
                lang, confidence = predict_audio(LANG_AUDIO_FILE, load_models_config, LANGUAGES)
                print(f"[LANG] You said {lang}, I am {confidence * 100:.2f}% confident")

                if lang in ('english', 'twi'):
                    say_in_language(f"You chose {lang}", lang, wait_for_completion=True)
                else:
                    lang = 'twi'
                    say_in_language(f"Could not understand, using default language {lang}", lang, wait_for_completion=True)

                save_language(lang)
                return lang

        except Exception as e:
            print("[LANG] Error during language selection:", e)

    # Fallback if something went wrong
    return settings.get_language() or "twi"
