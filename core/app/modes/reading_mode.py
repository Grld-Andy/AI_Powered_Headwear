import cv2
import numpy as np
from utils.say_in_language import say_in_language
from google.generativeai import upload_file, GenerativeModel
import os
import re

# Clean text extracted from image
def clean_response(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)  # remove emojis
    text = re.sub(r"[^a-zA-Z0-9\s.,;:'\"!?-]", "", text)  # remove weird chars
    text = re.sub(r"\s+", " ", text).strip()
    return text

def handle_reading_mode(frame, language, _):  # same signature
    """Extracts only text from the given frame using Google Gemini."""
    print("Reading mode activated")

    if frame is None or not isinstance(frame, np.ndarray):
        say_in_language("No valid image to read.", language, wait_for_completion=True)
        return None, ""

    # Resize frame for consistency
    frame = cv2.resize(frame, (640, 480))
    cv2.imshow("Camera View", frame)
    cv2.waitKey(1)

    # Save frame to disk
    temp_image_path = "data/captured_image.png"
    os.makedirs("data", exist_ok=True)
    cv2.imwrite(temp_image_path, frame)

    extracted_text = ""
    try:
        # Upload image and get only text
        uploaded_file = upload_file(temp_image_path)
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {"role": "user", "parts": ["Extract only the text content from this image. Do not describe the scene.", uploaded_file]}
        ])
        extracted_text = clean_response(response.text)
        print("Extracted text:", extracted_text)
    except Exception as e:
        print("Text extraction error:", e)

    # Speak the text directly without extra words
    if extracted_text:
        say_in_language(extracted_text, language, wait_for_completion=True)
    else:
        say_in_language("No text found.", language, wait_for_completion=True)

    return frame, extracted_text
