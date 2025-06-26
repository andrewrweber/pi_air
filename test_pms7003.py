#!/usr/bin/env python3
"""
PMS7003 Air Quality Sensor Test Script
Tests the PMS7003 sensor connected to UART1 (pins 8 TX, 10 RX)
"""

import serial
import struct
import time
import sys

class PMS7003:
    """Driver for PMS7003 particulate matter sensor"""
    
    START_BYTE_1 = 0x42
    START_BYTE_2 = 0x4d
    FRAME_LENGTH = 32
    
    def __init__(self, port='/dev/ttyS0', baudrate=9600, timeout=2):
        """Initialize sensor connection"""
        try:
            self.serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print(f"✓ Connected to PMS7003 on {port} at {baudrate} baud")
        except Exception as e:
            print(f"✗ Failed to connect to sensor: {e}")
            sys.exit(1)
    
    def read_frame(self):
        """Read a data frame from the sensor"""
        while True:
            # Look for start bytes
            first_byte = self.serial.read(1)
            if not first_byte or first_byte[0] != self.START_BYTE_1:
                continue
                
            second_byte = self.serial.read(1)
            if not second_byte or second_byte[0] != self.START_BYTE_2:
                continue
            
            # Read the rest of the frame
            frame = self.serial.read(self.FRAME_LENGTH - 2)
            if len(frame) != self.FRAME_LENGTH - 2:
                print("✗ Incomplete frame received")
                continue
            
            # Combine all bytes
            data = bytes([self.START_BYTE_1, self.START_BYTE_2]) + frame
            
            # Verify checksum
            checksum = struct.unpack('>H', data[-2:])[0]
            calculated_checksum = sum(data[:-2])
            
            if checksum == calculated_checksum:
                return data
            else:
                print("✗ Checksum mismatch")
    
    def parse_data(self, data):
        """Parse sensor data frame"""
        # Data structure based on PMS7003 datasheet
        values = struct.unpack('>HHHHHHHHHHHHHH', data[4:32])
        
        return {
            # CF=1 standard particle (μg/m³)
            'pm1_0_cf1': values[0],
            'pm2_5_cf1': values[1],
            'pm10_cf1': values[2],
            
            # Atmospheric environment (μg/m³)
            'pm1_0_atm': values[3],
            'pm2_5_atm': values[4],
            'pm10_atm': values[5],
            
            # Particle count per 0.1L air
            'particles_0_3um': values[6],
            'particles_0_5um': values[7],
            'particles_1_0um': values[8],
            'particles_2_5um': values[9],
            'particles_5_0um': values[10],
            'particles_10um': values[11],
        }
    
    def close(self):
        """Close serial connection"""
        if self.serial:
            self.serial.close()

def main():
    """Test the PMS7003 sensor"""
    print("PMS7003 Air Quality Sensor Test")
    print("=" * 40)
    
    # Initialize sensor
    sensor = PMS7003()
    
    print("\nReading sensor data (press Ctrl+C to stop)...")
    print("-" * 40)
    
    try:
        while True:
            # Read and parse data
            frame = sensor.read_frame()
            data = sensor.parse_data(frame)
            
            # Display readings
            print(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"PM 1.0: {data['pm1_0_atm']} μg/m³")
            print(f"PM 2.5: {data['pm2_5_atm']} μg/m³")
            print(f"PM 10:  {data['pm10_atm']} μg/m³")
            print(f"Particles > 0.3μm: {data['particles_0_3um']}/0.1L")
            print(f"Particles > 2.5μm: {data['particles_2_5um']}/0.1L")
            print("-" * 40)
            
            # Wait before next reading
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        sensor.close()
        print("✓ Sensor connection closed")

if __name__ == "__main__":
    main()