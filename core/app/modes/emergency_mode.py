import requests
from config.settings import API_BASE_URL
from core.database.database import get_device_id
from utils.say_in_language import say_in_language

def trigger_emergency_mode(frame, language, device_id="123456",
                           alert_type="other", severity="high",
                           latitude=None, longitude=None,
                           sensor_data=None, message="Emergency triggered from device"):
    """
    Handles emergency mode: announces alert and sends it to the API.
    """

    # Say alert
    say_in_language("Emergency mode activated. Sending alert.", language,
                    wait_for_completion=True, priority=1)

    # Example: use frame to calculate sensor data if needed
    if sensor_data is None:
        # fallback dummy sensor data
        sensor_data = {
            "accelerometer": [1.2, 0.8, 9.8],
            "gyroscope": [0.1, 0.2, 0.3],
            "heartRate": 85
        }

    deviceId = get_device_id()
    url = f"{API_BASE_URL}/alerts/emergency"
    payload = {
        "deviceId": deviceId,
        "alertType": alert_type,
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "sensorData": sensor_data,
        "message": message
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print("[EMERGENCY] Alert sent successfully:", response.json())
    except requests.RequestException as e:
        print("[EMERGENCY] Failed to send alert:", e)

    return frame, "start"
