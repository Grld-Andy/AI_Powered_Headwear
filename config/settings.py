import cv2
import threading
from ultralytics import YOLO
from tensorflow.keras.models import load_model

# Initialize these outside your loop once
last_frame_time = 0
last_depth_time = 0
DEPTH_INTERVAL = 7  # seconds between depth estimation
FRAME_INTERVAL = 1 / 15  # target ~15 FPS (adjust as needed)
cached_depth_vis = None
cached_depth_raw = None
SELECTED_LANGUAGE = ''
wakeword_processing = False

# === Constants and Globals ===
HOST = 'localhost'
PORT = 1234
FS_AUDIO = 22050
COMMAND_SECONDS = 2
N_MFCC = 40
MAX_TIMESTEPS = 100
LANG_AUDIO_FILE = "./data/audio_capture/lang_command.wav"
training_phrases = [
    # reading
    "can you read this", "read the text on the screen", "what does it say", "read this label for me",
    # stop
    "stop everything", "pause the system", "turn off the assistant", "halt all processes",
    # start
    "start detecting objects", "what's in front of me", "what's near me", "look around", "identify the things around",
    # count
    "how much money is here", "count the cash", "what amount do I have", "tell me how much this is",
    # reset
    "change language", "reset the system", "start setup again", "switch to another language",
    # current_location
    "where am I", "what's my current location", "tell me where I am", "give me my location",
    # navigate
    "take me to the mall", "I want directions to the hospital", "how do I get to the train station", "navigate to the pharmacy",
    # bookmark_location
    "save this location", "remember where I am", "bookmark this place", "mark this spot",
    # save_contact
    "save a new contact", "add John to my contacts", "remember this phone number", "store a contact for me",
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
    # background
    "random noise", "nothing here", "background", "i dont understand"
]
command_labels = [
    "reading", "reading", "reading", "reading", "stop", "stop", "stop", "stop", "start",
    "start", "start", "start", "start", "count", "count", "count", "count", "reset",
    "reset", "reset", "reset", "current_location", "current_location", "current_location", "current_location",
    "navigate", "navigate", "navigate", "navigate", "bookmark_location", "bookmark_location", "bookmark_location",
    "bookmark_location", "save_contact", "save_contact", "save_contact", "save_contact", "send_money", "send_money",
    "send_money", "send_money", "time", "time", "time", "time", "hotspots", "hotspots", "hotspots", "hotspots",
    "chat", "chat", "chat", "chat", "chat", "shutdown", "shutdown", "shutdown", "shutdown",
    "start", "start", "start", "start"
]
COMMAND_CLASSES = ["background", "reading", "start", "stop", "reset", "count"]
last_play_time = 0
tts_lock = threading.Lock()
audio_playing = threading.Event()
LANG_MODEL_PATH = './models/language_selector.keras'
LANG_MODEL = load_model(LANG_MODEL_PATH)
LANGUAGES = ['background', 'english', 'twi']
translated_audio = 'data/translated/'
translated_phrases = translated_audio + 'phrases/'
translated_numbers = translated_audio + 'numbers/'
translated_labels = translated_audio + 'labels/'

# Load models
AUDIO_COMMAND_MODEL = None
yolo_model = YOLO("./models/yolov5n.pt")
INTENT_CLASSIFIER_MODEL = "./models/knn_classifier.joblib"

cap = cv2.VideoCapture(0)

# State variables
wakeword_detected = threading.Event()
awaiting_command = False
current_mode = "start"
DATABASE = 'database.db'
