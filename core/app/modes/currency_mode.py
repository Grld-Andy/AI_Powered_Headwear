from core.vision.currency import calculate_currency
from core.tts.piper import send_text_to_tts


def handle_currency_mode(frame, language):
    send_text_to_tts("Counting currency", wait_for_completion=True)
    detections, total = calculate_currency(frame)
    send_text_to_tts(f"Currency detected: {detections}, making a total of {total} cedis", wait_for_completion=True)
