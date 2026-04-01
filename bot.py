import os
import telebot
import json
from datetime import timedelta, datetime
from dotenv import load_dotenv
import pandas as pd
from pydantic import BaseModel, Field
from typing import Literal

from database import get_workouts, get_coach_logs, save_coach_log, delete_workout, add_workout
from coach import ask_coach, ask_gemini
from agents import analyze_history, propose_one_training, propose_weekly_plan, parse_workout_data, delete_workout_bot, parse_workout_from_image
from tools import ask_gemini


# 1. Ładowanie konfiguracji
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_CHAT_ID = int(os.getenv("MY_CHAT_ID"))

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 2. Zabezpieczenie: Funkcja sprawdzająca, czy to Ty piszesz
def is_me(message):
    return message.chat.id == MY_CHAT_ID

# 3. Komenda /start
@bot.message_handler(commands=['start'], func=is_me)
def send_welcome(message):
    bot.reply_to(message, "Cześć Szefie!")

########################################
# Komendy 
########################################


# /zobacz_treningi - pokazuje historię treningów z ostatniego tygodnia

@bot.message_handler(commands=['zobacz_treningi'], func=is_me)
def send_workouts(message):
    try:
        workouts = get_workouts(limit=14)
        workouts['date'] = pd.to_datetime(workouts['date'])
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_history = workouts[workouts['date'] >= cutoff_date]
        recent_history['date'] = recent_history['date'].dt.strftime('%Y-%m-%d')

        
        if workouts.empty:
            bot.reply_to(message, "Brak zapisanych treningów.")
            return
        
        response = "Oto twoje treningi z ostatniego tygodnia:\n\n"

        for index, row in recent_history.iterrows():
            date_val = row['date']
            disc_val = row['discipline']
            dist_val = row['distance_km']
            dur_val = row['duration_minutes']
            rpe_val = row['rpe']
            
            hr_val = int(row['avg_heart_rate']) if pd.notna(row['avg_heart_rate']) else "-"
            
            response += f"{date_val} | {disc_val} | {dist_val}km ({dur_val} min) | RPE: {rpe_val} | HR: {hr_val}\n"

        bot.reply_to(message, response, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd w kodzie:\n`{str(e)}`", parse_mode="Markdown")


# /ostatnia_porada - pokazuje ostatnią poradę trenera

@bot.message_handler(commands=['ostatnia_porada'], func=is_me)
def send_latest_advice(message):
    try:
        latest_advice, advice_date = get_coach_logs()
        if latest_advice:
            response = f"**Ostatnia porada trenera (z {advice_date}):**\n\n{latest_advice}"
        else:
            response = "Brak zapisanych porad trenera."
        bot.reply_to(message, response, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd w kodzie:\n`{str(e)}`", parse_mode="Markdown")


# /nowa_porada - generuje nową poradę trenera na podstawie historii

@bot.message_handler(commands=['nowa_porada'], func=is_me)
def send_new_advice(message):
    try:
        history = get_workouts(limit=14)

        advice, _, _ = ask_coach(history, True, True, False, True)
        save_coach_log(advice)
        response = f"**Nowa porada trenera:**\n\n{advice}"
        bot.reply_to(message, response, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd w kodzie:\n`{str(e)}`", parse_mode="Markdown")


# /trening - generuje pomysł na trening na dziś

@bot.message_handler(commands=['trening'], func=is_me)
def send_one_training(message):
    try:
        history = get_workouts(limit=14)
        user_input = ""
        advice = propose_one_training(user_input, history, True)
        response = f"**Trening na dziś:**\n\n{advice}"
        bot.reply_to(message, response, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd w kodzie:\n`{str(e)}`", parse_mode="Markdown")


###
@bot.message_handler(content_types=['photo'], func=is_me)
def handle_photo_workout(message):
    try:
        bot.send_message(message.chat.id, "Analizuję zrzut ekranu... 📸", parse_mode="Markdown")
        
        # 1. Telegram wysyła zdjęcie w kilku rozdzielczościach. Ostatnie [-1] jest największe.
        file_info = bot.get_file(message.photo[-1].file_id)
        
        # 2. Pobieramy plik z serwerów Telegrama do pamięci bota
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 3. Wysyłamy obraz do naszego nowego Agenta Vision
        parsed_data = parse_workout_from_image(downloaded_file)
        
        # 4. Magia integracji: Używamy tego samego podglądu co przy dodawaniu z tekstu!
        preview = f"Odczytałem następujące dane ze zdjęcia:\n\nData: {parsed_data['date']}\nDyscyplina: {parsed_data['discipline']}\nCzas: {parsed_data['duration_minutes']} min\nDystans: {parsed_data['distance_km']} km\nRPE: {parsed_data['rpe']}\nHR: {parsed_data['avg_heart_rate']}\nNotatki: {parsed_data['notes']}\n\n**Czy wszystko się zgadza?**\n(Napisz 'Tak' by zapisać, lub powiedz co poprawić)"
        
        msg = bot.reply_to(message, preview, parse_mode="Markdown")
        
        # 5. Przekazujemy pałeczkę do Twojej funkcji akceptującej!
        bot.register_next_step_handler(msg, process_add_confirmation, parsed_data)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Nie udało się odczytać zdjęcia:\n`{str(e)}`", parse_mode="Markdown")



########################################
# NLP
########################################

class RouterSchema(BaseModel):
    intent: Literal["HISTORIA", "DODAJ_TRENING", "WYMYŚL_TRENING", "TYGODNIOWY_PLAN", "USUN_TRENING", "INNE"]
    odpowiedz_trenera: str = Field(description="Jeśli intent to INNE, odpowiedz użytkownikowi. W przeciwnym razie zostaw puste.")

@bot.message_handler(func=lambda message: is_me(message) and message.text and not message.text.startswith('/'))
def handle_natural_language(message):
    user_text = message.text

    router_prompt = f"""
    Jesteś asystentem trenera. Użytkownik napisał: "{user_text}".
    Odgadnij intencję z wiadomości (HISTORIA, DODAJ_TRENING, WYMYŚL_TRENING, TYGODNIOWY_PLAN lub INNE).
    """
    
    try:
        bot.send_message(message.chat.id, "Analizuję Twoją wiadomość...", parse_mode="Markdown")
        
        json_response, _ = ask_gemini(router_prompt, response_schema=RouterSchema)
    
        ai_data = json.loads(json_response)
        intent = ai_data.get("intent")
        
        if intent == "HISTORIA":
            bot.send_message(message.chat.id, "Analizuję twoją historię treningową...", parse_mode="Markdown")
            history = get_workouts(limit=14)
            response = analyze_history(user_text, history) 
            response = response.replace('*', '')
            bot.reply_to(message, response)

        elif intent == "DODAJ_TRENING":
            bot.send_message(message.chat.id, "Analizuję Twoje dane...", parse_mode="Markdown")
            parsed_data = parse_workout_data(user_text)
            preview = f"Oto Twój trening:\n\nData: {parsed_data['date']}\nDyscyplina: {parsed_data['discipline']}\nCzas: {parsed_data['duration_minutes']} min\nDystans: {parsed_data['distance_km']} km\nRPE: {parsed_data['rpe']}\nHR: {parsed_data['avg_heart_rate']}\nNotatki: {parsed_data['notes']}\n\nCzy wszystko się zgadza?"
            msg = bot.reply_to(message, preview, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_add_confirmation, parsed_data)
            
        elif intent == "WYMYŚL_TRENING":
            bot.send_message(message.chat.id, "Przygotowuję plan na trening...", parse_mode="Markdown")
            history = get_workouts(limit=14)
            response = propose_one_training(user_text, history, True) 
            response = response.replace('*', '')
            bot.reply_to(message, response)

        elif intent == "TYGODNIOWY_PLAN":
            bot.send_message(message.chat.id, "Przygotowuję tygodniowy plan treningowy...", parse_mode="Markdown")
            history = get_workouts(limit=14)
            response = propose_weekly_plan(user_text, history) 
            response = response.replace('*', '')
            bot.reply_to(message, response)
            
        elif intent == "INNE":
            odpowiedz = ai_data.get("odpowiedz_trenera")
            bot.reply_to(message, odpowiedz, parse_mode="Markdown")

        elif intent == "USUN_TRENING":
            bot.send_message(message.chat.id, "Szukam treningu, o który Ci chodzi...")
            history = get_workouts(limit=14)
            found_id = delete_workout_bot(user_text, history)
                
            if found_id == -1:
                bot.reply_to(message, "Nie mogłem dopasować Twojego opisu do żadnego z ostatnich treningów. Spróbuj napisać dokładniej (np. 'usuń wczorajszy basen').")
            else:
                target_workout = history[history['id'] == found_id].iloc[0]
                    
                w_id = int(target_workout['id'])
                details = f"{target_workout['date']} | {target_workout['discipline']} | {target_workout['distance_km']}km | {target_workout['duration_minutes']}min"
                    
                msg = bot.reply_to(message, f"Znalazłem ten trening. Czy na pewno chcesz go usunąć?\n\n{details}\n\nOdpowiedz: Tak lub Nie.")
                bot.register_next_step_handler(msg, process_delete_confirmation, w_id)    

    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd w kodzie:\n`{str(e)}`", parse_mode="Markdown")



# Pamiętaj, żeby zaimportować parse_workout_from_image z agents.py na górze pliku!




########################################
# Helper functions for confirmations
########################################
def process_delete_confirmation(message, workout_id):
    user_answer = message.text.lower()
    confirm_prompt = f"Użytkownik odpowiedział: '{user_answer}' na pytanie o potwierdzenie usunięcia treningu. Czy to oznacza TAK czy NIE? Zwróć tylko jedno słowo: TAK lub NIE."
    
    try:
        decision, _ = ask_gemini(confirm_prompt, temperature=0.1)
        
        if "TAK" in decision.upper():
            delete_workout(workout_id)
            bot.reply_to(message, "Trening został trwale usunięty z bazy.")
        else:
            bot.reply_to(message, "Trening zostaje w bazie.")
            
    except Exception as e:
        bot.reply_to(message, f"Coś poszło nie tak: {str(e)}")


def process_add_confirmation(message, parsed_data):
    user_answer = message.text
    confirm_prompt = f"Użytkownik napisał: '{user_answer}'. Czy to oznacza bezwarunkową akceptację i zgodę (TAK), czy użytkownik podał jakiekolwiek dane lub chce je usunąć (ZMIANA)? Zwróć tylko jedno słowo: TAK lub ZMIANA."
    
    try:
        decision, _ = ask_gemini(confirm_prompt, temperature=0.1)
        
        if "TAK" in decision.upper():
            date_to_save = parsed_data['date']
            add_workout(
                date_to_save, 
                parsed_data['discipline'], 
                parsed_data['duration_minutes'], 
                parsed_data['distance_km'], 
                parsed_data['rpe'], 
                parsed_data['avg_heart_rate'], 
                parsed_data['notes']
            )
            response = f"""Dodałem trening:\n
Data: {date_to_save},
Dyscyplina: {parsed_data['discipline']},
Czas trwania: {parsed_data['duration_minutes']} min,
Dystans: {parsed_data['distance_km']} km,
RPE: {parsed_data['rpe']},
Średnie tętno: {parsed_data['avg_heart_rate']},
Notatki: {parsed_data['notes']}

Świetna robota!"""
            
            bot.reply_to(message, response)
            
        else:
            bot.send_message(message.chat.id, "Nanoszę poprawki...")
            new_parsed_data = parse_workout_data(user_answer, previous_data=parsed_data)
            preview = f"Poprawione! Nowe dane:\n\nData: {new_parsed_data['date']}\nDyscyplina: {new_parsed_data['discipline']}\nCzas: {new_parsed_data['duration_minutes']} min\nDystans: {new_parsed_data['distance_km']} km\nRPE: {new_parsed_data['rpe']}\nHR: {new_parsed_data['avg_heart_rate']}\nNotatki: {new_parsed_data['notes']}\n\n**Czy teraz wszystko się zgadza?"
            msg = bot.reply_to(message, preview, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_add_confirmation, new_parsed_data)
            
    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd podczas potwierdzania: {str(e)}")


# 4. Uruchomienie bota
bot.infinity_polling()