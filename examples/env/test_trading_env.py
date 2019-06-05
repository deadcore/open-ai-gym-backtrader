import pandas as pd
import backtrader as bt

from env.TradingEnv import TradingEnv


def main():
    df = pd.read_csv('data/binance-ETHBTC-1m-01-01-2017-01-01-2018.csv')[:1000]
    df['open_timestamp'] = pd.to_datetime(df['open_timestamp'], unit='ms')
    df = df.set_index('open_timestamp').sort_values('open_timestamp')

    cerebro = bt.Cerebro()

    cerebro.broker.setcash(0.1885)
    cerebro.broker.setcommission(commission=0.0025)

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    env = TradingEnv(cerebro)

    for i_episode in range(1000):
        env.reset()
        for t in range(100):
            action = env.action_space.sample()
            observation, reward, done, info = env.step(action)
            if done:
                print(f"Episode finished after {t + 1} timestamps with reward: {reward}")
                env.render()
                break
    env.close()


if __name__ == "__main__":
    main()
