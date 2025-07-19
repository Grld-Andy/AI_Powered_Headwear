from core.audio.audio_capture import play_audio_winsound, predict_audio
from core.tts.piper import send_text_to_tts
from core.socket.esp32_listener import send_command_to_esp32, wait_for_audio_stream
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

    print("[LANG] Requesting ESP32 to start language capture...")

    send_command_to_esp32("MODE_LANGUAGE")

    audio_data = wait_for_audio_stream()
    if not audio_data:
        print("[LANG] No audio received from ESP32.")
        return 'twi'

    # === Save to WAV ===
    audio_path = "audio_capture/lang_detect.wav"
    with wave.open(audio_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_data)

    try:
        lang, confidence = predict_audio(audio_path, settings.load_models_config, settings.LANGUAGES, duration=2)
        print(f'[LANG] You said {lang}, I am {confidence * 100:.2f}% confident')

        if lang in ('english','twi'):
            say_in_language(f"You chose {lang}", lang, wait_for_completion=True)
        else:
            lang = 'twi'
            say_in_language(f"Could not understand, using default language {lang}", lang, wait_for_completion=True)

        save_language(lang)
        return lang
    except Exception as e:
        print("An error occurred: ", e)
        return settings.get_language() or 'twi'

