"""
Configuration management for Pi Air Monitor
Handles location settings and API configuration
"""

import json
import os
from typing import Dict, Any, Optional

class Config:
    """Configuration manager for Pi Air Monitor"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config.json in project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, 'config.json')
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with fallback defaults"""
        default_config = {
            "location": {
                "name": "Unknown Location",
                "zipcode": None,
                "latitude": 37.7749,  # San Francisco default
                "longitude": -122.4194,
                "timezone": "America/Los_Angeles"
            },
            "forecast": {
                "enabled": True,
                "provider": "open-meteo",
                "cache_hours": 1,
                "forecast_days": 3
            },
            "apis": {
                "open_meteo": {
                    "base_url": "https://air-quality-api.open-meteo.com/v1/air-quality"
                },
                "epa_airnow": {
                    "base_url": "https://www.airnowapi.org/aq/forecast/latLong/",
                    "api_key": None,
                    "enabled": False
                }
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._deep_merge(default_config, config)
            else:
                # Create default config file
                self._save_config(default_config)
                return default_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return default_config
    
    def _deep_merge(self, default: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries, with override taking precedence"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config to {self.config_path}: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'location.latitude')"""
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the final key
        config[keys[-1]] = value
        
        # Save to file
        self._save_config(self._config)
    
    @property
    def location(self) -> Dict[str, Any]:
        """Get location configuration"""
        return self._config['location']
    
    @property
    def forecast(self) -> Dict[str, Any]:
        """Get forecast configuration"""
        return self._config['forecast']
    
    @property
    def apis(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self._config['apis']
    
    def get_coordinates(self) -> tuple[float, float]:
        """Get latitude and longitude as tuple"""
        return (
            self.get('location.latitude'),
            self.get('location.longitude')
        )
    
    def get_timezone(self) -> str:
        """Get configured timezone"""
        return self.get('location.timezone', 'America/Los_Angeles')
    
    def is_forecast_enabled(self) -> bool:
        """Check if forecast functionality is enabled"""
        return self.get('forecast.enabled', True)
    
    def get_forecast_provider(self) -> str:
        """Get configured forecast provider"""
        return self.get('forecast.provider', 'open-meteo')
    
    def get_cache_hours(self) -> int:
        """Get forecast cache duration in hours"""
        return self.get('forecast.cache_hours', 1)
    
    def get_forecast_days(self) -> int:
        """Get number of forecast days to retrieve"""
        return self.get('forecast.forecast_days', 3)

# Global configuration instance
config = Config()