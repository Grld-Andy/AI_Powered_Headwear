<<<<<<< HEAD
import socketio
import threading
import time

from config.settings import API_BASE_URL, get_language
from utils import say_in_language  # or wherever your token is stored

# Your JWT token for authentication
TOKEN = "your_jwt_token_here"
=======
import base64
import os
import requests
import socketio
import threading
import time
from config.settings import API_BASE_URL, BASE_URL, get_language, set_mode, get_mode
from core.audio.audio_capture import listen_and_save
from core.database.database import get_device_id
from twi_stuff.twi_recognition import record_and_transcribe
from utils.say_in_language import say_in_language

def fetch_device_token():
    device_id = get_device_id()
    response = requests.post(f"{API_BASE_URL}/devices/token", json={"deviceId": device_id})
    response.raise_for_status()
    data = response.json()
    return data["token"]

TOKEN = fetch_device_token()
>>>>>>> raspberry_pi_2

# Create Socket.IO client
sio = socketio.Client(reconnection=True)

<<<<<<< HEAD
=======
# ------------------ Device status emitter ------------------
def send_status_periodically():
    """Emit device status every 5 seconds in a separate thread."""
    device_id = get_device_id()
    while sio.connected:
        print(f"[SOCKET -->] Device status for {device_id}: connected")
        sio.emit("device_status", {
            "deviceId": device_id,
            "status": "active",
            "batteryLevel": 90,
            "isOnline": True
        })
        time.sleep(5)

def start_status_thread():
    thread = threading.Thread(target=send_status_periodically, daemon=True)
    thread.start()
# ------------------------------------------------------------

>>>>>>> raspberry_pi_2
# Connect event
@sio.event
def connect():
    print("[SOCKET] Connected to server")

    # Join device room after connecting
<<<<<<< HEAD
    device_ids = ["123456"]  # replace with your device IDs
    sio.emit("join_devices", device_ids)
    print(f"[SOCKET] Joined device rooms: {device_ids}")

=======
    device_ids = [get_device_id()]
    sio.emit("join_devices", device_ids)
    print(f"[SOCKET] Joined device rooms: {device_ids}")

    # Start periodic status updates in background
    start_status_thread()

>>>>>>> raspberry_pi_2
# Disconnect event
@sio.event
def disconnect():
    print("[SOCKET] Disconnected from server")

# Listen for emergency alerts
@sio.on("emergency_alert")
def handle_emergency(data):
    print("[SOCKET] Emergency alert received:", data)
<<<<<<< HEAD
    # Here you can trigger something in your Python app, e.g., display, TTS, etc.
=======
    # Trigger TTS or other actions here
>>>>>>> raspberry_pi_2

# Listen for location updates
@sio.on("location_update")
def handle_location_update(data):
    print("[SOCKET] Location update:", data)

<<<<<<< HEAD
# Function to send emergency from Python to Node server
def send_emergency_alert(device_id, alert_type="fall", severity="high", latitude=None, longitude=None, message="Emergency triggered"):
=======
# Send emergency alert
def send_emergency_alert(device_id, alert_type="fall", severity="high",
                         latitude=None, longitude=None, message="Emergency triggered",
                         audio_path=None):
    if not sio.connected:
        connect_socket()

    voice_bytes = None
    if audio_path:
        with open(audio_path, "rb") as f:
            voice_bytes = base64.b64encode(f.read()).decode("utf-8")  # convert to base64 string

>>>>>>> raspberry_pi_2
    payload = {
        "deviceId": device_id,
        "alertType": alert_type,
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
<<<<<<< HEAD
        "message": message
    }
    sio.emit("emergency_alert", payload)
    print("[SOCKET] Emergency alert sent:", payload)

# Connect to Socket.IO server
def connect_socket():
    sio.connect(
        API_BASE_URL.replace("http", "ws") + "/socket.io", 
        auth={"token": TOKEN}
    )
=======
        "message": message,
        "voiceFile": voice_bytes  # send audio as base64 string
    }

    sio.emit("emergency_alert", payload)
    print("[SOCKET] Emergency alert sent:", payload)


def connect_socket():
    global TOKEN
    TOKEN = fetch_device_token()
    print("[SOCKET] Connecting with token:", TOKEN)
    sio.connect(BASE_URL, auth={"token": TOKEN}, transports=["websocket"])
>>>>>>> raspberry_pi_2

# Start client in separate thread
def start_socket_thread():
    threading.Thread(target=connect_socket, daemon=True).start()

# Send a message from Python to a device room
def send_message(device_id, content, message_type="text"):
    payload = {
        "deviceId": device_id,
        "content": content,
        "messageType": message_type
    }
    sio.emit("send_message", payload)
    print("[SOCKET] Message sent:", payload)

<<<<<<< HEAD

# Listen for messages from devices
@sio.on("new_message")
def handle_new_message(data):
    print(f"New message from guardian: {data['content']}")
    # You can also use TTS here:
    say_in_language(data['content'], get_language())
=======
@sio.on("new_message")
def handle_new_message(data):
    message = data['content']
    print(f"[DEVICE] New message from guardian: {message}")
    prev_mode = get_mode()
    set_mode("stop")
    time.sleep(2)

    lang = get_language()
    say_in_language(f"New message {message}", lang, wait_for_completion=True)
    audio_path = "./data/audio_capture/confirmation.wav"
    say_in_language("Do you want to reply? Say yes or no.", lang, wait_for_completion=True)

    if lang == "twi":
        confirmation = record_and_transcribe(duration=3)
    else:
        confirmation = listen_and_save(audio_path, duration=3)

    if confirmation and confirmation.strip().lower() in ["yes", "yeah", "yep", "sure"]:
        say_in_language("Please say your reply.", lang, wait_for_completion=True)

        reply_path = "./data/audio_capture/reply.wav"
        if lang == "twi":
            user_reply = record_and_transcribe(duration=8)
        else:
            user_reply = listen_and_save(reply_path, duration=8)

        if user_reply and user_reply.strip():
            print(f"[USER REPLY] {user_reply}")
            sio.emit("reply_message", {
                "content": user_reply,
                "from": "device"
            })
            say_in_language("Your reply has been sent.", lang, wait_for_completion=True)
        else:
            say_in_language("No reply was detected.", lang, wait_for_completion=True)
    else:
        say_in_language("Okay, no reply sent.", lang, wait_for_completion=True)

    set_mode(prev_mode)


def send_payment_to_server(amount, payee_name, payee_account):
    sio.emit("send_money", {
        "amount": float(amount),
        "payeeName": payee_name,
        "payeeAccount": payee_account,
    })
>>>>>>> raspberry_pi_2
