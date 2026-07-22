const API_BASE_URL = "http://127.0.0.1:8000";

let map;
let markers = [];
let currentAdvisoryData = { english: "", local: "" }; // Holds translated advisory states

// US EPA AQI Calculation Function
function calculateAQI(concentration, pollutant) {
    let c, breakpoints;
    
    if (pollutant === 'PM2.5') {
        c = Math.floor(concentration * 10) / 10;
        breakpoints = [
            [0.0, 12.0, 0, 50],
            [12.1, 35.4, 51, 100],
            [35.5, 55.4, 101, 150],
            [55.5, 150.4, 151, 200],
            [150.5, 250.4, 201, 300],
            [250.5, 350.4, 301, 400],
            [350.5, 500.4, 401, 500]
        ];
    } else if (pollutant === 'PM10') {
        c = Math.floor(concentration);
        breakpoints = [
            [0, 54, 0, 50],
            [55, 154, 51, 100],
            [155, 254, 101, 150],
            [255, 354, 151, 200],
            [355, 424, 201, 300],
            [425, 504, 301, 400],
            [505, 604, 401, 500]
        ];
    }

    for (let i = 0; i < breakpoints.length; i++) {
        let [cLow, cHigh, iLow, iHigh] = breakpoints[i];
        if (c >= cLow && c <= cHigh) {
            return Math.round(((iHigh - iLow) / (cHigh - cLow)) * (c - cLow) + iLow);
        }
    }
    return 500;
}

// Initialize Map
function initMap() {
    map = L.map('map').setView([28.6139, 77.2090], 11);
    
    // Dark themed map tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
}

// Clear existing markers
function clearMarkers() {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
}

async function fetchData() {
    const city = document.getElementById('city-select').value;
    
    // UI Loading state
    document.getElementById('refresh-btn').innerText = "Analyzing...";
    document.getElementById('ai-loading').style.display = "block";
    document.getElementById('ai-attribution').querySelector('.ai-text').innerText = "";
    document.getElementById('ai-confidence').innerText = "";
    document.getElementById('action-list').innerHTML = '<li class="ai-text">Waiting for AI...</li>';
    document.getElementById('ai-forecast').querySelector('.ai-text').innerText = "Waiting for AI...";
    document.getElementById('ai-advisory-text').innerText = "Waiting for AI...";

    try {
        // 1. Fetch Live AQI
        const aqiRes = await fetch(`${API_BASE_URL}/api/live-aqi/${city}`);
        if(aqiRes.ok) {
            const aqiData = await aqiRes.json();
            const reading = aqiData.latest_reading;
            
            // Calculate true AQI from raw concentrations
            const pm25AQI = calculateAQI(reading.pm25, 'PM2.5');
            const pm10AQI = calculateAQI(reading.pm10, 'PM10');
            const mainAQI = Math.max(pm25AQI, pm10AQI);
            
            const aqiValElem = document.getElementById('aqi-val');
            aqiValElem.innerText = mainAQI;
            
            // Color coding based on AQI brackets
            aqiValElem.className = 'value';
            if(mainAQI <= 50) aqiValElem.classList.add('aqi-good');
            else if(mainAQI <= 100) aqiValElem.classList.add('aqi-moderate');
            else aqiValElem.classList.add('aqi-hazardous');

            // Display raw concentrations in the subtext element
            document.getElementById('pm10-val').innerText = `PM2.5: ${reading.pm25} µg/m³ | PM10: ${reading.pm10} µg/m³`;
            document.getElementById('temp-val').innerText = `${reading.temperature}°C`;
            document.getElementById('wind-val').innerText = `${reading.wind_speed} km/h`;
            document.getElementById('humidity-val').innerText = `${reading.humidity}%`;
        }
        
        // 2. Fetch Geospatial Zones for Map
        clearMarkers();
        let bounds = [];
        
        const geoRes = await fetch(`${API_BASE_URL}/api/geospatial-zones/${city}`);
        if(geoRes.ok) {
            const geoData = await geoRes.json();
            geoData.zones.forEach(zone => {
                let color = zone.category === 'hospital' ? '#3b82f6' : 
                            zone.category === 'school' ? '#10b981' : '#ef4444';
                            
                let radius = 5;
                if (zone.category === 'industrial') {
                    if (zone.emission_risk === 'High') radius = 12;
                    else if (zone.emission_risk === 'Medium') radius = 8;
                    else radius = 4;
                }
                            
                let circle = L.circleMarker([zone.latitude, zone.longitude], {
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.6,
                    radius: radius,
                    className: zone.category === 'industrial' && zone.emission_risk === 'High' ? 'industrial-glow' : ''
                }).addTo(map);
                
                // Richer Popup with real DB Risk Score
                const riskHtml = zone.category === 'industrial' ? `<br><b style="color:#ef4444;">Emission Risk: ${zone.emission_risk || 'Unknown'}</b>` : '';
                
                circle.bindPopup(`<b>${zone.name}</b><br>${zone.category.toUpperCase()} ${riskHtml}`);
                markers.push(circle);
                bounds.push([zone.latitude, zone.longitude]);
            });
        }
        
        // 3. Fetch Traffic Incidents (Map Markers)
        try {
            const incRes = await fetch(`${API_BASE_URL}/api/traffic-incidents/${city}`);
            if(incRes.ok) {
                const incData = await incRes.json();
                incData.incidents.forEach(inc => {
                    let marker = L.circleMarker([inc.latitude, inc.longitude], {
                        radius: 5,
                        fillColor: "#f97316",
                        color: "#c2410c",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8,
                        className: 'pulse-marker'
                    }).bindPopup(`<b>Traffic Incident</b><br>${inc.severity}`).addTo(map);
                    markers.push(marker);
                    bounds.push([inc.latitude, inc.longitude]);
                });
            }
        } catch(e) {
            console.log("Error fetching traffic incidents.");
        }
        
        if(bounds.length > 0) map.fitBounds(bounds, {padding: [50, 50]});

        // 4. Fetch AI Insights
        const aiRes = await fetch(`${API_BASE_URL}/api/ai-insights/${city}`);
        if(aiRes.ok) {
            const aiData = await aiRes.json();
            const insights = aiData.ai_insights;
            
            document.getElementById('ai-loading').style.display = "none";
            
            if (insights.error) {
                document.getElementById('ai-attribution').querySelector('.ai-text').innerText = insights.error;
            } else {
                // Source Attribution
                document.getElementById('ai-attribution').querySelector('.ai-text').innerText = insights.source_attribution?.summary || "No data.";
                document.getElementById('ai-confidence').innerText = `AI Confidence: ${insights.source_attribution?.confidence || "N/A"}`;
                
                // Hyperlocal Forecast
                document.getElementById('ai-forecast').querySelector('.ai-text').innerHTML = `
                    <b>Predicted PM2.5 (24h):</b> ${insights.hyperlocal_forecast?.predicted_pm25 || "--"}<br>
                    <b>RMSE vs Baseline:</b> ${insights.hyperlocal_forecast?.rmse_vs_baseline || "--"}<br>
                    <b>Trend:</b> ${insights.hyperlocal_forecast?.trend || "--"}
                `;
                
                // Enforcement Recommendations
                const actionList = document.getElementById('action-list');
                actionList.innerHTML = "";
                if(insights.enforcement_recommendations && insights.enforcement_recommendations.length > 0) {
                    insights.enforcement_recommendations.forEach(rec => {
                        let li = document.createElement('li');
                        li.className = 'ai-text';
                        li.innerHTML = `<b>[${rec.priority}] ${rec.target}:</b> ${rec.action} <br><span style="color:#10b981; font-size:0.85rem;">Estimated Impact: ${rec.estimated_impact}</span>`;
                        actionList.appendChild(li);
                    });
                } else {
                    actionList.innerHTML = '<li class="ai-text">No immediate interventions required.</li>';
                }
                
                // Citizen Advisory - Load into variables and set current UI state
                currentAdvisoryData.english = insights.citizen_advisory?.english || "No advisory available.";
                currentAdvisoryData.local = insights.citizen_advisory?.local_language || "No local advisory available.";

                const langSelect = document.getElementById('advisory-lang-select');
                const advisoryText = document.getElementById('ai-advisory-text');

                if (langSelect.value === 'english') {
                    advisoryText.innerText = currentAdvisoryData.english;
                    advisoryText.style.color = "#e2e8f0";
                    advisoryText.style.fontStyle = "normal";
                } else {
                    advisoryText.innerText = currentAdvisoryData.local;
                    advisoryText.style.color = "#a78bfa";
                    advisoryText.style.fontStyle = "italic";
                }
            }
        }

    } catch (error) {
        console.error("Error fetching data:", error);
        alert("Failed to connect to the backend API. Is FastAPI running on port 8000?");
    } finally {
        document.getElementById('refresh-btn').innerText = "Generate Interventions";
        document.getElementById('ai-loading').style.display = "none";
    }
}

// Event Listeners
document.getElementById('refresh-btn').addEventListener('click', fetchData);
document.getElementById('city-select').addEventListener('change', fetchData);

// Language Toggle Listener
document.getElementById('advisory-lang-select').addEventListener('change', (e) => {
    const advisoryText = document.getElementById('ai-advisory-text');
    
    if (e.target.value === 'english') {
        advisoryText.innerText = currentAdvisoryData.english;
        advisoryText.style.color = "#e2e8f0";
        advisoryText.style.fontStyle = "normal";
    } else {
        advisoryText.innerText = currentAdvisoryData.local;
        advisoryText.style.color = "#a78bfa";
        advisoryText.style.fontStyle = "italic";
    }
});

// Init
window.onload = () => {
    initMap();
    fetchData(); // Load initial data
};
