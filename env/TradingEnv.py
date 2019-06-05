import backtrader as bt
import gym
import numpy as np
from gym import spaces

from env.RemoteCerebro import RemoteCerebroRunner


class TradingEnv(gym.Env):
    """A Bitcoin trading environment for OpenAI gym"""
    metadata = {'render.modes': ['human', 'system', 'none']}
    viewer = None
    remote_cerebro_runner = None

    def __init__(self, cerebro):
        super(TradingEnv, self).__init__()

        self.cerebro = cerebro

        # Actions of the format Buy 1/10, Sell 3/10, Hold (amount ignored), etc.
        self.action_space = spaces.MultiDiscrete([3, 100])
        self.observation_space = spaces.Box(low=0, high=np.inf, shape=(5,), dtype=np.float32)

    def reset(self):
        if self.remote_cerebro_runner:
            self.remote_cerebro_runner.stop()
        self.remote_cerebro_runner = RemoteCerebroRunner(self.cerebro)
        return self._next_observation(self.remote_cerebro_runner.start())[0]

    def step(self, action):
        observation = self.remote_cerebro_runner.action(action)

        obs, done, reward = self._next_observation(observation)

        return obs, reward, done, {}

    def _next_observation(self, observation):

        if observation['event'] == 'done':
            return [], True, observation['net_value']
        else:
            rejected_orders = observation['rejected_orders']
            done = True in [order.status in [bt.Order.Canceled, bt.Order.Margin, bt.Order.Rejected] for order in
                            rejected_orders]

            obs = [
                observation['open'],
                observation['high'],
                observation['close'],
                observation['low'],
                observation['volume']
            ]

            return obs, done, observation['net_value']

    def render(self, mode='human'):
        self.remote_cerebro_runner.plot()

    def close(self):
        if self.remote_cerebro_runner:
            self.remote_cerebro_runner.stop()
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
