import re
import time
from together import Together
from dotenv import load_dotenv

load_dotenv()
# meta-llama/Llama-Vision-Free
# google/gemma-3n-E4B-it

client = Together()

def clean_response(text: str) -> str:
    # Remove formatting symbols and emojis
    text = re.sub(r"[*_`#~>|]", "", text)
    text = re.sub(r"[^\w\s.,!?;:'\"()-]", "", text)  # removes emojis & other symbols
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

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
                       model: str = "google/gemma-3n-E4B-it") -> tuple[str, float]:
    try:
        start_time = time.time()
        # Add the user's message to the conversation
        conversation_history.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=conversation_history
        )

        elapsed = time.time() - start_time
        raw_output = response.choices[0].message.content
        cleaned = clean_response(raw_output)

        # Save the assistant's reply for future context
        conversation_history.append({"role": "assistant", "content": cleaned})

        return cleaned, elapsed
    except Exception as e:
        return f"Error calling Together API: {e}", None


# Loop to interact
while True:
    try:
        text = input("Enter text (or 'exit' to quit): ")
        if text.lower() == 'exit':
            break
        response, elapsed_time = chat_with_together(text)
        print(f"Response: {response}")
        if elapsed_time is not None:
            print(f"Time taken: {elapsed_time:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")
