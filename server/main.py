# Python 3 server example
from http.server import BaseHTTPRequestHandler, HTTPServer
import paho.mqtt.client as mqtt
from threading import Thread
import json
import time


hostName = "172.20.10.9"
serverPort = 8080

mqttBroker = "mqtt20.iik.ntnu.no"
mqttPort = 1883
mqttUnlockChannel = "ttm4115/team-13/scooter"
mqttResponseChannel = "ttm4115/team-13/scooter"
scooterUnlockTimeout = 10


class Scooter():
    id = -1
    locked = False

    def __init__(self, id):
        self.id = id


class Server(BaseHTTPRequestHandler):
    scooters = {}
    
    def __init__(self, broker, port):
        self.client = mqtt.Client()
        self.client.on_connect = self.mqtt_on_connect
        self.client.on_message = self.mqtt_on_message

        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)

        self.client.subscribe(mqttResponseChannel)

        try:
            # line below should not have the () after the function!
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()

    def mqtt_on_connect(self, client, userdata, flags, rc):
        print("on_connect(): {}".format(mqtt.connack_string(rc)))

    def do_GET(self):
        payload = {}
        if self.path.split('?')[0] == '/add_scooter':
            sid = self.path.split('?')[1]
            #TODO: Sjekk at ikke allerede finnes med denne sid
            #TODO: Gjør noe dersom de ikke kommer med egen sid?
            self.scooters[sid] = Scooter(sid)
            print(f'INFO: Added scooter with ID {sid}')

        if self.path.split('?')[0] == '/list_available':
            payload['scooters'] = []
            for sid, scooter in self.scooters.items():
                if not scooter.locked:
                    payload['scooters'].append(scooter.id)

        if self.path.split('?')[0] == '/rent_scooter':
            sid = self.path.split('?')[1]

            #TODO: Hva om den allerede var låst?

            #self.client.publish(mqttUnlockChannel, {'id': sid})
            #sendTime = time.time()            
            #while time.time() < sendTime + scooterUnlockTimeout:
            #    continue
            #self.scooters[sid].locked = True

        if self.path.split('?')[0] == '/unrent_scooter':
            sid = self.path.split('?')[1]
            #TODO: Hva om den allerede var ulåst?
            self.scooters[sid].locked = False

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(payload), 'utf-8'))

    def mqtt_on_message(self, client, userdata, msg):
        print("on_message(): topic: {}".format(msg.topic))
        self.stm_driver.send("message", "tick_tock")



if __name__ == "__main__":        
    webServer = HTTPServer((hostName, serverPort), Server(mqttBroker, mqttPort))
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
