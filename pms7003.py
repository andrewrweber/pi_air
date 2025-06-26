#!/usr/bin/env python3
"""
PMS7003 Air Quality Sensor Module
"""

import serial
import struct
import threading
import time
import logging

logger = logging.getLogger(__name__)

class PMS7003:
    """Driver for PMS7003 particulate matter sensor"""
    
    START_BYTE_1 = 0x42
    START_BYTE_2 = 0x4d
    FRAME_LENGTH = 32
    
    def __init__(self, port='/dev/ttyS0', baudrate=9600, timeout=2):
        """Initialize sensor connection"""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.latest_data = None
        self.last_update = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        
    def connect(self):
        """Connect to the sensor"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            logger.info(f"Connected to PMS7003 on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PMS7003: {e}")
            return False
    
    def start(self):
        """Start continuous reading in background thread"""
        if self.connect():
            self.running = True
            self.thread = threading.Thread(target=self._read_loop)
            self.thread.daemon = True
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Stop reading and close connection"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.serial:
            self.serial.close()
            
    def _read_loop(self):
        """Continuous reading loop"""
        while self.running:
            try:
                frame = self._read_frame()
                if frame:
                    data = self._parse_data(frame)
                    with self.lock:
                        self.latest_data = data
                        self.last_update = time.time()
            except Exception as e:
                logger.error(f"Error reading PMS7003: {e}")
                time.sleep(1)
    
    def _read_frame(self):
        """Read a data frame from the sensor"""
        # Clear buffer
        self.serial.reset_input_buffer()
        
        # Look for start bytes
        while self.running:
            b = self.serial.read(1)
            if not b or b[0] != self.START_BYTE_1:
                continue
                
            b = self.serial.read(1)
            if not b or b[0] != self.START_BYTE_2:
                continue
            
            # Read rest of frame
            frame = self.serial.read(self.FRAME_LENGTH - 2)
            if len(frame) != self.FRAME_LENGTH - 2:
                continue
            
            # Combine all bytes
            data = bytes([self.START_BYTE_1, self.START_BYTE_2]) + frame
            
            # Verify checksum
            checksum = struct.unpack('>H', data[-2:])[0]
            calculated_checksum = sum(data[:-2])
            
            if checksum == calculated_checksum:
                return data
                
        return None
    
    def _parse_data(self, data):
        """Parse sensor data frame"""
        values = struct.unpack('>HHHHHHHHHHHHHH', data[4:32])
        
        return {
            'pm1_0': values[3],  # PM1.0 atmospheric
            'pm2_5': values[4],  # PM2.5 atmospheric
            'pm10': values[5],   # PM10 atmospheric
            'particles_0_3um': values[6],
            'particles_0_5um': values[7],
            'particles_1_0um': values[8],
            'particles_2_5um': values[9],
            'particles_5_0um': values[10],
            'particles_10um': values[11],
        }
    
    def get_data(self):
        """Get latest sensor data"""
        with self.lock:
            if self.latest_data and self.last_update:
                # Add air quality index calculation
                aqi = self._calculate_aqi(self.latest_data['pm2_5'])
                return {
                    **self.latest_data,
                    'aqi': aqi,
                    'aqi_level': self._get_aqi_level(aqi),
                    'last_update': self.last_update
                }
        return None
    
    def _calculate_aqi(self, pm25):
        """Calculate AQI from PM2.5 value"""
        # EPA AQI breakpoints for PM2.5
        if pm25 <= 12.0:
            return self._linear_scale(pm25, 0, 12.0, 0, 50)
        elif pm25 <= 35.4:
            return self._linear_scale(pm25, 12.1, 35.4, 51, 100)
        elif pm25 <= 55.4:
            return self._linear_scale(pm25, 35.5, 55.4, 101, 150)
        elif pm25 <= 150.4:
            return self._linear_scale(pm25, 55.5, 150.4, 151, 200)
        elif pm25 <= 250.4:
            return self._linear_scale(pm25, 150.5, 250.4, 201, 300)
        elif pm25 <= 350.4:
            return self._linear_scale(pm25, 250.5, 350.4, 301, 400)
        elif pm25 <= 500.4:
            return self._linear_scale(pm25, 350.5, 500.4, 401, 500)
        else:
            return 500
    
    def _linear_scale(self, value, in_min, in_max, out_min, out_max):
        """Linear interpolation for AQI calculation"""
        return round((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)
    
    def _get_aqi_level(self, aqi):
        """Get AQI level description"""
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"