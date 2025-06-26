#!/usr/bin/env python3
"""
Test PMS7003 sensor using pms5003 library
"""

import time
from pms5003 import PMS5003, ReadTimeoutError

def main():
    print("PMS7003 Test using pms5003 library")
    print("=" * 40)
    
    try:
        # Initialize sensor on /dev/ttyS0
        pms = PMS5003(device='/dev/ttyS0', baudrate=9600, pin_enable=None, pin_reset=None)
        print("✓ Connected to sensor on /dev/ttyS0")
        
        print("\nReading data (Ctrl+C to stop)...")
        print("-" * 40)
        
        while True:
            try:
                data = pms.read()
                print(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"PM1.0: {data.pm_ug_per_m3(1.0)} μg/m³")
                print(f"PM2.5: {data.pm_ug_per_m3(2.5)} μg/m³")
                print(f"PM10:  {data.pm_ug_per_m3(10)} μg/m³")
                print(f"Particles > 0.3μm: {data.pm_per_1l_air(0.3)}/L")
                print(f"Particles > 2.5μm: {data.pm_per_1l_air(2.5)}/L")
                print("-" * 40)
                
            except ReadTimeoutError:
                print("✗ Timeout reading data")
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n✓ Test stopped")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()