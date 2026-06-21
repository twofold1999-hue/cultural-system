"""启动 GUI 并切换到版权卫士模块，截图保存"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.main_window import MasterControlWindow

app = QApplication(sys.argv)
window = MasterControlWindow("admin", "admin")
window.show()

def switch_and_capture():
    # 切换到版权卫士模块（第7个菜单）
    window.menu_list.setCurrentRow(7)
    QTimer.singleShot(500, capture)

def capture():
    # 截取整个窗口
    pixmap = window.grab()
    pixmap.save("h:/TEST1/cultural_system/copyright_screenshot.png")
    print("截图已保存到 copyright_screenshot.png")
    app.quit()

QTimer.singleShot(500, switch_and_capture)
app.exec()
