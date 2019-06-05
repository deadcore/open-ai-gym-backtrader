import copy
import threading
from queue import Queue

import backtrader as bt

Stop = [-99, 0]


class RemoteCerebroRunner:

    def __init__(self, cerebro: bt.Cerebro):
        self.cerebro = copy.deepcopy(cerebro)
        self.observation_queue = None
        self.action_queue = None
        self.t = None

    def start(self):
        self.observation_queue = Queue(maxsize=1)
        self.action_queue = Queue(maxsize=1)
        self.t = threading.Thread(target=self.cerebro_runner)
        self.t.start()
        return self.observation_queue.get(timeout=2)

    def stop(self):
        self._stop_cerebro_runner()

    def action(self, action):
        self.action_queue.put(action, timeout=2)
        return self.observation_queue.get(timeout=2)

    def _stop_cerebro_runner(self):
        self.cerebro.runstop()
        self.action_queue.put(Stop, timeout=2)

        if self.t is not None:
            self.t.join()

    def cerebro_runner(self):
        self.cerebro.addstrategy(RemoteStrategy,
                                 action_queue=self.action_queue,
                                 observation_queue=self.observation_queue)
        # Run over everything
        self.cerebro.run()

        self.observation_queue.put({'event': 'done', 'net_value': self.cerebro.broker.get_value()})

    def plot(self):
        self.cerebro.plot()


# Create a Stratey
class RemoteStrategy(bt.Strategy):

    def __init__(self, action_queue, observation_queue):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.action_queue = action_queue
        self.observation_queue = observation_queue
        self.dataclose = self.datas[0].close
        self.order = None
        self.rejected_orders = []

    def log(self, txt, dt=None):
        pass
        # dt = dt or self.datas[0].datetime.datetime()
        # print('%s - %s' % (dt, txt))

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price, order.executed.value, order.executed.comm))

            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.rejected_orders.append(self.order)

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log(
            f'OHCLV: {self.data.tick_open}, {self.data.tick_high}, {self.data.tick_close}, {self.data.tick_low}, {self.data.tick_volume}')
        self.log('Publishing observation')

        self.observation_queue.put(self._observation(), timeout=2)

        self.log('Waiting on action')

        self._handle_action(self.action_queue.get(timeout=2))
        self.log("Finished handling action")

    def _observation(self):
        return {
            'event': 'ohcl',
            'open': self.data.tick_open,
            'high': self.data.tick_high,
            'close': self.data.tick_close,
            'low': self.data.tick_low,
            'volume': self.data.tick_volume,
            'rejected_orders': self.rejected_orders,
            'net_value': self.env.broker.get_value(),
        }

    def _handle_action(self, action):
        self.log(f'Received action: {action}')

        order_type = action[0]
        size = action[1]

        if order_type == 0:
            self.order = self.buy(size=size)
        elif order_type == 1:
            self.order = self.sell(size=size)
        elif order_type == Stop[0]:
            self.env.runstop()
