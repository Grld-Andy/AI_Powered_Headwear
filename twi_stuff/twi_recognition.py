import requests
import os
from dotenv import load_dotenv
load_dotenv()

# Constants
GHANA_NLP_API = os.getenv("GHANA_NLP_API")
ASR_URL = "https://translation-api.ghananlp.org/asr/v1/transcribe"

def transcribe_audio(file_path: str, language: str = "tw") -> str:
    """
    Transcribes an audio file using the GhanaNLP ASR API.

    Args:
        file_path (str): Path to the audio file (.mp3).
        language (str): Language code (e.g., 'tw', 'ee', 'gaa', etc.)

    Returns:
        str: Transcribed text or error message.
    """
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

# Example usage
transcribed_text = transcribe_audio("sample.mp3", language="tw")
print("Transcribed Text:", transcribed_text)
