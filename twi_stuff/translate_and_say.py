import re
from core.audio.audio_capture import play_audio_winsound
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.twi_tts import synthesize_speech
import os


def translate_and_play(text, wait_for_completion=False):
    if 'scene_description' not in text:
        safe_filename = f"data/twi/{re.sub(r'[^a-zA-Z0-9_]', '', text.replace(' ', '_')).lower()}.wav"
    else:
        safe_filename = f"data/twi/scene_description.wav"
    print("Translating and playing:", text)

    if os.path.exists(safe_filename):
        print('file exists')
        play_audio_winsound(safe_filename, wait_for_completion)
    else:
        print('file does not exist, translating and synthesizing')
        translated = translate_text(text, "en-tw")
        success = synthesize_speech(translated, output_filename=safe_filename)
        if success:
            print("✅ Successfully synthesized and saved audio.")
            play_audio_winsound(safe_filename, wait_for_completion)
        else:
            print("❌ Failed to synthesize or play audio.")
