import os

import winsound
from together import Together
from dotenv import load_dotenv

from core.audio.googleRecognition import recognize_speech

import pyttsx3

from twi_stuff.eng_to_twi import translate_text
from twi_stuff.twi_recognition import record_and_transcribe
from twi_stuff.twi_tts import synthesize_speech


def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


load_dotenv()


def chat_with_together(
        prompt: str,
        model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
) -> str:
    try:
        client = Together()  # Uses TOGETHER_API_KEY from environment

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error calling Together API: {e}"


def play_audio_winsound(filename, wait_for_completion=True):
    if not os.path.isfile(filename):
        print(f"[ERROR] File not found: {filename}")
        return
    flags = winsound.SND_FILENAME
    if not wait_for_completion:
        flags |= winsound.SND_ASYNC
    winsound.PlaySound(filename, flags)


## English
# while True:
#     try:
#         print('start talking')
#         text = recognize_speech()
#         if text:
#             response = chat_with_together(text)
#             speak(response)
#     except Exception as e:
#         continue

## Twi
# while True:
#     try:
#         print('start talking')
#         text = record_and_transcribe(language="tw", duration=2)
#         if text:
#             text = translate_text(text, "tw-en")
#             response = chat_with_together(text)
#             translated = translate_text(response, "en-tw")
#             print(translated)
#             synthesize_speech(translated, output_filename="output.wav")
#             play_audio_winsound("output.wav")
#     except Exception as e:
#         continue
