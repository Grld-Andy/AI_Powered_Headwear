from core.audio.audio_capture import listen
from core.database.database import save_contact_to_db, get_contact_by_name, save_transaction
from core.tts.python_ttsx3 import speak
import re


def extract_name_from_phrase(phrase):
    # General fallback: extract a capitalized word before 'number' or 'contact'
    match = re.search(r"\b([A-Z][a-z]+)\b(?:'s)?\s+(?:number|contact)", phrase)
    if match:
        return match.group(1).strip()

    # Look for phrases like "what's John's number", "give me Sarah's contact", etc.
    match = re.search(
        r"(?:what(?:'s| is)|give me|show me|get|find|look up|see if|check if)\s+(.*?)'s\s+(?:number|contact|info|information)",
        phrase, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback to pattern like: "do I have Lisa's number"
    match = re.search(r"have\s+(.*?)'s\s+(?:number|contact)", phrase, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None


def handle_save_contact_mode(transcribed_text):
    speak("Please say the name of the contact.")
    name = listen()
    if not name:
        speak("Sorry, I could not understand the name. Please try again later.")
        return

    speak(f"You said {name}. Now, please say the phone number.")
    number = listen()
    if not number:
        speak("Sorry, I could not understand the number. Please try again later.")
        return

    save_contact_to_db(name, number)
    speak(f"Contact {name} with number {number} saved successfully.")


def handle_get_contact_mode():
    speak("Who do you want to search for?")
    name = listen()
    if not name:
        speak("Sorry, I could not understand the name. Please try again.")
        return
    contact = get_contact_by_name(name)

    if contact:
        speak(f"{contact['name']}'s phone number is {contact['number']}.")
    else:
        speak(f"Sorry, I couldn't find any contact named {name}.")


def handle_send_money_mode(transcribed_text=None):
    speak("How much money would you like to send?")
    amount = listen()

    if not amount:
        speak("Sorry, I couldn't understand the amount. Please try again later.")
        return

    speak("Who do you want to send the money to?")
    recipient_name = listen()

    if not recipient_name:
        speak("Sorry, I couldn't understand the name. Please try again later.")
        return

    contacts = get_contact_by_name(recipient_name)

    if not contacts:
        speak(f"I couldn't find any contact named {recipient_name}.")
        return

    contact = contacts[0]
    recipient_number = contact['number']

    # Simulate sending money
    speak(f"Sending {amount} to {contact['name']} at number {recipient_number}.")
    speak("The money has been sent successfully.")

    # Save the transaction
    save_transaction(contact['name'], recipient_number, amount)
