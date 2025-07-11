import datetime
from core.tts.piper import send_text_to_tts
from utils.say_in_language import say_in_language


def get_current_time(language):
    print("detecting time")
    now = datetime.datetime.now()
    formatted_time = now.strftime("%A, %B %d, %Y. The time is %I:%M %p.")
    say_in_language(f"Today's date is {formatted_time}", language, wait_for_completion=True, priority=1)
    return
