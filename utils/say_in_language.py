from core.tts.piper import send_text_to_tts
from twi_stuff.translate_and_say import translate_and_play


def say_in_language(text, language, wait_for_completion=False, priority=0, volume=1.0):
    if language == 'twi':
        translate_and_play(text, wait_for_completion)
    else:
        send_text_to_tts(text, wait_for_completion, priority, volume=volume)
