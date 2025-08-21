import time
import threading
from gpiozero import Button
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command
from config.settings import get_mode, set_mode, get_language

BUTTON_PINS = {
    "voice": 17,
    "start": 27,
    "emergency_mode": 22,
    "reading": 23
}

buttons = {
    name: Button(pin, pull_up=True) for name, pin in BUTTON_PINS.items()
}

def button_listener_thread():
    """
    Monitors the hardware buttons and changes modes accordingly.
    Runs in a background thread.
    """
    print("[GPIO Listener] Button listener started. Waiting for presses...")

    while True:
        if buttons["voice"].is_pressed and get_mode() != "voice":
            print("[BUTTON] Voice mode")
            set_mode("voice")
            got_mode, _ = handle_command(get_language())
            set_mode(got_mode)

        elif buttons["start"].is_pressed and get_mode() != "start":
            print("[BUTTON] Start mode")
            set_mode("start")

        elif buttons["emergency_mode"].is_pressed and get_mode() != "emergency_mode":
            print("[BUTTON] Emergency mode")
            set_mode("emergency_mode")

        elif buttons["reading"].is_pressed and get_mode() != "reading":
            print("[BUTTON] Reading mode")
            set_mode("reading")

        time.sleep(0.1)
