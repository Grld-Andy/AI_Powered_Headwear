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

# Create Socket.IO client
sio = socketio.Client(reconnection=True)

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

# Connect event
@sio.event
def connect():
    print("[SOCKET] Connected to server")

    # Join device room after connecting
    device_ids = [get_device_id()]
    sio.emit("join_devices", device_ids)
    print(f"[SOCKET] Joined device rooms: {device_ids}")

    # Start periodic status updates in background
    start_status_thread()

# Disconnect event
@sio.event
def disconnect():
    print("[SOCKET] Disconnected from server")

# Listen for emergency alerts
@sio.on("emergency_alert")
def handle_emergency(data):
    print("[SOCKET] Emergency alert received:", data)
    # Trigger TTS or other actions here

# Listen for location updates
@sio.on("location_update")
def handle_location_update(data):
    print("[SOCKET] Location update:", data)

# Send emergency alert
def send_emergency_alert(device_id, alert_type="fall", severity="high", latitude=None, longitude=None, message="Emergency triggered"):
    if not sio.connected:
        print("[SOCKET] Not connected. Connecting now...")
        connect_socket()
        time.sleep(1)

    payload = {
        "deviceId": device_id,
        "alertType": alert_type,
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "message": message
    }
    sio.emit("emergency_alert", payload)
    print("[SOCKET] Emergency alert sent:", payload)

def connect_socket():
    global TOKEN
    TOKEN = fetch_device_token()
    print("[SOCKET] Connecting with token:", TOKEN)
    sio.connect(BASE_URL, auth={"token": TOKEN}, transports=["websocket"])

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

@sio.on("new_message")
def handle_new_message(data):
    message = data['content']
    print(f"[DEVICE] New message from guardian: {message}")
    prev_mode = get_mode()
    set_mode("stop")
    time.sleep(2)

    say_in_language(f"New message {message}", get_language(), wait_for_completion=True)
    
    sio.emit("reply_message", {
        "deviceId": get_device_id(),
        "content": "i have received the message",
        "messageType": "voice"
    })
    print('replied to message')

    # say_in_language(f"New message {message}", get_language(), wait_for_completion=True)
    # say_in_language("Do you want to reply? Say yes or no after the beep.", get_language(), wait_for_completion=True)
    # lang = get_language()
    # audio_path = "./data/audio_capture/confirmation.wav"

    # if lang == "twi":
    #     confirmation = record_and_transcribe(duration=3)
    # else:
    #     confirmation = listen_and_save(audio_path, duration=3)

    # if confirmation and confirmation.strip().lower() in ["yes", "yeah", "yep", "sure"]:
    #     say_in_language("Please say your reply after the beep.", lang, wait_for_completion=True)

    #     reply_path = "./data/audio_capture/reply.wav"
    #     if lang == "twi":
    #         user_reply = record_and_transcribe(duration=8)
    #     else:
    #         user_reply = listen_and_save(reply_path, duration=8)

    #     if user_reply and user_reply.strip():
    #         print(f"[USER REPLY] {user_reply}")
    #         sio.emit("reply_message", {
    #             "content": user_reply,
    #             "from": "device"
    #         })
    #         say_in_language("Your reply has been sent.", lang, wait_for_completion=True)
    #     else:
    #         say_in_language("No reply was detected.", lang, wait_for_completion=True)
    # else:
    #     say_in_language("Okay, no reply sent.", lang, wait_for_completion=True)

    set_mode(prev_mode)


def send_payment_to_server(amount, payee_name, payee_account):
    sio.emit("send_money", {
        "amount": amount,
        "payeeName": payee_name,
        "payeeAccount": payee_account,
    })