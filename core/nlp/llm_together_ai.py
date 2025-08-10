import os
import subprocess
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
    """Optimized for Raspberry Pi:
    - Uses 'aplay' for low-latency WAV playback
    - Falls back to pydub for other formats
    """
    if not os.path.isfile(filename):
        print(f"[ERROR] File not found: {filename}")
        return

    # Try aplay for WAV files first
    if filename.lower().endswith(".wav"):
        try:
            if wait_for_completion:
                subprocess.run(["aplay", "-q", filename], check=False)
            else:
                subprocess.Popen(["aplay", "-q", filename])
            return
        except Exception as e:
            print(f"[WARN] aplay failed, falling back to pydub: {e}")

    # Fallback: pydub playback for non-WAV files
    try:
        from pydub import AudioSegment
        from pydub.playback import play
        audio = AudioSegment.from_file(filename)
        if wait_for_completion:
            play(audio)
        else:
            import threading
            threading.Thread(target=play, args=(audio,), daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Failed to play audio: {e}")


## Example English loop
# while True:
#     try:
#         print('start talking')
#         text = recognize_speech()
#         if text:
#             response = chat_with_together(text)
#             speak(response)
#     except Exception as e:
#         continue

## Example Twi loop
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
