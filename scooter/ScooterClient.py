import argparse
import paho.mqtt.client as mqtt
from threading import Thread
import json
from stmpy import Driver
from ScooterLogic import ScooterLogic, MQTT_TOPIC_OUTPUT
from ZoneLogic import check_temperature
import logging

class ScooterClient:
    def __init__(self, id):
        # Initialize logger
        self._logger = logging.getLogger("ScooterClient")
        self._logger.setLevel(logging.INFO)

        self.client = mqtt.Client()
        self.client.id = id
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        broker, port = "mqtt20.iik.ntnu.no", 1883

        scooter = ScooterLogic(self.client)
        scooter_machine = scooter.stm

        driver = Driver()
        driver.add_machine(scooter_machine)

        scooter.mqtt_client = self.client
        self.scooter = scooter
        self.stm_driver = driver

        driver.start()
        self.start(broker, port)

        # Auto-start the scooter so it registers with the server
        self.stm_driver.send("start", "scooterMachine")

    def on_connect(self, client, userdata, flags, rc):
        print(f"[SCOOTER {self.client.id}] Connected to MQTT broker")

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except Exception as err:
            print(f"[SCOOTER {self.client.id}] ERROR: Invalid message received")
            return

        command = payload.get('command')
        match command:
            case "start":
                print(f"[SCOOTER {self.client.id}] Received command: START")
                self.stm_driver.send("start", "scooterMachine")
            case "claim":
                print(f"[SCOOTER {self.client.id}] Received command: CLAIM")
                self.stm_driver.send("claim", "scooterMachine")
            case "unlock":
                print(f"[SCOOTER {self.client.id}] Received command: UNLOCK (rent)")
                allowed, temp = check_temperature()
                if not allowed:
                    print(f"[SCOOTER {self.client.id}] RENTAL DENIED - temperature {temp:.1f}°C is below 40°C")
                    # Reset claim timer so it doesn't expire while user retries
                    self.scooter.stm.stop_timer("t_claimed")
                    self.scooter.stm.start_timer("t_claimed", 10000)
                    payload = json.dumps({"id": str(self.client.id), "command": "rental_denied_temperature", "temperature": round(temp, 1)})
                    self.client.publish(MQTT_TOPIC_OUTPUT, payload)
                else:
                    print(f"[SCOOTER {self.client.id}] Temperature OK ({temp:.1f}°C) - unlocking")
                    self.stm_driver.send("unlock", "scooterMachine")
            case "stop_renting":
                print(f"[SCOOTER {self.client.id}] Received command: STOP RENTING (attempting to park)")
                self.stm_driver.send("stop_renting", "scooterMachine")
            case _:
                print(f"[SCOOTER {self.client.id}] WARNING: Unknown command '{command}'")

    def start(self, broker, port):
        print(f"[SCOOTER {self.client.id}] Connecting to MQTT broker at {broker}:{port}...")
        self.client.connect(broker, port)

        topic = f"ttm4115/team-13/scooter/{self.client.id}/command"
        self.client.subscribe(topic)

        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            self.client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Start the ScooterClient.")
    parser.add_argument(
        "--id",
        type=int,
        default=1234,
        help="The ID of the scooter (default: 1234)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print(f"  E-SCOOTER SIMULATION - Scooter #{args.id}")
    print("=" * 50)
    print()

    ScooterClient(args.id)
