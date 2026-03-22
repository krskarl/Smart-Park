import stmpy
import logging
from Display import display_text, display_status, display_battery
from ZoneLogic import try_to_stop, check_temperature;
import json
import time
import threading


MQTT_BROKER = 'mqtt20.iik.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_OUTPUT = 'ttm4115/team-13/scooter'

class ScooterLogic:
    """
    State Machine for a scooter.

    This is the support object for a state machine that models a single scooter.
    """
    def __init__(self, client):

        self._logger = logging.getLogger("ScooterLogic")
        self._logger.setLevel(logging.WARNING)
        self.client = client
        self.battery_level = 100

        # Transitions

        initial = {
            'source': 'initial',
            'target': 'off'
        }

        start = {
            'source': 'off',
            'target': 'available',
            'trigger': 'start',
            'effect': 'start_scooter'
        }

        claim = {
            'source': 'available',
            'target': 'claimed',
            'trigger':'claim',
            'effect': 'start_timer("t_claimed", 10000)'
        }

        unclaim = {
            'source': 'claimed',
            'target': 'available',
            'trigger': 't_claimed',
            'effect': 'unclaim_scooter'
        }

        rent = {
            'source': 'claimed',
            'target': 'rented',
            'trigger': 'unlock',
            'effect': 'unlock_scooter'
        }

        battery_drained = {
            'source': 'rented',
            'target': 'off',
            'trigger': 'battery_drained',
            'effect': 'stop_battery_drain; battery_drained'
        }

        stop_rent = {
            'source': 'rented',
            'target': 'available',
            'trigger': 'lock_scooter',
            'effect': 'stop_battery_drain;'
        }


        # States
        off = {
            'name': 'off',
            'entry': 'off_state'
        }

        available = {
            'name': 'available',
            'entry': 'available_state',
        }

        claimed = {
            'name': 'claimed',
            'entry': 'claimed_state'
        }

        rented = {
            'name': 'rented',
            'entry': 'rented_state; stop_timer("t_claimed")',
            'stop_renting': 'lock_scooter'
        }

        self.stm = stmpy.Machine(name="scooterMachine", transitions=[initial, start, claim, unclaim,  rent, stop_rent, battery_drained], states=[available, off, claimed, rented], obj=self)


    # State methods
    def off_state(self):
        print(f"[STATE] Scooter is OFF")

    def available_state(self):
        print(f"[STATE] Scooter is AVAILABLE (battery: {self.battery_level:.0f}%)")
        display_battery(self.battery_level)

    def claimed_state(self):
        print(f"[STATE] Scooter is CLAIMED by a user")
        payload = {
            'id': f'{self.client.id}',
            'command': 'scooter_claimed',
        }
        self.client.publish(MQTT_TOPIC_OUTPUT, json.dumps(payload))
        display_text("Claimed", [0, 255, 0])

    def rented_state(self):
        print(f"[STATE] Scooter is RENTED - ride in progress")
        payload = {
            'id': f'{self.client.id}',
            'command': 'scooter_unlocked'
        }
        self.start_battery_drain()
        self.client.publish(MQTT_TOPIC_OUTPUT, json.dumps(payload))


    # Transition methods
    def start_scooter(self):
        print(f"[ACTION] Scooter powered on and registered with server")
        payload = {
            'id': f'{self.client.id}',
            'command': 'scooter_started'
        }
        self.client.publish(MQTT_TOPIC_OUTPUT, json.dumps(payload))
        display_text("Started", [0, 255, 0])

    def unclaim_scooter(self):
        print(f"[ACTION] Claim expired - scooter unclaimed")
        payload = {
            'id': f'{self.client.id}',
            'command': 'scooter_unclaimed'
        }
        self.client.publish(MQTT_TOPIC_OUTPUT, json.dumps(payload))
        display_text("Unclaimed", [255, 0, 0])

    def unlock_scooter(self):
        print(f"[ACTION] Scooter unlocked for ride")
        display_status("Unlocked", [0, 255, 0])

    def lock_scooter(self):
        if self.stm.state != "rented":
            return
        print(f"[ACTION] User wants to park - checking parking zone...")
        if try_to_stop():
            print(f"[RESULT] PARKING APPROVED - scooter is in a valid parking zone")
            payload = {
                'id': f'{self.client.id}',
                'command': 'scooter_locked'
            }
            self.client.publish(MQTT_TOPIC_OUTPUT, json.dumps(payload))
            self.stm.send("lock_scooter", "scooterMachine")
            display_status("Locked", [0, 0, 255])
        else:
            print(f"[RESULT] PARKING DENIED - scooter is NOT in a valid parking zone")
            payload = {
                'id': f'{self.client.id}',
                'command': 'unable_to_lock'
            }
            self.client.publish(MQTT_TOPIC_OUTPUT, json.dumps(payload))
            display_text("Invalid zone", [255, 0, 0])



    # Battery draining
    def start_battery_drain(self):
        """Starts a thread to drain the battery."""
        self.running = True
        try:
            self.battery_thread = threading.Thread(target=self.drain_battery)
            self.battery_thread.start()
        except KeyboardInterrupt:
            self.mqtt_client.disconnect()

    def stop_battery_drain(self):
        """Stops the battery drain thread."""
        self.running = False
        if self.battery_thread:
            self.battery_thread.join()

    def battery_drained(self):
        print(f"[STATE] Battery fully drained - scooter shutting down")

    def drain_battery(self):
        """Drains the battery level over time."""
        last_printed = self.battery_level
        while self.running:
            if(self.battery_level>0):
                self.battery_level -= 0.5
            display_battery(self.battery_level)
            # Only print battery every 10%
            if int(self.battery_level) % 10 == 0 and int(self.battery_level) != int(last_printed):
                print(f"[BATTERY] {self.battery_level:.0f}%")
                last_printed = self.battery_level
            if self.battery_level <= 0:
                self.stm.send("battery_drained", "scooterMachine")
                self.running = False
                display_text("Battery drained", [255, 0, 0])
            else:
                time.sleep(0.5)

    def test(self):
        print(self.stm.state)
