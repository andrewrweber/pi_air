# Stage 5: Enhanced Features

## Overview
Add advanced features including historical data access, data export, device management, and sharing capabilities.

## Goals
- Extend data retention beyond 24 hours
- Implement data export functionality
- Create device management interface
- Add dashboard sharing features
- Enable notifications and alerts

## Feature Implementations

### 1. Historical Data Access

#### Extended Data Retention

```sql
-- Modify data retention strategy
-- Instead of deleting after 24h, archive to separate tables

CREATE TABLE air_quality_readings_archive (
    -- Same structure as air_quality_readings
    LIKE air_quality_readings INCLUDING ALL
);

-- Archive old data instead of deleting
CREATE OR REPLACE FUNCTION archive_old_readings()
RETURNS void AS $$
BEGIN
    -- Move readings older than 24h to archive
    INSERT INTO air_quality_readings_archive
    SELECT * FROM air_quality_readings
    WHERE timestamp < NOW() - INTERVAL '24 hours';
    
    -- Keep only 24h in main table for performance
    DELETE FROM air_quality_readings
    WHERE timestamp < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;
```

#### Historical Data API

```python
@app.route('/api/v1/device/<device_id>/historical')
def get_historical_data(device_id):
    """Get historical data beyond 24h"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interval = request.args.get('interval', '1h')  # 15m, 1h, 1d
    
    # Query from archive table
    data = query_historical_data(device_id, start_date, end_date, interval)
    return jsonify(data)
```

#### Date Range Picker UI

```javascript
// Add date range picker to dashboard
const HistoricalView = {
    init() {
        // Add controls to chart sections
        const chartControls = document.querySelectorAll('.chart-controls');
        chartControls.forEach(control => {
            control.innerHTML += `
                <button onclick="HistoricalView.showDatePicker()">
                    📅 Custom Range
                </button>
            `;
        });
    },
    
    showDatePicker() {
        // Show date picker modal
        const modal = `
            <div class="modal">
                <h3>Select Date Range</h3>
                <input type="date" id="start-date" max="${new Date().toISOString().split('T')[0]}">
                <input type="date" id="end-date" max="${new Date().toISOString().split('T')[0]}">
                <button onclick="HistoricalView.loadRange()">Load Data</button>
            </div>
        `;
        showModal(modal);
    },
    
    async loadRange() {
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        
        const data = await fetch(`/api/v1/device/${currentDeviceId}/historical?start_date=${startDate}&end_date=${endDate}`);
        const readings = await data.json();
        
        // Update charts with historical data
        updateChartsWithData(readings);
    }
};
```

### 2. Data Export

#### Export Service

```python
from flask import send_file
import csv
import json
import pandas as pd
from io import BytesIO, StringIO

@app.route('/api/v1/export', methods=['POST'])
def export_data():
    """Export data in various formats"""
    data = request.json
    device_ids = data.get('device_ids', [])
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    format = data.get('format', 'csv')  # csv, json, excel
    
    # Fetch data
    readings = fetch_readings_for_export(device_ids, start_date, end_date)
    
    if format == 'csv':
        return export_as_csv(readings)
    elif format == 'json':
        return export_as_json(readings)
    elif format == 'excel':
        return export_as_excel(readings)
        
def export_as_csv(readings):
    """Export data as CSV"""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'device_name', 'pm2_5', 'pm10', 'aqi', 'temperature'])
    writer.writeheader()
    writer.writerows(readings)
    
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'air_quality_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )
    
def export_as_excel(readings):
    """Export data as Excel with multiple sheets"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Summary sheet
        df = pd.DataFrame(readings)
        df.to_excel(writer, sheet_name='Raw Data', index=False)
        
        # Daily averages sheet
        daily_avg = df.groupby([pd.to_datetime(df['timestamp']).dt.date, 'device_name']).mean()
        daily_avg.to_excel(writer, sheet_name='Daily Averages')
        
        # Statistics sheet
        stats = df.groupby('device_name').agg(['mean', 'min', 'max', 'std'])
        stats.to_excel(writer, sheet_name='Statistics')
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'air_quality_analysis_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )
```

#### Export UI

```javascript
// Export dialog
const DataExport = {
    showExportDialog() {
        const dialog = `
            <div class="export-dialog">
                <h3>Export Data</h3>
                
                <div class="export-options">
                    <label>
                        <input type="checkbox" id="export-all-devices" onchange="DataExport.toggleDeviceSelection()">
                        All Devices
                    </label>
                    
                    <div id="device-selection" class="device-selection">
                        ${DeviceSelector.devices.map(device => `
                            <label>
                                <input type="checkbox" name="export-device" value="${device.id}">
                                ${device.name}
                            </label>
                        `).join('')}
                    </div>
                    
                    <div class="date-range">
                        <label>Start Date: <input type="date" id="export-start"></label>
                        <label>End Date: <input type="date" id="export-end"></label>
                    </div>
                    
                    <div class="format-selection">
                        <label>Format:</label>
                        <select id="export-format">
                            <option value="csv">CSV</option>
                            <option value="json">JSON</option>
                            <option value="excel">Excel</option>
                        </select>
                    </div>
                    
                    <button onclick="DataExport.performExport()">Export</button>
                </div>
            </div>
        `;
        showModal(dialog);
    },
    
    async performExport() {
        const deviceIds = Array.from(document.querySelectorAll('input[name="export-device"]:checked'))
            .map(cb => cb.value);
        
        const exportData = {
            device_ids: deviceIds,
            start_date: document.getElementById('export-start').value,
            end_date: document.getElementById('export-end').value,
            format: document.getElementById('export-format').value
        };
        
        const response = await fetch('/api/v1/export', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.currentSession.access_token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportData)
        });
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `air_quality_export.${exportData.format}`;
        a.click();
    }
};
```

### 3. Device Management

#### Management Interface

```html
<!-- Device Management Page -->
<div class="device-management">
    <h2>Device Management</h2>
    
    <div class="device-list">
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Last Seen</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="device-table-body">
                <!-- Populated by JavaScript -->
            </tbody>
        </table>
    </div>
    
    <button onclick="DeviceManagement.showAddDevice()">+ Add Device</button>
</div>
```

```javascript
const DeviceManagement = {
    async loadDevices() {
        const tbody = document.getElementById('device-table-body');
        tbody.innerHTML = DeviceSelector.devices.map(device => `
            <tr>
                <td>
                    <span class="device-icon">${device.icon}</span>
                    ${device.name}
                </td>
                <td>${device.room_type} - ${device.group_name}</td>
                <td><span class="status-badge ${device.status}">${device.status}</span></td>
                <td>${formatTimeAgo(device.last_seen)}</td>
                <td>
                    <button onclick="DeviceManagement.editDevice('${device.id}')">Edit</button>
                    <button onclick="DeviceManagement.showApiKey('${device.id}')">API Key</button>
                    <button onclick="DeviceManagement.archiveDevice('${device.id}')">Archive</button>
                </td>
            </tr>
        `).join('');
    },
    
    editDevice(deviceId) {
        const device = DeviceSelector.devices.find(d => d.id === deviceId);
        const dialog = `
            <div class="edit-device-dialog">
                <h3>Edit Device</h3>
                <form onsubmit="DeviceManagement.saveDevice(event, '${deviceId}')">
                    <input type="text" id="device-name" value="${device.name}" required>
                    <select id="device-room-type">
                        <option value="living_room" ${device.room_type === 'living_room' ? 'selected' : ''}>Living Room</option>
                        <option value="bedroom" ${device.room_type === 'bedroom' ? 'selected' : ''}>Bedroom</option>
                        <option value="kitchen" ${device.room_type === 'kitchen' ? 'selected' : ''}>Kitchen</option>
                        <option value="office" ${device.room_type === 'office' ? 'selected' : ''}>Office</option>
                    </select>
                    <input type="text" id="device-group" value="${device.group_name}">
                    <textarea id="device-description">${device.description || ''}</textarea>
                    
                    <label>
                        <input type="checkbox" id="device-default" ${device.is_default ? 'checked' : ''}>
                        Set as default device
                    </label>
                    
                    <button type="submit">Save Changes</button>
                </form>
            </div>
        `;
        showModal(dialog);
    }
};
```

### 4. Dashboard Sharing

#### Public Share Links

```python
import secrets
from datetime import datetime, timedelta

# Database table for share links
"""
CREATE TABLE share_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    user_id UUID REFERENCES auth.users(id),
    share_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

@app.route('/api/v1/share', methods=['POST'])
def create_share_link():
    """Create a public share link for a device"""
    device_id = request.json.get('device_id')
    expires_in_days = request.json.get('expires_in_days', 30)
    
    # Generate unique token
    share_token = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Save to database
    link_id = create_share_link_record(device_id, share_token, expires_at)
    
    return jsonify({
        'share_url': f"{request.host_url}share/{share_token}",
        'expires_at': expires_at.isoformat()
    })

@app.route('/share/<share_token>')
def view_shared_dashboard(share_token):
    """View a shared dashboard"""
    # Verify token and get device
    share_link = get_share_link(share_token)
    if not share_link or share_link['expires_at'] < datetime.utcnow():
        return "Share link expired or invalid", 404
        
    # Increment view count
    increment_share_view_count(share_token)
    
    # Render read-only dashboard
    return render_template('shared_dashboard.html', 
                         device_id=share_link['device_id'],
                         device_name=share_link['device_name'])
```

#### Share UI

```javascript
const Sharing = {
    showShareDialog(deviceId) {
        const dialog = `
            <div class="share-dialog">
                <h3>Share Dashboard</h3>
                
                <div class="share-options">
                    <label>
                        Expires in:
                        <select id="share-expiry">
                            <option value="1">1 day</option>
                            <option value="7">1 week</option>
                            <option value="30" selected>1 month</option>
                            <option value="365">1 year</option>
                        </select>
                    </label>
                    
                    <button onclick="Sharing.createShareLink('${deviceId}')">
                        Generate Link
                    </button>
                </div>
                
                <div id="share-link-result" style="display:none;">
                    <input type="text" id="share-link" readonly>
                    <button onclick="Sharing.copyLink()">Copy</button>
                    
                    <div class="share-qr">
                        <canvas id="qr-code"></canvas>
                    </div>
                </div>
            </div>
        `;
        showModal(dialog);
    },
    
    async createShareLink(deviceId) {
        const expiryDays = document.getElementById('share-expiry').value;
        
        const response = await fetch('/api/v1/share', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.currentSession.access_token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                device_id: deviceId,
                expires_in_days: parseInt(expiryDays)
            })
        });
        
        const data = await response.json();
        
        // Show link
        document.getElementById('share-link').value = data.share_url;
        document.getElementById('share-link-result').style.display = 'block';
        
        // Generate QR code
        new QRCode(document.getElementById('qr-code'), data.share_url);
    }
};
```

### 5. Notifications & Alerts

#### Alert Configuration

```javascript
const Alerts = {
    showAlertSettings() {
        const dialog = `
            <div class="alert-settings">
                <h3>Alert Settings</h3>
                
                ${DeviceSelector.devices.map(device => `
                    <div class="device-alerts">
                        <h4>${device.name}</h4>
                        
                        <label>
                            PM2.5 Alert (µg/m³):
                            <input type="number" id="pm25-threshold-${device.id}" 
                                   value="${device.alert_thresholds?.pm25 || 35}">
                        </label>
                        
                        <label>
                            AQI Alert:
                            <input type="number" id="aqi-threshold-${device.id}" 
                                   value="${device.alert_thresholds?.aqi || 100}">
                        </label>
                        
                        <label>
                            <input type="checkbox" id="offline-alert-${device.id}" checked>
                            Alert when device goes offline
                        </label>
                    </div>
                `).join('')}
                
                <button onclick="Alerts.saveSettings()">Save Alert Settings</button>
            </div>
        `;
        showModal(dialog);
    }
};
```

## Testing Requirements

### Feature Tests
- [ ] Historical data loads correctly
- [ ] Export generates valid files
- [ ] Device management CRUD operations
- [ ] Share links work and expire
- [ ] Alerts trigger correctly

### Performance Tests
- [ ] Large date range queries
- [ ] Export with 100k+ records
- [ ] Multiple concurrent exports
- [ ] Share link generation speed

### Security Tests
- [ ] Share links can't access other data
- [ ] Expired links are rejected
- [ ] Export respects user permissions
- [ ] API key rotation works

## Success Criteria
- [ ] Users can view data beyond 24h
- [ ] All export formats work correctly
- [ ] Device management is intuitive
- [ ] Share links are secure
- [ ] Alerts notify users promptly

## Next Steps
This completes the core hosted service implementation. Additional enhancements can be added based on user feedback and requirements.