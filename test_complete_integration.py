#!/usr/bin/env python3
"""
Complete integration test for forecast functionality
Tests both backend and frontend working together
"""

import sys
import os
import requests
import time
import threading
import webbrowser
from subprocess import Popen, PIPE
import signal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def start_flask_server():
    """Start Flask server in background"""
    print("Starting Flask server...")
    
    # Set environment variables
    env = os.environ.copy()
    env['FLASK_HOST'] = '127.0.0.1'
    env['FLASK_PORT'] = '5555'  # Use different port for testing
    env['FLASK_DEBUG'] = 'true'
    
    # Start server
    process = Popen([
        'python', 'src/app.py'
    ], env=env, stdout=PIPE, stderr=PIPE, cwd=os.getcwd())
    
    # Wait for server to start
    print("Waiting for server to start...")
    for i in range(10):
        try:
            response = requests.get('http://127.0.0.1:5555/api/stats', timeout=2)
            if response.status_code == 200:
                print("✓ Flask server started successfully")
                return process
        except:
            time.sleep(1)
    
    print("✗ Flask server failed to start")
    return None

def test_api_endpoints():
    """Test all forecast API endpoints"""
    print("\n=== Testing API Endpoints ===")
    
    base_url = 'http://127.0.0.1:5555'
    endpoints = [
        '/api/air-quality-forecast?hours=6',
        '/api/air-quality-forecast-summary?days=2',
        '/api/forecast-cache-stats',
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {
                    'status': 'SUCCESS',
                    'data_keys': list(data.keys()) if isinstance(data, dict) else 'not_dict',
                    'data_size': len(str(data))
                }
                print(f"  ✓ {endpoint} - OK ({len(str(data))} bytes)")
            else:
                results[endpoint] = {
                    'status': 'ERROR',
                    'code': response.status_code,
                    'error': response.text[:100]
                }
                print(f"  ✗ {endpoint} - HTTP {response.status_code}")
                
        except Exception as e:
            results[endpoint] = {
                'status': 'EXCEPTION',
                'error': str(e)
            }
            print(f"  ✗ {endpoint} - Exception: {e}")
    
    return results

def test_main_page():
    """Test main page loads with forecast section"""
    print("\n=== Testing Main Page ===")
    
    try:
        response = requests.get('http://127.0.0.1:5555/', timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check for forecast-related elements
            forecast_checks = [
                'air-quality-forecast-section',
                'forecast-cards',
                'forecastChart',
                'forecast.js',
                'showForecastData'
            ]
            
            missing = []
            for check in forecast_checks:
                if check not in content:
                    missing.append(check)
            
            if not missing:
                print("✓ Main page contains all forecast elements")
                return True
            else:
                print(f"✗ Main page missing: {', '.join(missing)}")
                return False
        else:
            print(f"✗ Main page HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Main page exception: {e}")
        return False

def test_cache_functionality():
    """Test forecast caching"""
    print("\n=== Testing Cache Functionality ===")
    
    base_url = 'http://127.0.0.1:5555'
    
    try:
        # Clear cache
        clear_response = requests.post(f"{base_url}/api/forecast-cache-clear", timeout=10)
        if clear_response.status_code == 200:
            print("✓ Cache cleared successfully")
        else:
            print(f"✗ Cache clear failed: HTTP {clear_response.status_code}")
            return False
        
        # Get forecast data (should populate cache)
        forecast_response = requests.get(f"{base_url}/api/air-quality-forecast?hours=6", timeout=15)
        if forecast_response.status_code == 200:
            print("✓ Forecast data fetched (cache populated)")
        else:
            print(f"✗ Forecast fetch failed: HTTP {forecast_response.status_code}")
            return False
        
        # Check cache stats
        stats_response = requests.get(f"{base_url}/api/forecast-cache-stats", timeout=10)
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            cache_stats = stats_data.get('cache_stats', {})
            
            if cache_stats and 'open-meteo' in cache_stats:
                count = cache_stats['open-meteo']['count']
                print(f"✓ Cache contains {count} forecast points")
                return True
            else:
                print("✗ Cache appears empty after forecast fetch")
                return False
        else:
            print(f"✗ Cache stats failed: HTTP {stats_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Cache test exception: {e}")
        return False

def show_browser_test():
    """Open browser for manual testing"""
    print("\n=== Manual Browser Test ===")
    print("Opening browser for manual testing...")
    print("Please check:")
    print("1. Air Quality tab shows forecast section below charts")
    print("2. 3-Day Outlook cards display correctly")
    print("3. Hourly forecast chart shows data")
    print("4. Time range buttons (12h, 24h, 48h, 72h) work")
    print("5. Forecast metadata shows correct location/provider")
    print("\nPress Enter when done testing...")
    
    try:
        webbrowser.open('http://127.0.0.1:5555/')
        input()  # Wait for user
        return True
    except Exception as e:
        print(f"Could not open browser: {e}")
        return False

def main():
    """Run complete integration test"""
    print("Complete Forecast Integration Test")
    print("==================================")
    
    # Start Flask server
    server_process = None
    try:
        server_process = start_flask_server()
        if not server_process:
            print("✗ Cannot start Flask server - aborting tests")
            return False
        
        # Run tests
        results = {}
        
        # API endpoint tests
        results['api'] = test_api_endpoints()
        
        # Main page test
        results['page'] = test_main_page()
        
        # Cache functionality test
        results['cache'] = test_cache_functionality()
        
        # Browser test
        results['browser'] = show_browser_test()
        
        # Summary
        print("\n=== Test Summary ===")
        api_success = all(r.get('status') == 'SUCCESS' for r in results['api'].values())
        print(f"API Endpoints: {'✓ PASS' if api_success else '✗ FAIL'}")
        print(f"Main Page: {'✓ PASS' if results['page'] else '✗ FAIL'}")
        print(f"Cache Functionality: {'✓ PASS' if results['cache'] else '✗ FAIL'}")
        print(f"Browser Test: {'✓ COMPLETED' if results['browser'] else '✗ SKIPPED'}")
        
        overall_success = api_success and results['page'] and results['cache']
        print(f"\nOverall: {'✓ SUCCESS' if overall_success else '✗ FAILURE'}")
        
        if overall_success:
            print("\n🎉 Forecast integration is working correctly!")
            print("Backend and frontend are properly connected.")
        else:
            print("\n❌ Some issues need to be resolved.")
        
        return overall_success
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"\nTest failed with exception: {e}")
        return False
    finally:
        # Clean up
        if server_process:
            print("\nStopping Flask server...")
            server_process.terminate()
            server_process.wait(timeout=5)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)