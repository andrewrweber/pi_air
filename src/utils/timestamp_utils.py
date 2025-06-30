"""
Centralized timestamp handling utilities for Pi Air Monitor

This module provides consistent timezone operations across the application.
All timestamps are stored in UTC and converted for display as needed.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import re

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config


class TimestampUtils:
    """Centralized timestamp handling for consistent timezone operations"""
    
    # ISO format for database storage (always UTC)
    DB_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    
    @staticmethod
    def utc_now() -> datetime:
        """
        Always return current UTC time as timezone-aware datetime
        
        Returns:
            datetime: Current UTC time with timezone info
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def utc_now_iso() -> str:
        """
        Return current UTC timestamp as ISO string for database storage
        
        Returns:
            str: UTC timestamp in ISO format (YYYY-MM-DDTHH:MM:SS.fffffZ)
        """
        return TimestampUtils.utc_now().isoformat().replace('+00:00', 'Z')
    
    @staticmethod
    def parse_to_utc(timestamp_str: str) -> datetime:
        """
        Parse any timestamp string to UTC timezone-aware datetime
        
        Handles various input formats:
        - ISO format with 'Z' suffix (UTC)
        - ISO format with timezone offset (+HH:MM)
        - ISO format without timezone (assumed UTC)
        - SQLite CURRENT_TIMESTAMP format (assumed UTC)
        
        Args:
            timestamp_str: String representation of timestamp
            
        Returns:
            datetime: UTC timezone-aware datetime
            
        Raises:
            ValueError: If timestamp string cannot be parsed
        """
        if not timestamp_str:
            raise ValueError("Empty timestamp string")
        
        # Remove any whitespace
        timestamp_str = timestamp_str.strip()
        
        try:
            # Handle 'Z' suffix (UTC indicator)
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Handle timezone offset (+/-HH:MM)
            if '+' in timestamp_str or timestamp_str.count('-') > 2:
                return datetime.fromisoformat(timestamp_str).astimezone(timezone.utc)
            
            # Handle SQLite CURRENT_TIMESTAMP format: 'YYYY-MM-DD HH:MM:SS'
            if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', timestamp_str):
                # SQLite CURRENT_TIMESTAMP is UTC, add timezone info
                dt = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                return dt.replace(tzinfo=timezone.utc)
            
            # Handle ISO format without timezone (assume UTC)
            if 'T' in timestamp_str:
                dt = datetime.fromisoformat(timestamp_str)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            
            # Fallback: try parsing as ISO and assume UTC
            dt = datetime.fromisoformat(timestamp_str)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
            
        except ValueError as e:
            raise ValueError(f"Cannot parse timestamp '{timestamp_str}': {e}")
    
    @staticmethod
    def to_configured_timezone(utc_dt: datetime, timezone_name: Optional[str] = None) -> datetime:
        """
        Convert UTC datetime to configured timezone
        
        Args:
            utc_dt: UTC timezone-aware datetime
            timezone_name: Optional timezone name (defaults to config timezone)
            
        Returns:
            datetime: Datetime in configured timezone
        """
        if utc_dt.tzinfo is None:
            raise ValueError("Input datetime must be timezone-aware")
        
        # Get timezone from config or use provided one
        tz_name = timezone_name or config.get_timezone()
        
        try:
            # Use zoneinfo for timezone conversion (Python 3.9+)
            try:
                from zoneinfo import ZoneInfo
                target_tz = ZoneInfo(tz_name)
            except ImportError:
                # Fallback for older Python versions - use pytz if available
                try:
                    import pytz
                    target_tz = pytz.timezone(tz_name)
                except ImportError:
                    # Ultimate fallback - return UTC
                    return utc_dt
            
            return utc_dt.astimezone(target_tz)
            
        except Exception:
            # If timezone conversion fails, return UTC
            return utc_dt
    
    @staticmethod
    def format_for_display(utc_dt: datetime, timezone_name: Optional[str] = None, 
                          include_seconds: bool = False) -> str:
        """
        Format UTC datetime for user display in configured timezone
        
        Args:
            utc_dt: UTC timezone-aware datetime
            timezone_name: Optional timezone name (defaults to config timezone)
            include_seconds: Whether to include seconds in display
            
        Returns:
            str: Formatted datetime string for display
        """
        local_dt = TimestampUtils.to_configured_timezone(utc_dt, timezone_name)
        
        # Format for display
        date_str = local_dt.strftime("%m/%d/%Y")
        
        if include_seconds:
            time_str = local_dt.strftime("%H:%M:%S")
        else:
            time_str = local_dt.strftime("%H:%M")
        
        # Get timezone abbreviation
        tz_abbr = local_dt.strftime("%Z")
        if not tz_abbr:
            tz_abbr = "UTC"
        
        return f"{date_str} at {time_str} {tz_abbr}"
    
    @staticmethod
    def get_utc_cutoff_time(hours_ago: int) -> datetime:
        """
        Get UTC datetime for a time cutoff (e.g., 24 hours ago)
        
        Args:
            hours_ago: Number of hours in the past
            
        Returns:
            datetime: UTC timezone-aware datetime for cutoff
        """
        return TimestampUtils.utc_now() - timedelta(hours=hours_ago)
    
    @staticmethod
    def get_utc_cutoff_iso(hours_ago: int) -> str:
        """
        Get UTC ISO string for a time cutoff (e.g., 24 hours ago)
        
        Args:
            hours_ago: Number of hours in the past
            
        Returns:
            str: UTC ISO timestamp string for cutoff
        """
        cutoff_dt = TimestampUtils.get_utc_cutoff_time(hours_ago)
        return cutoff_dt.isoformat().replace('+00:00', 'Z')
    
    @staticmethod
    def is_timezone_aware(dt: datetime) -> bool:
        """
        Check if datetime object is timezone-aware
        
        Args:
            dt: Datetime object to check
            
        Returns:
            bool: True if timezone-aware, False if naive
        """
        return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None
    
    @staticmethod
    def ensure_utc(dt: Union[datetime, str]) -> datetime:
        """
        Ensure datetime is UTC timezone-aware
        
        Args:
            dt: Datetime object or string to convert
            
        Returns:
            datetime: UTC timezone-aware datetime
        """
        if isinstance(dt, str):
            return TimestampUtils.parse_to_utc(dt)
        
        if not TimestampUtils.is_timezone_aware(dt):
            # Assume naive datetime is already UTC
            return dt.replace(tzinfo=timezone.utc)
        
        return dt.astimezone(timezone.utc)


# Convenience functions for common operations
def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime"""
    return TimestampUtils.utc_now()

def utc_now_iso() -> str:
    """Get current UTC time as ISO string for database storage"""
    return TimestampUtils.utc_now_iso()

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to UTC datetime"""
    return TimestampUtils.parse_to_utc(timestamp_str)

def format_timestamp(utc_dt: datetime, timezone_name: Optional[str] = None) -> str:
    """Format UTC datetime for display"""
    return TimestampUtils.format_for_display(utc_dt, timezone_name)