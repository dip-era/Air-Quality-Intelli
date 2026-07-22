import os
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from ai_agents import generate_city_insights


# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is missing in .env file.")

supabase: Client = create_client(url, key)

# Initialize FastAPI app
app = FastAPI(
    title="Air Quality Intelligence API",
    description="FastAPI Gateway for serving AQI, Weather, Geospatial, and Satellite data.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For hackathon MVP, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Air Quality Intelligence Gateway is running."}

@app.get("/api/live-aqi/{city}")
def get_live_aqi(city: str):
    """Fetches the most recent AQI and weather reading for a specific city."""
    try:
        response = supabase.table("aqi_weather_data") \
            .select("*") \
            .ilike("city", city) \
            .order("timestamp", desc=True) \
            .limit(1) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No data found for city: {city}")
            
        return {"city": city, "latest_reading": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/geospatial-zones/{city}")
def get_geospatial_zones(city: str):
    """Fetches all geospatial zones (schools, hospitals, industrial) for a city."""
    try:
        response = supabase.table("geospatial_zones") \
            .select("*") \
            .ilike("city", city) \
            .execute()
        
        return {"city": city, "zones": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/satellite-fires")
def get_satellite_fires():
    """Fetches historical thermal anomalies (fires)."""
    try:
        response = supabase.table("satellite_thermal_anomalies") \
            .select("*") \
            .execute()
            
        return {"fires": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live-traffic/{city}")
def get_live_traffic(city: str):
    """Fetches the 24-hr Traffic reading history for a specific city."""
    try:
        response = supabase.table("traffic_data") \
            .select("*") \
            .ilike("city", city) \
            .order("timestamp", desc=True) \
            .limit(24) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"No traffic data found for city: {city}")
            
        return {"city": city, "traffic_history": response.data, "latest_traffic": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traffic-incidents/{city}")
def get_traffic_incidents(city: str):
    """Fetches all live traffic incidents (accidents, jams) for a specific city."""
    try:
        response = supabase.table("traffic_incidents") \
            .select("*") \
            .ilike("city", city) \
            .execute()
        
        return {"city": city, "incidents": response.data, "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai-insights/{city}")
def get_ai_insights(city: str):
    """Uses Groq API to act as the Geospatial Source Attribution Engine."""
    try:
        # 1. Fetch latest AQI
        aqi_resp = supabase.table("aqi_weather_data").select("*").ilike("city", city).order("timestamp", desc=True).limit(1).execute()
        if not aqi_resp.data:
            raise HTTPException(status_code=404, detail="No AQI data found for this city.")
        aqi_data = aqi_resp.data[0]

        # 2. Fetch Geospatial Zones
        geo_resp = supabase.table("geospatial_zones").select("*").ilike("city", city).execute()
        geospatial_data = geo_resp.data

        # 3. Fetch Satellite Fires
        fire_resp = supabase.table("satellite_thermal_anomalies").select("*").execute()
        satellite_data = fire_resp.data
        
        # 4. Fetch Traffic History
        traffic_resp = supabase.table("traffic_data").select("*").ilike("city", city).order("timestamp", desc=True).limit(24).execute()
        traffic_data = traffic_resp.data if traffic_resp.data else None
        
        # 5. Fetch Traffic Incidents
        incident_resp = supabase.table("traffic_incidents").select("*").ilike("city", city).execute()
        incidents_data = incident_resp.data if incident_resp.data else None

        # 6. Pass everything to Groq
        insights = generate_city_insights(city, aqi_data, geospatial_data, satellite_data, traffic_data, incidents_data)

        return {"city": city, "ai_insights": insights}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
def calculate_us_epa_aqi(concentration, pollutant="PM2.5"):
    """
    Calculates the AQI based on US EPA standards for PM2.5 and PM10.
    """
    if pollutant == "PM2.5":
        # EPA standard: Truncate PM2.5 to 1 decimal place
        c = int(float(concentration) * 10) / 10.0
        
        # Format: (C_low, C_high, I_low, I_high)
        breakpoints = [
            (0.0, 12.0, 0, 50),
            (12.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 150.4, 151, 200),
            (150.5, 250.4, 201, 300),
            (250.5, 350.4, 301, 400),
            (350.5, 500.4, 401, 500)
        ]
        
    elif pollutant == "PM10":
        # EPA standard: Truncate PM10 to an integer
        c = int(float(concentration))
        
        breakpoints = [
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, 504, 301, 400),
            (505, 604, 401, 500)
        ]
    else:
        raise ValueError("Pollutant must be 'PM2.5' or 'PM10'")

    # Find the matching bracket and apply linear interpolation
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= c <= c_high:
            aqi = ((i_high - i_low) / (c_high - c_low)) * (c - c_low) + i_low
            return round(aqi)

    # Return max index for extreme pollution beyond the standard scale
    return 500


# --- Usage Example for api.py ---
if __name__ == "__main__":
    raw_pm25 = 12.3
    raw_pm10 = 25.0
    
    pm25_aqi = calculate_us_epa_aqi(raw_pm25, "PM2.5")
    pm10_aqi = calculate_us_epa_aqi(raw_pm10, "PM10")
    
    print(f"PM2.5 AQI: {pm25_aqi}") # Outputs: 51
    print(f"PM10 AQI:  {pm10_aqi}") # Outputs: 23