"""启动 GUI 并切换到反馈管理模块，截图保存"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from views.main_window import MasterControlWindow

app = QApplication(sys.argv)
window = MasterControlWindow("admin", "admin")
window.show()

def switch_and_capture():
    window.menu_list.setCurrentRow(8)
    QTimer.singleShot(800, capture)

def capture():
    pixmap = window.grab()
    pixmap.save("h:/TEST1/cultural_system/feedback_v3_screenshot.png")
    print("截图已保存到 feedback_v3_screenshot.png")
    app.quit()

QTimer.singleShot(500, switch_and_capture)
app.exec()
