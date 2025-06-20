import cv2
import numpy as np
from core.vision.ocr import ocr_space_file
from utils.say_in_language import say_in_language


def handle_reading_mode(frame, language, _):  # frozen_frame no longer needed
    print("Reading mode activated")

    if frame is None or not isinstance(frame, np.ndarray):
        say_in_language("No valid image to read.", language, wait_for_completion=True)
        return None, "start"

    # Resize for display/OCR consistency
    frame = cv2.resize(frame, (640, 480))
    cv2.imshow("Camera View", frame)
    cv2.waitKey(1)

    # Save frame to disk for OCR
    cv2.imwrite("data/captured_image.png", frame)

    try:
        print("Extracting text")
        text = ocr_space_file("data/captured_image.png").strip()
        print("Extracted text:", text)
    except Exception as e:
        print("OCR Error:", e)
        text = ""

    if text:
        say_in_language(f"Reading now. {text}. Done reading.", language, wait_for_completion=True)
    else:
        say_in_language("No text found.", language, wait_for_completion=True)

    # Return to 'start' mode either way
    return frame, "start"
