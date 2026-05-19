from datetime import datetime, timedelta
import pandas as pd

from tools import get_weather_forecast, long_term_stats, ask_openrouter_native


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

    messages = [{"role": "user", "content": prompt}]
    response = ask_openrouter_native(messages, temperature=0.5)

    return response, 0, prompt




def summary_all(history_df):
    history_text = history_df.to_string(index=False)
    
    prompt = f"""
Jesteś profesjonalnym trenerem triathlonu. Przygotowujesz mnie do zawodów. Oto moja historia treningów:
    
{history_text}
    
Napisz wnioski z przygotowań w 3 krótkich bulletpointach. Zwróć JEDYNIE te bulletpointy.
"""
    
    messages = [{"role": "user", "content": prompt}]
    response = ask_openrouter_native(messages)

    return response, 0