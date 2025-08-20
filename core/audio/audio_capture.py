import os
import time
import librosa
import threading
import numpy as np
import sounddevice as sd
from pydub import AudioSegment
from scipy.io.wavfile import write
from pydub.playback import play
from core.nlp.intent_classifier import CommandClassifier
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from config.settings import (
    LANG_MODEL_PATH, N_MFCC, MAX_TIMESTEPS, COMMAND_CLASSES, command_labels, training_phrases
)
from core.tts.piper import send_text_to_tts
from twi_stuff.twi_recognition import record_and_transcribe
import speech_recognition as sr


# import sounddevice as sd
# print(sd.query_devices())


# Audio event globals
tts_lock = threading.Lock()
audio_playing = threading.Event()
last_play_time = 0

# Models — loaded once
LANG_MODEL = load_model(LANG_MODEL_PATH)

# Default INMP441 params
DEFAULT_FS = 16000
DEFAULT_DEVICE = None  # set to "hw:1,0" or device index after checking sd.query_devices()

def listen(audio_path, duration, fs=DEFAULT_FS, device=DEFAULT_DEVICE, i=0):
    return listen_and_save(audio_path, duration, fs, device, i)

def combine_audio_files(file_list, output_path="./data/audio_capture/combined_audio.wav",
                        wait_for_completion=False, priority=0):
    global last_play_time

    if priority == 0 and audio_playing.is_set():
        return

    acquired = tts_lock.acquire(timeout=5)
    if not acquired:
        return

    try:
        if priority == 0 and audio_playing.is_set():
            return

        combined = AudioSegment.empty()
        for file in file_list:
            if not os.path.isfile(file):
                continue
            try:
                audio = AudioSegment.from_file(file)
                combined += audio
            except Exception as e:
                print("Exception reading file:", file, e)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined.export(output_path, format="wav")

        audio_playing.set()

        def play_and_release():
            global last_play_time
            try:
                play_audio_pi(output_path, wait_for_completion=True)
                last_play_time = time.time()
            finally:
                audio_playing.clear()
                tts_lock.release()

        if wait_for_completion:
            play_and_release()
        else:
            threading.Thread(target=play_and_release).start()

    except Exception as e:
        print("Exception during audio combination or playback:", e)
        audio_playing.clear()
        tts_lock.release()


def record_audio(path, duration=3, fs=DEFAULT_FS, device=DEFAULT_DEVICE):
    """Record from INMP441 (I2S) and save as WAV"""
    print(f"[INMP441] Recording {duration}s at {fs}Hz...")
    try:
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1,
                       dtype='int16', device=device)
        sd.wait()
        write(path, fs, audio)
        print(f"[INMP441] Saved to {path}")
    except Exception as e:
        print(f"[ERROR] Recording failed: {e}")


def play_audio_pi(filename, wait_for_completion=False):
    """Play audio using pydub (works on Raspberry Pi/Linux)."""
    if not os.path.isfile(filename):
        print(f"[ERROR] File not found: {filename}")
        return

    try:
        audio = AudioSegment.from_file(filename)
        if wait_for_completion:
            play(audio)
        else:
            threading.Thread(target=play, args=(audio,)).start()
    except Exception as e:
        print(f"[ERROR] Could not play audio {filename}: {e}")


def predict_audio(audio_path, model, classes, duration=2, fs=DEFAULT_FS, device=DEFAULT_DEVICE):
    """Record from INMP441, extract MFCCs, run prediction."""
    print(f"[INMP441] Recording {duration}s for prediction...")
    try:
        myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1,
                             dtype='int16', device=device)
        sd.wait()
        write(audio_path, fs, myrecording)

        audio, sample_rate = librosa.load(audio_path, sr=None)
        mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=N_MFCC)
        mfcc = mfcc.T
        mfcc_padded = pad_sequences([mfcc], maxlen=MAX_TIMESTEPS,
                                    dtype='float32', padding='post', truncating='post')
        prediction = model.predict(mfcc_padded)
        predicted_class = np.argmax(prediction)
        confidence = prediction[0][predicted_class]
        return classes[predicted_class], confidence
    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        return "error", 0.0


def listen_and_save(audio_path, duration, fs=DEFAULT_FS, device=DEFAULT_DEVICE, i=0):
    """
    Record with INMP441 instead of sr.Microphone,
    then transcribe using Google Speech Recognition.
    """
    recognizer = sr.Recognizer()
    try:
        # record with sounddevice
        print(f"🎤 Recording from INMP441 (attempt {i+1}) for {duration}s...")
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1,
                       dtype='int16', device=device)
        sd.wait()
        write(audio_path, fs, audio)

        # load and send to recognizer
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)

        print("📝 Transcribing...")
        transcribed_text = recognizer.recognize_google(audio_data)
        print(f"🗣 Transcribed: '{transcribed_text}'")
        return transcribed_text

    except sr.UnknownValueError:
        print("Could not understand audio.")
        if i < 2:
            send_text_to_tts("I didn't get that. Could you please try again?", wait_for_completion=True, priority=1)
            return listen_and_save(audio_path, duration, fs=fs, device=device, i=i + 1)
        else:
            send_text_to_tts("Sorry, I'm still having trouble understanding you.", wait_for_completion=True, priority=1)
            return ""

    except sr.RequestError as e:
        print(f"Google request failed: {e}")
        send_text_to_tts("Please check your network connection and try again.", wait_for_completion=True, priority=1)
        return ""

    except Exception as e:
        print(f"[ERROR] Mic error: {e}")
        send_text_to_tts("No microphone was found or it isn't working.", wait_for_completion=True, priority=1)
        return ""


def predict_command(audio_path, language, duration=3, fs=DEFAULT_FS, device=DEFAULT_DEVICE):
    if language == 'twi':
        transcribed_text = record_and_transcribe(duration)
        print("Translated text: ", transcribed_text)
    else:
        transcribed_text = listen_and_save(audio_path, duration, fs=fs, device=device)

    if transcribed_text == "":
        return "background", transcribed_text

    print(f"this is what you said {transcribed_text}")
    classifier = CommandClassifier(training_phrases, command_labels)
    predicted_label = classifier.classify(transcribed_text)
    print(f"🔮 Predicted Class: {predicted_label}")

    return predicted_label, transcribed_text
