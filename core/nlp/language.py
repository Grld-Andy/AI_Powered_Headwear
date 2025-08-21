import os
import time
from core.audio.audio_capture import predict_audio, record_audio
import config.settings as settings
from config.settings import LANG_AUDIO_FILE, LANGUAGES
import config.load_models as load_models_config
from core.database.database import get_device_id, setup_db, get_saved_language, save_language
from utils.say_in_language import say_in_language


def detect_or_load_language():
    setup_db()
    lang = get_saved_language()
    return lang if lang else set_preferred_language()

def set_preferred_language():
    # Step 1: Prompt the user to speak their preferred language
    print('language in settings: ', settings.get_language())
    if not settings.get_language():
        say_in_language("Please say your preferred language.", 'english', wait_for_completion=True, priority=1)
        say_in_language("Please, what language do you prefer", 'twi', wait_for_completion=True, priority=1)
    else:
        if settings.get_language() == 'twi':
            say_in_language("Please, what language do you prefer", 'twi', wait_for_completion=True, priority=1)
        else:
            say_in_language("Please say your preferred language.", 'english', wait_for_completion=True, priority=1)

    # Step 2: Record audio from laptop microphone
    try:
        LANG_AUDIO_FILE = "./data/choosing_language.wav"
        print("[LANG] Listening via laptop microphone...", LANG_AUDIO_FILE)
        # record_audio(LANG_AUDIO_FILE, duration=3)  # Record 3 seconds

        # Step 3: Predict language from recorded audio
        lang, confidence = predict_audio(LANG_AUDIO_FILE, load_models_config.LANG_MODEL, LANGUAGES)
        print(f"[LANG] You said {lang}, I am {confidence * 100:.2f}% confident")

        if lang in ('english', 'twi'):
            say_in_language(f"You said {lang}", lang, wait_for_completion=True)
        else:
            lang = 'twi'
            say_in_language(f"Could not understand, using {lang}", lang, wait_for_completion=True)

        save_language(lang)
        return lang

    except Exception as e:
        print("[LANG] Error during language selection:", e)

    # Fallback
    return settings.get_language() or "twi"
