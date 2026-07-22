import os
import certifi
import random
import math
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

os.environ["SSL_CERT_FILE"] = certifi.where()

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
if not url or not key:
    print("Warning: SUPABASE_URL or SUPABASE_KEY missing.")
    supabase = None
else:
    supabase: Client = create_client(url, key)

LOCATIONS = {
    "Delhi": {"lat": 28.6139, "lon": 77.2090, "radius": 0.15, "incidents": 45},
    "Guwahati": {"lat": 26.1445, "lon": 91.7362, "radius": 0.05, "incidents": 8},
    "Kanpur": {"lat": 26.4499, "lon": 80.3319, "radius": 0.08, "incidents": 15},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "radius": 0.12, "incidents": 38},
    "Shimla": {"lat": 31.1048, "lon": 77.1734, "radius": 0.03, "incidents": 3},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946, "radius": 0.14, "incidents": 50},
    "Chennai": {"lat": 13.0827, "lon": 80.2707, "radius": 0.10, "incidents": 25}
}

def generate_random_coordinate(center_lat, center_lon, radius_deg):
    angle = random.uniform(0, 2 * math.pi)
    r = radius_deg * math.sqrt(random.uniform(0, 1))
    return center_lat + r * math.cos(angle), center_lon + r * math.sin(angle)

def get_congestion_level(current, free_flow):
    ratio = current / free_flow if free_flow > 0 else 1.0
    if ratio < 0.4: return "Severe", ratio
    if ratio < 0.7: return "Moderate", ratio
    return "Free-flowing", ratio

def generate_time_series_traffic(city):
    """Generates 24 hours of traffic data simulating a realistic rush hour curve."""
    rows = []
    base_time = datetime.now(timezone.utc)
    
    free_flow = random.randint(50, 70) if city in ["Delhi", "Mumbai", "Bengaluru"] else random.randint(40, 60)
    
    for i in range(24):
    
        dt = base_time - timedelta(hours=i)
        hour = dt.hour
  
        if (7 <= hour <= 10) or (16 <= hour <= 19):
            # Rush hour
            current = int(free_flow * random.uniform(0.2, 0.4))
        else:
            # Off peak
            current = int(free_flow * random.uniform(0.6, 0.95))
            
        level, ratio = get_congestion_level(current, free_flow)
        
        rows.append({
            "city": city,
            "timestamp": dt.isoformat(),
            "current_speed": current,
            "free_flow_speed": free_flow,
            "congestion_ratio": ratio,
            "congestion_level": level
        })
    return rows

def generate_incidents(city, data):
    """Generates specific geospatial traffic jams for the Leaflet Map."""
    rows = []
    base_time = datetime.now(timezone.utc)
    for _ in range(data["incidents"]):
        lat, lon = generate_random_coordinate(data["lat"], data["lon"], data["radius"])
        
    
        if city == "Mumbai" and lon < 72.84:
            lon = 72.84 + random.uniform(0.01, 0.06) 
        if city == "Chennai" and lon > 80.28:
            lon = 80.28 - random.uniform(0.01, 0.06)
            
        severity = random.choice(["Accident", "Road Closure", "Heavy Jam", "Construction"])
        rows.append({
            "city": city,
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "severity": severity,
            "timestamp": base_time.isoformat()
        })
    return rows

def main():
    print("Starting Tier 4 High-Precision Traffic Ingestion...")
    
    if supabase:
        print("Cleaning up old database records to save space...")
        try:
            
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            supabase.table("traffic_data").delete().lt("timestamp", cutoff_time).execute()
            supabase.table("traffic_incidents").delete().lt("timestamp", cutoff_time).execute()
        except Exception as e:
            print(f"Cleanup error: {e}")
        
    for city, data in LOCATIONS.items():
        print(f"\nGenerating Precision Data for {city}...")
        
       
        traffic_rows = generate_time_series_traffic(city)
        print(f"  Generated {len(traffic_rows)} hours of time-series traffic.")
        
        
        incident_rows = generate_incidents(city, data)
        print(f"  Generated {len(incident_rows)} specific traffic incidents across the city.")
        
        if supabase:
           
            print("  Uploading time-series...")
            for t_row in traffic_rows:
                try:
                    supabase.table("traffic_data").insert(t_row).execute()
                except Exception as e:
                    pass 
            
           
            print("  Uploading incidents...")
            for i_row in incident_rows:
                try:
                    supabase.table("traffic_incidents").insert(i_row).execute()
                except Exception as e:
                    pass
            print("  Saved safely to Database!")

if __name__ == "__main__":
    main()
