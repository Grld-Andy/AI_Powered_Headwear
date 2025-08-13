import sqlite3
import random
import requests
import json
from config.settings import DATABASE, API_BASE_URL
from datetime import datetime


def setup_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            number TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_contacts_name_lower ON contacts (LOWER(name))')
    c.execute('''
        CREATE TABLE IF NOT EXISTS device (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            language TEXT NOT NULL,
            device_id INTEGER UNIQUE NOT NULL,
            is_registered BOOLEAN DEFAULT FALSE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL,
            amount TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    ''')
    c.execute('SELECT COUNT(*) FROM device')
    if c.fetchone()[0] == 0:
        device_id = random.randint(100000, 999999)
        c.execute(
            'INSERT INTO device (id, language, device_id, is_registered) VALUES (1, ?, ?, FALSE)',
            ("english", device_id)
        )
        print(f"Generated device ID: {device_id}")
        register_device_with_api(device_id)
    conn.commit()
    conn.close()


def register_device_with_api(device_id):
    try:
        url = f"{API_BASE_URL}/devices/register"
        registration_data = {
            "deviceId": str(device_id)
        }
        print(f"Registering device {device_id} with API...")
        response = requests.post(
            url,
            json=registration_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if response.status_code == 201:
            print(f"✅ Device {device_id} registered successfully with API")
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('UPDATE device SET is_registered = TRUE WHERE device_id = ?', (device_id,))
            conn.commit()
            conn.close()
            return True
        elif response.status_code == 400:
            error_data = response.json()
            if "Device ID already exists" in error_data.get('message', ''):
                print(f"⚠️ Device {device_id} already registered with API")
                conn = sqlite3.connect(DATABASE)
                c = conn.cursor()
                c.execute('UPDATE device SET is_registered = TRUE WHERE device_id = ?', (device_id,))
                conn.commit()
                conn.close()
                return True
            else:
                print(f"❌ API registration failed: {error_data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ API registration failed with status {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during device registration: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during device registration: {e}")
        return False


def ensure_device_registered():
    """
    Check if device is registered with API, if not, try to register it
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT device_id, is_registered FROM device WHERE id = 1')
    row = c.fetchone()
    conn.close()
    if row:
        device_id, is_registered = row
        if not is_registered:
            print(f"Device {device_id} not registered with API, attempting registration...")
            return register_device_with_api(device_id)
        else:
            print(f"Device {device_id} already registered with API")
            return True
    return False


def get_device_id():
    """
    Get the device ID from local database
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT device_id FROM device WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_saved_language():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT language FROM device WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def save_language(lang):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    print("saving into database the language: ", lang)
    # Update language without changing device_id
    c.execute('UPDATE device SET language = ? WHERE id = 1', (lang,))
    conn.commit()
    conn.close()


def get_contact_by_name(name):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    normalized_name = name.strip().lower()
    cursor.execute('''
        SELECT id, name, number FROM contacts
        WHERE LOWER(name) = ?
    ''', (normalized_name,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"id": result[0], "name": result[1], "number": result[2]}
    else:
        return None


def save_contact_to_db(name, number):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO contacts (name, number) VALUES (?, ?)
    ''', (name, number))
    conn.commit()
    conn.close()


def save_transaction(name, number, amount):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM contacts WHERE number = ?', (number,))
    contact_row = cursor.fetchone()
    if not contact_row:
        cursor.execute('INSERT INTO contacts (name, number) VALUES (?, ?)', (name, number))
        contact_id = cursor.lastrowid
    else:
        contact_id = contact_row[0]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO transactions (contact_id, amount, timestamp)
        VALUES (?, ?, ?)
    ''', (contact_id, amount, timestamp))

    conn.commit()
    conn.close()