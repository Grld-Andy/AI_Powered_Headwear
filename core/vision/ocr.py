import os
import requests
from dotenv import load_dotenv

load_dotenv()
OCR_API_KEY = os.getenv("OCR_API_KEY")

def ocr_space_file(filename, api_key=OCR_API_KEY, language='eng'):
    print('sending request')
    url = 'https://api.ocr.space/parse/image'
    with open(filename, 'rb') as f:
        payload = {
            'isOverlayRequired': False,
            'apikey': api_key,
            'language': language,
        }
        response = requests.post(url, files={'filename': f}, data=payload, timeout=30)
    print('gotten response')

    result = response.json()

    if result.get("IsErroredOnProcessing"):
        print("OCR API Error:", result.get("ErrorMessage"))
        return ""

    parsed_results = result.get("ParsedResults")
    if not parsed_results:
        print("No ParsedResults in response.")
        return ""

    return parsed_results[0].get("ParsedText", "")
