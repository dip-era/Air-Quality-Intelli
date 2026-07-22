import os
import certifi
import requests
import json

os.environ["SSL_CERT_FILE"] = certifi.where()

# Initialize Groq API Key
api_key = os.environ.get("GROQ_API_KEY")

def generate_city_insights(city_name: str, aqi_data: dict, geospatial_data: list, satellite_data: list, traffic_data: list = None, incidents_data: list = None):
    """
    Acts as the Geospatial Source Attribution Engine using Groq (LLaMA-3).
    """
    if not api_key:
        return {"error": "GROQ_API_KEY is missing from .env file."}

    # Count infrastructure for context
    hospitals = sum(1 for zone in geospatial_data if zone.get("category") == "hospital")
    schools = sum(1 for zone in geospatial_data if zone.get("category") == "school")
    industrial = sum(1 for zone in geospatial_data if zone.get("category") == "industrial")
    fires = len(satellite_data)
    
    # Format Traffic Context (Trend & Incidents)
    traffic_context = "No live traffic data available."
    if traffic_data and len(traffic_data) > 0:
        latest = traffic_data[0]
        # Calculate trend (compare latest with 6 hours ago if available)
        trend_str = "Stable"
        if len(traffic_data) > 6:
            past = traffic_data[6]
            if latest.get("congestion_ratio", 1) < past.get("congestion_ratio", 1) - 0.1:
                trend_str = "Worsening (Congestion Increasing)"
            elif latest.get("congestion_ratio", 1) > past.get("congestion_ratio", 1) + 0.1:
                trend_str = "Improving (Congestion Decreasing)"
                
        incidents_count = len(incidents_data) if incidents_data else 0
        
        traffic_context = f"""
        - Current Congestion: {latest.get('congestion_level')} (Avg Speed: {latest.get('current_speed')} km/h)
        - 6-Hour Trend: {trend_str}
        - Traffic Incidents (Jams/Accidents): {incidents_count} active incidents mapped in {city_name}.
        """

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
    
    4. TRAFFIC & MOBILITY:
    {traffic_context}
    
    Based on this data, provide a structured JSON output with exactly these keys:
    {{
        "source_attribution": {{
            "summary": "Detailed analysis of what is causing the current pollution levels based on wind, factories, and fires.",
            "confidence": "A percentage string e.g. '85%'"
        }},
        "hyperlocal_forecast": {{
            "predicted_pm25": 140,
            "rmse_vs_baseline": "12.4",
            "trend": "Short string describing the trend (e.g. 'Increasing due to falling wind speeds')"
        }},
        "enforcement_recommendations": [
            {{
                "action": "Specific action to take",
                "target": "Target entity or zone type",
                "priority": "CRITICAL, HIGH, or MODERATE",
                "estimated_impact": "Estimated PM reduction (e.g. '-15% PM10')"
            }}
        ],
        "citizen_advisory": {{
            "english": "Public health warning in English",
            "local_language": "Public health warning translated to the primary local language of {city_name}, written strictly in its native script (e.g. Devanagari for Hindi/Pahari, Kannada for Bengaluru, etc.), avoiding Romanized or English alphabet transliteration."        }}
    }}
    
    IMPORTANT RULES FOR ENFORCEMENT RECOMMENDATIONS:
    - You MUST output at least 3 or 4 actionable interventions! Do NOT output less than 3!
    - At least ONE of the interventions MUST specifically address the "TRAFFIC & MOBILITY" data (e.g., rerouting traffic around incidents, managing the 6-hour trend, etc.).
    
    Return ONLY valid JSON. No markdown formatting or extra text.
    """

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code != 200:
            return {"error": f"Groq API Error {response.status_code}: {response.text}"}
            
        data = response.json()
        text_response = data['choices'][0]['message']['content']
        
        # Clean up markdown JSON block if present
        text_response = text_response.strip()
        if text_response.startswith("```json"):
            text_response = text_response[7:-3].strip()
        elif text_response.startswith("```"):
            text_response = text_response[3:-3].strip()
            
        insights = json.loads(text_response)
        return insights
    except Exception as e:
        return {"error": f"Failed to generate insights via Groq: {str(e)}"}