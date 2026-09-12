import sys, os
sys.argv = ['m5nav']
sys.path.insert(0, r"C:\Users\y\Desktop\zcode项目记录\课表日程App")
import faulthandler
faulthandler.dump_traceback_later(12, exit=True)
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
app = QApplication([])
from app.ui.main_window import MainWindow
w = MainWindow()
w.show()
def go():
    w.switchTo(w.pages["page_calendar"])
    QTimer.singleShot(900, grab)
def grab():
    from self_capture import capture_window, find_hwnd
    hwnd = find_hwnd("课表日程助手")
    print("captured:", capture_window(hwnd, "C:/Users/y/Desktop/zcode项目记录/课表日程App/real_m5.png")[1:] if hwnd else "NOT FOUND")
    QTimer.singleShot(500, lambda: os._exit(0))
QTimer.singleShot(2500, go)
app.exec()
