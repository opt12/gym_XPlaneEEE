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
        obs = np.zeros(10)
        planeStateLock.acquire()
        if self.planeState == None:
            #it may happen, that there is no observation available yet
            planeStateLock.release()
            return obs
        obs[1] = self.planeState['stallWarning']
        obs[2] = self.planeState['true_airspeed']
        obs[3] = self.planeState['vh_ind']
        obs[4] = self.planeState['h_ind']
        obs[5] = self.planeState['alpha']
        obs[6] = self.planeState['true_theta']
        obs[7] = self.planeState['yoke_pitch_ratio']
        obs[8] = self.planeState['true_phi']
        obs[9] = self.planeState['yoke_roll_ratio']
        planeStateLock.release()
        if obs[2] != 0:
            #wir müssen den Gleitwinkel selber rechnen aus true_airspeed und sinkrate
            #der von XPlane ausgegebene Winkel ist bezogen auf ground_speed und damit bei Wind unbrauchbar.
            obs[0] = np.rad2deg(np.arctan(obs[3]/obs[2]))

        return obs


    def awaitNextObservation(self):
        """Blocks until a new observation is received"""
        newDataEvent.clear()
        newDataEvent.wait(1)    #1 second timeout
        return newDataEvent.isSet()


        