"""
Gateway for Binance Crypto Exchange.
"""

import urllib
import hashlib
import hmac
import time
from copy import copy
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Dict, List, Tuple

import pytz

from requests.exceptions import SSLError
from vnpy.api.rest import RestClient, Request
from vnpy.api.websocket import WebsocketClient
from vnpy.trader.constant import (
    Direction,
    Exchange,
    Product,
    Status,
    OrderType,
    Interval,
    Offset
)
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    ContractData,
    PositionData,
    BarData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    HistoryRequest, BalanceData
)
from vnpy.trader.event import EVENT_TIMER
from vnpy.event import Event, EventEngine

F_REST_HOST: str = "https://fapi.binance.com"
F_WEBSOCKET_TRADE_HOST: str = "wss://fstream.binance.com/ws/"
F_WEBSOCKET_DATA_HOST: str = "wss://fstream.binance.com/stream?streams="

F_TESTNET_RESTT_HOST: str = "https://testnet.binancefuture.com"
F_TESTNET_WEBSOCKET_TRADE_HOST: str = "wss://stream.binancefuture.com/ws/"
F_TESTNET_WEBSOCKET_DATA_HOST: str = "wss://stream.binancefuture.com/stream?streams="

D_REST_HOST: str = "https://dapi.binance.com"
D_WEBSOCKET_TRADE_HOST: str = "wss://dstream.binance.com/ws/"
D_WEBSOCKET_DATA_HOST: str = "wss://dstream.binance.com/stream?streams="

D_TESTNET_RESTT_HOST: str = "https://testnet.binancefuture.com"
D_TESTNET_WEBSOCKET_TRADE_HOST: str = "wss://dstream.binancefuture.com/ws/"
D_TESTNET_WEBSOCKET_DATA_HOST: str = "wss://dstream.binancefuture.com/stream?streams="

STATUS_BINANCES2VT: Dict[str, Status] = {
    "NEW": Status.NOTTRADED,
    "PARTIALLY_FILLED": Status.PARTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED,
    "REJECTED": Status.REJECTED,
    "EXPIRED": Status.CANCELLED
}

ORDERTYPE_VT2BINANCES: Dict[OrderType, Tuple[str, str]] = {
    OrderType.LIMIT: ("LIMIT", "GTC"),
    OrderType.MARKET: ("MARKET", "GTC"),
    OrderType.FAK: ("LIMIT", "IOC"),
    OrderType.FOK: ("LIMIT", "FOK"),
    OrderType.STOP: ("STOP", "GTC"),
}
ORDERTYPE_BINANCES2VT: Dict[Tuple[str, str], OrderType] = {v: k for k, v in ORDERTYPE_VT2BINANCES.items()}

DIRECTION_VT2BINANCES: Dict[Direction, str] = {
    Direction.LONG: "LONG",
    Direction.SHORT: "SHORT",
    Direction.NET: "BOTH"
}
DIRECTION_BINANCES2VT: Dict[str, Direction] = {v: k for k, v in DIRECTION_VT2BINANCES.items()}

INTERVAL_VT2BINANCES: Dict[Interval, str] = {
    Interval.MINUTE: "1m",
    Interval.MINUTE_15: "15m",
    Interval.HOUR: "1h",
    Interval.HOUR_4: "4h",
    Interval.DAILY: "1d",
}

TIMEDELTA_MAP: Dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}

CHINA_TZ = pytz.timezone("Asia/Shanghai")


class Security(Enum):
    NONE: int = 0
    SIGNED: int = 1
    API_KEY: int = 2


symbol_contract_map: Dict[str, ContractData] = {}


class BinancesGateway(BaseGateway):
    """
    VN Trader Gateway for Binance connection.
    """
    default_name = "BINANCES"
    default_setting = {
        "key": "",
        "secret": "",
        "会话数": 3,
        "服务器": ["TESTNET", "REAL"],
        "合约模式": ["反向", "正向"],
        "代理地址": "",
        "代理端口": 0,
    }

    exchanges: Exchange = [Exchange.BINANCES]

    def __init__(self, event_engine: EventEngine, gateway_name: str = "BINANCES") -> None:
        """Constructor"""
        super().__init__(event_engine, gateway_name)

        self.orders: Dict[str, OrderData] = {}

        self.trade_ws_api = BinancesTradeWebsocketApi(self)
        self.market_ws_api = BinancesDataWebsocketApi(self)
        self.rest_api = BinancesRestApi(self)

    def connect(self, setting: dict) -> None:
        """"""
        key = setting["key"]
        secret = setting["secret"]
        session_number = setting["会话数"]
        server = setting["服务器"]
        proxy_host = setting["代理地址"]
        proxy_port = setting["代理端口"]

        if setting["合约模式"] == "正向":
            usdt_base = True
        else:
            usdt_base = False

        self.rest_api.connect(usdt_base, key, secret, session_number, server,
                              proxy_host, proxy_port)
        self.market_ws_api.connect(usdt_base, proxy_host, proxy_port, server)

        self.event_engine.register(EVENT_TIMER, self.process_timer_event)

    def subscribe(self, req: SubscribeRequest) -> None:
        """"""
        self.market_ws_api.subscribe(req)
        self.rest_api.set_margin_type(req.symbol)
        self.rest_api.set_leverage(req.symbol)

    def send_order(self, req: OrderRequest) -> str:
        """"""
        return self.rest_api.send_order(req)

    def cancel_order(self, req: CancelRequest) -> Request:
        """"""
        self.rest_api.cancel_order(req)

    def query_account(self) -> None:
        """"""
        pass

    def query_position(self) -> None:
        """"""
        pass

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """"""
        return self.rest_api.query_history(req)

    def close(self) -> None:
        """"""
        self.rest_api.stop()
        self.trade_ws_api.stop()
        self.market_ws_api.stop()

    def process_timer_event(self, event: Event) -> None:
        """"""
        if self.rest_api.user_stream_key:
            self.rest_api.keep_user_stream()
        else:
            self.rest_api.start_user_stream()

    def on_order(self, order: OrderData) -> None:
        """"""
        self.orders[order.orderid] = copy(order)
        super().on_order(order)

    def get_order(self, orderid: str) -> OrderData:
        """"""
        return self.orders.get(orderid, None)


class BinancesRestApi(RestClient):
    """
    BINANCE REST API
    """

    def __init__(self, gateway: BinancesGateway):
        """"""
        super().__init__()

        self.gateway: BinancesGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.trade_ws_api: BinancesTradeWebsocketApi = self.gateway.trade_ws_api

        self.key: str = ""
        self.secret: str = ""

        self.user_stream_key: str = ""
        self.keep_alive_count: int = 0
        self.recv_window: int = 5000
        self.time_offset: int = 0

        self.order_count: int = 1_000_000
        self.order_count_lock: Lock = Lock()
        self.connect_time: int = 0
        self.usdt_base: bool = False

    def sign(self, request: Request) -> Request:
        """
        Generate BINANCE signature.
        """
        security = request.data["security"]
        if security == Security.NONE:
            request.data = None
            return request

        if request.params:
            path = request.path + "?" + urllib.parse.urlencode(request.params)
        else:
            request.params = dict()
            path = request.path

        if security == Security.SIGNED:
            timestamp = int(time.time() * 1000)

            if self.time_offset > 0:
                timestamp -= abs(self.time_offset)
            elif self.time_offset < 0:
                timestamp += abs(self.time_offset)

            request.params["timestamp"] = timestamp

            query = urllib.parse.urlencode(sorted(request.params.items()))
            signature = hmac.new(self.secret, query.encode(
                "utf-8"), hashlib.sha256).hexdigest()

            query += "&signature={}".format(signature)
            path = request.path + "?" + query

        request.path = path
        request.params = {}
        request.data = {}

        # Add headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-MBX-APIKEY": self.key,
            "Connection": "close"
        }

        if security in [Security.SIGNED, Security.API_KEY]:
            request.headers = headers

        return request

    def connect(
        self,
        usdt_base: bool,
        key: str,
        secret: str,
        session_number: int,
        server: str,
        proxy_host: str,
        proxy_port: int
    ) -> None:
        """
        Initialize connection to REST server.
        """
        self.usdt_base = usdt_base
        self.key = key
        self.secret = secret.encode()
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host
        self.server = server

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        if self.server == "REAL":
            if self.usdt_base:
                self.init(F_REST_HOST, proxy_host, proxy_port)
            else:
                self.init(D_REST_HOST, proxy_host, proxy_port)
        else:
            if self.usdt_base:
                self.init(F_TESTNET_RESTT_HOST, proxy_host, proxy_port)
            else:
                self.init(D_TESTNET_RESTT_HOST, proxy_host, proxy_port)

        self.start(session_number)

        self.gateway.write_log("REST API启动成功")

        self.query_time()
        self.query_account()
        self.query_position()
        self.query_order()
        self.query_contract()

    def query_time(self) -> Request:
        """"""
        data = {
            "security": Security.NONE
        }

        if self.usdt_base:
            path = "/fapi/v1/time"
        else:
            path = "/dapi/v1/time"

        return self.add_request(
            "GET",
            path,
            callback=self.on_query_time,
            data=data
        )

    def query_account(self):
        """"""
        data = {"security": Security.SIGNED}

        if self.usdt_base:
            path = "/fapi/v2/balance"
        else:
            path = "/dapi/v2/balance"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_account,
            data=data
        )

    def query_position(self):
        """"""
        data = {"security": Security.SIGNED}

        if self.usdt_base:
            path = "/fapi/v2/positionRisk"
        else:
            path = "/dapi/v2/positionRisk"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_position,
            data=data
        )

    def query_order(self):
        """"""
        data = {"security": Security.SIGNED}

        if self.usdt_base:
            path = "/fapi/v1/openOrders"
        else:
            path = "/dapi/v1/openOrders"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_order,
            data=data
        )

    def query_contract(self) -> Request:
        """"""
        data = {
            "security": Security.NONE
        }

        if self.usdt_base:
            path = "/fapi/v1/exchangeInfo"
        else:
            path = "/dapi/v1/exchangeInfo"

        self.add_request(
            method="GET",
            path=path,
            callback=self.on_query_contract,
            data=data
        )

    def _new_order_id(self) -> int:
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def set_leverage(self, symbol: str):
        if self.usdt_base:
            path = "/fapi/v1/leverage"
        else:
            path = "/dapi/v1/leverage"

        data = {"security": Security.SIGNED}

        params = {
            "symbol": symbol,
            "leverage": 6
        }

        self.add_request(
            method="POST",
            path=path,
            callback=self.on_set_leverage_type,
            data=data,
            params=params
        )

    def set_margin_type(self, symbol: str):
        if self.usdt_base:
            path = "/fapi/v1/marginType"
        else:
            path = "/dapi/v1/marginType"

        data = {"security": Security.SIGNED}

        params = {
            "symbol": symbol,
            "marginType": "CROSSED"
        }

        self.add_request(
            method="POST",
            path=path,
            callback=self.on_set_margin_type,
            data=data,
            params=params
        )

    def send_order(self, req: OrderRequest) -> str:
        """"""
        orderid = "328hhn6c-" + str(self.connect_time + self._new_order_id())
        order = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        data = {
            "security": Security.SIGNED
        }

        order_type, time_condition = ORDERTYPE_VT2BINANCES[req.type]

        if req.offset == Offset.OPEN:
            if req.direction == Direction.LONG:
                pos_side = "LONG"
                side = "BUY"
            else:
                pos_side = "SHORT"
                side = "SELL"
        else:
            if req.direction == Direction.LONG:
                pos_side = "SHORT"
                side = "BUY"
            else:
                pos_side = "LONG"
                side = "SELL"

        params = {
            "symbol": req.symbol,
            "side": side,
            "positionSide": pos_side,
            "type": order_type,
            "quantity": float(req.volume),
            "newClientOrderId": orderid,
        }

        if req.type == OrderType.LIMIT:
            params["price"] = float(req.price)
            params["timeInForce"] = time_condition

        if self.usdt_base:
            path = "/fapi/v1/order"
        else:
            path = "/dapi/v1/order"

        self.add_request(
            method="POST",
            path=path,
            callback=self.on_send_order,
            data=data,
            params=params,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        return order.vt_orderid

    def cancel_order(self, req: CancelRequest) -> Request:
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "origClientOrderId": req.orderid
        }

        if self.usdt_base:
            path = "/fapi/v1/order"
        else:
            path = "/dapi/v1/order"

        order: OrderData = self.gateway.get_order(req.orderid)

        self.add_request(
            method="DELETE",
            path=path,
            callback=self.on_cancel_order,
            params=params,
            data=data,
            on_failed=self.on_cancel_failed,
            extra=order
        )

    def start_user_stream(self) -> Request:
        """"""
        data = {
            "security": Security.API_KEY
        }

        if self.usdt_base:
            path = "/fapi/v1/listenKey"
        else:
            path = "/dapi/v1/listenKey"

        self.add_request(
            method="POST",
            path=path,
            callback=self.on_start_user_stream,
            data=data
        )

    def keep_user_stream(self):
        """"""
        self.keep_alive_count += 1
        if self.keep_alive_count < 1800:
            return
        self.keep_alive_count = 0

        data = {
            "security": Security.API_KEY
        }

        params = {
            "listenKey": self.user_stream_key
        }

        if self.usdt_base:
            path = "/fapi/v1/listenKey"
        else:
            path = "/dapi/v1/listenKey"

        self.add_request(
            method="PUT",
            path=path,
            callback=self.on_keep_user_stream,
            params=params,
            data=data,
            on_error=self.on_keep_user_stream_error
        )

    def delete_user_stream(self):
        data = {
            "security": Security.API_KEY
        }

        params = {
            "listenKey": self.user_stream_key
        }

        if self.usdt_base:
            path = "/fapi/v1/listenKey"
        else:
            path = "/dapi/v1/listenKey"

        self.add_request(
            method="DELETE",
            path=path,
            callback=self.on_delete_user_stream,
            params=params,
            data=data
        )

    def on_query_time(self, data: dict, request: Request) -> None:
        """"""
        local_time = int(time.time() * 1000)
        server_time = int(data["serverTime"])
        self.time_offset = local_time - server_time

    def on_query_account(self, data: dict, request: Request) -> None:
        """"""
        for asset in data:
            account = AccountData(
                accountid=asset["asset"],
                balance=float(asset["balance"]),
                available=float(asset["availableBalance"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("账户资金查询成功")

    def on_query_position(self, data: dict, request: Request) -> None:
        """"""
        for d in data:
            ps = d["positionSide"]
            pa = d["positionAmt"]
            position = PositionData(
                symbol=d["symbol"],
                exchange=Exchange.BINANCES,
                direction=DIRECTION_BINANCES2VT[ps],
                volume=float(pa),
                price=float(d["entryPrice"]),
                pnl_unreal=float(d["unRealizedProfit"]),
                liq_px=float(d["liquidationPrice"]),
                lever=float(d["leverage"]),
                gateway_name=self.gateway_name,
            )
            self.gateway.on_position(position)
        self.gateway.write_log("持仓信息查询成功")

    def on_query_order(self, data: dict, request: Request) -> None:
        """"""
        for d in data:
            time_f = d["timeInForce"] if d["timeInForce"] else ""
            key = (d["type"], time_f)
            order_type = ORDERTYPE_BINANCES2VT.get(key, None)
            if not order_type:
                continue

            pos_side = d["positionSide"]
            order_side = d["side"]

            if pos_side == 'BOTH':
                order_offset = Offset.NONE
                pos_side = Direction.NET
            elif pos_side == 'LONG' and order_side == "BUY":
                order_offset = Offset.OPEN
                pos_side = Direction.LONG
            elif pos_side == 'SHORT' and order_side == "SELL":
                order_offset = Offset.OPEN
                pos_side = Direction.SHORT
            elif pos_side == 'LONG' and order_side == "SELL":
                order_offset = Offset.CLOSE
                pos_side = Direction.SHORT
            else:
                order_offset = Offset.CLOSE
                pos_side = Direction.LONG

            order = OrderData(
                orderid=d["clientOrderId"],
                symbol=d["symbol"],
                exchange=Exchange.BINANCES,
                price=float(d["price"]),
                trade_avg_price=float(d["avgPrice"]),
                volume=float(d["origQty"]),
                type=order_type,
                direction=pos_side,
                offset=order_offset,
                traded=float(d["executedQty"]),
                status=STATUS_BINANCES2VT.get(d["status"], None),
                datetime=generate_datetime(d["time"]),
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("委托信息查询成功")

    def on_query_contract(self, data: dict, request: Request) -> None:
        """"""
        for d in data["symbols"]:
            base_currency = d["baseAsset"]
            quote_currency = d["quoteAsset"]
            name = f"{base_currency.upper()}/{quote_currency.upper()}"

            pricetick = 1
            min_volume = 1
            step_volume = 1
            limit_max_qty = 0
            market_max_qty = 0

            for f in d["filters"]:
                if f["filterType"] == "PRICE_FILTER":
                    pricetick = float(f["tickSize"])
                elif f["filterType"] == "LOT_SIZE":
                    min_volume = float(f["minQty"])
                    step_volume = float(f["stepSize"])
                    limit_max_qty = float(f["maxQty"])
                elif f["filterType"] == "MARKET_LOT_SIZE":
                    market_max_qty = float(f["maxQty"])

            contract = ContractData(
                symbol=d["symbol"],
                exchange=Exchange.BINANCES,
                name=name,
                pricetick=pricetick,
                size=1,
                min_volume=min_volume,
                step_volume= step_volume,
                maxLmt_vol= limit_max_qty,
                maxMkt_vol= market_max_qty,
                product=Product.FUTURES,
                net_position=False,
                history_data=True,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

            symbol_contract_map[contract.symbol] = contract

        self.gateway.write_log("合约信息查询成功")

    def on_send_order(self, data: dict, request: Request) -> None:
        """"""
        pass

    def on_send_order_failed(self, status_code: int, request: Request) -> None:
        """
        Callback when sending order failed on server.
        """
        order:OrderData = request.extra
        order.status = Status.REJECTED
        text = eval(request.response.text)
        order.err_code = text['code']
        self.gateway.on_order(order)

        msg = f"委托失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ) -> None:
        """
        Callback when sending order caused exception.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        if not issubclass(exception_type, (ConnectionError, SSLError)):
            self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order(self, data: dict, request: Request) -> None:
        """"""
        pass

    def on_cancel_failed(self, status_code: str, request: Request) -> None:
        """"""
        # if request.extra:
        #     order = request.extra
        #     order.status = Status.REJECTED
        #     text = eval(request.response.text)
        #     order.err_code = text['code']
        #     self.gateway.on_order(order)

        msg = f"撤单失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def on_start_user_stream(self, data: dict, request: Request) -> None:
        """"""
        self.user_stream_key = data["listenKey"]
        self.keep_alive_count = 0

        if self.server == "REAL":
            url = F_WEBSOCKET_TRADE_HOST + self.user_stream_key
            if not self.usdt_base:
                url = D_WEBSOCKET_TRADE_HOST + self.user_stream_key
        else:
            url = F_TESTNET_WEBSOCKET_TRADE_HOST + self.user_stream_key
            if not self.usdt_base:
                url = D_TESTNET_WEBSOCKET_TRADE_HOST + self.user_stream_key

        self.trade_ws_api.connect(url, self.proxy_host, self.proxy_port)
        self.gateway.write_log("on_start_user_stream")

    def on_set_dual_side_position(self, data: dict, request: Request) -> None:
        if data["code"] == 200:
            self.gateway.write_log("set_dualSidePosition sucess")

    def on_set_margin_type(self, data: dict, request: Request) -> None:
        if data["code"] == 200:
            self.gateway.write_log("on_set_margin_type sucess")

    def on_set_leverage_type(self, data: dict, request: Request) -> None:
        self.gateway.write_log(data)

    def on_keep_user_stream(self, data: dict, request: Request) -> None:
        """"""
        pass

    def on_delete_user_stream(self, data: dict, request: Request) -> None:
        """"""
        self.gateway.write_log("on_delete_user_stream")

    def on_keep_user_stream_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ) -> None:
        """
        Callback when sending order caused exception.
        """
        # Ignore timeout error when trying to keep user stream
        if not issubclass(exception_type, TimeoutError):
            self.on_error(exception_type, exception_value, tb, request)

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """"""
        history = []
        limit = 1500
        if req.start :
            start_time = int(datetime.timestamp(req.start))
        else:
            start_time = datetime.now()
        if req.end:
            end_time = int(datetime.timestamp(req.end))
        else:
            end_time = datetime.now()

        # Create query params
        params = {
            "symbol": req.symbol,
            "interval": INTERVAL_VT2BINANCES[req.interval],
            "limit": limit
        }

        if self.usdt_base:
            path = "/fapi/v1/klines"
        else:
            path = "/dapi/v1/klines"

        while True:

            params["startTime"] = start_time * 1000
            params["endTime"] = end_time * 1000

            try:
                resp = self.request(
                    "GET",
                    path=path,
                    data={"security": Security.NONE},
                    params=params
                )
            except BaseException as e:
                msg = repr(e)
                print(msg)
                break

            # Break if request failed with other status code
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data = resp.json()
                if not data:
                    msg = f"获取历史数据为空，开始时间：{start_time}"
                    self.gateway.write_log(msg)
                    break

                buf = []

                for l in data:
                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=generate_datetime(l[0]),
                        interval=req.interval,
                        volume=float(l[5]),
                        open_price=float(l[1]),
                        high_price=float(l[2]),
                        low_price=float(l[3]),
                        close_price=float(l[4]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                begin = buf[0].datetime
                end = buf[-1].datetime

                if not self.usdt_base:
                    buf = list(reversed(buf))
                history.extend(buf)
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # Break if total data count less than limit (latest date collected)
                if len(data) < limit:
                    break

                # Update start time
                if self.usdt_base:
                    start_dt = buf[-1].datetime + TIMEDELTA_MAP[req.interval]
                    start_time = int(datetime.timestamp(start_dt))
                # Update end time
                else:
                    end_dt = begin - TIMEDELTA_MAP[req.interval]
                    end_time = int(datetime.timestamp(end_dt))

        if not self.usdt_base:
            history = list(reversed(history))
        history.pop()
        return history


class BinancesTradeWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway: BinancesGateway):
        """"""
        super().__init__()

        self.gateway: BinancesGateway = gateway
        self.gateway_name: str = gateway.gateway_name

    def connect(self, url: str, proxy_host: str, proxy_port: int) -> None:
        """"""
        self.init(url, proxy_host, proxy_port)
        self.start()

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("交易Websocket API连接成功")

    def on_packet(self, packet: dict) -> None:  # type: (dict)->None
        """"""
        if packet["e"] == "ACCOUNT_UPDATE":
            self.on_account(packet)
        elif packet["e"] == "ORDER_TRADE_UPDATE":
            self.on_order(packet)
        elif packet["e"] == "listenKeyExpired":
            self.on_listen_key_expired(packet)

    def on_listen_key_expired(self, packet: dict) -> None:
        self.gateway.write_log("on_listen_key_expired")
        self.gateway.rest_api.user_stream_key = ""
        self.stop()

    def on_account(self, packet: dict) -> None:
        """"""
        event_type = packet["a"]["m"]
        for acc_data in packet["a"]["B"]:
            account = AccountData(
                accountid=acc_data["a"],
                balance=float(acc_data["wb"]),
                frozen=float(acc_data["wb"]) - float(acc_data["cw"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

            balance: BalanceData = BalanceData(
                ccy=acc_data["a"],
                cash_bal=float(acc_data["wb"]),
                bal_change=float(acc_data["bc"]),
                eventType=event_type,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_balance(balance)

        for pos_data in packet["a"]["P"]:
            ps = pos_data["ps"]
            pa = pos_data["pa"]
            if ps != "BOTH":
                position = PositionData(
                    symbol=pos_data["s"],
                    exchange=Exchange.BINANCES,
                    direction=DIRECTION_BINANCES2VT[ps],
                    volume=float(pa),
                    price=float(pos_data["ep"]),
                    pnl=float(pos_data["cr"]),
                    pnl_unreal=float(pos_data["up"]),
                    gateway_name=self.gateway_name,
                )
                self.gateway.on_position(position)

    def on_order(self, packet: dict) -> None:
        """"""
        order_data = packet["o"]
        key = (order_data["o"], order_data["f"])
        order_type = ORDERTYPE_BINANCES2VT.get(key, None)
        if not order_type:
            return

        pos_side = order_data["ps"]
        order_side = order_data["S"]

        if pos_side == 'BOTH':
            order_offset = Offset.NONE
            pos_side = Direction.NET
        elif pos_side == 'LONG' and order_side == "BUY":
            order_offset = Offset.OPEN
            pos_side = Direction.LONG
        elif pos_side == 'SHORT' and order_side == "SELL":
            order_offset = Offset.OPEN
            pos_side = Direction.SHORT
        elif pos_side == 'LONG' and order_side == "SELL":
            order_offset = Offset.CLOSE
            pos_side = Direction.SHORT
        else:
            order_offset = Offset.CLOSE
            pos_side = Direction.LONG

        order = OrderData(
            symbol=order_data["s"],
            exchange=Exchange.BINANCES,
            orderid=str(order_data["c"]),
            type=order_type,
            direction=pos_side,
            offset= order_offset,
            price=float(order_data["p"]),
            trade_avg_price=float(order_data["ap"]),
            volume=float(order_data["q"]),
            traded=float(order_data["z"]),
            status=STATUS_BINANCES2VT[order_data["X"]],
            datetime=generate_datetime(order_data["T"]),
            gateway_name=self.gateway_name
        )
        self.gateway.on_order(order)

        # Round trade volume to minimum trading volume
        trade_volume = float(order_data["l"])

        # contract: ContractData = symbol_contract_map.get(order.symbol, None)
        # if contract:
        #     trade_volume = round_to(trade_volume, contract.step_volume)

        if not trade_volume:
            return

        # Push trade event
        trade = TradeData(
            symbol=order.symbol,
            exchange=order.exchange,
            orderid=order.orderid,
            tradeid=order_data["t"],
            direction=order.direction,
            offset=order_offset,
            price=float(order_data["L"]),
            volume=trade_volume,
            datetime=generate_datetime(order_data["T"]),
            fee=-get_float_value(order_data, "n"),
            profit=get_float_value(order_data, "rp"),
            gateway_name=self.gateway_name,
        )
        self.gateway.on_trade(trade)


class BinancesDataWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway: BinancesGateway):
        """"""
        super().__init__()

        self.gateway: BinancesGateway = gateway
        self.gateway_name: str = gateway.gateway_name

        self.ticks: Dict[str, TickData] = {}
        self.bars: Dict[str, BarData] = {}
        self.usdt_base = False
        self.host = None
        self.proxy_host = None
        self.proxy_port = None

    def connect(
        self,
        usdt_base: bool,
        proxy_host: str,
        proxy_port: int,
        server: str
    ) -> None:
        """"""
        self.usdt_base = usdt_base

        if server == "REAL":
            url = F_WEBSOCKET_DATA_HOST
            if not self.usdt_base:
                url = D_WEBSOCKET_DATA_HOST
        else:
            url = F_TESTNET_WEBSOCKET_DATA_HOST
            if not self.usdt_base:
                url = D_TESTNET_WEBSOCKET_DATA_HOST

        self.host = url
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def on_connected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API连接刷新")

    def on_disconnected(self) -> None:
        """"""
        self.gateway.write_log("行情Websocket API断开成功")

    def subscribe(self, req: SubscribeRequest) -> None:
        """"""
        if req.symbol not in symbol_contract_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}")
            return

        # Create tick buf data
        tick = TickData(
            symbol=req.symbol,
            name=symbol_contract_map[req.symbol].name,
            exchange=Exchange.BINANCES,
            datetime=datetime.now(CHINA_TZ),
            gateway_name=self.gateway_name,
        )
        self.ticks[req.symbol.lower()] = tick
        # Create bar buf data
        bar = BarData(
            symbol=req.symbol,
            exchange=Exchange.BINANCES,
            datetime=datetime.now(CHINA_TZ),
            gateway_name=self.gateway_name,
            interval=Interval.MINUTE
        )
        self.bars[req.symbol.lower()] = bar

        # Close previous connection
        if self._active:
            self.stop()
            self.join()

        # Create new connection
        channels = []
        for ws_symbol in self.ticks.keys():
            channels.append(ws_symbol + "@ticker")
            channels.append(ws_symbol + "@depth5")
            channels.append(ws_symbol + "_perpetual" + "@continuousKline" + "_1m")

        url = self.host + "/".join(channels)
        self.init(url, self.proxy_host, self.proxy_port)
        self.start()

    def on_packet(self, packet: dict) -> None:
        """"""
        stream = packet["stream"]
        data = packet["data"]

        symbol, channel = stream.split("@")

        if channel == "ticker":
            tick = self.ticks[symbol]
            tick.volume = float(data['v'])
            tick.open_price = float(data['o'])
            tick.high_price = float(data['h'])
            tick.low_price = float(data['l'])
            tick.last_price = float(data['c'])
            tick.datetime = generate_datetime(float(data['E']))
            self.gateway.on_tick(copy(tick))
        elif channel == "depth5":
            tick = self.ticks[symbol]
            bids = data["b"]
            for n in range(min(5, len(bids))):
                price, volume = bids[n]
                tick.__setattr__("bid_price_" + str(n + 1), float(price))
                tick.__setattr__("bid_volume_" + str(n + 1), float(volume))

            asks = data["a"]
            for n in range(min(5, len(asks))):
                price, volume = asks[n]
                tick.__setattr__("ask_price_" + str(n + 1), float(price))
                tick.__setattr__("ask_volume_" + str(n + 1), float(volume))
            if tick.last_price:
                self.gateway.on_tick(copy(tick))
        elif channel == "continuousKline_1m":
            symbol, _type = symbol.split("_")
            bar = self.bars[symbol]
            _k = data["k"]
            bar.datetime = generate_datetime(float(_k['t']))
            bar.volume = float(_k['v'])
            bar.open_price = float(_k['o'])
            bar.high_price = float(_k['h'])
            bar.low_price = float(_k['l'])
            bar.close_price = float(_k['c'])
            if _k['x']:
                self.gateway.on_bar(copy(bar))


def generate_datetime(timestamp: float) -> datetime:
    """"""
    dt = datetime.fromtimestamp(timestamp / 1000)
    dt = CHINA_TZ.localize(dt)
    return dt

def get_float_value(data: dict, key: str) -> float:
    """获取字典中对应键的浮点数值"""
    data_str = data.get(key, "")
    if not data_str:
        return 0.0
    return float(data_str)

