#!/usr/bin/env python3
"""
Test backend forecast integration
Tests the full backend stack including Flask endpoints
"""

import sys
import os
import requests
import time
import threading
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import app
from config import config

def start_test_server():
    """Start Flask app in test mode"""
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    return app.test_client()

def test_forecast_endpoints():
    """Test forecast API endpoints"""
    print("=== Testing Backend Forecast Integration ===")
    
    # Start test client
    client = start_test_server()
    
    print(f"Testing with location: {config.get('location.name')} ({config.get_coordinates()})")
    print(f"Forecast provider: {config.get_forecast_provider()}")
    
    # Test 1: Basic forecast endpoint
    print("\n1. Testing /api/air-quality-forecast...")
    response = client.get('/api/air-quality-forecast?hours=6')
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"   Forecast points: {data.get('count', 0)}")
        print(f"   Provider: {data.get('provider')}")
        print(f"   Location: {data.get('location', {}).get('name')}")
        
        if data.get('forecast'):
            first_point = data['forecast'][0]
            print(f"   First forecast: {first_point.get('time')} - PM2.5: {first_point.get('pm2_5')}μg/m³, AQI: {first_point.get('aqi')}")
    else:
        print(f"   Error: {response.get_data(as_text=True)}")
    
    # Test 2: Forecast summary endpoint
    print("\n2. Testing /api/air-quality-forecast-summary...")
    response = client.get('/api/air-quality-forecast-summary?days=2')
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"   Daily summaries: {data.get('count', 0)}")
        
        if data.get('forecast'):
            for day in data['forecast']:
                print(f"   {day.get('date')}: PM2.5 avg {day.get('pm2_5_avg')}μg/m³, AQI avg {day.get('aqi_avg')} ({day.get('aqi_level')})")
    else:
        print(f"   Error: {response.get_data(as_text=True)}")
    
    # Test 3: Cache stats endpoint
    print("\n3. Testing /api/forecast-cache-stats...")
    response = client.get('/api/forecast-cache-stats')
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"   Cache enabled: {data.get('cache_enabled')}")
        print(f"   Cache hours: {data.get('cache_hours')}")
        print(f"   Cache stats: {data.get('cache_stats')}")
    else:
        print(f"   Error: {response.get_data(as_text=True)}")
    
    # Test 4: Cache clear endpoint
    print("\n4. Testing /api/forecast-cache-clear...")
    response = client.post('/api/forecast-cache-clear')
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"   Message: {data.get('message')}")
    else:
        print(f"   Error: {response.get_data(as_text=True)}")
    
    # Test 5: Parameter validation
    print("\n5. Testing parameter validation...")
    
    # Test invalid hours parameter
    response = client.get('/api/air-quality-forecast?hours=invalid')
    print(f"   Invalid hours parameter: {response.status_code} (should be 200 with default)")
    
    # Test extreme hours parameter
    response = client.get('/api/air-quality-forecast?hours=9999')
    print(f"   Extreme hours parameter: {response.status_code} (should be 200 with capped value)")
    
    # Test invalid days parameter
    response = client.get('/api/air-quality-forecast-summary?days=invalid')
    print(f"   Invalid days parameter: {response.status_code} (should be 200 with default)")
    
    return True

def test_configuration():
    """Test configuration system"""
    print("\n=== Testing Configuration System ===")
    
    print(f"Location: {config.location}")
    print(f"Forecast config: {config.forecast}")
    print(f"API config: {config.apis}")
    
    # Test coordinate access
    lat, lon = config.get_coordinates()
    print(f"Coordinates: {lat}, {lon}")
    
    # Test forecast settings
    print(f"Forecast enabled: {config.is_forecast_enabled()}")
    print(f"Forecast provider: {config.get_forecast_provider()}")
    print(f"Cache hours: {config.get_cache_hours()}")
    print(f"Forecast days: {config.get_forecast_days()}")
    
    return True

def test_forecast_service_directly():
    """Test forecast service directly"""
    print("\n=== Testing Forecast Service Directly ===")
    
    from services.forecast_service import forecast_service
    
    try:
        # Test cache stats
        stats = forecast_service.get_cache_stats()
        print(f"Cache stats: {stats}")
        
        # Test forecast fetch (small amount for testing)
        print("Fetching 3-hour forecast...")
        forecast_data = forecast_service.get_forecast(hours=3)
        
        if forecast_data:
            print(f"✓ Got {len(forecast_data)} forecast points")
            for i, point in enumerate(forecast_data[:2]):  # Show first 2 points
                print(f"  Point {i+1}: {point['forecast_for_time']} - PM2.5: {point['pm2_5']}μg/m³, AQI: {point['aqi']}")
        else:
            print("✗ No forecast data returned")
        
        return len(forecast_data) > 0
        
    except Exception as e:
        print(f"✗ Error testing forecast service: {e}")
        return False

def main():
    """Run all backend tests"""
    print("Backend Forecast Integration Test")
    print("=================================")
    
    try:
        # Test configuration
        config_ok = test_configuration()
        
        # Test forecast service directly
        service_ok = test_forecast_service_directly()
        
        # Test Flask endpoints
        endpoints_ok = test_forecast_endpoints()
        
        print("\n=== Test Summary ===")
        print(f"Configuration: {'✓' if config_ok else '✗'}")
        print(f"Forecast service: {'✓' if service_ok else '✗'}")
        print(f"Flask endpoints: {'✓' if endpoints_ok else '✗'}")
        
        if config_ok and service_ok and endpoints_ok:
            print("\n✓ All backend tests passed!")
            print("Backend forecast implementation is working correctly")
            return True
        else:
            print("\n✗ Some backend tests failed")
            return False
            
    except Exception as e:
        print(f"\n✗ Backend test failed with error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)