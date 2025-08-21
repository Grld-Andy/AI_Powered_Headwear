import os
import re
import time
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import upload_file, GenerativeModel

# Load API key from .env
load_dotenv()
api_key = os.getenv("GOOGLE_STUDIO_AI")

if not api_key:
    raise ValueError("No API key found in .env file under GOOGLE_STUDIO_AI")

# Configure Google AI
genai.configure(api_key=api_key)

# Role instructions
CHAT_ROLE = (
    "You are a conversational assistant for a visually impaired person. "
    "Respond helpfully and clearly to text-based input. "
    "Do not assume or describe images unless explicitly told."
)

SCENE_ROLE = (
    "You are an assistant for a visually impaired person. "
    "You are given an image and must describe it clearly and in detail. "
    "Avoid emojis, keep language simple, concise, and accessible."
)

EXIT_KEYWORDS = {"exit", "quit", "close", "leave", "stop", "goodbye", "bye"}

conversation_history = []  # for text-only chat

def clean_response(text: str) -> str:
    """Cleans AI response by removing emojis, excessive punctuation, and TTS-breaking symbols."""
    if not text:
        return ""
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)  # remove emojis
    text = re.sub(r"[^a-zA-Z0-9\s.,;:'\"!?-]", "", text)  # remove weird chars
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_exit_command(user_input: str) -> bool:
    if not user_input:
        return False
    return any(word in user_input.lower() for word in EXIT_KEYWORDS)

def chat_with_gemini(prompt: str, history: list = None) -> str:
    """
    Text-only chat with Google Gemini.
    Returns cleaned text response only.
    """
    if history is None:
        history = []

    history.append({"role": "user", "parts": [CHAT_ROLE, prompt]})

    try:
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(history)
        cleaned_text = clean_response(response.text)

        history.append({"role": "model", "parts": [cleaned_text]})
        return cleaned_text
    except Exception as e:
        return f"Error calling Google Gemini: {e}"

def describe_scene_with_gemini(image_path: str,
                               prompt: str = "Describe the scene in this image.") -> str:
    """
    Sends a local image to Google Gemini and returns only the description text.
    """
    if not os.path.exists(image_path):
        return f"Error: File not found at {image_path}"

    try:
        uploaded_file = upload_file(image_path)
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([
            {"role": "user", "parts": [SCENE_ROLE, prompt, uploaded_file]}
        ])
        return clean_response(response.text)
    except Exception as e:
        return f"Error describing image: {e}"

if __name__ == "__main__":
    print("Google Gemini Chatbot (type 'exit', 'quit', 'bye' to leave)")
    conversation_history = []

    while True:
        user_input = input("You (or 'img:<path>' to send image): ")

        if is_exit_command(user_input):
            print(":exit:")
            break

        if user_input.startswith("img:"):
            image_file = user_input.replace("img:", "").strip()
            reply = describe_scene_with_gemini(image_file)
        else:
            reply = chat_with_gemini(user_input, history=conversation_history)

        print(f"Bot: {reply}")
