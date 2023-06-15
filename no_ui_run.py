# -*- coding: UTF-8 -*-
import multiprocessing
import os
import signal
import sys
from time import sleep
from datetime import datetime, time
from logging import INFO

from vnpy.event import EventEngine
from vnpy.trader.setting import SETTINGS
from vnpy.trader.engine import MainEngine
from vnpy.gateway.okex import OkexGateway
from vnpy.gateway.binances import BinancesGateway

from vnpy.app.cta_strategy import CtaStrategyApp, CtaEngine
from vnpy.app.cta_strategy.base import EVENT_CTA_LOG
from vnpy.trader.utility import load_json

SETTINGS["log.active"] = True
SETTINGS["log.level"] = INFO
SETTINGS["log.console"] = True


def run_child(gateway_name: str):
    """
    Running in the child process.
    """
    SETTINGS["log.file"] = True

    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    cta_engine: CtaEngine = main_engine.add_app(CtaStrategyApp)
    main_engine.write_log("主引擎创建成功")

    log_engine = main_engine.get_engine("log")
    event_engine.register(EVENT_CTA_LOG, log_engine.process_log_event)
    main_engine.write_log("注册日志事件监听")

    main_engine.add_gateway(OkexGateway)
    main_engine.add_gateway(BinancesGateway)
    _filename = f"connect_{gateway_name.lower()}.json"
    _setting = load_json(_filename)

    main_engine.connect(_setting, gateway_name)
    main_engine.write_log(f"连接{gateway_name}接口")

    sleep(5)

    cta_engine.init_engine()
    main_engine.write_log("CT引擎初始化完成")

    cta_engine.init_all_strategies()
    sleep(5)  # Leave enough time to complete strategy initialization
    main_engine.write_log("CTA策略全部初始化")

    cta_engine.start_all_strategies()
    main_engine.write_log("CTA策略全部启动")

    def keyboard_interrupt(s, f):
        print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(s))
        main_engine.close()
        event_engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, keyboard_interrupt)
    while True:
        sleep(10)


def run_parent():
    """
    Running in the parent process.
    """
    print("启动CTA策略守护父进程")

    child_process = None

    while True:
        # Start child process in trading period
        if child_process is None:
            print("启动子进程")
            child_process = multiprocessing.Process(target=run_child)
            child_process.start()
            print("子进程启动成功")

        sleep(5)


if __name__ == "__main__":
    try:
        platform = sys.argv[1]
    except IndexError:
        platform = "OKEX"

    if platform.startswith("o"):
        platform = "OKEX"
    elif platform.startswith("b"):
        platform = "BINANCES"

    platform = platform.upper()
    run_child(platform)
