from core.audio.audio_capture import play_audio_winsound, predict_audio
from core.tts.piper import send_text_to_tts
import config.settings as settings
from core.database.database import setup_db, get_saved_language, save_language
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.translate_and_say import translate_and_play
from twi_stuff.twi_tts import synthesize_speech


def detect_or_load_language():
    setup_db()
    lang = get_saved_language()
    # lang = ""
    if lang:
        return lang
    else:
        return set_preferred_language()


def set_preferred_language():
    if not settings.SELECTED_LANGUAGE:
        send_text_to_tts("Please say your preferred language.", wait_for_completion=True)
        translate_and_play("what language do you prefer", wait_for_completion=True)
        # play_audio_winsound(f"./{settings.translated_phrases}what language do you prefer.wav", wait_for_completion=True)
    else:
        if settings.SELECTED_LANGUAGE == 'twi':
            translate_and_play("what language do you prefer", wait_for_completion=True)
            # play_audio_winsound(f'{settings.translated_phrases}what language do you prefer.wav', wait_for_completion=True)
        else:
            send_text_to_tts("Please say your preferred language.", wait_for_completion=True)

    try:
        print("You can try speaking")
        lang, confidence = predict_audio(settings.LANG_AUDIO_FILE, settings.LANG_MODEL, settings.LANGUAGES, duration=2)
        print(f'[LANG] You said {lang}, I am {confidence * 100}% confident')
        if lang == 'english':
            send_text_to_tts(f"You choose {lang}", True)
        elif lang == 'twi':
            translate_and_play("You choose twi", wait_for_completion=True)
            # play_audio_winsound(f'hello.wav', wait_for_completion=True)
        else:
            lang = 'twi'
            translate_and_play(f"Could not understand, using default language {lang}", wait_for_completion=True)
            # send_text_to_tts(f"Could not understand, using default language {lang}", True)
        save_language(lang)
        return lang
    except Exception as e:
        print("An error occurred: ", e)
        if settings.SELECTED_LANGUAGE:
            return settings.SELECTED_LANGUAGE
        else:
            return 'twi'
