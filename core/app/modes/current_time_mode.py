import datetime
from core.tts.piper import send_text_to_tts


def get_current_time():
    now = datetime.datetime.now()
    formatted_time = now.strftime("%A, %B %d, %Y. The time is %I:%M %p.")
    send_text_to_tts(formatted_time, wait_for_completion=True)
    return
