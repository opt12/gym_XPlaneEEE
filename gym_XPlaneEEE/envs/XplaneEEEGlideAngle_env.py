
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
MAX_ALLOWED_DEVIATION = 10 #end the episode when the glide angle is further away then 10° from the setpoint
SOCKET_NAME = "/tmp/eee_AutoViewer"
DESIRED_GLIDE_ANGLE = -6  #just a first guess
PUNISHMENT_STALL = -1   #TODO compare with the speed punishment and scale accordingly

def clamp(n, minn, maxn): return max(min(maxn, n), minn)
def knots_in_ms(knots): return  knots * 0.51444444444
def ms_in_knots(ms): return  ms / 0.51444444444

class XplaneEEEGlideAngleEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(XplaneEEEGlideAngleEnv, self).__init__()
        self.dc = DataCenter.instance()
        self.ipcClient = None
        self.curr_episode = 0
        self.reward = 0
        self.targetGlideAngle = DESIRED_GLIDE_ANGLE
        # Define action and observation space
        #- yoke_pitch_ratio
        self.action_space = spaces.Box(-1, 1, shape = (1,), dtype=np.float32)

        #- glide Angle           #the descent angle to be controlled glide Angle = to_degrees(atan(Vh_ind/tas)
        #- stallWarning          #The stall warning signal
        #- tas                   #the true airspeed [m/s]
        ##- Vh_ind                #the sinkrate [m/s]
        ##- h_ind                 #Indicated barometric altitude, quite probably in feet actually.
        ##- alpha                 #angle of attack
        ##- true_theta            #pitch
        ##- yoke_pitch_ratio      #The deflection of the joystick axis controlling pitch.
        ##- true_phi              #roll
        ##- yoke_roll_ratio       #The deflection of the joystick axis controlling roll.
        # self.observation_space = spaces.Box(low=np.array([-90.0, 0.0,   0.0, -100.0,     0.0, -25.0, -90.0, -1.0, -90.0, -1.0]), 
        #                                    high=np.array([ 90.0, 1.0, 200.0, +100.0, 15000.0, +25.0, +90.0, +1.0, +90.0, +1.0]), dtype=np.float32)
        # Observations are:
        # obs[0]: sin(angleDeviation)
        # obs[1]: cos(angleDeviation)
        # obs[2]: Qrad (i. e. ThetaDot /rad)
        # obs[3]: angleDeviation /rad
        # obs[4]: yoke_pitch_ratio (of last action)
        # # obs[5]: stall Warning
        # # obs[6]: true Airspeed [m/s range 0...120]

        self.observation_space = spaces.Box(low=np.array([-1.0, -1.0, -20.0, -3.14, -1.0]), 
                                           high=np.array([ 1.0,  1.0,  20.0,  3.14,  1.0]), dtype=np.float32)
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

        obs = self._get_Observations()
        self.glideAngleObservation = obs
        self.reward = self._get_reward(obs[3], obs[2], obs[4])

        episode_over = self._check_end_episode()    #TODO
        return self.glideAngleObservation, self.reward, episode_over, {}

    def _get_Observations(self):
        """
        Observations are:
        obs[0]: sin(angleDeviation)
        obs[1]: cos(angleDeviation)
        obs[2]: Qrad (i. e. ThetaDot /rad)
        obs[3]: angleDeviation /rad
        obs[4]: yoke_pitch_ratio (of last action)
        # obs[5]: stall Warning
        # obs[6]: true Airspeed [m/s range 0...120]
        """

        keyList = [None, None, 'Qrad', None, 'yoke_pitch_ratio']
        obs = self.dc.getObservation(keyList)
        tas, Vh_ind = self.dc.getObservation(['true_airspeed','vh_ind'])
        glideAngleRad = 0.0
        if tas != 0:
            #wir müssen den Gleitwinkel selber rechnen aus true_airspeed und sinkrate
            #der von XPlane ausgegebene Winkel ist bezogen auf ground_speed und damit bei Wind unbrauchbar.
            glideAngleRad = np.arctan(Vh_ind/tas)  #in radians
        # glideAngleRad = np.deg2rad(self.dc.getObservation(['true_theta']))
        targetGlideAngle = np.deg2rad(self.dc.getObservation([['targetValues','requestedClimbRate']])[0])
        angleDeviation = glideAngleRad - targetGlideAngle
        obs[0] = np.sin(angleDeviation)
        obs[1] = np.cos(angleDeviation)
        obs[3] = angleDeviation
        return obs

    def fakeStep(self, action):
        """
        The fakeStep method is to get the actions and rewards into the GYM environment from the PID controller of DubinsPilot.
        The action parameter will be silently swallowed and only the current observation and reward is returned.
        
        Parameters
        ----------
        action (float): Will be ignored.

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
        # self._take_action(action)

        obs = self._get_Observations()
        self.glideAngleObservation = obs
        self.reward = self._get_reward(obs[3], obs[2], obs[4])

        episode_over = self._check_end_episode()    #TODO
        return self.glideAngleObservation, self.reward, episode_over, {}

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
          - MAX_EPISODE_LENGTH seconds passed since the start of the episode
          - the deviation from the desired Angle is too high
          - the plane is in some weird flight conditions
        Returns
        -------
        true: when the episode is over
        false: when the episde continues
        """
        return False    # the TimeLimit is done using the TimeLimit-Wrapper
        # if (datetime.datetime.now() - self.startOfEpisode).seconds >= MAX_EPISODE_LENGTH:
        #     print(f'{MAX_EPISODE_LENGTH} seconds over. Starting new episode.')
        #     return True
        # deviation = abs(self.glideAngleObservation[0] - self.targetGlideAngle)
        # if  deviation >= MAX_ALLOWED_DEVIATION: #TODO Das ist Mist, dass ich hier wissen muss, dass [0] der GLide angle ist. 
        #     print(f'Deviation too high: {deviation}')
        #     #TODO stelle das um auf ein Kriterium, das mit dem self.reward arbeitet
        #     return True
        # return False    #TODO check for weird flight conditions

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
        waitingSteps = 10
        # calculate new initial plane state
        newPlaneState = prepareInitialPlaneState()
        # set initial plane state
        if self.ipcClient.socketSendData("SET_PLANE_STATE", 1, newPlaneState['data']):
            self._take_action(0.0)  #reset the elevator to 0
            #get the first observation after changing the plane's state
            print("Waiting for first {} observations after RESET".format(waitingSteps))
            for i in range(waitingSteps):
                if not self.dc.awaitNextObservation():  #block until a new observation is sent from XPlane
                    # raise ConnectionError("Didn't receive any new Observations within one second. Check Connection to XPlane!")
                    return None #timeout ocurred
            return self._get_Observations()
        else:
            return None

    def render(self, mode='human', close=False):
        """ This function is currently useless as the rendering is 
            done externally. 
        """
        self.glideAngleObservation = self._get_Observations()
        print(f'current Deviation: {self.glideAngleObservation[3]}; current Qrad: {self.glideAngleObservation[2]}; reward: {self.reward};')
    
    def _seed(self):
        pass

    # def _calculate_glide_angle_deviation(self, angle):
    #     """
    #     calculates absolute value deviation of the current state from the desired glide angle
    #     """
    #     self.targetGlideAngle = self.dc.getObservation([['targetValues','requestedClimbRate']])[0]
    #     #angles are usually small, so no normalization
    #     dev = (angle - self.targetGlideAngle)
    #     return dev
    
    def _caclulate_actuation_smoothness(self):
        #TODO calculate the smoothness over the last n elevator actions and weigh them with a suitable factor
        return 0

    def _get_reward(self, angleDeviation, qrad, actuation):
        """ 
        Reward is given for maintaining the desired glide angle within suitable flight conditions.
        The maximum reward to be earned is 0. Quadratic deviation from the desired angle is given
        as negative reward.
        Additional punishment is given 
          #TODO - when the stall warning is active.
          #TODO - for the smoothness of the actuation
        """
        cost = 10*angleDeviation**2 + 0.1*qrad**2 + 0.1*actuation**2
        return -cost
