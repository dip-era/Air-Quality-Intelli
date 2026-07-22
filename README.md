# Air Quality Intelligence Platform 

**A Geospatial Source Attribution & Intervention Engine**

**Live Demo** [https://drive.google.com/file/d/1YPeyasHlbcL-65DB1C--nejh4v1ux3h5/view?usp=sharing](https://drive.google.com/file/d/1YPeyasHlbcL-65DB1C--nejh4v1ux3h5/view?usp=sharing)

**Live Dashboard:** [https://air-quality-intelli.onrender.com/](https://air-quality-intelli.onrender.com/)

<img width="1919" height="1079" alt="screen1" src="https://github.com/user-attachments/assets/851f1c06-f806-413d-9a1c-38e5bd73060c" />


## Overview
Current Air Quality solutions suffer from a critical flaw: they lack **Source Attribution**. A sensor reading of PM2.5 = 150 does not tell a city planner *why* the air is polluted. 

The **Air Quality Intelligence Platform** is a comprehensive, AI-driven municipal dashboard designed to transition city planners from reactive monitoring to proactive intervention. It ingests real-time data across three distinct verticals (Meteorology, Land Use, and Mobility), fuses them into a unified geospatial view, and leverages the **Groq LLaMA-3 AI engine** to deduce the exact hyper-local sources of pollution. 

The AI acts as an expert environmental scientist, automatically generating actionable, highly targeted interventions to protect vulnerable populations (schools, hospitals) and mitigate pollution sources.

##  Key Features
- **Real-Time Geospatial Map:** Interactive Leaflet map plotting live traffic incidents, industrial zones, and vulnerable populations.
- **3-Tier Data Ingestion Pipeline:** 
  - **Tier 1 (Weather):** Live API ingestion of wind, temperature, humidity, and raw particulate matter.
  - **Tier 2 (Land Use):** OpenStreetMap integration mapping schools, hospitals, and factories.
  - **Tier 3 (Mobility):** Algorithmic diurnal traffic congestion simulation.
- **AI Source Attribution:** High-speed LLaMA-3 inference via Groq to correlate wind direction with static emitters and traffic jams.
- **Actionable Interventions:** Dynamic generation of targeted municipal action plans (e.g., "Dispatch traffic police to incident #43 to reduce idling emissions near City Hospital").
- **Dark Mode UI:** A beautiful, glassmorphism-styled command center designed for long-term municipal monitoring.

##  Technology Stack
*   **Frontend:** Vanilla JavaScript, HTML5, CSS3 (Glassmorphism), Leaflet.js
*   **Backend:** Python, FastAPI
*   **Database:** Supabase (PostgreSQL)
*   **Automation:** GitHub Actions (cron jobs)
*   **AI Engine:** Groq API (LLaMA-3)
*   **Deployment:** Render.com

##  Running Locally

### Prerequisites
- Python 3.9+
- A Supabase account
- A Groq API key

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/air-quality-intelli.git
cd air-quality-intelli
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the root directory and add your keys:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
GROQ_API_KEY=your_groq_api_key
```

### 4. Run the API Server
```bash
uvicorn api:app --reload
```
The backend will start at `http://127.0.0.1:8000`. You can now open `http://127.0.0.1:8000` in your browser to view the application!

