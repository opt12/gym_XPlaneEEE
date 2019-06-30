from threading import Lock, Event
from gym_XPlaneEEE.utils.singleton import SingletonMixin
import numpy as np

planeStateLock = Lock()
newDataEvent = Event()

class DataCenter(SingletonMixin):
    def __init__ (self):
        self.planeState = None
        self.observation = 0

    def putState(self, planeState):
        planeStateLock.acquire()
        self.planeState = planeState
        planeStateLock.release()
        self.observation += 1
        newDataEvent.set()

    def getState(self):
        newDataEvent.clear()
        planeStateLock.acquire()
        currentState = self.planeState
        planeStateLock.release()
        return currentState
    
    def getSpeedObservation(self):
        """
        Returns
        -------
        Returns a single (raw) observation to be used for the speed control. The following datarefs are included:
          - indicated_airspeed_ms #the speed to be controlled
          - stallWarning          #The stall warning signal
          - h_ind                 #Indicated barometric altitude, quite probably in feet actually.
          - alpha                 #angle of attack
          - true_theta            #pitch
          - yoke_pitch_ratio      #The deflection of the joystick axis controlling pitch.
          - true_phi              #roll
          - yoke_roll_ratio       #The deflection of the joystick axis controlling roll.

        Normalization of the values needs to be done in a wrapper.
        """
        obs = np.zeros(8)
        planeStateLock.acquire()
        if self.planeState == None:
            #it may happen, that there is no observation available yet
            planeStateLock.release()
            return obs
        obs[0] = self.planeState['indicated_airspeed_ms']
        obs[1] = self.planeState['stallWarning']
        obs[2] = self.planeState['h_ind']
        obs[3] = self.planeState['alpha']
        obs[4] = self.planeState['true_theta']
        obs[5] = self.planeState['yoke_pitch_ratio']
        obs[6] = self.planeState['true_phi']
        obs[7] = self.planeState['yoke_roll_ratio']
        planeStateLock.release()

        return obs

    def getGlideAngleObservation(self):
        """
        Returns
        -------
        Returns a single (raw) observation to be used for the speed control. The following datarefs are included:
        - glide Angle           #the descent angle to be controlled glide Angle = to_degrees(atan(Vh_ind/tas)
        - stallWarning          #The stall warning signal
        - tas                   #the true airspeed [m/s]
        - Vh_ind                #the sinkrate [m/s]
        - h_ind                 #Indicated barometric altitude, quite probably in feet actually.
        - alpha                 #angle of attack
        - true_theta            #pitch
        - yoke_pitch_ratio      #The deflection of the joystick axis controlling pitch.
        - true_phi              #roll
        - yoke_roll_ratio       #The deflection of the joystick axis controlling roll.

        Normalization of the values needs to be done in a wrapper.
        """
        keyList = [None, 'stallWarning', 'true_airspeed', 'vh_ind', 'h_ind', 
                   'alpha', 'true_theta', 'yoke_pitch_ratio', 'true_phi', 'yoke_roll_ratio']
        obs = self.getObservation(keyList)
        if obs[2] != 0:
            #wir müssen den Gleitwinkel selber rechnen aus true_airspeed und sinkrate
            #der von XPlane ausgegebene Winkel ist bezogen auf ground_speed und damit bei Wind unbrauchbar.
            obs[0] = np.rad2deg(np.arctan(obs[3]/obs[2]))
        return obs

    def getObservation(self, keyList):
        """
        Args
        ------
        A list of strings holding the interesting keys (strings) to extract from full state dictionary. 
        As a placeholder for derived values, None instead of a string can be used. A Zero value is returned at that position.

        When accessing nested keys, use a list of subsequent subkeys at the desired position. (e. g. targetValueKeys = [['targetValues','requestedClimbRate'], ['targetValues','requestedRoll']])

        Returns
        -------
        Returns a single (raw) observation in form of a Numpy array. The datarefs given in the input list are included in the given order.
        Normalization of the values needs to be done in a wrapper.
        Derived values shall be calculated in the calling function. They are left as Zero values in the returned array.
        """
        obs = np.zeros(len(keyList))
        planeStateLock.acquire()
        if self.planeState == None:
            #it may happen, that there is no observation available yet
            planeStateLock.release()
            return obs
        for idx, key in enumerate(keyList):
            if key == None:
                continue
            if not isinstance(key, list):
                key = [key] #now we have a single element list
            retrievedItem = self.planeState
            for subKey in key:
                retrievedItem = retrievedItem[subKey]
            obs[idx] = retrievedItem
        planeStateLock.release()
        return obs

    def awaitNextObservation(self):
        """Blocks until a new observation is received"""
        newDataEvent.clear()
        newDataEvent.wait(1)    #1 second timeout
        return newDataEvent.isSet()


        