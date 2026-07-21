import os
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
from ai_agents import generate_city_insights

# Load environment variables


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

@app.get("/api/ai-insights/{city}")
def get_ai_insights(city: str):
    """Uses Gemini API to act as the Geospatial Source Attribution Engine."""
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

        # 4. Pass everything to Gemini
        insights = generate_city_insights(city, aqi_data, geospatial_data, satellite_data)

        return {"city": city, "ai_insights": insights}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))