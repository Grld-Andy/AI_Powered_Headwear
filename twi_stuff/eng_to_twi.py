import requests
import os
from dotenv import load_dotenv
load_dotenv()

# Constants
GHANA_NLP_API = os.getenv("GHANA_NLP_API")
TRANSLATION_URL = "https://translation-api.ghananlp.org/v1/translate"


def translate_text(text: str, lang: str = "en-tw") -> str:
    """
    Translates the given text using GhanaNLP Translation API.

    Args:
        text (str): The text to translate.
        lang (str): Language pair in 'from-to' format (e.g., 'en-tw').

    Returns:
        str: Translated text or error message.
    """
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": GHANA_NLP_API
    }

    payload = {
        "in": text,
        "lang": lang
    }

    try:
        response = requests.post(TRANSLATION_URL, json=payload, headers=headers)

        if response.status_code == 200:
            print(f"Translated text: {response.text}")
            return response.text
        else:
            return f"Error {response.status_code}: {response.json().get('message', 'Unknown error')}"
    except Exception as e:
        return f"Exception occurred: {str(e)}"


# # Example usage
# translated = translate_text("Good morning", "en-tw")
# print("Translated:", translated)
