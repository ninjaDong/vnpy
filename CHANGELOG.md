# 3.9.1版本

## 新增

1. 增加i18n国际化支持，以及对应的英文翻译
2. 增加CFD和SWAP品种类型枚举值
3. vnpy_ib增加COMEX、Eurex交易所支持
4. vnpy_ib增加CFD品种支持

## 调整

1. vnpy_rqdata完善对于周五夜盘数据查询的支持
2. vnpy_ib订阅行情和委托下单时，检查代码字符串是否包含空格
3. vnpy_ib解析合约对象时，增加对于ConId是否包含非数字字符的检查
4. vnpy_ib查询历史K线数据，支持更长时间段跨度（不再限制半年）
5. vnpy_da更新API版本到1.18.2.0
6. vnpy_da移除历史数据查询功能
7. vnpy_tora调整期权接口的委托号生成规则，支持上限10万数量委托
8. vnpy_xtp调整账户冻结资金的计算逻辑
9. vnpy_optionmaster增加对IB的股票期权品种支持
10. vnpy_optionmaster定价模型改为计算理论希腊值
11. vnpy_optionmaster调整对象希腊值为理论模式
12. vnpy_optionmaster调整中值隐波动的计算方法
13. vnpy_spreadtrading使用线程池实现策略初始化的异步执行
14. vnpy_postgresql支持自动重用已经打开的数据库连接
15. vnpy_ctptest更新API版本至6.7.2
16. 接口封装升级更新pybind11到2.11.1版本：vnpy_ctptest、vnpy_sopttest
17. vnpy_ctp更新API版本到6.7.2
18. 调整extract_vt_symbol函数，兼容代码中带有"."的情况，如HHI.HK-HKD-FUT.HKFE
19. 更新vnpy框架的核心依赖模块到2024年较新的版本

## 修复

1. 修复vnpy_portfoliostrategy调用stop_strategy没有撤销活动委托的问题
2. 修复vnpy_xtp的API封装中queryTickersPriceInfo底层调用错误
3. 修复RpcClient中_last_received_ping变量的类型问题


# 3.9.0版本

## 新增

1. 迅投研数据服务vnpy_xt，支持股票、期货、期权、债券、基金历史数据获取
2. vnpy_ib增加对CBOE和CBOT交易所的支持、对指数期权的支持
3. vnpy_rqdata增加对于88A2连续次主力合约的支持
4. vnpy_wind增加广期所和上期能源交易所的数据支持

## 调整

1. vnpy_sopt升级3.7.0版本API
2. vnpy_portfoliostrategy回测引擎支持交易日参数annual_days
3. K线合成器（BarGenerator）移除对于Tick时间戳的检查过滤逻辑，交由用户层负责控制过滤
4. vnpy_ib收到期权合约数据后，自动查询其切片行情数据
5. vnpy_paperaccount实现对于IB接口合约的特殊路由处理
6. 接口封装升级更新pybind11到2.11.1版本：vnpy_ctp、vnpy_sopt、vnpy_tora
7. vnpy_ctp过滤不支持的委托状态推送
8. vnpy_mysql兼容无数据库写入权限情况下的数据表初始化
9. vnpy_chartwizard支持关闭单个图表标签页
10. vnpy_portfoliostrategy移除策略后同时清除对应的策略状态缓存数据
11. vnpy_portfoliostrategy调整每日盈亏清算对象开盘持仓数据的初始化方式
12. 策略模块遗传优化函数增加ngen_size和max_workers参数


## 修复

1. 修复vnpy_tora接口中的委托部分撤单状态映射缺失
2. 修复vnpy_wind查询日线历史数据时数值存在NaN的问题
3. 修复vnpy_mongodb的Tick汇总数据的条数统计错误
4. 修复vnpy_chartwizard对于升级后的vnpy_spreadtrading价差行情显示问题
5. 修复vnpy_ctastrategy回测成交记录为空时的报错
6. 修复vnpy_ctastrategy策略初始化时，历史数据重复推送调用on_bar的问题


# 3.8.0版本

## 新增

1. K线合成器（BarGenerator）增加对日K线的合成支持
2. 基于华鑫奇点柜台的C++ API重构vnpy_tora，实现VeighNa Station加载支持
3. 新增vnpy_ib对于期权合约查询、波动率和希腊值等扩展行情数据的支持

## 调整

1. vnpy_rest/vnpy_websocket限制在Windows上改为必须使用Selector事件循环
2. vnpy_rest/vnpy_websocket客户端关闭时确保所有会话结束，并等待有异步任务完成后安全退出
3. vnpy_ctp升级6.6.9版本API
4. vnpy_ctp支持大商所的1毫秒级别行情时间戳
5. vnpy_tqsdk过滤不支持的K线频率查询并输出日志
6. vnpy_datamanager增加数据频率下按交易所显示支持，优化数据加载显示速度
7. vnpy_ctabacktester如果加载的历史数据为空，则不执行后续回测
8. vnpy_spreadtrading采用轻量级数据结构，优化图形界面更新机制
9. vnpy_spreadtrading价差子引擎之间的事件推送，不再经过事件引擎，降低延迟水平
10. vnpy_rpcservice增加对下单返回委托号的gateway_name替换处理
11. vnpy_portfoliostrategy策略模板增加引擎类型查询函数get_engine_type
12. vnpy_sec更新行情API至1.6.45.0版本，更新交易API版本至1.6.88.18版本
13. vnpy_ib更新10.19.1版本的API，恢复对于数字格式代码（ConId）的支持
14. 没有配置数据服务或者加载模块失败的情况下，使用BaseDatafeed作为数据服务
15. 遗传优化算法运行时，子进程指定使用spawn方式启动，避免数据库连接对象异常
16. 合约管理控件，增加对于期权合约的特有数据字段显示

## 修复

1. 修复vnpy_datarecorder对于新版本vnpy_spreadtrading价差数据的录制支持
2. 修复vnpy_algotrading条件委托算法StopAlgo全部成交后状态更新可能缺失的问题
3. 修复vnpy_ctastrategy策略初始化时，历史数据重复推送调用on_bar的问题
4. 修复vnpy_wind查询日线历史数据时，数值存在NaN的问题


# 3.7.0版本

## 新增

1. 新增沪股通和深股通交易所枚举值
2. 增加vnpy_tap对于Linux系统的支持
3. 增加vnpy_rqdata对于新型主力合约数据支持（切换前一日收盘价比例复权）

## 调整

1. vnpy_ctastrategy/vnpy_ctabacktester加载策略类时，过滤TargetPosTemplate模板
2. vnpy_ctp连接登录过程中，只有在授权码错误的情况下，才禁止再次发起认证
3. vnpy_uft增加对广期所GFEX的支持
4. vnpy_tqsdk增加对于output日志输出功能的支持
5. vnpy_dolphindb允许指定用户自行配置具体的数据库实例
6. vnpy_rqdata优化对于郑商所期货和期权合约的查询代码转换规则
7. vnpy_rqdata增加对广期所GFEX的支持
8. vnpy_portfoliostrategy增加回测爆仓检查
9. vnpy_portfoliostrategy策略模板增加合约乘数查询函数get_size
10. vnpy_portfoliostrategy回测加载日线和小时线数据时，不使用分段加载

## 修复

1. 修复vnpy_rpcservice中，RPC接口对于推送数据的vt前缀相关字段错误问题
2. 修复vnpy_mini中，对于INE交易所今昨仓位的特殊处理
3. 修复vnpy_datamanager中，批量数据更新时缺失output函数的问题
4. 修复vnpy_spreadtrading中，回测加载数据时优先从数据服务获取历史数据的问题，改为优先从本地数据库加载


# 3.6.0版本

## 新增

1. 新增vnpy_ctp的Mac系统支持（M1/M2）

## 调整

1. BaseDatafeed的相关功能函数增加output入参用于输出日志
2. 修改相关数据服务模块适配output参数：vnpy_rqdata/vnpy_ifind/vnpy_wind/vnpy_tushare
3. 修改相关策略应用模块适配output参数：vnpy_ctastrategy/vnpy_ctabacktester/vnpy_portfoliostrategy/vnpy_spreadtrading/vnpy_datamanager
3. OffsetConverter增加对于SHFE/INE合约的锁仓模式支持
4. 在OmsEngine中添加全局的OffsetConverter功能，不再需要各AppEngine自行维护
5. 添加CTA策略模块在执行参数优化时的最大进程数量限制参数：vnpy_ctastrategy/vnpy_ctabacktester
6. 增加穷举优化算法运行过程中基于tqdm的进度条输出
7. 增加遗传优化算法运行过程中的迭代次数进度输出
8. 增加vnpy_optionmaster模块的期权产品对应标的合约的匹配函数，不再限制产品范围
9.  升级vnpy_tts的dll链接库，解决openctp升级导致的资金不显示的问题
10. 修改vnpy_ctastrategy使用vnpy.trader.database中统一定义的时区来加载数据
11. 增加vnpy_ctastrategy策略模板的合约乘数查询函数get_size
12. 增加vnpy_spreadtrading回测中统计绩效时对于爆仓情况的检查
13. 增加vnpy_scripttrader基于vt_symbol和direction查询持仓数据的函数
14. 修改vt_positionid的字符串内容，增加gateway_name前缀标识

## 修复

1. 修复异常捕捉钩子threading_excepthook的参数错误问题
2. 修复vnpy_ib获取历史数据时的异常失败问题
3. 修复vnpy_rest/vnpy_websocket中aiohttp的代理参数proxy传空时必须为None的问题
4. 修复vnpy_optionmaster模块的Greeks监控表行数设置不足的问题
5. 修复vnpy_rqdata查询股票期权数据报错的问题
6. 修复vnpy_rqdata中RqdataGateway获取期货指数和连续合约信息时错误的问题
7. 修复vnpy_portfoliostrategy中，从缓存文件恢复数据，导致defaultdict变成dict的问题


# 3.5.0版本

## 新增

1. 新增基于米筐RQData的跨市场行情数据接口RqdataGateway
2. 新增东方财富证券EMT柜台交易接口vnpy_emt

## 调整

1. 调整vnpy_algotrading模块设计（模板、引擎），只支持单合约算法执行交易
2. 优化vnpy_algotrading的算法状态控制，增加状态枚举值，算法支持暂停和恢复运行
3. 升级vnpy_hft接口支持HFT国君统一交易网关的2.0版本API
4. 优化vnpy_portfoliostrategy的策略模板，支持持仓目标调仓交易模式

## 修复

1. 修复后台线程异常捕捉钩子函数，对于Python 3.7的语法兼容性问题
2. 修复vnpy_mysql加载历史数据时存在时段重复的问题
3. 修复vnpy_ib由于TWS客户端升级导致的委托失败问题
4. 修复vnpy_rest/vnpy_websocket对Python 3.10后asyncio的支持
5. 修复vnpy_sopt由于流控导致的委托失败时，返回【提交中】状态委托的问题


# 3.4.0版本

## 新增

1. 新增杰宜斯资管系统交易接口vnpy_jees

## 调整

1. 开启vnpy.rpc的pyzmq连接keepalive机制，避免在复杂网络环境下闲置连接的断开
2. 移除vnpy_rpcservice中服务端的EVENT_TIMER定时事件推送
3. 调整vnpy_postgresql采用批量方式写入数据，提高效率
4. 添加VeighNa Trader中的子线程异常捕捉（需要Python>=3.8）
5. 调整vnpy_ib接口查询历史K线数据时，对外汇和贵金属均采用中间价（而非成交价）
6. 增加vnpy_ctastrategy对于回测过程中资金爆仓（小于等于0）情况的检查
7. 优化vnpy_webtrader模块的加密鉴权，支持web进程关闭重启

## 修复

1. 修复vnpy.rpc模块对于23.0以上版本pyzmq的NOBLOCK兼容性问题
2. 修复vnpy_taos由于TDengine版本升级，出现d的一系列兼容问题
3. 修复vnpy_datamanager刷新数据汇总信息显示时，老数据点移除失败的问题



# 3.3.0版本

## 新增
1. 新增数据库组件vnpy.trader.database中的TickOverview对象
2. 新增掘金仿真环境交易接口vnpy_gm
3. BaseData基础数据类型增加extra字段（字典类型），用于传送任意相关数据

## 调整
1. 使用Python内置的zoneinfo库替换三方的pytz库
2. 调整相关交易接口、数据服务接口、数据库适配器、应用模块，使用新的ZoneInfo对象来标识时区信息
3. 数据库适配器接口vnpy.trader.database写入数据时，新增流式写入参数stream，提高行情录制性能


# 3.2.0版本

## 新增
1. 添加广州期货交易所枚举值字段GFEX
2. 新增CTP期权（ETF）穿透式测试接口vnpy_sopttest
3. 新增Currency.CAD（加元）枚举值
4. 新增Exchange.TSE（多伦多交易所）和Exchange.AMEX（美洲交易所）枚举值
5. 新增vnpy_taos，涛思数据TDengine时序数据库适配器
5. 新增vnpy_timescaledb，TimescaleDB时序数据库适配器

## 调整
1. 更新vnpy_ctp/vnpy_ctptest支持广州期货交易所
2. 更新vnpy_tora的现货API接口到最新版本：API_Python3.7_交易_v4.0.3_20220222
3. 更新vnpy_tora的期权API接口到最新版本：API_Python3.7_v1.3.2_20211201
4. 更新vnpy_esunny/vnpy_tap添加关闭接口时对于API退出函数的调用
5. 移除vnpy_ctastrategy/vnpy_ctabacktester/vnpy_optionmaster的反向合约支持
6. 增加vnpy_ib对于沪股通、深股通、多伦多交易所、美洲交易所的支持
7. 增加vnpy_ib对于指数行情数据的支持
8. 添加vnpy_ctastrategy策略交易管理界面的策略实例查找功能

## 修复

1. 修复vnpy_mongodb中K线数据量统计的问题（使用新的count_documents函数）
2. 修复由于PySide6对象销毁先于__del__调用，导致的BaseMonitor衍生组件无法自动保存界面状态的问题



# 3.1.0版本

## 新增
1. 新增恒生云UF2.0证券仿真环境交易接口vnpy_uf
2. 新增火象投教仿真环境交易接口vnpy_hx

## 调整
1. 升级tzlocal库的版本到4.2，消除get_localzone()函数的warning
2. 完善代码中函数和变量类型提示
3. 使用QtCore.Signal代替老的QtCore.pyqtSignal
4. 优化vnpy_rohon接口的委托成交相关细节功能
5. 更新vnpy_xtp到2.2.32.2.0版本XTP API，支持上交所新债系统
6. 优化vnpy_mongodb的数据写入速度，基于pymongo 4.0版本的批量写入功能
7. 增加vnpy_ctp对于委托函数返回值为非0（请求发送失败）状态的处理
8. 对vnpy_ctastrategy和vnpy_ctabacktester的策略模板下拉框中内容，改为基于首字母排序

## 修复
1. 修复vnpy_optionmaster模块希腊值监控组件的数据刷新问题
2. 修复vnpy_mongodb由于时间戳的时区信息确实，导致的数据加载范围问题
3. 修复vnpy_tts的sdist源代码打包缺失lib文件的问题
4. 修复vnpy_rqdata由于查询返回数据为NaN导致的解析问题


# 3.0.0版本

## 调整
1. 移除api、gateway、app子模块的目录
2. 移除requirements.txt对于插件的默认依赖
3. 简化重构rpc子模块，定位于可靠环境下跨进程通讯（本机、局域网）
4. 移除rpc子模块对于鉴权的支持
5. 调整rpc子模块中的心跳机制的实现方式
6. 移除基于QScintilla开发的代码编辑器，改用VSCode打开代码
7. 优化MainWindow主窗口中，对于QAction按钮图标的加载逻辑
8. MainEngine添加交易接口时，支持自定义接口名称

## 修复
1. 使用非原生窗口菜单栏，修复Linux/Mac下【配置】按钮不显示的问题


# 2.9.0版本

## 新增
1. 新增顶点HTS柜台交易接口vnpy_hts

#1.0.1
  ###增加日内交易次数限制为day_max_count设置
#1.0.2
  ###stop_win之后给予repeat机会.
#1.0.3
  ###邮箱系统压力过大:部分成交或取消发送邮件通知.
  ###恢复停止单(移动止盈)修复
#1.0.4 (Todo)
  ###修复正向合约利润计算的一个bug(回测使用)
  ###通过trade单逐笔计算收益和损耗~
#1.0.5
  ###平仓单未成交状态检测立即cancel,重新下单.
  ###只能在实盘使用,回测不行.
#1.0.6
  ###usdt_永续合约 对接
  ###开仓策略调整,拆单操作(暂时不用).
  ###最高价最低价修改
  ###邮箱系统改用企业微信模式
#1.0.7
  ###微信推送格式,markdown格式 价格 成交量.
  ###huobis 账户和持仓查询不用rest模式,改为websockt模式.
#1.0.8
  ###开始策略时候计算前高和前低错误的bug.
#1.1.3
 ## 平仓逻辑：偏离开仓价大于滑点，止损。否则躺平，超过规定时间用止损价之内价格挂单。