import machine
import onewire
import ds18x20
import network
import time
import json
import socket
import _thread

from config import (
    WIFI_SSID, WIFI_PASSWORD, SENSOR_PIN, READ_INTERVAL,
    MAX_READINGS, WEB_PORT,
)

readings = []
readings_lock = _thread.allocate_lock()


def add_reading(timestamp, temp):
    with readings_lock:
        readings.append((timestamp, temp))
        if len(readings) > MAX_READINGS:
            readings.pop(0)


def get_readings_json():
    with readings_lock:
        data = list(readings)
    return json.dumps({
        "timestamps": [r[0] for r in data],
        "temperatures": [r[1] for r in data],
    })


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi …")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Connected – IP:", ip)
        return ip
    else:
        raise RuntimeError("WiFi connection failed")


def init_sensor():
    pin = machine.Pin(SENSOR_PIN)
    ow = onewire.OneWire(pin)
    sensor = ds18x20.DS18X20(ow)
    roms = sensor.scan()
    if not roms:
        raise RuntimeError("No DS18B20 sensor found")
    print("Found DS18B20 sensor(s):", [rom.hex() for rom in roms])
    return sensor, roms


def read_temperature(sensor, roms):
    sensor.convert_temp()
    time.sleep_ms(750)
    return sensor.read_temp(roms[0])


def sensor_loop(sensor, roms):
    while True:
        try:
            temp = read_temperature(sensor, roms)
            ts = time.time()
            add_reading(ts, round(temp, 2))
            print("Temp: {:.2f} °C".format(temp))
        except Exception as e:
            print("Sensor read error:", e)
        time.sleep(READ_INTERVAL)


def serve_web(ip):
    addr = socket.getaddrinfo(ip, WEB_PORT)[0][-1]
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(addr)
    srv.listen(3)
    print("Web server listening on http://{}:{}".format(ip, WEB_PORT))

    while True:
        cl, remote = srv.accept()
        try:
            request = cl.recv(1024).decode("utf-8")
            path = request.split(" ")[1] if len(request.split(" ")) > 1 else "/"

            if path == "/api/readings":
                body = get_readings_json()
                cl.send("HTTP/1.1 200 OK\r\n")
                cl.send("Content-Type: application/json\r\n")
                cl.send("Access-Control-Allow-Origin: *\r\n")
                cl.send("Connection: close\r\n\r\n")
                cl.send(body)
            elif path == "/api/current":
                with readings_lock:
                    last = readings[-1] if readings else (0, None)
                body = json.dumps({
                    "timestamp": last[0],
                    "temperature": last[1],
                })
                cl.send("HTTP/1.1 200 OK\r\n")
                cl.send("Content-Type: application/json\r\n")
                cl.send("Access-Control-Allow-Origin: *\r\n")
                cl.send("Connection: close\r\n\r\n")
                cl.send(body)
            else:
                cl.send("HTTP/1.1 200 OK\r\n")
                cl.send("Content-Type: text/html\r\n")
                cl.send("Connection: close\r\n\r\n")
                cl.send(HTML_PAGE)
        except Exception as e:
            print("Request error:", e)
        finally:
            cl.close()


HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Solar Boiler – Temperature Monitor</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a; color: #e2e8f0;
    display: flex; flex-direction: column; align-items: center;
    min-height: 100vh; padding: 1rem;
  }
  h1 { margin: 1rem 0 0.25rem; font-size: 1.5rem; }
  .current { font-size: 2.5rem; font-weight: 700; color: #38bdf8; margin-bottom: 1rem; }
  .chart-container { width: 95%; max-width: 1100px; position: relative; }
  canvas { width: 100% !important; }
  .status { margin-top: 0.5rem; font-size: 0.85rem; color: #94a3b8; }
  .range-buttons { margin: 0.75rem 0; display: flex; gap: 0.5rem; }
  .range-buttons button {
    background: #1e293b; color: #94a3b8; border: 1px solid #334155;
    padding: 0.35rem 0.9rem; border-radius: 6px; cursor: pointer;
    font-size: 0.85rem;
  }
  .range-buttons button.active { background: #38bdf8; color: #0f172a; border-color: #38bdf8; }
</style>
</head>
<body>
  <h1>Solar Boiler – Hot Water Temperature</h1>
  <div class="current" id="currentTemp">-- &deg;C</div>
  <div class="range-buttons" id="rangeButtons">
    <button data-hours="1">1 h</button>
    <button data-hours="6">6 h</button>
    <button data-hours="12">12 h</button>
    <button data-hours="24" class="active">24 h</button>
  </div>
  <div class="chart-container">
    <canvas id="tempChart"></canvas>
  </div>
  <div class="status" id="status">Loading…</div>
<script>
(function() {
  const POLL_MS = 10000;
  let rangeHours = 24;
  let chart;
  let allTimestamps = [];
  let allTemps = [];

  function epochToDate(epoch) {
    return new Date((epoch + 946684800) * 1000);
  }

  function initChart() {
    const ctx = document.getElementById('tempChart').getContext('2d');
    chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Temperature (°C)',
          data: [],
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56,189,248,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            type: 'time',
            time: { tooltipFormat: 'HH:mm:ss', displayFormats: { minute: 'HH:mm', hour: 'HH:mm' } },
            ticks: { color: '#64748b', maxTicksLimit: 12 },
            grid: { color: '#1e293b' },
          },
          y: {
            title: { display: true, text: '°C', color: '#94a3b8' },
            ticks: { color: '#64748b' },
            grid: { color: '#1e293b' },
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) { return ctx.parsed.y.toFixed(2) + ' °C'; }
            }
          }
        }
      }
    });
  }

  function updateChart() {
    const now = new Date();
    const cutoff = new Date(now.getTime() - rangeHours * 3600000);
    const filtered = [];
    const filteredLabels = [];
    for (let i = 0; i < allTimestamps.length; i++) {
      const d = epochToDate(allTimestamps[i]);
      if (d >= cutoff) {
        filteredLabels.push(d);
        filtered.push(allTemps[i]);
      }
    }
    chart.data.labels = filteredLabels;
    chart.data.datasets[0].data = filtered;
    chart.update();
  }

  async function fetchReadings() {
    try {
      const res = await fetch('/api/readings');
      const data = await res.json();
      allTimestamps = data.timestamps;
      allTemps = data.temperatures;
      if (allTemps.length > 0) {
        document.getElementById('currentTemp').textContent =
          allTemps[allTemps.length - 1].toFixed(2) + ' °C';
      }
      updateChart();
      document.getElementById('status').textContent =
        'Last update: ' + new Date().toLocaleTimeString() +
        '  |  Readings: ' + allTemps.length;
    } catch (e) {
      document.getElementById('status').textContent = 'Error: ' + e;
    }
  }

  document.getElementById('rangeButtons').addEventListener('click', function(e) {
    if (e.target.tagName !== 'BUTTON') return;
    document.querySelectorAll('.range-buttons button').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    rangeHours = parseInt(e.target.dataset.hours);
    updateChart();
  });

  initChart();
  fetchReadings();
  setInterval(fetchReadings, POLL_MS);
})();
</script>
</body>
</html>
"""


def main():
    ip = connect_wifi()
    sensor, roms = init_sensor()
    _thread.start_new_thread(sensor_loop, (sensor, roms))
    serve_web(ip)


main()
