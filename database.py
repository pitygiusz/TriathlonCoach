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
            avg_heart_rate INTEGER,
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
    
    # Migracja: dodanie kolumny avg_heart_rate jeśli jej brakuje
    c.execute("PRAGMA table_info(workouts)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'avg_heart_rate' not in columns:
        c.execute('ALTER TABLE workouts ADD COLUMN avg_heart_rate INTEGER DEFAULT NULL')
        conn.commit()
    
    conn.close()

def add_workout(date, discipline, duration, distance, rpe, avg_heart_rate, notes):
    ''' 
    Dodawanie nowego treningu do bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()
    c.execute('INSERT INTO workouts (date, discipline, duration_minutes, distance_km, rpe, avg_heart_rate, notes) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (date, discipline, duration, distance, rpe, avg_heart_rate, notes))
    conn.commit()
    conn.close()

def get_workouts(limit=None):
    '''
    Pobieranie ostatnich treningów z bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    if limit is not None:
        df = pd.read_sql_query(f"SELECT * FROM workouts ORDER BY date DESC LIMIT {limit}", conn)
    else:
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

def get_coach_logs(limit=None):
    '''
    Pobieranie ostatnich logów trenera z bazy danych 
    '''
    conn = sqlite3.connect('triathlon_logs.db')
    if limit is not None:
        df = pd.read_sql_query(f"SELECT * FROM coach_logs ORDER BY date DESC LIMIT {limit}", conn)
        conn.close()
        return df
    else:
        c = conn.cursor()
        c.execute("SELECT advice, date FROM coach_logs ORDER BY id DESC LIMIT 1")
        result = c.fetchone()
        conn.close()
        return result[0], result[1]

def update_workout(workout_id, date, discipline, duration, distance, rpe, avg_heart_rate, notes):
    ''' Aktualizuje istniejący trening w bazie '''
    conn = sqlite3.connect('triathlon_logs.db')
    c = conn.cursor()
    c.execute('''
        UPDATE workouts 
        SET date=?, discipline=?, duration_minutes=?, distance_km=?, rpe=?, avg_heart_rate=?, notes=?
        WHERE id=?
    ''', (date, discipline, duration, distance, rpe, avg_heart_rate, notes, workout_id))
    conn.commit()
    conn.close()


