from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time
import paho.mqtt.client as mqtt
from threading import Thread
import sys

hostName = sys.argv[1]
serverPort = int(sys.argv[2])

scooterUnlockTimeout = 5

MQTT_BROKER = "mqtt20.iik.ntnu.no"
MQTT_PORT = 1883
mqttUnlockChannel = "ttm4115/team-13/scooter"
mqttResponseChannel = "ttm4115/team-13/scooter"


class Scooter():
    id = -1
    rented = False
    claimed = False
    battery = 100
    parked = True
    invalidParking = False
    temperatureDenied = False
    temperature = None
    owner = ""

    def __init__(self, id):
        self.id = id



class MQTTComponent:

    def on_connect(self, client, userdata, flags, rc):
        print(f"[SERVER] Connected to MQTT broker")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            print(f'[SERVER] ERROR: Invalid MQTT message received')
            return

        # Always expects "command" and "id"
        command = payload.get('command')
        sid = payload.get('id')

        if command == 'scooter_started':
            self.httpserver.scooters[sid] = Scooter(sid)
            print(f'[SERVER] Scooter #{sid} connected and registered')
        elif command == 'scooter_unlocked':
            self.httpserver.scooters[sid].rented = True
            self.httpserver.scooters[sid].parked = False
            print(f'[SERVER] Scooter #{sid} unlocked - ride started')
        elif command == 'scooter_locked':
            self.httpserver.scooters[sid].rented = False
            self.httpserver.scooters[sid].claimed = False
            self.httpserver.scooters[sid].invalidParking = False
            self.httpserver.scooters[sid].parked = True
            print(f'[SERVER] Scooter #{sid} locked and parked successfully')
        elif command == 'scooter_claimed':
            self.httpserver.scooters[sid].claimed = True
            print(f'[SERVER] Scooter #{sid} claimed by user')
        elif command == 'scooter_unclaimed':
            self.httpserver.scooters[sid].claimed = False
            print(f'[SERVER] Scooter #{sid} claim expired')
        elif command == 'unable_to_lock':
            self.httpserver.scooters[sid].invalidParking = True
            print(f'[SERVER] Scooter #{sid} parking rejected - not in valid zone')
        elif command == 'rental_denied_temperature':
            temp = payload.get('temperature')
            self.httpserver.scooters[sid].temperatureDenied = True
            self.httpserver.scooters[sid].temperature = temp
            print(f'[SERVER] Scooter #{sid} rental denied - temperature {temp}°C is below 40°C')
        else:
            print(f'[SERVER] WARNING: Unknown command received: {command}')

    def __init__(self, httpserver):
        print(f'[SERVER] Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...')
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.subscribe(mqttResponseChannel)

        # Save reference to http server
        self.httpserver = httpserver
        self.httpserver.mqtt_client = self.mqtt_client


        try:
            self.thread = Thread(target=self.mqtt_client.loop_forever)
            self.thread.start()
        except KeyboardInterrupt:
            self.mqtt_client.disconnect()


    def stop(self):
        """
        Stop the component.
        """
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print('[SERVER] MQTT disconnected')



class myHandler(BaseHTTPRequestHandler):
    scooters = {}
    mqtt_client: mqtt.Client = None

    def log_message(self, format, *args):
        """Suppress default HTTP request logging."""
        pass

    def do_GET(self):
        payload = {}

        if self.path.split('?')[0] == '/list_available':
            payload['scooters'] = []
            for sid, scooter in self.scooters.items():
                if not (scooter.rented or scooter.claimed):
                    payload['scooters'].append(scooter.id)
            count = len(payload['scooters'])
            print(f'[SERVER] User requested scooter list -> {count} available')

        if self.path.split('?')[0] == '/rent_scooter':
            sid = self.path.split('?')[1]
            if self.scooters[sid].owner != self.request.getpeername()[0]:
                payload['status'] = 'failure'
                payload['errormessage'] = 'you do not own the claim to this scooter'
                print(f'[SERVER] Rent request for scooter #{sid} DENIED - user does not own claim')
            else:
                self.scooters[sid].temperatureDenied = False
                self.mqtt_client.publish(mqttUnlockChannel+'/1234/command', json.dumps({"id":sid,"command":"unlock"}))
                sendTime = time.time()
                payload['status'] = 'failure'
                while time.time() < sendTime + scooterUnlockTimeout:
                    if self.scooters[sid].rented:
                        payload['status'] = 'success'
                        break
                    if self.scooters[sid].temperatureDenied:
                        break
                if payload['status'] == 'success':
                    print(f'[SERVER] Scooter #{sid} rented successfully')
                elif self.scooters[sid].temperatureDenied:
                    payload['status'] = 'failure'
                    payload['errormessage'] = 'temperature_too_low'
                    payload['temperature'] = self.scooters[sid].temperature
                    print(f'[SERVER] Rent request for scooter #{sid} DENIED - temperature too low ({self.scooters[sid].temperature}°C)')
                else:
                    print(f'[SERVER] Rent request for scooter #{sid} FAILED - scooter did not respond')

        if self.path.split('?')[0] == '/unrent_scooter':
            sid = self.path.split('?')[1]
            if self.scooters[sid].owner != self.request.getpeername()[0]:
                payload['status'] = 'failure'
                payload['errormessage'] = 'you do not have this scooter rented'
                print(f'[SERVER] Stop rental for scooter #{sid} DENIED - user does not own rental')
            else:
                print(f'[SERVER] User requesting to park scooter #{sid} - waiting for scooter response...')
                self.mqtt_client.publish(mqttUnlockChannel+'/1234/command', json.dumps({"id":sid,"command":"stop_renting"}))
                sendTime = time.time()
                status = 'failure'
                while time.time() < sendTime + scooterUnlockTimeout:
                    if self.scooters[sid].rented == False:
                        status = 'success'
                        self.scooters[sid].claimed = False
                        break
                if status == 'success':
                    print(f'[SERVER] Scooter #{sid} parked and returned successfully')
                elif self.scooters[sid].invalidParking:
                    print(f'[SERVER] Scooter #{sid} CANNOT PARK - not in a valid parking zone')
                    status = 'failure'
                    payload['errormessage'] = 'invalid_parking'
                else:
                    print(f'[SERVER] Stop rental for scooter #{sid} FAILED - scooter did not respond')
                    self.scooters[sid].rented = False

            payload['status'] = status


        if self.path.split('?')[0] == '/claim_scooter':
            sid = self.path.split('?')[1]
            if (self.scooters[sid].claimed or self.scooters[sid].rented):
                payload['status'] = 'failure'
                payload['errormessage'] = 'already_claimed'
                print(f'[SERVER] Claim request for scooter #{sid} DENIED - already claimed/rented')
            else:
                self.mqtt_client.publish(mqttUnlockChannel+'/1234/command', json.dumps({"id":sid,"command":"claim"}))
                sendTime = time.time()
                payload['status'] = 'failure'
                while time.time() < sendTime + scooterUnlockTimeout:
                    if self.scooters[sid].claimed:
                        self.scooters[sid].owner = self.request.getpeername()[0]
                        payload['status'] = 'success'
                        break
                if payload['status'] == 'success':
                    print(f'[SERVER] Scooter #{sid} claimed successfully')
                else:
                    print(f'[SERVER] Claim request for scooter #{sid} FAILED - scooter did not respond')

        if self.path.split('?')[0] == '/unclaim_scooter':
            sid = self.path.split('?')[1]
            if self.scooters[sid].owner != self.request.getpeername()[0]:
                payload['status'] = 'failure'
                payload['errormessage'] = 'you do not own the claim to this scooter'
                print(f'[SERVER] Unclaim request for scooter #{sid} DENIED - user does not own claim')
            else:
                self.mqtt_client.publish(mqttUnlockChannel+'/1234/command', json.dumps({"id":sid,"command":"unclaim"}))
                sendTime = time.time()
                status = 'failure'
                while time.time() < sendTime + scooterUnlockTimeout:
                    if self.scooters[sid].claimed == False:
                        status = 'success'
                        break
                if status == 'success':
                    print(f'[SERVER] Scooter #{sid} unclaimed successfully')
                else:
                    print(f'[SERVER] Unclaim request for scooter #{sid} FAILED - scooter did not respond')
                payload['status'] = 'success'
                self.scooters[sid].claimed = False


        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(payload), 'utf-8'))


if __name__ == "__main__":
    print("=" * 50)
    print("  E-SCOOTER SYSTEM - Server")
    print("=" * 50)
    print()
    mqttbroker = MQTTComponent(myHandler)
    webServer = HTTPServer((hostName,serverPort),myHandler)
    print(f"[SERVER] HTTP server running at http://{hostName}:{serverPort}")
    print(f"[SERVER] Waiting for scooters to connect...")
    print()
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    mqttbroker.stop()
    print("[SERVER] Server stopped.")
