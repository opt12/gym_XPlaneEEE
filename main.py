from gym_XPlaneEEE.envs import XplaneEEEGlideAngleEnv
import gym

from time import sleep

if __name__ == "__main__":
    env = gym.make("XPlaneEEEGlideAngle-v0")
    
    total_reward = 0.0
    total_steps = 0
    obs = env.reset()
    episode_over = False
    #perform 100 random steps
    # for x in range(100):
    while total_steps< 1:
        sleep(0.100)
        total_steps +=1
        action = env.action_space.sample()
        obs, reward, episode_over, info = env.step(action)
        env.render()
        # print(f'{total_steps}: Action: {action} yields:  obs: {obs}, reward: {reward}')
        if episode_over:
            print(f'Episode over after {total_steps} steps.')
            break
    print(f'Over and Out')





