# ESP32 Solar Boiler Temperature Monitor

Web-based temperature monitoring system using a DS18B20 sensor connected to a **Heltec WiFi LoRa 32 (V2)** board. Reads temperature every 10 seconds and displays a live chart with up to 24 hours of history.

---

## What You Need

| # | Item | Notes |
|---|------|-------|
| 1 | Heltec WiFi LoRa 32 V2 | The development board |
| 2 | DS18B20 temperature sensor (3-wire) | Red, Black, Yellow wires |
| 3 | 4.7 kΩ resistor | Pull-up resistor (essential!) |
| 4 | Breadboard | For easy prototyping |
| 5 | Jumper wires | Male-to-male, 3 pieces |
| 6 | Micro-USB cable | To connect the board to your computer |
| 7 | Computer | With Windows, macOS, or Linux |

---

## Step-by-Step Guide

### PART 1 — Hardware Wiring

The Heltec WiFi LoRa 32 V2 uses GPIO 4 and GPIO 15 for its built-in OLED display, so we use **GPIO 22** for the sensor.

#### 1.1 Identify the DS18B20 wires

Your DS18B20 has three wires:

```
  Red    = VCC (power, 3.3V)
  Black  = GND (ground)
  Yellow = DATA (signal)
```

#### 1.2 Identify the Heltec board pins

Look at your Heltec board with the USB connector pointing **down**. The pins we need are:

```
  3.3V  — on the left header, labeled "3V3"
  GND   — on the left header, labeled "GND"
  GPIO 22 — on the right header, labeled "22"
```

#### 1.3 Connect everything on a breadboard

```
                    Heltec WiFi LoRa 32 V2
                   ┌──────────────────────┐
                   │                      │
          3V3  ●───┤ 3V3            13    ├───● GPIO 22
                   │                      │
          GND  ●───┤ GND                  │
                   │                      │
                   │      [USB PORT]      │
                   └──────────────────────┘

DS18B20 Wiring:
                         4.7 kΩ
               3V3 ●────┤RESISTOR├────● GPIO 22
                         (pull-up)     │
                                       │
  DS18B20 Red (VCC)    ──────────────── 3V3
  DS18B20 Black (GND)  ──────────────── GND
  DS18B20 Yellow (DATA) ──────────────── GPIO 22
```

**Wire-by-wire instructions:**

1. Plug the Heltec board into the breadboard (straddling the center channel)
2. Connect **DS18B20 Red wire** → breadboard row connected to **3V3** pin
3. Connect **DS18B20 Black wire** → breadboard row connected to **GND** pin
4. Connect **DS18B20 Yellow wire** → breadboard row connected to **GPIO 22** pin
5. Place the **4.7 kΩ resistor** between the **3V3 row** and the **GPIO 22 row**

> **Important:** The 4.7 kΩ pull-up resistor between DATA and 3V3 is essential. Without it, the sensor will not be detected.

#### 1.4 Verify your wiring

Double-check before powering on:
- Red wire goes to 3V3 (NOT 5V)
- Black wire goes to GND
- Yellow wire goes to GPIO 22
- Resistor bridges between 3V3 and GPIO 22
- No wires are touching each other where they shouldn't

---

### PART 2 — Install Software on Your Computer

#### 2.1 Install Python

If you don't have Python installed:

- **Windows**: Download from https://www.python.org/downloads/ — check "Add Python to PATH" during install
- **macOS**: `brew install python3` or download from python.org
- **Linux**: `sudo apt install python3 python3-pip`

Verify:
```bash
python3 --version
```

#### 2.2 Install the required tools

Open a terminal (Command Prompt on Windows) and run:

```bash
pip install esptool mpremote
```

#### 2.3 Install the USB driver (if needed)

The Heltec V2 uses a **CP2102** USB-to-serial chip. Most modern operating systems include the driver, but if your board isn't recognized:

- **Windows/macOS**: Download the CP2102 driver from https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- **Linux**: The driver (`cp210x`) is built into the kernel — no action needed

#### 2.4 Connect the board and find the serial port

Plug the Heltec board into your computer with the micro-USB cable.

Find the port name:

- **Linux**: `ls /dev/ttyUSB*` → typically `/dev/ttyUSB0`
- **macOS**: `ls /dev/cu.SLAB*` → typically `/dev/cu.SLAB_USBtoUART`
- **Windows**: Open Device Manager → Ports (COM & LPT) → look for "Silicon Labs CP210x" → note the COM port (e.g., `COM3`)

---

### PART 3 — Flash MicroPython Firmware

#### 3.1 Download MicroPython firmware

Go to: https://micropython.org/download/ESP32_GENERIC/

Download the latest **`.bin`** file (e.g., `ESP32_GENERIC-20xxxxxx-vX.X.X.bin`).

Save it to a known folder (e.g., your Downloads folder).

#### 3.2 Erase the board's flash memory

Replace `/dev/ttyUSB0` with your actual port from step 2.4:

```bash
esptool.py --port /dev/ttyUSB0 erase_flash
```

**Windows example:**
```bash
esptool.py --port COM3 erase_flash
```

You should see output ending with `Chip erase completed successfully`.

#### 3.3 Flash the MicroPython firmware

Replace the port and `.bin` filename with your actual values:

```bash
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20xxxxxx-vX.X.X.bin
```

Wait for it to finish. You should see `Hash of data verified`.

#### 3.4 Verify MicroPython is running

```bash
mpremote connect /dev/ttyUSB0 repl
```

You should see the MicroPython REPL prompt `>>>`. Type:

```python
print("Hello from Heltec!")
```

Press **Ctrl+]** to exit the REPL.

---

### PART 4 — Configure and Upload the Code

#### 4.1 Edit WiFi credentials

Open the file `config.py` in any text editor and change:

```python
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
```

Save the file.

#### 4.2 Upload both files to the board

```bash
mpremote connect /dev/ttyUSB0 cp config.py :config.py
mpremote connect /dev/ttyUSB0 cp main.py :main.py
```

**Windows example:**
```bash
mpremote connect COM3 cp config.py :config.py
mpremote connect COM3 cp main.py :main.py
```

#### 4.3 Verify files were uploaded

```bash
mpremote connect /dev/ttyUSB0 ls
```

You should see `config.py` and `main.py` listed.

---

### PART 5 — Run and View the Dashboard

#### 5.1 Reset the board

Either:
- Press the **RST** button on the Heltec board, or
- Unplug and re-plug the USB cable

#### 5.2 Find the IP address

Open the serial monitor to see the board's output:

```bash
mpremote connect /dev/ttyUSB0 repl
```

You should see output like:

```
Connecting to WiFi …
Connected – IP: 192.168.1.105
Found DS18B20 sensor(s): ['28ff1234abcd']
Web server listening on http://192.168.1.105:80
Temp: 25.31 °C
Temp: 25.37 °C
```

**Write down the IP address** (e.g., `192.168.1.105`).

Press **Ctrl+]** to exit the REPL (the board keeps running).

#### 5.3 Open the dashboard in a web browser

On any device connected to the **same WiFi network**, open a web browser and go to:

```
http://192.168.1.105
```

(Replace with your actual IP address from step 5.2.)

You will see:
- The **current temperature** in large text
- A **live chart** that updates every 10 seconds
- **Time range buttons** (1h, 6h, 12h, 24h) to zoom in/out

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No DS18B20 sensor found` | Check wiring. Make sure the 4.7 kΩ pull-up resistor is in place between DATA and 3V3. |
| `WiFi connection failed` | Verify SSID and password in `config.py`. The ESP32 only supports **2.4 GHz WiFi** (not 5 GHz). |
| Board not detected by computer | Install the CP2102 driver (step 2.3). Try a different USB cable (some are charge-only). |
| `esptool.py` can't connect | Hold the **PRG** button on the board while running the esptool command, release after "Connecting…" appears. |
| Browser can't reach the page | Make sure your phone/computer is on the **same WiFi network** as the ESP32. |
| Chart not loading | The viewing device needs **internet access** to load Chart.js from CDN. |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | HTML dashboard |
| `GET /api/readings` | JSON with all stored `{timestamps, temperatures}` |
| `GET /api/current` | JSON with latest `{timestamp, temperature}` |

## Notes

- The ESP32 stores up to 8,640 readings in RAM (24h at 10s intervals)
- Data is lost on power loss or reset (no persistent storage)
- MicroPython epoch starts at 2000-01-01; the dashboard handles the conversion
- The Heltec V2's built-in OLED and LoRa are not used by this project but remain available for future enhancements
