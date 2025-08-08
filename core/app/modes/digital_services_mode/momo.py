import http.client
import urllib.parse
import json
import base64
import uuid
import os
from dotenv import load_dotenv
load_dotenv()

def create_api_user(reference_id, subscription_key, callback_host):
    """Create API user"""
    headers = {
        'X-Reference-Id': reference_id,
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    params = urllib.parse.urlencode({})
    body = json.dumps({
        "providerCallbackHost": callback_host
    })
    try:
        conn = http.client.HTTPSConnection('ericssonbasicapi2.azure-api.net')
        conn.request("POST", f"/v1_0/apiuser?{params}", body, headers)
        response = conn.getresponse()
        print("Create API User:", response.status, response.reason)
        print(response.read().decode())
        conn.close()
    except Exception as e:
        print(f"Error in create_api_user: {e}")


def create_api_key(reference_id, subscription_key, callback_host):
    """Create API key"""
    headers = {
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': subscription_key
    }
    params = urllib.parse.urlencode({})
    body = json.dumps({
        "providerCallbackHost": callback_host
    })
    try:
        conn = http.client.HTTPSConnection('ericssonbasicapi2.azure-api.net')
        conn.request("POST", f"/v1_0/apiuser/{reference_id}/apikey?{params}", body, headers)
        response = conn.getresponse()
        print("Create API Key:", response.status, response.reason)
        print(response.read().decode())
        conn.close()
    except Exception as e:
        print(f"Error in create_api_key: {e}")


def get_collection_token(api_user, api_key, subscription_key):
    """Get collection token"""
    api_user_and_key = f"{api_user}:{api_key}"
    encoded = base64.b64encode(api_user_and_key.encode()).decode()
    headers = {
        'Authorization': f"Basic {encoded}",
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    params = urllib.parse.urlencode({})
    try:
        conn = http.client.HTTPSConnection('ericssonbasicapi2.azure-api.net')
        conn.request("POST", f"/collection/token/?{params}", "{body}", headers)
        response = conn.getresponse()
        print("Get Collection Token:", response.status, response.reason)
        print(response.read().decode())
        conn.close()
    except Exception as e:
        print(f"Error in get_collection_token: {e}")


def request_to_pay(token, subscription_key, callback_url, amount, currency, external_id, party_id, payer_message, payee_note):
    """Send a request-to-pay using MTN MoMo API"""
    reference_id = str(uuid.uuid4())
    print(f"Reference ID: {reference_id}")

    headers = {
        'Authorization': f'Bearer {token}',
        'X-Callback-Url': callback_url,
        'X-Reference-Id': reference_id,
        'X-Target-Environment': 'production',  # Change to 'production' if live
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': subscription_key,
    }

    params = urllib.parse.urlencode({})

    body = json.dumps({
        "amount": str(amount),
        "currency": currency,
        "externalId": external_id,
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": party_id
        },
        "payerMessage": payer_message,
        "payeeNote": payee_note
    })

    try:
        conn = http.client.HTTPSConnection('ericssonbasicapi2.azure-api.net')
        conn.request("POST", f"/collection/v1_0/requesttopay?{params}", body, headers)
        response = conn.getresponse()
        print("Request to Pay:", response.status, response.reason)
        print(response.read().decode())
        conn.close()
    except Exception as e:
        print(f"Error in request_to_pay: {e}")


reference_id=os.getenv("MOMO_REFERENCE_ID")
subscription_key=os.getenv("MOMO_SUBSCRIPTION_KEY")
domain='myapp.testdomain.com'
token=os.getenv("MOMO_ACCESS_TOKEN")
api_key=os.getenv("MOMO_API_KEY")

# create_api_user(reference_id, subscription_key, domain)
# create_api_key(reference_id, subscription_key, domain)
# get_collection_token(reference_id, api_key, subscription_key)

request_to_pay(
    token,
    subscription_key,
    f"http://{domain}/momoapi/callback",
    '1',                 # amount in GHS
    "EUR",
    "ORDER12345",            # your external ID
    "233241234567",
    "Payment for order",
    "Thanks for your business"
)
