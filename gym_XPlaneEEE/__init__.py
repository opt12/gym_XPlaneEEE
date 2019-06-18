import logging
from gym.envs.registration import register

logger = logging.getLogger(__name__)

register(
    id='XPlaneEEESpeed-v0',
    entry_point='gym_XPlaneEEE.envs:XplaneEEESpeedEnv',
    max_episode_steps=3000,    #this equals 300secs=5mins of flight at a rate of 10/sec
    reward_threshold=1.0,   #TODO tbc. don't know yet
    nondeterministic = True,#TODO what does this mean
)

register(
    id='XPlaneEEEGlideAngle-v0',
    entry_point='gym_XPlaneEEE.envs:XplaneEEEGlideAngleEnv',
    max_episode_steps=3000,    #this equals 300secs=5mins of flight at a rate of 10/sec
    reward_threshold=1.0,   #TODO tbc. don't know yet
    nondeterministic = True,#TODO what does this mean
)
