from core.audio.audio_capture import listen
from core.database.database import save_contact_to_db, get_contact_by_name, save_transaction
import re
from core.socket.socket_client import send_payment_to_server
from utils.say_in_language import say_in_language
import requests

API_USER = "your_api_user"
API_KEY = "your_api_key"
SUBSCRIPTION_KEY = "your_subscription_key"
BASE_URL = "https://sandbox.momodeveloper.mtn.com"

def get_access_token():
    headers = {
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY
    }
    data = {
        "username": API_USER,
        "password": API_KEY
    }
    response = requests.post(f"{BASE_URL}/collection/token/", headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def send_money(amount, phone_number):
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Reference-Id": "unique_transaction_id_here",
        "X-Target-Environment": "sandbox",  # Use "production" for live
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY
    }
    body = {
        "amount": str(amount),
        "currency": "UGX",  # or GHS, ZMW, etc.
        "externalId": "123456",
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": phone_number
        },
        "payerMessage": "Payment from voice assistant",
        "payeeNote": "Thanks"
    }
    response = requests.post(f"{BASE_URL}/collection/v1_0/requesttopay", headers=headers, json=body)
    response.raise_for_status()
    return response.status_code == 202


def extract_name_from_phrase(phrase):
    match = re.search(r"\b([A-Z][a-z]+)\b(?:'s)?\s+(?:number|contact)", phrase)
    if match:
        return match.group(1).strip()
    match = re.search(
        r"(?:what(?:'s| is)|give me|show me|get|find|look up|see if|check if)\s+(.*?)'s\s+(?:number|contact|info|information)",
        phrase, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"have\s+(.*?)'s\s+(?:number|contact)", phrase, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def try_listen_with_retries(prompt_text, language, retries=2):
    for attempt in range(retries + 1):
        if attempt > 0:
            say_in_language("Please try again.", language, wait_for_completion=True)
        say_in_language(prompt_text, language, wait_for_completion=True)
        response = listen("./data/audio_capture/mobile_network.wav", language=language, duration=5, fs=16000, device=None)
        if response:
            return response
    return None


def handle_save_contact_mode(transcribed_text, language):
    while True:
        name = try_listen_with_retries("Please say the name of the contact.", language)
        if not name:
            say_in_language("Sorry, I could not understand the name. Please try again later.", language, wait_for_completion=True)
            return
        existing_contact = get_contact_by_name(name)
        if existing_contact:
            say_in_language(f"A contact named {name} already exists with number {existing_contact['number']}. Please choose a different name.", language, wait_for_completion=True)
            continue
        else:
            break
    while True:
        say_in_language(f"You said {name}. Now, please say the phone number.", language, wait_for_completion=True)
        number_raw = try_listen_with_retries("Please say the phone number.", language)
        if not number_raw:
            say_in_language("Sorry, I could not understand the number. Please try again later.", language, wait_for_completion=True)
            return
        number_digits = re.sub(r"\D", "", number_raw)
        if len(number_digits) == 10:
            save_contact_to_db(name, number_digits)
            say_in_language(f"Contact {name} with number {number_digits} saved successfully.", language, wait_for_completion=True)
            break
        else:
            say_in_language("The phone number must be exactly 10 digits. Please try again.", language, wait_for_completion=True)


def handle_get_contact_mode(language):
    name = try_listen_with_retries("Who do you want to search for?", language)
    if not name:
        say_in_language("Sorry, I could not understand the name. Please try again later.", language, wait_for_completion=True)
        return
    contact = get_contact_by_name(name)
    if contact:
        say_in_language(f"{contact['name']}'s phone number is {contact['number']}.", language, wait_for_completion=True)
    else:
        say_in_language(f"Sorry, I couldn't find any contact named {name}.", language, wait_for_completion=True)


def handle_send_money_mode(transcribed_text, language):
    amount = try_listen_with_retries("How much money would you like to send?", language)
    if not amount:
        say_in_language("Sorry, I couldn't understand the amount. Please try again later.", language, wait_for_completion=True)
        return

    recipient_input = try_listen_with_retries("Who do you want to send the money to? You can say a name or a phone number.", language)
    if not recipient_input:
        say_in_language("Sorry, I couldn't understand the recipient. Please try again later.", language, wait_for_completion=True)
        return

    recipient_number_digits = re.sub(r"\D", "", recipient_input)
    if len(recipient_number_digits) == 10:
        payee_name = "Unknown"
        send_payment_to_server(amount, payee_name, recipient_number_digits)
        save_transaction(payee_name, recipient_number_digits, amount)
        say_in_language(f"Sending {amount} to number {recipient_number_digits}.", language, wait_for_completion=True)
        say_in_language("The money has been sent successfully.", language, wait_for_completion=True)
        return

    contact = get_contact_by_name(recipient_input)
    if not contact:
        say_in_language(f"I couldn't find any contact named {recipient_input}.", language, wait_for_completion=True)
        return

    recipient_number = contact['number']
    send_payment_to_server(amount, contact['name'], recipient_number)
    save_transaction(contact['name'], recipient_number, amount)
    say_in_language(f"Sending {amount} to {contact['name']} at number {recipient_number}.", language, wait_for_completion=True)
    say_in_language("The money has been sent successfully.", language, wait_for_completion=True)
    