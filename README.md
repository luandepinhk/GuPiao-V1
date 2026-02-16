# GuPiao-V1 股票离线行情分析选股工具

基于 PyQt5 + Matplotlib 的本地股票日线分析工具，支持通达信 .day 数据导入、日/周/月 K 线、价格与成交量均线、SQLite 本地存储。

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
