from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from datetime import datetime
import os.path
import sys
import backtrader as bt
import akshare as ak
from backtrader import feeds
import backtrader.feeds as btfeeds
import pandas as pd

# 创建 一个Stratey
class TestStrategy(bt.Strategy):
    params = (
        ('exitbars',5),
        ('maperiod',65),
        ('printlog', False),
    )
    def log(self,txt,dt=None, doprint=False):
        ''' 打印日志 '''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(),txt))
    
    def __init__(self) -> None:
        self.dataclose = self.datas[0].close
        self.order = None
        self.bar_executed=None        
        self.buyprice = None
        self.buycomm = None

        # 添加简单移动平均线
        self.sma = bt.indicators.MovingAverageSimple(self.datas[0],period=self.params.maperiod)
        # Indicators for the plotting show
        bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        bt.indicators.WeightedMovingAverage(self.datas[0], period=25,
                                            subplot=True)
        bt.indicators.StochasticSlow(self.datas[0])
        bt.indicators.MACDHisto(self.datas[0])
        rsi = bt.indicators.RSI(self.datas[0])
        bt.indicators.SmoothedMovingAverage(rsi, period=10)
        bt.indicators.ATR(self.datas[0], plot=False)

    def notify_order(self, order):
        # 订单提交 
        if order.status in [order.Submitted,order.Accepted]:
            #print("订单提交 ")
            return
        # 交易成功
        if order.status in [order.Completed]:
            #买进
            if order.isbuy():
                self.log('买进价格: %.2f,数量：%.2f,费用: %.2f' % 
                        (order.executed.price,
                        order.executed.value,
                        order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm        
            #卖出
            else:
                self.log('卖出价格: %.2f,数量：%.2f,费用: %.2f' % 
                        (order.executed.price,
                        order.executed.value,
                        order.executed.comm))
            
            self.bar_executed = len(self)

        #交易失败的类型
        elif order.status in [order.Canceled,order.Margin,order.Rejected]:
            print('交易不成功/订单没有提及/资金不足/股票退市/暂停交易')   
        self.order = None
    def notify_trade(self,trade):
        if not trade.isclosed:
            return 
        self.log('运营利润,毛利:%.2f,净利：%.2f'%
                (trade.pnl,trade.pnlcomm))
    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])
        '''股票连跌3天买买买'''
        if self.order:
            return
        self.log('self len：%s,bar_executed:%s' % (len(self),self.bar_executed))
        #没有持仓，买入    
        if not self.position:
            if self.dataclose[0] >self.sma[0]:
                if self.dataclose[0] <self.dataclose[-1]:
                    self.log('Buy create ,%.2f'% self.dataclose[0])
                    self.order = self.buy()
        else:
            if self.dataclose[0]< self.sma[0]:
                self.log('卖出:%.2f'% self.dataclose[0])

                self.order = self.sell()

    def stop(self):
        self.log('(移动平均 %2d) Ending Value %.2f'%
                (self.params.maperiod,self.broker.getvalue()),doprint=True)
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TestStrategy)
    # 58 65 营利

    # strats = cerebro.optstrategy(
    #     TestStrategy,
    #     maperiod=(58,65))
    
    cerebro.broker.setcash(100000.0)
    # 购买固定的股票数
    cerebro.addsizer(bt.sizers.FixedSize,stake=100)
    cerebro.broker.setcommission(commission=0.001)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    df = ak.stock_zh_a_daily(symbol='sz000063',start_date='20201103',end_date='20221103',adjust='hfq')
    df.set_index(df['date'],inplace=True)
    df.drop('date',axis=1,inplace=True)
    df.index = pd.to_datetime(df.index)
#    print(df)
    data = bt.feeds.PandasData(dataname=df,fromdate=datetime(2020,11,3),todate=datetime(2022,11,3))
    
    cerebro.adddata(data)
    cerebro.run(maxcpus=4)
    cerebro.plot(style='bar')
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())