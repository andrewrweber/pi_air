#!/usr/bin/env python3
"""
Test script for configuration system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config import config

def test_config():
    """Test configuration loading and access"""
    print("=== Configuration Test ===")
    
    # Test location configuration
    print(f"Location: {config.location['name']}")
    print(f"Coordinates: {config.get_coordinates()}")
    print(f"Timezone: {config.get_timezone()}")
    print(f"Zipcode: {config.get('location.zipcode')}")
    
    # Test forecast configuration
    print(f"\nForecast enabled: {config.is_forecast_enabled()}")
    print(f"Forecast provider: {config.get_forecast_provider()}")
    print(f"Forecast days: {config.get_forecast_days()}")
    print(f"Cache hours: {config.get_cache_hours()}")
    
    # Test API configuration
    print(f"\nOpen-Meteo URL: {config.get('apis.open_meteo.base_url')}")
    print(f"EPA AirNow enabled: {config.get('apis.epa_airnow.enabled')}")
    
    # Test dot notation access
    lat = config.get('location.latitude')
    lon = config.get('location.longitude')
    print(f"\nCoordinates via dot notation: {lat}, {lon}")
    
    return True

if __name__ == "__main__":
    try:
        test_config()
        print("\n✓ Configuration system working correctly!")
    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        sys.exit(1)