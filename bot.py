import os
import telebot
import json
from dotenv import load_dotenv
import pandas as pd
from pydantic import BaseModel, Field
from typing import Literal

from database import get_workouts, get_coach_logs, save_coach_log, delete_workout, add_workout
from coach import ask_coach
from agents import analyze_history, propose_training, parse_workout_data, delete_workout_bot, parse_workout_from_image
from tools import ask_gemini


# 1. Ładowanie konfiguracji
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MY_CHAT_ID = int(os.getenv("MY_CHAT_ID"))

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 2. Zabezpieczenie, tylko znajomy użytkownik może korzystać z bota
def is_me(message):
    return message.chat.id == MY_CHAT_ID

# 3. Komenda /start
@bot.message_handler(commands=['start'], func=is_me)
def send_welcome(message):
    bot.reply_to(message, "Cześć Szefie!")

########################################
# COMMANDS 
########################################

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


########################################
# SCREENSHOT PARSING
########################################
@bot.message_handler(content_types=['photo'], func=is_me)
def handle_photo_workout(message):
    try:
        bot.send_message(message.chat.id, "Analizuję zrzut ekranu... 📸", parse_mode="Markdown")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        parsed_data = parse_workout_from_image(downloaded_file)
        
        preview = f"Odczytałem następujące dane ze zdjęcia:\n\nData: {parsed_data['date']}\nDyscyplina: {parsed_data['discipline']}\nCzas: {parsed_data['duration_minutes']} min\nDystans: {parsed_data['distance_km']} km\nRPE: {parsed_data['rpe']}\nHR: {parsed_data['avg_heart_rate']}\nNotatki: {parsed_data['notes']}\n\n**Czy wszystko się zgadza?**\n(Napisz 'Tak' by zapisać, lub powiedz co poprawić)"
        msg = bot.reply_to(message, preview, parse_mode="Markdown")

        bot.register_next_step_handler(msg, process_add_confirmation, parsed_data)
        
    except Exception as e:
        bot.reply_to(message, f"Nie udało się odczytać zdjęcia:\n`{str(e)}`", parse_mode="Markdown")



########################################
# NLP
########################################

last_bot_responses = {}
user_state = {}

class RouterSchema(BaseModel):
    intent: Literal["HISTORIA", "DODAJ_TRENING", "PLAN_TRENINGOWY", "USUN_TRENING", "INNE"]
    is_follow_up: bool = Field(description="Zaznacz True, jeśli użytkownik nawiązuje do Twojej ostatniej odpowiedzi (np. 'zrób to krócej', 'zmień na bieganie').")
    #odpowiedz_trenera: str = Field(description="Jeśli intent to INNE, odpowiedz użytkownikowi. W przeciwnym razie zostaw puste.")

@bot.message_handler(func=lambda message: is_me(message) and message.text and not message.text.startswith('/'))
def handle_natural_language(message):
    user_text = message.text
    chat_id = message.chat.id

    stan = user_state.get(chat_id, {"response": "", "intent": ""})
    ostatnia_odpowiedz = stan["response"]
    ostatni_intent = stan["intent"]

    router_prompt = f"""
    Jesteś asystentem trenera. 
    Oto Twoja OSTATNIA odpowiedź do użytkownika: "{ostatnia_odpowiedz}"
    TERAZ użytkownik napisał: "{user_text}".
    Jeśli użytkownik nawiązuje do Twojej ostatniej odpowiedzi, ustaw is_follow_up na True oraz intencję na {ostatni_intent}.
    Jeśli użytkownik zadaje nowe pytanie lub prośbę, ustaw is_follow_up na False i odgadnij intencję z wiadomości (HISTORIA, DODAJ_TRENING, PLAN_TRENINGOWY, USUN_TRENING lub INNE).

    """
    
    try:
        bot.send_message(message.chat.id, "Analizuję Twoją wiadomość...", parse_mode="Markdown")
        
        json_response, _ = ask_gemini(router_prompt, response_schema=RouterSchema, temperature=0.0)
    
        ai_data = json.loads(json_response)
        
        intent = ai_data.get("intent")
        is_follow_up = ai_data.get("is_follow_up", False)

        if intent != ostatni_intent:
            is_follow_up = False

        if is_follow_up and ostatnia_odpowiedz:
            rich_query = f"Kontekst rozmowy - to była Twoja ostatnia odpowiedź do mnie:\n{ostatnia_odpowiedz}\n\nTeraz napisałem do Ciebie: \"{user_text}\"\nOdpowiedz mi w nawiązaniu do naszej rozmowy."
        else:
            rich_query = user_text
        
        if intent == "HISTORIA":
            if is_follow_up and ostatnia_odpowiedz:
                bot.send_message(message.chat.id, "Modyfikuję odpowiedź...", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Analizuję twoją historię treningową...", parse_mode="Markdown")
            history = get_workouts(limit=14)
            response = analyze_history(rich_query, history) 
            response = response.replace('*', '')
            bot.reply_to(message, response)
            user_state[chat_id] = {"response": response, "intent": intent}

        elif intent == "DODAJ_TRENING":
            bot.send_message(message.chat.id, "Analizuję Twoje dane...", parse_mode="Markdown")
            parsed_data = parse_workout_data(rich_query)
            preview = f"Oto Twój trening:\n\nData: {parsed_data['date']}\nDyscyplina: {parsed_data['discipline']}\nCzas: {parsed_data['duration_minutes']} min\nDystans: {parsed_data['distance_km']} km\nRPE: {parsed_data['rpe']}\nHR: {parsed_data['avg_heart_rate']}\nNotatki: {parsed_data['notes']}\n\nCzy wszystko się zgadza?"
            msg = bot.reply_to(message, preview, parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_add_confirmation, parsed_data)
            user_state[chat_id] = {"response": "", "intent": ""}
            
        elif intent == "PLAN_TRENINGOWY":
            if is_follow_up and ostatnia_odpowiedz:
                bot.send_message(message.chat.id, "Modyfikuję plan treningowy...", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Przygotowuję plan treningowy...", parse_mode="Markdown")
            history = get_workouts(limit=14)
            response = propose_training(rich_query, history) 
            response = response.replace('*', '')
            bot.reply_to(message, response)
            user_state[chat_id] = {"response": response, "intent": intent}
            
        elif intent == "INNE":
            if is_follow_up and ostatnia_odpowiedz:
                bot.send_message(message.chat.id, "Odpowiadam na Twoje kolejne pytanie...", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Odpowiadam na Twoje pytanie...", parse_mode="Markdown")
            #bot.send_message(message.chat.id, "Odpowiadam na Twoje pytanie...", parse_mode="Markdown")
            response = ask_gemini(prompt = rich_query, temperature=0.7, model_name="gemini-3-flash-preview")
            #odpowiedz = ai_data.get("odpowiedz_trenera")
            bot.reply_to(message, response, parse_mode="Markdown")
            user_state[chat_id] = {"response": response, "intent": intent}

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
            user_state[chat_id] = {"response": "", "intent": ""}

    except Exception as e:
        bot.reply_to(message, f"Wystąpił błąd w kodzie:\n`{str(e)}`", parse_mode="Markdown")



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