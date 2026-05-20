import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import pandas as pd

from database import get_workouts
from agents import analyze_history, propose_training

load_dotenv()

# Kolory
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_section(title: str):
    """Drukuje nagłówek sekcji"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print(f"{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}{Colors.ENDC}\n")


def print_test_case(number: int, title: str):
    """Drukuje nagłówek przypadku testowego"""
    print(f"{Colors.BOLD}{Colors.OKBLUE}[TEST {number}] {title}{Colors.ENDC}\n")


def print_user_query(query: str):
    """Drukuje zapytanie użytkownika"""
    print(f"{Colors.OKGREEN}[UŻYTKOWNIK]{Colors.ENDC}: {query}\n")


def print_agent_response(response: str):
    """Drukuje odpowiedź agenta"""
    print(f"{Colors.OKBLUE}[TRENER]{Colors.ENDC}:\n{response}\n")


def run_test_case(number: int, title: str, query: str, agent_func, *args):
    """Uruchamia pojedynczy przypadek testowy"""
    print_test_case(number, title)
    print_user_query(query)
    
    try:
        # Przygotuj wiadomości dla agenta
        messages = [
            {"role": "system", "content": "Jesteś profesjonalnym trenerem triathlonu."},
            {"role": "user", "content": query}
        ]
        
        # Uruchom agenta
        response = agent_func(messages, *args)
        
        print_agent_response(response)
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}Test nie powiódł się: {str(e)}{Colors.ENDC}\n")
        return False


def main():
    print_section("TRIATHLON COACH - ZAUTOMATYZOWANY TEST AGENTA")
    
    # Załaduj dane
    print(f"{Colors.BOLD}Ładowanie danych treningowych...{Colors.ENDC}")
    history = get_workouts(limit=14)
    
    if history.empty:
        print(f"{Colors.WARNING}Brak danych treningowych w bazie! Dodaj kilka treningów, aby uruchomić testy.{Colors.ENDC}\n")
        return
    
    print(f"{Colors.OKGREEN}Załadowano {len(history)} treningów z ostatnich 14 dni{Colors.ENDC}\n")
    
    # Wyświetl statystyki
    print_section("STATYSTYKI DANYCH TESTOWYCH")
    print(f"Liczba treningów: {len(history)}")
    print(f"Dyscypliny: {history['discipline'].unique().tolist()}")
    print(f"Całkowity dystans: {history['distance_km'].sum():.2f} km")
    print(f"Całkowity czas: {history['duration_minutes'].sum():.0f} minut")
    
    # Uruchom testy
    print_section("SCENARIUSZE TESTOWE")
    
    results = []
    
    results.append(run_test_case(
        1,
        "Analiza Historii - Podsumowanie",
        "Podsumuj ostatni tydzień.",
        analyze_history,
        history
    ))


    results.append(run_test_case(
        2,
        "Analiza Historii - Konkretna Dyscyplina",
        "Podsumuj moje ostatnie treningi rowerowe.",
        analyze_history,
        history
    ))
    

    results.append(run_test_case(
        3,
        "Plan Treningowy - Ogólny",
        "Zaplanuj treningi na najbliższy tydzień",
        propose_training,
        history
    ))
    
    
    results.append(run_test_case(
        4,
        "Plan Treningowy - Konkretna Dyscyplina",
        "Zaproponuj mi trening pływacki na dziś",
        propose_training,
        history
    ))
    
<<<<<<< HEAD
=======
    results.append(run_test_case(
        5,
        "Analiza Historii - Forma Fizyczna",
        "W jakiej jestem formie? Czy jestem dobrze przygotowany?",
        analyze_history,
        history
    ))


>>>>>>> 82e8a00364dde03cb0cdbcc693c86b938e36fb4c

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.BOLD}{Colors.WARNING}Przerwano przez użytkownika.{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n{Colors.FAIL}Błąd: {str(e)}{Colors.ENDC}\n")
