from core.audio.audio_capture import play_audio_winsound, predict_audio
from core.tts.piper import send_text_to_tts
from config.settings import SELECTED_LANGUAGE, translated_phrases, LANGUAGES, LANG_AUDIO_FILE, LANG_MODEL
from core.database.database import setup_db, get_saved_language, save_language


def detect_or_load_language():
    setup_db()
    lang = get_saved_language()
    # lang = ""
    if lang:
        return lang
    else:
        return set_preferred_language()


def set_preferred_language():
    if not SELECTED_LANGUAGE:
        send_text_to_tts("Please say your preferred language.", wait_for_completion=True)
        play_audio_winsound(f"./{translated_phrases}what language do you prefer.wav", wait_for_completion=True)
    else:
        if SELECTED_LANGUAGE == 'twi':
            play_audio_winsound(f'{translated_phrases}what language do you prefer.wav', wait_for_completion=True)
        else:
            send_text_to_tts("Please say your preferred language.", wait_for_completion=True)

    try:
        print("You can try speaking")
        lang, confidence = predict_audio(LANG_AUDIO_FILE, LANG_MODEL, LANGUAGES, duration=2)
        print(f'[LANG] You said {lang}, I am {confidence * 100}% confident')
        if lang == 'english':
            send_text_to_tts(f"You said {lang}", True)
        elif lang == 'twi':
            play_audio_winsound(f'{translated_phrases}you said twi.wav', wait_for_completion=True)
        else:
            lang = 'twi'
            send_text_to_tts(f"Could not understand, using default language {lang}", True)
        save_language(lang)
        return lang
    except Exception as e:
        print("An error occurred: ", e)
        if SELECTED_LANGUAGE:
            return SELECTED_LANGUAGE
        else:
            return 'twi'
