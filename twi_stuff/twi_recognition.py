import requests
import os
import sounddevice as sd
from scipy.io.wavfile import write
from pydub import AudioSegment
from dotenv import load_dotenv

from config.settings import get_language
from twi_stuff.eng_to_twi import translate_text

load_dotenv()

# Constants
GHANA_NLP_API = os.getenv("GHANA_NLP_API")
ASR_URL = "https://translation-api.ghananlp.org/asr/v1/transcribe"


def record_audio(filename="data/twi_audio.wav", duration=2, fs=44100):
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    write(filename, fs, audio)
    print(f"💾 Audio saved to {filename}")


def convert_wav_to_mp3(wav_file="data/user_command.wav", mp3_file="data/twi_audio.mp3"):
    audio = AudioSegment.from_wav(wav_file)
    audio.export(mp3_file, format="mp3")
    print(f"🔄 Converted to {mp3_file}")
    return mp3_file


def transcribe_audio(file_path: str, language: str = "tw") -> str:
    headers = {
        "Ocp-Apim-Subscription-Key": GHANA_NLP_API,
        "Content-Type": "audio/mpeg"
    }

    params = {
        "language": language
    }

    try:
        with open(file_path, "rb") as audio_file:
            response = requests.post(
                ASR_URL,
                headers=headers,
                params=params,
                data=audio_file
            )

        if response.status_code == 200:
            print("✅ Transcription successful:")
            return response.text
        else:
            print(f"❌ Failed with status code {response.status_code}")
            return response.text
    except Exception as e:
        return f"❌ Exception: {str(e)}"


def record_and_transcribe(language="tw", duration=4):
    wav_file = "audio_capture/user_command.wav"
    mp3_file = "audio_capture/twi_audio.mp3"
    record_audio(wav_file, duration)
    convert_wav_to_mp3(wav_file, mp3_file)
    transcribed_text = transcribe_audio(mp3_file, language)
    translated_text = translate_text(transcribed_text, lang="tw-en")
    return translated_text

# transcription = record_and_transcribe(language="tw", duration=2)
# print("📝 Transcribed Text:", transcription)
