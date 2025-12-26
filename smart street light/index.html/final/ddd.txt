from flask import Flask, jsonify, request, session
from flask_cors import CORS
from functools import wraps
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️  RPi.GPIO not available - running in simulation mode")
import time
import random
import datetime

app = Flask(__name__)

# ============================================================================
# CONFIGURATION - CHANGE THESE IN PRODUCTION
# ============================================================================
app.secret_key = 'smart_street_light_secret_key_12345'  # Change this!
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set True with HTTPS in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Login Credentials (CHANGE IN PRODUCTION!)
VALID_USERS = {
    'admin': 'admin',      # Default credentials
    'user': 'password',    # Additional user
    'test': 'test123'      # Test user
}

# ============================================================================
# CORS Configuration
# ============================================================================
CORS(app, 
     supports_credentials=True,
     origins=['http://localhost:*', 'http://127.0.0.1:*'],
     allow_headers=['Content-Type'],
     methods=['GET', 'POST', 'OPTIONS'])

# ============================================================================
# DECORATORS
# ============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({
                'error': 'Authentication required', 
                'logged_in': False
            }), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# GPIO CONFIGURATION
# ============================================================================
RELAY_PINS = [17, 18, 27, 22]  # GPIO pins for 4 relays (BCM mode)
LDR_PINS = [5, 6, 13, 19]      # LDR sensor pins

if GPIO_AVAILABLE:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup relay pins as outputs (Active LOW relays)
        for pin in RELAY_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)  # OFF state (active low)

        # Setup LDR pins as inputs with pull-up resistors
        for pin in LDR_PINS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        print("✅ GPIO initialized successfully")
    except Exception as e:
        print(f"❌ GPIO initialization error: {e}")
        GPIO_AVAILABLE = False
else:
    print("⚙️  Running in SIMULATION mode (no hardware)")

# ============================================================================
# GLOBAL STATE
# ============================================================================
light_states = [
    {'id': 1, 'relay_state': 'OFF', 'voltage': 0, 'current': 0, 'lux': 0},
    {'id': 2, 'relay_state': 'OFF', 'voltage': 0, 'current': 0, 'lux': 0},
    {'id': 3, 'relay_state': 'OFF', 'voltage': 0, 'current': 0, 'lux': 0},
    {'id': 4, 'relay_state': 'OFF', 'voltage': 0, 'current': 0, 'lux': 0}
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def read_sensor_data(light_index):
    """Read sensor data for a specific light with automatic control"""
    try:
        if GPIO_AVAILABLE:
            ldr_pin = LDR_PINS[light_index]
            ldr_val = GPIO.input(ldr_pin)  # 0 = dark, 1 = light

            if light_index == 2:  # Light 3 (index 2) always sensor fault
                lux = -1
                voltage = 0
                current = 0
                # Don't control relay for light 3
            else:
                # Automatic control for lights 1-3 based on LDR
                if ldr_val == 0:  # Dark - turn ON
                    light_states[light_index]['relay_state'] = 'ON'
                    GPIO.output(RELAY_PINS[light_index], GPIO.LOW)  # Active LOW
                    voltage = round(random.uniform(11.5, 12.5), 1)
                    current = round(random.uniform(1.0, 1.4), 1)
                    lux = ldr_val * 500  # 0 * 500 = 0, but we'll set to low lux
                else:  # Bright - turn OFF
                    light_states[light_index]['relay_state'] = 'OFF'
                    GPIO.output(RELAY_PINS[light_index], GPIO.HIGH)  # Active LOW
                    voltage = 0
                    current = 0
                    lux = ldr_val * 500  # 1 * 500 = 500
        else:
            # Simulation mode
            if light_index == 2:  # Light 3 always sensor fault
                lux = -1
                voltage = 0
                current = 0
            else:
                # Simulate automatic control
                ldr_val = random.choice([0, 1])  # Simulate dark/bright
                if ldr_val == 0:  # Dark - turn ON
                    light_states[light_index]['relay_state'] = 'ON'
                    voltage = round(random.uniform(11.5, 12.5), 1)
                    current = round(random.uniform(1.0, 1.4), 1)
                    lux = random.randint(0, 50)  # Low lux for dark
                else:  # Bright - turn OFF
                    light_states[light_index]['relay_state'] = 'OFF'
                    voltage = 0
                    current = 0
                    lux = random.randint(450, 550)  # High lux for bright

        return voltage, current, lux
    except Exception as e:
        print(f"❌ Sensor read error for light {light_index + 1}: {e}")
        return 0, 0, 0

def update_light_data():
    """Update sensor data for all lights"""
    for i in range(4):
        voltage, current, lux = read_sensor_data(i)
        light_states[i]['voltage'] = voltage
        light_states[i]['current'] = current
        light_states[i]['lux'] = lux

def calculate_stats():
    """Calculate system statistics"""
    active_lights = [light for light in light_states if light['relay_state'] == 'ON']
    
    # Voltage remains constant at 12V when any light is on
    total_voltage = 12.0 if active_lights else 0
    
    # Current is sum of all active lights
    total_current = sum(light['current'] for light in active_lights)
    
    # Total luminosity
    total_lux = sum(light['lux'] for light in active_lights)
    
    # System status
    system_status = 'No Fault'
    if total_current > 6.0:  # Example: Over-current protection
        system_status = 'Warning: High Current'
    
    return {
        'total_voltage': round(total_voltage, 1),
        'total_current': round(total_current, 1),
        'luminosity': int(total_lux),
        'system_status': system_status
    }

def generate_chart_data():
    """Generate historical chart data"""
    now = datetime.datetime.now()
    labels = [(now - datetime.timedelta(hours=5-i)).strftime('%H:%M') for i in range(6)]
    
    # Generate realistic historical data
    voltage_data = [round(random.uniform(11.5, 12.5), 1) for _ in range(6)]
    current_data = [round(random.uniform(0.5, 1.5), 1) for _ in range(6)]
    
    return {
        'voltage': {'labels': labels, 'data': voltage_data},
        'current': {'labels': labels, 'data': current_data}
    }

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Serve main page"""
    return jsonify({
        'message': 'Smart Street Light Backend API',
        'version': '1.0',
        'endpoints': {
            'login': '/login [POST]',
            'logout': '/logout [POST]',
            'check_login': '/check_login [GET]',
            'data': '/api/data [GET] - requires login',
            'control': '/control [POST] - requires login'
        }
    })

@app.route('/api/data', methods=['GET'])
@login_required
def get_data():
    """Get current system data (requires authentication)"""
    try:
        # Update sensor readings
        update_light_data()
        
        # Calculate statistics
        stats = calculate_stats()
        
        # Generate chart data
        charts = generate_chart_data()
        
        data = {
            'lights': light_states,
            'stats': stats,
            'charts': charts,
            'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(data), 200
    
    except Exception as e:
        print(f"❌ Error in get_data: {e}")
        return jsonify({'error': 'Failed to fetch data'}), 500

@app.route('/control', methods=['POST', 'OPTIONS'])
@login_required
def control_light():
    """Control individual lights (requires authentication)"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False, 
                'message': 'No data provided'
            }), 400
        
        light_id = data.get('light_id')
        action = data.get('action', '').lower()
        
        # Validation
        if light_id is None:
            return jsonify({
                'success': False, 
                'message': 'Light ID is required'
            }), 400
        
        try:
            light_id = int(light_id)
        except ValueError:
            return jsonify({
                'success': False, 
                'message': 'Light ID must be a number'
            }), 400
        
        if not (1 <= light_id <= 4):
            return jsonify({
                'success': False, 
                'message': f'Invalid light ID: {light_id}. Must be 1-4'
            }), 400
        
        if action not in ['on', 'off']:
            return jsonify({
                'success': False, 
                'message': f'Invalid action: {action}. Must be "on" or "off"'
            }), 400
        
        # Control GPIO if available
        light_index = light_id - 1
        
        if GPIO_AVAILABLE:
            try:
                pin = RELAY_PINS[light_index]
                if action == 'on':
                    GPIO.output(pin, GPIO.LOW)   # Active LOW relay
                    print(f"✅ GPIO: Light {light_id} ON (Pin {pin} -> LOW)")
                else:
                    GPIO.output(pin, GPIO.HIGH)  # Active LOW relay
                    print(f"✅ GPIO: Light {light_id} OFF (Pin {pin} -> HIGH)")
            except Exception as gpio_error:
                print(f"❌ GPIO control error: {gpio_error}")
                return jsonify({
                    'success': False,
                    'message': f'GPIO control failed: {str(gpio_error)}'
                }), 500
        else:
            print(f"⚙️  SIMULATION: Light {light_id} {action.upper()}")
        
        # Update state
        new_state = 'ON' if action == 'on' else 'OFF'
        light_states[light_index]['relay_state'] = new_state
        
        # Update sensor values immediately
        if action == 'on':
            light_states[light_index]['voltage'] = round(random.uniform(11.5, 12.5), 1)
            light_states[light_index]['current'] = round(random.uniform(1.0, 1.4), 1)
            light_states[light_index]['lux'] = random.randint(450, 550)
        else:
            light_states[light_index]['voltage'] = 0
            light_states[light_index]['current'] = 0
            light_states[light_index]['lux'] = 0
        
        return jsonify({
            'success': True,
            'message': f'Light {light_id} turned {action.upper()}',
            'light_state': light_states[light_index]
        }), 200
    
    except Exception as e:
        print(f"❌ Error in control_light: {e}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """User login endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password required'
            }), 400
        
        print(f"🔐 Login attempt - Username: '{username}'")
        
        # Check credentials
        if username in VALID_USERS and VALID_USERS[username] == password:
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = datetime.datetime.now().isoformat()
            
            print(f"✅ Login successful - User: '{username}'")
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'username': username
            }), 200
        else:
            print(f"❌ Login failed - Invalid credentials for '{username}'")
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            }), 401
    
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Server error during login'
        }), 500

@app.route('/logout', methods=['POST', 'OPTIONS'])
def logout():
    """User logout endpoint"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200
    
    username = session.get('username', 'Unknown')
    session.clear()
    print(f"👋 Logout - User: '{username}'")
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200

@app.route('/check_login', methods=['GET'])
def check_login():
    """Check if user is logged in"""
    is_logged_in = 'logged_in' in session and session['logged_in']
    username = session.get('username', '') if is_logged_in else ''

    return jsonify({
        'logged_in': is_logged_in,
        'username': username
    }), 200

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get backend status"""
    return jsonify({'status': 'online'}), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'error': 'Endpoint not found',
        'message': str(e)
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Authentication required'
    }), 401

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    try:
        print("\n" + "=" * 70)
        print("     🌟 SMART STREET LIGHT CONTROL SYSTEM 🌟")
        print("=" * 70)
        print(f"  Mode: {'🔧 HARDWARE' if GPIO_AVAILABLE else '💻 SIMULATION'}")
        print(f"  Server: http://0.0.0.0:5000")
        print(f"  GPIO: {'✅ Available' if GPIO_AVAILABLE else '❌ Not Available'}")
        print("=" * 70)
        print("  📋 VALID LOGIN CREDENTIALS:")
        print("-" * 70)
        for user, pwd in VALID_USERS.items():
            print(f"     Username: '{user}' | Password: '{pwd}'")
        print("=" * 70)
        print("  🚀 Starting server...")
        print("=" * 70 + "\n")
        
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
        
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("  ⚠️  Server shutdown requested...")
        print("=" * 70)
        if GPIO_AVAILABLE:
            print("  🧹 Cleaning up GPIO...")
            GPIO.cleanup()
            print("  ✅ GPIO cleanup complete")
        print("  👋 Server stopped successfully")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if GPIO_AVAILABLE:
            GPIO.cleanup()
    
    finally:
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except:
                pass