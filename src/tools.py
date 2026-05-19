import requests
import pandas as pd
import statistics
from datetime import timedelta
from google import genai
from google.genai import types
import time
import json
import os
from openai import OpenAI

from database import get_workouts



def ask_openrouter_native(messages, temperature=0.0, max_retries=3, response_schema=None, model_name="google/gemini-3.1-flash-lite", api_key=None):

    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://triathlon-coach.local",
            "X-Title": "TriathlonCoach"
        }
    )
    
    wait_time = 2
    
    for attempt in range(max_retries):
        try:
            if response_schema:
                response = client.chat.completions.parse(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    response_format=response_schema 
                )
                
                parsed_object = response.choices[0].message.parsed
                
            else:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature
                )
                parsed_object = response.choices[0].message.content
            
            return parsed_object
            
        except Exception as e:
            error_msg = str(e)
            if any(err in error_msg.lower() for err in ["429", "503", "rate limit", "unavailable"]):
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2
                    continue
            raise Exception(f"Błąd API: {error_msg}")



def get_weather_forecast(date_str):
    """Get weather forecast for a given date from weather API"""
    # Adjusted Lat/Lon to central Warsaw 
    lat = 52.23 
    lon = 21.01

    # Calculate end date (7 days ahead)
    date_end = pd.to_datetime(date_str) + pd.Timedelta(days=7)
    date_end_str = date_end.strftime('%Y-%m-%d')
    
    # API URL

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_sum,windspeed_10m_max&timezone=Europe%2FWarsaw&start_date={date_str}&end_date={date_end_str}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        daily = data.get('daily', {})
        
        temps = daily['temperature_2m_max']
        precip = daily['precipitation_sum']
        winds = daily['windspeed_10m_max']
        
        temps = [x for x in temps if x is not None]
        precip = [x for x in precip if x is not None]
        winds = [x for x in winds if x is not None]

        return {
            'period_start': date_str,
            'period_end': date_end_str,
            'temp_max_weekly_avg': round(statistics.mean(temps), 2),    # Średnia maks. temp
            'precip_weekly_sum': round(sum(precip), 2),                 # Suma opadów w tygodniu
            'precip_daily_avg': round(statistics.mean(precip), 2),      # Średni opad dzienny
            'wind_weekly_avg': round(statistics.mean(winds), 2)         # Średnia prędkość wiatru
        }
    else:
        print(f"Error: {response.status_code}")
        return None

def long_term_stats():
    df = get_workouts()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])

    weekly_stats = df.resample('W-MON', on='date').agg({ # Grupowanie po tygodniach (od poniedziałku)
            'duration_minutes': 'sum',
            'distance_km': 'sum',
            'rpe': 'mean' 
        })

    summary = ""

    for date, row in weekly_stats.iterrows():
        date = pd.to_datetime(date)
        week_start = date - timedelta(days=6)
        summary += f"- Tydzień {week_start.strftime('%Y-%m-%d')} do {date.strftime('%Y-%m-%d')}: "
        summary += f"{row['duration_minutes']} minut, {row['distance_km']} km, RPE {row['rpe']:.1f}\n"
    
    return summary
