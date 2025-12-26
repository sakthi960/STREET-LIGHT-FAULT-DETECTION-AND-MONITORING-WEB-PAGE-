# Smart Street Light Dashboard

A real-time monitoring and control system for street lights using Raspberry Pi hardware integration.

## Features

- **Real-time Data Monitoring**: Live voltage, current, and lux readings from sensors
- **Individual Light Control**: Control 4 street lights independently via relay modules
- **Interactive Dashboard**: Modern web interface with real-time updates
- **Performance Charts**: Voltage and current trend visualization
- **System Status Monitoring**: Fault detection and system health indicators
- **Responsive Design**: Works on desktop and mobile devices

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- 4-channel relay module
- Voltage, current, and lux sensors (optional - simulated data available)
- GPIO connections:
  - Relays: GPIO 17, 18, 27, 22
  - Sensors: GPIO 23 (voltage), 24 (current), 25 (lux)

## Software Requirements

- Python 3.7+
- Flask
- RPi.GPIO (for Raspberry Pi)
- Chart.js (included via CDN)

## Installation

1. **Clone or download the project files to your Raspberry Pi**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Hardware Setup:**
   - Connect relay module to GPIO pins 17, 18, 27, 22
   - Connect sensors to GPIO pins 23, 24, 25 (optional)
   - Ensure proper power connections

4. **Run the server:**
   ```bash
   python run_server.py
   ```

5. **Access the dashboard:**
   - Open a web browser
   - Navigate to `http://<raspberry-pi-ip>:5000`
   - Or if running locally: `http://localhost:5000`

## API Endpoints

### GET /api/data
Returns real-time data for all lights and system stats.

**Response:**
```json
{
  "lights": [
    {
      "relay_state": "ON",
      "voltage": 220.0,
      "current": 1.2,
      "lux": 500
    }
  ],
  "stats": {
    "total_voltage": 220.0,
    "total_current": 1.2,
    "luminosity": 500,
    "system_status": "No Fault"
  },
  "charts": {
    "voltage_data": [220, 218, 221, 219, 222, 220],
    "current_data": [1.2, 1.1, 1.3, 1.0, 1.4, 1.2]
  }
}
```

### POST /api/control/{light_id}/{action}
Controls individual lights.

**Parameters:**
- `light_id`: 1-4 (integer)
- `action`: "on" or "off"

**Example:** `POST /api/control/1/on`

## File Structure

```
smart-street-light/
├── index.html          # Main dashboard interface
├── backend.py          # Flask server with GPIO control
├── run_server.py      # Server startup script
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── TODO.md            # Development tasks
```

## Development

The dashboard uses simulated sensor data when hardware is not available. To enable real hardware integration:

1. Uncomment the actual sensor reading code in `backend.py`
2. Connect physical sensors to the specified GPIO pins
3. Ensure proper sensor calibration

## Troubleshooting

- **Server won't start**: Check if GPIO pins are available and not in use by other processes
- **Dashboard not updating**: Verify the server is running and accessible on port 5000
- **Control buttons not working**: Check relay connections and GPIO pin configurations
- **Sensor data not reading**: Ensure sensors are properly connected and powered

## Security Notes

- This is a development/demo system
- For production use, add authentication and HTTPS
- Consider network security when exposing the Raspberry Pi to the internet

## License

This project is open source and available under the MIT License.
