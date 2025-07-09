# logistic_route_carbon_app.py
"""Streamlit app: Logistics Route & Carbon Tracker
--------------------------------------------------
Run:
    streamlit run logistic_route_carbon_app.py

Requires:
    streamlit
    requests
    folium
    streamlit-folium
"""

import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------
CO2_PER_KM = 150   # grams CO₂ per kilometre
COST_PER_KM = 8    # ₹ per kilometre
TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
TILE_ATTR = "© OpenStreetMap • © CartoDB"
HEADERS = {"User-Agent": "streamlit-carbon-demo"}

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

def geocode(place: str):
    """Return (lat, lon) tuple using Nominatim."""
    url = (
        "https://nominatim.openstreetmap.org/search?format=json&q="
        + requests.utils.quote(place)
        + "&limit=1"
    )
    js = requests.get(url, headers=HEADERS, timeout=15).json()
    if not js:
        raise ValueError(f"Place not found: {place}")
    return float(js[0]["lat"]), float(js[0]["lon"])


def fetch_routes(start, end):
    """Return OSRM 'best' and first alternative routes."""
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        + coords
        + "?alternatives=true&overview=full&geometries=geojson"
    )
    js = requests.get(url, timeout=20).json()
    if not js.get("routes"):
        raise ValueError("No routes found from OSRM")
    routes = js["routes"]
    return routes[0], (routes[1] if len(routes) > 1 else routes[0])


def km(meters):
    return round(meters / 1000, 2)


def hmin(seconds):
    h = int(seconds // 3600)
    m = int(round((seconds % 3600) / 60))
    return f"{h} h {m} min"


def calc_metrics(distance_km):
    co2 = int(distance_km * CO2_PER_KM)
    cost = int(distance_km * COST_PER_KM)
    return co2, cost


# ------------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------------
st.set_page_config(page_title="Route & Carbon Tracker", layout="wide")

st.title("🚚 Logistics Route & Carbon Tracker")

col1, col2, col_btn = st.columns([3, 3, 1])
with col1:
    origin = st.text_input("Origin", "Uttam Nagar, Delhi")
with col2:
    destination = st.text_input("Destination", "Dwarka Sector 21, Delhi")
with col_btn:
    go = st.button("Get Routes", use_container_width=True)

if go:
    try:
        start = geocode(origin)
        end = geocode(destination)

        best, alt = fetch_routes(start, end)

        # Metrics
        best_km = km(best["distance"])
        alt_km = km(alt["distance"])
        best_co2, best_cost = calc_metrics(best_km)
        alt_co2, alt_cost = calc_metrics(alt_km)

        # Map
        m = folium.Map(location=[(start[0] + end[0]) / 2, (start[1] + end[1]) / 2], zoom_start=10, tiles=TILE_URL, attr=TILE_ATTR)

        folium.GeoJson(
            best["geometry"],
            name="Old route",
            style_function=lambda _: {
                "color": "red",
                "weight": 6,
            },
            tooltip=f"Old: {best_km} km, {hmin(best['duration'])}"
        ).add_to(m)

        folium.GeoJson(
            alt["geometry"],
            name="Optimized route",
            style_function=lambda _: {
                "color": "blue",
                "weight": 6,
                "dashArray": "6 6",
            },
            tooltip=f"Opt: {alt_km} km, {hmin(alt['duration'])}"
        ).add_to(m)

        folium.Marker(start, tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(end, tooltip="End", icon=folium.Icon(color="green", icon="flag-checkered", prefix="fa")).add_to(m)

        folium.LayerControl().add_to(m)

        st_folium(m, width=900, height=600)

        st.markdown("### 📊 Route metrics")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Old route", f"{best_km} km", help=f"{hmin(best['duration'])}")
            st.metric("CO₂", f"{best_co2} g")
            st.metric("Cost", f"₹{best_cost}")
        with c2:
            st.metric("Optimized", f"{alt_km} km", delta=f"{best_km-alt_km:+} km", help=f"{hmin(alt['duration'])}")
            st.metric("CO₂", f"{alt_co2} g", delta=f"{best_co2-alt_co2:+} g")
            st.metric("Cost", f"₹{alt_cost}", delta=f"₹{best_cost-alt_cost:+}")
        with c3:
            st.success(f"**CO₂ saved:** {best_co2-alt_co2} g")
            st.success(f"**₹ saved:** {best_cost-alt_cost}")

    except Exception as e:
        st.error(str(e))
