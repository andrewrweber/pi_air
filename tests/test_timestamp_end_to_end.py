"""
End-to-end tests for timestamp handling
Tests the complete flow from backend storage to frontend display
"""

import unittest
import json
from datetime import datetime, timezone, timedelta
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.timestamp_utils import TimestampUtils


class TestTimestampEndToEnd(unittest.TestCase):
    """Test cases for end-to-end timestamp handling"""

    def test_backend_to_frontend_timestamp_flow(self):
        """Test complete timestamp flow from backend to frontend"""
        
        # Step 1: Backend generates UTC timestamp for API response
        backend_timestamp = TimestampUtils.utc_now_iso()
        
        # Step 2: Verify backend timestamp format
        self.assertTrue(backend_timestamp.endswith('Z'))
        self.assertIn('T', backend_timestamp)
        
        # Step 3: Simulate frontend parsing (what JavaScript would do)
        # Frontend adds 'Z' if not present and creates Date object
        frontend_timestamp = backend_timestamp if backend_timestamp.endswith('Z') else backend_timestamp + 'Z'
        
        # Step 4: Verify frontend can parse to same UTC time
        parsed_backend = TimestampUtils.parse_to_utc(frontend_timestamp)
        original_backend = TimestampUtils.parse_to_utc(backend_timestamp)
        
        self.assertEqual(parsed_backend, original_backend)

    def test_database_to_api_timestamp_consistency(self):
        """Test that database timestamps work consistently in API responses"""
        
        # Simulate database storage (SQLite CURRENT_TIMESTAMP format)
        sqlite_timestamp = "2025-06-30 15:30:45"
        
        # Backend parses database timestamp
        parsed_db = TimestampUtils.parse_to_utc(sqlite_timestamp)
        
        # Backend converts to API response format
        api_timestamp = parsed_db.isoformat().replace('+00:00', 'Z')
        
        # Verify API format
        self.assertTrue(api_timestamp.endswith('Z'))
        self.assertIn('T', api_timestamp)
        
        # Frontend would parse this
        frontend_parsed = TimestampUtils.parse_to_utc(api_timestamp)
        
        # Should be same time
        self.assertEqual(parsed_db, frontend_parsed)

    def test_timezone_conversion_roundtrip(self):
        """Test timezone conversion roundtrip doesn't lose data"""
        
        # Start with UTC time
        utc_time = TimestampUtils.utc_now()
        
        # Convert to Pacific Time (what frontend might do)
        pt_time = TimestampUtils.to_configured_timezone(utc_time, 'America/Los_Angeles')
        
        # Convert back to UTC (for storage or comparison)
        back_to_utc = pt_time.astimezone(timezone.utc)
        
        # Should be the same (within microsecond precision)
        self.assertEqual(
            utc_time.replace(microsecond=0),
            back_to_utc.replace(microsecond=0)
        )

    def test_cutoff_time_api_consistency(self):
        """Test that cutoff times work consistently across API calls"""
        
        # Backend generates cutoff for "last 24 hours"
        cutoff_time = TimestampUtils.get_utc_cutoff_time(24)
        cutoff_iso = TimestampUtils.get_utc_cutoff_iso(24)
        
        # Both should represent the same time
        parsed_cutoff = TimestampUtils.parse_to_utc(cutoff_iso)
        
        # Should be equivalent (within second precision)
        self.assertAlmostEqual(
            cutoff_time.timestamp(),
            parsed_cutoff.timestamp(),
            delta=1
        )
        
        # Frontend could use either format
        now = TimestampUtils.utc_now()
        
        # Both should be 24 hours ago
        self.assertAlmostEqual(
            (now - cutoff_time).total_seconds(),
            24 * 3600,
            delta=10
        )
        self.assertAlmostEqual(
            (now - parsed_cutoff).total_seconds(),
            24 * 3600,
            delta=10
        )

    def test_api_response_json_serialization(self):
        """Test that timestamps serialize properly in JSON API responses"""
        
        # Simulate API response data
        api_data = {
            'timestamp': TimestampUtils.utc_now_iso(),
            'readings': [
                {
                    'timestamp': TimestampUtils.utc_now_iso(),
                    'pm2_5': 15.0,
                    'aqi': 50
                }
            ]
        }
        
        # Serialize to JSON (what Flask would do)
        json_string = json.dumps(api_data)
        
        # Deserialize (what frontend would do)
        parsed_data = json.loads(json_string)
        
        # Verify timestamps are still valid
        main_timestamp = TimestampUtils.parse_to_utc(parsed_data['timestamp'])
        self.assertTrue(TimestampUtils.is_timezone_aware(main_timestamp))
        
        reading_timestamp = TimestampUtils.parse_to_utc(parsed_data['readings'][0]['timestamp'])
        self.assertTrue(TimestampUtils.is_timezone_aware(reading_timestamp))

    def test_forecast_timestamp_consistency(self):
        """Test forecast timestamp handling end-to-end"""
        
        # Simulate Open-Meteo API response (UTC without timezone indicator)
        openmeteo_time = "2025-06-30T15:30"
        
        # Backend parses this (forecast service)
        parsed_forecast = TimestampUtils.parse_to_utc(openmeteo_time)
        
        # Backend stores in database
        stored_time = parsed_forecast.isoformat().replace('+00:00', 'Z')
        
        # Backend serves via API
        api_response_time = stored_time
        
        # Frontend parses for display
        frontend_time = TimestampUtils.parse_to_utc(api_response_time)
        
        # All should be equivalent
        self.assertEqual(parsed_forecast, frontend_time)
        
        # Should be UTC timezone-aware
        self.assertEqual(frontend_time.tzinfo, timezone.utc)

    def test_error_handling_consistency(self):
        """Test that error handling is consistent across components"""
        
        invalid_timestamps = [
            "",
            "invalid-date",
            "2025-13-40T25:70:70Z",  # Invalid date components
            None
        ]
        
        for invalid_ts in invalid_timestamps:
            if invalid_ts is None:
                continue
                
            # Backend should raise ValueError
            with self.assertRaises(ValueError):
                TimestampUtils.parse_to_utc(invalid_ts)

    def test_different_input_formats_compatibility(self):
        """Test that different timestamp formats are handled consistently"""
        
        # Base datetime for comparison
        base_dt = datetime(2025, 6, 30, 15, 30, 45, tzinfo=timezone.utc)
        
        # Different input formats that should all parse to the same time
        formats = [
            "2025-06-30T15:30:45Z",                    # ISO with Z
            "2025-06-30T15:30:45+00:00",              # ISO with +00:00
            "2025-06-30T15:30:45.000000Z",            # ISO with microseconds
            "2025-06-30 15:30:45",                    # SQLite format
            "2025-06-30T15:30:45",                    # ISO without timezone
        ]
        
        for fmt in formats:
            parsed = TimestampUtils.parse_to_utc(fmt)
            
            # All should parse to UTC
            self.assertEqual(parsed.tzinfo, timezone.utc)
            
            # All should be the same time (within second precision for formats without seconds)
            self.assertEqual(
                parsed.replace(microsecond=0),
                base_dt.replace(microsecond=0)
            )

    def test_performance_consistency(self):
        """Test that timestamp operations perform consistently"""
        import time
        
        # Time some common operations
        start = time.time()
        
        for _ in range(100):
            # Common backend operations
            utc_now = TimestampUtils.utc_now()
            iso_string = TimestampUtils.utc_now_iso()
            parsed = TimestampUtils.parse_to_utc(iso_string)
            cutoff = TimestampUtils.get_utc_cutoff_time(24)
        
        duration = time.time() - start
        
        # Should complete reasonably quickly
        self.assertLess(duration, 1.0)  # Less than 1 second for 100 operations

    def test_daylight_saving_time_handling(self):
        """Test that DST transitions are handled correctly"""
        
        # Test both standard time and daylight time
        winter_utc = datetime(2025, 1, 15, 20, 0, 0, tzinfo=timezone.utc)  # 12 PM PST
        summer_utc = datetime(2025, 7, 15, 19, 0, 0, tzinfo=timezone.utc)  # 12 PM PDT
        
        # Convert to Pacific Time
        winter_pt = TimestampUtils.to_configured_timezone(winter_utc, 'America/Los_Angeles')
        summer_pt = TimestampUtils.to_configured_timezone(summer_utc, 'America/Los_Angeles')
        
        # Both should be 12 PM local time but different UTC offsets
        self.assertEqual(winter_pt.hour, 12)  # PST
        self.assertEqual(summer_pt.hour, 12)  # PDT
        
        # UTC offsets should be different
        winter_offset = winter_pt.utcoffset().total_seconds()
        summer_offset = summer_pt.utcoffset().total_seconds()
        
        # PST is UTC-8, PDT is UTC-7
        self.assertEqual(winter_offset, -8 * 3600)
        self.assertEqual(summer_offset, -7 * 3600)


if __name__ == '__main__':
    unittest.main()