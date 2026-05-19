import os
import telebot
import json
from dotenv import load_dotenv
import pandas as pd
from pydantic import BaseModel, Field
from typing import Literal

from database import get_workouts, delete_workout, add_workout
from agents import analyze_history, propose_training, parse_workout_data, delete_workout_bot, parse_workout_from_image
from tools import ask_openrouter_native


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
# SCREENSHOT PARSING
########################################
@bot.message_handler(content_types=['photo'], func=is_me)
def handle_photo_workout(message):
    try:
        bot.send_message(message.chat.id, "Analizuję zrzut ekranu...", parse_mode="Markdown")
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

@bot.message_handler(func=lambda message: is_me(message) and message.text and not message.text.startswith('/'))
def handle_natural_language(message):
    user_text = message.text
    chat_id = message.chat.id

    stan = user_state.get(chat_id, {"response": "", "intent": ""})
    ostatnia_odpowiedz = stan.get("response", "")
    ostatni_intent = stan.get("intent", "")

    messages = [
        {
            "role": "system", 
            "content": (
                "Jesteś inteligentnym routerem dla trenera triathlonu. "
                "Zklasyfikuj intencję najnowszej wiadomości użytkownika. "
                "Intencje do wyboru: HISTORIA (analiza historii treningowej), DODAJ_TRENING (dodanie odbytego juz treningu), PLAN_TRENINGOWY (propozycja planu treningowego), USUN_TRENING (usunięcie treningu z historii), INNE (inne pytania lub prośby). "
                f"Jeśli jest to kontynuacja poprzedniego tematu, ustaw is_follow_up na True."
            )
        }
    ]

    # Dodajemy poprzednią odpowiedź asystenta (jeśli istnieje)
    if ostatnia_odpowiedz:
        messages.append({"role": "assistant", "content": ostatnia_odpowiedz})

    # Dodajemy bieżące zapytanie użytkownika
    messages.append({"role": "user", "content": user_text})
    
    try:
        bot.send_message(chat_id, "Analizuję Twoją wiadomość...", parse_mode="Markdown")
        
        # Podajemy listę wiadomości i nasz model Pydantic
        router_result = ask_openrouter_native(messages, response_schema=RouterSchema, temperature=0.0)
        
    
        intent = router_result.intent
        is_follow_up = router_result.is_follow_up

        if intent != ostatni_intent:
            is_follow_up = False

        agent_messages = messages[1:] # Pomijamy systemową wiadomość przy przekazywaniu do agenta
        
        if intent == "HISTORIA":
            if is_follow_up and ostatnia_odpowiedz:
                bot.send_message(message.chat.id, "Modyfikuję odpowiedź...", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Analizuję twoją historię treningową...", parse_mode="Markdown")
            history = get_workouts(limit=14)
            response = analyze_history(agent_messages, history) 
            response = response.replace('*', '')
            bot.reply_to(message, response)
            user_state[chat_id] = {"response": response, "intent": intent}

        elif intent == "DODAJ_TRENING":
            bot.send_message(message.chat.id, "Analizuję Twoje dane...", parse_mode="Markdown")
            parsed_data = parse_workout_data(user_text)
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
            response = propose_training(agent_messages, history) 
            response = response.replace('*', '')
            bot.reply_to(message, response)
            user_state[chat_id] = {"response": response, "intent": intent}
            
        elif intent == "INNE":
            if is_follow_up and ostatnia_odpowiedz:
                bot.send_message(message.chat.id, "Odpowiadam na Twoje kolejne pytanie...", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Odpowiadam na Twoje pytanie...", parse_mode="Markdown")
            #bot.send_message(message.chat.id, "Odpowiadam na Twoje pytanie...", parse_mode="Markdown")
            #response = ask_openrouter_native(prompt = rich_query, temperature=0.7)
            inne_messages = [{"role": "user", "content": agent_messages}]
            response = ask_openrouter_native(inne_messages, temperature=0.7)
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
    messages = [{"role": "user", "content": confirm_prompt}]
    try:
        decision = ask_openrouter_native(messages, temperature=0.1)
        
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
    messages = [{"role": "user", "content": confirm_prompt}]
    try:
        decision = ask_openrouter_native(messages, temperature=0.1)
        
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