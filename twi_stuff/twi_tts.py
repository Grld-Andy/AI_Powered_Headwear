import requests
import os
from dotenv import load_dotenv
load_dotenv()

# Constants
GHANA_NLP_API = os.getenv("GHANA_NLP_API")
TTS_URL = "https://translation-api.ghananlp.org/tts/v1/synthesize"


def synthesize_speech(
    text: str,
    language: str = "tw",
    speaker_id: str = "twi_speaker_4",
    output_filename: str = "output.wav"
) -> bool:
    """
    Synthesizes speech using the GhanaNLP TTS API and saves it as an audio file.

    Args:
        text (str): Text to synthesize.
        language (str): Language code (e.g., 'tw', 'ee', 'ki').
        speaker_id (str): Voice ID based on the language.
        output_filename (str): Name of the output WAV file.

    Returns:
        bool: True if audio was saved successfully, False otherwise.
    """
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": GHANA_NLP_API
    }

    payload = {
        "text": text,
        "language": language,
        "speaker_id": speaker_id
    }

    try:
        response = requests.post(TTS_URL, json=payload, headers=headers)

        if response.status_code == 200:
            with open(output_filename, "wb") as f:
                f.write(response.content)
            print(f"✅ Audio saved as {output_filename}")
            return True
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print("Message:", response.text)
            return False
    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return False


# Example usage
synthesize_speech("Ɛte sɛn?", language="tw", speaker_id="twi_speaker_4")
