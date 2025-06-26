#!/usr/bin/env python3
"""
Simple PMS7003 test - direct serial communication
"""

import serial
import time

def main():
    print("Simple PMS7003 Serial Test")
    print("=" * 40)
    
    try:
        # Open serial port
        ser = serial.Serial('/dev/ttyS0', 9600, timeout=1)
        print(f"✓ Opened /dev/ttyS0 at 9600 baud")
        print(f"Port info: {ser}")
        
        print("\nReading raw data (Ctrl+C to stop)...")
        print("Looking for start bytes 0x42 0x4D...")
        print("-" * 40)
        
        # Clear any buffered data
        ser.reset_input_buffer()
        
        byte_count = 0
        start_found = False
        
        while True:
            # Read one byte at a time
            byte = ser.read(1)
            
            if byte:
                byte_count += 1
                byte_val = byte[0]
                
                # Show first 100 bytes regardless
                if byte_count <= 100:
                    print(f"Byte {byte_count}: 0x{byte_val:02X} ({byte_val})", end=" ")
                    if byte_count % 5 == 0:
                        print()
                
                # Look for PMS start sequence
                if byte_val == 0x42:
                    next_byte = ser.read(1)
                    if next_byte and next_byte[0] == 0x4D:
                        if not start_found:
                            print(f"\n\n✓ Found start sequence at byte {byte_count}!")
                            start_found = True
                        
                        # Read frame length
                        frame_length_bytes = ser.read(2)
                        if len(frame_length_bytes) == 2:
                            frame_length = (frame_length_bytes[0] << 8) | frame_length_bytes[1]
                            print(f"Frame length: {frame_length}")
                            
                            # Read rest of frame
                            remaining = ser.read(frame_length)
                            print(f"Read {len(remaining)} more bytes")
                            
                            if len(remaining) >= 12:
                                # Extract PM2.5 value (bytes 6-7)
                                pm25 = (remaining[4] << 8) | remaining[5]
                                print(f"PM2.5: {pm25} μg/m³")
                                print("-" * 40)
            else:
                print(".", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'ser' in locals():
            ser.close()
            print("✓ Serial port closed")

if __name__ == "__main__":
    main()