import sqlite3
import random

from core.database.database import register_device_with_api

def setup_db():
    conn = sqlite3.connect("database.db")
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

setup_db()