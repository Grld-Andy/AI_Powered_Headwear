# core/tts/python_ttsx3.py
import pyttsx3

engine = pyttsx3.init()
current_volume = 0.8  # default volume


def set_volume(vol):
    global current_volume
    current_volume = max(0.0, min(vol, 1.0))
    engine.setProperty('volume', current_volume)


def increase_volume():
    set_volume(current_volume + 0.1)
    speak("Volume increased.")


def decrease_volume():
    set_volume(current_volume - 0.1)
    speak("Volume decreased.")


def speak(text, volume=None):
    if volume is not None:
        original = current_volume
        set_volume(volume)
    engine.say(text)
    engine.runAndWait()
    if volume is not None:
        set_volume(original)
