import pandas as pd
from stable_baselines import A2C
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines.common.policies import MlpPolicy

from env.TradingEnv import TradingEnv

df = pd.read_csv('../data/binance-ETHBTC-1m-01-01-2017-01-01-2018.csv')[:1000]

df['open_timestamp'] = pd.to_datetime(df['open_timestamp'], unit='ms')

df = df.set_index('open_timestamp').sort_values('open_timestamp')

slice_point = int(len(df) * 0.8)

train_df = df[:slice_point]
test_df = df[slice_point:]

trading_env_generator = [lambda: TradingEnv(train_df, commission=0.0025, initial_balance=0.1885)]

train_env = DummyVecEnv(trading_env_generator)

model = A2C(MlpPolicy, train_env, verbose=1, tensorboard_log="./tensorboard/", full_tensorboard_log=True)
model.learn(total_timesteps=100_000)

model.save("a2c_eth_btc")

model = A2C.load('a2c_eth_btc.pkl')

test_env = DummyVecEnv(trading_env_generator)

obs = test_env.reset()
for i in range(50000):
    action, _states = model.predict(obs)

    print('action: {}'.format(action))

    obs, rewards, done, info = test_env.step(action)

    print('obs: {}'.format(obs))
    print('rewards: {}'.format(rewards))
    print('done: {}'.format(done))
    print('info: {}'.format(info))

    if done:
        print('I am done')
        break

test_env.close()