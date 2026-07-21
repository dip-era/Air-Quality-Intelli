import os
import ssl
import certifi
import json
import google.generativeai as genai

# Monkeypatch ssl to completely bypass the broken Windows Certificate Store
orig_create_default_context = ssl.create_default_context
def custom_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
    if cafile is None:
        cafile = certifi.where()
    return orig_create_default_context(purpose=purpose, cafile=cafile, capath=capath, cadata=cadata)
ssl.create_default_context = custom_create_default_context

# Initialize Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    
    # Fetch available models that support content generation
    valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Target 3.1-flash-lite for the 15 RPM free tier allowance
    if "models/gemini-3.1-flash-lite" in valid_models:
        chosen_model = "models/gemini-3.1-flash-lite"
    else:
        # Fallback to hardcoding if the list is acting up
        chosen_model = "gemini-3.1-flash-lite"
        
    model = genai.GenerativeModel(chosen_model)
else:
    model = None

def generate_city_insights(city_name: str, aqi_data: dict, geospatial_data: list, satellite_data: list):
    """
    Acts as the Geospatial Source Attribution Engine.
    Passes the context to Gemini to generate an analytical report.
    """
    if not model:
        return {"error": "GEMINI_API_KEY is missing from .env file."}

    # Count infrastructure for context
    hospitals = sum(1 for zone in geospatial_data if zone.get("category") == "hospital")
    schools = sum(1 for zone in geospatial_data if zone.get("category") == "school")
    industrial = sum(1 for zone in geospatial_data if zone.get("category") == "industrial")
    fires = len(satellite_data)

    # Construct the Prompt
    prompt = f"""
    You are the 'Geospatial Source Attribution Engine' for an Urban Air Quality Intelligence Platform.
    
    Analyze the following real-time and static data for {city_name}:
    
    1. CURRENT WEATHER & AQI:
    - PM2.5: {aqi_data.get('pm25')}
    - PM10: {aqi_data.get('pm10')}
    - Temperature: {aqi_data.get('temperature')}°C
    - Humidity: {aqi_data.get('humidity')}%
    - Wind Speed: {aqi_data.get('wind_speed')} km/h
    
    2. LOCAL INFRASTRUCTURE & VULNERABILITY:
    - Vulnerable Zones: {hospitals} hospitals and {schools} schools in the area.
    - Potential Emission Sources: {industrial} industrial zones mapped.
    
    3. SATELLITE ANOMALIES:
    - {fires} historical thermal anomalies (fires) detected nearby.
    
    Based on this data, provide a structured JSON output with exactly these 3 keys:
    1. "attribution": A short 2-sentence explanation of what is likely causing the current PM2.5 levels (e.g. blame industrial zones or fires based on wind speed and AQI).
    2. "advisory": A 1-sentence health warning directed at the hospitals and schools.
    3. "forecast_hint": A 1-sentence prediction of what might happen to the AQI if the wind speed drops.
    
    Return ONLY valid JSON.
    """

    try:
        # Generate content while strictly enforcing a JSON response format
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        insights = json.loads(response.text)
        return insights
    except Exception as e:
        return {"error": f"Failed to generate insights: {str(e)}"}