import httpx
import speech_recognition as sr

from config.settings import SELECTED_LANGUAGE
from core.nlp.llm_together_ai import chat_with_together
from core.tts.piper import send_text_to_tts
from twi_stuff.eng_to_twi import translate_text
from twi_stuff.translate_and_say import translate_and_play

# ----------- Configuration ------------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "tinyllama"


class TinyLlamaClient:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model
        self.client = httpx.Client(timeout=15.0)  # sync client with keep-alive

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


# warm_up_tinyllama()

# # Optional: preload model into memory
# llama = TinyLlamaClient()
# prompt = "where is tarkwa?"
# new_response = llama.send_prompt(prompt)
# print("TinyLlama Response:\n", new_response)
# llama.close()


def handle_chat_mode(duration: int = 2) -> str:
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎤 Listening for chat prompt...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, phrase_time_limit=duration)

    try:
        # Transcribe using Google
        transcribed_text = recognizer.recognize_google(audio)
        print(f"🗣️ User said: {transcribed_text}")

        # # Send to TinyLlama
        # tiny_llama = TinyLlamaClient()
        # response = tiny_llama.send_prompt(transcribed_text)
        # tiny_llama.close()

        response = chat_with_together(transcribed_text)

        if SELECTED_LANGUAGE == 'twi':
            translated_text = translate_text(transcribed_text, "en-tw")
            translate_and_play(translated_text, wait_for_completion=True)
        else:
            send_text_to_tts(response, wait_for_completion=True, priority=0)
        return response

    except sr.UnknownValueError:
        return "Sorry, I couldn't understand what you said."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"
