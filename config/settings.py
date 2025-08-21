import cv2
import threading
# from ultralytics import YOLO
# from tensorflow.keras.models import load_model

# Initialize these outside your loop once
last_frame_time = 0
last_depth_time = 0
DEPTH_INTERVAL = 7  # seconds between depth estimation
FRAME_INTERVAL = 1 / 5 # target ~15 FPS (adjust as needed)
cached_depth_vis = None
cached_depth_raw = None
SELECTED_LANGUAGE = ''
wakeword_processing = False
pc_Ip = "172.20.10.3"

def get_language():
    global SELECTED_LANGUAGE
    return SELECTED_LANGUAGE

def set_language(language):
    global SELECTED_LANGUAGE
    SELECTED_LANGUAGE = language

# === Constants and Globals ===
HOST = f'{pc_Ip}'
PORT = 1234
FS_AUDIO = 22050
COMMAND_SECONDS = 2
N_MFCC = 40
MAX_TIMESTEPS = 100
LANG_AUDIO_FILE = "./data/audio_capture/lang_command.wav"
english_training_phrases = [
    # reading
    "can you read this", "read the text on the screen", "what does it say", "read this label for me",
    # stop
    "stop everything", "pause the system", "turn off the assistant", "halt all processes",
    # start
    "start detecting objects", "what's in front of me", "what's near me", "look around", "identify the things around",
    # reset
    "change language", "reset the system", "start setup again", "switch to another language",
    # current_location
    "where am I", "what's my current location", "tell me where I am", "give me my location",
    # navigate
    "take me somewhere", "I want directions", "how do I get to the train station", "navigate to the pharmacy",
    # bookmark_location
    "save this location", "remember where I am", "bookmark this place", "mark this spot",
    # save_contact
    "save a phone number", "add a new contact info", "remember this phone number", "store a contact for me",
    # send_money
    "send money to Sarah", "transfer cash to my friend", "make a mobile payment", "pay someone now",
    # time
    "what time is it", "tell me the current time", "what's the time now", "give me the time",
    # hotspots
    "find nearby restaurants", "show places around me", "what's close by", "list nearby hotspots",
    # chat (fallback/general)
    "what can you do", "how are you today", "tell me something interesting", "let's chat", "can you help me",
    # shutdown
    "shut down the device", "turn off the system", "power off", "shutdown now",
    # get contact
    "get a phone number", "find contact info", "show me my contacts", "retrieve a phone number",
    # emergency_mode
    "help me", "emergency", "call for help", "alert authorities", "I need help now", "danger", "urgent assistance",
    # describe scene
    "describe what is in front of me", "what does the scene look like", "tell me what you see", "describe my surroundings",
    # get_device_id
    "what is my device id", "show me my device id", "give me my device serial", "display my device identifier"
]
training_phrases = english_training_phrases
command_labels = [
    # reading
    "reading", "reading", "reading", "reading",
    # stop
    "stop", "stop", "stop", "stop",
    # start
    "start", "start", "start", "start", "start",
    # reset
    "reset", "reset", "reset", "reset",
    # current location
    "current_location", "current_location", "current_location", "current_location",
    # navigate
    "navigate", "navigate", "navigate", "navigate",
    # bookmark location
    "bookmark_location", "bookmark_location", "bookmark_location", "bookmark_location",
    # save contact
    "save_contact", "save_contact", "save_contact", "save_contact",
    # send money
    "send_money", "send_money", "send_money", "send_money",
    # time
    "time", "time", "time", "time",
    # hotspot
    "hotspots", "hotspots", "hotspots", "hotspots",
    # chat
    "chat", "chat", "chat", "chat", "chat",
    # shutdown
    "shutdown", "shutdown", "shutdown", "shutdown",
    # get contact
    "get_contact", "get_contact", "get_contact", "get_contact",
    # emergency_mode
    "emergency_mode", "emergency_mode", "emergency_mode", "emergency_mode", 
    "emergency_mode", "emergency_mode", "emergency_mode",
    # describe scene
    "describe_scene", "describe_scene", "describe_scene", "describe_scene",
    # get_device_id
    "get_device_id", "get_device_id", "get_device_id", "get_device_id"
]
COMMAND_CLASSES = [
    "background", "reading", "start", "stop", "reset",
    "current_location", "navigate", "bookmark_location", "save_contact",
    "send_money", "time", "hotspots", "chat", "shutdown",
    "get_contact", "emergency_mode", "describe_scene", "get_device_id"
]
last_play_time = 0
tts_lock = threading.Lock()
audio_playing = threading.Event()
LANG_MODEL_PATH = './models/language_selector.keras'
LANGUAGES = ['background', 'english', 'twi']
translated_audio = 'data/translated/'
translated_phrases = translated_audio + 'phrases/'
translated_numbers = translated_audio + 'numbers/'
translated_labels = translated_audio + 'labels/'
AUDIO_COMMAND_MODEL = None
INTENT_CLASSIFIER_MODEL = "./models/knn_classifier.joblib"

# # Load models
# LANG_MODEL = load_model(LANG_MODEL_PATH)
# yolo_model = YOLO("./models/yolov5n.pt")
CAMERA_IP = "192.168.137.171"
MJPEG_PORT = 81
MJPEG_URL = f"http://{CAMERA_IP}:{MJPEG_PORT}/stream"
cap = cv2.VideoCapture(MJPEG_URL)

# State variables
wakeword_detected = threading.Event()
esp32_connected = threading.Event()
awaiting_command = False
DATABASE = 'database.db'
BASE_URL = f'http://{pc_Ip}:3000'
API_BASE_URL = f"http://{pc_Ip}:3000/api"

current_mode = "stop"
def get_mode():
    global current_mode
    return current_mode

def set_mode(new_mode):
    global current_mode
    current_mode = new_mode
