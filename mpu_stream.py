from flask import Flask, render_template_string
from flask_socketio import SocketIO
import time
import board
import busio
import adafruit_mpu6050
import threading

# 1. Initialize Flask and SocketIO Web Server
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 2. Initialize I2C Bus and MPU6050 Sensor Hardware
i2c = busio.I2C(board.SCL, board.SDA)
mpu = adafruit_mpu6050.MPU6050(i2c)

# 3. Embedded HTML & JavaScript Dashboard Interface
html_dashboard = """
<!DOCTYPE html>
<html>
<head>
    <title>MPU6050 Real-Time Telemetry</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { background-color: #1a1a1a; color: #e0e0e0; font-family: 'Courier New', monospace; text-align: center; padding-top: 50px; }
        h1 { color: #ffffff; font-size: 2.5em; text-transform: uppercase; letter-spacing: 2px; }
        .container { display: flex; justify-content: center; gap: 30px; margin-top: 40px; }
        .card { background-color: #2d2d2d; border: 2px solid #444; border-radius: 8px; padding: 20px; width: 180px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
        .label { font-size: 1.2em; color: #888; text-transform: uppercase; }
        .value { font-size: 2.5em; font-weight: bold; margin-top: 10px; }
        #x_card { border-color: #ff5555; .value { color: #ff5555; } }
        #y_card { border-color: #55ff55; .value { color: #55ff55; } }
        #z_card { border-color: #5555ff; .value { color: #5555ff; } }
    </style>
</head>
<body>
    <h1>IMU Accelerometer Telemetry</h1>
    <div class="container">
        <div class="card" id="x_card">
            <div class="label">Accel X</div>
            <div class="value" id="x_val">0.00</div>
        </div>
        <div class="card" id="y_card">
            <div class="label">Accel Y</div>
            <div class="value" id="y_val">0.00</div>
        </div>
        <div class="card" id="z_card">
            <div class="label">Accel Z</div>
            <div class="value" id="z_val">0.00</div>
        </div>
    </div>

    <script>
        // Establish permanent WebSocket connection back to the backend server
        var socket = io();

        // Listen for the specific 'telemetry_update' event pushed by the Pi
        socket.on('telemetry_update', function(data) {
            document.getElementById('x_val').innerText = data.x.toFixed(2);
            document.getElementById('y_val').innerText = data.y.toFixed(2);
            document.getElementById('z_val').innerText = data.z.toFixed(2);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_dashboard)

# 4. Background Thread to Stream Sensor Data Continuously
def stream_sensor_data():
    while True:
        try:
            # Read raw data directly from the MPU6050 registers via I2C
            accel_x, accel_y, accel_z = mpu.acceleration
            
            # Broadcast the telemetry payload to all connected WebSocket clients globally
            socketio.emit('telemetry_update', {
                'x': accel_x,
                'y': accel_y,
                'z': accel_z
            })
        except Exception as e:
            print(f"Sensor read error: {e}")
            
        # Sample rate delay: 50ms (corresponds to a smooth 20Hz refresh rate)
        time.sleep(0.05)

if __name__ == '__main__':
    print("Initializing background telemetry thread...")
    threading.Thread(target=stream_sensor_data, daemon=True).start()
    
    print("Launching Web Server on home network interface...")
    # Bind to 0.0.0.0 to listen to requests from your laptop on your home router
    socketio.run(app, host='0.0.0.0', port=8080)
