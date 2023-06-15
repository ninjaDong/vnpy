import time
import argparse
import asyncio
from datetime import datetime, timedelta
from requests import Response

from vnpy_rest import RestClient
from vnpy.trader.database import get_database, DB_TZ
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData

gateway_name = "OKEX"
REST_HOST = 'https://www.okx.com'
URL = "/api/v5/market/history-candles"
interval = Interval.MINUTE

TIMEDELTA_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}

# 数据频率映射
INTERVAL_VT2OKEX = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1H",
    Interval.DAILY: "1D",
}


def generate_timestamp() -> str:
    """生成时间戳"""
    now: datetime = datetime.utcnow()
    timestamp: str = now.isoformat("T", "milliseconds")
    return timestamp + "Z"


def parse_timestamp(timestamp: str) -> datetime:
    """解析回报时间戳"""
    dt: datetime = datetime.fromtimestamp(int(timestamp) / 1000)
    return DB_TZ.localize(dt)


def query_history():
    """"""
    history = []
    count = 100
    _from = start_dt
    _to = None
    time_delta = TIMEDELTA_MAP[interval]

    while True:
        # Calculate end time
        _to = _from + time_delta * count

        _to = min(_to, end_dt)

        # Create query params
        params = {
            "instId": instId,
            "bar": INTERVAL_VT2OKEX[interval],
            "before": str(int(_from.timestamp() * 1000)),
            "after": str(int(_to.timestamp() * 1000))
        }

        # Get response from server
        try:
            resp: Response = okex_rest_client.request(
                "GET",
                URL,
                params=params
            )
        except BaseException as e:
            msg = repr(e)
            print(msg)
            break

        # Break if request failed with other status code
        if resp.status_code // 100 != 2:
            msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
            print(msg)
            break
        else:
            data = resp.json()
            if not data["data"]:
                m = data["msg"]
                msg = f"获取历史数据为空,{m}"
                print(msg)
                break

            buf = []
            for d in data["data"]:
                ts, o, h, l, c, vol, *_, = d
                dt = parse_timestamp(ts)

                bar = BarData(
                    symbol=instId,
                    exchange=Exchange.OKEX,
                    datetime=dt,
                    interval=interval,
                    volume=float(vol),
                    open_price=float(o),
                    high_price=float(h),
                    low_price=float(l),
                    close_price=float(c),
                    gateway_name=gateway_name
                )
                buf.append(bar)

            buf.reverse()
            history.extend(buf)

            begin = buf[0].datetime
            end = buf[-1].datetime
            msg = f"获取历史数据成功，{instId} - {interval.value}，{begin} - {end}"
            print(msg)

            delta1 = (end_dt - end).total_seconds()
            delta2 = time_delta.total_seconds()

            if delta1 < delta2 * 2:
                break

            # Update start time
            _from = end
            time.sleep(0.1)

    return history


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str, default=None)
    parser.add_argument('--dt', type=str, default=None)
    args = parser.parse_args()
    instId = args.id.upper() + "-USDT-SWAP"
    start, end = args.dt.split("/")

    start_dt = datetime.fromisoformat(start).astimezone(DB_TZ)
    if not end:
        end_dt = datetime.now(DB_TZ)
    else:
        end_dt = datetime.fromisoformat(end).astimezone(DB_TZ)

    print(start_dt)
    print(end_dt)

    okex_rest_client = RestClient()

    okex_rest_client.init(REST_HOST, proxy_host="127.0.0.1", proxy_port=1087)

    okex_rest_client.start()

    data = query_history()

    okex_rest_client.stop()

    if data:
        get_database().save_bar_data(data)
        print(len(data))
