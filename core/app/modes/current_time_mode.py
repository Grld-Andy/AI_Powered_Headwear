import datetime
from core.tts.piper import send_text_to_tts


def get_current_time(language):
    print("detecting time")
    now = datetime.datetime.now()
    formatted_time = now.strftime("%A, %B %d, %Y. The time is %I:%M %p.")
    print("Current time:", formatted_time)
    send_text_to_tts(f"Today's date is {formatted_time}", language, wait_for_completion=True, priority=1)
    return
