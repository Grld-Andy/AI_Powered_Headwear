import time
import threading
from gpiozero import Button
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command
from config.settings import set_mode, get_language

BUTTON_PINS = {
    "voice": 17,
    "start": 27,
    "stop": 22,
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
        if buttons["voice"].is_pressed:
            print("[BUTTON] Voice mode")
            set_mode("voice")
            say_in_language("Hello, how may I help you?", get_language(),
                            priority=1, wait_for_completion=True)
            got_mode, _ = handle_command(get_language())
            set_mode(got_mode)

        elif buttons["start"].is_pressed:
            print("[BUTTON] Start mode")
            set_mode("start")

        elif buttons["stop"].is_pressed:
            print("[BUTTON] Stop mode")
            set_mode("stop")

        elif buttons["reading"].is_pressed:
            print("[BUTTON] Reading mode")
            set_mode("reading")

        time.sleep(0.1)
