import os
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

import random
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY missing in .env file.")
    exit(1)

supabase: Client = create_client(url, key)

def simulate_historical_fires():
    print("Simulating historical NASA FIRMS satellite thermal anomalies (Multi-Region)...")
    
    if supabase:
        print("Cleaning up old database records to save space...")
        try:
            cutoff_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
            supabase.table("satellite_thermal_anomalies").delete().lt("acq_date", cutoff_date).execute()
        except Exception as e:
            print(f"Cleanup error: {e}")
            
    base_date = datetime(2025, 11, 4)
    
    FIRE_ZONES = [
        (29.5, 30.8, 74.5, 76.5, 150),
        (26.3, 26.8, 91.8, 92.5, 30),
        (19.3, 19.8, 73.2, 73.8, 20)
    ]
    
    anomalies = []
    
    for zone in FIRE_ZONES:
        lat_min, lat_max, lon_min, lon_max, count = zone
        for i in range(count):
            lat = round(random.uniform(lat_min, lat_max), 4)
            lon = round(random.uniform(lon_min, lon_max), 4)
            brightness = round(random.uniform(310.0, 345.0), 1)
            day_offset = random.randint(0, 2)
            acq_date = (base_date + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            confidence = random.choice(["n", "n", "n", "h"]) 
            
            anomalies.append({
                "latitude": lat,
                "longitude": lon,
                "brightness": brightness,
                "acq_date": acq_date,
                "confidence": confidence
            })

    print(f"Generated {len(anomalies)} thermal anomalies across {len(FIRE_ZONES)} regions. Uploading to Supabase...")
    
    batch_size = 50
    inserted = 0
    for i in range(0, len(anomalies), batch_size):
        batch = anomalies[i:i+batch_size]
        try:
            supabase.table("satellite_thermal_anomalies").insert(batch).execute()
            inserted += len(batch)
            print(f"  Inserted {inserted} records...")
        except Exception as e:
            print(f"  Error inserting batch: {e}")
            break
        
    print("Success! Tier 3 multi-region historical satellite data is now in your database.")

if __name__ == "__main__":
    simulate_historical_fires()
