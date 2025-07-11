from core.audio.audio_capture import play_audio_winsound, predict_command
from core.tts.piper import send_text_to_tts
from config.settings import translated_phrases, COMMAND_CLASSES
from twi_stuff.translate_and_say import translate_and_play
from utils.say_in_language import say_in_language


def handle_command(language):
    say_in_language("Hello, how may I help you?", language, wait_for_completion=True, priority=1)
    command, transcribed_text = predict_command("audio_capture/user_command.wav", language, duration=4)

    if command != "background":
        confirm_command(language, command)
        return command, transcribed_text
    else:
        say_in_language("Switching to default mode.", language, wait_for_completion=True)
        return "start", transcribed_text


def confirm_command(language, command):
    if command not in ('reading', 'count', 'chat'):
        return
    if language == 'twi':
        translate_and_play(f"You said {command}", wait_for_completion=True)
    else:
        send_text_to_tts(f"{command.capitalize()} mode activated.", wait_for_completion=True)
