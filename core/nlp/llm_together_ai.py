import re
import time
from together import Together
from dotenv import load_dotenv

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
    if not user_input:
        return False
    return any(word in user_input.lower() for word in EXIT_KEYWORDS)

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
    print("sending image to describe: ", image_path)
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
