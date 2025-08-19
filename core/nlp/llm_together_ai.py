<<<<<<< HEAD
import re
import time
from together import Together
=======
import os
import re
import time
>>>>>>> raspberry_pi_2
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import upload_file, GenerativeModel

<<<<<<< HEAD
# Load environment variables
load_dotenv()
# meta-llama/Llama-Vision-Free
# google/gemma-3n-E4B-it

client = Together()

# Exit keywords for detecting quit intent
EXIT_KEYWORDS = {"exit", "quit", "close", "leave", "stop", "goodbye", "bye", "end chat"}

def clean_response(text: str) -> str:
    """
    Cleans AI response by removing unnecessary symbols, formatting characters, and emojis.
    """
    if not text:
        return ""
    text = re.sub(r"[*_`#~>|]", "", text)  # formatting characters
    text = re.sub(r"[^\w\s.,!?;:'\"()-]", "", text)  # emojis & non-std symbols
    text = re.sub(r"\s{2,}", " ", text).strip()  # collapse spaces
    return text

def is_exit_command(user_input: str) -> bool:
    """
    Checks if the user wants to exit the chatbot.
    """
=======
# Load API key from .env
load_dotenv()
api_key = os.getenv("GOOGLE_STUDIO_AI")

if not api_key:
    raise ValueError("No API key found in .env file under GOOGLE_STUDIO_AI")

# Configure Google AI
genai.configure(api_key=api_key)

# Role instruction for the assistant
ROLE_INSTRUCTION = (
    "You are an assistant for a visually impaired person. "
    "The user cannot see; images will be sent from a camera. "
    "If images are given, describe them clearly and in detail, "
    "avoid emojis, and use simple, concise, and accessible language."
)

EXIT_KEYWORDS = {"exit", "quit", "close", "leave", "stop", "goodbye", "bye"}

# Conversation history for multi-turn context
conversation_history = []

def clean_response(text: str) -> str:
    """
    Cleans AI response by removing emojis, excessive punctuation, and TTS-breaking symbols.
    """
    if not text:
        return ""
    # Remove emojis & non-standard symbols
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    # Remove special characters except basic punctuation
    text = re.sub(r"[^a-zA-Z0-9\s.,;:'\"!?-]", "", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_exit_command(user_input: str) -> bool:
>>>>>>> raspberry_pi_2
    if not user_input:
        return False
    return any(word in user_input.lower() for word in EXIT_KEYWORDS)

<<<<<<< HEAD
# Retentive memory: store conversation here
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are an assistant for a visually impaired person who cannot see. "
            "Images will be provided through a live camera feed. "
            "Describe visual scenes clearly and in detail, avoiding emojis, "
            "and using simple, spoken-friendly language that can be read aloud. "
            "Keep responses short and concise, but informative."
        )
    }
]

def chat_with_together(prompt: str,
                       model: str = "google/gemma-3n-E4B-it",
                       image_path: str = None) -> tuple[str, float]:
    try:
        start_time = time.time()
        conversation_history.append({"role": "user", "content": prompt})

        if image_path:
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            response = client.chat.completions.create(
                model=model,
                messages=conversation_history,
                files=[{"file": image_bytes, "name": "scene.png"}]
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=conversation_history
            )

        elapsed = time.time() - start_time
        raw_output = response.choices[0].message.content
        cleaned = clean_response(raw_output)

        conversation_history.append({"role": "assistant", "content": cleaned})
        return cleaned, elapsed

    except Exception as e:
        return f"Error calling Together API: {e}", None


def describe_scene_with_together(image_path: str,
                                 prompt: str = "Describe the scene in this image.",
                                 model: str = "google/gemma-3n-E4B-it") -> tuple[str, float]:
    """
    Sends an image to Together AI and returns a description.
    """
    try:
        start_time = time.time()

        with open(image_path, "rb") as img_file:
            image_bytes = img_file.read()

        # We only send this as a one-shot request for scene description
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant describing images for a visually impaired person. "
                    "Be clear, concise, and spoken-friendly. Avoid emojis."
                )
            },
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            files=[{"file": image_bytes, "name": "scene.png"}]
        )

        elapsed = time.time() - start_time
        raw_output = response.choices[0].message.content
        cleaned = clean_response(raw_output)

        return cleaned, elapsed

    except Exception as e:
        return f"Error calling Together API: {e}", None

if __name__ == "__main__":
    print("Together API Chatbot (type 'exit', 'quit', 'bye' to leave)")

    while True:
        try:
            user_input = input("You: ")

            # Detect quit intent before calling API
            if is_exit_command(user_input):
                print(":exit:")
                break

            response, elapsed_time = chat_with_together(user_input)
            print(f"Bot: {response}")
            if elapsed_time is not None:
                print(f"(Time taken: {elapsed_time:.2f} seconds)")

        except Exception as e:
            print(f"Error: {e}")
=======
def chat_with_gemini(prompt: str = None, image_path: str = None, history: list = None):
    """
    Chat with Google Gemini, supports optional image input.
    """
    if history is None:
        history = []

    parts = []
    if prompt:
        parts.append(prompt)

    if image_path and os.path.exists(image_path):
        try:
            uploaded_file = upload_file(image_path)
            parts.append(uploaded_file)
        except Exception as e:
            return f"Error uploading image: {e}", None, history

    # Always include role instruction
    history.append({"role": "user", "parts": [ROLE_INSTRUCTION] + parts})

    start_time = time.time()
    try:
        model = GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(history)

        cleaned_text = clean_response(response.text)
        elapsed = time.time() - start_time

        history.append({"role": "model", "parts": [cleaned_text]})
        return cleaned_text, elapsed, history

    except Exception as e:
        return f"Error calling Google Gemini: {e}", None, history

def describe_scene_with_gemini(image_path: str,
                               prompt: str = "Describe the scene in this image.",
                               history: list = None) -> tuple[str, float]:
    """
    Sends a local image to Google Gemini and returns a description.
    """
    return chat_with_gemini(prompt=prompt, image_path=image_path, history=history)[:2]

if __name__ == "__main__":
    print("Google Gemini Chatbot with Image Support (type 'exit', 'quit', 'bye' to leave)")
    conversation_history = []

    while True:
        user_input = input("You (or 'img:<path>' to send image): ")

        if is_exit_command(user_input):
            print(":exit:")
            break

        image_file = None
        text_message = None

        if user_input.startswith("img:"):
            image_file = user_input.replace("img:", "").strip()
        else:
            text_message = user_input

        reply, elapsed_time, conversation_history = chat_with_gemini(
            prompt=text_message,
            image_path=image_file,
            history=conversation_history
        )

        print(f"Bot: {reply}")
        if elapsed_time:
            print(f"(Time taken: {elapsed_time:.2f} seconds)")
>>>>>>> raspberry_pi_2
