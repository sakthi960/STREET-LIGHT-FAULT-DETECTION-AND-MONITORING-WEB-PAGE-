#!/usr/bin/env python3
"""
smart_street_light_combined.py
Raspberry Pi with hardware control + web dashboard
Run: python3 smart_street_light_combined.py
Access: http://raspberry-pi-ip:5000
"""

import time
import threading
import signal
import sys
from datetime import datetime
from collections import deque

try:
    import RPi.GPIO as GPIO # pyright: ignore[reportMissingModuleSource]
except (RuntimeError, ModuleNotFoundError):
    import lgpio as GPIO # pyright: ignore[reportMissingImports]

from flask import Flask, render_template_string, jsonify, request # pyright: ignore[reportMissingImports]

# ------------------ CONFIG ------------------
SAMPLE_INTERVAL = 2
RELAY_PINS = [17, 18, 27, 22]
LDR_PINS = [5, 6, 13, 19]
AUTO_MODE = False  # Set to True for automatic control

# ------------------ GLOBAL DATA ------------------
lights_data = [
    {"relay_state": "OFF", "lux": 0, "voltage": 0, "current": 0}
    for i in range(4)
]

# Chart data storage (last 6 readings)
voltage_history = deque(maxlen=6)
current_history = deque(maxlen=6)
time_labels = deque(maxlen=6)

# Initialize with zeros
for i in range(6):
    voltage_history.append(0)
    current_history.append(0)
    time_labels.append(f"{i:02d}:00")

# ------------------ GPIO Setup ------------------
GPIO.setmode(GPIO.BCM)
for pin in RELAY_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)

for pin in LDR_PINS:
    GPIO.setup(pin, GPIO.IN)

# ------------------ Flask App ------------------
app = Flask(_name_)

# ========== HTML TEMPLATE ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Street Light Dashboard - 4 Lights Control</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            margin-bottom: 30px;
            animation: fadeInDown 0.8s ease;
        }
        
        .header-left h1 {
            font-size: 2.5em;
            background: linear-gradient(45deg, #00ff88, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }
        
        .header-left .subtitle {
            color: #aaa;
            font-size: 1em;
        }
        
        .header-right {
            text-align: right;
        }

        .user-info {
            color: #00d4ff;
            font-size: 1.1em;
            margin-bottom: 10px;
        }

        #backend-status {
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
            animation: fadeIn 1s ease;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.3);
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #aaa;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stat-value {
            font-size: 2.2em;
            font-weight: bold;
            color: #00ff88;
        }
        
        .stat-unit {
            font-size: 0.5em;
            color: #888;
            margin-left: 5px;
        }
        
        /* Section Title */
        .section-title {
            font-size: 1.8em;
            margin: 40px 0 25px 0;
            color: #00d4ff;
            border-left: 4px solid #00d4ff;
            padding-left: 15px;
            animation: fadeIn 1.2s ease;
        }
        
        /* Lights Grid - 4 Cards */
        .lights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        
        .light-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            animation: slideUp 0.8s ease;
        }
        
        .light-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 212, 255, 0.3);
        }
        
        .light-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        
        .light-name {
            font-size: 1.5em;
            font-weight: bold;
            color: #00d4ff;
        }
        
        .light-bulb {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5em;
            animation: pulse 2s infinite;
            font-weight: bold;
        }
        
        .light-on {
            background: rgba(0, 255, 136, 0.3);
            box-shadow: 0 0 30px rgba(0, 255, 136, 0.6);
            color: #00ff88;
        }
        
        .light-off {
            background: rgba(255, 68, 68, 0.2);
            box-shadow: 0 0 20px rgba(255, 68, 68, 0.4);
            color: #ff4444;
        }
        
        /* Light Info Grid */
        .light-info {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
            padding: 20px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }
        
        .info-item {
            text-align: center;
        }
        
        .info-label {
            font-size: 0.8em;
            color: #888;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .info-value {
            font-size: 1.3em;
            font-weight: bold;
            color: #00d4ff;
        }
        
        /* Status Badge */
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 25px;
            font-size: 0.9em;
            font-weight: bold;
            margin: 15px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .status-on {
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
            border: 2px solid #00ff88;
            box-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
        }
        
        .status-off {
            background: rgba(255, 68, 68, 0.2);
            color: #ff4444;
            border: 2px solid #ff4444;
            box-shadow: 0 0 10px rgba(255, 68, 68, 0.3);
        }
        
        /* Control Buttons */
        .control-buttons {
            display: flex;
            gap: 12px;
            margin-top: 20px;
        }
        
        .btn-control {
            flex: 1;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            font-size: 0.95em;
            letter-spacing: 1px;
        }
        
        .btn-on {
            background: linear-gradient(45deg, #00ff88, #00d4a0);
            color: #000;
            box-shadow: 0 4px 15px rgba(0, 255, 136, 0.3);
        }
        
        .btn-on:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0, 255, 136, 0.5);
        }
        
        .btn-off {
            background: linear-gradient(45deg, #ff4444, #ff6666);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 68, 68, 0.3);
        }
        
        .btn-off:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(255, 68, 68, 0.5);
        }
        
        .btn-control:active {
            transform: translateY(0);
        }
        
        /* Charts Section */
        .charts-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(550px, 1fr));
            gap: 30px;
            margin: 40px 0;
        }
        
        .chart-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chart-title {
            font-size: 1.4em;
            margin-bottom: 20px;
            color: #00d4ff;
            font-weight: bold;
        }
        
        canvas {
            max-height: 300px;
        }
        
        /* Last Update */
        .last-update {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #888;
            font-size: 1em;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 10px;
        }
        
        .last-update strong {
            color: #00d4ff;
        }
        
        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.08); opacity: 0.9; }
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            header {
                flex-direction: column;
                text-align: center;
            }
            .header-right {
                margin-top: 20px;
                text-align: center;
            }
            .charts-section {
                grid-template-columns: 1fr;
            }
            .lights-grid {
                grid-template-columns: 1fr;
            }
            .header-left h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <!-- HEADER -->
    <header>
        <div class="header-left">
            <h1>⚡ Smart Street Light Dashboard</h1>
            <p class="subtitle">Real-time Monitoring & Control System</p>
        </div>
        <div class="header-right">
            <div class="user-info">👤 Raspberry Pi</div>
            <div id="backend-status">🟢 Backend: Online</div>
        </div>
    </header>

    <div class="container">
        <!-- OVERALL STATS -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Voltage</div>
                <div class="stat-value" id="total-voltage">0<span class="stat-unit">V</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Current</div>
                <div class="stat-value" id="total-current">0<span class="stat-unit">A</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Luminosity</div>
                <div class="stat-value" id="total-lux">0<span class="stat-unit">Lux</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">System Status</div>
                <div class="stat-value" style="color: #00ff88">Active</div>
            </div>
        </div>
        
        <!-- 4 LIGHTS CONTROL SECTION -->
        <h2 class="section-title">💡 Individual Light Control (4 Lights)</h2>
        <div class="lights-grid">
            
            <!-- LIGHT 1 -->
            <div class="light-card" id="light-card-1">
                <div class="light-header">
                    <div class="light-name">Light 1</div>
                    <div class="light-bulb light-off" id="bulb-1">○</div>
                </div>
                <div class="light-info">
                    <div class="info-item">
                        <div class="info-label">Voltage</div>
                        <div class="info-value" id="voltage-1">0V</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Current</div>
                        <div class="info-value" id="current-1">0A</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Lux</div>
                        <div class="info-value" id="lux-1">0</div>
                    </div>
                </div>
                <div style="text-align: center;">
                    <span class="status-badge status-off" id="status-1">OFF</span>
                </div>
                <div class="control-buttons">
                    <button class="btn-control btn-on" onclick="controlLight(1, 'on')">⚡ Turn ON</button>
                    <button class="btn-control btn-off" onclick="controlLight(1, 'off')">⭕ Turn OFF</button>
                </div>
            </div>
            
            <!-- LIGHT 2 -->
            <div class="light-card" id="light-card-2">
                <div class="light-header">
                    <div class="light-name">Light 2</div>
                    <div class="light-bulb light-off" id="bulb-2">○</div>
                </div>
                <div class="light-info">
                    <div class="info-item">
                        <div class="info-label">Voltage</div>
                        <div class="info-value" id="voltage-2">0V</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Current</div>
                        <div class="info-value" id="current-2">0A</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Lux</div>
                        <div class="info-value" id="lux-2">0</div>
                    </div>
                </div>
                <div style="text-align: center;">
                    <span class="status-badge status-off" id="status-2">OFF</span>
                </div>
                <div class="control-buttons">
                    <button class="btn-control btn-on" onclick="controlLight(2, 'on')">⚡ Turn ON</button>
                    <button class="btn-control btn-off" onclick="controlLight(2, 'off')">⭕ Turn OFF</button>
                </div>
            </div>
            
            <!-- LIGHT 3 -->
            <div class="light-card" id="light-card-3">
                <div class="light-header">
                    <div class="light-name">Light 3</div>
                    <div class="light-bulb light-off" id="bulb-3">○</div>
                </div>
                <div class="light-info">
                    <div class="info-item">
                        <div class="info-label">Voltage</div>
                        <div class="info-value" id="voltage-3">0V</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Current</div>
                        <div class="info-value" id="current-3">0A</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Lux</div>
                        <div class="info-value" id="lux-3">0</div>
                    </div>
                </div>
                <div style="text-align: center;">
                    <span class="status-badge status-off" id="status-3">OFF</span>
                </div>
                <div class="control-buttons">
                    <button class="btn-control btn-on" onclick="controlLight(3, 'on')">⚡ Turn ON</button>
                    <button class="btn-control btn-off" onclick="controlLight(3, 'off')">⭕ Turn OFF</button>
                </div>
            </div>
            
            <!-- LIGHT 4 -->
            <div class="light-card" id="light-card-4">
                <div class="light-header">
                    <div class="light-name">Light 4</div>
                    <div class="light-bulb light-off" id="bulb-4">○</div>
                </div>
                <div class="light-info">
                    <div class="info-item">
                        <div class="info-label">Voltage</div>
                        <div class="info-value" id="voltage-4">0V</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Current</div>
                        <div class="info-value" id="current-4">0A</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Lux</div>
                        <div class="info-value" id="lux-4">0</div>
                    </div>
                </div>
                <div style="text-align: center;">
                    <span class="status-badge status-off" id="status-4">OFF</span>
                </div>
                <div class="control-buttons">
                    <button class="btn-control btn-on" onclick="controlLight(4, 'on')">⚡ Turn ON</button>
                    <button class="btn-control btn-off" onclick="controlLight(4, 'off')">⭕ Turn OFF</button>
                </div>
            </div>
            
        </div>
        
        <!-- PERFORMANCE GRAPHS -->
        <h2 class="section-title">📊 Performance Graphs</h2>
        <div class="charts-section">
            <div class="chart-card">
                <h3 class="chart-title">📈 Voltage Trend</h3>
                <canvas id="voltageChart"></canvas>
            </div>
            <div class="chart-card">
                <h3 class="chart-title">📊 Current Trend</h3>
                <canvas id="currentChart"></canvas>
            </div>
        </div>
        
        <!-- LAST UPDATE -->
        <div class="last-update" id="last-update-text">
            <strong>Last Updated:</strong> -- | <strong>Auto-refresh:</strong> Every 2 seconds
        </div>
    </div>
    
    <script>
        let voltageChart, currentChart;

        // Function to control lights
        async function controlLight(lightId, action) {
            try {
                const response = await fetch('/control', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({light_id: lightId, action: action})
                });

                const data = await response.json();

                if (data.success) {
                    console.log(Light ${lightId} ${action} successful);
                    // Immediately refresh to show changes
                    fetchData();
                } else {
                    alert('Control failed: ' + (data.message || 'unknown error'));
                }
            } catch (error) {
                console.error('Control error:', error);
                alert('Failed to control light. Check backend connection.');
            }
        }

        // Function to fetch data from backend API
        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();

                // Update backend status
                document.getElementById('backend-status').innerHTML = '🟢 Backend: Online';

                // Update individual lights
                updateLights(data.lights);

                // Update charts with real data
                updateCharts(data.charts);

                // Update last update time
                document.getElementById('last-update-text').innerHTML =
                    <strong>Last Updated:</strong> ${data.time} | <strong>Auto-refresh:</strong> Every 2 seconds;

            } catch (error) {
                console.error('Fetch error:', error);
                document.getElementById('backend-status').innerHTML = '🔴 Backend: Offline';
            }
        }

        // Function to update light displays
        function updateLights(lights) {
            let totalLux = 0;
            let totalVoltage = 0;
            let totalCurrent = 0;

            // Update each light (1-4)
            for (let i = 0; i < 4; i++) {
                const light = lights[i];

                if (light) {
                    const isOn = light.relay_state === 'ON';

                    // Update bulb icon
                    const bulb = document.getElementById(bulb-${i+1});
                    bulb.className = isOn ? 'light-bulb light-on' : 'light-bulb light-off';
                    bulb.textContent = isOn ? '●' : '○';

                    // Update voltage, current, and lux from backend data
                    const voltage = light.voltage;
                    const current = light.current;
                    const luxValue = light.lux;

                    document.getElementById(voltage-${i+1}).textContent = ${voltage}V;
                    document.getElementById(current-${i+1}).textContent = ${current}A;
                    document.getElementById(lux-${i+1}).textContent = luxValue;

                    // Accumulate totals
                    totalVoltage += voltage;
                    totalCurrent += current;
                    totalLux += luxValue;

                    // Update status badge
                    const statusBadge = document.getElementById(status-${i+1});
                    statusBadge.className = isOn ? 'status-badge status-on' : 'status-badge status-off';
                    statusBadge.textContent = light.relay_state;
                }
            }

            // Update overall stats
            document.getElementById('total-voltage').innerHTML = ${totalVoltage.toFixed(1)}<span class="stat-unit">V</span>;
            document.getElementById('total-current').innerHTML = ${totalCurrent.toFixed(1)}<span class="stat-unit">A</span>;
            document.getElementById('total-lux').innerHTML = ${totalLux}<span class="stat-unit">Lux</span>;
        }

        // Function to update charts with real data
        function updateCharts(charts) {
            if (charts && voltageChart && currentChart) {
                // Update voltage chart
                if (charts.voltage) {
                    voltageChart.data.labels = charts.voltage.labels;
                    voltageChart.data.datasets[0].data = charts.voltage.data;
                    voltageChart.update();
                }

                // Update current chart
                if (charts.current) {
                    currentChart.data.labels = charts.current.labels;
                    currentChart.data.datasets[0].data = charts.current.data;
                    currentChart.update();
                }
            }
        }

        // Initialize Charts
        document.addEventListener('DOMContentLoaded', function() {
            // Voltage Chart
            const voltageCtx = document.getElementById('voltageChart').getContext('2d');
            voltageChart = new Chart(voltageCtx, {
                type: 'line',
                data: {
                    labels: ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00'],
                    datasets: [{
                        label: 'Voltage (V)',
                        data: [0, 0, 0, 0, 0, 0],
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#fff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#aaa'
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#aaa'
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            }
                        }
                    }
                }
            });

            // Current Chart
            const currentCtx = document.getElementById('currentChart').getContext('2d');
            currentChart = new Chart(currentCtx, {
                type: 'line',
                data: {
                    labels: ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00'],
                    datasets: [{
                        label: 'Current (A)',
                        data: [0, 0, 0, 0, 0, 0],
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            labels: {
                                color: '#fff'
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                color: '#aaa'
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            }
                        },
                        y: {
                            ticks: {
                                color: '#aaa'
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            }
                        }
                    }
                }
            });

            // Start fetching data every 2 seconds
            fetchData(); // Initial fetch
            setInterval(fetchData, 2000);
        });
    </script>
</body>
</html>
"""
# ========== END OF HTML TEMPLATE ==========

# ------------------ Flask Routes ------------------
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/control', methods=['POST'])
def control():
    """Control endpoint to turn lights on/off via relay"""
    try:
        payload = request.get_json(force=True)
        light_id = int(payload.get("light_id", 0))
        action = payload.get("action", "").lower()
    except Exception as e:
        return jsonify({"success": False, "message": "Invalid JSON payload"}), 400

    idx = light_id - 1
    if idx < 0 or idx >= len(RELAY_PINS):
        return jsonify({"success": False, "message": "Invalid light id"}), 400

    if action == "on":
        GPIO.output(RELAY_PINS[idx], GPIO.LOW)
        lights_data[idx]["relay_state"] = "ON"
        print(f"✅ Light {light_id} turned ON (via web)")
    elif action == "off":
        GPIO.output(RELAY_PINS[idx], GPIO.HIGH)
        lights_data[idx]["relay_state"] = "OFF"
        print(f"❌ Light {light_id} turned OFF (via web)")
    else:
        return jsonify({"success": False, "message": "Invalid action"}), 400

    return jsonify({"success": True, "status": lights_data[idx]["relay_state"]})

@app.route('/api/data')
def get_data():
    """Return current status of all lights with chart data"""
    # Update chart history
    current_time = datetime.now().strftime("%H:%M")
    time_labels.append(current_time)
    
    # Calculate totals for history
    total_voltage = sum(light["voltage"] for light in lights_data)
    total_current = sum(light["current"] for light in lights_data)
    
    voltage_history.append(total_voltage)
    current_history.append(total_current)
    
    return jsonify({
        "lights": lights_data,
        "time": datetime.now().strftime("%H:%M:%S"),
        "charts": {
            "voltage": {
                "labels": list(time_labels),
                "data": list(voltage_history)
            },
            "current": {
                "labels": list(time_labels),
                "data": list(current_history)
            }
        }
    })

# ------------------ Hardware Functions ------------------
def read_ldr(ldr_index):
    """Read LDR sensor value"""
    if 0 <= ldr_index < len(LDR_PINS):
        ldr_state = GPIO.input(LDR_PINS[ldr_index])
        lux = 100 if ldr_state == GPIO.HIGH else 0
        return lux
    return 0

def auto_control_lights():
    """Automatically control lights based on LDR readings"""
    for i in range(4):
        lux = lights_data[i]["lux"]
        current_status = lights_data[i]["relay_state"]
        
        if lux == 0 and current_status == "OFF":
            GPIO.output(RELAY_PINS[i], GPIO.HIGH)
            lights_data[i]["relay_state"] = "ON"
            print(f"🤖 Auto: Light {i+1} turned ON (dark detected)")
        elif lux > 0 and current_status == "ON":
            GPIO.output(RELAY_PINS[i], GPIO.LOW)
            lights_data[i]["relay_state"] = "OFF"
            print(f"🤖 Auto: Light {i+1} turned OFF (bright detected)")

# ------------------ Sensor Loop ------------------
def sensor_loop(stop_event):
    """Continuously read LDR sensors"""
    while not stop_event.is_set():
        # Read all sensors
        for i in range(4):
            lux = read_ldr(i)
            lights_data[i]["lux"] = lux
            # Voltage and current remain 0 (no sensors connected)
            lights_data[i]["voltage"] = 0
            lights_data[i]["current"] = 0
        
        # Auto control if enabled
        if AUTO_MODE:
            auto_control_lights()
        
        # Sleep
        for _ in range(int(SAMPLE_INTERVAL)):
            if stop_event.is_set():
                break
            time.sleep(1)

# ------------------ MAIN ------------------
def main():
    stop_event = threading.Event()
    sensor_thread = threading.Thread(target=sensor_loop, args=(stop_event,), daemon=True)
    sensor_thread.start()

    def handle_sigterm(signum, frame):
        print("\n🛑 Shutdown signal received, cleaning up...")
        stop_event.set()
        for pin in RELAY_PINS:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()
        time.sleep(0.5)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        print("🚀 Starting Smart Street Light Dashboard on http://0.0.0.0:5000")
        print("📡 Monitoring 4 lights with LDR sensors")
        print(f"🤖 Auto mode: {'ENABLED' if AUTO_MODE else 'DISABLED'}")
        print("🌐 Web interface: http://your-raspberry-pi-ip:5000")
        print("\nPress Ctrl+C to stop\n")
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        stop_event.set()
        for pin in RELAY_PINS:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()

if _name_ == "_main_":
    main()