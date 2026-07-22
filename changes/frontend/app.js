const API_BASE_URL = "http://127.0.0.1:8000";

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
    document.getElementById('ai-advisory').querySelector('.ai-text').innerText = "Waiting for AI...";
    document.getElementById('ai-advisory-local').innerText = "";

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
        
        // 1.5 Fetch Live Traffic Trend
        try {
            const trafficRes = await fetch(`${API_BASE_URL}/api/live-traffic/${city}`);
            if(trafficRes.ok) {
                const trafficData = await trafficRes.json();
                const traffic = trafficData.latest_traffic;
                const history = trafficData.traffic_history;
                
                let trendIcon = "➡️";
                if(history && history.length > 6) {
                    let past = history[6];
                    if(traffic.congestion_ratio < past.congestion_ratio - 0.1) trendIcon = "⬆️"; // Worsening
                    else if(traffic.congestion_ratio > past.congestion_ratio + 0.1) trendIcon = "⬇️"; // Improving
                }
                
                const trafficElem = document.getElementById('traffic-val');
                trafficElem.innerText = `${traffic.congestion_level} ${trendIcon}`;
                
                trafficElem.style.color = "inherit";
                if(traffic.congestion_level === "Severe") trafficElem.style.color = "#ef4444";
                if(traffic.congestion_level === "Moderate") trafficElem.style.color = "#f59e0b";
            }
        } catch(e) {
            console.log("Traffic API error or data not available yet.");
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
                    radius: radius
                }).addTo(map);
                
                // Richer Popup with real DB Risk Score
                const riskHtml = zone.category === 'industrial' ? `<br><b style="color:#ef4444;">Emission Risk: ${zone.emission_risk || 'Unknown'}</b>` : '';
                
                circle.bindPopup(`<b>${zone.name}</b><br>${zone.category.toUpperCase()} ${riskHtml}`);
                markers.push(circle);
                bounds.push([zone.latitude, zone.longitude]);
            });
        }

        // 3. Fetch Satellite Fires & Draw Heatmap/Wind Paths
        const fireRes = await fetch(`${API_BASE_URL}/api/satellite-fires`);
        if(fireRes.ok) {
            const fireData = await fireRes.json();
            
            // Generate Heatmap
            let heatData = [];
            let fireClusters = []; // We will grab a few prominent fires to act as smoke sources
            
            fireData.fires.forEach((fire, index) => {
                let intensity = (fire.brightness - 300) / 50; // Normalize intensity somewhat
                if (intensity > 1) intensity = 1;
                if (intensity < 0.2) intensity = 0.2;
                heatData.push([fire.latitude, fire.longitude, intensity]);
                
                // Save a few fires evenly spread out to act as wind path origins
                if (index % 50 === 0) {
                    fireClusters.push([fire.latitude, fire.longitude]);
                }
            });
            
            let heatLayer = L.heatLayer(heatData, {
                radius: 20,
                blur: 15,
                maxZoom: 10,
                gradient: {0.4: 'yellow', 0.7: 'orange', 1.0: 'red'}
            }).addTo(map);
            markers.push(heatLayer);
            
            // Generate Animated Wind Smoke Paths
            if (bounds.length > 0) {
                // Calculate roughly where the selected city is based on POI bounds
                let cityLat = 0, cityLng = 0;
                bounds.forEach(b => { cityLat += b[0]; cityLng += b[1]; });
                cityLat /= bounds.length;
                cityLng /= bounds.length;
                
                // Draw wind paths from the fire clusters to the city
                fireClusters.forEach(cluster => {
                    let windPath = L.polyline([cluster, [cityLat, cityLng]], {
                        color: 'rgba(255, 255, 255, 0.7)',
                        weight: 4,
                        className: 'wind-path' // This triggers the CSS animation!
                    }).addTo(map);
                    markers.push(windPath);
                });
            }
        }
        
        // 3.5 Fetch Traffic Incidents
        try {
            const incRes = await fetch(`${API_BASE_URL}/api/traffic-incidents/${city}`);
            if(incRes.ok) {
                const incData = await incRes.json();
                incData.incidents.forEach(inc => {
                    let marker = L.circleMarker([inc.latitude, inc.longitude], {
                        radius: 5,
                        fillColor: "#ef4444",
                        color: "#991b1b",
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
                
                // Citizen Advisory
                document.getElementById('ai-advisory').querySelector('.ai-text').innerText = insights.citizen_advisory?.english || "";
                document.getElementById('ai-advisory-local').innerText = insights.citizen_advisory?.local_language || "";
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

// Init
window.onload = () => {
    initMap();
    fetchData(); // Load initial data
};
