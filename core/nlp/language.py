from core.audio.audio_capture import predict_audio
from core.tts.piper import send_text_to_tts
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
        send_text_to_tts("Please say your preferred language.", wait_for_completion=True)
        translate_and_play("Please, what language do you prefer", wait_for_completion=True)
    else:
        if settings.get_language() == 'twi':
            translate_and_play("Please, what language do you prefer", wait_for_completion=True)
        else:
            send_text_to_tts("Please say your preferred language.", wait_for_completion=True)

    # Step 2: Send voice prompt request to ESP32
    for conn in list(clients):  # Use a copy to avoid concurrency issues
        try:
            _send_to_client(conn, "VOICE_PROMPT_DONE")  # ESP32 will send AUDIO_START + audio + AUDIO_END
            print("[LANG] Waiting for ESP32 audio...")

            # Step 3: Receive audio from ESP32
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
