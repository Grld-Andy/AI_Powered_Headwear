import os
import cv2
import time
import socket
import librosa
import winsound
import requests
import threading
import numpy as np
import sounddevice as sd
from ultralytics import YOLO
from pydub import AudioSegment
from collections import Counter
from scipy.io.wavfile import write
from tensorflow.keras.models import load_model
from core.database.database import setup_db, get_saved_language, save_language
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Initialize these outside your loop once
last_frame_time = 0
last_depth_time = 0
DEPTH_INTERVAL = 2  # seconds between depth estimation
FRAME_INTERVAL = 1 / 15  # target ~15 FPS (adjust as needed)
cached_depth_vis = None
cached_depth_raw = None
SELECTED_LANGUAGE = ''
wakeword_processing = False

# === Constants and Globals ===
HOST = 'localhost'
PORT = 65432
FS_AUDIO = 22050
COMMAND_SECONDS = 2
N_MFCC = 40
MAX_TIMESTEPS = 100
LANG_AUDIO_FILE = "data/audio_capture/lang_command.wav"
COMMAND_CLASSES = ["background", "reading", "start", "stop", "reset", "count"]
last_play_time = 0
tts_lock = threading.Lock()
audio_playing = threading.Event()
LANG_MODEL_PATH = 'models/language_selector.keras'
LANG_MODEL = load_model(LANG_MODEL_PATH)
LANGUAGES = ['background', 'english', 'twi']
translated_audio = 'data/translated/'
translated_phrases = translated_audio + 'phrases/'
translated_numbers = translated_audio + 'numbers/'
translated_labels = translated_audio + 'labels/'

# Load models
AUDIO_COMMAND_MODEL = None
yolo_model = YOLO("models/yolov5n.pt")
midas_net = cv2.dnn.readNet("./models/Midas-V2.onnx")
midas_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
midas_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

cap = cv2.VideoCapture(0)

# State variables
wakeword_detected = threading.Event()
awaiting_command = False
current_mode = "start"


# === Audio / TTS Functions ===
def predict_audio(audio_path, model, classes, duration=2):
    seconds = duration
    fs = 44100
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()
    write(audio_path, fs, myrecording)
    audio, sample_rate = librosa.load(audio_path, sr=None)
    mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=N_MFCC)
    mfcc = mfcc.T
    mfcc_padded = pad_sequences([mfcc], maxlen=MAX_TIMESTEPS, dtype='float32', padding='post', truncating='post')
    prediction = model.predict(mfcc_padded)
    predicted_class = np.argmax(prediction)
    confidence = prediction[0][predicted_class]
    return classes[predicted_class], confidence


def detect_or_load_language():
    setup_db()
    lang = get_saved_language()
    lang = ""
    if lang:
        return lang
    else:
        return set_preferred_language()


def set_preferred_language():
    global LANG_MODEL

    if not SELECTED_LANGUAGE:
        send_text_to_tts("Please say your preferred language.", wait_for_completion=True)
        play_audio_winsound(f"./{translated_phrases}what language do you prefer.wav", wait_for_completion=True)
    else:
        if SELECTED_LANGUAGE == 'twi':
            play_audio_winsound(f'{translated_phrases}what language do you prefer.wav', wait_for_completion=True)
        else:
            send_text_to_tts("Please say your preferred language.", wait_for_completion=True)

    try:
        print("You can try speaking")
        lang, confidence = predict_audio(LANG_AUDIO_FILE, LANG_MODEL, LANGUAGES, duration=2)
        print(f'[LANG] You said {lang}, I am {confidence*100}% confident')
        if lang == 'english':
            send_text_to_tts(f"You said {lang}", True)
        elif lang == 'twi':
            play_audio_winsound(f'{translated_phrases}you said twi.wav', wait_for_completion=True)
        else:
            lang = 'twi'
            send_text_to_tts(f"Could not understand, using default language {lang}", True)
        save_language(lang)
        return lang
    except Exception as e:
        print("An error occured: ", e)
        if SELECTED_LANGUAGE:
            return SELECTED_LANGUAGE
        else:
            return 'twi'


def play_audio_winsound(filename, wait_for_completion=False):
    flags = winsound.SND_FILENAME
    if not wait_for_completion:
        flags |= winsound.SND_ASYNC
    winsound.PlaySound(filename, flags)


def send_text_to_tts(text, wait_for_completion=False, priority=0):
    global last_play_time
    if not tts_lock.acquire(blocking=False):
        if not priority:
            return
        # high-priority: try again after a brief wait or force reset
        tts_lock.acquire()
    current_time = time.time()

    if priority == 0 and (current_time - last_play_time < 1.5):
        tts_lock.release()
        return

    url = 'http://localhost:5000'
    outputFilename = 'audio_capture/output.wav'
    payload = {'text': text}

    try:
        response = requests.get(url, params=payload)
        os.makedirs(os.path.dirname(outputFilename), exist_ok=True)
        with open(outputFilename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=128):
                f.write(chunk)
        play_audio_winsound(outputFilename, wait_for_completion)
        last_play_time = time.time()
    except Exception as e:
        print("Exception: ", e)
    finally:
        tts_lock.release()


# === Wake Word Socket Client ===
def listen_wakeword_socket():
    global wakeword_detected
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        buffer = b""
        while True:
            data = s.recv(1024)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = line.decode().strip()
                if msg == "WAKEWORD" and not wakeword_detected.is_set():
                    wakeword_detected.set()


def combine_audio_files(file_list, output_path="./data/audio_capture/combined_audio.wav", wait_for_completion=False, priority=0):
    global last_play_time

    if priority == 0 and audio_playing.is_set():
        return

    acquired = tts_lock.acquire(timeout=5)
    if not acquired:
        return

    try:
        if priority == 0 and audio_playing.is_set():
            return

        combined = AudioSegment.empty()
        for file in file_list:
            if not os.path.isfile(file):
                continue
            try:
                audio = AudioSegment.from_file(file)
                combined += audio
            except Exception as e:
                print("Exception reading file:", file, e)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined.export(output_path, format="wav")

        audio_playing.set()

        def play_and_release():
            global last_play_time
            try:
                play_audio_winsound(output_path, wait_for_completion=True)
                last_play_time = time.time()
            finally:
                audio_playing.clear()
                tts_lock.release()

        if wait_for_completion:
            play_and_release()
        else:
            threading.Thread(target=play_and_release).start()

    except Exception as e:
        print("Exception during audio combination or playback:", e)
        audio_playing.clear()
        tts_lock.release()


def calculate_currency(frame, save_path='currency.png', url='http://localhost:8000/detect/'):
    cv2.imwrite(save_path, frame)

    with open(save_path, 'rb') as f:
        files = {'file': (save_path, f, 'image/png')}
        try:
            response = requests.post(url, files=files, timeout=10)
            if response.status_code != 200:
                print(f"Server returned status code {response.status_code}")
                print(response.text)
                return None, None

            detections = response.json().get("detections", [])
            if not detections:
                return "No currency detected.", 0.0

            # Count occurrences of each class
            class_counts = Counter(det["class"] for det in detections)

            # Build summary string
            summary_parts = [f"{count} x {cls}" for cls, count in class_counts.items()]
            summary = ", ".join(summary_parts)

            # Calculate total value
            total = 0.0
            for cls, count in class_counts.items():
                try:
                    value = float(cls.split()[0])  # Get the numeric part
                    total += value * count
                except ValueError:
                    print(f"Could not parse currency value from class: {cls}")

            return summary, total

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None, None


# === Depth Estimation & Object Detection ===
def run_depth_estimation(frame, net):
    input_size = (256, 256)
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, input_size, (0, 0, 0), swapRB=True, crop=False)
    net.setInput(blob)
    output = net.forward()
    depth = output.squeeze()
    depth = cv2.resize(depth, (frame.shape[1], frame.shape[0]))
    norm_depth = cv2.normalize(depth, None, 255, 0, cv2.NORM_MINMAX, cv2.CV_8U)
    color_depth = cv2.applyColorMap(norm_depth, cv2.COLORMAP_JET)
    return color_depth, depth


def run_object_detection(frame):
    results = yolo_model(frame)
    detections = []
    for r in results:
        for *box, conf, cls in r.boxes.data.tolist():
            detections.append({'bbox': tuple(map(int, box)), 'confidence': conf, 'class_id': int(cls)})
    return detections


def ocr_space_file(filename, api_key='helloworld', language='eng'):
    url = 'https://api.ocr.space/parse/image'
    with open(filename, 'rb') as f:
        payload = {
            'isOverlayRequired': False,
            'apikey': api_key,
            'language': language,
        }
        response = requests.post(url, files={'filename': f}, data=payload)
    result = response.json()
    return result.get("ParsedResults")[0].get("ParsedText", "")


# === Main Loop ===
def main_loop():
    global awaiting_command, current_mode, wakeword_processing, SELECTED_LANGUAGE

    cv2.namedWindow("Camera View", cv2.WINDOW_NORMAL)

    frozen_frame = None

    while True:
        # === Wake Word Trigger ===
        if wakeword_detected.is_set() and not awaiting_command:
            awaiting_command = True
            if SELECTED_LANGUAGE == 'twi':
                play_audio_winsound(f"{translated_phrases}hello what can i do for you.wav", wait_for_completion=True)
            else:
                send_text_to_tts("Hi, how may I help you?", wait_for_completion=True, priority=1)

            command, confidence = predict_audio("./data/audio_capture/user_command.wav", AUDIO_COMMAND_MODEL, COMMAND_CLASSES)

            if confidence > 0.9 and command in COMMAND_CLASSES and command != "background":
                if SELECTED_LANGUAGE == 'twi':
                    if command == "reading":
                        play_audio_winsound(f"{translated_phrases}you said reading.wav", wait_for_completion=True)
                    elif command == "start":
                        play_audio_winsound(f"{translated_phrases}you said start.wav", wait_for_completion=True)
                    elif command == "stop":
                        play_audio_winsound(f"{translated_phrases}you said stop.wav", wait_for_completion=True)
                    else:
                        send_text_to_tts(f"{command.capitalize()} mode activated.", wait_for_completion=True)
                else:
                    send_text_to_tts(f"{command.capitalize()} mode activated.", wait_for_completion=True)
                current_mode = command
            else:
                if SELECTED_LANGUAGE == 'twi':
                    play_audio_winsound(f"{translated_phrases}sorry I did not understand.wav", wait_for_completion=True)
                else:
                    send_text_to_tts("Sorry, I did not understand that command.", wait_for_completion=True)

            awaiting_command = False
            wakeword_detected.clear()

        ret, frame = cap.read()
        if not ret:
            break


        key = cv2.waitKey(1) & 0xFF
        # elif current_mode == "count" and not wakeword_processing:
        if key == ord('r'):
            send_text_to_tts("Counting currency", wait_for_completion=True)
            detections, total = calculate_currency(frame)
            send_text_to_tts(f"Currency detected: {detections}, making a total of {total} cedis", wait_for_completion=True)
            current_mode = "start"

        if current_mode == "start" and not wakeword_processing:
            global last_frame_time, last_depth_time, cached_depth_vis, cached_depth_raw
            current_time = time.time()

            if current_time - last_frame_time < FRAME_INTERVAL:
                key = cv2.waitKey(1) & 0xFF
                continue

            last_frame_time = current_time
            small_frame = cv2.resize(frame, (640, 480))
            detections = run_object_detection(small_frame)

            if current_time - last_depth_time >= DEPTH_INTERVAL or cached_depth_raw is None:
                cached_depth_vis, cached_depth_raw = run_depth_estimation(small_frame, midas_net)
                last_depth_time = current_time

            close_objects = []

            for det in detections:
                conf = det['confidence']
                if conf < 0.6:
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
                parts = []
                counts = Counter(close_objects)
                wav_files = []
                for kind, count in counts.items():
                    label = f"{count} {kind}"
                    if count > 1:
                        label += "s"

                    label_base = kind
                    wav_files.append(f"{translated_labels}{label_base}.wav")
                    parts.append(label)
                    wav_files.append(f"{translated_numbers}{count}.wav")
                print("🎙 All wav files: ", wav_files)

                if SELECTED_LANGUAGE == 'twi':
                    if not wakeword_detected.is_set():
                        wav_files.append(f"{translated_phrases}in front of you.wav")
                        threading.Thread(
                            target=combine_audio_files,
                            args=(wav_files,),
                            kwargs={'wait_for_completion': False},
                            daemon=True
                        ).start()

                elif SELECTED_LANGUAGE == "english":
                    print("Parts: ", parts)
                    if len(parts) == 1:
                        sentence = parts[0]
                    elif len(parts) == 2:
                        sentence = f"{parts[0]} and {parts[1]}"
                    else:
                        sentence = ", ".join(parts[:-1]) + ", and " + parts[-1]
                    tts_sentence = f"{sentence} in front of you."
                    if not wakeword_detected.is_set():
                        threading.Thread(
                            target=send_text_to_tts,
                            args=(tts_sentence,),
                            kwargs={'wait_for_completion': False},
                            daemon=True
                        ).start()
                    cv2.putText(small_frame, tts_sentence, (10, small_frame.shape[0] - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            elapsed = time.time() - last_frame_time
            if elapsed == 0:
                elapsed = 1e-6
            fps = 1.0 / elapsed

            # cv2.putText(small_frame, f"FPS: {fps:.2f}", (10, 30),
            # cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("Camera View", small_frame)

            key = cv2.waitKey(1) & 0xFF


        # === READING MODE ===
        elif current_mode == "reading" and not wakeword_processing:
            if frozen_frame is None:
                frozen_frame = frame.copy()
                cv2.imshow("Camera View", frozen_frame)
                cv2.waitKey(1)

                # Save frame as image for OCR
                image_path = "captured_image.png"
                cv2.imwrite(image_path, frozen_frame)

                try:
                    text = ocr_space_file(image_path).strip()
                except Exception as e:
                    print("OCR Error:", e)
                    text = ""

                if text:
                    if SELECTED_LANGUAGE == 'twi':
                        play_audio_winsound(f"{translated_phrases}start reading.wav", wait_for_completion=True, priority=1)
                        send_text_to_tts(text, wait_for_completion=True, priority=1)
                        play_audio_winsound(f"{translated_phrases}done reading.wav", wait_for_completion=True, priority=1)
                    else:
                        print("💝☮🕳☪💤: ", text)
                        send_text_to_tts("Reading text now.", wait_for_completion=True)
                        send_text_to_tts(text, wait_for_completion=True, priority=1)
                        send_text_to_tts("Done reading text.", wait_for_completion=True, priority=1)
                    current_mode = "start"
                else:
                    send_text_to_tts("No text found.", wait_for_completion=True)
                    current_mode = "reading"

                
                frozen_frame = None

            else:
                cv2.imshow("Camera View", frozen_frame)
        
        # === RESET MODE ===
        elif current_mode == "reset" and not wakeword_processing:
            SELECTED_LANGUAGE = set_preferred_language()
            current_mode = "start"

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    play_audio_winsound("./data/custom_audio/deviceOn1.wav", True)
    SELECTED_LANGUAGE = detect_or_load_language()
    print("Selected language: ", SELECTED_LANGUAGE)
    AUDIO_COMMAND_MODEL = load_model(f"./models/{SELECTED_LANGUAGE}/command_classifier.keras")
    threading.Thread(target=listen_wakeword_socket, daemon=True).start()
    main_loop()
