from core.audio.audio_capture import play_audio_winsound, predict_command
from core.tts.piper import send_text_to_tts
from config.settings import translated_phrases, COMMAND_CLASSES


def handle_command(language):
    if language == 'twi':
        play_audio_winsound(f"{translated_phrases}hello what can i do for you.wav", wait_for_completion=True)
    else:
        send_text_to_tts("Hi, how may I help you?", wait_for_completion=True, priority=1)

    command, transcribed_text = predict_command("audio_capture/user_command.wav")

    if command != "background":
        confirm_command(language, command)
        return command, transcribed_text
    else:
        if language == 'twi':
            play_audio_winsound(f"{translated_phrases}sorry I did not understand.wav", wait_for_completion=True)
        else:
            send_text_to_tts("Sorry, I did not understand that command.", wait_for_completion=True)

    return "start", transcribed_text


def confirm_command(language, command):
    if language == 'twi':
        play_audio_winsound(f"{translated_phrases}you said {command}.wav", wait_for_completion=True)
    else:
        send_text_to_tts(f"{command.capitalize()} mode activated.", wait_for_completion=True)
