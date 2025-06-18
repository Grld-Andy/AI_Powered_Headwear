import os
import time
import librosa
import winsound
import requests
import threading
import numpy as np
import sounddevice as sd
from pydub import AudioSegment
from scipy.io.wavfile import write
import speech_recognition as sr

from core.nlp.intent_classifier import CommandClassifier
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from config.settings import (
    LANG_MODEL_PATH, N_MFCC, MAX_TIMESTEPS, COMMAND_CLASSES, command_labels, training_phrases
)
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.twi_recognition import record_and_transcribe

# Audio event globals
tts_lock = threading.Lock()
audio_playing = threading.Event()
last_play_time = 0

# Models — loaded once
LANG_MODEL = load_model(LANG_MODEL_PATH)


def combine_audio_files(file_list, output_path="./data/audio_capture/combined_audio.wav", wait_for_completion=False,
                        priority=0):
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
                play_audio_winsound(output_path, wait_for_completion=True)
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


def record_audio(path, duration=2, fs=22050):
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    write(path, fs, audio)


def play_audio_winsound(filename, wait_for_completion=False):
    if not os.path.isfile(filename):
        print(f"[ERROR] File not found: {filename}")
        return
    flags = winsound.SND_FILENAME
    if not wait_for_completion:
        flags |= winsound.SND_ASYNC
    winsound.PlaySound(filename, flags)


def predict_audio(audio_path, model, classes, duration=2):
    seconds = duration
    fs = 44100
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
    sd.wait()
    write(audio_path, fs, myrecording)
    audio, sample_rate = librosa.load(audio_path, sr=None)
    mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=N_MFCC)
    mfcc = mfcc.T
    mfcc_padded = pad_sequences([mfcc], maxlen=MAX_TIMESTEPS, dtype='float32', padding='post', truncating='post')
    prediction = model.predict(mfcc_padded)
    predicted_class = np.argmax(prediction)
    confidence = prediction[0][predicted_class]
    return classes[predicted_class], confidence


def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Speech recognition error: {e}")
        return None


def listen_and_save(audio_path, duration):
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source)
        print(f"Recording for {duration} seconds...")
        audio_data = recognizer.record(source, duration=duration)

    with open(audio_path, "wb") as f:
        f.write(audio_data.get_wav_data())

    try:
        print("Transcribing...")
        transcribed_text = recognizer.recognize_google(audio_data)
        print(f"🗣 Transcribed Text: '{transcribed_text}'")
        return transcribed_text
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"Google request failed: {e}")
        return None


def predict_command(audio_path, language, duration=2):
    transcribed_text = ""
    print(f'the selected language is {language}')
    if language == 'twi':
        transcribed_text = record_and_transcribe()
        transcribed_text = translate_text(transcribed_text, lang="tw-en")
        print(transcribed_text)
    else:
        transcribed_text = listen_and_save(audio_path, duration)

    print(training_phrases[0])
    classifier = CommandClassifier(training_phrases, command_labels)
    predicted_label = classifier.classify(transcribed_text)
    print(f"🔮 Predicted Class: {predicted_label}")

    return predicted_label, transcribed_text
