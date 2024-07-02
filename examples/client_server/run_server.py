import sys
from time import sleep

from vnpy.event import EventEngine, Event
from vnpy.gateway.okex import OkexGateway
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy.trader.event import EVENT_LOG

from vnpy_rpcservice import RpcServiceApp
from vnpy_rpcservice.rpc_service.engine import EVENT_RPC_LOG
from vnpy.trader.utility import load_json


def main_ui():
    """"""
    qapp = create_qapp()

    event_engine = EventEngine()

    main_engine = MainEngine(event_engine)

    main_engine.add_gateway(OkexGateway)
    main_engine.add_app(RpcServiceApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()


def process_log_event(event: Event):
    """"""
    log = event.data
    msg = f"{log.time}\t{log.msg}"
    print(msg)


def main_terminal(gateway_name: str):
    """"""
    event_engine = EventEngine()
    event_engine.register(EVENT_LOG, process_log_event)
    event_engine.register(EVENT_RPC_LOG, process_log_event)

    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(OkexGateway)
    rpc_engine = main_engine.add_app(RpcServiceApp)

    _filename = f"connect_{gateway_name.lower()}.json"
    _setting = load_json(_filename)
    main_engine.connect(_setting, gateway_name)
    sleep(10)

    rep_address = "tcp://0.0.0.0:2014"
    pub_address = "tcp://0.0.0.0:4102"
    rpc_engine.start(rep_address, pub_address)

    while True:
        sleep(1)


if __name__ == "__main__":
    # Run in GUI mode
    # main_ui()
    try:
        platform = sys.argv[1]
    except IndexError:
        print("platform name is not provide !")
        sys.exit()
    # Run in CLI mode
    main_terminal(platform)
