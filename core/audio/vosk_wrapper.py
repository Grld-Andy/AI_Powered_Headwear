from vosk import Model, KaldiRecognizer
import sounddevice as sd
import json

MODEL_PATH = "../../models/vosk-model-en-us-0.22-lgraph"
model = Model(MODEL_PATH)
rec = KaldiRecognizer(model, 16000)

def callback(indata, frames, time, status):
    if status:
        print("Status:", status)
    if rec.AcceptWaveform(bytes(indata)):
        result = json.loads(rec.Result())
        print("Recognized:", result.get("text", ""))

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    print("Speak into the microphone...")
    input()  # Press Enter to stop








# import sounddevice as sd
# import wave
# import numpy as np
# import time
# from vosk import Model, KaldiRecognizer
# import json
#
# # === Config ===
# MODEL_PATH = "../../models/vosk-model-en-us-0.22-lgraph"
# DURATION = 2  # seconds
# SAMPLE_RATE = 16000
# CHANNELS = 1
# FILENAME = "recorded.wav"
#
#
# # === Step 2: Load model and recognize ===
# model = Model(MODEL_PATH)
# rec = KaldiRecognizer(model, SAMPLE_RATE)
#
# # === Step 3: Notify user ===
# print("Talk now...")
#
# # === Step 4: Record audio ===
# recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')
# sd.wait()  # Wait until recording is finished
#
# # === Step 5: Save as .wav ===
# with wave.open(FILENAME, 'wb') as wf:
#     wf.setnchannels(CHANNELS)
#     wf.setsampwidth(2)  # 16-bit audio = 2 bytes
#     wf.setframerate(SAMPLE_RATE)
#     wf.writeframes(recording.tobytes())
#
# print(f"Saved recording to {FILENAME}")
#
#
# # Read the file back in chunks
# with wave.open(FILENAME, "rb") as wf:
#     while True:
#         data = wf.readframes(4000)
#         if len(data) == 0:
#             break
#         rec.AcceptWaveform(data)
#
# result = json.loads(rec.FinalResult())
# print("Recognized text:", result.get("text", ""))
