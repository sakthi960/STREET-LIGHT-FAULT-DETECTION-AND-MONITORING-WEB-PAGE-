// Backend URL for Raspberry Pi
const backendUrl = 'http://10.32.60.212:5000';

let voltageChart, currentChart;

// Function to control lights
async function controlLight(lightId, action) {
    try {
        const response = await fetch(`${backendUrl}/control`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({light_id: lightId, action: action})
        });

        const data = await response.json();

        if (data.success) {
            console.log(`Light ${lightId} ${action} successful`);
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
        const response = await fetch(`${backendUrl}/api/data`);
        const data = await response.json();

        // Update backend status
        document.getElementById('backend-status').innerHTML = '🟢 Backend: Online';

        // Update individual lights
        updateLights(data.lights);

        // Update charts with real data
        updateCharts(data.charts);

        // Update last update time
        document.getElementById('last-update-text').innerHTML =
            `<strong>Last Updated:</strong> ${data.time} | <strong>Auto-refresh:</strong> Every 2 seconds`;

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
            const bulb = document.getElementById(`bulb-${i+1}`);
            bulb.className = isOn ? 'light-bulb light-on' : 'light-bulb light-off';
            bulb.textContent = isOn ? '●' : '○';

            // Update voltage, current, and lux from backend data
            const voltage = light.voltage;
            const current = light.current;
            const luxValue = light.lux;

            document.getElementById(`voltage-${i+1}`).textContent = `${voltage}V`;
            document.getElementById(`current-${i+1}`).textContent = `${current}A`;
            document.getElementById(`lux-${i+1}`).textContent = luxValue;

            // Accumulate totals
            totalVoltage += voltage;
            totalCurrent += current;
            totalLux += luxValue;

            // Update status badge
            const statusBadge = document.getElementById(`status-${i+1}`);
            statusBadge.className = isOn ? 'status-badge status-on' : 'status-badge status-off';
            statusBadge.textContent = light.relay_state;
        }
    }

    // Update overall stats
    document.getElementById('total-voltage').innerHTML = `${totalVoltage.toFixed(1)}<span class="stat-unit">V</span>`;
    document.getElementById('total-current').innerHTML = `${totalCurrent.toFixed(1)}<span class="stat-unit">A</span>`;
    document.getElementById('total-lux').innerHTML = `${totalLux}<span class="stat-unit">Lux</span>`;
}

// Function to update charts with real data
function updateCharts(charts) {
    if (charts && voltageChart && currentChart) {
        // Update voltage chart
        if (charts.voltage) {
            // If structure matches nested: charts.voltage.data & charts.voltage.labels
            if (charts.voltage.data && charts.voltage.labels) {
                voltageChart.data.labels = charts.voltage.labels;
                voltageChart.data.datasets[0].data = charts.voltage.data;
            } else if (Array.isArray(charts.voltage) && charts.labels) {
                // fallback if server returns flat arrays
                voltageChart.data.labels = charts.labels;
                voltageChart.data.datasets[0].data = charts.voltage;
            }
            voltageChart.update();
        }

        // Update current chart
        if (charts.current) {
            if (charts.current.data && charts.current.labels) {
                currentChart.data.labels = charts.current.labels;
                currentChart.data.datasets[0].data = charts.current.data;
            } else if (Array.isArray(charts.current) && charts.labels) {
                currentChart.data.labels = charts.labels;
                currentChart.data.datasets[0].data = charts.current;
            }
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