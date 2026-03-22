# E-scooter System

![Supported Python version](https://img.shields.io/badge/python-3.12-blue)

An IoT-based e-scooter rental system that uses **magnetism to enforce designated parking zones**. Scooters can only be locked and returned in areas where a magnet is detected by the onboard magnetometer, preventing users from parking outside valid zones.

The system consists of three components:

1. **Scooter** — State machine running on a Raspberry Pi (or in simulation mode on any computer) that manages scooter state and checks for magnetic parking zones.
2. **Server** — HTTP + MQTT backend that coordinates scooter availability, claims, and rentals.
3. **User App** — GUI application for users to list, claim, rent, and return scooters.

## Project Structure

```
scooter/
    ScooterClient.py    # MQTT client, receives commands from server
    ScooterLogic.py     # State machine (off -> available -> claimed -> rented)
    ZoneLogic.py        # Magnetometer reading / parking zone detection
    Display.py          # Sense HAT display (or silent in simulation mode)
    BatteryLogic.py     # Battery drain logic
    requirements.txt
server/
    serverapp.py        # HTTP server + MQTT bridge
    requirements.txt
userapp/
    userapp.py          # GUI client (appJar/Tkinter)
    requirements.txt
```

## Quick Start (Simulation Mode)

Run the full system on any computer **without a Raspberry Pi**. The magnetometer is simulated via keyboard input — press Enter to toggle whether the scooter is in a parking zone.

**Requirements:** Python 3.12, Tkinter (`brew install python-tk@3.12` on macOS)

Open **3 separate terminals**:

### Terminal 1 — Server

```bash
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python serverapp.py 127.0.0.1 8080
```

### Terminal 2 — Scooter

```bash
cd scooter
python -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
python ScooterClient.py --id 1234
```

### Terminal 3 — User App

```bash
cd userapp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python userapp.py 127.0.0.1 8080
```

## Demo Walkthrough

1. **List scooters** — In the User App GUI, click "List nearby scooters". Scooter 1234 appears.
2. **Claim** — Click "ID: 1234 - Claim". The scooter is reserved for you (10s timeout).
3. **Rent** — Click "ID: 1234 - Rent". The scooter unlocks and the ride begins. Battery starts draining.
4. **Try to park (fail)** — Click "ID: 1234 - Stop rental". The scooter checks the magnetometer and rejects the parking because no magnet is detected.
5. **Simulate entering a parking zone** — In Terminal 2 (scooter), **press Enter**. This simulates the scooter detecting a magnet.
6. **Park successfully** — Click "ID: 1234 - Stop rental" again. The scooter detects the magnet and allows parking. The ride ends.

### What you will see in the terminals

**Scooter terminal (parking denied, then approved):**
```
[ACTION] User wants to park - checking parking zone...
[MAGNET] Sensor reading: no magnet detected (not in parking zone)
[RESULT] PARKING DENIED - scooter is NOT in a valid parking zone

  (press Enter)
[MAGNET] Magnet DETECTED - scooter is now in a parking zone

[ACTION] User wants to park - checking parking zone...
[MAGNET] Sensor reading: magnet detected (in parking zone)
[RESULT] PARKING APPROVED - scooter is in a valid parking zone
[STATE] Scooter is AVAILABLE (battery: 85%)
```

**Server terminal:**
```
[SERVER] Scooter #1234 connected and registered
[SERVER] Scooter #1234 claimed successfully
[SERVER] Scooter #1234 rented successfully
[SERVER] Scooter #1234 CANNOT PARK - not in a valid parking zone
[SERVER] Scooter #1234 parked and returned successfully
```

## Raspberry Pi Setup

When running on a Raspberry Pi with a Sense HAT, the system automatically uses the real magnetometer and LED display — no code changes needed.

1. Transfer files to the Pi:
   ```bash
   scp -r scooter/ gruppe13@raspberrypi13:~/
   ```

2. SSH into the Pi:
   ```bash
   ssh gruppe13@raspberrypi13
   cd scooter
   ```

3. Set up and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install sense-hat
   ```

4. Start the scooter:
   ```bash
   python ScooterClient.py --id 1234
   ```

### Troubleshooting RTIMU on Raspberry Pi

If `sense-hat` fails to install:
```bash
git clone https://github.com/RPi-Distro/RTIMULib/ RTIMU
cd RTIMU/Linux/python
sudo apt install python3-dev
python setup.py build
python setup.py install
sudo apt install libopenjp2-7
sudo apt install sense-hat
```

## Dependencies

| Component | Libraries |
|-----------|-----------|
| Scooter   | `stmpy`, `paho-mqtt`, `sense-hat` (optional, for Raspberry Pi) |
| Server    | `paho-mqtt` |
| User App  | `appJar`, `requests` |

Install dependencies per component using `pip install -r requirements.txt` in each directory.

## Notes

- **Python 3.12 is required.** Python 3.13+ is not supported (`appJar` uses the removed `imghdr` module).
- The MQTT broker at `mqtt20.iik.ntnu.no` must be reachable from your network.
- Use the same IP/port for both the server and user app.
