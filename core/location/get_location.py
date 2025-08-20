#!/usr/bin/env python3
"""
Accurate Location Detection using Google Maps Geolocation API
Gets user's precise location using WiFi, cell towers, and GPS data
"""

import requests
import json
import platform
import subprocess
import sys
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()

# You need to get this from Google Cloud Console
# https://console.cloud.google.com/apis/credentials
GOOGLE_MAPS_API = os.getenv("GOOGLE_MAPS_API")

def get_wifi_networks():
    """Get nearby WiFi networks for location triangulation"""
    wifi_networks = []
    system = platform.system()
    
    try:
        if system == "Windows":
            # Use netsh on Windows
            result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Get detailed WiFi info
                result2 = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], 
                                       capture_output=True, text=True, timeout=10)
                
                # Parse WiFi data (simplified - real implementation would be more complex)
                lines = result2.stdout.split('\n')
                for line in lines:
                    if 'BSSID' in line:
                        bssid = line.split(':')[1].strip()
                        wifi_networks.append({
                            "macAddress": bssid,
                            "signalStrength": -50,  # Estimated
                            "signalToNoiseRatio": 0
                        })
        
        elif system == "Darwin":  # macOS
            # Use airport utility on macOS
            result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-s'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 6:
                            bssid = parts[1]
                            signal = int(parts[2])
                            wifi_networks.append({
                                "macAddress": bssid,
                                "signalStrength": signal,
                                "signalToNoiseRatio": 0
                            })
        
        elif system == "Linux":
            # Use iwlist on Linux
            result = subprocess.run(['iwlist', 'scan'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_network = {}
                
                for line in lines:
                    line = line.strip()
                    if 'Address:' in line:
                        bssid = line.split('Address: ')[1]
                        current_network['macAddress'] = bssid
                    elif 'Signal level=' in line:
                        signal = line.split('Signal level=')[1].split()[0]
                        current_network['signalStrength'] = int(signal)
                        current_network['signalToNoiseRatio'] = 0
                        
                        if 'macAddress' in current_network:
                            wifi_networks.append(current_network.copy())
                            current_network = {}
    
    except Exception as e:
        print(f"Warning: Could not scan WiFi networks: {e}")
    
    return wifi_networks[:10]  # Limit to 10 networks

def get_cell_towers():
    """Get nearby cell towers (simplified - requires special hardware/permissions)"""
    # This is a placeholder - getting cell tower info requires special permissions
    # and is not easily accessible on most systems
    return []

def get_location_google_api(api_key: str) -> Optional[Dict]:
    """Get location using Google Maps Geolocation API"""
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("❌ Google API key not configured!")
        print("Get your API key from: https://console.cloud.google.com/apis/credentials")
        print("Enable the 'Geolocation API' in your Google Cloud project")
        return None
    
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}"
    
    # Collect WiFi networks for better accuracy
    wifi_networks = get_wifi_networks()
    cell_towers = get_cell_towers()
    
    # Request payload
    payload = {
        "considerIp": True,  # Use IP as fallback
        "wifiAccessPoints": wifi_networks,
        "cellTowers": cell_towers
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Get additional location details using reverse geocoding
            location_details = get_address_from_coordinates(
                data['location']['lat'], 
                data['location']['lng'], 
                api_key
            )
            
            return {
                'method': 'Google Maps Geolocation API',
                'latitude': data['location']['lat'],
                'longitude': data['location']['lng'],
                'accuracy': f"{data.get('accuracy', 'Unknown')}m",
                'wifi_networks_found': len(wifi_networks),
                **location_details
            }
        else:
            print(f"API Error: {response.status_code}")
            if response.status_code == 400:
                print("Bad request - check your API key and request format")
            elif response.status_code == 403:
                print("Forbidden - check if Geolocation API is enabled")
            elif response.status_code == 429:
                print("Rate limit exceeded")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Google API request failed: {e}")
    
    return None

def get_address_from_coordinates(lat: float, lng: float, api_key: str) -> Dict:
    """Convert coordinates to address using Google Geocoding API"""
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'latlng': f"{lat},{lng}",
        'key': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['results']:
                result = data['results'][0]
                
                # Extract address components
                address_components = {}
                for component in result.get('address_components', []):
                    types = component['types']
                    if 'locality' in types:
                        address_components['city'] = component['long_name']
                    elif 'administrative_area_level_1' in types:
                        address_components['region'] = component['long_name']
                    elif 'country' in types:
                        address_components['country'] = component['long_name']
                    elif 'postal_code' in types:
                        address_components['postal'] = component['long_name']
                
                return {
                    'formatted_address': result['formatted_address'],
                    **address_components
                }
    except Exception as e:
        print(f"Geocoding failed: {e}")
    
    return {}

def load_api_key():
    """Load API key from environment variable or file"""
    # Try environment variable first
    api_key = os.getenv('GOOGLE_MAPS_API')
    if api_key:
        return api_key
    
    # Try loading from config file
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return config.get('GOOGLE_MAPS_API')
    except FileNotFoundError:
        pass
    
    return None

def create_config_file():
    """Create a config file for the API key"""
    print("\n🔧 Setting up Google Maps API key...")
    print("1. Go to: https://console.cloud.google.com/apis/credentials")
    print("2. Create a new project or select existing one")
    print("3. Enable 'Geolocation API' and 'Geocoding API'")
    print("4. Create credentials (API key)")
    print("5. Enter your API key below")
    
    api_key = input("\nEnter your Google Maps API key: ").strip()
    
    if api_key:
        config = {'GOOGLE_MAPS_API': api_key}
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
        print("✅ API key saved to config.json")
        return api_key
    
    return None

def format_location(location_data):
    """Format location data for display"""
    if not location_data:
        return "Location not available"
    
    output = f"\n📍 Location found using: {location_data['method']}\n"
    output += "=" * 60 + "\n"
    
    if location_data.get('latitude') and location_data.get('longitude'):
        output += f"🌐 Coordinates: {location_data['latitude']:.6f}, {location_data['longitude']:.6f}\n"
        output += f"🗺️  Google Maps: https://maps.google.com/?q={location_data['latitude']},{location_data['longitude']}\n"
    
    if location_data.get('formatted_address'):
        output += f"📍 Address: {location_data['formatted_address']}\n"
    
    if location_data.get('city'):
        output += f"🏙️  City: {location_data['city']}\n"
    
    if location_data.get('region'):
        output += f"🏞️  Region: {location_data['region']}\n"
    
    if location_data.get('country'):
        output += f"🌍 Country: {location_data['country']}\n"
    
    if location_data.get('postal'):
        output += f"📮 Postal Code: {location_data['postal']}\n"
    
    if location_data.get('accuracy'):
        output += f"🎯 Accuracy: {location_data['accuracy']}\n"
    
    if location_data.get('wifi_networks_found'):
        output += f"📶 WiFi Networks Used: {location_data['wifi_networks_found']}\n"
    
    return output

def main():
    """Main function to detect location"""
    print("🔍 Detecting your precise location using Google Maps API...")
    print("=" * 60)
    
    # Load API key
    api_key = load_api_key()
    
    if not api_key:
        api_key = create_config_file()
    
    if not api_key:
        print("❌ Cannot proceed without API key")
        return
    
    print("🛰️  Scanning WiFi networks for triangulation...")
    print("🌐 Querying Google Maps Geolocation API...")
    
    location = get_location_google_api(api_key)
    
    # Display results
    if location:
        print(format_location(location))
        
        # Save to file option
        save = input("\n💾 Save location to file? (y/n): ").lower().strip()
        if save == 'y':
            with open('precise_location.json', 'w') as f:
                json.dump(location, f, indent=2)
            print("📄 Location saved to precise_location.json")
    else:
        print("❌ Could not determine location")
        print("\nTroubleshooting:")
        print("- Check your Google Maps API key")
        print("- Ensure Geolocation API is enabled in Google Cloud Console")
        print("- Check your internet connection")
        print("- Make sure location services are enabled on your device")

if __name__ == "__main__":
    main()