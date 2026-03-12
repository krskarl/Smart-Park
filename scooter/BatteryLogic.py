from Display import display_battery, display_text
import time

def drain_battery(scooter):
    """Drains the battery level over time."""
    while scooter.running:
        if(scooter.battery_level>0):
            scooter.battery_level -= 0.5
        display_battery(scooter.battery_level)
        scooter._logger.info(f'Battery level: {scooter.battery_level}')
        if scooter.battery_level <= 0:
            scooter._logger.debug('Battery drained')
            scooter.stm.send("battery_drained", "scooterMachine")
            scooter.running = False
            display_text("Battery drained", [255, 0, 0])
        else:
            time.sleep(0.5)