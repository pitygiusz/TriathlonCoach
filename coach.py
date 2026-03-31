from google import genai
from datetime import datetime, timedelta
import pandas as pd

from tools import get_weather_forecast, long_term_stats

# --- LOGIKA GEMINI ---

def ask_gemini(prompt, temperature=1.0):
    client = genai.Client() 

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config =genai.types.GenerateContentConfig(
            temperature=temperature)
    )

    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count
    output_tokens = usage.candidates_token_count

    cost = (input_tokens * 0.5 / 1000000) + (output_tokens * 3 / 1000000)
    return response.text, cost

def ask_coach(history_df, include_competition, include_weather, easier_week, include_long_term):
 
    history_df['date'] = pd.to_datetime(history_df['date'])
    cutoff_date = datetime.now() - timedelta(days=7)
    recent_history = history_df[history_df['date'] >= cutoff_date]

    if recent_history.empty:
        return "Brak danych z ostatnich 7 dni. Dodaj więcej treningów, aby otrzymać analizę.", 0, ""

    today = datetime.now().strftime('%Y-%m-%d')
    long_term_prompt = ""
    weather_prompt = ""
    competition_prompt = ""
    easier_week_prompt = ""

    if include_long_term:
        long_term = long_term_stats()
        long_term_prompt = f"Weź pod uwagę moje długoterminowe statystyki treningowe:\n{long_term}"

    if include_weather:
        weather = get_weather_forecast(today)
        weather_prompt = f"Weź pod uwagę warunki pogodowe na najbliszy tydzień:\n{weather}.\nNie chcę jeździć w deszczu i mrozie."

    if include_competition:
        competition_prompt = "Uwzględnij w analizie, że moim celem są zawody SuperSprint Grudziądz 14.06 i 1/2 IM Malbork 06.09."
    
    if easier_week:
        easier_week_prompt = "Zaproponuj łatwiejszy tydzień, bo mam mniej czasu."


    history_text = recent_history.to_string(index=False)
    
    prompt = f"""
Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów. Oto moje treningi z ostatnich 7 dni:
    
{history_text}

Oto dodatkowy kontekst:
{long_term_prompt}
{weather_prompt}
{competition_prompt}

Ogólne uwagi:
- chce mieć minimum 1 dzień przerwy w tygodniu,
- nie mam trenażera rowerowego, mam dostęp do siłowni i basenu.
{easier_week_prompt}

Na podstawie tych danych odpowiedz na poniższe pytania:

1. Podsumuj krótko ostatni tydzień treningów, wypisz statystyki, oceń ogólną intensywność, weź pod uwagę średnie tętno.
2. Zaproponuj plan na kolejne 7 dni w formie tabelki.
Bądź konkretny, motywujący, ale surowy jeśli trzeba. 
"""

    response, cost = ask_gemini(prompt, temperature=0.5)

    return response, cost, prompt

def summary_all(history_df):
    client = genai.Client()  
    history_text = history_df.to_string(index=False)
    
    prompt = f"""
Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów. Oto moja historia treningów:
    
{history_text}
    
Napisz wnioski z przygotowań w 3 krótkich bulletpointach. Zwróć JEDYNIE te bulletpointy.
"""
    
    response, cost = ask_gemini(prompt)

    return response, cost


def kitchen_help():
    kitchen_prompt = f"""
Jesteś dietetykiem sportowym dla triathlonistów.
Zadanie: Wymyśl prosty, szybki i pożywny posiłek, który mógłbym zjeść jako główny posiłek dnia. Najbardziej lubię dania mięsne (kurczak, indyk, wołowina)

W odpowiedzi uwzględnij JEDYNIE następujące elementy:
- nazwę dania
- bardzo krótkie uzasadnienie, dlaczego jest dobre dla triathlonisty (np. zawiera odpowiednią ilość białka, węglowodanów, jest łatwostrawne itp.)
- listę zakupów (tylko kluczowe składniki)
- główne kroki przygotowania (maks 5, bardzo proste, bez skomplikowanych technik kulinarnych).
"""
    response, cost = ask_gemini(kitchen_prompt, temperature=2.0)
    return response, cost

def gym_plan():
    gym_prompt = f"""
Jesteś trenerem personalnym dla triathlonistów.
Zadanie: Zaproponuj plan na pojedynczy trening na siłowni, dostosowany do potrzeb triathlonisty. 
Trening powinien być krótki (maks 45 minut), ale efektywny, skupiający się na budowaniu siły i wytrzymałości, bez nadmiernego obciążania stawów. Skorzystaj z maszyn na siłowni.

W odpowiedzi uwzględnij JEDYNIE następujące elementy:
- nazwę treningu
- bardzo krótkie uzasadnienie, dlaczego ten trening jest dobry dla triathlonisty (np. skupia się na kluczowych grupach mięśniowych, poprawia stabilizację itp.)
- listę ćwiczeń (maks 5), z krótkim opisem każdego ćwiczenia (np. "Przysiady z hantlami - 3 serie po 12 powtórzeń, skup się na technice i kontroli ruchu")
- ogólne wskazówki dotyczące tempa, przerw między seriami itp.
"""
    
    response, cost = ask_gemini(gym_prompt, temperature=2.0)
    return response, cost