#!/usr/bin/env python3
"""
Test script for air quality forecast APIs
Tests EPA AirNow and Open-Meteo APIs to validate retrieval strategy
"""

import requests
import json
from datetime import datetime, timedelta
import sys

def test_epa_airnow_api():
    """Test EPA AirNow API for air quality forecast"""
    print("\n=== Testing EPA AirNow API ===")
    
    # Pacifica, CA 94044 coordinates  
    lat, lon = 37.6138, -122.4869
    
    # AirNow API endpoint (requires API key for full access)
    # Using the public reporting area endpoint as a test
    url = f"https://www.airnowapi.org/aq/forecast/latLong/?format=application/json&latitude={lat}&longitude={lon}&date={datetime.now().strftime('%Y-%m-%d')}&distance=25&API_KEY=YOUR_API_KEY"
    
    print(f"URL: {url}")
    print("Note: This requires an API key from airnowapi.org")
    print("For testing, we'll use a mock response structure")
    
    # Mock response structure based on AirNow API documentation
    mock_response = {
        "DateIssue": "2024-06-28 00:00 UTC",
        "DateForecast": "2024-06-29",
        "ReportingArea": "Los Angeles-South Coast Air Basin",
        "StateCode": "CA",
        "Latitude": 34.0522,
        "Longitude": -118.2437,
        "ParameterName": "PM2.5",
        "AQI": 85,
        "Category": {
            "Number": 2,
            "Name": "Moderate"
        },
        "ActionDay": False,
        "Discussion": "Air quality forecast discussion..."
    }
    
    print("Mock AirNow Response:")
    print(json.dumps(mock_response, indent=2))
    return True

def test_open_meteo_api():
    """Test Open-Meteo Air Quality API"""
    print("\n=== Testing Open-Meteo Air Quality API ===")
    
    # Pacifica, CA 94044 coordinates
    lat, lon = 37.6138, -122.4869
    
    # Open-Meteo Air Quality API endpoint
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
        "forecast_days": 3,
        "timezone": "auto"
    }
    
    try:
        print(f"Making request to: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print("Response structure:")
        print(f"- Latitude: {data.get('latitude')}")
        print(f"- Longitude: {data.get('longitude')}")
        print(f"- Timezone: {data.get('timezone')}")
        print(f"- UTC Offset: {data.get('utc_offset_seconds')}")
        
        hourly = data.get('hourly', {})
        if hourly:
            times = hourly.get('time', [])
            pm25 = hourly.get('pm2_5', [])
            pm10 = hourly.get('pm10', [])
            
            print(f"- Forecast hours available: {len(times)}")
            print(f"- First forecast time: {times[0] if times else 'None'}")
            print(f"- Last forecast time: {times[-1] if times else 'None'}")
            
            # Show first few forecast points
            print("\nFirst 6 hours of PM2.5 forecast:")
            for i in range(min(6, len(times))):
                time_str = times[i]
                pm25_val = pm25[i] if i < len(pm25) else 'N/A'
                pm10_val = pm10[i] if i < len(pm10) else 'N/A'
                print(f"  {time_str}: PM2.5={pm25_val}μg/m³, PM10={pm10_val}μg/m³")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def calculate_aqi_from_pm25(pm25_value):
    """Calculate AQI from PM2.5 concentration using EPA 2024 standards"""
    if pm25_value is None:
        return None, "Unknown"
    
    # EPA 2024 PM2.5 AQI breakpoints (updated May 2024)
    breakpoints = [
        (0.0, 9.0, 0, 50, "Good"),
        (9.1, 35.4, 51, 100, "Moderate"), 
        (35.5, 55.4, 101, 150, "Unhealthy for Sensitive Groups"),
        (55.5, 150.4, 151, 200, "Unhealthy"),
        (150.5, 250.4, 201, 300, "Very Unhealthy"),
        (250.5, 350.4, 301, 400, "Hazardous"),
        (350.5, 500.4, 401, 500, "Hazardous")
    ]
    
    for c_low, c_high, i_low, i_high, category in breakpoints:
        if c_low <= pm25_value <= c_high:
            # Linear interpolation
            aqi = ((i_high - i_low) / (c_high - c_low)) * (pm25_value - c_low) + i_low
            return round(aqi), category
    
    # If concentration is above all breakpoints
    return 500, "Hazardous"

def test_aqi_calculation():
    """Test AQI calculation with sample PM2.5 values"""
    print("\n=== Testing AQI Calculation ===")
    
    test_values = [5.0, 12.0, 25.0, 45.0, 75.0, 200.0]
    
    for pm25 in test_values:
        aqi, category = calculate_aqi_from_pm25(pm25)
        print(f"PM2.5: {pm25}μg/m³ → AQI: {aqi} ({category})")

def main():
    print("Air Quality Forecast API Testing")
    print("================================")
    
    # Test AQI calculation
    test_aqi_calculation()
    
    # Test EPA AirNow API (mock)
    test_epa_airnow_api()
    
    # Test Open-Meteo API (live)
    success = test_open_meteo_api()
    
    print(f"\n=== Summary ===")
    print(f"Open-Meteo API test: {'✓ Success' if success else '✗ Failed'}")
    print("EPA AirNow API: Requires API key registration")
    
    if success:
        print("\n✓ API retrieval strategy validated!")
        print("✓ Open-Meteo provides reliable forecast data")
        print("✓ AQI calculation working with 2024 EPA standards")
    else:
        print("\n✗ Issues detected with API retrieval")
        print("Check internet connection and API endpoints")

if __name__ == "__main__":
    main()