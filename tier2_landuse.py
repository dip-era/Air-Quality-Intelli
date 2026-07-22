import os
import certifi
os.environ["SSL_CERT_FILE"] = certifi.where()

import requests
import time
import random
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY missing in .env file.")
    exit(1)

supabase: Client = create_client(url, key)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

CITIES = {
    "Delhi": (28.40, 76.83, 28.88, 77.34),
    "Kanpur": (26.35, 80.21, 26.58, 80.42),
    "Mumbai": (18.89, 72.77, 19.27, 73.00),
    "Guwahati": (26.07, 91.54, 26.24, 91.88),
    "Shimla": (31.06, 77.12, 31.14, 77.22),
    "Bengaluru": (12.83, 77.46, 13.14, 77.78),
    "Chennai": (12.92, 80.12, 13.20, 80.34)
}

def build_query(bbox_tuple):

    bbox_str = f"({bbox_tuple[0]}, {bbox_tuple[1]}, {bbox_tuple[2]}, {bbox_tuple[3]})"
    return f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"]{bbox_str};
      node["amenity"="school"]{bbox_str};
      node["landuse"="industrial"]{bbox_str};
    );
    out body;
    """

def generate_mock_points(city, bbox_tuple, count=1200):
    """Generates random POIs within the city bounds."""
    mock_batch = []
    categories = ["hospital", "school", "industrial"]
    s, w, n, e = bbox_tuple
    
    for i in range(count):
        category = random.choice(categories)
        emission_risk = "None"
        if category == "industrial":
            emission_risk = random.choice(["Low", "Medium", "High", "High"])
            
        mock_batch.append({
            "city": city,
            "name": f"Mock {category.title()} {i}",
            "category": category,
            "latitude": round(random.uniform(s, n), 6),
            "longitude": round(random.uniform(w, e), 6),
            "emission_risk": emission_risk
        })
    return mock_batch

def fetch_and_upload():
    for city, bbox in CITIES.items():
        print(f"\nFetching REAL static land use data for {city}...")
        headers = {"User-Agent": "AirQualityMVP/1.0", "Accept": "application/json"}
        
        batch = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:

                response = requests.post(OVERPASS_URL, data={'data': build_query(bbox)}, headers=headers, timeout=60)
                
                if response.status_code == 429 or response.status_code == 504:
                    print(f"  Overpass HTTP Error {response.status_code}. Server overloaded.")
                    if attempt < max_retries - 1:
                        sleep_time = 15 * (attempt + 1)
                        print(f"  Waiting {sleep_time} seconds before retrying...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        print("  Max retries reached. Using fallback data.")
                        batch = generate_mock_points(city, bbox, 500)
                        break
                        
                elif response.status_code != 200:
                    print(f"  Unexpected Error {response.status_code}: {response.text}")
                    batch = generate_mock_points(city, bbox, 500)
                    break
                    
                else:
                    data = response.json()
                    elements = data.get('elements', [])
                    print(f"  SUCCESS! Found {len(elements)} REAL points of interest from OpenStreetMap.")
                    
                    if len(elements) == 0:
                        print("  OSM returned 0 points. Using fallback data.")
                        batch = generate_mock_points(city, bbox, 500)
                    else:
                        for el in elements:
                            tags = el.get("tags", {})
                            if tags.get("amenity") == "hospital":
                                category, risk = "hospital", "None"
                            elif tags.get("amenity") == "school":
                                category, risk = "school", "None"
                            else:
                                category, risk = "industrial", random.choice(["Low", "Medium", "High", "High"])
                                
                            name = tags.get("name") or tags.get("operator") or "Unknown Facility"
                            batch.append({
                                "city": city, "name": name, "category": category,
                                "latitude": el["lat"], "longitude": el["lon"], "emission_risk": risk
                            })
                    break 
                    
            except requests.exceptions.Timeout:
                print(f"  Connection Timed Out.")
                if attempt < max_retries - 1:
                    print("  Waiting 15 seconds before retrying...")
                    time.sleep(15)
                else:
                    print("  Max retries reached. Using fallback data.")
                    batch = generate_mock_points(city, bbox, 500)
            except Exception as e:
                print(f"  Connection error: {e}")
                batch = generate_mock_points(city, bbox, 500)
                break
            
    
        try:
            if len(batch) > 0:
                print(f"  Uploading {len(batch)} records to Supabase...")
                for i in range(0, len(batch), 500):
                    chunk = batch[i:i+500]
                    supabase.table("geospatial_zones").insert(chunk).execute()
                print("  Successfully saved to Database!")
        except Exception as e:
            print(f"  Error inserting into Supabase: {e}")
            
        time.sleep(5) 

if __name__ == "__main__":
    fetch_and_upload()
