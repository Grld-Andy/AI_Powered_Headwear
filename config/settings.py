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
twi_training_phrases = [
    # reading
    ["Wobɛtumi akyerɛw eyi?", "Kyerɛw nsɛm a ɛwɔ skrini no so", "Ɛka sɛn?", "Kyerɛw label yi ma me"],

    # stop
    ["Gyina biribiara", "Pa ɔsistem no so", "Twi assistant no so", "Gyina adwuma biara a rekɔ so"],

    # start
    ["Hyɛ ase hu adeɛ a ɛda hɔ", "Dɛn na ɛwɔ me anim?", "Dɛn na ɛbɛn me?", "Hwɛ mmerɛ so", "Hunuu nneɛma a ɛbɛn me"],

    # count
    ["Sikasɛm yi dodow bɛn?", "Kan sika no", "Mede bɛn na mewɔ?", "Ka kyerɛ me sɛ eyi yɛ sika ahe?"],

    # reset
    ["Sesaa kasa", "San yɛ sistem no foforɔ", "Hyɛ ase setup bio", "Fa kasa foforɔ"],

    # current_location
    ["Ɛhe na mewɔ?", "Ɛhe na mewɔ seesei?", "Ka kyerɛ me me baabi a mewɔ", "Ma me me baabi a mewɔ"],

    # navigate
    ["Fa me kɔ mall no", "Mepɛ kwan a ɛkɔ ayaresabea no so", "Ɛkwan bɛn so na metumi kɔ train station no?",
     "Ma kwan so kɔ pharmacy no"],

    # bookmark_location
    ["Sie baabi yi", "Kae me baabi a mewɔ", "Mark baabi yi", "Na baabi yi ho no ho"],

    # save_contact
    ["Sie contact foforɔ bi", "Fa John to me contacts mu", "Kae saa phone number yi", "Sie contact ma me"],

    # send_money
    ["Som sika kɔ maa Sarah", "Fa sika kɔ me yɔnko anim", "Yɛ mobile payment", "Tua obi sika seesei"],

    # time
    ["Ɛberɛ bɛn na ɛreba so?", "Ka kyerɛ me bere a ɛyɛ seesei", "Ɛberɛ bɛn seesei?", "Ma me bere no"],

    # hotspots
    ["Hwehwɛ adidibea a ɛbɛn hɔ", "Kyerɛ mmeaeɛ a ɛbɛn me", "Dɛn na ɛbɛn ha?", "Kyerɛ hotspots a ɛbɛn ha"],

    # chat (fallback/general)
    ["Dɛn na wokotumi yɛ?", "Wote sɛn ɛnnɛ?", "Ka biribi a eye ho asɛe", "Ma yɛnkasa", "Wobɛtumi aboa me?"],

    # shutdown
    ["Gyaade device no so", "Twi sistem no so", "Gyina power so", "Gyaade seesei"],

    # background
    ["Mmɛhwɛ haw", "Hwee nni ha", "Background", "Mente ase"]
]

english_training_phrases = [
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
training_phrases = english_training_phrases
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
current_mode = "stop"
DATABASE = 'database.db'
