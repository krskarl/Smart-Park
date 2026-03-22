#import paho.mqtt.client as mqtt
#from threading import Thread
#import json
from appJar import gui
import logging
import requests # type: ignore
import asyncio
import sys
import argparse

parser = argparse.ArgumentParser(
    prog='userapp.py',
    description='Client side for renting scooters',
)
parser.add_argument('source')
parser.add_argument('port')
args = parser.parse_args()

print(args)

SERVERURL = args.source
SERVERPORT = args.port

# Used for simulating scooters
class Scooter:
    def __init__(self, id, distance=None, battery=None):
        self.id = id
        self.distance = distance #Future feature
        self.battery = battery #Future feature
        self.rented = False
        self.claimed = False

list_of_scooters = []

class Command:
    def __init__(self,title,id=None):
        self.title = title
        self.id = id


class UserApp:
    """
    The frontend component for users to list/rent/claim/unrent scooters.
    """

    def __init__(self, scooterList, serverurl, serverport):

        self.scooterList = scooterList
        self.server = 'http://'+serverurl+':'+serverport

        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        self.create_gui()
    
    def CustomGETrequest(self,command):
        url = self.server

        if command.title == 'list':
            url += '/list_available'
            response = requests.get(url)
            return response.json()
        elif command.title == 'rent':
            url += '/rent_scooter?{}'.format(command.id)
            response = requests.get(url)
            return response.json()
        elif command.title == 'unrent':
            url += '/unrent_scooter?{}'.format(command.id)
            response = requests.get(url)
            return response.json()
        elif command.title == 'claim':
            url += '/claim_scooter?{}'.format(command.id)
            response = requests.get(url)
            return response.json()
        elif command.title == 'unclaim':
            url += '/unclaim_scooter?{}'.format(command.id)
            response = requests.get(url)
            return response.json()
        else:
            #some error handling
            print('error')

    def create_gui(self):
        self.app = gui('Smart Park - E-Scooter Rental', '800x500', handleArgs=False)

        # Colors
        self.app.setBg('#F5F5F5')
        self.app.setFg('#333333')
        self.app.setFont(12)

        # Title
        self.app.addLabel('title', 'Smart Park - E-Scooter Rental', 0, 0, 3)
        self.app.setLabelBg('title', '#2196F3')
        self.app.setLabelFg('title', 'white')
        self.app.getLabelWidget('title').config(font=('Helvetica', 18, 'bold'), pady=10)

        def extract_scooter_id(label):
            label = label.lower()
            scooter_id = int(label.split(' ')[1])
            return scooter_id

        ### REQUEST LIST OF SCOOTERS
        self.app.startLabelFrame('Available Scooters', 1, 0, 1, 1)
        self.app.setSticky('ew')
        def on_button_pressed_start():
            self.app.openLabelFrame('Available Scooters')
            self.app.emptyCurrentContainer()
            self.app.openLabelFrame('Claim')
            self.app.emptyCurrentContainer()

            self.scooterList = []

            self.app.openLabelFrame('Available Scooters')
            self.app.addButton('Refresh Scooters', on_button_pressed_start)
            self.app.setButtonBg('Refresh Scooters', '#2196F3')
            self.app.setButtonFg('Refresh Scooters', 'white')

            command = Command('list')
            response = self.CustomGETrequest(command)
            if len(response['scooters']) > 0:
                for scooter in self.CustomGETrequest(command)['scooters']:
                    print(scooter)
                    self.scooterList.append(Scooter(id=scooter))

                for i in range(len(self.scooterList)):
                    self.app.addLabel(
                        'l{}'.format(i),
                        'Scooter #{}'.format(self.scooterList[i].id))
                    self.app.setLabelBg('l{}'.format(i), '#E3F2FD')

                self.app.openLabelFrame('Claim')
                for i in range(len(self.scooterList)):
                    btn_name = 'Scooter {} - Claim'.format(self.scooterList[i].id)
                    self.app.addButton(btn_name, on_button_pressed_claim)
                    self.app.setButtonBg(btn_name, '#4CAF50')
                    self.app.setButtonFg(btn_name, 'white')
            else:
                self.app.infoBox('No Scooters', 'No scooters available nearby.', parent=None)

        self.app.addButton('Refresh Scooters', on_button_pressed_start)
        self.app.setButtonBg('Refresh Scooters', '#2196F3')
        self.app.setButtonFg('Refresh Scooters', 'white')
        self.app.stopLabelFrame()

        ### CLAIM
        self.app.startLabelFrame('Claim', 1, 1, 1, 1)
        self.app.setSticky('ew')
        def on_button_pressed_claim(title):
            id = extract_scooter_id(title)
            index = [i for i,x in enumerate(self.scooterList) if x.id == str(id)][0]

            command = Command('claim', id)
            response = self.CustomGETrequest(command)
            if 'errormessage' in response:
                if response['errormessage'] == 'already_claimed':
                    self.app.infoBox('Already Claimed', 'This scooter is already claimed by another user.', parent=None)
            else:
                self.scooterList[index].claimed = True
                print('claimed scooter {}'.format(id))

                # Add rent button
                self.app.openLabelFrame('Rent')
                btn_name = 'Scooter {} - Rent'.format(id)
                self.app.addButton(btn_name, on_button_pressed_rent)
                self.app.setButtonBg(btn_name, '#FF9800')
                self.app.setButtonFg(btn_name, 'white')

                # Add unclaim button
                self.app.openLabelFrame('Active Claims')
                btn_name = 'Scooter {} - Unclaim'.format(id)
                self.app.addButton(btn_name, on_button_pressed_unclaim)
                self.app.setButtonBg(btn_name, '#9E9E9E')
                self.app.setButtonFg(btn_name, 'white')

        self.app.stopLabelFrame()

        ### RENT
        self.app.startLabelFrame('Rent', 1, 2, 1, 1)
        self.app.setSticky('ew')
        def on_button_pressed_rent(title):
            id = extract_scooter_id(title)
            index = [i for i,x in enumerate(self.scooterList) if x.id == str(id)][0]

            try:
                command = Command('rent', id)
                response = self.CustomGETrequest(command)
            except:
                print('request failed')
                return

            if response and 'errormessage' in response:
                if response['errormessage'] == 'temperature_too_low':
                    temp = response.get('temperature', '?')
                    self.app.infoBox('Temperature Too Low',
                        'Cannot rent: temperature is {}C (minimum 40C required).'.format(temp), parent=None)
                    return
                else:
                    self.app.infoBox('Rental Error', response['errormessage'], parent=None)
                    return

            print('Started a rental of {}'.format(id))
            self.scooterList[index].rented = True

            self.app.openLabelFrame('Active Rentals')
            btn_name = 'Scooter {} - Stop Rental'.format(id)
            self.app.addButton(btn_name, on_button_pressed_stop)
            self.app.setButtonBg(btn_name, '#F44336')
            self.app.setButtonFg(btn_name, 'white')

        self.app.stopLabelFrame()

        ### ACTIVE RENTALS
        self.app.startLabelFrame('Active Rentals', 2, 0, 1, 2)
        self.app.setSticky('ew')
        def on_button_pressed_stop(title):
            id = extract_scooter_id(title)
            index = [i for i,x in enumerate(self.scooterList) if x.id == str(id)][0]

            command = Command('unrent', id)
            response = self.CustomGETrequest(command)
            if 'errormessage' in response:
                if response['errormessage'] == 'invalid_parking':
                    self.app.infoBox('Invalid Parking', 'Scooter is not in a valid parking zone. Please move to a designated area.', parent=None)
            else:
                self.scooterList[index].rented = False
                print('Stopped a rental of {}'.format(id))
                self.app.removeButton('Scooter {} - Stop Rental'.format(id))
                self.app.removeButton('Scooter {} - Unclaim'.format(id))

        self.app.stopLabelFrame()

        ### ACTIVE CLAIMS
        self.app.startLabelFrame('Active Claims', 2, 2, 1, 1)
        self.app.setSticky('ew')
        def on_button_pressed_unclaim(title):
            id = extract_scooter_id(title)
            index = [i for i,x in enumerate(self.scooterList) if x.id == str(id)][0]
            print('Stopped a claim of {}'.format(id))
            self.scooterList[index].claimed = False
            self.app.removeButton('Scooter {} - Unclaim'.format(id))

        self.app.stopLabelFrame()

        self.app.go()


# logging.DEBUG: Most fine-grained logging, printing everything
# logging.INFO:  Only the most important informational log items
# logging.WARN:  Show only warnings and errors.
# logging.ERROR: Show only error messages.
debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)



# Async functions to ensure app can connect to server and get list

async def testConnection(server):
    canConnect = False

    try:
        response = requests.get(server) #Sends GET to mainpage to check connectivity
        if response.status_code==200:
            print('Connection successfull')
            canConnect = True
        else:
            print(f'Request failed with code: {response.status_code}')
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as err:
        print(f'Failed to establish connection: {err}')
    except Exception as e:
        print(f'Unknown error occured : {e}')
        
    return canConnect


async def runApp(serverurl,serverport):

    able_to_connect = await testConnection('http://'+serverurl+':'+serverport)

    if able_to_connect:
        return UserApp([],serverurl,serverport)
    else:
        print('Cannot connect to server')
        

if __name__ == '__main__':
    try:
        app=asyncio.run(runApp(SERVERURL,SERVERPORT))
    except KeyboardInterrupt:
        print('Program stopped by interrupt')