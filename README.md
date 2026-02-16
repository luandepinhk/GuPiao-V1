# GuPiao-V1 股票离线行情分析选股工具

基于 PyQt5 + Matplotlib 的本地股票日线分析工具，支持通达信 .day 数据导入、日/周/月 K 线、价格与成交量均线、SQLite 本地存储。

https://blog.csdn.net/starsky2006/article/details/5863426?utm_source=chatgpt.com 
https://blog.csdn.net/starsky2006/article/details/5863426?utm_source=chatgpt.com 
https://blog.csdn.net/lh2273341049/article/details/145273996?utm_source=chatgpt.com 
https://damodev.csdn.net/69250d913fd22d045343e476.html?utm_source=chatgpt.com 


●存储的数据（推荐入库）：公司代码：股票代码
●日K 原始数据：日期、开、高、低、收、成交额、成交量
●来源路径：导入时的 .day 文件路径（可选，用于 DB 无数据时回退读取）
●不存储的数据（运行时计算）：周K、月K：由日K 聚合
●股价均线 Ma5～Ma240：由收盘价计算
●成交量均线 Ma5～Ma90：由成交量计算
1.数据流：导入 .day → 解析 → 写入 DB → 加入列表
2.切换股票 → 优先从 DB 读取 → 若 DB 没有则从文件读取并写入 DB
3.启动程序 → 从 DB 读取股票列表 → 加载当前选中股票数据


## 环境

- Python 3.10+
- PyQt5, matplotlib

```bash
pip install -r requirements.txt
```

## 运行

```bash
python test_pyqt5.py
```

## 说明

- 左侧：股票列表，支持导入 .day 文件
- 中间：K 线图 + 成交量/均线
- 右侧：公司代码、K 线周期、股价均线、成交量 VOL 与均线
- 数据存于项目目录下 `stock_data.db`（SQLite）

详见 `PyQt5-开发环境说明.md`、`数据库说明.md`。
