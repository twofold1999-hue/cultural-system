from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class BaseBusinessModule(QWidget):
    """
    所有独立业务菜单的生命周期与公共上下文基类
    """
    def __init__(self, title=""):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        """留给子类实现各自深度交互的接口"""
        pass

    def cleanup(self):
        """
        模块被卸载/热重载前的清理钩子
        子类应在此处停止定时器、断开信号、释放资源，避免 C++ 对象被删除后崩溃
        """
        pass
