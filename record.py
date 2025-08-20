import sounddevice as sd
import numpy as np
import wave


def record_audio(filename="output.wav", duration=5, samplerate=16000, channels=1):
    """
    Record audio from INMP441 I2S microphone and save as WAV.

    Args:
        filename (str): output wav file name
        duration (int): recording duration in seconds
        samplerate (int): sample rate in Hz (INMP441 supports up to 48kHz)
        channels (int): number of channels (1 for mono)
    """

    print(f"Recording {duration} seconds...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording finished, saving...")

    # Save as WAV
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(samplerate)
        wf.writeframes(recording.tobytes())

    print(f"Saved as {filename}")

record_audio("test_inmp441.wav", duration=10, samplerate=16000, channels=1)
