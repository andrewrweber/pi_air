# Stage 1: Database Foundation

## Overview
Set up the Supabase backend infrastructure including database schema, authentication, and security policies. This forms the foundation for all cloud functionality.

## Goals
- Create a secure, scalable database structure
- Implement user authentication system
- Set up Row Level Security (RLS) policies
- Enable API access for devices

## Database Schema

### Core Tables

```sql
-- Users table (managed by Supabase Auth)
-- Automatically created by Supabase

-- Devices table
CREATE TABLE devices (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, -- "Living Room", "Bedroom", "Kitchen", etc.
  room_type TEXT, -- "bedroom", "living_room", "kitchen", "office", "outdoor", "other"
  description TEXT, -- "Main bedroom, second floor"
  location JSONB, -- {lat: float, lon: float, address: string, timezone: string, floor: string, building: string}
  group_name TEXT, -- "Home", "Office", "Vacation House", etc.
  display_order INTEGER DEFAULT 0, -- for custom ordering in UI
  icon TEXT, -- icon identifier for UI display
  color TEXT, -- hex color for UI customization
  api_key TEXT UNIQUE NOT NULL,
  last_seen TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN DEFAULT true,
  is_default BOOLEAN DEFAULT false, -- default device for user
  metadata JSONB, -- {model: string, firmware: string, etc}
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Air quality readings
CREATE TABLE air_quality_readings (
  id BIGSERIAL PRIMARY KEY,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  pm1_0 REAL,
  pm2_5 REAL NOT NULL,
  pm10 REAL NOT NULL,
  aqi INTEGER NOT NULL,
  aqi_level TEXT NOT NULL,
  temperature REAL,
  humidity REAL,
  sample_count INTEGER DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System readings
CREATE TABLE system_readings (
  id BIGSERIAL PRIMARY KEY,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  cpu_temp REAL,
  cpu_usage REAL,
  memory_usage REAL,
  disk_usage REAL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User settings
CREATE TABLE user_settings (
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  preferences JSONB DEFAULT '{}', -- {theme: string, units: string, default_device_id: uuid, etc}
  notification_settings JSONB DEFAULT '{}', -- {email_alerts: bool, per_device_thresholds: {device_id: {pm25: 35, aqi: 100}}}
  device_display_settings JSONB DEFAULT '{}', -- {sort_order: "name|aqi|last_updated", view_mode: "grid|list"}
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API Keys table for device authentication
CREATE TABLE api_keys (
  key TEXT PRIMARY KEY,
  device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_used TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN DEFAULT true
);
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_air_quality_device_timestamp ON air_quality_readings(device_id, timestamp DESC);
CREATE INDEX idx_system_device_timestamp ON system_readings(device_id, timestamp DESC);
CREATE INDEX idx_devices_user ON devices(user_id);
CREATE INDEX idx_devices_group ON devices(user_id, group_name);
CREATE INDEX idx_devices_active ON devices(user_id, is_active);
CREATE INDEX idx_api_keys_device ON api_keys(device_id);

-- Unique constraint to prevent duplicate readings
CREATE UNIQUE INDEX idx_air_quality_unique ON air_quality_readings(device_id, timestamp);
```

## Row Level Security (RLS) Policies

```sql
-- Enable RLS on all tables
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE air_quality_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Devices policies
CREATE POLICY "Users can view their own devices" ON devices
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own devices" ON devices
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own devices" ON devices
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own devices" ON devices
  FOR DELETE USING (auth.uid() = user_id);

-- Air quality readings policies
CREATE POLICY "Users can view their devices' readings" ON air_quality_readings
  FOR SELECT USING (
    device_id IN (
      SELECT id FROM devices WHERE user_id = auth.uid()
    )
  );

-- API key based insert for devices
CREATE POLICY "Devices can insert readings with valid API key" ON air_quality_readings
  FOR INSERT WITH CHECK (
    device_id IN (
      SELECT device_id FROM api_keys 
      WHERE key = current_setting('app.api_key', true)::text 
      AND is_active = true
    )
  );

-- Similar policies for system_readings
CREATE POLICY "Users can view their devices' system readings" ON system_readings
  FOR SELECT USING (
    device_id IN (
      SELECT id FROM devices WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Devices can insert system readings with valid API key" ON system_readings
  FOR INSERT WITH CHECK (
    device_id IN (
      SELECT device_id FROM api_keys 
      WHERE key = current_setting('app.api_key', true)::text 
      AND is_active = true
    )
  );

-- User settings policies
CREATE POLICY "Users can view their own settings" ON user_settings
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own settings" ON user_settings
  FOR ALL USING (auth.uid() = user_id);

-- API keys policies (only viewable by device owner)
CREATE POLICY "Users can view their devices' API keys" ON api_keys
  FOR SELECT USING (
    device_id IN (
      SELECT id FROM devices WHERE user_id = auth.uid()
    )
  );
```

## Supabase Setup Steps

1. **Create Supabase Project**
   - Sign up at supabase.com
   - Create new project
   - Note the project URL and anon key

2. **Enable Authentication**
   - Enable email/password authentication
   - Configure email templates
   - Set up password policies

3. **Run Database Migrations**
   - Execute schema SQL via Supabase SQL editor
   - Verify all tables created successfully
   - Test RLS policies with sample data

4. **Configure API Settings**
   - Enable required APIs
   - Set up CORS policies
   - Configure rate limiting

## Testing Requirements

### Unit Tests
- [ ] Test RLS policies with different user contexts
- [ ] Verify API key authentication works
- [ ] Test data insertion with valid/invalid keys
- [ ] Verify user isolation

### Integration Tests
- [ ] Create test user and authenticate
- [ ] Register test device
- [ ] Insert sample readings
- [ ] Query data and verify access controls

### Performance Tests
- [ ] Bulk insert 10,000 readings
- [ ] Query performance with indexes
- [ ] Concurrent device uploads

## Success Criteria
- [ ] Database schema deployed successfully
- [ ] Authentication system functional
- [ ] RLS policies prevent unauthorized access
- [ ] API keys authenticate devices correctly
- [ ] All indexes improve query performance

## Next Stage
Once the database foundation is complete and tested, proceed to Stage 2: Device Configuration & Registration.