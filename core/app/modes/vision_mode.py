# core/app/modes/vision_mode.py

import threading
import cv2
import time
from collections import Counter
from config.settings import FRAME_INTERVAL, DEPTH_INTERVAL, translated_labels, translated_numbers, translated_phrases, yolo_model, wakeword_detected
from core.vision.object_detection import run_object_detection
from core.audio.audio_capture import combine_audio_files
from core.tts.piper import send_text_to_tts
from core.vision.depth_estimation import load_depth_model, run_depth_estimation

midas_net = load_depth_model()
stop_vision = threading.Event()

def run_background_vision(frame_func, language_func, last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw):
    while not stop_vision.is_set():
        frame = frame_func()
        language = language_func()
        if frame is None:
            time.sleep(FRAME_INTERVAL)
            continue
        handle_vision_mode(frame, language, last_frame_time, last_depth_time,
                           cached_depth_vis, cached_depth_raw, volume=0.3)
        time.sleep(FRAME_INTERVAL)


def handle_vision_mode(frame, language, last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw, volume=1.0):
    current_time = time.time()
    if current_time - last_frame_time < FRAME_INTERVAL:
        return cached_depth_vis, cached_depth_raw, last_frame_time, last_depth_time

    last_frame_time = current_time
    small_frame = cv2.resize(frame, (640, 480))
    detections = run_object_detection(small_frame)

    if current_time - last_depth_time >= DEPTH_INTERVAL or cached_depth_raw is None:
        print("generating new depth map")
        cached_depth_vis, cached_depth_raw = run_depth_estimation(small_frame, midas_net)
        last_depth_time = current_time

    close_objects = []
    for det in detections:
        conf = det['confidence']
        if conf < 0.65:
            continue
        x1, y1, x2, y2 = det['bbox']
        class_id = det['class_id']
        class_name = yolo_model.names[class_id]
        object_depth_roi = cached_depth_raw[y1:y2, x1:x2]
        if object_depth_roi.size and object_depth_roi.min() < 200:
            close_objects.append(class_name)
            label = f"{class_name} {conf:.2f} - CLOSE!"
            color = (0, 0, 255)
        else:
            label = f"{class_name} {conf:.2f}"
            color = (0, 255, 0)
        cv2.rectangle(small_frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(small_frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    if close_objects:
        announce_detected_objects(language, close_objects, volume)

    cv2.imshow("Camera View", small_frame)
    return cached_depth_vis, cached_depth_raw, last_frame_time, last_depth_time


def announce_detected_objects(language, objects, volume=0.5):
    parts = []
    wav_files = []
    counts = Counter(objects)
    for kind, count in counts.items():
        parts.append(f"{count} {kind}" + ("s" if count > 1 else ""))
        wav_files.append(f"{translated_labels}{kind}.wav")
        wav_files.append(f"{translated_numbers}{count}.wav")

    if language == 'twi':
        if not wakeword_detected.is_set():
            print(f"{translated_phrases}in front of you")
            wav_files.append(f"{translated_phrases}in front of you.wav")
            threading.Thread(
                target=combine_audio_files,
                args=(wav_files,),
                kwargs={'wait_for_completion': False, 'volume': volume},
                daemon=True
            ).start()
    else:
        if not wakeword_detected.is_set():
            sentence = ", ".join(parts[:-1]) + ", and " + parts[-1] if len(parts) > 1 else parts[0]
            sentence += " in front of you"
            print(sentence)
            threading.Thread(
                target=send_text_to_tts,
                args=(sentence,),
                kwargs={'wait_for_completion': False, 'volume': volume},
                daemon=True
            ).start()
