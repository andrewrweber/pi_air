# Stage 2: Device Configuration & Registration

## Overview
Implement the configuration system that allows devices to operate in either self-hosted or cloud mode, with a setup wizard for device registration.

## Goals
- Extend existing config.py to support dual-mode operation
- Create device registration flow
- Generate and manage API keys
- Maintain backward compatibility

## Configuration Structure

### Extended config.json Format

```json
{
  "mode": "cloud|self-hosted",
  "cloud": {
    "enabled": true,
    "api_endpoint": "https://your-project.supabase.co",
    "device_id": "uuid",
    "api_key": "device-api-key",
    "device_name": "Living Room",
    "room_type": "living_room",
    "device_group": "Home",
    "sync_interval": 30,
    "batch_size": 100,
    "retry_attempts": 3,
    "offline_buffer_days": 7
  },
  "location": {
    "latitude": 37.123,
    "longitude": -122.456,
    "timezone": "America/Los_Angeles",
    "city": "Pacifica",
    "state": "CA",
    "building": "Main House",
    "floor": "1st Floor"
  },
  "monitoring": {
    "temperature_units": "celsius|fahrenheit",
    "data_retention_hours": 24
  },
  "display": {
    "icon": "couch",
    "color": "#3B82F6"
  }
}
```

## Implementation Files

### 1. Enhanced Config Module (`src/config.py`)

```python
class Config:
    """Extended configuration manager supporting cloud mode"""
    
    def __init__(self, config_path=None):
        # Existing initialization
        self.load_config()
        
    def get_mode(self) -> str:
        """Get operation mode: 'cloud' or 'self-hosted'"""
        return self.get('mode', 'self-hosted')
    
    def is_cloud_enabled(self) -> bool:
        """Check if cloud sync is enabled"""
        return self.get_mode() == 'cloud' and self.get('cloud.enabled', False)
    
    def get_cloud_config(self) -> Dict:
        """Get all cloud configuration"""
        return self.get('cloud', {})
    
    def get_device_id(self) -> Optional[str]:
        """Get device UUID"""
        return self.get('cloud.device_id')
    
    def get_api_key(self) -> Optional[str]:
        """Get device API key"""
        return self.get('cloud.api_key')
    
    def set_cloud_config(self, cloud_config: Dict):
        """Update cloud configuration"""
        self.data['cloud'] = cloud_config
        self.save()
```

### 2. Setup Wizard (`src/setup_wizard.py`)

```python
import inquirer
from typing import Dict, Optional
import requests
import uuid
from config import config

class SetupWizard:
    """Interactive setup wizard for device configuration"""
    
    def __init__(self, supabase_url: Optional[str] = None):
        self.supabase_url = supabase_url or "https://your-project.supabase.co"
        
    def run(self) -> Dict:
        """Run the interactive setup wizard"""
        # Step 1: Mode selection
        mode = self._select_mode()
        
        if mode == 'self-hosted':
            return self._configure_self_hosted()
        else:
            return self._configure_cloud()
    
    def _select_mode(self) -> str:
        """Select operation mode"""
        questions = [
            inquirer.List('mode',
                message="Select operation mode",
                choices=['self-hosted (local only)', 'cloud (with sync)'],
            ),
        ]
        answers = inquirer.prompt(questions)
        return 'self-hosted' if 'self-hosted' in answers['mode'] else 'cloud'
    
    def _configure_cloud(self) -> Dict:
        """Configure cloud mode"""
        # Step 1: Authentication
        auth_token = self._authenticate()
        
        # Step 2: Device details
        device_info = self._get_device_info()
        
        # Step 3: Register device
        device_id, api_key = self._register_device(auth_token, device_info)
        
        # Step 4: Test connection
        if self._test_connection(api_key):
            print("✓ Connection successful!")
        else:
            print("✗ Connection failed. Please check your settings.")
        
        return {
            'mode': 'cloud',
            'cloud': {
                'enabled': True,
                'api_endpoint': self.supabase_url,
                'device_id': device_id,
                'api_key': api_key,
                **device_info
            }
        }
    
    def _get_device_info(self) -> Dict:
        """Collect device information"""
        questions = [
            inquirer.Text('device_name',
                message="Device name",
                default="Living Room"
            ),
            inquirer.List('room_type',
                message="Room type",
                choices=['living_room', 'bedroom', 'kitchen', 'office', 'garage', 'outdoor', 'other']
            ),
            inquirer.Text('device_group',
                message="Device group",
                default="Home"
            ),
            inquirer.Text('description',
                message="Description (optional)",
                default=""
            ),
        ]
        return inquirer.prompt(questions)
```

### 3. Device Registration API (`src/services/device_service.py`)

```python
import requests
from typing import Tuple, Optional
import secrets
import uuid

class DeviceService:
    """Handle device registration and management"""
    
    def __init__(self, api_endpoint: str):
        self.api_endpoint = api_endpoint
        
    def register_device(self, auth_token: str, device_info: Dict) -> Tuple[str, str]:
        """
        Register a new device with the cloud service
        Returns: (device_id, api_key)
        """
        device_id = str(uuid.uuid4())
        api_key = self._generate_api_key()
        
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'id': device_id,
            'api_key': api_key,
            **device_info
        }
        
        response = requests.post(
            f"{self.api_endpoint}/rest/v1/devices",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 201:
            # Also create API key record
            self._create_api_key(auth_token, device_id, api_key)
            return device_id, api_key
        else:
            raise Exception(f"Registration failed: {response.text}")
    
    def _generate_api_key(self) -> str:
        """Generate a secure API key"""
        return f"piair_{secrets.token_urlsafe(32)}"
    
    def _create_api_key(self, auth_token: str, device_id: str, api_key: str):
        """Create API key record"""
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'key': api_key,
            'device_id': device_id,
            'is_active': True
        }
        
        requests.post(
            f"{self.api_endpoint}/rest/v1/api_keys",
            json=payload,
            headers=headers
        )
```

## Local UI Updates

### Sync Status Display (`templates/index.html`)

Add minimal sync status to existing dashboard:

```html
<!-- Add to existing header -->
<div class="sync-status" id="sync-status" style="display: none;">
    <span class="sync-icon">🔄</span>
    <span class="sync-text">Syncing...</span>
    <span class="sync-count"></span>
</div>

<style>
.sync-status {
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 0.9em;
    color: #666;
}
.sync-status.offline {
    color: #e74c3c;
}
.sync-status.syncing {
    color: #3498db;
}
.sync-status.synced {
    color: #27ae60;
}
</style>
```

## Testing Requirements

### Unit Tests
- [ ] Test config mode detection
- [ ] Test cloud configuration save/load
- [ ] Test API key generation
- [ ] Test device registration flow

### Integration Tests
- [ ] Complete setup wizard flow
- [ ] Verify device appears in database
- [ ] Test API key authentication
- [ ] Test connection verification

### User Experience Tests
- [ ] Setup wizard is intuitive
- [ ] Error messages are helpful
- [ ] Backward compatibility maintained
- [ ] Self-hosted mode unchanged

## Success Criteria
- [ ] Existing self-hosted mode works unchanged
- [ ] Setup wizard successfully registers devices
- [ ] API keys are securely generated
- [ ] Configuration persists across restarts
- [ ] Sync status appears only in cloud mode

## Next Stage
Once device configuration is working, proceed to Stage 3: Data Sync Pipeline.