import streamlit as st
import wikipedia
import requests
from datetime import date
from geopy.distance import geodesic

# Read secure keys
GOOGLE_API_KEY = st.secrets["api_keys"]["google"]
WEATHER_API_KEY = st.secrets["api_keys"]["weather"]

# Get weather
def get_weather(location):
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": WEATHER_API_KEY, "units": "metric"}
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        return f"🌡️ {temp}°C, {desc.capitalize()}"
    return "⚠️ Couldn't fetch weather."

# Wikipedia summary
def get_wiki_summary(place):
    try:
        summary = wikipedia.summary(place, sentences=5)
        url = wikipedia.page(place).url
        return summary, url
    except:
        return "No Wikipedia summary available.", ""

# Get coordinates of a place
def get_coordinates(place):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place, "key": GOOGLE_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json().get("results")
        if results:
            loc = results[0]['geometry']['location']
            return loc['lat'], loc['lng']
    return None, None

# Get nearby places
def get_places_with_distances(place, place_type):
    lat, lng = get_coordinates(place)
    station_lat, station_lng = get_nearest_railway_station_coords(place)
    if not lat or not station_lat:
        return []

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 50000,
        "type": place_type,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    results = response.json().get("results", [])
    places = []
    for p in results:
        name = p.get("name")
        address = p.get("vicinity", "")
        rating = p.get("rating", "N/A")
        loc = p.get("geometry", {}).get("location", {})
        distance = geodesic((station_lat, station_lng), (loc['lat'], loc['lng'])).km
        places.append(f"{name} ({address}) - ⭐ {rating} - 📏 {distance:.1f} km from station")
    return places

# Get nearest railway station
def get_nearest_railway_station_coords(place):
    lat, lng = get_coordinates(place)
    if lat is None:
        return None, None

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 20000,
        "keyword": "railway station",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    results = response.json().get("results", [])
    if results:
        station = results[0]['geometry']['location']
        return station['lat'], station['lng']
    return None, None

# Recommendation
def get_recommendation(place):
    return f"🌟 {place} offers a unique travel experience. Ideal for a short trip or weekend getaway!"

# How to Reach
def show_travel_info(place, user_location):
    lat, lng = get_coordinates(place)
    station_lat, station_lng = get_nearest_railway_station_coords(place)

    if not lat:
        st.error("Could not fetch travel data.")
        return

    # Airport info
    airport_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    airport_params = {
        "location": f"{lat},{lng}",
        "radius": 50000,
        "type": "airport",
        "key": GOOGLE_API_KEY
    }
    airport_resp = requests.get(airport_url, params=airport_params).json()
    airports = airport_resp.get("results", [])
    airport_name = airports[0]['name'] if airports else "Not Found"
    airport_dist = geodesic((station_lat, station_lng), (airports[0]['geometry']['location']['lat'], airports[0]['geometry']['location']['lng'])).km if airports else 0

    # Railway name (approx)
    railway_name = "Banaras" if station_lat else "Unknown"

    # Google directions
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": user_location,
        "destination": place,
        "mode": "driving",
        "key": GOOGLE_API_KEY
    }
    directions_resp = requests.get(directions_url, params=params).json()

    if directions_resp.get("routes"):
        leg = directions_resp["routes"][0]["legs"][0]
        duration = leg["duration"]["text"]
        distance = leg["distance"]["text"]
        map_link = f"https://www.google.com/maps/dir/{user_location.replace(' ', '+')}/{place.replace(' ', '+')}"

        st.markdown(f"""
✈️ **By Air:** {airport_name} - 📏 {airport_dist:.1f} km from railway station  
🚆 **By Train:** Nearest Railway Station: {railway_name}  
🚁 **By Helipad:** Check local/state helipad info.  
🛣️ **By Road:** [🗺️ Google Maps Directions]({map_link})  
🕒 Estimated Travel Time: {duration}, 📏 Distance: {distance}
        """)
    else:
        st.warning("Couldn't fetch travel time from Google Maps.")

# --- UI ---
st.set_page_config(page_title="Explore Places", layout="wide")
st.title("🌍 STAT-TECH-AI: Explore the Places across the Globe")

with st.sidebar:
    st.header("Enter a Place to Explore")
    place = st.text_input("Place", placeholder="e.g. Chikmagalur, Paris, New York...")
    selected_info = st.selectbox("Choose Information Category", [
        "Overview", "Visiting Places Around", "Famous Eateries", "Hotels to Stay", "How to Reach"
    ])

if place.strip():
    st.subheader(f"📍 Exploring: {place}")
    st.write(f"**Weather:** {get_weather(place)}")

    if selected_info == "Overview":
        summary, url = get_wiki_summary(place)
        st.markdown(f"**Overview:** {summary}")
        if url:
            st.markdown(f"[🔗 Read more on Wikipedia]({url})")
        st.info(get_recommendation(place))

    elif selected_info == "Visiting Places Around":
        st.subheader("🏛️ Attractions Nearby (from railway station)")
        for item in get_places_with_distances(place, "tourist_attraction"):
            st.write(f"- {item}")

    elif selected_info == "Famous Eateries":
        st.subheader("🍽️ Eateries (with distance from railway station)")
        for item in get_places_with_distances(place, "restaurant"):
            st.write(f"- {item}")

    elif selected_info == "Hotels to Stay":
        st.subheader("🏨 Hotels to Stay (with distance from railway station)")
        for item in get_places_with_distances(place, "lodging"):
            st.write(f"- {item}")

    elif selected_info == "How to Reach":
        user_location = st.text_input("📍 Enter Your Starting Location")
        if user_location:
            show_travel_info(place, user_location)
