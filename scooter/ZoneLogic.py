import threading

try:
    from sense_hat import SenseHat
    sense = SenseHat()
    sense.set_imu_config(True, False, False)
    SIMULATION_MODE = False
except ImportError:
    SIMULATION_MODE = True

# Simulation state
_in_zone = False
_input_thread_started = False

def _start_input_thread():
    """Starts a background thread that listens for Enter key to toggle zone state."""
    global _input_thread_started
    if _input_thread_started:
        return
    _input_thread_started = True

    def listen():
        global _in_zone
        while True:
            try:
                input()  # Wait for Enter
                _in_zone = not _in_zone
                if _in_zone:
                    print(f"[MAGNET] Magnet DETECTED - scooter is now in a parking zone")
                else:
                    print(f"[MAGNET] Magnet REMOVED - scooter is now outside a parking zone")
            except EOFError:
                break

    t = threading.Thread(target=listen, daemon=True)
    t.start()

def try_to_stop():
    """Try to stop the scooter."""
    if SIMULATION_MODE:
        _start_input_thread()
        if _in_zone:
            print(f"[MAGNET] Sensor reading: magnet detected (in parking zone)")
        else:
            print(f"[MAGNET] Sensor reading: no magnet detected (not in parking zone)")
        return _in_zone

    mag = sense.get_compass_raw()
    x = mag['x']
    y = mag['y']
    z = mag['z']

    print(f"[MAGNET] Sensor reading: x={x:.1f}, y={y:.1f}, z={z:.1f}")

    if abs(mag['x']) > 100 or abs(mag['y']) > 100:
        print(f"[MAGNET] Strong magnetic field detected - valid parking zone")
        return True

    print(f"[MAGNET] No significant magnetic field - not a parking zone")
    return False
