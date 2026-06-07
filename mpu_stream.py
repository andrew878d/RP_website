from flask import Flask, render_template_string, send_from_directory
from flask_socketio import SocketIO
import board
import busio
import adafruit_mpu6050
import os

# 1. Initialize Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 2. Initialize MPU6050 Hardware via I2C
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    mpu = adafruit_mpu6050.MPU6050(i2c)
except Exception as e:
    print(f"I2C Hardware Error: {e}")
    mpu = None

# 3. Web Dashboard with Local Script Loading and Dynamic URL Connection
html_dashboard = """
<!DOCTYPE html>
<html>
<head>
    <title>MPU6050 Telemetry & Lag Test</title>
    <script src="/static/socket.io.js"></script>
    <style>
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Courier New', monospace; text-align: center; padding-top: 30px; }
        h1 { color: #ffffff; font-size: 2.2em; text-transform: uppercase; letter-spacing: 2px; }
        .container { display: flex; justify-content: center; gap: 20px; margin-top: 30px; }
        .card { background-color: #2d2d2d; border: 2px solid #444; border-radius: 8px; padding: 15px; width: 150px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
        .label { font-size: 1em; color: #888; text-transform: uppercase; }
        .value { font-size: 2em; font-weight: bold; margin-top: 10px; }
        #x_card { border-color: #ff5555; .value { color: #ff5555; } }
        #y_card { border-color: #55ff55; .value { color: #55ff55; } }
        #z_card { border-color: #5555ff; .value { color: #5555ff; } }
        .lag-container { margin-top: 40px; font-size: 1.2em; }
        .lag-value { font-size: 3.5em; font-weight: bold; color: #ffaa00; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>IMU Telemetry & Network Latency</h1>
    
    <div class="container">
        <div class="card" id="x_card"><div class="label">Accel X</div><div class="value" id="x_val">0.00</div></div>
        <div class="card" id="y_card"><div class="label">Accel Y</div><div class="value" id="y_val">0.00</div></div>
        <div class="card" id="z_card"><div class="label">Accel Z</div><div class="value" id="z_val">0.00</div></div>
    </div>

    <div class="lag-container">
        <div>One-Way Sensor Transfer Lag:</div>
        <div class="lag-value"><span id="lag_val">0</span> ms</div>
    </div>

    <script>
        // FIX 2: Explicitly point the WebSocket to the exact IP/domain used in the browser URL bar
        var socket = io(window.location.origin);

        // 1. Request sensor data from the Pi, stamped with the Mac's exact time
        function pullTelemetry() {
            socket.emit('request_telemetry', Date.now());
        }

        // 2. When the Pi responds, process data and calculate lag immediately
        socket.on('telemetry_response', function(data) {
            document.getElementById('x_val').innerText = data.x.toFixed(2);
            document.getElementById('y_val').innerText = data.y.toFixed(2);
            document.getElementById('z_val').innerText = data.z.toFixed(2);
            
            let roundTripTime = Date.now() - data.client_timestamp;
            let oneWayLag = roundTripTime / 2;
            
            document.getElementById('lag_val').innerText = oneWayLag.toFixed(1);

            // Wait 50ms then request the next frame
            setTimeout(pullTelemetry, 50);
        });

        socket.on('connect', function() {
            pullTelemetry();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_dashboard)

# FIX 3: Add an explicit Flask route to serve the local JS file to the browser
@app.route('/static/socket.io.js')
def serve_js():
    return send_from_directory(os.path.join(app.root_path, 'templates'), 'socket.io.js')

# 4. Listen for the Mac's pull requests
@socketio.on('request_telemetry')
def handle_telemetry_request(client_timestamp):
    try:
        if mpu:
            accel_x, accel_y, accel_z = mpu.acceleration
        else:
            accel_x, accel_y, accel_z = 0.0, 0.0, 0.0
        
        payload = {
            'x': accel_x,
            'y': accel_y,
            'z': accel_z,
            'client_timestamp': client_timestamp
        }
    except Exception as e:
        payload = {'x': 0, 'y': 0, 'z': 0, 'client_timestamp': client_timestamp}
        print(f"I2C Read Error: {e}")

    socketio.emit('telemetry_response', payload)

if __name__ == '__main__':
    print("Launching Universal Telemetry & Latency Server...")
    # FIX 4: Add allow_unsafe_werkzeug=True to prevent production server blocks when running offline
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True)
