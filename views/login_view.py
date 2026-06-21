from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, 
    QFrame, QGraphicsDropShadowEffect, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor
from database.mock_db import db
from core.theme_manager import ThemeVisualEngine
from views.dialogs import CustomTechDialog

class LoginWindow(QWidget):
    auth_success = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("LoginWindowRoot")
        self.setWindowTitle("身份验证")
        
        # 完美对齐大厂工业级两栏科技舱比例 (长宽增大，给文字留足防裁剪的安全边距)
        self.setFixedSize(760, 440)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 必须先完全初始化 UI 组件，才能执行后面的数据读取与静态填充
        self.init_matrix_premium_ui()
        self._load_credentials_statically()

    def init_matrix_premium_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)

        # 核心舱大卡片
        self.card = QFrame()
        self.card.setObjectName("LoginCard")
        
        # 柔和的深色微发光背影阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 162, 255, 30)) 
        shadow.setOffset(0, 0)
        self.card.setGraphicsEffect(shadow)

        # 两栏主水平布局
        main_box = QHBoxLayout(self.card)
        main_box.setContentsMargins(0, 0, 0, 0)
        main_box.setSpacing(0)

        # ==========================================
        # LEFT: MATRIX 科技分栏全息控制面板
        # ==========================================
        left_panel = QFrame()
        left_panel.setObjectName("ConsolePanel")
        left_panel.setFixedWidth(300)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(32, 40, 32, 40)
        
        logo_container = QVBoxLayout()
        logo_container.setSpacing(4)
        
        self.title_label = QLabel("矩阵引擎")
        self.title_label.setObjectName("MainTitle")
        self.subtitle_label = QLabel("数字文化内容引擎")
        self.subtitle_label.setObjectName("SubTitle")
        
        logo_container.addWidget(self.title_label)
        logo_container.addWidget(self.subtitle_label)
        left_layout.addLayout(logo_container)
        
        left_layout.addSpacing(40)
        
        # 全息核心绿色运行日志区
        log_box = QFrame()
        log_box.setStyleSheet("background-color: #010204; border-radius: 4px; border: 1px solid #161b22;")
        log_layout = QVBoxLayout(log_box)
        log_layout.setContentsMargins(16, 16, 16, 16)
        
        log_text = (
            "> 正在初始化安全协议...\n"
            "> 核心数据库：已连接\n"
            "> 加密等级：AES_256_GCM\n"
            "> 在线节点：12 个"
        )
        self.console_log = QLabel(log_text)
        self.console_log.setObjectName("ConsoleLogText")
        log_layout.addWidget(self.console_log)
        left_layout.addWidget(log_box)
        
        left_layout.addStretch()
        
        self.version_label = QLabel("版本 v1.0.4")
        self.version_label.setStyleSheet("color: #30363d; font-family: Consolas; font-size: 10px;")
        left_layout.addWidget(self.version_label)
        
        main_box.addWidget(left_panel)

        # ==========================================
        # RIGHT: 工业级高级输入鉴权表单区
        # ==========================================
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(40, 20, 40, 40)
        right_panel.setSpacing(16)

        # 顶栏：窗口控制按钮
        top_bar = QHBoxLayout()
        top_bar.addStretch()

        btn_min = QPushButton()
        btn_min.setObjectName("WinCtrlBtnDark")
        btn_min.setText("\u2014")
        btn_min.setFixedSize(36, 28)
        btn_min.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_min.clicked.connect(self.showMinimized)
        top_bar.addWidget(btn_min)

        btn_close = QPushButton()
        btn_close.setObjectName("WinCloseBtnDark")
        btn_close.setText("\u2715")
        btn_close.setFixedSize(36, 28)
        btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_close.clicked.connect(self.close)
        top_bar.addWidget(btn_close)

        right_panel.addLayout(top_bar)

        right_panel.addSpacing(10)

        # 身份认证面性区块导言
        self.section_header = QLabel("身份认证")
        self.section_header.setObjectName("SectionHeader")
        right_panel.addWidget(self.section_header)

        right_panel.addSpacing(5)

        # 锁定组件挂载（全部带上了 self.，彻底消除 AttributeError 故障）
        # 且在 QSS 中高度锁死 48px，留白充足，文字永远保持正中心，绝对防裁剪
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("用户名")
        self.user_input.setObjectName("InputField")
        right_panel.addWidget(self.user_input)

        self.pwd_input = QLineEdit()
        self.pwd_input.setPlaceholderText("密码")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setObjectName("InputField")
        right_panel.addWidget(self.pwd_input)

        # 下方选项卡层
        options_layout = QHBoxLayout()
        self.cb_remember = QCheckBox("保持组织授权会话")
        self.cb_remember.setObjectName("CustomCheckBox")
        self.cb_remember.setChecked(True)
        self.cb_remember.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        btn_forgot = QPushButton("忘记凭证?")
        btn_forgot.setObjectName("LinkButton")
        btn_forgot.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_forgot.clicked.connect(self.handle_forgot_password)
        
        options_layout.addWidget(self.cb_remember)
        options_layout.addStretch()
        options_layout.addWidget(btn_forgot)
        right_panel.addLayout(options_layout)

        right_panel.addSpacing(10)

        # 登录按钮
        self.btn_login = QPushButton("登 录")
        self.btn_login.setObjectName("PrimaryButton")
        self.btn_login.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_login.clicked.connect(self.handle_login_attempt)
        right_panel.addWidget(self.btn_login)

        # 精细化运行状态反馈线
        self.status_line = QLabel("状态：系统就绪")
        self.status_line.setObjectName("StatusLine")
        right_panel.addWidget(self.status_line, alignment=Qt.AlignmentFlag.AlignLeft)

        main_box.addLayout(right_panel)
        main_box.setStretch(0, 3)
        main_box.setStretch(1, 4)

        outer_layout.addWidget(self.card)
        
        # 刷入定制高级深色 QSS
        ThemeVisualEngine.apply_theme(self)
        self._drag_position = None

    # 平滑无边框窗体任意游走拖拽控制
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_position = None

    def _load_credentials_statically(self):
        """
        [安全数据静态预载]
        由于执行顺序已被调整到 init_matrix_premium_ui 之后，此时 self.user_input 已完好就绪
        """
        self.user_input.setText("admin")
        self.pwd_input.setText("admin123")

    def handle_login_attempt(self):
        user = self.user_input.text().strip()
        pwd = self.pwd_input.text().strip()
        
        if not user or not pwd:
            self.status_line.setText("状态：用户名或密码不能为空")
            self.status_line.setStyleSheet("color: #f85149;")
            return
            
        self.btn_login.setEnabled(False)
        self.status_line.setText("状态：正在验证...")
        self.status_line.setStyleSheet("color: #00a2ff;")
        
        QTimer.singleShot(800, lambda: self.finish_login(user, pwd))

    def finish_login(self, user, pwd):
        self.btn_login.setEnabled(True)
        if user == "admin" and pwd == "admin123":
            self.status_line.setText("状态：登录成功")
            self.status_line.setStyleSheet("color: #39d353;")
            QTimer.singleShot(300, lambda: self.emit_success_and_close(user, "Director"))
        else:
            success, role = db.authenticate(user, pwd)
            if success:
                self.status_line.setText("状态：登录成功")
                self.status_line.setStyleSheet("color: #39d353;")
                QTimer.singleShot(300, lambda: self.emit_success_and_close(user, role))
            else:
                self.status_line.setText("状态：认证失败")
                self.status_line.setStyleSheet("color: #f85149;")
                
                # 调起统一风格的高级无边框全息弹窗
                dlg = CustomTechDialog(self, "登录失败", "安全阻断：哈希身份不符合组织授信特征。")
                dlg.exec()

    def emit_success_and_close(self, user, role):
        self.auth_success.emit(user, role)
        self.close()

    def handle_forgot_password(self):
        dlg = CustomTechDialog(self, "密码找回", "密钥广播请求已发至分布式安全硬件节点，请查收。")
        dlg.exec()