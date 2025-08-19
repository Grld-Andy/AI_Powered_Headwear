import googlemaps
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from datetime import datetime
from typing import Dict, Tuple, List
import os
import geocoder
from dotenv import load_dotenv
load_dotenv()

# Initialize Google Maps and Nominatim
GOOGLE_MAPS_API = os.getenv("GOOGLE_MAPS_API")
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API)
geolocator = Nominatim(user_agent="geoapi")


# 1. Get current coordinates (stub)
def get_current_coordinates() -> Dict[str, float]:
    g = geocoder.ip('me')
    # return {'lat': g.latlng[0], 'lng': g.latlng[1]}
    return {'lat': 5.304704, 'lng': -2.002229}


# 2. Reverse geocode to get city and country
def get_location_info(lat: float, lng: float) -> Tuple[str, str]:
    result = gmaps.reverse_geocode((lat, lng))
    city, country = "Unknown City", "Unknown Country"

    if result:
        for component in result[0]['address_components']:
            if 'locality' in component['types']:
                city = component['long_name']
            elif 'country' in component['types']:
                country = component['long_name']
    return city, country


# 3. Get driving directions from origin to destination
def get_directions(origin: Tuple[float, float], destination: Tuple[float, float]) -> List[str]:
    directions_result = gmaps.directions(origin, destination, mode="driving", departure_time="now")
    steps = []

    if directions_result:
        for step in directions_result[0]['legs'][0]['steps']:
            steps.append(step['html_instructions'])

    return steps


# 4. Geocode an address (text to coordinates)
def geocode_address(address: str) -> Tuple[float, float]:
    location = geolocator.geocode(address)
    return (location.latitude, location.longitude) if location else (0.0, 0.0)


# 5. Reverse geocode coordinates to address
def reverse_geocode_coordinates(lat: float, lng: float) -> str:
    location = geolocator.reverse((lat, lng), language='en')
    return location.address if location else "Unknown address"


# 6. Calculate distance between two coordinates
def calculate_distance_km(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    return geodesic(coord1, coord2).kilometers


# --------------------------
# Example Usage
# --------------------------

# # Step 1: Get current location and save
# current_coords = get_current_coordinates()
# print(current_coords)
# lat, lng = current_coords['lat'], current_coords['lng']
# print("Saved Coordinates:", {"lat": lat, "lng": lng})

# # Step 2: Get readable location
# city, country = get_location_info(lat, lng)
# print(f"You are in {city}, {country}")

# # Step 3: Simulate saved location and get directions
# saved_location = {'lat': 5.5600, 'lng': -0.2050}
# directions = get_directions((current_coords['lat'], current_coords['lng']),
#                             (saved_location['lat'], saved_location['lng']))
# print("Directions:")
# for d in directions:
#     print(d)

# # Step 4: Geocode an address
# address_coords = geocode_address("University of Mines and Technology, Ghana")
# print("UMaT Coordinates:", address_coords)

# # Step 5: Reverse geocode another location
# print("Location Address:", reverse_geocode_coordinates(5.6037, -0.1870))

# # Step 6: Calculate distance
# accra = (5.6037, -0.1870)
# umat = (5.3030, -1.9894)
# print(f"Distance Accra <-> UMaT: {calculate_distance_km(accra, umat):.2f} km")
