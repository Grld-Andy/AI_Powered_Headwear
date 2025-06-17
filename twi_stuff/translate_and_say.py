from core.audio.audio_capture import play_audio_winsound
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.twi_tts import synthesize_speech

import os


def translate_and_play(text, wait_for_completion=False):
    safe_filename = f"{text}.wav".replace(" ", "_").lower()

    if os.path.exists(safe_filename):
        play_audio_winsound(safe_filename, wait_for_completion)
    else:
        translated = translate_text(text, "en-tw")
        success = synthesize_speech(translated, output_filename=safe_filename)
        if success:
            play_audio_winsound(safe_filename, wait_for_completion)
        else:
            print("❌ Failed to synthesize or play audio.")
