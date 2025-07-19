from core.audio.audio_capture import play_audio_winsound, predict_audio
from core.tts.piper import send_text_to_tts
import config.settings as settings
import wave
import config.load_models as load_models_config
from core.database.database import setup_db, get_saved_language, save_language
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.translate_and_say import translate_and_play
from twi_stuff.twi_tts import synthesize_speech
from utils.say_in_language import say_in_language


def detect_or_load_language():
    setup_db()
    lang = get_saved_language()
    # lang = ""
    if lang:
        return lang
    else:
        return set_preferred_language()


def set_preferred_language():
    if not settings.get_language():
        send_text_to_tts("Please say your preferred language.", wait_for_completion=True)
        translate_and_play("Please, what language do you prefer", wait_for_completion=True)
    else:
        if settings.get_language() == 'twi':
            translate_and_play("Please, what language do you prefer", wait_for_completion=True)
        else:
            send_text_to_tts("Please say your preferred language.", wait_for_completion=True)

    lang = get_saved_language()
    if lang:
        return lang
    else:
        print("[LANG] Could not detect language, defaulting to 'twi'")
        return 'twi'
