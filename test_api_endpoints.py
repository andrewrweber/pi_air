#!/usr/bin/env python3
"""
API Endpoint Test Script for Pi Air Monitor
Tests all API endpoints to ensure they're working correctly.
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://pi-air.local:5000"
TIMEOUT = 10  # seconds

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.tests_passed = 0
        self.tests_failed = 0
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_endpoint(self, endpoint: str, test_name: str, 
                     expected_keys: list = None, 
                     validate_func: callable = None) -> bool:
        """Test a single API endpoint"""
        url = f"{self.base_url}{endpoint}"
        self.log(f"Testing {test_name}: {endpoint}")
        
        try:
            response = self.session.get(url)
            
            # Check HTTP status
            if response.status_code != 200:
                self.log(f"❌ {test_name} failed: HTTP {response.status_code}", "ERROR")
                self.tests_failed += 1
                return False
                
            # Check if response is valid JSON
            try:
                data = response.json()
            except json.JSONDecodeError:
                self.log(f"❌ {test_name} failed: Invalid JSON response", "ERROR")
                self.tests_failed += 1
                return False
                
            # Check for expected keys
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    self.log(f"❌ {test_name} failed: Missing keys {missing_keys}", "ERROR")
                    self.tests_failed += 1
                    return False
                    
            # Run custom validation
            if validate_func:
                validation_result = validate_func(data)
                if not validation_result:
                    self.log(f"❌ {test_name} failed: Custom validation failed", "ERROR")
                    self.tests_failed += 1
                    return False
                    
            self.log(f"✅ {test_name} passed")
            self.tests_passed += 1
            return True
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ {test_name} failed: Network error - {e}", "ERROR")
            self.tests_failed += 1
            return False
            
    def validate_system_info(self, data: Dict[str, Any]) -> bool:
        """Validate system info response"""
        required_fields = ['platform', 'hostname', 'cpu_usage', 'memory_percentage']
        for field in required_fields:
            if field not in data:
                self.log(f"Missing required field: {field}", "ERROR")
                return False
                
        # Check that percentages are reasonable
        if 'cpu_usage' in data:
            cpu_str = data['cpu_usage'].rstrip('%')
            try:
                cpu_val = float(cpu_str)
                if not (0 <= cpu_val <= 100):
                    self.log(f"Invalid CPU usage: {cpu_val}%", "ERROR")
                    return False
            except ValueError:
                self.log(f"Invalid CPU usage format: {data['cpu_usage']}", "ERROR")
                return False
                
        return True
        
    def validate_stats(self, data: Dict[str, Any]) -> bool:
        """Validate real-time stats response"""
        required_fields = ['cpu_percent', 'memory_percent', 'timestamp']
        for field in required_fields:
            if field not in data:
                self.log(f"Missing required field: {field}", "ERROR")
                return False
                
        # Validate percentage ranges
        if not (0 <= data['cpu_percent'] <= 100):
            self.log(f"Invalid CPU percent: {data['cpu_percent']}", "ERROR")
            return False
            
        if not (0 <= data['memory_percent'] <= 100):
            self.log(f"Invalid memory percent: {data['memory_percent']}", "ERROR")
            return False
            
        # Check timestamp format
        try:
            datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        except ValueError:
            self.log(f"Invalid timestamp format: {data['timestamp']}", "ERROR")
            return False
            
        return True
        
    def validate_air_quality_latest(self, data: Dict[str, Any]) -> bool:
        """Validate air quality latest response"""
        if 'latest_reading' not in data:
            self.log("Missing latest_reading field", "ERROR")
            return False
            
        reading = data['latest_reading']
        if reading is None:
            self.log("No air quality data available (this is OK for testing)", "WARN")
            return True
            
        required_fields = ['pm1_0', 'pm2_5', 'pm10', 'aqi', 'timestamp']
        for field in required_fields:
            if field not in reading:
                self.log(f"Missing air quality field: {field}", "ERROR")
                return False
                
        # Validate AQI range
        if reading['aqi'] is not None and not (0 <= reading['aqi'] <= 500):
            self.log(f"Invalid AQI value: {reading['aqi']}", "ERROR")
            return False
            
        return True
        
    def validate_air_quality_worst(self, data: Dict[str, Any]) -> bool:
        """Validate worst air quality response"""
        if 'worst_reading' not in data:
            self.log("Missing worst_reading field", "ERROR")
            return False
            
        reading = data['worst_reading']
        if reading is None:
            self.log("No worst air quality data available (this is OK for testing)", "WARN")
            return True
            
        required_fields = ['pm1_0', 'pm2_5', 'pm10', 'aqi', 'timestamp']
        for field in required_fields:
            if field not in reading:
                self.log(f"Missing worst air quality field: {field}", "ERROR")
                return False
                
        return True
        
    def validate_air_quality_history(self, data: Dict[str, Any]) -> bool:
        """Validate air quality history response"""
        required_fields = ['interval_averages', 'stats', 'time_range']
        for field in required_fields:
            if field not in data:
                self.log(f"Missing field: {field}", "ERROR")
                return False
                
        # Check time_range is valid
        if data['time_range'] not in ['1h', '6h', '24h']:
            self.log(f"Invalid time_range: {data['time_range']}", "ERROR")
            return False
            
        return True
        
    def validate_temperature_history(self, data: Dict[str, Any]) -> bool:
        """Validate temperature history response"""
        required_fields = ['real_time_history', 'database_history']
        for field in required_fields:
            if field not in data:
                self.log(f"Missing field: {field}", "ERROR")
                return False
                
        # Check that histories are lists
        if not isinstance(data['real_time_history'], list):
            self.log("real_time_history is not a list", "ERROR")
            return False
            
        if not isinstance(data['database_history'], list):
            self.log("database_history is not a list", "ERROR")
            return False
            
        return True
        
    def validate_system_history(self, data: Dict[str, Any]) -> bool:
        """Validate system history response"""
        required_fields = ['hourly_averages', 'latest_reading']
        for field in required_fields:
            if field not in data:
                self.log(f"Missing field: {field}", "ERROR")
                return False
                
        if not isinstance(data['hourly_averages'], list):
            self.log("hourly_averages is not a list", "ERROR")
            return False
            
        return True
        
    def run_all_tests(self):
        """Run all API endpoint tests"""
        self.log("Starting API endpoint tests...")
        self.log(f"Target server: {self.base_url}")
        
        # Test basic connectivity
        try:
            response = self.session.get(self.base_url, timeout=5)
            if response.status_code == 200:
                self.log("✅ Server is reachable")
            else:
                self.log(f"⚠️  Server returned HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Cannot reach server: {e}", "ERROR")
            return False
            
        # Test all endpoints
        tests = [
            ("/api/system", "System Information", None, self.validate_system_info),
            ("/api/stats", "Real-time Stats", None, self.validate_stats),
            ("/api/air-quality-latest", "Air Quality Latest", None, self.validate_air_quality_latest),
            ("/api/air-quality-worst-24h", "Worst Air Quality 24h", None, self.validate_air_quality_worst),
            ("/api/air-quality-history", "Air Quality History (24h)", None, self.validate_air_quality_history),
            ("/api/air-quality-history?range=1h", "Air Quality History (1h)", None, self.validate_air_quality_history),
            ("/api/air-quality-history?range=6h", "Air Quality History (6h)", None, self.validate_air_quality_history),
            ("/api/temperature-history", "Temperature History", None, self.validate_temperature_history),
            ("/api/system-history", "System History", None, self.validate_system_history),
        ]
        
        for endpoint, name, keys, validator in tests:
            self.test_endpoint(endpoint, name, keys, validator)
            
        # Summary
        total_tests = self.tests_passed + self.tests_failed
        self.log(f"\n=== TEST SUMMARY ===")
        self.log(f"Total tests: {total_tests}")
        self.log(f"Passed: {self.tests_passed}")
        self.log(f"Failed: {self.tests_failed}")
        
        if self.tests_failed == 0:
            self.log("🎉 All tests passed!")
            return True
        else:
            self.log(f"❌ {self.tests_failed} test(s) failed")
            return False

def main():
    """Main function"""
    print("Pi Air Monitor API Test Suite")
    print("=" * 40)
    
    tester = APITester(BASE_URL)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()