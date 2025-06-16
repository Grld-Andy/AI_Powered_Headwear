import cv2
from core.vision.ocr import ocr_space_file
from core.audio.audio_capture import play_audio_winsound
from core.tts.piper import send_text_to_tts
from config.settings import translated_phrases

def handle_reading_mode(frame, language, frozen_frame):
    if frozen_frame is None:
        frozen_frame = frame.copy()
        cv2.imshow("Camera View", frozen_frame)
        cv2.waitKey(1)
        cv2.imwrite("captured_image.png", frozen_frame)
        try:
            text = ocr_space_file("captured_image.png").strip()
        except Exception as e:
            print("OCR Error:", e)
            text = ""

        if text:
            if language == 'twi':
                play_audio_winsound(f"{translated_phrases}start reading.wav", wait_for_completion=True)
                send_text_to_tts(text, wait_for_completion=True)
                play_audio_winsound(f"{translated_phrases}done reading.wav", wait_for_completion=True)
            else:
                send_text_to_tts("Reading text now.", wait_for_completion=True)
                send_text_to_tts(text, wait_for_completion=True)
                send_text_to_tts("Done reading text.", wait_for_completion=True)
            return None, "start"
        else:
            send_text_to_tts("No text found.", wait_for_completion=True)
            return None, "reading"
    else:
        cv2.imshow("Camera View", frozen_frame)
        return frozen_frame, "reading"
