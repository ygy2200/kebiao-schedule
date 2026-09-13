# -*- coding: utf-8 -*-
"""新版入口（v2 重构）。

运行：python app/app.py   （项目根目录的数据层直接 import）
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
APP_DIR = os.path.join(ROOT, "app")

sys.argv = [sys.argv[0]] + sys.argv[1:]

from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

import db
import icon
import reminder

INSTANCE_NAME = "KebiaoScheduleApp"


def single_instance():
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return None, False
    server = QLocalServer()
    QLocalServer.removeServer(INSTANCE_NAME)
    server.listen(INSTANCE_NAME)
    return server, True


def apply_theme(app):
    """主题持久化走 db.settings（qfw 的 qconfig 在本机实测不落盘，json 恒空 {}，
    故弃用 qconfig 持久化）。显式 setTheme(save=False)，启动/系统变化时调用。
    设置页切主题：db.set_setting("theme_mode", ...) 后调用本函数。"""
    from qfluentwidgets import Theme, qconfig
    mode = (db.get_setting("theme_mode", "dark") or "dark").lower()
    if mode == "auto":
        try:
            dark = app.styleHints().colorScheme().name == "ColorScheme.Dark"
        except Exception:
            dark = False
    else:
        dark = mode == "dark"
    # 源码级关键（qfw 1.11.3）：setTheme() 写 themeMode 配置项但不更新运行时
    # 主题 qconfig._cfg._theme；唯一入口是 qconfig.theme = t 这个 setter。
    # 用 setTheme 是无效切换——此前"深窗浅卡"的最终根因。
    qconfig.theme = Theme.DARK if dark else Theme.LIGHT


def check_reminders(window, tray, fired):
    if tray is not None and getattr(tray, "paused", False):
        return
    now = dt.datetime.now()
    first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
    ahead = int(db.get_setting("remind_ahead", reminder.DEFAULT_AHEAD) or reminder.DEFAULT_AHEAD)
    for r in reminder.candidates(now, db.list_courses(), db.list_events(),
                                 first_monday, ahead):
        if r["key"] in fired:
            continue
        fired.add(r["key"])
        kind = "下节课" if r["kind"] == "course" else "日程提醒"
        db.add_reminder(r["kind"], r["title"], r["detail"],
                        now.isoformat(timespec="seconds"))  # M6 留痕
        from qfluentwidgets import InfoBar, InfoBarPosition
        pos = InfoBarPosition.TOP_RIGHT
        InfoBar.success(title=kind, content=f"{r['title']}　{r['detail']}",
                        orient=0, isClosable=True, duration=8000,
                        position=pos, parent=window)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("课表日程助手")
    app.setQuitOnLastWindowClosed(False)

    server, is_first = single_instance()
    if not is_first:
        return 0

    db.init_db()
    try:
        from app.core import backup as _backup
        _backup.backup_all()  # 启动自动备份（保留最近 5 份）
    except Exception:
        pass

    from app.ui.main_window import MainWindow
    from tray import TrayIcon

    apply_theme(app)  # 显式主题须在窗口构造前（qfw 控件构造时定色）
    window = MainWindow()
    fired = set()

    # 启动画面：盖住 qfw+PyInstaller 的初始化期（数秒），避免"半成品界面"
    from qfluentwidgets import SplashScreen
    from qfluentwidgets import FluentIcon as FIF
    splash = SplashScreen(FIF.TILES, window)
    splash.show()

    tray = TrayIcon(icon.ICON_PATH, window, on_quit=lambda: on_quit(window, tray, app))
    tray.setToolTip("课表日程助手")
    tray.show()
    window.setup_shortcuts(tray)

    # Alt+A 全局热键快速添加（失败降级：应用内 Ctrl+K 仍有"添加日程"）
    from app.ui.quick_add import GlobalHotkeyManager, QuickAddWindow

    def _on_quick_saved():
        window.page_events.refresh()
        from qfluentwidgets import InfoBar
        InfoBar.success("已添加", "今日快速日程已保存", duration=2500, parent=window)

    quick_add = QuickAddWindow(on_saved=_on_quick_saved)
    hotkeys = GlobalHotkeyManager(on_trigger=quick_add.popup)
    hotkeys.register()

    server.newConnection.connect(lambda: (
        (s := server.nextPendingConnection()) and (
            s.waitForReadyRead(300),
            window.bring_up(),
            s.disconnectFromServer())))

    timer = QTimer()
    timer.setInterval(60 * 1000)
    timer.timeout.connect(lambda: check_reminders(window, tray, fired))
    timer.start()
    check_reminders(window, tray, fired)

    # 法定节假日数据：启动后台静默更新（30 天缓存，失败用内置/缓存）
    import threading
    from app.core import holidays as _hol

    def _refresh_holidays_bg():
        try:
            _hol.refresh()
        except Exception:
            pass
    threading.Thread(target=_refresh_holidays_bg, daemon=True).start()

    try:
        app.styleHints().colorSchemeChanged.connect(lambda *_: (
            apply_theme(app), window.refresh()))
    except Exception:
        pass

    # 先显示主窗口，再弹引导（此前引导在 show 之前模态阻塞，主窗口缺席 =
    # 用户看到的"初启动界面不完整"）
    window.show()
    splash.finish()

    if not db.list_courses():
        QTimer.singleShot(600, lambda: QMessageBox.information(
            window, "第一次使用",
            "先导入你的课表：\n\n课表页 → 「导入课表 xlsx」\n\n"
            "然后在设置页确认「学期第一周周一」的日期，提醒功能即生效。"))

    return app.exec()


def on_quit(window, tray, app):
    """退出：隐藏 + quit + 强杀兜底（PySide6 6.11 item view+QSS 退出 bug）。"""
    window.hide()
    tray.hide()
    app.processEvents()
    app.quit()
    QTimer.singleShot(1200, lambda: os._exit(0))


if __name__ == "__main__":
    sys.exit(main())
