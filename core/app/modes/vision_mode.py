import threading
import cv2
import time
from collections import Counter
from config.settings import (
    FRAME_INTERVAL, DEPTH_INTERVAL,
    translated_labels, translated_numbers,
    wakeword_detected
)
from config.load_models import yolo_model
from core.tts.piper import get_volume
from core.vision.object_detection import run_object_detection
from core.vision.depth_estimation import load_depth_model, run_depth_estimation
from utils.say_in_language import say_in_language

midas_net = load_depth_model()
stop_vision = threading.Event()

# Shared state wrapper
class VisionState:
    def __init__(self):
        self.last_frame_time = 0
        self.last_depth_time = 0
        self.cached_depth_vis = None
        self.cached_depth_raw = None

def run_background_vision(frame_func, language_func, state: VisionState):
    print("[Vision] Background vision thread started.")
    while not stop_vision.is_set():
        frame = frame_func()
        language = language_func()
        if frame is None:
            time.sleep(FRAME_INTERVAL)
            continue
        _ = handle_vision_mode(
            frame, language,
            state, passive=True  # passive: no camera view
        )
        time.sleep(FRAME_INTERVAL)
    print("[Vision] Background vision thread stopped.")

def handle_vision_mode(frame, language, state: VisionState, passive=False):
    current_time = time.time()
    if current_time - state.last_frame_time < FRAME_INTERVAL:
        return state.cached_depth_vis, state.cached_depth_raw, state.last_frame_time, state.last_depth_time

    state.last_frame_time = current_time
    small_frame = cv2.resize(frame, (640, 480))
    detections = run_object_detection(small_frame)

    if current_time - state.last_depth_time >= DEPTH_INTERVAL or state.cached_depth_raw is None:
        print("[Vision] Generating new depth map...")
        state.cached_depth_vis, state.cached_depth_raw = run_depth_estimation(small_frame, midas_net)
        state.last_depth_time = current_time

    close_objects = []
    for det in detections:
        conf = det['confidence']
        if conf < 0.65:
            continue
        x1, y1, x2, y2 = det['bbox']
        class_id = det['class_id']
        class_name = yolo_model.names[class_id]
        object_depth_roi = state.cached_depth_raw[y1:y2, x1:x2]
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
        announce_detected_objects(language, close_objects)

    if not passive:
        cv2.imshow("Camera View", small_frame)

    return state.cached_depth_vis, state.cached_depth_raw, state.last_frame_time, state.last_depth_time

def announce_detected_objects(language, objects):
    parts = []
    counts = Counter(objects)
    for kind, count in counts.items():
        parts.append(f"{count} {kind}" + ("s" if count > 1 else ""))

    sentence = ", ".join(parts[:-1]) + ", and " + parts[-1] if len(parts) > 1 else parts[0]
    sentence += " in front of you"

    if not wakeword_detected.is_set():
        threading.Thread(
            target=say_in_language,
            args=(sentence, language,),
            kwargs={'wait_for_completion': False, 'volume': get_volume()},
            daemon=True
        ).start()
