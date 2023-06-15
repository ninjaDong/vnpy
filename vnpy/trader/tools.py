import decimal
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Dict, List

from vnpy.trader.constant import Interval, Direction, OrderType
from vnpy.trader.object import BarData, TickData


def get_hold_pnl(open_p: float, close_p: float, pos, ct_size: float, inverse: bool) -> float:
    """"""
    if not open_p or not close_p:
        return 0

    if inverse:  # For crypto currency inverse contract
        holding_pnl = pos * (1 / open_p - 1 / close_p) * ct_size

    else:  # For normal contract
        holding_pnl = pos * (close_p - open_p) * ct_size

    return holding_pnl


def get_commission(price: float, pos: float, ct_size: float, inverse: bool, rate: float):
    if not price:
        return
    if inverse:  # 反向合约
        turnover = pos * ct_size * (1 / price)
        commission = turnover * rate

    else:  # 正向合约
        turnover = pos * ct_size * price
        commission = turnover * rate
    return commission


def get_pinbar_statu(bar: BarData):
    up_size = bar.high_price - max(bar.open_price, bar.close_price)
    down_size = min(bar.open_price, bar.close_price) - bar.low_price
    body_size = abs(bar.open_price - bar.close_price)
    all_size = bar.high_price - bar.low_price
    # 阳线

    if bar.close_price > bar.open_price and down_size > all_size / 3 > up_size:
        return 1
    if down_size > all_size*2/3:
        return 1
    if bar.close_price < bar.open_price and up_size > all_size / 3 > down_size:
        return -1
    if up_size > all_size*2/3:
        return -1
    return 0

@dataclass
class MyOrderData:
    direction: Direction
    target_pos: decimal  # 目标仓位 判断开仓是否完成。

    open_datetime: datetime = None
    close_datetime: datetime = None

    size: int = 0  # 已开仓次数
    opened_pos: decimal = decimal.Decimal('0')
    closed_pos: decimal = decimal.Decimal('0')

    opened_value: float = 0.0
    closed_value: float = 0.0

    order_type: OrderType = OrderType.LIMIT

    open_price: List = field(default_factory=list)
    close_price: List = field(default_factory=list)

    open_avg_price: float = 0.0
    close_avg_price: float = 0.0

    comm_fee: float = 0.0
    pnl: float = 0.0

    open_order_id: List = field(default_factory=list)
    close_order_id: List = field(default_factory=list)

    top_price: float = 0.0
    floor_price: float = 0.0

    net_pnl: float = 0.0
    pnl_ratio: float = 0.0
    max_pnl_ratio: float = 0.0
    min_pnl_ratio: float = 0.0

    pre_dif: float = 0.0

    def process(self):
        self.net_pnl = self.pnl + self.comm_fee
        if self.opened_pos and self.opened_value:
            self.open_avg_price = self.opened_value / float(self.opened_pos)
        if self.closed_pos and self.closed_value:
            self.close_avg_price = self.closed_value / float(self.closed_pos)
        if self.open_avg_price:
            if self.direction == Direction.LONG:
                if self.top_price and self.floor_price:
                    self.max_pnl_ratio = (self.top_price - self.open_avg_price)/self.open_avg_price
                    self.min_pnl_ratio = (self.floor_price - self.open_avg_price)/self.open_avg_price
                if self.close_avg_price:
                    self.pnl_ratio = (self.close_avg_price - self.open_avg_price) / self.open_avg_price
            elif self.direction == Direction.SHORT:
                if self.top_price and self.floor_price:
                    self.max_pnl_ratio = (self.open_avg_price - self.floor_price)/self.open_avg_price
                    self.min_pnl_ratio = (self.open_avg_price - self.top_price)/self.open_avg_price
                if self.close_avg_price:
                    self.pnl_ratio = (self.open_avg_price - self.close_avg_price) / self.open_avg_price


class SecondBarGenerator:
    """
    For:
    generateing 1 second bar data from tick data

    Notice:
    1. for x second bar, x must be able to divide 60: 2, 3, 5, 6, 10, 15, 20, 30
    2. for x minute bar, x must be able to divide 60: 2, 3, 5, 6, 10, 15, 20, 30
    2. for x hour bar, x can be any number
    """

    def __init__(
            self,
            on_bar: Callable,
            window: int = 0,
            on_window_bar: Callable = None
    ):
        """Constructor"""
        self.bar: BarData = None
        self.on_bar: Callable = on_bar

        self.interval: Interval = Interval.SECOND
        self.interval_count: int = 0

        self.hour_bar: BarData = None

        self.window: int = window
        self.window_bar: BarData = None
        self.on_window_bar: Callable = on_window_bar

        self.last_bar: BarData = None
        self.last_tick: TickData = None

    def update_tick(self, tick: TickData) -> None:
        """
        Update new tick data into generator.
        """
        new_second = False

        # Filter tick data with 0 last price
        if not tick.last_price:
            return

        # Filter tick data with older timestamp
        if self.last_tick and tick.datetime < self.last_tick.datetime:
            return

        if not self.bar:
            new_second = True
        elif (
                (self.bar.datetime.second != tick.datetime.second)
                or (self.bar.datetime.minute != tick.datetime.minute)
                or (self.bar.datetime.hour != tick.datetime.hour)
        ):
            self.bar.datetime = self.bar.datetime.replace(
                microsecond=0
            )
            self.on_bar(self.bar)

            new_second = True

        if new_second:
            self.bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                interval=Interval.SECOND,
                datetime=tick.datetime,
                gateway_name=tick.gateway_name,
                open_price=tick.last_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                open_interest=tick.open_interest
            )
        else:
            self.bar.high_price = max(self.bar.high_price, tick.last_price)
            if tick.high_price > self.last_tick.high_price:
                self.bar.high_price = max(self.bar.high_price, tick.high_price)

            self.bar.low_price = min(self.bar.low_price, tick.last_price)
            if tick.low_price < self.last_tick.low_price:
                self.bar.low_price = min(self.bar.low_price, tick.low_price)

            self.bar.close_price = tick.last_price
            self.bar.open_interest = tick.open_interest
            self.bar.datetime = tick.datetime

        if self.last_tick:
            volume_change = tick.volume - self.last_tick.volume
            self.bar.volume += max(volume_change, 0)

        self.last_tick = tick

    def update_bar(self, bar: BarData) -> None:
        """
        Update 1 minute bar into generator
        """
        if self.interval == Interval.SECOND:
            self.update_bar_second_window(bar)
        if self.interval == Interval.MINUTE:
            self.update_bar_minute_window(bar)
        elif self.interval == Interval.HOUR:
            self.update_bar_hour_window(bar)

    def update_bar_second_window(self, bar: BarData) -> None:
        """"""
        # If not inited, create window bar object
        if not self.window_bar:
            dt = bar.datetime.replace(microsecond=0)
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price
            )
        # Otherwise, update high/low price into window bar
        else:
            self.window_bar.high_price = max(
                self.window_bar.high_price,
                bar.high_price
            )
            self.window_bar.low_price = min(
                self.window_bar.low_price,
                bar.low_price
            )

        # Update close price/volume into window bar
        self.window_bar.close_price = bar.close_price
        self.window_bar.volume += int(bar.volume)
        self.window_bar.open_interest = bar.open_interest

        # Check if window bar completed
        if not (bar.datetime.second + 1) % self.window:
            self.on_window_bar(self.window_bar)
            self.window_bar = None

        # Cache last bar object
        self.last_bar = bar

    def update_bar_minute_window(self, bar: BarData) -> None:
        """"""
        # If not inited, create window bar object
        if not self.window_bar:
            dt = bar.datetime.replace(second=0, microsecond=0)
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price
            )
        # Otherwise, update high/low price into window bar
        else:
            self.window_bar.high_price = max(
                self.window_bar.high_price,
                bar.high_price
            )
            self.window_bar.low_price = min(
                self.window_bar.low_price,
                bar.low_price
            )

        # Update close price/volume into window bar
        self.window_bar.close_price = bar.close_price
        self.window_bar.volume += int(bar.volume)
        self.window_bar.open_interest = bar.open_interest

        # Check if window bar completed
        if not (bar.datetime.minute + 1) % self.window:
            self.on_window_bar(self.window_bar)
            self.window_bar = None

        # Cache last bar object
        self.last_bar = bar

    def update_bar_hour_window(self, bar: BarData) -> None:
        """"""
        # If not inited, create window bar object
        if not self.hour_bar:
            dt = bar.datetime.replace(minute=0, second=0, microsecond=0)
            self.hour_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                volume=bar.volume
            )
            return

        finished_bar = None

        # If minute is 59, update minute bar into window bar and push
        if bar.datetime.minute == 59:
            self.hour_bar.high_price = max(
                self.hour_bar.high_price,
                bar.high_price
            )
            self.hour_bar.low_price = min(
                self.hour_bar.low_price,
                bar.low_price
            )

            self.hour_bar.close_price = bar.close_price
            self.hour_bar.volume += int(bar.volume)
            self.hour_bar.open_interest = bar.open_interest

            finished_bar = self.hour_bar
            self.hour_bar = None

        # If minute bar of new hour, then push existing window bar
        elif bar.datetime.hour != self.hour_bar.datetime.hour:
            finished_bar = self.hour_bar

            dt = bar.datetime.replace(minute=0, second=0, microsecond=0)
            self.hour_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=bar.volume
            )
        # Otherwise only update minute bar
        else:
            self.hour_bar.high_price = max(
                self.hour_bar.high_price,
                bar.high_price
            )
            self.hour_bar.low_price = min(
                self.hour_bar.low_price,
                bar.low_price
            )

            self.hour_bar.close_price = bar.close_price
            self.hour_bar.volume += int(bar.volume)
            self.hour_bar.open_interest = bar.open_interest

        # Push finished window bar
        if finished_bar:
            self.on_hour_bar(finished_bar)

        # Cache last bar object
        self.last_bar = bar

    def on_hour_bar(self, bar: BarData) -> None:
        """"""
        if self.window == 1:
            self.on_window_bar(bar)
        else:
            if not self.window_bar:
                self.window_bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=bar.datetime,
                    gateway_name=bar.gateway_name,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price
                )
            else:
                self.window_bar.high_price = max(
                    self.window_bar.high_price,
                    bar.high_price
                )
                self.window_bar.low_price = min(
                    self.window_bar.low_price,
                    bar.low_price
                )

            self.window_bar.close_price = bar.close_price
            self.window_bar.volume += int(bar.volume)
            self.window_bar.open_interest = bar.open_interest

            self.interval_count += 1
            if not self.interval_count % self.window:
                self.interval_count = 0
                self.on_window_bar(self.window_bar)
                self.window_bar = None

    def generate(self) -> Optional[BarData]:
        """
        Generate the bar data and call callback immediately.
        """
        bar = self.bar

        if self.bar:
            bar.datetime = bar.datetime.replace(microsecond=0)
            self.on_bar(bar)

        self.bar = None
        return bar
