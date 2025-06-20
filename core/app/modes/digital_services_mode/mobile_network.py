from core.audio.audio_capture import listen
from core.database.database import save_contact_to_db, get_contact_by_name, save_transaction
import re

from utils.say_in_language import say_in_language


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
    for attempt in range(retries + 1):  # 1 initial try + retries
        if attempt > 0:
            say_in_language("Please try again.", language, wait_for_completion=True)
        say_in_language(prompt_text, language, wait_for_completion=True)
        response = listen()
        if response:
            return response
    return None


def handle_save_contact_mode(transcribed_text, language):
    name = try_listen_with_retries("Please say the name of the contact.", language)
    if not name:
        say_in_language("Sorry, I could not understand the name. Please try again later.", language, wait_for_completion=True)
        return

    say_in_language(f"You said {name}. Now, please say the phone number.", language, wait_for_completion=True)
    number = try_listen_with_retries("Please say the phone number.", language)
    if not number:
        say_in_language("Sorry, I could not understand the number. Please try again later.", language, wait_for_completion=True)
        return

    save_contact_to_db(name, number)
    say_in_language(f"Contact {name} with number {number} saved successfully.", language, wait_for_completion=True)


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

    recipient_name = try_listen_with_retries("Who do you want to send the money to?", language)
    if not recipient_name:
        say_in_language("Sorry, I couldn't understand the name. Please try again later.", language, wait_for_completion=True)
        return

    contacts = get_contact_by_name(recipient_name)
    if not contacts:
        say_in_language(f"I couldn't find any contact named {recipient_name}.", language, wait_for_completion=True)
        return

    contact = contacts[0]
    recipient_number = contact['number']

    say_in_language(f"Sending {amount} to {contact['name']} at number {recipient_number}.", language, wait_for_completion=True)
    say_in_language("The money has been sent successfully.", language, wait_for_completion=True)
    save_transaction(contact['name'], recipient_number, amount)
