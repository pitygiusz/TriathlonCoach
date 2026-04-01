from datetime import datetime, timedelta
import pandas as pd
import json

from pydantic import BaseModel, Field
from typing import Literal

from tools import get_weather_forecast, ask_gemini
from coach import ask_gemini


########################################
# AGENT 1: One Training Proposer
########################################

def propose_one_training(message, history_df, include_weather):
    history_df['date'] = pd.to_datetime(history_df['date'])
    cutoff_date = datetime.now() - timedelta(days=7)
    recent_history = history_df[history_df['date'] >= cutoff_date]

    if recent_history.empty:
        return "Brak danych z ostatnich 7 dni. Dodaj więcej treningów, aby otrzymać analizę.", 0

    today = datetime.now().strftime('%Y-%m-%d')
    weather_prompt = ""

    if include_weather:
        weather = get_weather_forecast(today)
        weather_prompt = f"Weź pod uwagę warunki pogodowe na najbliszy tydzień:\n{weather}.\nNie chcę jeździć w deszczu i mrozie."

    history_text = recent_history.to_string(index=False)
    
    prompt = f"""Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów. Oto moje treningi z ostatnich 7 dni:
    {history_text}
    {weather_prompt}
Na podstawie tych danych zaproponuj JEDEN trening, który będzie najbardziej efektywny i dopasowany do mojej aktualnej formy i warunków. Uwzględnij prośbę {message}.

Zwróć JEDYNIE plan tego treningu (dyscyplina, czas trwania, dystans, intensywność) w zwięzłej formie.
Bądź konkretny, motywujący, ale surowy jeśli trzeba.
"""
    response, _ = ask_gemini(prompt, temperature=2.0)
    return response

########################################
# AGENT 2: History Analyzer
########################################

def analyze_history(question, history_df):
    history_text = history_df.to_string(index=False)
    today = datetime.now().strftime('%Y-%m-%d')
    prompt = f"""Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do
zawodów SuperSprint Grudziądz 14.06 i 1/2 IM Malbork 06.09. Dziś jest {today}. Oto moje ostatnie treningi:
{history_text}
Na ich podstawie odpowiedz na moje pytanie: {question}
Jeeli pytam o podsumowanie to wypisz statystyki, oceń fomę oraz podaj wskazówki.
Zwróć maksymalnie 5 zdań plus statystyki, jeśli o nie proszę.
Nie dodawaj zbędnych wstępów i komentarzy. Bądź konkretny, motywujący, ale surowy jeśli trzeba.
"""
    response, _ = ask_gemini(prompt, temperature=2.0)
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
    # Pobieramy dzisiejszą datę, żeby Gemini miało punkt odniesienia
    today_ref = datetime.now().strftime('%Y-%m-%d (dzisiaj to %A)')
    
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

    response_text, _ = ask_gemini(prompt, temperature=0.1, response_schema=AddWorkoutScema)
    workout = AddWorkoutScema.model_validate_json(response_text)

    return {
        "date": workout.date, # Dodajemy datę do zwracanego słownika
        "discipline": workout.discipline,
        "duration_minutes": workout.duration_minutes,
        "distance_km": workout.distance_km,
        "rpe": workout.rpe,
        "avg_heart_rate": workout.avg_heart_rate,
        "notes": workout.notes
    }




########################################
# AGENT 4: Weekly Plan Proposer
########################################

def propose_weekly_plan(message, history_df):
    history_df['date'] = pd.to_datetime(history_df['date'])
    cutoff_date = datetime.now() - timedelta(days=7)
    recent_history = history_df[history_df['date'] >= cutoff_date]

    if recent_history.empty:
        return "Brak danych z ostatnich 7 dni. Dodaj więcej treningów, aby otrzymać analizę."

    today = datetime.now().strftime('%Y-%m-%d')
    weather = get_weather_forecast(today)

    weather_prompt = f"Weź pod uwagę warunki pogodowe na najbliszy tydzień:\n{weather}.\nNie chcę jeździć w deszczu i mrozie."
    competition_prompt = "Uwzględnij w analizie, że moim celem są zawody SuperSprint Grudziądz 14.06 i 1/2 IM Malbork 06.09."
    history_text = recent_history.to_string(index=False)
    
    prompt = f"""Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów. Oto moje treningi z ostatnich 7 dni:
    {history_text}

Oto dodatkowy kontekst:
{weather_prompt}
{competition_prompt}

Na podstawie tych danych zaproponuj plan treningowy na najbliższy tydzień, który będzie najbardziej efektywny i dopasowany do mojej aktualnej formy i warunków. Uwzględnij prośbę {message}.

Zwróć JEDYNIE ten plan w zwięzłej formie. Bądź konkretny, motywujący, ale surowy jeśli trzeba.
"""
    response, _ = ask_gemini(prompt, temperature=0.5)
    return response



########################################
# AGENT 5: Delete Workout Agent
########################################


class DeleteMatchSchema(BaseModel):
    matched_id: int = Field(description="ID znalezionego treningu, lub -1 jeśli nie znaleziono dopasowania w bazie.")




def delete_workout_bot(message, history_df):
    recent_workouts = history_df
            
    if recent_workouts.empty:
        return -1
    else:
        # 2. Zamieniamy ramkę Pandasa na słownik, żeby dać to Gemini
        workouts_list = recent_workouts.to_dict(orient='records')
        today_str = datetime.now().strftime('%Y-%m-%d (%A)')
                
                # 3. Prompt detektywistyczny dla Gemini
        match_prompt = f"""
Dzisiaj jest {today_str}. Użytkownik napisał polecenie usunięcia: "{message}"
Oto Twoja baza 10 ostatnich treningów w formacie JSON:
{json.dumps(workouts_list, ensure_ascii=False, default=str)}
                
Znajdź ID treningu, o który chodzi użytkownikowi. 
- Jeśli wprost mówi np. "wczorajszy rower", oblicz datę i znajdź go.
- Jeśli po prostu mówi "usuń ostatni trening", wybierz pierwszy z góry.
- Jeśli żaden trening nie pasuje do opisu, zwróć -1.
"""
                
                # 4. Odpytujemy Gemini, wymuszając zwrócenie ID
        match_response, _ = ask_gemini(match_prompt, temperature=0.1, response_schema=DeleteMatchSchema)
        match_data = DeleteMatchSchema.model_validate_json(match_response)
                
        found_id = match_data.matched_id
    return found_id


########################################
# AGENT 6: Parse Workout from Image
########################################

import io
from PIL import Image
# Upewnij się, że masz tu import ask_gemini i AddWorkoutScema

def parse_workout_from_image(image_bytes):
    # Zamieniamy surowe bajty z Telegrama na obiekt obrazu dla Gemini
    img = Image.open(io.BytesIO(image_bytes))
    
    today_ref = datetime.now().strftime('%Y-%m-%d (%A)')
    
    prompt = f"""
    Jesteś profesjonalnym trenerem triathlonu. Dzisiaj jest {today_ref}.
    Przeanalizuj ten zrzut ekranu z aplikacji treningowej (np. Strava, Garmin Connect).
    Odczytaj z niego podstawowe dane: dyscyplinę, czas trwania (przelicz na minuty), dystans (w km), średnie tętno (jeśli widoczne).
    
    Jeśli na zdjęciu widać datę (np. "Wczoraj", "Dzisiaj" lub konkretny dzień), przelicz ją na format RRRR-MM-DD w odniesieniu do dzisiaj. Jeśli nie ma daty, przyjmij dzisiejszą.
    Jeśli tytuł lub opis na zdjęciu sugeruje zmęczenie, oszacuj RPE (1-10). Jeśli brakuje poszlak, RPE to domyślnie 5.
    
    Zwróć wynik jako JSON pasujący do schematu.
    """

    # Wywołujemy Gemini z obrazem
    response_text, _ = ask_gemini(prompt, temperature=0.1, response_schema=AddWorkoutScema, image=img)
    workout = AddWorkoutScema.model_validate_json(response_text)

    return {
        "date": workout.date,
        "discipline": workout.discipline,
        "duration_minutes": workout.duration_minutes,
        "distance_km": workout.distance_km,
        "rpe": workout.rpe,
        "avg_heart_rate": workout.avg_heart_rate,
        "notes": workout.notes
    }