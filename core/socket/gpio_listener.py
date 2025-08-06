import RPi.GPIO as GPIO
import time
import threading
import wave

from config.settings import set_mode, get_mode, get_language
from utils.say_in_language import say_in_language
from core.app.command_handler import handle_command

# GPIO pin mapping to mode names
BUTTONS = {
    17: "voice",
    27: "reading",
    22: "start",
    23: "stop",
    24: "language"
}

def handle_mode_switch(mode):
    set_mode(mode)

    if mode == "voice":
        say_in_language("Hello, how may I help you?", get_language(), wait_for_completion=True, priority=1)
        print("🔊 Recording audio now...")
        record_and_transcribe()

    elif mode == "language":
        say_in_language("Please say your preferred language", get_language(), wait_for_completion=True)

    else:
        print(f"[GPIO] Mode set to: {mode}")


def record_and_transcribe():
    import pyaudio

    try:
        sample_rate = 16000
        channels = 1
        sample_format = pyaudio.paInt16
        chunk = 1024
        record_seconds = 5  # You can adjust this or make it dynamic
        wav_output_filename = "audio_capture/user_command.wav"

        audio = pyaudio.PyAudio()

        stream = audio.open(format=sample_format,
                            channels=channels,
                            rate=sample_rate,
                            input=True,
                            frames_per_buffer=chunk)

        print("🎙️ Recording...")
        frames = []

        for _ in range(0, int(sample_rate / chunk * record_seconds)):
            data = stream.read(chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        audio.terminate()

        wf = wave.open(wav_output_filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(sample_format))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        print("🧠 Transcribing...")
        command, text = handle_command(get_language())

        set_mode(command)
        print(f"[VOICE] Final Command: {command} | Transcribed: {text}")
    except Exception as e:
        print(f"[VOICE] Error during voice interaction: {e}")


def button_listener_thread():
    GPIO.setmode(GPIO.BCM)
    for pin in BUTTONS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("[GPIO] ✅ Button listener started.")
    try:
        while True:
            for pin, mode in BUTTONS.items():
                if GPIO.input(pin) == GPIO.LOW:  # Button pressed
                    print(f"[GPIO] Button on pin {pin} pressed. Switching to mode: {mode}")
                    handle_mode_switch(mode)
                    time.sleep(0.5)  # Software debounce
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("[GPIO] Button listener stopped.")
    finally:
        GPIO.cleanup()
