import requests
import pandas as pd
import statistics
from datetime import timedelta

from database import get_all_workouts

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
    df = get_all_workouts()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])

    weekly_stats = df.resample('W-MON', on='date').agg({
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
