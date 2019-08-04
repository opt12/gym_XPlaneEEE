#!/usr/bin/env python3
from gym_XPlaneEEE.envs import XplaneEEEGlideAngleEnv
from gym_XPlaneEEE.wrappers import wrappers
import gym
import time
import argparse
import numpy as np

DEFAULT_ENV_NAME = "XPlaneEEEGlideAngle-v0"
STEPS_PER_SECOND = 10

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument("-m", "--model", required=True, help="Model file to load")
    parser.add_argument("-e", "--env", default=DEFAULT_ENV_NAME,
                        help="Environment name to use, default=" + DEFAULT_ENV_NAME)
    # parser.add_argument("-r", "--record", help="Directory to store video recording")
    # parser.add_argument("--no-visualize", default=True, action='store_false', dest='visualize',
    #                     help="Disable visualization of the game play")
    args = parser.parse_args()

    env = gym.make(args.env)
    # env = wrappers.FakeActions(env)
    env = wrappers.TimeLimit(env, max_episode_steps=250)
    # env = wrappers.EndOfBadEpisodes(env, -80, 50, suicide_penalty = -3000)
    env = wrappers.TimedActions(env, STEPS_PER_SECOND)
    # env = wrappers.ObservationScaler(env)
    # env = wrappers.BufferWrapper(env, 10)

    total_reward = 0.0
    total_steps = 0
    episode_number = 0
    obs = env.reset()
    episode_over = False

    #perform some episodes with a random agent
    while episode_number< 10:
        action = env.action_space.sample()
        obs, reward, episode_over, info = env.step(action)
        total_steps +=1
        total_reward += reward
        # env.render()
        # print(f'{total_steps}: Action: {action} yields:  obs: {obs}, reward: {reward}')
        if episode_over:
            print(f'Episode {episode_number} over after {total_steps} steps with total reward = {total_reward}.')
            total_reward = 0.0
            total_steps = 0
            episode_number += 1
            obs = env.reset()
            episode_over = False
            continue
    print(f'Over and Out')





