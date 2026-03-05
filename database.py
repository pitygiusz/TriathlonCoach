import sqlite3
import pandas as pd

# --- BAZA DANYCH (SQLite) ---

def init_db():
    ''' 
    Inicjalizacja bazy danych i tworzenie tabeli, jeśli nie istnieje 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            discipline TEXT,
            duration_minutes INTEGER,
            distance_km REAL,
            rpe INTEGER,
            notes TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS coach_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              date TEXT,
              advice TEXT
        )
    ''')

    conn.commit()
    conn.close()

def add_workout(date, discipline, duration, distance, rpe, notes):
    ''' 
    Dodawanie nowego treningu do bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()
    c.execute('INSERT INTO workouts (date, discipline, duration_minutes, distance_km, rpe, notes) VALUES (?, ?, ?, ?, ?, ?)',
              (date, discipline, duration, distance, rpe, notes))
    conn.commit()
    conn.close()

def get_workouts(limit=10):
    '''
    Pobieranie ostatnich treningów z bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    df = pd.read_sql_query(f"SELECT * FROM workouts ORDER BY date DESC LIMIT {limit}", conn)
    conn.close()
    return df

def get_all_workouts():
    '''
    Pobieranie wszystkich treningów z bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    df = pd.read_sql_query("SELECT * FROM workouts ORDER BY date DESC", conn)
    conn.close()
    return df


def delete_workout(workout_id):
    '''
    Usuwanie treningu z bazy danych na podstawie ID 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()
    c.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    conn.commit()
    conn.close()

def save_coach_log(advice):
    '''
    Zapisywanie porady trenera do bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()

    date = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
    c.execute('INSERT INTO coach_logs (date, advice) VALUES (?, ?)', (date, advice))
    conn.commit()
    conn.close()

def get_coach_logs(limit=10):
    '''
    Pobieranie ostatnich logów trenera z bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    df = pd.read_sql_query(f"SELECT * FROM coach_logs ORDER BY date DESC LIMIT {limit}", conn)
    conn.close()
    return df


def get_latest_coach_log():
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()
    # Pobieramy najnowszy wpis
    c.execute("SELECT advice, date FROM coach_logs ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1]
    return None, None

