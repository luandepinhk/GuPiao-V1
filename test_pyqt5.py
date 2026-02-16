"""股票离线行情分析 - 左股票列表 | 中K线图 | 下成交量/指标 | 右参数/策略（含日周月K、价格/成交量均线）"""
import struct
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QFrame, QComboBox, QScrollArea,
)
from PyQt5.QtCore import Qt

# 尝试嵌入 Matplotlib，并配置中文显示
try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "SimSun", "KaiTi", "FangSong", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# 通达信 .day
DAY_RECORD_SIZE = 32
DAY_STRUCT_FMT = "IIIIIfII"
DEFAULT_DAY_DIR = r"E:\ZSZQ\vipdoc\sz\lday"

# 关注的指标参数
PRICE_MA_PERIODS = [5, 10, 20, 30, 40, 50, 60, 90, 120, 240]
VOL_MA_PERIODS = [5, 10, 20, 30, 60, 90]
K_PERIODS = ["日K", "周K", "月K"]

# SQLite 数据库路径（项目目录下）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_data.db")


# ========== SQLite 数据库 ==========
def init_db():
    """初始化数据库表。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            source_path TEXT,
            updated_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_k (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            amount REAL, vol INTEGER,
            PRIMARY KEY (code, date)
        )
    """)
    conn.commit()
    conn.close()


def load_from_db(code):
    """从数据库加载日线，返回 [{'date','open','high','low','close','amount','vol'}, ...] 或 None。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT date, open, high, low, close, amount, vol FROM daily_k WHERE code=? ORDER BY date",
        (code,),
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return None
    return [
        {"date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "amount": r[5], "vol": r[6]}
        for r in rows
    ]


def save_to_db(code, items, source_path=None):
    """将日线写入数据库。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT OR REPLACE INTO stocks (code, source_path, updated_at) VALUES (?, ?, ?)",
        (code, source_path or "", now),
    )
    for d in items:
        cur.execute(
            """INSERT OR REPLACE INTO daily_k (code, date, open, high, low, close, amount, vol)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, d["date"], d["open"], d["high"], d["low"], d["close"], d["amount"], d["vol"]),
        )
    conn.commit()
    conn.close()


def get_stock_list_from_db():
    """获取数据库中已有股票代码列表，用于启动时填充左侧列表。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, source_path FROM stocks ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1] or "") for r in rows]


# ========== .day 解析 ==========
def read_day_file(file_path):
    """解析通达信日线 .day 文件。"""
    items = []
    try:
        with open(file_path, "rb") as f:
            buf = f.read()
    except FileNotFoundError:
        return None, "文件不存在"
    except Exception as e:
        return None, str(e)
    if len(buf) % DAY_RECORD_SIZE != 0:
        return None, "不是有效 .day 文件"
    n = len(buf) // DAY_RECORD_SIZE
    for i in range(n):
        b = i * DAY_RECORD_SIZE
        data = struct.unpack(DAY_STRUCT_FMT, buf[b : b + DAY_RECORD_SIZE])
        date_int = data[0]
        if date_int < 19900101 or date_int > 21001231:
            continue
        try:
            date_str = datetime.strptime(str(date_int), "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            continue
        items.append({
            "date": date_str,
            "open": round(data[1] / 1000.0, 2),
            "high": round(data[2] / 1000.0, 2),
            "low": round(data[3] / 1000.0, 2),
            "close": round(data[4] / 1000.0, 2),
            "amount": round(data[5], 0),
            "vol": int(data[6]),
        })
    return items, None


def resample_k(daily_bars, period):
    """将日线聚合为 日K/周K/月K。period: '日K'|'周K'|'月K'。"""
    if not daily_bars:
        return []
    if period == "日K":
        return list(daily_bars)
    bars = []
    for d in daily_bars:
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        if period == "周K":
            key = (dt.isocalendar()[0], dt.isocalendar()[1])
        else:
            key = (dt.year, dt.month)
        bars.append((key, d))
    groups = defaultdict(list)
    for key, d in bars:
        groups[key].append(d)
    out = []
    for key in sorted(groups.keys()):
        g = groups[key]
        out.append({
            "date": g[-1]["date"],
            "open": g[0]["open"],
            "high": max(x["high"] for x in g),
            "low": min(x["low"] for x in g),
            "close": g[-1]["close"],
            "amount": sum(x["amount"] for x in g),
            "vol": sum(x["vol"] for x in g),
        })
    return out


def calc_ma(series, periods):
    n = len(series)
    result = {}
    for p in periods:
        arr = [None] * n
        for i in range(p - 1, n):
            arr[i] = sum(series[i - p + 1 : i + 1]) / p
        result[p] = arr
    return result


def draw_kline_volume(canvas, plot_data, stock_code, k_period, price_ma_d, vol_ma_d):
    if not HAS_MATPLOTLIB or not plot_data:
        return
    fig = canvas.figure
    fig.clear()
    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in plot_data]
    o = [d["open"] for d in plot_data]
    h = [d["high"] for d in plot_data]
    l = [d["low"] for d in plot_data]
    c = [d["close"] for d in plot_data]
    v = [d["vol"] for d in plot_data]

    ax1 = fig.add_subplot(211)
    ax1.set_title(f"{stock_code} - {k_period}")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    for i in range(len(dates)):
        color = "red" if c[i] >= o[i] else "green"
        ax1.vlines(dates[i], l[i], h[i], color=color, linewidth=1)
        ax1.vlines(dates[i], min(o[i], c[i]), max(o[i], c[i]), color=color, linewidth=3)
    colors_ma = "blue orange green red purple brown pink gray olive cyan".split()
    for idx, (period, ma_list) in enumerate(price_ma_d.items()):
        if not ma_list or ma_list[-1] is None:
            continue
        valid = [(dates[i], ma_list[i]) for i in range(len(dates)) if ma_list[i] is not None]
        if not valid:
            continue
        xs, ys = zip(*valid)
        ax1.plot(xs, ys, label=f"Ma{period}", color=colors_ma[idx % len(colors_ma)], linewidth=1, alpha=0.8)
    ax1.set_ylabel("价格")
    ax1.legend(loc="upper left", fontsize=7, ncol=2)
    ax1.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    ax2 = fig.add_subplot(212, sharex=ax1)
    ax2.set_title("成交量 VOL 与均线")
    bar_colors = ["red" if c[i] >= o[i] else "green" for i in range(len(dates))]
    ax2.bar(dates, v, color=bar_colors, width=0.6, alpha=0.7, label="VOL")
    for idx, (period, ma_list) in enumerate(vol_ma_d.items()):
        if not ma_list or ma_list[-1] is None:
            continue
        valid = [(dates[i], ma_list[i]) for i in range(len(dates)) if ma_list[i] is not None]
        if not valid:
            continue
        xs, ys = zip(*valid)
        ax2.plot(xs, ys, label=f"V_Ma{period}", color=colors_ma[idx % len(colors_ma)], linewidth=1.2, alpha=0.9)
    ax2.set_ylabel("成交量")
    ax2.legend(loc="upper right", fontsize=7, ncol=2)
    ax2.grid(True, alpha=0.3)
    fig.tight_layout()
    canvas.draw()


def main():
    init_db()

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("股票离线行情分析软件-选股工具V1.0")
    win.resize(1280, 720)

    left = QFrame()
    left.setFrameStyle(QFrame.StyledPanel)
    left_layout = QVBoxLayout(left)
    left_layout.addWidget(QLabel("股票列表"))
    stock_list = QListWidget()
    stock_list.setMinimumWidth(160)
    left_layout.addWidget(stock_list)
    btn_import = QPushButton("导入数据")
    left_layout.addWidget(btn_import)
    left_layout.addStretch()

    if HAS_MATPLOTLIB:
        center_fig = Figure(figsize=(7, 5), dpi=100)
        center_canvas = FigureCanvas(center_fig)
        center_canvas.setMinimumSize(500, 400)
    else:
        center_canvas = QLabel("请安装 matplotlib：pip install matplotlib")
        center_canvas.setMinimumSize(500, 400)

    right = QFrame()
    right.setFrameStyle(QFrame.StyledPanel)
    right_scroll = QScrollArea()
    right_scroll.setWidget(right)
    right_scroll.setWidgetResizable(True)
    right_scroll.setMinimumWidth(220)
    right_layout = QVBoxLayout(right)

    right_layout.addWidget(QLabel("参数 / 策略"))
    code_box = QGroupBox("公司代码")
    code_layout = QFormLayout(code_box)
    label_stock_code = QLabel("-")
    code_layout.addRow("代码:", label_stock_code)
    right_layout.addWidget(code_box)
    k_box = QGroupBox("K线周期")
    k_layout = QFormLayout(k_box)
    combo_k_period = QComboBox()
    combo_k_period.addItems(K_PERIODS)
    k_layout.addRow("周期:", combo_k_period)
    right_layout.addWidget(k_box)
    price_box = QGroupBox("股价均线")
    price_form = QFormLayout(price_box)
    price_ma_labels = {p: QLabel("-") for p in PRICE_MA_PERIODS}
    for p in PRICE_MA_PERIODS:
        price_form.addRow(f"Ma{p}:", price_ma_labels[p])
    right_layout.addWidget(price_box)
    vol_box = QGroupBox("成交量 VOL 与均线")
    vol_form = QFormLayout(vol_box)
    vol_ma_labels = {"VOL": QLabel("-")}
    vol_form.addRow("VOL:", vol_ma_labels["VOL"])
    for p in VOL_MA_PERIODS:
        vol_ma_labels[p] = QLabel("-")
        vol_form.addRow(f"Ma{p}:", vol_ma_labels[p])
    right_layout.addWidget(vol_box)
    btn_analyze = QPushButton("执行分析")
    right_layout.addWidget(btn_analyze)
    right_layout.addStretch()

    main_split = QSplitter(Qt.Horizontal)
    main_split.addWidget(left)
    main_split.addWidget(center_canvas)
    main_split.addWidget(right_scroll)
    main_split.setStretchFactor(0, 0)
    main_split.setStretchFactor(1, 1)
    main_split.setStretchFactor(2, 0)

    layout = QVBoxLayout(win)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.addWidget(main_split)

    day_data = []
    current_stock_code = "-"

    def add_stock_to_list(code, path):
        """向列表添加一项，并保存 path 到 UserRole。"""
        for i in range(stock_list.count()):
            if stock_list.item(i).text() == code:
                stock_list.item(i).setData(Qt.UserRole, path)
                return
        item = QListWidgetItem(code)
        item.setData(Qt.UserRole, path)
        stock_list.addItem(item)

    def refresh_chart_and_params():
        if not day_data:
            label_stock_code.setText("-")
            return
        k_period = combo_k_period.currentText()
        plot_data = resample_k(day_data, k_period)
        if not plot_data:
            return
        label_stock_code.setText(current_stock_code)
        closes = [x["close"] for x in plot_data]
        vols = [x["vol"] for x in plot_data]
        price_ma_d = calc_ma(closes, PRICE_MA_PERIODS)
        vol_ma_d = calc_ma(vols, VOL_MA_PERIODS)
        for p in PRICE_MA_PERIODS:
            arr = price_ma_d.get(p, [])
            price_ma_labels[p].setText(f"{arr[-1]:.2f}" if arr and arr[-1] is not None else "-")
        last = plot_data[-1]
        vol_ma_labels["VOL"].setText(str(last["vol"]))
        for p in VOL_MA_PERIODS:
            arr = vol_ma_d.get(p, [])
            vol_ma_labels[p].setText(f"{int(arr[-1])}" if arr and arr[-1] is not None else "-")
        if HAS_MATPLOTLIB and center_canvas:
            draw_kline_volume(center_canvas, plot_data, current_stock_code, k_period, price_ma_d, vol_ma_d)

    def load_stock(code, path):
        """加载股票数据：优先从 DB，否则从 path 对应的 .day 文件。"""
        nonlocal day_data, current_stock_code
        items = load_from_db(code)
        if items is None and path and os.path.isfile(path):
            items, err = read_day_file(path)
            if err or not items:
                return False
            save_to_db(code, items, path)
        if not items:
            return False
        day_data = items
        current_stock_code = code
        refresh_chart_and_params()
        return True

    def on_k_period_changed():
        refresh_chart_and_params()

    def on_import():
        path, _ = QFileDialog.getOpenFileName(
            win, "选择日线文件", DEFAULT_DAY_DIR, "日线 (*.day);;全部 (*.*)"
        )
        if not path:
            return
        code = path.replace("\\", "/").split("/")[-1].replace(".day", "")
        items, err = read_day_file(path)
        if err or not items:
            QMessageBox.warning(win, "导入失败", "无法解析该文件。")
            return
        save_to_db(code, items, path)
        add_stock_to_list(code, path)
        stock_list.setCurrentRow(stock_list.count() - 1)
        load_stock(code, path)
        QMessageBox.information(win, "导入完成", f"已导入 {len(items)} 条日线，并存入数据库。")

    def on_stock_selected():
        item = stock_list.currentItem()
        if not item:
            return
        code = item.text()
        path = item.data(Qt.UserRole) or ""
        if not load_stock(code, path):
            # 若 DB 无数据且 path 无效，尝试默认目录
            try_path = os.path.join(DEFAULT_DAY_DIR, code + ".day")
            if os.path.isfile(try_path):
                load_stock(code, try_path)
                item.setData(Qt.UserRole, try_path)

    def on_analyze():
        if not day_data:
            QMessageBox.information(win, "提示", "请先导入日线数据。")
            return
        QMessageBox.information(win, "分析", f"已加载 {len(day_data)} 条数据，策略逻辑可在此扩展。")

    combo_k_period.currentTextChanged.connect(on_k_period_changed)
    btn_import.clicked.connect(on_import)
    stock_list.currentRowChanged.connect(lambda: on_stock_selected())
    btn_analyze.clicked.connect(on_analyze)

    # 启动时：从 DB 加载股票列表；若无则尝试默认 sz000001
    db_stocks = get_stock_list_from_db()
    if db_stocks:
        for code, path in db_stocks:
            add_stock_to_list(code, path or "")
        stock_list.setCurrentRow(0)
        on_stock_selected()
    else:
        default_path = os.path.join(DEFAULT_DAY_DIR, "sz000001.day")
        if os.path.isfile(default_path):
            items, err = read_day_file(default_path)
            if not err and items:
                save_to_db("sz000001", items, default_path)
                add_stock_to_list("sz000001", default_path)
                stock_list.setCurrentRow(0)
                load_stock("sz000001", default_path)

    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
