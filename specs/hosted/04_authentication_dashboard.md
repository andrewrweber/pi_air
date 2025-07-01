# Stage 4: Authentication & Web Dashboard

## Overview
Extend the existing Pi Air Monitor dashboard with authentication and multi-device support while maintaining the current UI design and user experience.

## Goals
- Add authentication layer to existing dashboard
- Implement device selector dropdown
- Create "All Devices" view
- Maintain existing UI/UX
- Keep backward compatibility

## Authentication Implementation

### 1. Supabase Auth Integration (`static/js/auth.js`)

```javascript
// Authentication module
const Auth = {
    supabase: null,
    
    init(supabaseUrl, supabaseAnonKey) {
        this.supabase = window.supabase.createClient(supabaseUrl, supabaseAnonKey);
        this.checkSession();
    },
    
    async checkSession() {
        const { data: { session } } = await this.supabase.auth.getSession();
        if (session) {
            this.onAuthenticated(session);
        } else {
            this.showLoginForm();
        }
    },
    
    async signIn(email, password) {
        const { data, error } = await this.supabase.auth.signInWithPassword({
            email,
            password
        });
        
        if (error) {
            this.showError(error.message);
        } else {
            this.hideLoginForm();
            this.onAuthenticated(data.session);
        }
    },
    
    async signUp(email, password) {
        const { data, error } = await this.supabase.auth.signUp({
            email,
            password
        });
        
        if (error) {
            this.showError(error.message);
        } else {
            this.showMessage('Check your email for verification');
        }
    },
    
    async signOut() {
        await this.supabase.auth.signOut();
        location.reload();
    },
    
    onAuthenticated(session) {
        // Store session
        window.currentSession = session;
        
        // Load user devices
        DeviceManager.loadDevices();
        
        // Show logout button
        document.getElementById('auth-controls').style.display = 'block';
    }
};
```

### 2. Login UI Overlay (`templates/auth.html`)

```html
<!-- Include this in index.html -->
<div id="auth-overlay" class="auth-overlay">
    <div class="auth-container">
        <h2>🍓 Pi Air Monitor</h2>
        <div class="auth-tabs">
            <button class="auth-tab active" onclick="showAuthTab('login')">Login</button>
            <button class="auth-tab" onclick="showAuthTab('register')">Register</button>
        </div>
        
        <form id="auth-form" onsubmit="handleAuth(event)">
            <div id="login-tab" class="auth-tab-content">
                <input type="email" id="email" placeholder="Email" required>
                <input type="password" id="password" placeholder="Password" required>
                <button type="submit">Login</button>
                <a href="#" onclick="showForgotPassword()">Forgot password?</a>
            </div>
            
            <div id="register-tab" class="auth-tab-content" style="display:none;">
                <input type="email" id="reg-email" placeholder="Email" required>
                <input type="password" id="reg-password" placeholder="Password" required>
                <input type="password" id="reg-confirm" placeholder="Confirm Password" required>
                <button type="submit">Register</button>
            </div>
        </form>
        
        <div id="auth-message" class="auth-message"></div>
    </div>
</div>

<style>
/* Match existing Pi Air Monitor styling */
.auth-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.auth-container {
    background: #1a1a1a;
    border-radius: 10px;
    padding: 2rem;
    width: 90%;
    max-width: 400px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.auth-container h2 {
    color: #c41e3a;
    text-align: center;
    margin-bottom: 1.5rem;
}

.auth-tabs {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.auth-tab {
    flex: 1;
    padding: 0.5rem;
    background: #2a2a2a;
    border: none;
    color: #fff;
    cursor: pointer;
    border-radius: 5px;
}

.auth-tab.active {
    background: #c41e3a;
}

.auth-container input {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    color: #fff;
    border-radius: 5px;
}

.auth-container button[type="submit"] {
    width: 100%;
    padding: 0.75rem;
    background: #27ae60;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
}
</style>
```

## Multi-Device Dashboard Extensions

### 1. Device Selector Component (`static/js/device-selector.js`)

```javascript
const DeviceSelector = {
    devices: [],
    currentDevice: null,
    
    init() {
        // Add device selector to header
        const header = document.querySelector('h1');
        header.innerHTML += `
            <div class="device-selector">
                <select id="device-dropdown" onchange="DeviceSelector.switchDevice(this.value)">
                    <option value="">Loading devices...</option>
                </select>
            </div>
        `;
    },
    
    async loadDevices() {
        try {
            const response = await fetch('/api/v1/user/devices', {
                headers: {
                    'Authorization': `Bearer ${window.currentSession.access_token}`
                }
            });
            
            const data = await response.json();
            this.devices = data.devices;
            this.updateDropdown();
            
            // Select default device
            const defaultDevice = data.default_device_id || this.devices[0]?.id;
            if (defaultDevice) {
                this.switchDevice(defaultDevice);
            }
        } catch (error) {
            console.error('Failed to load devices:', error);
        }
    },
    
    updateDropdown() {
        const dropdown = document.getElementById('device-dropdown');
        dropdown.innerHTML = `
            <option value="all">All Devices</option>
            ${this.devices.map(device => `
                <option value="${device.id}">
                    ${device.icon || '📍'} ${device.name} - ${device.current_aqi ? `AQI: ${device.current_aqi}` : 'Offline'}
                </option>
            `).join('')}
        `;
    },
    
    switchDevice(deviceId) {
        if (deviceId === 'all') {
            this.showAllDevices();
        } else {
            this.showSingleDevice(deviceId);
        }
    },
    
    showSingleDevice(deviceId) {
        this.currentDevice = this.devices.find(d => d.id === deviceId);
        
        // Update existing dashboard to show this device's data
        window.currentDeviceId = deviceId;
        
        // Refresh charts and stats
        updateAirQualityDisplay();
        updateSystemStats();
    },
    
    showAllDevices() {
        // Show all devices tab
        showTab('all-devices');
        this.renderAllDevicesGrid();
    }
};
```

### 2. All Devices View (`static/js/all-devices.js`)

```javascript
const AllDevicesView = {
    render() {
        const container = document.getElementById('all-devices-grid');
        container.innerHTML = DeviceSelector.devices.map(device => `
            <div class="device-card" onclick="DeviceSelector.switchDevice('${device.id}')">
                <div class="device-header">
                    <span class="device-icon">${device.icon || '📍'}</span>
                    <h3>${device.name}</h3>
                    <span class="device-status ${device.status}">${device.status}</span>
                </div>
                
                <div class="aqi-display" style="background-color: ${getAQIColor(device.current_aqi)}">
                    <div class="aqi-value">${device.current_aqi || '--'}</div>
                    <div class="aqi-label">AQI</div>
                </div>
                
                <div class="device-stats">
                    <div class="stat">
                        <span class="label">PM2.5</span>
                        <span class="value">${device.current_pm25 || '--'} µg/m³</span>
                    </div>
                    <div class="stat">
                        <span class="label">Temperature</span>
                        <span class="value">${device.temperature || '--'}°C</span>
                    </div>
                </div>
                
                <div class="device-footer">
                    <span class="last-update">Updated ${formatTimeAgo(device.last_reading)}</span>
                </div>
            </div>
        `).join('');
    }
};
```

### 3. Updated index.html Structure

```html
<!-- Add to existing tab structure -->
<div class="tab-buttons">
    <button class="tab-button active" onclick="showTab('air-quality')">Air Quality</button>
    <button class="tab-button" onclick="showTab('hardware')">Hardware</button>
    <button class="tab-button" onclick="showTab('all-devices')" id="all-devices-tab" style="display:none;">All Devices</button>
</div>

<!-- Add new tab content -->
<div class="tab-content" id="all-devices" style="display: none;">
    <h2>All Devices Overview</h2>
    <div class="devices-controls">
        <button onclick="AllDevicesView.toggleView()">Switch View</button>
        <select onchange="AllDevicesView.sortBy(this.value)">
            <option value="name">Sort by Name</option>
            <option value="aqi">Sort by AQI</option>
            <option value="updated">Sort by Last Update</option>
        </select>
    </div>
    <div id="all-devices-grid" class="devices-grid"></div>
</div>

<!-- Auth controls in header -->
<div id="auth-controls" class="auth-controls" style="display:none;">
    <span id="user-email"></span>
    <button onclick="Auth.signOut()">Logout</button>
</div>
```

### 4. API Integration Updates

```javascript
// Modify existing API calls to include device ID
async function fetchAirQualityData() {
    const deviceId = window.currentDeviceId || 'local';
    
    if (deviceId === 'local') {
        // Existing local API call
        return fetch('/api/air-quality');
    } else {
        // Cloud API call
        return fetch(`/api/v1/device/${deviceId}/readings`, {
            headers: {
                'Authorization': `Bearer ${window.currentSession.access_token}`
            }
        });
    }
}
```

## Styling Updates

```css
/* Add to existing style.css */

/* Device Selector */
.device-selector {
    display: inline-block;
    margin-left: 2rem;
}

.device-selector select {
    background: #2a2a2a;
    color: #fff;
    border: 1px solid #3a3a3a;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    font-size: 0.9rem;
}

/* All Devices Grid */
.devices-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 1.5rem;
}

.device-card {
    background: #2a2a2a;
    border-radius: 10px;
    padding: 1.5rem;
    cursor: pointer;
    transition: transform 0.2s;
}

.device-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.device-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.device-icon {
    font-size: 1.5rem;
}

.device-status {
    margin-left: auto;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
}

.device-status.online {
    background: #27ae60;
}

.device-status.offline {
    background: #e74c3c;
}

/* Auth Controls */
.auth-controls {
    position: absolute;
    top: 1rem;
    right: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}

.auth-controls button {
    background: #e74c3c;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
}
```

## Testing Requirements

### Unit Tests
- [ ] Test authentication flow
- [ ] Test device switching
- [ ] Test API token handling
- [ ] Test session persistence

### Integration Tests
- [ ] Login and view devices
- [ ] Switch between devices
- [ ] View all devices grid
- [ ] Logout and session cleanup

### UI/UX Tests
- [ ] Authentication overlay styling
- [ ] Device selector functionality
- [ ] All devices view layout
- [ ] Mobile responsiveness

## Success Criteria
- [ ] Users can login/register
- [ ] Device selector shows all user devices
- [ ] Switching devices updates dashboard
- [ ] All devices view shows grid
- [ ] Existing UI remains unchanged
- [ ] Mobile experience works well

## Next Stage
Once authentication and multi-device dashboard are complete, proceed to Stage 5: Enhanced Features.