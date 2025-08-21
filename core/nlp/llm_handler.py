import httpx
import speech_recognition as sr

from config.settings import SELECTED_LANGUAGE, pc_Ip, set_mode
from core.nlp.llm_together_ai import chat_with_gemini
from core.tts.piper import send_text_to_tts
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.translate_and_say import translate_and_play

OLLAMA_URL = f"http://{pc_Ip}:11434/api/generate"
MODEL_NAME = "tinyllama"


class TinyLlamaClient:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
        self.client = httpx.Client(timeout=15.0)

    def send_prompt(self, prompt: str, stream: bool = False) -> str:
        try:
            response = self.client.post(
                OLLAMA_URL,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": stream
                }
            )
            response.raise_for_status()
            return response.json().get("response", "No 'response' key found.")
        except httpx.HTTPStatusError as e:
            return f"HTTP Error: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Request failed: {e}"

    def close(self):
        self.client.close()


def warm_up_tinyllama(model: str = MODEL_NAME):
    """Preloads the model into memory."""
    try:
        print("Warming up TinyLlama...")
        response = httpx.post(OLLAMA_URL, json={"model": model, "prompt": "warmup"})
        response.raise_for_status()
        print("TinyLlama is ready.")
    except Exception as e:
        print("Failed to warm up TinyLlama:", e)

def handle_chat_mode(duration: int = 2) -> str:
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎤 Listening for chat prompt...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, phrase_time_limit=duration)

    try:
        transcribed_text = recognizer.recognize_google(audio)
        print(f"🗣️ User said: {transcribed_text}")
        # if exit or close in user input return
        if "exit" in transcribed_text.lower() or "close" in transcribed_text.lower():
            set_mode("stop")
            return "Goodbye!"
        response = chat_with_gemini(transcribed_text)
        print(response)

        if SELECTED_LANGUAGE == 'twi':
            translated_text = translate_text(transcribed_text, "en-tw")
            translate_and_play(translated_text, wait_for_completion=True)
        else:
            send_text_to_tts(response, wait_for_completion=True, priority=1)
        return response

    except sr.UnknownValueError:
        return "Sorry, I couldn't understand what you said."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"
