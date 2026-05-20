from datetime import datetime, timedelta
import pandas as pd
import json
from pydantic import BaseModel, Field
from typing import Literal
import base64

from tools import get_weather_forecast, ask_openrouter_native


########################################
# AGENT 1: Training Proposer
########################################

def propose_training(conversation_context, history_df):
    history_df['date'] = pd.to_datetime(history_df['date'])
    cutoff_date = datetime.now() - timedelta(days=14)
    recent_history = history_df[history_df['date'] >= cutoff_date]

    if recent_history.empty:
        return "Brak danych z ostatnich 7 dni. Dodaj więcej treningów, aby otrzymać analizę."
        
    history_text = recent_history.to_string(index=False)

    today = datetime.now().strftime('%Y-%m-%d')
    weather = get_weather_forecast(today)
    weather_prompt = f"Warunki pogodowe na najbliższe dni:\n{weather}.\nNie jeżdżę na rowerze na zewnątrz w deszczu i mrozie. Przy ładnej pogodzie nie proponuję treningów na rowerze stacjonarnym, wolę jeździć na zewnątrz."
    competition_prompt = "Mój cel: SuperSprint Grudziądz 14.06 i 1/2 IM Malbork 06.09."
    context_info = "Sprzęt: Nie mam trenażera rowerowego, ale mam dostęp do siłowni i basenu. "

    system_prompt = f"""Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów. Dziś jest {today}. 
Oto moje treningi z ostatnich 14 dni:
{history_text}

Oto dodatkowy kontekst:
{weather_prompt}
{competition_prompt}
{context_info}

Odpowiedz na moją prośbę o plan treningowy, stosując się do poniższych zasad:

1. LISTA TRENINGÓW: Jezeli pytam o jeden trening, zaproponuj tylko ten jeden trening, nie cały plan. Każdy trening z planu zapisz w jednej linii od myślnika (jeden myślnik = jeden trening). W tej linii zmieść dzień, dyscyplinę, całkowity czas i główne zadanie (np. "- Sobota: Rower, 2h, spokojnie w Z2 z akcentami na podjazdach"). Weź pod uwagę zmęczenie z ostatnich 2 dni.
2. PODSUMOWANIE: Pod listą treningów dodaj DOKŁADNIE 2-3 zdania podsumowania mojej formy i wskazówek na najbliższe dni.
3. FORMAT: Zwróć JEDYNIE plan i podsumowanie. Nie zwracaj uwagi na RPE. Nie korzystaj z markdowna. Akapity oddzielaj pusta linia. Listy wypisuj od myślnika. Dodaj nagłówek z zakresem dat, który obejmuje plan (np. "Plan treningowy na okres 10.06-16.06" lub "Plan na dziś").
4. TON: Bądź konkretny, motywujący, ale surowy jeśli obijam się na treningach.
"""
    
    messages = [{"role": "system", "content": system_prompt}] + conversation_context
    
    response = ask_openrouter_native(messages, temperature=1.5)
    return response

########################################
# AGENT 2: History Analyzer
########################################

def analyze_history(conversation_context, history_df):
    history_text = history_df.to_string(index=False)
    today = datetime.now().strftime('%Y-%m-%d')
    
    system_prompt = f"""Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów SuperSprint Grudziądz 14.06 i 1/2 IM Malbork 06.09. Dziś jest {today}. 
Oto moje ostatnie treningi:
{history_text}

Odpowiedz na moje pytanie na podstawie powyższych danych.

WAŻNE ZASADY:
1. ANALIZA TRENINGÓW: Jeśli z zapytania wynika, że chodzi o jeden konkretny trening, znajdź go w historii i skup się tylko na nim. Jezeli pytam o jedną dyscyplinę, skup się tylko na treningach z tej dyscypliny. Jezeli pytam o konkretny okres czasu, skup się tylko na treningach z tego okresu. Wypisz statystyki z podziałem na dyscypliny (czas, dystans)
2. PODSUMOWANIE: Po analizie dodaj krótkie podsumowanie (2-3 zdania) dotyczące mojej formy, postępów i wskazówek na przyszłość.
3. FORMAT: Zwróć JEDYNIE plan i podsumowanie. Nie zwracaj uwagi na RPE. Nie korzystaj z markdowna. Akapity oddzielaj pusta linia. Listy wypisuj od myślnika. Dodaj nagłówek z zakresem dat, który obejmuje analiza (np. "Analiza treningów z okresu 01.06-07.06"). 
4. TON: Bądź konkretny, motywujący, ale surowy jeśli obijam się na treningach.
"""

    messages = [{"role": "system", "content": system_prompt}] + conversation_context
    
    response = ask_openrouter_native(messages, temperature=1.0)
    return response

########################################
# AGENT 3: Add Workout Agent
########################################
class AddWorkoutScema(BaseModel):
    date: str = Field(description="Data treningu w formacie RRRR-MM-DD")
    discipline: Literal["Pływanie", "Rower", "Bieg", "Siłownia", "Inne"]
    duration_minutes: int = Field(description="Czas trwania treningu w minutach")
    distance_km: float = Field(description="Dystans treningu w kilometrach (jeśli dotyczy, np. dla biegu i roweru)")
    rpe: int = Field(description="Poziom odczuwalnego wysiłku (RPE) w skali 1-10")
    avg_heart_rate: int = Field(description="Średnie tętno podczas treningu (jeśli dotyczy)", default=0)
    notes: str = Field(description="Dodatkowe notatki dotyczące treningu (jezeli podane przez uzytkownika, np. partie mięśni na siłowni czy typ roweru)", default="")


def parse_workout_data(query, previous_data=None):
    today_ref = datetime.now().strftime('%Y-%m-%d')
    
    if previous_data:
        prompt = f"""Dzisiaj jest {today_ref}. 
        Oto dane treningu: {json.dumps(previous_data, ensure_ascii=False)}
        Użytkownik prosi o poprawki: "{query}"
        Zaktualizuj dane (w tym datę, jeśli użytkownik o niej wspomina)."""
    else:
        prompt = f"""Jesteś profesjonalnym trenerem. Dzisiaj jest {today_ref}.
        Użytkownik podał dane treningu: "{query}"
        
        WAŻNE: Jeśli użytkownik używa określeń typu 'dzisiaj', 'wczoraj', 'przedwczoraj' lub 'w poniedziałek', 
        oblicz właściwą datę na podstawie dzisiejszego dnia ({today_ref}) i wpisz ją w formacie RRRR-MM-DD.
        Jeśli nie podał daty, przyjmij datę dzisiejszą."""

    messages = [{"role": "user", "content": prompt}]
    workout = ask_openrouter_native(messages, temperature=0.1, response_schema=AddWorkoutScema)

    return {
        "date": workout.date,
        "discipline": workout.discipline,
        "duration_minutes": workout.duration_minutes,
        "distance_km": workout.distance_km,
        "rpe": workout.rpe,
        "avg_heart_rate": workout.avg_heart_rate,
        "notes": workout.notes
    }


########################################
# AGENT 4: Delete Workout Agent
########################################


class DeleteMatchSchema(BaseModel):
    matched_id: int = Field(description="ID znalezionego treningu, lub -1 jeśli nie znaleziono dopasowania w bazie.")

def delete_workout_bot(message, history_df):
    recent_workouts = history_df
            
    if recent_workouts.empty:
        return -1
    else:
        workouts_list = recent_workouts.to_dict(orient='records')
        today_str = datetime.now().strftime('%Y-%m-%d (%A)')
                
        match_prompt = f"""
Dzisiaj jest {today_str}. Użytkownik napisał polecenie usunięcia: "{message}"
Oto Twoja baza 10 ostatnich treningów w formacie JSON:
{json.dumps(workouts_list, ensure_ascii=False, default=str)}
                
Znajdź ID treningu, o który chodzi użytkownikowi. 
- Jeśli wprost mówi np. "wczorajszy rower", oblicz datę i znajdź go.
- Jeśli po prostu mówi "usuń ostatni trening", wybierz pierwszy z góry.
- Jeśli żaden trening nie pasuje do opisu, zwróć -1.
"""

        messages = [{"role": "user", "content": match_prompt}]
        match_data = ask_openrouter_native(messages, temperature=0.1, response_schema=DeleteMatchSchema)
        
        found_id = match_data.matched_id
        
    return found_id

########################################
# AGENT 5: Parse Workout from Image 
########################################


def parse_workout_from_image(image_bytes):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    today_ref = datetime.now().strftime('%Y-%m-%d (%A)')
    
    prompt = f"""
    Jesteś profesjonalnym trenerem triathlonu. Dzisiaj jest {today_ref}.
    Przeanalizuj ten zrzut ekranu z aplikacji treningowej (np. Strava, Garmin Connect).
    Odczytaj z niego podstawowe dane: dyscyplinę, czas trwania (przelicz na minuty), dystans (w km), średnie tętno (jeśli widoczne).
    
    Jeśli na zdjęciu widać datę (np. "Wczoraj", "Dzisiaj" lub konkretny dzień), przelicz ją na format RRRR-MM-DD w odniesieniu do dzisiaj. Jeśli nie ma daty, przyjmij dzisiejszą.
    Jeśli tytuł lub opis na zdjęciu sugeruje zmęczenie, oszacuj RPE (1-10). Jeśli brakuje poszlak, RPE to domyślnie 5.
    
    Zwróć wynik jako JSON pasujący do schematu.
    """

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}" 
                    }
                }
            ]
        }
    ]

    workout = ask_openrouter_native(
        messages=messages, 
        temperature=0.1, 
        response_schema=AddWorkoutScema,
        model_name="google/gemini-3.1-flash-lite" 
    )

    return {
        "date": workout.date,
        "discipline": workout.discipline,
        "duration_minutes": workout.duration_minutes,
        "distance_km": workout.distance_km,
        "rpe": workout.rpe,
        "avg_heart_rate": workout.avg_heart_rate,
        "notes": workout.notes
    }