from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor
from core.theme_manager import ThemeVisualEngine

class CustomTechDialog(QDialog):
    """
    全系统统一的自定义高级科技感通知弹窗（完全替换原生 QMessageBox）
    """
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 200)
        
        # 外层布局
        out_layout = QVBoxLayout(self)
        out_layout.setContentsMargins(10, 10, 10, 10)
        
        # 核心卡片容器
        card = QFrame()
        card.setObjectName("DialogCard")
        
        # 微发光阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 162, 255, 40))
        shadow.setOffset(0, 0)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        
        # 标题栏
        title_label = QLabel(title)
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # 内容栏
        msg_label = QLabel(message)
        msg_label.setObjectName("DialogMessage")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        layout.addStretch()
        
        # 确认按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("确认")
        btn_ok.setObjectName("DialogButton")
        btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)
        
        out_layout.addWidget(card)
        
        # 应用全局QSS
        ThemeVisualEngine.apply_theme(self)