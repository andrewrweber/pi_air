"""
Tests for timestamp utilities
Ensures consistent timezone handling across the application
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.timestamp_utils import TimestampUtils, utc_now, utc_now_iso, parse_timestamp, format_timestamp


class TestTimestampUtils(unittest.TestCase):
    """Test cases for TimestampUtils class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_utc_dt = datetime(2025, 6, 30, 15, 30, 45, 123456, tzinfo=timezone.utc)
        self.test_iso_string = "2025-06-30T15:30:45.123456Z"
        self.test_sqlite_string = "2025-06-30 15:30:45"

    def test_utc_now_returns_timezone_aware(self):
        """Test that utc_now returns timezone-aware datetime"""
        now = TimestampUtils.utc_now()
        self.assertIsInstance(now, datetime)
        self.assertTrue(TimestampUtils.is_timezone_aware(now))
        self.assertEqual(now.tzinfo, timezone.utc)

    def test_utc_now_iso_format(self):
        """Test that utc_now_iso returns proper ISO format with Z suffix"""
        iso_string = TimestampUtils.utc_now_iso()
        self.assertIsInstance(iso_string, str)
        self.assertTrue(iso_string.endswith('Z'))
        
        # Should be parseable back to UTC datetime
        parsed = TimestampUtils.parse_to_utc(iso_string)
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_parse_to_utc_iso_with_z(self):
        """Test parsing ISO string with Z suffix"""
        result = TimestampUtils.parse_to_utc(self.test_iso_string)
        self.assertEqual(result, self.test_utc_dt)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_parse_to_utc_iso_with_offset(self):
        """Test parsing ISO string with timezone offset"""
        test_string = "2025-06-30T15:30:45.123456+00:00"
        result = TimestampUtils.parse_to_utc(test_string)
        self.assertEqual(result, self.test_utc_dt)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_parse_to_utc_iso_without_timezone(self):
        """Test parsing ISO string without timezone (assumes UTC)"""
        test_string = "2025-06-30T15:30:45.123456"
        result = TimestampUtils.parse_to_utc(test_string)
        expected = datetime(2025, 6, 30, 15, 30, 45, 123456, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_parse_to_utc_sqlite_format(self):
        """Test parsing SQLite CURRENT_TIMESTAMP format"""
        result = TimestampUtils.parse_to_utc(self.test_sqlite_string)
        expected = datetime(2025, 6, 30, 15, 30, 45, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_parse_to_utc_invalid_string(self):
        """Test parsing invalid timestamp string raises ValueError"""
        with self.assertRaises(ValueError):
            TimestampUtils.parse_to_utc("invalid-timestamp")
        
        with self.assertRaises(ValueError):
            TimestampUtils.parse_to_utc("")

    def test_parse_to_utc_with_different_timezone(self):
        """Test parsing timestamp with different timezone converts to UTC"""
        # PST is UTC-8
        pst_string = "2025-06-30T15:30:45-08:00"
        result = TimestampUtils.parse_to_utc(pst_string)
        
        # Should be converted to UTC (8 hours ahead)
        expected = datetime(2025, 6, 30, 23, 30, 45, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_to_configured_timezone_with_valid_timezone(self):
        """Test converting UTC to configured timezone"""
        # Convert to Eastern Time (UTC-5 in summer)
        result = TimestampUtils.to_configured_timezone(
            self.test_utc_dt, 
            'America/New_York'
        )
        
        # Should be timezone-aware but in Eastern timezone
        self.assertTrue(TimestampUtils.is_timezone_aware(result))
        # The UTC offset should be negative (behind UTC)
        self.assertLess(result.utcoffset().total_seconds(), 0)

    def test_to_configured_timezone_naive_datetime_raises_error(self):
        """Test that naive datetime raises ValueError"""
        naive_dt = datetime(2025, 6, 30, 15, 30, 45)
        
        with self.assertRaises(ValueError):
            TimestampUtils.to_configured_timezone(naive_dt)

    def test_format_for_display(self):
        """Test formatting UTC datetime for display"""
        result = TimestampUtils.format_for_display(
            self.test_utc_dt,
            'America/Los_Angeles'
        )
        
        self.assertIsInstance(result, str)
        self.assertIn('2025', result)  # Should contain year
        self.assertIn(':', result)     # Should contain time
        self.assertTrue(result.endswith('PDT') or result.endswith('PST'))

    def test_get_utc_cutoff_time(self):
        """Test getting UTC cutoff time"""
        cutoff = TimestampUtils.get_utc_cutoff_time(24)
        now = TimestampUtils.utc_now()
        
        self.assertTrue(TimestampUtils.is_timezone_aware(cutoff))
        self.assertEqual(cutoff.tzinfo, timezone.utc)
        self.assertLess(cutoff, now)
        
        # Should be approximately 24 hours ago
        diff = now - cutoff
        self.assertAlmostEqual(diff.total_seconds(), 24 * 3600, delta=10)

    def test_get_utc_cutoff_iso(self):
        """Test getting UTC cutoff time as ISO string"""
        cutoff_iso = TimestampUtils.get_utc_cutoff_iso(24)
        
        self.assertIsInstance(cutoff_iso, str)
        self.assertTrue(cutoff_iso.endswith('Z'))
        
        # Should be parseable
        parsed = TimestampUtils.parse_to_utc(cutoff_iso)
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_is_timezone_aware(self):
        """Test timezone awareness detection"""
        naive_dt = datetime(2025, 6, 30, 15, 30, 45)
        aware_dt = datetime(2025, 6, 30, 15, 30, 45, tzinfo=timezone.utc)
        
        self.assertFalse(TimestampUtils.is_timezone_aware(naive_dt))
        self.assertTrue(TimestampUtils.is_timezone_aware(aware_dt))

    def test_ensure_utc_with_string(self):
        """Test ensuring UTC with string input"""
        result = TimestampUtils.ensure_utc(self.test_iso_string)
        self.assertEqual(result, self.test_utc_dt)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_ensure_utc_with_naive_datetime(self):
        """Test ensuring UTC with naive datetime (assumes UTC)"""
        naive_dt = datetime(2025, 6, 30, 15, 30, 45, 123456)
        result = TimestampUtils.ensure_utc(naive_dt)
        
        expected = datetime(2025, 6, 30, 15, 30, 45, 123456, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_ensure_utc_with_aware_datetime(self):
        """Test ensuring UTC with timezone-aware datetime"""
        # Create datetime in Pacific Time
        pst_offset = timezone(timedelta(hours=-8))
        pst_dt = datetime(2025, 6, 30, 7, 30, 45, tzinfo=pst_offset)
        
        result = TimestampUtils.ensure_utc(pst_dt)
        
        # Should be converted to UTC
        expected = datetime(2025, 6, 30, 15, 30, 45, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    def test_convenience_functions(self):
        """Test convenience functions work correctly"""
        # Test utc_now convenience function
        now1 = utc_now()
        now2 = TimestampUtils.utc_now()
        self.assertAlmostEqual(
            now1.timestamp(), 
            now2.timestamp(), 
            delta=1  # Within 1 second
        )
        
        # Test utc_now_iso convenience function
        iso1 = utc_now_iso()
        iso2 = TimestampUtils.utc_now_iso()
        # Both should be valid ISO strings
        self.assertTrue(iso1.endswith('Z'))
        self.assertTrue(iso2.endswith('Z'))
        
        # Test parse_timestamp convenience function
        parsed1 = parse_timestamp(self.test_iso_string)
        parsed2 = TimestampUtils.parse_to_utc(self.test_iso_string)
        self.assertEqual(parsed1, parsed2)
        
        # Test format_timestamp convenience function
        formatted1 = format_timestamp(self.test_utc_dt)
        formatted2 = TimestampUtils.format_for_display(self.test_utc_dt)
        self.assertEqual(formatted1, formatted2)


class TestTimestampConsistency(unittest.TestCase):
    """Test cases for timestamp consistency across operations"""

    def test_roundtrip_utc_iso_parsing(self):
        """Test that ISO string can be round-tripped without loss"""
        # Start with current UTC time
        original = TimestampUtils.utc_now()
        
        # Convert to ISO string
        iso_string = original.isoformat().replace('+00:00', 'Z')
        
        # Parse back
        parsed = TimestampUtils.parse_to_utc(iso_string)
        
        # Should be equal (within microsecond precision)
        self.assertEqual(original.replace(microsecond=0), parsed.replace(microsecond=0))

    def test_database_timestamp_consistency(self):
        """Test that database-style timestamps are handled consistently"""
        # Simulate SQLite CURRENT_TIMESTAMP format
        sqlite_time = "2025-06-30 15:30:45"
        
        # Parse as UTC (SQLite CURRENT_TIMESTAMP is UTC)
        parsed = TimestampUtils.parse_to_utc(sqlite_time)
        
        # Should be UTC timezone-aware
        self.assertEqual(parsed.tzinfo, timezone.utc)
        
        # Convert back to ISO for storage
        iso_string = parsed.isoformat().replace('+00:00', 'Z')
        
        # Should be properly formatted
        self.assertTrue(iso_string.endswith('Z'))
        self.assertIn('T', iso_string)

    def test_api_response_consistency(self):
        """Test that API responses use consistent UTC timestamps"""
        # Simulate API response timestamp generation
        api_timestamp = TimestampUtils.utc_now_iso()
        
        # Should be properly formatted for JSON
        self.assertTrue(api_timestamp.endswith('Z'))
        
        # Should be parseable by frontend
        parsed = TimestampUtils.parse_to_utc(api_timestamp)
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_cutoff_time_consistency(self):
        """Test that cutoff times work consistently with database queries"""
        # Get cutoff time for 24 hours ago
        cutoff_dt = TimestampUtils.get_utc_cutoff_time(24)
        cutoff_iso = TimestampUtils.get_utc_cutoff_iso(24)
        
        # Both should represent the same time
        parsed_iso = TimestampUtils.parse_to_utc(cutoff_iso)
        
        # Should be equal (within second precision due to different creation times)
        self.assertAlmostEqual(
            cutoff_dt.timestamp(),
            parsed_iso.timestamp(),
            delta=1
        )

    def test_timezone_conversion_consistency(self):
        """Test that timezone conversions are consistent"""
        utc_time = TimestampUtils.utc_now()
        
        # Convert to Pacific Time
        pt_time = TimestampUtils.to_configured_timezone(utc_time, 'America/Los_Angeles')
        
        # Convert back to UTC
        back_to_utc = pt_time.astimezone(timezone.utc)
        
        # Should be the same as original
        self.assertEqual(utc_time.replace(microsecond=0), back_to_utc.replace(microsecond=0))


if __name__ == '__main__':
    unittest.main()