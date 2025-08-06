import os
import time
from core.audio.audio_capture import predict_audio, record_audio_to_file  # Assuming you have this
import config.settings as settings
from config.settings import LANG_AUDIO_FILE, LANGUAGES
import config.load_models as load_models_config
from core.database.database import setup_db, get_saved_language, save_language
from utils.say_in_language import say_in_language


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

    # Step 2: Record audio from laptop microphone
    try:
        print("[LANG] Listening via laptop microphone...")
        record_audio_to_file(LANG_AUDIO_FILE, duration=4)  # Record 4 seconds

        # Step 3: Predict language from recorded audio
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

    # Fallback
    return settings.get_language() or "twi"
