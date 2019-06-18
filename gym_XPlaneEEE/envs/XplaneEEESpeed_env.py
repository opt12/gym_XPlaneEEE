import gym
from gym import spaces
# from gym import utils
# from gym.utils import seeding
import numpy as np
import datetime

from gym_XPlaneEEE.utils.IpcClient import IpcClient
from gym_XPlaneEEE.utils.dataCenter import DataCenter
from gym_XPlaneEEE.utils.xPlaneGymCalculations import prepareInitialPlaneState


import logging
logger = logging.getLogger(__name__)

MAX_EPISODE_LENGTH = 90    #end the episode after 90 seconds
SOCKET_NAME = "/tmp/eee_AutoViewer"
DESIRED_SPEED = 68  #the best glide for the Cessna is 68 KIAS
PUNISHMENT_STALL = -1   #TODO compare with the speed punishment and scale accordingly

def clamp(n, minn, maxn): return max(min(maxn, n), minn)
def knots_in_ms(knots): return  knots * 0.51444444444
def ms_in_knots(ms): return  ms / 0.51444444444

class XplaneEEESpeedEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(XplaneEEESpeedEnv, self).__init__()
        self.dc = DataCenter.instance()
        self.ipcClient = None
        self.curr_episode = 0
        self.reward = -10
        # Define action and observation space
        #- yoke_pitch_ratio
        self.action_space = spaces.Box(low=np.array([-1.0]), high=np.array([1.0]))

        #- indicated_airspeed_ms #the speed to be controlled
        #- stallWarning          #The stall warning signal
        #- h_ind                 #Indicated barometric altitude, quite probably in feet actually.
        #- alpha                 #angle of attack
        #- true_theta            #pitch
        #- yoke_pitch_ratio      #The deflection of the joystick axis controlling pitch.
        #- true_phi              #roll
        #- yoke_roll_ratio       #The deflection of the joystick axis controlling roll.
        self.observation_space = spaces.Box(low=np.array([0.0,   0.0,     0.0,  10.0, -30.0, -1.0, -90.0, -1.0]), 
                                           high=np.array([120.0, 1.0, 15000.0, +10.0, +30.0, +1.0, +90.0, +1.0]), dtype=np.float32)
        try: 
            self._establish_connection()
        except Exception as inst:
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)          # __str__ allows args to be printed directly, but may be overridden in exception subclasses
            raise inst           # re-raise the exception to higher instances TODO: is this a good idea

    def __del__(self):
        self.ipcClient.setContinueFlag(False)   #make the ipcListener stop

    def _establish_connection(self):
        #start a listener thread
        self.ipcClient = IpcClient.instance()
        self.ipcClient.connect(SOCKET_NAME)
        self.ipcClient.daemon = True    #like seen on https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
        self.ipcClient.start()

    def step(self, action):
        """

        Parameters
        ----------
        action (float): is the value of the elevator in the ranges [-1:1] as continuous float 

        Returns
        -------
        ob, reward, episode_over, info : tuple
            ob (object) :
                an environment-specific object representing your observation of
                the environment.
            reward (float) :
                amount of reward achieved by the previous action. The scale
                varies between environments, but the goal is always to increase
                your total reward.
            episode_over (bool) :
                whether it's time to reset the environment again. Most (but not
                all) tasks are divided up into well-defined episodes, and done
                being True indicates the episode has terminated. (For example,
                perhaps the pole tipped too far, or you lost your last life.)
            info (dict) :
                 diagnostic information useful for debugging. It can sometimes
                 be useful for learning (for example, it might contain the raw
                 probabilities behind the environment's last state change).
                 However, official evaluations of your agent are not allowed to
                 use this for learning.
        """
        self._take_action(action)
        self.speedObservation = self.dc.getSpeedObservation()
        self.reward = self._get_reward()
        episode_over = self._check_end_episode()    #TODO
        return self.speedObservation, self.reward, episode_over, {}

    def _take_action(self, action):
        action = float(action)  # convert the np.array[float32] to a single float value
        clamp(action, -1.0, +1.0)
        # prepare the entire message to be sent out to the DubinsPilot socket
        ctrlDict = {}
        ctrlDict['yoke_pitch_ratio'] = action  #action is a numpy.array with a single element
        self.ipcClient.socketSendData('SET_ELEVATOR', 1, ctrlDict)

    def _check_end_episode(self):
        """
        Checks the end of an episode.
        An Episode is over when either
          - 300 seconds passed since the start of the episode
          - the deviation from the desired speed is too high
          - the plane is in some weird flight conditions
        Returns
        -------
        true: when the episode is over
        false: when the episde continues
        """
        if (datetime.datetime.now() - self.startOfEpisode).seconds >= MAX_EPISODE_LENGTH:
            return True

        return False    #TODO check for weird flight conditions

    def reset(self):
        """
        Reset the state of the environment and returns an initial observation.
        Returns
        -------
        observation (object): the initial observation of the space.
        """
        self.curr_step = -1
        self.curr_episode += 1
        self.startOfEpisode = datetime.datetime.now()
        # calculate new initial plane state
        newPlaneState = prepareInitialPlaneState()
        # set initial plane state
        if self.ipcClient.socketSendData("SET_PLANE_STATE", 1, newPlaneState['data']):
            #get the first observation after changing the plane's state
            print("Waiting for first two observations after RESET")
            if not self.dc.awaitNextObservation():  #block until a new observation is sent from XPlane
                return None #timeout ocurred
            if not self.dc.awaitNextObservation():  #Do this twice to be sure, there is no in between state captured
                return None #timeout ocurred
            return self.dc.getSpeedObservation()
        else:
            return None

    def render(self, mode='human', close=False):
        """ This function is currently useless as the rendering is 
            done externally. 
        """
        print(f'indicated Airspeed: {ms_in_knots(self.speedObservation[0])}; target Airspeed: {DESIRED_SPEED}; reward: {self.reward};')
    
    def _seed(self):
        pass

    def _calculate_speed_deviation(self, ias_ms):
        """
        calculates the mean square deviation of the current state from the desired speed
        """
        #normalize
        ias_ms_norm = ias_ms/knots_in_ms(DESIRED_SPEED)
        mse = (ias_ms_norm - 1)**2
        return mse
    
    def _caclulate_actuation_smoothness(self):
        #TODO calculate the smoothness over the last n elevator actions and weigh them with a suitable factor
        return 0

    def _get_reward(self):
        """ 
        Reward is given for maintaining the desired glide speed within suitable flight conditions.
        The maximum reward to be earned is 0. Quadratic deviation from the desired speed is given
        as negative reward.
        Additional punishment is given 
          - when the stall warning is active.
          #TODO - for the smoothness of the actuation
        """
        #calculate deviation from the desired speed. Desired speed is normalized to 1.
        reward = -10*self._calculate_speed_deviation(self.speedObservation[0])  #TODO this calculation and the factor are still somewhat arbitrary
        if self.speedObservation[1] != 0:
            reward += PUNISHMENT_STALL
        reward += self._caclulate_actuation_smoothness()
        return reward
