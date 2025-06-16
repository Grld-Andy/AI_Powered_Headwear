import requests


def ocr_space_file(filename, api_key='helloworld', language='eng'):
    url = 'https://api.ocr.space/parse/image'
    with open(filename, 'rb') as f:
        payload = {
            'isOverlayRequired': False,
            'apikey': api_key,
            'language': language,
        }
        response = requests.post(url, files={'filename': f}, data=payload)
    result = response.json()
    return result.get("ParsedResults")[0].get("ParsedText", "")
