#!/usr/bin/env python3
#

import sys
import time
import requests

from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property

class Topas(Device):

    __h = 4.135667696E-15   #Planck's constant in eVs'
    __c = 299792458         #Speed of light in m/s
    # -----------------
    # Device Properties
    # -----------------

    IP = device_property(dtype='DevString', default_value = '192.168.1.108') #127.0.0.1 if device is local
    port = device_property(dtype='DevString', default_value = '8000')
    serial = device_property(dtype='DevString', default_value = '00666')

    # ----------
    # Attributes
    # ----------

    wavelength = attribute(
        dtype='DevFloat',
        access=AttrWriteType.READ_WRITE,
        label="wavelength",
        unit="nm",
        format="%5.1f",
    )

    energy = attribute(
        dtype='DevFloat',
        access=AttrWriteType.READ_WRITE,
        label="energy",
        unit="eV",
        format="%5.4f",
    )

    ShutterOpen = attribute(dtype = 'DevBoolean',
        label = 'Shutter open',
        access = AttrWriteType.READ_WRITE,)

    ShutterSardana = attribute(dtype = 'DevFloat',
        label = 'Shutter open',
        access = AttrWriteType.READ_WRITE,
        format="%1.0f",
        min_value = 0,
        max_value = 1,
        display_level=DispLevel.EXPERT)

    authentication = attribute(dtype = 'DevBoolean',
        label = 'Authentication',
        access = AttrWriteType.READ,
        doc = 'only authenticated users can write attributes')

    interactions = attribute(dtype = 'DevString',
        label = 'Available interactions',
        access = AttrWriteType.READ,
        doc = 'only authenticated users can write attributes',
        display_level=DispLevel.EXPERT)
   
    # ---------------
    # General methods
    # ---------------

    def put(self, url, data):
        return requests.put(self.baseAddress + url, json =data)
    def post(self, url, data):
        return requests.post(self.baseAddress + url, json =data)
    def get(self, url):
        res = requests.get(self.baseAddress + url)
        return res.json() 
    
    def init_device(self):
        Device.init_device(self)
        self.baseAddress = 'http://'+str(self.IP)+':'+str(self.port)+'/'+str(self.serial)+'/v0/PublicAPI'
        self.set_state(DevState.ON)
        if self.checkauthentication():
            print('Caller is authorized.')
            self.getCalibrationInfo()
        else:
            print('Caller has no authorization.')
            line = input(r"Do you want to start authentication procedure? (Y\N)").upper()
            if line == "Y" or line == "YES":
                self.authenticate()

    @command(dtype_in = str, doc_in = 'start authentication procedure')
    def authenticate(self, value):
        self.post('/Authentication/StartAuthenticationByInterlock', '')
        print('repeatedly press interlock button to authenticate device')
        response = self.get('/Authentication/AuthenticationStatus')
        while response['IsAuthenticationInProgress'] and not response['CallerHasAccess']:
            response = self.get('/Authentication/AuthenticationStatus')
            time.sleep(1)
            print('repeatedly press interlock button to authenticate caller')
        else:
            if response['CallerHasAccess']:
                print('Authentication successful!')
            elif not response['IsAuthenticationInProgress']:
                print('Authentication timeout')
            else:
                print('unknown error')
       
    
    # ------------------
    # Attributes methods
    # ------------------

    ### READ methods ###

    def read_wavelength(self):
        return self.getWavelength()

    def read_energy(self):
        return 10**9*self.__h*self.__c/self.getWavelength()

    def read_ShutterOpen(self):
        res = self.get('/ShutterInterlock/IsShutterOpen')
        if res:
            self.set_state(DevState.OPEN)
        else:
            self.set_state(DevState.CLOSE)
        return res

    def read_authentication(self):
        return self.checkauthentication()

    def read_interactions(self):
        return self.getCalibrationInfo()

    def read_ShutterSardana(self):
        if self.read_ShutterOpen():
            return 1
        else:
            return 0

    ### WRITE methods ###
    
    def write_wavelength(self, value):
        return self.setWavelength(value)
    
    def write_energy(self,value):
        return self.setWavelength(10**9*self.__h*self.__c/value)
    
    def write_ShutterOpen(self,value):
        if value:
            self.put('/ShutterInterlock/OpenCloseShutter', True)
        else:
            self.put('/ShutterInterlock/OpenCloseShutter', False)
        time.sleep(0.2)

    def write_ShutterSardana(self,value):
        if int(value) == 0:
            self.write_ShutterOpen(False)
        elif int(value) == 1:
            self.write_ShutterOpen(True)

    ### Other methods ###

    def getCalibrationInfo(self):
        """Get basic calibration info"""
        interactions = self.get('/Optical/WavelengthControl/ExpandedInteractions')
        if len(interactions)==0:
            res = "There are no calibrated interactions"
        else:
            res = 'Available interactions'
            for item in interactions:
                s = item['Type'] + " %d - %d nm" % (item['OutputRange']['From'], item['OutputRange']['To'])
                res = res + '\n'+s
        return res

    def getWavelength(self):
        return float(self.get('/Optical/WavelengthControl/Output/Wavelength'))

    def setWavelength(self,value):
        response =self.put('/Optical/WavelengthControl/SetWavelengthUsingAnyInteraction',value)
        self.waitTillWavelengthIsSet()
        return self.getWavelength()

    def checkauthentication(self):
        return self.get('/Authentication/CallerHasAccess')
    
    def waitTillWavelengthIsSet(self):
        """
        Waits till wavelength setting is finished.  If user needs to do any manual
        operations (e.g.  change wavelength separator), inform him/her and wait for confirmation.
        """
        
        while(True):
            s = self.get('/Optical/WavelengthControl/Output')
            if s['IsWavelengthSettingInProgress'] == False or s['IsWaitingForUserAction']:
                break
        state = self.get('/Optical/WavelengthControl/Output')
        if state['IsWaitingForUserAction']:
            print("\nUser actions required. Press enter key to confirm.")
            #inform user what needs to be done
            for item in state['Messages']:
                print(item['Text'] + ' ' + ('' if item['Image'] is None else ', image name: ' + item['Image']))
            sys.stdin.read(1)#wait for user confirmation
            # tell the device that required actions have been performed.  If shutter was open before setting wavelength it will be opened again
            self.put('/Optical/WavelengthControl/FinishWavelengthSettingAfterUserActions', {'RestoreShutter':True})

if __name__ == "__main__":
    Topas.run_server()
