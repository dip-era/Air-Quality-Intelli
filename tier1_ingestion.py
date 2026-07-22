import os
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

import requests
import random
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
if not url or not key:
    print("Warning: SUPABASE_URL or SUPABASE_KEY is not set in .env file. Data will be printed but not inserted.")
    supabase = None
else:
    supabase: Client = create_client(url, key)
LOCATIONS = {
    "Delhi": {"lat": 28.6139, "lon": 77.2090},
    "Guwahati": {"lat": 26.1445, "lon": 91.7362},
    "Kanpur": {"lat": 26.4499, "lon": 80.3319},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
    "Shimla": {"lat": 31.1048, "lon": 77.1734},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946},
    "Chennai": {"lat": 13.0827, "lon": 80.2707}
}

def generate_mock_aqi(city):
    """Fallback generator if API fails."""
    if city in ["Delhi", "Kanpur"]:
        return random.randint(150, 300), random.randint(200, 400) 
    elif city in ["Mumbai", "Chennai", "Bengaluru"]:
        return random.randint(60, 120), random.randint(80, 150) 
    else:
        return random.randint(10, 40), random.randint(15, 50) 

def generate_mock_weather(city):
    """Fallback weather if API fails."""
    if city == "Shimla":
        return random.randint(10, 20), random.randint(40, 60), round(random.uniform(2.0, 15.0), 1)
    else:
        return random.randint(25, 35), random.randint(50, 90), round(random.uniform(5.0, 25.0), 1)

def fetch_air_quality_data(lat, lon, city):
    """Fetches current PM2.5 and PM10 from Open-Meteo Air Quality API."""
    api_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=pm10,pm2_5"
    
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        current = data.get('current', {})
        return current.get('pm2_5'), current.get('pm10')
    except Exception as e:
        print(f"  [API Error] Generating fallback AQI data for {city}...")
        return generate_mock_aqi(city)

def fetch_open_meteo_data(lat, lon, city):
    """Fetches current weather data from Open-Meteo."""
    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        current = data.get('current', {})
        return current.get('temperature_2m'), current.get('relative_humidity_2m'), current.get('wind_speed_10m')
    except Exception as e:
        print(f"  [API Error] Generating fallback Weather data for {city}...")
        return generate_mock_weather(city)

def main():
    print("Starting Tier 1 Ingestion Pipeline...")
    
    if supabase:
        print("Cleaning up old database records to save space...")
        try:
           
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            supabase.table("aqi_weather_data").delete().lt("timestamp", cutoff_time).execute()
        except Exception as e:
            print(f"Cleanup error: {e}")
            
    for city, coords in LOCATIONS.items():
        print(f"\nProcessing {city}...")
        
        pm25, pm10 = fetch_air_quality_data(coords['lat'], coords['lon'], city)
        print(f"  AQI -> PM2.5: {pm25}, PM10: {pm10}")
       
        temp, humidity, wind_speed = fetch_open_meteo_data(coords['lat'], coords['lon'], city)
        print(f"  Weather -> Temp: {temp}°C, Humidity: {humidity}%, Wind Speed: {wind_speed} km/h")
        
      
        payload = {
            "city": city,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pm25": pm25,
            "pm10": pm10,
            "temperature": temp,
            "humidity": humidity,
            "wind_speed": wind_speed
        }
        
    
        if supabase:
            try:
                result = supabase.table("aqi_weather_data").insert(payload).execute()
                print(f"  Successfully inserted data for {city} into Supabase.")
            except Exception as e:
                print(f"  Error inserting into Supabase for {city}: {e}")
        else:
            print("  Skipping Supabase insert (Credentials missing). Payload would be:")
            print(f"  {payload}")

if __name__ == "__main__":
    main()
