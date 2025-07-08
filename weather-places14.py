import streamlit as st
import wikipedia
import requests
from datetime import date
from geopy.distance import geodesic

# --- Read secure keys from secrets ---
GOOGLE_API_KEY = st.secrets["api_keys"]["google"]
WEATHER_API_KEY = st.secrets["api_keys"]["weather"]

# --- Weather Info ---
def get_weather(location):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": WEATHER_API_KEY, "units": "metric"}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        data = r.json()
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        return f"🌡️ {temp} °C, {desc.capitalize()}"
    return "⚠️ Couldn't fetch weather."

# --- Wikipedia Summary ---
def get_wiki_summary(place):
    try:
        summary = wikipedia.summary(place, sentences=5)
        url = wikipedia.page(place).url
        return summary, url
    except:
        return "No Wikipedia summary available.", ""

# --- Coordinates ---
def get_coordinates(place):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place, "key": GOOGLE_API_KEY}
    r = requests.get(url, params=params)
    if r.status_code == 200:
        results = r.json().get("results")
        if results:
            loc = results[0]['geometry']['location']
            return loc['lat'], loc['lng']
    return None, None

# --- Nearest Railway Station ---
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
    r = requests.get(url, params=params)
    results = r.json().get("results", [])
    if results:
        loc = results[0]['geometry']['location']
        return loc['lat'], loc['lng']
    return None, None

# --- Places Around with Distance ---
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
    r = requests.get(url, params=params)
    results = r.json().get("results", [])
    places = []
    for p in results:
        name = p.get("name")
        address = p.get("vicinity", "")
        rating = p.get("rating", "N/A")
        loc = p.get("geometry", {}).get("location", {})
        dist = geodesic((station_lat, station_lng), (loc['lat'], loc['lng'])).km
        places.append(f"{name} ({address}) - ⭐ {rating} - 📏 {dist:.1f} km from station")
    return places

# --- Nearest Airport ---
def get_nearest_airport_info(place):
    lat, lng = get_coordinates(place)
    if lat is None:
        return "Unknown", 0.0
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 200000,
        "keyword": "international airport",
        "key": GOOGLE_API_KEY
    }
    r = requests.get(url, params=params)
    results = r.json().get("results", [])
    if not results:
        params["keyword"] = "airport"
        r = requests.get(url, params=params)
        results = r.json().get("results", [])
    nearest = None
    min_dist = float("inf")
    for airport in results:
        loc = airport["geometry"]["location"]
        dist = geodesic((lat, lng), (loc["lat"], loc["lng"])).km
        if dist < min_dist:
            min_dist = dist
            nearest = airport
    if nearest:
        return f"{nearest['name']} ({nearest.get('vicinity', '')})", min_dist
    return "Not Found", 0.0

# --- Recommendation ---
def get_recommendation(place):
    return f"🌟 {place} offers a unique travel experience. Ideal for a short trip or weekend getaway!"

# --- Travel Info ---
def show_travel_info(place, user_location):
    lat, lng = get_coordinates(place)
    station_lat, station_lng = get_nearest_railway_station_coords(place)
    if not lat:
        st.error("Could not fetch travel data.")
        return
    airport_name, airport_dist = get_nearest_airport_info(place)
    directions_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": user_location,
        "destination": place,
        "mode": "driving",
        "key": GOOGLE_API_KEY
    }
    r = requests.get(directions_url, params=params)
    directions = r.json()
    if directions.get("routes"):
        leg = directions["routes"][0]["legs"][0]
        duration = leg["duration"]["text"]
        distance = leg["distance"]["text"]
        map_link = f"https://www.google.com/maps/dir/{user_location.replace(' ', '+')}/{place.replace(' ', '+')}"
        st.markdown(f"""
✈️ **By Air:** {airport_name} - 📏 {airport_dist:.1f} km from city center  
🚆 **By Train:** Nearest Railway Station found.  
🚁 **By Helipad:** Check local/state helipad info.  
🚣 **By Road:** [🗘️ Google Maps Directions]({map_link})  
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
            st.markdown(f"[Read more on Wikipedia]({url})")
        st.info(get_recommendation(place))

    elif selected_info == "Visiting Places Around":
        st.subheader("🏩 Tourist Attractions")
        for item in get_places_with_distances(place, "tourist_attraction"):
            st.write(f"- {item}")

    elif selected_info == "Famous Eateries":
        st.subheader("🍽️ Famous Eateries")
        for item in get_places_with_distances(place, "restaurant"):
            st.write(f"- {item}")

    elif selected_info == "Hotels to Stay":
        st.subheader("🏨 Hotels to Stay")
        for item in get_places_with_distances(place, "lodging"):
            st.write(f"- {item}")

    elif selected_info == "How to Reach":
        user_location = st.text_input("📍 Your Starting Location")
        if user_location:
            show_travel_info(place, user_location)
