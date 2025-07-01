# Pi Air Monitor - Intelligent Alert System

The Pi Air Monitor includes a comprehensive alerting system that can notify you of air quality issues, system health problems, and sensor failures through multiple channels including email, webhooks, and logging.

## Features

- **Multi-Channel Notifications**: Email, webhooks (Slack, Discord, etc.), and log-based alerts
- **Configurable Thresholds**: Set custom triggers for air quality levels and system metrics
- **Rate Limiting**: Prevent alert spam with configurable rate limits
- **Alert History**: Track and review past alerts
- **Health Monitoring**: Monitor sensor connectivity and data freshness
- **Template-Based Configuration**: Quick setup with pre-configured templates

## Quick Start

### 1. Enable Alerting

Enable alerts in your `config.json`:

```json
{
  "alerts": {
    "enabled": true
  }
}
```

### 2. Use a Template (Recommended)

Apply a pre-configured template:

```bash
# For basic log-only alerts
python scripts/alert_manager.py apply basic

# For email notifications
python scripts/alert_manager.py apply email_only

# For Slack integration
python scripts/alert_manager.py apply webhook_slack

# For comprehensive alerting
python scripts/alert_manager.py apply comprehensive
```

### 3. Configure Notifications

Update the notification settings in `config.json` with your credentials:

```json
{
  "alerts": {
    "notifications": {
      "email": {
        "enabled": true,
        "recipients": ["your-email@example.com"],
        "smtp": {
          "server": "smtp.gmail.com",
          "port": 587,
          "username": "your-email@gmail.com",
          "password": "your-app-password"
        }
      }
    }
  }
}
```

### 4. Test the System

```bash
# Test all components
python scripts/alert_manager.py test

# Check status
python scripts/alert_manager.py status
```

## Configuration Reference

### Alert Rules

Alert rules define when and how alerts are triggered:

```json
{
  "type": "air_quality",
  "enabled": true,
  "severity": "warning",
  "title": "Poor Air Quality",
  "message": "AQI is {aqi}, PM2.5: {pm2_5} μg/m³",
  "condition": {
    "aqi_above": 100,
    "aqi_level_in": ["Unhealthy for Sensitive Groups"]
  }
}
```

#### Rule Types

- **`air_quality`**: Air quality threshold alerts
- **`system_health`**: System resource alerts (CPU temp, memory, etc.)
- **`sensor_failure`**: Sensor connectivity issues
- **`data_staleness`**: Old or missing data alerts

#### Condition Options

**Air Quality Conditions:**
- `aqi_above`: Trigger when AQI exceeds value
- `pm25_above`: Trigger when PM2.5 exceeds value (μg/m³)
- `pm10_above`: Trigger when PM10 exceeds value (μg/m³)
- `aqi_level_in`: Trigger when AQI level matches list

**System Health Conditions:**
- `cpu_temp_above`: CPU temperature threshold (°C)
- `cpu_usage_above`: CPU usage threshold (%)
- `memory_usage_above`: Memory usage threshold (%)
- `disk_usage_above`: Disk usage threshold (%)

#### Severity Levels

- **`info`**: Informational alerts
- **`warning`**: Warning conditions
- **`critical`**: Critical issues requiring attention
- **`emergency`**: Emergency conditions requiring immediate action

### Notification Methods

#### Email Notifications

```json
{
  "email": {
    "enabled": true,
    "recipients": [
      "primary@example.com",
      "backup@example.com"
    ],
    "smtp": {
      "server": "smtp.gmail.com",
      "port": 587,
      "use_tls": true,
      "username": "your-email@gmail.com",
      "password": "your-app-password"
    }
  }
}
```

**Gmail Setup:**
1. Enable 2-factor authentication
2. Generate an App Password
3. Use your Gmail address as username
4. Use the App Password as password

#### Webhook Notifications

```json
{
  "webhook": {
    "enabled": true,
    "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    "timeout": 10,
    "headers": {
      "Content-Type": "application/json"
    },
    "custom_fields": {
      "channel": "#alerts",
      "username": "Pi Air Monitor"
    }
  }
}
```

**Slack Setup:**
1. Create a Slack app and webhook
2. Copy the webhook URL
3. Configure custom fields for channel and username

**Discord Setup:**
```json
{
  "webhook": {
    "enabled": true,
    "url": "https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK",
    "custom_fields": {
      "username": "Pi Air Monitor",
      "avatar_url": "https://example.com/avatar.png"
    }
  }
}
```

#### Log Notifications

```json
{
  "log": {
    "enabled": true,
    "level": "info"
  }
}
```

Log notifications are always available and write to the application logs.

### Rate Limiting

Prevent alert spam with rate limits (in minutes):

```json
{
  "rate_limits": {
    "air_quality_warning": 30,
    "air_quality_critical": 15,
    "system_health_warning": 45,
    "system_health_critical": 20,
    "sensor_failure_critical": 5,
    "data_staleness_warning": 30
  }
}
```

## Command-Line Management

The `alert_manager.py` script provides command-line management:

```bash
# Show current status
python scripts/alert_manager.py status

# View recent alerts
python scripts/alert_manager.py history --limit 20

# Test the alert system
python scripts/alert_manager.py test

# Validate configuration
python scripts/alert_manager.py validate

# List available templates
python scripts/alert_manager.py templates

# Apply a configuration template
python scripts/alert_manager.py apply comprehensive
```

## API Endpoints

The alert system provides REST API endpoints:

- **GET** `/api/alerts/status` - Get alert system status and statistics
- **GET** `/api/alerts/history?limit=50` - Get alert history
- **POST** `/api/alerts/test` - Send a test alert
- **GET** `/api/alerts/test-notifications` - Test notification methods
- **POST** `/api/alerts/check-system` - Manually trigger system health check

## Configuration Templates

### Basic Template (`alerts_basic.json`)
- Log notifications only
- Essential air quality and system health alerts
- Conservative rate limiting

### Email Only Template (`alerts_email_only.json`)
- Email notifications for critical events
- Higher rate limits to reduce email volume
- Focus on actionable alerts

### Webhook Slack Template (`alerts_webhook_slack.json`)
- Slack integration with emoji
- Multiple severity levels
- Real-time notifications

### Comprehensive Template (`alerts_comprehensive.json`)
- All notification methods
- Detailed alert rules for all scenarios
- Fine-tuned rate limiting
- Emergency-level alerts

## Troubleshooting

### Alerts Not Sending

1. **Check if alerting is enabled:**
   ```bash
   python scripts/alert_manager.py status
   ```

2. **Validate configuration:**
   ```bash
   python scripts/alert_manager.py validate
   ```

3. **Test notifications:**
   ```bash
   python scripts/alert_manager.py test
   ```

### Email Issues

- **Authentication errors:** Use App Passwords for Gmail
- **Connection errors:** Check firewall and network connectivity
- **SSL/TLS errors:** Verify `use_tls` setting matches server requirements

### Webhook Issues

- **HTTP errors:** Check webhook URL and credentials
- **Timeout errors:** Increase timeout value
- **Format errors:** Verify webhook expects JSON payload

### Performance Considerations

- **Rate limiting:** Adjust limits based on your notification preferences
- **History size:** Reduce `max_history_size` if memory is limited
- **Rule complexity:** Complex conditions may impact performance

## Integration with Monitoring

The alert system integrates automatically with:

- **Air Quality Monitor Service**: Real-time air quality alerts
- **Flask Web Application**: System health monitoring
- **Database**: Historical data analysis for staleness detection

### Adding Custom Alert Rules

1. Edit `config.json` to add new rules
2. Restart the air quality monitor service:
   ```bash
   sudo systemctl restart air-quality-monitor.service
   ```

3. Test the new rules:
   ```bash
   python scripts/alert_manager.py test
   ```

## Security Considerations

- **Credentials:** Store email passwords and webhook URLs securely
- **Network:** Use TLS/SSL for email and HTTPS for webhooks
- **Permissions:** Limit file permissions on config.json
- **Logging:** Be aware that credentials may appear in logs during errors

## Examples

### Environmental Monitoring Setup

For outdoor air quality monitoring:

```json
{
  "rules": [
    {
      "type": "air_quality",
      "severity": "info",
      "title": "Air Quality Update",
      "message": "AQI changed to {aqi_level} ({aqi})",
      "condition": {"aqi_above": 50}
    },
    {
      "type": "air_quality",
      "severity": "emergency",
      "title": "Hazardous Air Quality",
      "message": "EMERGENCY: AQI is {aqi}. Stay indoors!",
      "condition": {"aqi_above": 300}
    }
  ]
}
```

### Industrial Monitoring Setup

For higher-sensitivity industrial environments:

```json
{
  "rules": [
    {
      "type": "air_quality",
      "severity": "warning",
      "title": "PM2.5 Threshold Exceeded",
      "message": "PM2.5: {pm2_5} μg/m³ exceeds workplace limits",
      "condition": {"pm25_above": 25}
    }
  ],
  "rate_limits": {
    "air_quality_warning": 5
  }
}
```

This alert system provides comprehensive monitoring capabilities while remaining flexible and easy to configure for various use cases.