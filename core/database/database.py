import sqlite3
import random
from config.settings import DATABASE
from datetime import datetime


def setup_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Create tables with constraints and indexes
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            number TEXT NOT NULL UNIQUE
        )
    ''')

    # Create index on lowercase name for fast case-insensitive search
    c.execute('CREATE INDEX IF NOT EXISTS idx_contacts_name_lower ON contacts (LOWER(name))')

    c.execute('''
        CREATE TABLE IF NOT EXISTS device (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            language TEXT NOT NULL,
            device_id INTEGER UNIQUE NOT NULL
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

    # Insert device row if empty, generating unique device_id once
    c.execute('SELECT COUNT(*) FROM device')
    if c.fetchone()[0] == 0:
        device_id = random.randint(100000, 999999)  # 6-digit unique device id
        c.execute(
            'INSERT INTO device (id, language, device_id) VALUES (1, ?, ?)',
            ("en", device_id)
        )
        print(f"Generated device ID: {device_id}")

    conn.commit()
    conn.close()


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

    # Find contact_id by number first (guaranteed unique)
    cursor.execute('SELECT id FROM contacts WHERE number = ?', (number,))
    contact_row = cursor.fetchone()

    # If contact does not exist, insert it first
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
