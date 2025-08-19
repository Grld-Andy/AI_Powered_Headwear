import os
import time
import librosa
import threading
import numpy as np
import sounddevice as sd
from pydub import AudioSegment
from scipy.io.wavfile import write
import speech_recognition as sr
from pydub.playback import play
from core.nlp.intent_classifier import CommandClassifier
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from config.settings import (
    LANG_MODEL_PATH, N_MFCC, MAX_TIMESTEPS, COMMAND_CLASSES, command_labels, training_phrases
)
from core.tts.piper import send_text_to_tts
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


def record_audio(path, duration=3, fs=44100):
    print("[Mic] Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    write(path, fs, audio)
    print(f"[Mic] Saved to {path}")


def play_audio_pi(filename, wait_for_completion=False):
    """
    Plays audio using pydub instead of winsound (for Raspberry Pi/Linux).
    The function name is kept for compatibility with existing code.
    """
    if not os.path.isfile(filename):
        print(f"[ERROR] File not found: {filename}")
        return

    try:
        audio = AudioSegment.from_file(filename)
        if wait_for_completion:
            play(audio)
        else:
            # Play asynchronously in a thread
            threading.Thread(target=play, args=(audio,)).start()
    except Exception as e:
        print(f"[ERROR] Could not play audio {filename}: {e}")


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


def listen_and_save(audio_path, duration, i=0):
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print(f"🎤 Using PC microphone. Attempt {i + 1}")
            recognizer.adjust_for_ambient_noise(source)
            print(f"Listening... Please speak clearly. Recording for {duration} seconds.")
            audio_data = recognizer.record(source, duration=duration)

        with open(audio_path, "wb") as f:
            f.write(audio_data.get_wav_data())
        print("📝 Transcribing...")
        transcribed_text = recognizer.recognize_google(audio_data)
        print(f"🗣 Transcribed Text: '{transcribed_text}'")
        return transcribed_text

    except sr.UnknownValueError:
        print("Could not understand audio.")
        if i < 2:
            send_text_to_tts("I didn't get that. Could you please try again?", wait_for_completion=True, priority=1)
            return listen_and_save(audio_path, duration, i=i + 1)
        else:
            send_text_to_tts("Sorry, I'm still having trouble understanding you.", wait_for_completion=True, priority=1)
            return ""

    except sr.RequestError as e:
        print(f"Google request failed: {e}")
        send_text_to_tts("Please check your network connection and try again.", wait_for_completion=True, priority=1)
        return ""

    except OSError as e:
        print(f"Microphone error: {e}")
        send_text_to_tts("No microphone was found or it isn't working.", wait_for_completion=True, priority=1)
        return ""



def predict_command(audio_path, language, duration=3):
    if language == 'twi':
        transcribed_text = record_and_transcribe(duration)
        print("Translated text: ", transcribed_text)
    else:
        transcribed_text = listen_and_save(audio_path, duration)

    if transcribed_text == "":
        return "background", transcribed_text

    print(f"this is what you said {transcribed_text}")
    classifier = CommandClassifier(training_phrases, command_labels)
    predicted_label = classifier.classify(transcribed_text)
    print(f"🔮 Predicted Class: {predicted_label}")

    return predicted_label, transcribed_text
