# PyQt5 开发环境说明

## 已安装内容

| 项目 | 版本/路径 |
|------|-----------|
| **Python** | 3.10.11 (64-bit) |
| **Python 路径** | `%LOCALAPPDATA%\Programs\Python\Python310\` |
| **PyQt5** | 5.15.9（含 Qt 5.15.2） |
| **pyqt5-tools** | 5.15.9.3.3 |

已执行：
- `pip install pyqt5`
- `pip install pyqt5-tools`

---

## 在 PyCharm 中使用

1. **配置解释器**  
   打开 PyCharm → **File** → **Settings** → **Project: xxx** → **Python Interpreter**，添加解释器，选择：
   ```
   C:\Users\Laptop\AppData\Local\Programs\Python\Python310\python.exe
   ```

2. **Qt Designer（设计 .ui 界面）**  
   - **Settings** → **Tools** → **External Tools** → **+** 新建：
     - **Name**: `Qt Designer`
     - **Program**:  
       `C:\Users\Laptop\AppData\Local\Programs\Python\Python310\Scripts\pyqt5-tools.exe`
     - **Arguments**: `designer`
     - **Working directory**: `$ProjectFileDir$`

3. **pyuic5（.ui 转 .py）**  
   同上 **External Tools** 新增：
   - **Name**: `PyUIC`
   - **Program**:  
     `C:\Users\Laptop\AppData\Local\Programs\Python\Python310\Scripts\pyuic5.exe`
   - **Arguments**: `$FileName$ -o $FileNameWithoutExtension$_ui.py`
   - **Working directory**: `$FileDir$`

---

## 常用命令（新开终端需先刷新 PATH）

```powershell
# 若新终端中 python 不可用，可直接用完整路径
& "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" -m pip list

# 启动 Qt Designer
& "$env:LOCALAPPDATA\Programs\Python\Python310\Scripts\pyqt5-tools.exe" designer
```

---

## 最小测试脚本

创建 `test_pyqt5.py`：

```python
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

app = QApplication(sys.argv)
w = QWidget()
w.setWindowTitle("PyQt5 测试")
w.resize(300, 100)
label = QLabel("PyQt5 环境正常", w)
label.move(50, 40)
w.show()
sys.exit(app.exec_())
```

在项目目录运行：
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" test_pyqt5.py
```

若弹出窗口并显示「PyQt5 环境正常」，说明环境可用。
