#!/usr/bin/env python3
"""
smart_street_light_complete_final.py
Raspberry Pi hardware control + Flask web server for 4 lights
- Real-time hardware control through webpage (manual buttons)
- Automatic LDR-based control (dark = ON, bright = OFF)
- Light 4 has sensor fault (default)
- Real-time status updates on webpage

Installation:
    pip3 install flask flask-cors

Run:
    python3 smart_street_light_complete_final.py

Access via: http://YOUR_PI_IP:5000
"""

import time
import signal
import sys
import threading
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    import lgpio as GPIO

# ------------------ CONFIG ------------------
SAMPLE_INTERVAL = 2                       # seconds between sensor readings
RELAY_PINS = [17, 18, 27, 22]             # GPIO pins for 4-channel relay (BCM)
LDR_PINS = [5, 6, 13, 19]                 # digital inputs for 4 LDRs (BCM)
AUTO_MODE = True                          # Enable automatic LDR control
WEB_PORT = 5000                           # Flask web server port

# Manual override flags (when user clicks buttons)
manual_override = {
    "light1": False,
    "light2": False,
    "light3": False,
    "light4": False
}

# ------------------ GLOBAL DATA ------------------
lights_data = {
    "light1": {"status": "OFF", "lux": 100},  # Default lux = 100
    "light2": {"status": "OFF", "lux": 100},  # Default lux = 100
    "light3": {"status": "OFF", "lux": 100},  # Default lux = 100
    "light4": {"status": "OFF", "lux": -1}    # Light 4: Sensor Failed (always -1)
}

# ------------------ FLASK APP ------------------
app = Flask(__name__)
CORS(app)

# ------------------ GPIO Setup ------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in RELAY_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)  # Initialize all relays to OFF

for pin in LDR_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ------------------ Hardware Control Functions ------------------
def turn_light_on(light_index, source="manual"):
    """Turn on a specific light (0-3)"""
    if 0 <= light_index < len(RELAY_PINS):
        GPIO.output(RELAY_PINS[light_index], GPIO.HIGH)
        lights_data[f"light{light_index+1}"]["status"] = "ON"
        print(f"✅ Light {light_index+1} turned ON ({source})")

def turn_light_off(light_index, source="manual"):
    """Turn off a specific light (0-3)"""
    if 0 <= light_index < len(RELAY_PINS):
        GPIO.output(RELAY_PINS[light_index], GPIO.LOW)
        lights_data[f"light{light_index+1}"]["status"] = "OFF"
        print(f"❌ Light {light_index+1} turned OFF ({source})")

def read_ldr(ldr_index):
    """Read LDR sensor value (0-3)
    Returns: lux value (0=dark, 100=bright for lights 1-3, -1=failed for light 4)
    """
    try:
        # Light 4 (index 3) always returns sensor failed
        if ldr_index == 3:
            return -1  # Sensor failed for Light 4
        
        # Lights 1-3: Read actual LDR sensor
        if 0 <= ldr_index < len(LDR_PINS):
            ldr_state = GPIO.input(LDR_PINS[ldr_index])
            
            # LDR Logic:
            # GPIO.HIGH (1) = Bright light detected -> lux = 100
            # GPIO.LOW (0) = Dark detected -> lux = 0
            if ldr_state == GPIO.HIGH:
                lux = 100  # Bright
            else:
                lux = 0    # Dark
            
            return lux
        return -1  # Sensor not available
    except Exception as e:
        print(f"❌ LDR {ldr_index+1} read error: {e}")
        return -1  # Sensor failed

def update_sensors():
    """Read all LDR sensors and update light data"""
    for i in range(4):
        lux = read_ldr(i)
        lights_data[f"light{i+1}"]["lux"] = lux

def auto_control_lights():
    """Automatically control lights based on LDR readings
    Dark (lux=0) -> Turn ON
    Bright (lux>0) -> Turn OFF
    Only for lights without manual override
    """
    if not AUTO_MODE:
        return
    
    for i in range(4):
        light_key = f"light{i+1}"
        
        # Skip if manual override is active
        if manual_override[light_key]:
            continue
        
        # Skip Light 4 (sensor failed)
        if i == 3:
            continue
        
        lux = lights_data[light_key]["lux"]
        current_status = lights_data[light_key]["status"]
        
        # Auto control logic:
        # If DARK (lux = 0) and light is OFF -> Turn ON
        if lux == 0 and current_status == "OFF":
            turn_light_on(i, source="auto-LDR")
        
        # If BRIGHT (lux > 0) and light is ON -> Turn OFF
        elif lux > 0 and current_status == "ON":
            turn_light_off(i, source="auto-LDR")

def print_status():
    """Print current status of all lights"""
    print("\n" + "="*70)
    print(f"Status Update - {time.strftime('%H:%M:%S')}")
    print("="*70)
    for i in range(4):
        light_key = f"light{i+1}"
        status = lights_data[light_key]["status"]
        lux = lights_data[light_key]["lux"]
        override = "🔒 MANUAL" if manual_override[light_key] else "🤖 AUTO"
        
        if lux == -1:
            lux_str = "FAILED"
            symbol = "⚠️"
        elif lux == 0:
            lux_str = "  0 (DARK)"
            symbol = "🌙"
        else:
            lux_str = f"{lux:3d} (BRIGHT)"
            symbol = "☀️"
            
        print(f"💡 Light {i+1}: {status:3s} | {lux_str:15s} {symbol} | {override}")
    print("="*70)

# ------------------ Flask Routes ------------------
@app.route('/')
def index():
    """Serve the main dashboard HTML"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get current light status and sensor data"""
    return jsonify({
        'lights': lights_data,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'success': True
    })

@app.route('/control', methods=['POST'])
def control_light():
    """API endpoint to control lights - REAL-TIME HARDWARE CONTROL
    Sets manual override for 30 seconds, then returns to auto mode
    """
    try:
        data = request.json
        light_id = int(data.get('light_id'))      # 1-4
        action = data.get('action', '').lower()   # 'on' or 'off'
        
        # Validate input
        if light_id < 1 or light_id > 4:
            return jsonify({
                'success': False,
                'message': f'Invalid light_id: {light_id}. Must be 1-4.'
            }), 400
        
        if action not in ['on', 'off']:
            return jsonify({
                'success': False,
                'message': f'Invalid action: {action}. Must be "on" or "off".'
            }), 400
        
        light_key = f"light{light_id}"
        
        # Set manual override (disable auto mode for this light temporarily)
        manual_override[light_key] = True
        
        # Schedule to clear manual override after 30 seconds
        def clear_override():
            time.sleep(30)
            manual_override[light_key] = False
            print(f"🔓 Light {light_id} returned to AUTO mode")
        
        threading.Thread(target=clear_override, daemon=True).start()
        
        # REAL-TIME HARDWARE CONTROL
        if action == 'on':
            turn_light_on(light_id - 1, source="web-button")
        else:
            turn_light_off(light_id - 1, source="web-button")
        
        return jsonify({
            'success': True,
            'message': f'Light {light_id} turned {action.upper()} (Manual mode for 30s)',
            'light_id': light_id,
            'action': action,
            'new_status': lights_data[light_key]["status"]
        })
        
    except Exception as e:
        print(f"❌ Control error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ------------------ Hardware Loop ------------------
def hardware_loop(stop_event):
    """Main hardware control loop - runs in background thread"""
    print("\n🔧 Hardware monitoring thread started")
    print("🤖 Automatic LDR control ENABLED")
    print("   - Dark detected (LDR LOW) -> Light ON")
    print("   - Bright detected (LDR HIGH) -> Light OFF\n")
    
    while not stop_event.is_set():
        # Update sensor readings
        update_sensors()
        
        # Auto control lights based on LDR
        auto_control_lights()
        
        # Print status to console
        print_status()
        
        # Wait for next sample
        time.sleep(SAMPLE_INTERVAL)

# ------------------ MAIN ------------------
def main():
    stop_event = threading.Event()
    
    # Handle graceful shutdown (ctrl-c)
    def handle_sigterm(signum, frame):
        print("\n\n🛑 Shutdown signal received, cleaning up...")
        stop_event.set()
        
        # Turn off all relays before exit
        print("💡 Turning off all lights...")
        for pin in RELAY_PINS:
            GPIO.output(pin, GPIO.LOW)
        
        GPIO.cleanup()
        print("✅ GPIO cleanup complete")
        print("👋 Goodbye!\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    # Start hardware monitoring thread
    hardware_thread = threading.Thread(target=hardware_loop, args=(stop_event,))
    hardware_thread.daemon = True
    hardware_thread.start()

    # Get Pi IP address
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        pi_ip = s.getsockname()[0]
        s.close()
    except:
        pi_ip = "localhost"

    print("\n" + "="*80)
    print("🚀 Smart Street Light System Started - FULL FUNCTIONALITY")
    print("="*80)
    print(f"🌐 Web Dashboard: http://{pi_ip}:{WEB_PORT}")
    print(f"🌐 Local Access:  http://localhost:{WEB_PORT}")
    print(f"\n📡 GPIO Configuration:")
    print(f"   Relay Pins: {RELAY_PINS}")
    print(f"   LDR Pins:   {LDR_PINS}")
    print(f"\n⚡ Features:")
    print(f"   ✅ Manual Control: ON/OFF buttons work in real-time")
    print(f"   ✅ Auto LDR Control: Lights turn ON when dark, OFF when bright")
    print(f"   ✅ Light 1-3: Normal operation (12V, 0.6A, LDR-based lux)")
    print(f"   ✅ Light 4: Sensor Failed Status (always N/A)")
    print(f"   ✅ Manual Override: 30 seconds after button press, returns to auto")
    print(f"   ✅ Real-time Updates: Webpage updates every 2 seconds")
    print(f"\n🤖 Auto Mode Logic:")
    print(f"   - LDR senses DARK (LOW) → Light turns ON")
    print(f"   - LDR senses BRIGHT (HIGH) → Light turns OFF")
    print(f"\nPress Ctrl+C to stop")
    print("="*80 + "\n")

    try:
        # Start Flask web server
        app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        handle_sigterm(None, None)
    finally:
        stop_event.set()
        for pin in RELAY_PINS:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()

if __name__ == "__main__":
    main()