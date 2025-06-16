import sqlite3
from config.settings import DATABASE
from datetime import datetime


def setup_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                number TEXT NOT NULL
            )
        ''')
    c.execute('''CREATE TABLE IF NOT EXISTS preferences (
                   id INTEGER PRIMARY KEY,
                   language TEXT NOT NULL
               )''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                number TEXT NOT NULL,
                amount TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
    conn.commit()
    conn.close()


def get_saved_language():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT language FROM preferences WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def save_language(lang):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    print("saving into database the langugage: ", lang)
    c.execute('DELETE FROM preferences')
    c.execute('INSERT INTO preferences (id, language) VALUES (1, ?)', (lang,))
    conn.commit()
    conn.close()


def get_contact_by_name(name):
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, number FROM contacts
        WHERE LOWER(name) = LOWER(?)
    ''', (name,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"name": result[0], "number": result[1]}
    else:
        return None


def save_contact_to_db(name, number):
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            number TEXT NOT NULL
        )
    ''')
    cursor.execute('INSERT INTO contacts (name, number) VALUES (?, ?)', (name, number))
    conn.commit()
    conn.close()


def save_transaction(name, number, amount):
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO transactions (name, number, amount, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (name, number, amount, timestamp))

    conn.commit()
    conn.close()
