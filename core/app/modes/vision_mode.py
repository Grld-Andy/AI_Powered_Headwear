import threading
import cv2
import time
from collections import Counter
from config.settings import (
    FRAME_INTERVAL, DEPTH_INTERVAL,
    wakeword_detected
)
from config.load_models import yolo_model
from core.tts.piper import get_volume
from core.vision.object_detection import run_object_detection
from core.vision.depth_estimation import load_depth_model, run_depth_estimation
from utils.say_in_language import say_in_language

# Load depth model
midas_net = load_depth_model()
stop_vision = threading.Event()

# Region → natural speech mapping
REGION_MAP = {
    "middle": "in front of you",
    "middle-left": "slightly to the left",
    "middle-right": "slightly to the right",
    "leftmost": "to your left",
    "rightmost": "to your right"
}


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
            state, passive=True
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

    # Depth estimation
    if current_time - state.last_depth_time >= DEPTH_INTERVAL or state.cached_depth_raw is None:
        print("[Vision] Generating new depth map...")
        state.cached_depth_vis, state.cached_depth_raw = run_depth_estimation(small_frame, midas_net)
        state.last_depth_time = current_time

    close_objects = []
    stack_w = small_frame.shape[1] // 5  # divide into 5 regions
    stack_names = ["leftmost", "middle-left", "middle", "middle-right", "rightmost"]
    stack_close = {name: False for name in stack_names}
    stack_objects = {name: [] for name in stack_names}

    # ---- Draw region division lines ----
    for i in range(1, 5):
        x = i * stack_w
        cv2.line(small_frame, (x, 0), (x, small_frame.shape[0]), (255, 255, 0), 2)  # Cyan lines

    # ---- Object detection classification by region ----
    for det in detections:
        conf = det['confidence']
        if conf < 0.65:
            continue

        x1, y1, x2, y2 = det['bbox']
        class_id = det['class_id']
        class_name = yolo_model.names[class_id]

        # Skip unwanted classes
        if class_id in [4, 8, 10, 16, 17, 18, 19, 20, 21, 22, 23, 61, 78]:
            continue

        # Figure out which region (leftmost → rightmost)
        center_x = (x1 + x2) // 2
        region_idx = min(center_x // stack_w, 4)
        stack = stack_names[region_idx]

        # Mark close objects if depth is small
        object_depth_roi = state.cached_depth_raw[y1:y2, x1:x2]
        if object_depth_roi.size and object_depth_roi.min() < 200:
            stack_close[stack] = True
            stack_objects[stack].append((class_name, stack))
            close_objects.append(class_name)
            label = f"{class_name} {conf:.2f} - CLOSE!"
            color = (0, 0, 255)  # Red
        else:
            stack_objects[stack].append((class_name, stack))
            label = f"{class_name} {conf:.2f}"
            color = (0, 255, 0)  # Green

        cv2.rectangle(small_frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(small_frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # --- Navigation Guidance ---
    nav_message = ""

    # If middle blocked → apply new logic
    if stack_close["middle"]:
        lane_clearance = {}
        h, w = state.cached_depth_raw.shape
        lane_width = w // 5

        for lane, i in zip(stack_names, range(5)):
            x1, x2 = i * lane_width, (i + 1) * lane_width
            roi = state.cached_depth_raw[:, x1:x2]
            lane_clearance[lane] = roi.min() if roi.size > 0 else 0

        # Check best safe alternative
        if not stack_close["leftmost"]:
            nav_message = "Move to your left, it is safer."
        elif not stack_close["rightmost"]:
            nav_message = "Move to your right, it is safer."
        elif not stack_close["middle-left"]:
            nav_message = "Move slightly left, it is safer."
        elif not stack_close["middle-right"]:
            nav_message = "Move slightly right, it is safer."
        else:
            # Both sides blocked → pick based on clearance
            left_clear = lane_clearance["middle-left"] + lane_clearance["leftmost"]
            right_clear = lane_clearance["middle-right"] + lane_clearance["rightmost"]

            if left_clear > right_clear and left_clear - lane_clearance["middle"] > 100:
                nav_message = "Try moving left, it looks safer."
            elif right_clear > left_clear and right_clear - lane_clearance["middle"] > 100:
                nav_message = "Try moving right, it looks safer."
            else:
                nav_message = "Please stop, obstacles ahead."

        announce_detected_objects(language, stack_objects, nav_message)

    else:
        # Middle clear → announce objects + give suggestion if one side is blocked
        if stack_close["middle-left"] and not stack_close["middle-right"]:
            nav_message = "Keep slightly to your right, it is safer."
        elif stack_close["middle-right"] and not stack_close["middle-left"]:
            nav_message = "Keep slightly to your left, it is safer."

        all_objects = []
        for lane in stack_names:
            all_objects += stack_objects[lane]
        if all_objects:
            announce_detected_objects(language, stack_objects, nav_message)

    if not passive:
        cv2.imshow("Camera View", small_frame)

    return small_frame, state.cached_depth_raw, state.last_frame_time, state.last_depth_time


def announce_detected_objects(language, stack_objects, nav_message=""):
    # stack_objects is a dict {region: [(class_name, region), ...]}
    parts = []
    flat_list = []
    for lane, objs in stack_objects.items():
        for obj, region in objs:
            flat_list.append((obj, region))

    # Count objects by (class, region)
    counts = Counter(flat_list)
    for (kind, region), count in counts.items():
        region_label = REGION_MAP.get(region, region)
        parts.append(f"{count} {kind}" + ("s" if count > 1 else "") + f" {region_label}")

    if not parts:
        return

    sentence = ", ".join(parts[:-1]) + ", and " + parts[-1] if len(parts) > 1 else parts[0]
    if not nav_message:
        sentence += "."
    else:
        sentence += f". {nav_message}"

    if not wakeword_detected.is_set():
        threading.Thread(
            target=say_in_language,
            args=(sentence, language,),
            kwargs={'wait_for_completion': False, 'volume': get_volume()},
            daemon=True
        ).start()
