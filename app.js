const API_BASE_URL = "http://127.0.0.1:8000";

// 1. Coordinate Dictionary
const CITY_COORDINATES = {
    "delhi": [28.6139, 77.2090],
    "guwahati": [26.1445, 91.7362]
};

let map;
let markers = [];

// Initialize Map
function initMap() {
    map = L.map('map').setView([28.6139, 77.2090], 11);
    
    // Dark themed map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // --- Custom Map Legend (Top Right) ---
    let legend = L.control({position: 'topright'});

    legend.onAdd = function (map) {
        let div = L.DomUtil.create('div', 'map-legend');
        
        // Inline styling to match the dark dashboard theme
        div.style.backgroundColor = '#1e293b'; // Slate 800
        div.style.padding = '12px';
        div.style.borderRadius = '8px';
        div.style.border = '1px solid #334155'; // Slate 700
        div.style.color = '#f8fafc'; // Slate 50
        div.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        div.style.fontSize = '13px';
        div.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.5)';

        div.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 8px; font-size: 14px;">Map Key</div>
            <div style="display: flex; align-items: center; margin-bottom: 6px;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: #10b981; display: inline-block; margin-right: 8px;"></span> Hospital
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 6px;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: #3b82f6; display: inline-block; margin-right: 8px;"></span> School
            </div>
            <div style="display: flex; align-items: center;">
                <span style="width: 12px; height: 12px; border-radius: 50%; background-color: #ef4444; display: inline-block; margin-right: 8px;"></span> Industrial site
            </div>
        `;
        return div;
    };

    legend.addTo(map);
}

// Clear existing markers
function clearMarkers() {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
}

async function fetchData() {
    const city = document.getElementById('city-select').value;
    const cityKey = city.toLowerCase();

    // 2. Dynamic Map Centering
    if (CITY_COORDINATES[cityKey]) {
        map.flyTo(CITY_COORDINATES[cityKey], 11, { duration: 1.5 });
    }
    
    // UI Loading state
    document.getElementById('refresh-btn').innerText = "Analyzing...";
    document.getElementById('ai-loading').style.display = "block";
    document.getElementById('ai-attribution').querySelector('.ai-text').innerText = "";
    document.getElementById('ai-advisory').querySelector('.ai-text').innerText = "Waiting for AI...";

    try {
        // 1. Fetch Live AQI
        const aqiRes = await fetch(`${API_BASE_URL}/api/live-aqi/${city}`);
        if(aqiRes.ok) {
            const aqiData = await aqiRes.json();
            const reading = aqiData.latest_reading;
            
            const aqiValElem = document.getElementById('aqi-val');
            aqiValElem.innerText = reading.pm25;
            
            // Color coding
            aqiValElem.className = 'value';
            if(reading.pm25 < 50) aqiValElem.classList.add('aqi-good');
            else if(reading.pm25 < 150) aqiValElem.classList.add('aqi-moderate');
            else aqiValElem.classList.add('aqi-hazardous');

            document.getElementById('pm10-val').innerText = `PM10: ${reading.pm10}`;
            document.getElementById('temp-val').innerText = `${reading.temperature}°C`;
            document.getElementById('wind-val').innerText = `${reading.wind_speed} km/h`;
            document.getElementById('humidity-val').innerText = `${reading.humidity}%`;
        }

        // 2. Fetch Geospatial Zones for Map
        clearMarkers();
        const geoRes = await fetch(`${API_BASE_URL}/api/geospatial-zones/${city}`);
        if(geoRes.ok) {
            const geoData = await geoRes.json();
            
            let bounds = [];
            // Safeguard for empty zones
            if (geoData.zones && geoData.zones.length > 0) {
                geoData.zones.forEach(zone => {
                    
                    // SWAPPED COLORS: Hospital is Green, School is Blue
                    let color = zone.category === 'hospital' ? '#10b981' : 
                                zone.category === 'school' ? '#3b82f6' : '#ef4444';
                                
                    let circle = L.circleMarker([zone.latitude, zone.longitude], {
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.5,
                        radius: 5
                    }).addTo(map);
                    
                    circle.bindPopup(`<b>${zone.name}</b><br>${zone.category.toUpperCase()}`);
                    markers.push(circle);
                    bounds.push([zone.latitude, zone.longitude]);

                    // --- ADDED: 2km glowing radius for Industrial zones ---
                    if (zone.category === 'industrial') { 
                        let glowCircle = L.circle([zone.latitude, zone.longitude], {
                            color: '#ef4444',
                            fillColor: '#ef4444',
                            fillOpacity: 0.15,
                            weight: 1,
                            radius: 2000, // 2000 meters = 2 km
                            className: 'industrial-glow' // Attaching a custom CSS class for the glow
                        }).addTo(map);
                        
                        // Push to array so it clears automatically when changing cities
                        markers.push(glowCircle);
                    }
                });
                
                if(bounds.length > 0) map.fitBounds(bounds);
            }
        }

        // 3. Fetch AI Insights
        const aiRes = await fetch(`${API_BASE_URL}/api/ai-insights/${city}`);
        if(aiRes.ok) {
            const aiData = await aiRes.json();
            const insights = aiData.ai_insights;
            
            document.getElementById('ai-loading').style.display = "none";
            document.getElementById('ai-attribution').querySelector('.ai-text').innerText = insights.attribution || insights.error;
            document.getElementById('ai-advisory').querySelector('.ai-text').innerText = insights.advisory || "";
        }

    } catch (error) {
        console.error("Error fetching data:", error);
        alert("Failed to connect to the backend API. Is FastAPI running on port 8000?");
    } finally {
        document.getElementById('refresh-btn').innerText = "Live Analysis";
        document.getElementById('ai-loading').style.display = "none";
    }
}

// Event Listeners
document.getElementById('refresh-btn').addEventListener('click', fetchData);
document.getElementById('city-select').addEventListener('change', fetchData);

// Init
window.onload = () => {
    initMap();
    fetchData(); // Load initial data
};