import socketio
import threading
import time

from config.settings import API_BASE_URL, get_language
from utils import say_in_language  # or wherever your token is stored

# Your JWT token for authentication
TOKEN = "your_jwt_token_here"

# Create Socket.IO client
sio = socketio.Client(reconnection=True)

# Connect event
@sio.event
def connect():
    print("[SOCKET] Connected to server")

    # Join device room after connecting
    device_ids = ["123456"]  # replace with your device IDs
    sio.emit("join_devices", device_ids)
    print(f"[SOCKET] Joined device rooms: {device_ids}")

# Disconnect event
@sio.event
def disconnect():
    print("[SOCKET] Disconnected from server")

# Listen for emergency alerts
@sio.on("emergency_alert")
def handle_emergency(data):
    print("[SOCKET] Emergency alert received:", data)
    # Here you can trigger something in your Python app, e.g., display, TTS, etc.

# Listen for location updates
@sio.on("location_update")
def handle_location_update(data):
    print("[SOCKET] Location update:", data)

# Function to send emergency from Python to Node server
def send_emergency_alert(device_id, alert_type="fall", severity="high", latitude=None, longitude=None, message="Emergency triggered"):
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

# Connect to Socket.IO server
def connect_socket():
    sio.connect(
        API_BASE_URL.replace("http", "ws") + "/socket.io", 
        auth={"token": TOKEN}
    )

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


# Listen for messages from devices
@sio.on("new_message")
def handle_new_message(data):
    print(f"New message from guardian: {data['content']}")
    # You can also use TTS here:
    say_in_language(data['content'], get_language())
