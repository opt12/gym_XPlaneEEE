# wrappers bluntly stolen from https://github.com/PacktPublishing/Deep-Reinforcement-Learning-Hands-On/blob/master/Chapter06/lib/wrappers.py
# but reduced for simplicity
import gym
import gym.spaces
import numpy as np
import collections

class _MeanBuffer:   #bluntly stolen from Lapan p. 260
    def __init__(self, capacity):
        self.capacity = capacity
        self.deque = collections.deque(maxlen=capacity)
        self.sum = 0.0
    
    def clear(self):
        self.sum = 0.0
        self.deque.clear()

    def add(self, val):
        if len(self.deque) == self.capacity:
            self.sum -= self.deque[0]
        self.deque.append(val)
        self.sum += val

    def mean(self):
        if not self.deque:
            return 0.0
        return self.sum / len(self.deque)

class BufferWrapper(gym.ObservationWrapper):
    """
    Replaces the single observation coming directly from the environment by a stack of
    the last n_steps observations.

    This wrapper can be used to present soe dynamics over the last steps to the agent.

    TODO: Check the datatypes. I'm not quite sure whether all the matix and tensor shapes are really correct.
    """
    def __init__(self, env, n_steps, dtype=np.float32):
        super(BufferWrapper, self).__init__(env)
        self.dtype = dtype
        old_space = env.observation_space
        self.observation_space = gym.spaces.Box(old_space.low.repeat(n_steps, axis=0),
                                                old_space.high.repeat(n_steps, axis=0), dtype=dtype)

    def reset(self):
        self.buffer = np.zeros_like(self.observation_space.low, dtype=self.dtype)
        return self.observation(self.env.reset())

    def observation(self, observation):
        self.buffer[:-1] = self.buffer[1:]
        self.buffer[-1] = observation
        return self.buffer

import time
class TimeLimit(gym.Wrapper):
    """
    Applies a time limit or a maximum number of steps to the episodes of an environment.
    This enables the splitting of "endless" environments into smaller episodes for training.
    
    Arguments (either one is optional)
    ----------------------------------
    :param max_episode_seconds = None: give maximum length in seconds

    :param max_episode_steps = None: give maximum length in steps
    """
    def __init__(self, env, max_episode_seconds=None, max_episode_steps=None):
        super(TimeLimit, self).__init__(env)
        self._max_episode_seconds = max_episode_seconds
        self._max_episode_steps = max_episode_steps
        self._elapsed_steps = 0
        self._episode_started_at = None

    @property
    def _elapsed_seconds(self):
        return time.time() - self._episode_started_at

    def _past_limit(self):
        """Return true if we are past our limit"""
        if self._max_episode_steps is not None and self._max_episode_steps <= self._elapsed_steps:
            gym.logger.debug("Env has passed the step limit defined by TimeLimit.")
            return True

        if self._max_episode_seconds is not None and self._max_episode_seconds <= self._elapsed_seconds:
            gym.logger.debug("Env has passed the seconds limit defined by TimeLimit.")
            return True

        return False

    def step(self, action):
        assert self._episode_started_at is not None, "Cannot call env.step() before calling reset()"
        observation, reward, done, info = self.env.step(action)
        self._elapsed_steps += 1

        if self._past_limit():
            if self.metadata.get('semantics.autoreset'):
                _ = self.reset() # automatically reset the env
            done = True 

        return observation, reward, done, info

    def reset(self, **kwargs):
        self._episode_started_at = time.time()
        self._elapsed_steps = 0
        return self.env.reset(**kwargs)

class EndOfBadEpisodes(gym.Wrapper):
    """
    Prematurely ends an episode if the mean reward gained over the last n_steps steps
    is worse than the limit given in worst_reward_limit.
    
    Arguments
    ---------
    :param worst_reward_limit: the lower limit for the mean reward to end an episode prematurely

    :param n_steps = 1: give length of the moving average window to check the reward

    :param suicide_penalty = -100: The additional penalty for a premature end of Episode. 
    Make this negative enough to prevent the agent from learning suicide.
    """
    def __init__(self, env, worst_reward_limit, n_steps = 1, suicide_penalty = -100):
        super(EndOfBadEpisodes, self).__init__(env)
        self._worst_reward_limit = worst_reward_limit
        self._n_steps = n_steps
        self._past_reward_buffer = _MeanBuffer(n_steps)
        self._suicide_penalty = suicide_penalty

    def step(self, action):
        observation, reward, done, info = self.env.step(action)
        self._past_reward_buffer.add(reward)
        mean = self._past_reward_buffer.mean()
        if  mean < self._worst_reward_limit:
            info_string = f'Mean reward over last {self._n_steps} steps {mean} = < {self._worst_reward_limit}. ==> Prematurely stopping current episode'
            print (info_string)
            gym.logger.debug(info_string)
            done = True
            reward += self._suicide_penalty
        return observation, reward, done, info

    def reset(self, **kwargs):
        self._past_reward_buffer.clear()
        return self.env.reset(**kwargs)


class TimedActions(gym.ActionWrapper):
    """
    An ActionWrapper for gym environments that issues only a given (maximum) amount of actions per second to
    the environment. This is useful for interacting with real-time physical systems that need some time to settle
    after an action was issued. (e. g. interaction with XPlane where it deosn't make any sense to issue more than
    half a handful of commands per second.)

    After a env.reset() the next action may be issued immediately.
        Arguments
    ---------
    :param actions_per_second = 10: the number of steps per second that are maximally issued to the environment

    """
    def __init__(self, env, actions_per_second = 10):
        super(TimedActions, self).__init__(env)
        self.time_delay_between_actions = 1/actions_per_second
        #initialize next action time so that the first action will be issued immeadiately
        self.next_action_time = time.time()

    def step(self, action):
        wait_time = self.next_action_time - time.time() #determine the waiting time from now on
        self.next_action_time += self.time_delay_between_actions #reschedule the event
        if wait_time > 0:
            time.sleep(wait_time)
        return self.env.step(action)    #finally issue the action and return
    
    def reset(self, **kwargs):
        #re-initialize next action time so that the first action will be issued immeadiately
        self.next_action_time = time.time()
        return self.env.reset(**kwargs)


