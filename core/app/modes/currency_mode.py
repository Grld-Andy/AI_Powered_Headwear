from core.vision.currency import calculate_currency
from utils.say_in_language import say_in_language


def handle_currency_mode(frame, language):
    say_in_language("Counting currency", language, wait_for_completion=True)
    detections, total = calculate_currency(frame)
    say_in_language(f"Currency detected: {detections}, making a total of {total} cedis", language, wait_for_completion=True)
