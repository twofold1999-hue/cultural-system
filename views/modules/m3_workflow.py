"""
流程审批模块 (WorkflowModule)
==============================
MATRIX ENGINE 数字文化内容审批工作流系统 V2

参考工程交互升级（对齐参考截图）：
- 左侧：紧凑型审批单卡片列表（编号 + 标题两行）
- 右侧详情：大标题 → 圆形流程进度条 → 双栏卡片（基础上下文 | AI 风险扫描）
- 决策信息输入 / 全生命周期日志 标签页（评审意见 + 会签/总编评分勾选 + 提交分析按钮）
- 节点角色权限校验、批量操作、搜索过滤、热重载安全
"""

import time
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QTextEdit,
    QSplitter, QDialog, QFormLayout, QMessageBox, QWidget,
    QScrollArea, QSizePolicy, QMenu, QSlider, QProgressBar,
    QTabWidget, QStackedWidget, QGridLayout, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QFontMetrics, QRadialGradient
from PyQt6.QtWidgets import QApplication

from views.modules.base_module import BaseBusinessModule
from database.mock_db import db


# ============================================================
#  子组件：点击后才响应滚轮的滚动区（防误触）
# ============================================================
class ClickToScrollArea(QScrollArea):
    """
    鼠标悬停不会触发滚动，必须先点击面板获得焦点。
    点击其他地方后失去焦点，滚轮再次失效 —— 防止误触。

    视觉反馈（边框 + 滚动条联动）：
      失焦 → 透明边框 + 极淡滚动条（几乎不可见）
      聚焦 → 蓝色边框+光晕 + 主题蓝滚动条
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._focused = False

        # ---- 失焦状态样式（默认）----
        self._blur_style = (
            # 面板：透明边框，无光晕
            "QScrollArea { background: #f8fafc; border: 1px solid transparent; border-radius: 8px; }"
            # 滚动条轨道：极淡
            "QScrollBar:vertical { background: transparent; width: 8px; border-radius: 4px; margin: 2px; }"
            # 滚动条滑块：极淡灰，hover 也只稍微加深
            "QScrollBar::handle:vertical { background: rgba(203,213,225,0.25); border-radius: 4px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: rgba(203,213,225,0.45); }"
            # 去掉上下箭头按钮
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }"
        )
        # ---- 聚焦状态样式 ----
        self._focus_style = (
            # 面板：蓝色边框（Qt QSS 不支持 box-shadow，用加粗 border 模拟）
            "QScrollArea { background: #f8fafc; border: 2px solid #0ea5e9; border-radius: 8px; }"
            # 滚动条轨道：浅灰底
            "QScrollBar:vertical { background: #f1f5f9; width: 10px; border-radius: 5px; margin: 2px; }"
            # 滑块：主题蓝色
            "QScrollBar::handle:vertical { background: #0ea5e9; border-radius: 5px; min-height: 30px; }"
            "QScrollBar::handle:vertical:hover { background: #0284c7; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }"
        )
        self.setStyleSheet(self._blur_style)

    def wheelEvent(self, event):
        fw = QApplication.focusWidget()
        if fw is self or self.isAncestorOf(fw):
            super().wheelEvent(event)
        else:
            event.ignore()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._focused = True
        self.setStyleSheet(self._focus_style)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._focused = False
        self.setStyleSheet(self._blur_style)


# ============================================================
#  子组件：点击后才可拖动/滚轮的滑块（防误触）
# ============================================================
class ClickToActivateSlider(QSlider):
    """
    鼠标悬停不会触发拖动或滚轮，必须先点击激活。
    点击其他地方失活，再次需要点击才能操作 —— 防止打分误触。

    视觉反馈：
      失活 → 半透明滑块 + 灰色提示文字
      激活 → 正常亮色 + 蓝色边框
    """

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._active = False
        self._pressing = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(True)
        # 失活样式：半透明
        self._inactive_style = (
            "QSlider { border: 1px solid transparent; background: transparent; }"
            "QSlider::groove:horizontal { height: 6px; background: rgba(226,232,240,0.5); border-radius: 3px; }"
            "QSlider::sub-page:horizontal { height: 6px; background: rgba(14,165,233,0.35); border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #ffffff; border: 2px solid rgba(14,165,233,0.4); "
            "width: 16px; height: 16px; margin: -7px 0; border-radius: 9px; }"
        )
        # 激活样式：正常亮色
        self._active_style = (
            "QSlider { border: 1px solid #0ea5e9; background: transparent; }"
            "QSlider::groove:horizontal { height: 6px; background: #e2e8f0; border-radius: 3px; }"
            "QSlider::sub-page:horizontal { height: 6px; background: #0ea5e9; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #ffffff; border: 2px solid #0ea5e9; "
            "width: 16px; height: 16px; margin: -7px 0; border-radius: 9px; }"
            "QSlider::handle:horizontal:hover { background: #e0f2fe; border-color: #0284c7; }"
        )
        self.setStyleSheet(self._inactive_style)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._active:
                # 首次点击 → 仅激活，不移动
                self._activate()
                event.accept()
                return
            self._pressing = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active and self._pressing:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if self._active and self.isEnabled():
            super().wheelEvent(event)
        else:
            event.ignore()

    def _activate(self):
        if not self._active:
            self._active = True
            self.setStyleSheet(self._active_style)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def deactivate(self):
        if self._active:
            self._active = False
            self._pressing = False
            self.setStyleSheet(self._inactive_style)
            self.clearFocus()
            self.setCursor(Qt.CursorShape.ArrowCursor)


# ============================================================
#  子组件：圆形节点审批流程图（参考工程风格）
# ============================================================
class CircleWorkflowChart(QWidget):
    """
    参考工程风格的水平圆形节点流程图。
    已完成 = 绿色实心圆，当前 = 蓝色带光晕，待办 = 灰色空心圆。
    支持节点点击交互，发出 node_clicked 信号。
    """

    node_clicked = pyqtSignal(int)  # 点击的节点索引

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CircleWorkflowChart")
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.nodes = []
        self.current_idx = 0
        self.status = "pending"
        self._hover_idx = -1
        self._node_rects = []  # 缓存每个节点的点击区域

    def set_flow(self, nodes: list, current_idx: int, status: str):
        self.nodes = nodes
        self.current_idx = max(0, min(current_idx, len(nodes) - 1)) if nodes else 0
        self.status = status
        self.update()

    def mouseMoveEvent(self, event):
        """hover 高亮节点"""
        mx, my = event.position().x(), event.position().y()
        new_hover = -1
        for i, (cx, cy, r) in enumerate(self._node_rects):
            if (mx - cx) ** 2 + (my - cy) ** 2 <= (r + 4) ** 2:
                new_hover = i
                break
        if new_hover != self._hover_idx:
            self._hover_idx = new_hover
            self.setCursor(Qt.CursorShape.PointingHandCursor if new_hover >= 0
                          else Qt.CursorShape.ArrowCursor)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._hover_idx >= 0:
            self.node_clicked.emit(self._hover_idx)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            self._do_paint(painter)
        finally:
            painter.end()

    def _do_paint(self, painter: QPainter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        if not self.nodes:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Microsoft YaHei UI", 12))
            painter.drawText(QRectF(0, 0, w, h),
                            Qt.AlignmentFlag.AlignCenter, "暂无审批节点")
            return

        total = len(self.nodes)
        node_d = 50          # 圆圈直径
        radius = node_d // 2 # 圆圈半径
        label_h = 28         # 标签区域高度
        line_y = h // 2 - 6  # 连线垂直位置（略偏上，在圆心上方）
        circle_y = h // 2 - 6  # 圆心y坐标
        label_y = circle_y + radius + 10  # 标签起始y

        # 计算均匀分布的节点x坐标
        margin_x = 50
        usable_w = w - 2 * margin_x
        if total > 1:
            gap = usable_w / (total - 1)
        else:
            gap = 0
        x_coords = [margin_x + i * gap for i in range(total)]
        self._node_rects = []  # 重置点击区域缓存

        # ---- 1) 绘制连接线 ----
        for i in range(total - 1):
            x1 = x_coords[i]
            x2 = x_coords[i + 1]

            # 判断该段线是否已通过（对齐参考工程：已通过段=绿色）
            is_passed = (self.status == "approved") or (i < self.current_idx)
            if self.status == "rejected":
                line_color = QColor("#fecaca")   # 驳回时浅红
            elif is_passed:
                line_color = QColor("#38a169")    # 已通过绿色（参考工程配色）
            else:
                line_color = QColor("#e2e8f0")     # 未到灰色

            pen = QPen(line_color, 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(int(x1), line_y, int(x2), line_y)

        # ---- 2) 绘制节点圆圈 + 文字 + 标签 ----
        for i, node in enumerate(self.nodes):
            cx = int(x_coords[i])
            is_done = (self.status == "approved") or (i < self.current_idx)
            is_current = (i == self.current_idx and self.status == "pending")
            is_rejected = (self.status == "rejected" and i == self.current_idx)

            # 颜色方案（严格对齐参考工程截图）：
            #   已完成节点 = 绿色实心圆  |  当前节点 = 蓝色实心圆+光晕  |  待办 = 灰色空心圆  |  驳回 = 红色
            if is_rejected:
                fill_color = QColor("#ef4444")
                border_color = QColor("#ef4444")
                text_color = QColor("#ffffff")
            elif is_current:
                fill_color = QColor("#0ea5e9")      # 当前：蓝色
                border_color = QColor("#0ea5e9")
                text_color = QColor("#ffffff")
            elif is_done:
                fill_color = QColor("#22c55e")       # 已通过：绿色（参考工程第1个圆圈为绿）
                border_color = QColor("#22c55e")
                text_color = QColor("#ffffff")
            else:
                fill_color = QColor("#ffffff")      # 待办：白色空心
                border_color = QColor("#cbd5e1")     # 灰色边框
                text_color = QColor("#64748b")

            # 当前节点的光晕效果（蓝色光晕，与当前节点颜色一致）
            if is_current:
                glow = QRadialGradient(cx, circle_y, radius + 8)
                glow.setColorAt(0, QColor("#0ea5e940"))
                glow.setColorAt(1, QColor("#0ea5e900"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(cx - radius - 8, circle_y - radius - 8,
                                    node_d + 16, node_d + 16)

            # 绘制圆圈
            painter.setPen(QPen(border_color, 2.5))
            painter.setBrush(fill_color)
            painter.drawEllipse(cx - radius, circle_y - radius, node_d, node_d)

            # 缓存节点点击区域
            self._node_rects.append((cx, circle_y, radius))

            # hover 效果：额外外圈
            if i == self._hover_idx:
                painter.setPen(QPen(QColor("#0ea5e9"), 1.5, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(cx - radius - 5, circle_y - radius - 5,
                                    node_d + 10, node_d + 10)

            # 绘制序号（居中于圆圈内）
            font_num = QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold)
            painter.setFont(font_num)
            painter.setPen(text_color)
            num_text = str(i + 1)
            painter.drawText(
                QRectF(cx - radius, circle_y - radius, node_d, node_d),
                Qt.AlignmentFlag.AlignCenter,
                num_text
            )

            # 绘制节点名称标签（圆圈下方）
            font_label = QFont("Microsoft YaHei UI", 11)
            font_label.setWeight(QFont.Weight.Normal)
            painter.setFont(font_label)

            if is_current or is_done:
                painter.setPen(QColor("#0f172a"))
            else:
                painter.setPen(QColor("#64748b"))

            name_text = node.get("name", "-")
            # 截断过长文字
            max_w = int(gap) - 12 if total > 1 else 120
            fm = QFontMetrics(font_label)
            if fm.horizontalAdvance(name_text) > max_w:
                name_text = fm.elidedText(name_text, Qt.TextElideMode.ElideRight, max_w)

            painter.drawText(
                QRectF(cx - 60, label_y, 120, label_h),
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
                name_text
            )


# ============================================================
#  子组件：AI 智能风险扫描卡片
# ============================================================
class RiskScanWidget(QFrame):
    """
    AI 智能风险扫描面板（参考工程右侧栏）。
    展示合规度分值进度条 + 风险等级标签。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RiskScanWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#RiskScanWidget {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        self.setMinimumWidth(200)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title = QLabel("AI 智能风险扫描")
        title.setStyleSheet("font-weight: 600; font-size: 14px; color: #1e293b;")
        layout.addWidget(title)

        self._score_label = QLabel("合规度分值：--")
        self._score_label.setStyleSheet("font-size: 12px; color: #475569;")
        layout.addWidget(self._score_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(14)
        self._progress.setStyleSheet("""
            QProgressBar { background: #e2e8f0; border-radius: 7px; }
            QProgressBar::chunk { background: #38a169; border-radius: 7px; }
        """)
        layout.addWidget(self._progress)

        self._risk_label = QLabel("风险值：[--] --")
        self._risk_label.setStyleSheet("font-size: 12px; color: #475569;")
        layout.addWidget(self._risk_label)

        layout.addStretch()

    def analyze(self, record_type: str, amount: float, status: str):
        """模拟 AI 风险扫描，计算合规度与风险等级"""
        base = 85
        if amount > 1000000:
            base -= 15
        elif amount > 500000:
            base -= 8
        elif amount > 100000:
            base -= 3

        high_risk_types = ["商务合作", "版权授权", "产品开发"]
        if record_type in high_risk_types:
            base -= 5

        if status == "rejected":
            base = 30

        score = max(0, min(100, base))
        self._progress.setValue(score)

        if score >= 80:
            risk_text, color = "[0] 安全", "#38a169"
        elif score >= 60:
            risk_text, color = "[1] 提示", "#d97706"
        elif score >= 40:
            risk_text, color = "[2] 警告", "#f97316"
        else:
            risk_text, color = "[3] 危险", "#dc2626"

        self._score_label.setText(f"合规度分值：{score}")
        self._risk_label.setText(f"风险值：{risk_text}")
        self._risk_label.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: 600;")
        self._progress.setStyleSheet(f"""
            QProgressBar {{ background: #e2e8f0; border-radius: 7px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 7px; }}
        """)


# ============================================================
#  子组件：左侧紧凑型审批单卡片
# ============================================================
class ApprovalListItem(QFrame):
    """
    左侧审批单条目（参考工程风格：编号 + 标题两行紧凑布局）。
    点击选中高亮，支持 hover 反馈。
    """

    clicked = pyqtSignal(int)

    def __init__(self, index: int, record: dict, parent=None):
        super().__init__(parent)
        self._index = index
        self._record = record
        self.setObjectName("ApprovalListItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # 第一行：编号标签 + 编号文字
        id_row = QHBoxLayout()
        id_row.setSpacing(6)
        id_tag = QLabel("\u00C9")
        id_tag.setStyleSheet("""
            background: #f1f5f9;
            color: #64748b;
            font-size: 11px;
            font-weight: bold;
            padding: 1px 5px;
            border-radius: 3px;
        """)
        id_row.addWidget(id_tag)

        self._id_lbl = QLabel(self._record.get("id", "-"))
        self._id_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        id_row.addWidget(self._id_lbl)
        id_row.addStretch()
        layout.addLayout(id_row)

        # 第二行：标题（核心信息）
        title = QLabel(self._record.get("title", "未命名"))
        title.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px;")
        title.setWordWrap(True)
        layout.addWidget(title)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet("""
                QFrame#ApprovalListItem {
                    background: #f0f9ff;
                    border: 2px solid #00bfff;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#ApprovalListItem {
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                }
                QFrame#ApprovalListItem:hover {
                    background: #f8fafc;
                    border: 1px solid #cbd5e1;
                }
            """)


# ============================================================
#  决策信息输入页容器（拦截点击以失活滑块）
# ============================================================
class _DecisionPageWidget(QWidget):
    """
    决策输入页的容器 widget，点击非滑块区域时自动将所有打分滑块设为失活状态。
    """

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine

    def mousePressEvent(self, event):
        # 点击决策页任意非滑块区域 → 失活所有滑块
        if isinstance(self._engine, DecisionEngineWidget):
            self._engine.deactivate_all_sliders()
        super().mousePressEvent(event)


# ============================================================
#  子组件：决策引擎（决策信息输入 / 全生命周期日志 双标签页）
# ============================================================
class DecisionEngineWidget(QFrame):
    """
    参考工程风格的双标签页容器。

    Tab 1 — 决策信息输入：
      - 多维打分（法务合规分、总编终审分）QSlider
      - 评审意见文本框（多行）
      - 选择会签（checkbox）
      - 总编辑评分（checkbox）
      - 「执行决策提交分析」深色按钮

    Tab 2 — 全生命周期日志：
      - 时间线式流转记录
    """

    decision_submitted = pyqtSignal(str, bool, int, int)  # (comment, is_approve, legal_score, editor_score)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DecisionEngineWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("WorkflowTabs")

        # ========== 决策信息输入页 ==========
        self._decision_page = _DecisionPageWidget(self)
        dec_layout = QVBoxLayout(self._decision_page)
        dec_layout.setContentsMargins(16, 16, 16, 16)
        dec_layout.setSpacing(14)

        # 评审意见输入区
        self._comment_input = QTextEdit()
        self._comment_input.setPlaceholderText(
            "填写您的评审意见..."
        )
        self._comment_input.setMinimumHeight(70)
        self._comment_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                color: #334155;
                background: #ffffff;
            }
            QTextEdit:focus { border-color: #00bfff; }
        """)
        dec_layout.addWidget(self._comment_input)

        # ---- 多维打分（参考工程：法务合规分 + 总编终审分）----
        score_header = QLabel("请针对该内容进行多维打分（0-100）：")
        score_header.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
        dec_layout.addWidget(score_header)

        self._legal_score = self._build_score_slider("法务合规分")
        self._editor_score = self._build_score_slider("总编终审分")
        dec_layout.addLayout(self._legal_score["layout"])
        dec_layout.addLayout(self._editor_score["layout"])

        # ---- 快捷评语（2行×3列网格布局）----
        qc_header = QHBoxLayout()
        qc_label = QLabel("快捷评语")
        qc_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
        qc_header.addWidget(qc_label)
        qc_header.addStretch()
        dec_layout.addLayout(qc_header)

        qc_grid_widget = QWidget()
        qc_grid_widget.setMinimumHeight(62)
        qc_grid = QGridLayout(qc_grid_widget)
        qc_grid.setContentsMargins(0, 0, 0, 0)
        qc_grid.setHorizontalSpacing(6)
        qc_grid.setVerticalSpacing(4)
        # 三列等宽
        qc_grid.setColumnStretch(0, 1)
        qc_grid.setColumnStretch(1, 1)
        qc_grid.setColumnStretch(2, 1)

        quick_comments = [
            ("同意", "材料齐全", "agree"),
            ("同意", "符合规范", "agree"),
            ("同意", "加快执行", "agree"),
            ("需补材料", "后复议", "rework"),
            ("超预算", "建议调整", "rework"),
            ("驳回", "不符合标准", "reject"),
        ]
        for idx, (line1, line2, kind) in enumerate(quick_comments):
            btn = QPushButton(f"{line1}，{line2}")
            btn.setMinimumHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if kind == "agree":
                btn.setStyleSheet("""
                    QPushButton {
                        background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0;
                        border-radius: 5px; padding: 2px 6px; font-size: 11px;
                    }
                    QPushButton:hover { background: #dcfce7; border-color: #86efac; }
                """)
            elif kind == "reject":
                btn.setStyleSheet("""
                    QPushButton {
                        background: #fef2f2; color: #991b1b; border: 1px solid #fecaca;
                        border-radius: 5px; padding: 2px 6px; font-size: 11px;
                    }
                    QPushButton:hover { background: #fee2e2; border-color: #fca5a5; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #fffbeb; color: #92400e; border: 1px solid #fde68a;
                        border-radius: 5px; padding: 2px 6px; font-size: 11px;
                    }
                    QPushButton:hover { background: #fef3c7; border-color: #fcd34d; }
                """)
            btn.clicked.connect(lambda checked=False, t=f"{line1}，{line2}": (self.deactivate_all_sliders(), self._insert_quick_comment(t)))
            row, col = divmod(idx, 3)
            qc_grid.addWidget(btn, row, col)

        dec_layout.addWidget(qc_grid_widget)

        # 勾选项行
        check_row = QHBoxLayout()
        check_row.setSpacing(24)

        self._chk_countersign = QCheckBox("选择会签")
        self._chk_countersign.setStyleSheet("font-size: 13px; color: #475569;")
        check_row.addWidget(self._chk_countersign)

        self._chk_editor_score = QCheckBox("总编辑评分")
        self._chk_editor_score.setStyleSheet("font-size: 13px; color: #475569;")
        check_row.addWidget(self._chk_editor_score)

        check_row.addStretch()
        dec_layout.addLayout(check_row)

        # 提交分析按钮（深色宽按钮，参考工程风格）
        self._submit_btn = QPushButton("执行决策提交分析")
        self._submit_btn.setObjectName("DecisionSubmitButton")
        self._submit_btn.setFixedHeight(44)
        self._submit_btn.setStyleSheet("""
            QPushButton#DecisionSubmitButton {
                background: #1e293b;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton#DecisionSubmitButton:hover { background: #334155; }
            QPushButton#DecisionSubmitButton:pressed { background: #0f172a; }
            QPushButton#DecisionSubmitButton:disabled { background: #94a3b8; }
        """)
        self._submit_btn.clicked.connect(lambda: (self.deactivate_all_sliders(), self._on_submit()))
        dec_layout.addWidget(self._submit_btn)

        # 分析结果展示
        self._result_lbl = QLabel("")
        self._result_lbl.setWordWrap(True)
        self._result_lbl.setStyleSheet(
            "color: #475569; font-size: 12px; padding: 10px; "
            "background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;"
        )
        self._result_lbl.setVisible(False)
        dec_layout.addWidget(self._result_lbl)

        self._tabs.addTab(self._decision_page, "决策权重输入")

        # 点击评审意见框等非滑块区域时，失活所有打分滑块
        self._comment_input.installEventFilter(self)

        # ========== 全生命周期日志页 ==========
        self._log_page = QWidget()
        log_layout = QVBoxLayout(self._log_page)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(0)

        self._log_area = QScrollArea()
        self._log_area.setWidgetResizable(True)
        self._log_area.setFrameShape(QFrame.Shape.NoFrame)
        self._log_container = QWidget()
        self._log_layout = QVBoxLayout(self._log_container)
        self._log_layout.setContentsMargins(0, 0, 0, 0)
        self._log_layout.setSpacing(0)
        self._log_layout.addStretch()
        self._log_area.setWidget(self._log_container)
        log_layout.addWidget(self._log_area)

        self._tabs.addTab(self._log_page, "全生命期日志")

        layout.addWidget(self._tabs)

    def set_history(self, history: list):
        """刷新全生命周期日志时间线"""
        while self._log_layout.count() > 1:
            item = self._log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        if not history:
            empty = QLabel("暂无流转记录")
            empty.setStyleSheet("color: #94a3b8; padding: 20px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._log_layout.insertWidget(0, empty)
            return

        for idx, h in enumerate(history):
            self._log_layout.insertLayout(0, self._build_log_item(h, is_last=(idx == 0)))

    def _build_log_item(self, h: dict, is_last: bool) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        ts = time.strftime("%m-%d\n%H:%M", time.localtime(h.get("time", 0)))
        time_lbl = QLabel(ts)
        time_lbl.setStyleSheet("color: #64748b; font-size: 11px; text-align: center;")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_lbl.setFixedWidth(50)
        row.addWidget(time_lbl)

        axis = QVBoxLayout()
        axis.setSpacing(0)
        axis.setContentsMargins(0, 0, 0, 0)

        dot = QFrame()
        dot.setFixedSize(10, 10)
        action = h.get("action", "")
        color = "#38a169" if action == "通过" else "#e53e3e" if action == "驳回" else "#94a3b8"
        dot.setStyleSheet(f"background: {color}; border-radius: 5px;")
        axis.addWidget(dot, alignment=Qt.AlignmentFlag.AlignHCenter)

        if not is_last:
            line = QFrame()
            line.setFixedWidth(2)
            line.setStyleSheet("background: #e2e8f0;")
            axis.addWidget(line, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        else:
            axis.addStretch()
        row.addLayout(axis)

        content = QVBoxLayout()
        content.setSpacing(4)
        header = QHBoxLayout()
        node_lbl = QLabel(f"{h.get('node', '-')}")
        node_lbl.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 12px;")
        header.addWidget(node_lbl)
        action_lbl = QLabel(f"\u00B7 {action}")
        action_lbl.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
        header.addWidget(action_lbl)
        approver_lbl = QLabel(f"审批人：{h.get('approver', '-')}")
        approver_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        header.addWidget(approver_lbl)
        header.addStretch()
        content.addLayout(header)

        comment = h.get("comment", "")
        if comment:
            comment_lbl = QLabel(f"意见：{comment}")
            comment_lbl.setStyleSheet("color: #475569; font-size: 12px; padding-bottom: 8px;")
            comment_lbl.setWordWrap(True)
            content.addWidget(comment_lbl)
        row.addLayout(content, 1)
        return row

    def _insert_quick_comment(self, text: str):
        """快速插入常用评语到输入框"""
        current = self._comment_input.toPlainText().strip()
        if current:
            self._comment_input.setPlainText(f"{current}\n{text}")
        else:
            self._comment_input.setPlainText(text)
        # 移光标到末尾
        cursor = self._comment_input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._comment_input.setTextCursor(cursor)
        self._comment_input.setFocus()

    def _build_score_slider(self, title: str) -> dict:
        """构建参考工程风格的打分滑块行：标签 + 防误触滑块 + 数值"""
        row = QHBoxLayout()
        row.setSpacing(10)

        lbl = QLabel(title + "：")
        lbl.setStyleSheet("color: #475569; font-size: 12px; font-weight: 500; min-width: 70px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl)

        # 使用防误触滑块：必须点击激活后才能拖动/滚轮调整
        slider = ClickToActivateSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(70)
        slider.setFixedHeight(22)
        row.addWidget(slider, 1)

        val_lbl = QLabel("70")
        val_lbl.setStyleSheet("color: #0ea5e9; font-size: 12px; font-weight: 600; min-width: 28px;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda v: val_lbl.setText(str(v)))
        row.addWidget(val_lbl)

        return {"layout": row, "slider": slider, "label": val_lbl}

    def deactivate_all_sliders(self):
        """点击决策页其他区域时，将所有打分滑块设为失活状态"""
        if hasattr(self, "_legal_score") and isinstance(self._legal_score.get("slider"), ClickToActivateSlider):
            self._legal_score["slider"].deactivate()
        if hasattr(self, "_editor_score") and isinstance(self._editor_score.get("slider"), ClickToActivateSlider):
            self._editor_score["slider"].deactivate()

    def eventFilter(self, obj, event):
        """拦截评审意见框等子控件的 focus-in 事件，自动失活滑块"""
        if event.type() == event.Type.FocusIn:
            self.deactivate_all_sliders()
        return super().eventFilter(obj, event)

    def _on_submit(self):
        """执行决策提交分析（模拟多维度推演）"""
        comment = self._comment_input.toPlainText().strip()
        if not comment:
            self._result_lbl.setText("<span style='color:#e53e3e;'>请先填写评审意见</span>")
            self._result_lbl.setVisible(True)
            return

        legal_score = self._legal_score["slider"].value()
        editor_score = self._editor_score["slider"].value()

        # 模拟引擎分析：综合滑块分数 + 会签/总编复核 + 意见长度
        countersign_bonus = 5 if self._chk_countersign.isChecked() else 0
        editor_bonus = 8 if self._chk_editor_score.isChecked() else 0
        length_factor = min(len(comment) / 50, 1.0) * 10  # 意见越长越认真

        # 综合得分：法务合规 40% + 总编终审 40% + 附加权重 20%
        weighted = (legal_score * 0.4 + editor_score * 0.4
                    + countersign_bonus + editor_bonus + length_factor)
        score = min(100, max(0, int(weighted)))

        if score >= 85:
            conclusion = "强烈推荐通过"
            color = "#38a169"
        elif score >= 70:
            conclusion = "建议通过，需关注弱项"
            color = "#00bfff"
        elif score >= 55:
            conclusion = "建议补充材料后复议"
            color = "#d97706"
        else:
            conclusion = "建议驳回"
            color = "#e53e3e"

        extras = []
        if self._chk_countersign.isChecked():
            extras.append("已启用会签机制")
        if self._chk_editor_score.isChecked():
            extras.append("已触发总编复核权重")
        extra_str = " | ".join(extras) if extras else "标准审批路径"

        self._result_lbl.setText(
            f"<b style='color:{color};font-size:14px;'>{conclusion}</b><br>"
            f"综合评估得分：<b>{score}</b> / 100<br>"
            f"法务合规分：<b>{legal_score}</b> | 总编终审分：<b>{editor_score}</b><br>"
            f"附加策略：{extra_str}<br>"
            f"评审意见字数：{len(comment)}"
        )
        self._result_lbl.setVisible(True)

        # 参照工程：提交分析结果后，弹出确认弹窗让用户最终确认执行
        action = "通过" if score >= 55 else "驳回"
        confirm = ConfirmDecisionDialog(action, self.parent().parent()._detail_title.text() if hasattr(self.parent(), 'parent') and self.parent().parent() else "当前审批单", self)
        if confirm.exec() != QDialog.DialogCode.Accepted:
            return  # 用户取消 → 不执行

        # 发出信号给主模块做实际审批操作
        self.decision_submitted.emit(comment, score >= 55, legal_score, editor_score)

    def reset_decision(self):
        """切换选中记录时重置决策输入状态"""
        self._comment_input.clear()
        self._legal_score["slider"].setValue(70)
        self._editor_score["slider"].setValue(70)
        self.deactivate_all_sliders()
        self._chk_countersign.setChecked(False)
        self._chk_editor_score.setChecked(False)
        self._result_lbl.setVisible(False)

    def set_enabled(self, enabled: bool):
        """设置决策输入区的可用状态（非待审批时禁用）"""
        self._comment_input.setEnabled(enabled)
        self._legal_score["slider"].setEnabled(enabled)
        self._editor_score["slider"].setEnabled(enabled)
        self._chk_countersign.setEnabled(enabled)
        self._chk_editor_score.setEnabled(enabled)
        self._submit_btn.setEnabled(enabled)
        if not enabled:
            self._comment_input.setPlaceholderText("该审批单已结束，不可编辑")
            self.deactivate_all_sliders()


# ============================================================
#  审批决策确认弹窗（参照工程风格：问号图标 + 存证提示）
# ============================================================
class ConfirmDecisionDialog(QDialog):
    """
    参照工程风格的审批决策确认弹窗。
    - 大号问号图标
    - 「您确定要执行 [通过/驳回] 决策吗？」
    - 副提示：「该操作将记录在区块链存证日志中且不可更改。」
    - No（描边）+ Yes（实心主题色）按钮
    """

    def __init__(self, action: str, title: str, parent=None):
        """
        :param action: "通过" 或 "驳回"
        :param title: 审批单标题，用于确认文案中
        """
        super().__init__(parent)
        self._action = action
        self.setWindowTitle("决策确认")
        self.setFixedSize(420, 220)
        self.setObjectName("ConfirmDecisionDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        # ---- 上半区：图标 + 文字 ----
        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        # 大号问号图标
        icon_lbl = QLabel("?")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedSize(48, 48)
        is_pass = (action == "通过")
        icon_color = "#22c55e" if is_pass else "#ef4444"
        bg_color = "#dcfce7" if is_pass else "#fef2f2"
        icon_lbl.setStyleSheet(
            f"background: {bg_color}; color: {icon_color}; font-size: 28px; "
            f"font-weight: 700; border-radius: 24px; border: 2px solid {icon_color};"
        )
        top_row.addWidget(icon_lbl)

        # 右侧文字
        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        main_text = QLabel(f"您确定要执行「{action}」决策吗？")
        main_text.setStyleSheet("font-size: 15px; font-weight: 600; color: #1e293b;")
        text_col.addWidget(main_text)

        sub_text = QLabel("该操作将记录在区块链存证日志中且不可更改。")
        sub_text.setStyleSheet("font-size: 12px; color: #94a3b8;")
        sub_text.setWordWrap(True)
        text_col.addWidget(sub_text)

        top_row.addLayout(text_col, 1)
        layout.addLayout(top_row)

        layout.addSpacing(12)

        # ---- 按钮行 ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_no = QPushButton("No")
        btn_no.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_no.setFixedHeight(40)
        btn_no.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1.5px solid #cbd5e1;
                border-radius: 8px; color: #64748b;
                font-weight: 600; font-size: 14px;
            }
            QPushButton:hover {
                background: #f8fafc; border-color: #94a3b8; color: #334155;
            }
            QPushButton:pressed { background: #f1f5f9; }
        """)
        btn_no.clicked.connect(self.reject)
        btn_row.addWidget(btn_no, 1)

        btn_yes = QPushButton("Yes")
        btn_yes.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_yes.setFixedHeight(40)
        yes_bg = "#22c55e" if is_pass else "#ef4444"
        yes_hover = "#16a34a" if is_pass else "#dc2626"
        btn_yes.setStyleSheet(f"""
            QPushButton {{
                background: {yes_bg}; border: none;
                border-radius: 8px; color: white;
                font-weight: 600; font-size: 14px;
            }}
            QPushButton:hover {{ background: {yes_hover}; }}
            QPushButton:pressed {{ background: {yes_hover}; opacity: 0.85; }}
        """)
        btn_yes.clicked.connect(self.accept)
        btn_row.addWidget(btn_yes, 1)

        layout.addLayout(btn_row)


# ============================================================
#  新增审批申请弹窗
# ============================================================
class NewApprovalDialog(QDialog):
    """新增审批申请弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增审批申请")
        self.setMinimumSize(460, 420)
        self.setObjectName("TechDialog")

        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("请输入审批标题")
        layout.addRow("审批标题", self.title_input)

        self.applicant_input = QLineEdit()
        self.applicant_input.setPlaceholderText("申请人姓名")
        layout.addRow("申请人", self.applicant_input)

        self.type_input = QComboBox()
        self.type_input.addItems([
            "内容发布", "版权授权", "预算申请", "商务合作",
            "内容制作", "营销推广", "物资采购", "产品开发"
        ])
        layout.addRow("审批类型", self.type_input)

        self.urgency_input = QComboBox()
        self.urgency_input.addItems(["常规", "紧急", "特急"])
        layout.addRow("紧急程度", self.urgency_input)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("金额（元）")
        layout.addRow("涉及金额", self.amount_input)

        self.template_input = QComboBox()
        self.template_input.addItem("请选择模板")
        for t in db._approval_templates:
            self.template_input.addItem(t["name"])
        self.template_input.currentTextChanged.connect(self._on_template_changed)
        layout.addRow("审批模板", self.template_input)

        self._preview_label = QLabel("节点预览：-")
        self._preview_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 4px 0;")
        self._preview_label.setWordWrap(True)
        layout.addRow(self._preview_label)

        self.type_input.currentTextChanged.connect(self._auto_select_template)

        self.reason_input = QTextEdit()
        self.reason_input.setPlaceholderText("请输入申请理由...")
        self.reason_input.setMaximumHeight(100)
        layout.addRow("申请理由", self.reason_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("提交申请")
        self.btn_ok.setObjectName("PrimaryButton")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setObjectName("CancelButton")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addRow(btn_layout)

        self._auto_select_template(self.type_input.currentText())

    def _auto_select_template(self, record_type: str):
        mapping = {
            "内容发布": "标准内容发布审批",
            "版权授权": "版权授权快速通道",
            "预算申请": "大额采购审批",
            "商务合作": "大额采购审批",
            "物资采购": "大额采购审批",
            "产品开发": "大额采购审批",
        }
        target = mapping.get(record_type, "")
        if target:
            idx = self.template_input.findText(target)
            if idx >= 0:
                self.template_input.setCurrentIndex(idx)

    def _on_template_changed(self, name: str):
        for t in db._approval_templates:
            if t["name"] == name:
                nodes = []
                for nid in t["nodes"]:
                    idx = int(nid.replace("WF", "")) - 1
                    if 0 <= idx < len(db.get_workflow_nodes()):
                        nodes.append(db.get_workflow_nodes()[idx]["name"])
                self._preview_label.setText("节点预览：" + " \u2192 ".join(nodes) if nodes else "节点预览：-")
                return
        self._preview_label.setText("节点预览：-")

    def get_data(self):
        return {
            "title": self.title_input.text().strip(),
            "applicant": self.applicant_input.text().strip(),
            "type": self.type_input.currentText(),
            "urgency": self.urgency_input.currentText(),
            "amount": float(self.amount_input.text().strip() or 0),
            "reason": self.reason_input.toPlainText().strip(),
            "template": self.template_input.currentText(),
        }


# ============================================================
#  主模块
# ============================================================
class WorkflowModule(BaseBusinessModule):
    """
    流程审批主模块（参考工程 V2 风格）

    布局结构：
      QSplitter(H)
       ├─ 左侧面板：工具栏 + 统计 + 紧凑卡片列表 + 批量操作
       └─ 右侧面板：大标题 + 流程图 + [上下文|风险扫描] + 决策标签页
    """

    def __init__(self):
        # 数据属性必须在 super().__init__() 之前初始化，
        # 因为基类构造期即调用 setup_ui() -> _refresh_all() -> _refresh_card_list()
        self._current_role = "总监"
        self._selected_record = None
        self._search_keyword = ""
        self._status_filter_value = ""
        self._card_widgets = []
        super().__init__("流程审批")

    def setup_ui(self):
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # ====== 主分割器 ======
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ==================== 左侧面板 ====================
        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        title_lbl = QLabel("审批任务")
        title_lbl.setObjectName("SectionLabel")
        toolbar.addWidget(title_lbl)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索编号、标题、申请人...")
        self._search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self._search_input, 1)

        self._status_filter = QComboBox()
        self._status_filter.addItems(["全部", "待审批", "已通过", "已驳回"])
        self._status_filter.currentTextChanged.connect(self._on_status_changed)
        toolbar.addWidget(self._status_filter)

        self._btn_new = QPushButton("新增申请")
        self._btn_new.setObjectName("PrimaryButton")
        self._btn_new.clicked.connect(self._open_new_approval)
        toolbar.addWidget(self._btn_new)
        left_layout.addLayout(toolbar)

        # 统计摘要条
        stat_bar = QHBoxLayout()
        stat_bar.setSpacing(10)
        self._stat_total = QLabel("全部：0")
        self._stat_pending = QLabel("待审批：0")
        self._stat_approved = QLabel("已通过：0")
        self._stat_rejected = QLabel("已驳回：0")
        for lbl in [self._stat_total, self._stat_pending, self._stat_approved, self._stat_rejected]:
            lbl.setStyleSheet("color: #64748b; font-size: 12px;")
            stat_bar.addWidget(lbl)
        stat_bar.addStretch()
        left_layout.addLayout(stat_bar)

        # 紧凑卡片列表
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._list_container)
        left_layout.addWidget(self._scroll, 1)

        # 底部批量操作栏
        batch_bar = QHBoxLayout()
        self._btn_batch_approve = QPushButton("批量通过")
        self._btn_batch_approve.setObjectName("SuccessButton")
        self._btn_batch_approve.clicked.connect(self._batch_approve)
        batch_bar.addWidget(self._btn_batch_approve)

        self._btn_batch_reject = QPushButton("批量驳回")
        self._btn_batch_reject.setObjectName("DangerButton")
        self._btn_batch_reject.clicked.connect(self._batch_reject)
        batch_bar.addWidget(self._btn_batch_reject)

        self._btn_export = QPushButton("导出列表")
        self._btn_export.setObjectName("PrimaryButton")
        self._btn_export.clicked.connect(self._export_records)
        batch_bar.addWidget(self._btn_export)
        batch_bar.addStretch()
        left_layout.addLayout(batch_bar)

        splitter.addWidget(left_panel)

        # ==================== 右侧面板（整体可滚动） ====================
        # 标准做法：外层 QScrollArea 包裹全部内容，窗口不够大时整体滚动
        self._right_scroll = ClickToScrollArea()
        self._right_scroll.setWidgetResizable(True)
        self._right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 点击后才响应滚轮，避免鼠标悬停误触
        self._right_scroll.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(24, 20, 24, 24)
        right_layout.setSpacing(14)

        # 大标题
        self._detail_title = QLabel("请选择审批单查看详情")
        self._detail_title.setObjectName("SectionLabel")
        self._detail_title.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #0f172a;"
        )
        right_layout.addWidget(self._detail_title)

        # 圆形流程进度图
        self._flow_chart = CircleWorkflowChart()
        self._flow_chart.node_clicked.connect(self._on_flow_node_clicked)
        right_layout.addWidget(self._flow_chart)

        # ---- 当前节点信息条（新增功能：显示当前处理人/等待时间/催办）----
        self._current_node_bar = QFrame()
        self._current_node_bar.setObjectName("CurrentNodeBar")
        self._current_node_bar.setStyleSheet("""
            QFrame#CurrentNodeBar {
                background: #f0f9ff;
                border: 1px solid #bae6fd;
                border-radius: 8px;
            }
        """)
        cnb_layout = QHBoxLayout(self._current_node_bar)
        cnb_layout.setContentsMargins(14, 8, 14, 8)
        cnb_layout.setSpacing(12)

        self._cnb_label = QLabel("当前节点：-  |  处理人：-  |  已等待：-")
        self._cnb_label.setStyleSheet("color: #0369a1; font-size: 12px; font-weight: 500;")
        cnb_layout.addWidget(self._cnb_label)
        cnb_layout.addStretch()

        self._btn_urge = QPushButton("催办")
        self._btn_urge.setFixedHeight(28)
        self._btn_urge.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_urge.setStyleSheet("""
            QPushButton {
                background: #0ea5e9; color: white; border: none;
                border-radius: 4px; padding: 2px 12px; font-size: 12px;
            }
            QPushButton:hover { background: #0284c7; }
            QPushButton:disabled { background: #94a3b8; }
        """)
        self._btn_urge.clicked.connect(self._on_urge)
        cnb_layout.addWidget(self._btn_urge)
        self._current_node_bar.setVisible(False)
        right_layout.addWidget(self._current_node_bar)

        # 双栏：基础上下文（左） | AI 风险扫描（右）
        # 用水平 QHBoxLayout + 固定高度容器，杜绝溢出/重叠/挤压
        self._info_container = QFrame()
        self._info_container.setObjectName("InfoContainer")
        self._info_container.setStyleSheet("""
            QFrame#InfoContainer {
                background: transparent;
                border: none;
            }
        """)
        info_layout = QHBoxLayout(self._info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)

        # --- 基础上下文卡片（左半）---
        ctx_card = QFrame()
        ctx_card.setObjectName("ContextCard")
        ctx_card.setFrameShape(QFrame.Shape.StyledPanel)
        ctx_card.setStyleSheet("""
            QFrame#ContextCard {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)
        ctx_inner = QVBoxLayout(ctx_card)
        ctx_inner.setContentsMargins(12, 10, 12, 10)
        ctx_inner.setSpacing(4)

        ctx_header = QLabel("基础上下文")
        ctx_header.setStyleSheet("font-weight: 600; font-size: 13px; color: #1e293b;")
        ctx_inner.addWidget(ctx_header)

        # 用 2列 QGridLayout 实现 key-value 紧凑布局
        ctx_grid = QGridLayout()
        ctx_grid.setSpacing(6)
        ctx_grid.setContentsMargins(0, 2, 0, 0)
        ctx_grid.setColumnStretch(0, 0)
        ctx_grid.setColumnStretch(1, 1)
        ctx_grid.setColumnStretch(2, 0)
        ctx_grid.setColumnStretch(3, 1)
        label_style = "color: #94a3b8; font-size: 11px; background: transparent;"
        value_style = "color: #334155; font-size: 12px; font-weight: 500; background: transparent;"

        self._ctx_id = QLabel("-")
        self._ctx_applicant = QLabel("-")
        self._ctx_type = QLabel("-")
        self._ctx_amount = QLabel("-")
        self._ctx_urgency = QLabel("-")
        self._ctx_reason = QLabel("-")
        self._ctx_time = QLabel("-")

        fields = [
            ("任务编号", self._ctx_id),
            ("申请人", self._ctx_applicant),
            ("紧急程度", self._ctx_urgency),
        ]

        # 参照工程风格：上下文只显示3个核心字段，简洁紧凑
        for idx, (key_lbl_text, val_widget) in enumerate(fields):
            row = idx
            key_lbl = QLabel(key_lbl_text + "：")
            key_lbl.setStyleSheet(label_style)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_widget.setStyleSheet(value_style)
            val_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            ctx_grid.addWidget(key_lbl, row, 0)
            ctx_grid.addWidget(val_widget, row, 1)

        # 隐藏未使用的字段（保留数据绑定供详情弹窗使用）
        self._ctx_type.hide()
        self._ctx_amount.hide()
        self._ctx_reason.hide()
        self._ctx_time.hide()

        ctx_inner.addLayout(ctx_grid)

        ctx_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        info_layout.addWidget(ctx_card, 1)

        # --- AI 智能风险扫描（右半）---
        self._risk_scan = RiskScanWidget()
        self._risk_scan.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        info_layout.addWidget(self._risk_scan, 1)

        right_layout.addWidget(self._info_container)

        # ---- 终审操作栏（参照工程：退回修订 / 准予发布）----
        self._quick_action_bar = QFrame()
        qab_layout = QHBoxLayout(self._quick_action_bar)
        qab_layout.setContentsMargins(0, 0, 0, 0)
        qab_layout.setSpacing(12)

        self._btn_quick_reject = QPushButton("退回修订 (Return)")
        self._btn_quick_reject.setFixedHeight(44)
        self._btn_quick_reject.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_quick_reject.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f87171, stop:1 #ef4444);
                color: white; border: none;
                border-radius: 8px; font-weight: 600; font-size: 14px;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
            }
            QPushButton:pressed { background: #b91c1c; }
            QPushButton:disabled { background: #e5e7eb; color: #9ca3af; }
        """)
        self._btn_quick_reject.clicked.connect(self._on_quick_reject)
        qab_layout.addWidget(self._btn_quick_reject, 1)

        self._btn_quick_approve = QPushButton("准予发布 (Final Pass)")
        self._btn_quick_approve.setFixedHeight(44)
        self._btn_quick_approve.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_quick_approve.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4ade80, stop:1 #22c55e);
                color: white; border: none;
                border-radius: 8px; font-weight: 600; font-size: 14px;
                padding: 4px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #22c55e, stop:1 #15803d);
            }
            QPushButton:pressed { background: #15803d; }
            QPushButton:disabled { background: #e5e7eb; color: #9ca3af; }
        """)
        self._btn_quick_approve.clicked.connect(self._on_quick_approve)
        qab_layout.addWidget(self._btn_quick_approve, 1)

        self._quick_action_bar.setVisible(False)
        right_layout.addWidget(self._quick_action_bar)

        # 决策引擎（双标签页）
        self._decision_engine = DecisionEngineWidget()
        self._decision_engine.decision_submitted.connect(self._on_decision_submitted)
        right_layout.addWidget(self._decision_engine)

        # ---- 发布置信度指数展示区（参照工程：决策区外独立卡片）----
        self._confidence_card = QFrame()
        self._confidence_card.setObjectName("ConfidenceCard")
        self._confidence_card.setStyleSheet("""
            QFrame#ConfidenceCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ecfeff, stop:1 #f0fdfa);
                border: 1px solid #99f6e4;
                border-radius: 10px;
            }
        """)
        cc_layout = QVBoxLayout(self._confidence_card)
        cc_layout.setContentsMargins(18, 14, 18, 14)

        self._confidence_label = QLabel("")
        self._confidence_label.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #dc2626;"
        )
        self._confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cc_layout.addWidget(self._confidence_label)

        # 默认隐藏，提交分析后才显示
        self._confidence_card.setVisible(False)
        right_layout.addWidget(self._confidence_card)

        # 底部留白，避免滚动到底部时内容贴边
        right_layout.addSpacing(16)

        self._right_scroll.setWidget(right_content)
        splitter.addWidget(self._right_scroll)
        splitter.setSizes([340, 820])
        self.layout.addWidget(splitter, 1)

        self._refresh_all()

    # ================================================================
    #  数据刷新
    # ================================================================
    def _refresh_all(self):
        self._refresh_stats()
        self._refresh_card_list()

    def _filtered_records(self):
        records = db.get_approval_records(self._status_filter_value)
        if self._search_keyword:
            records = [
                r for r in records
                if (self._search_keyword in r.get("id", "").lower()
                    or self._search_keyword in r.get("title", "").lower()
                    or self._search_keyword in r.get("applicant", "").lower()
                    or self._search_keyword in r.get("type", "").lower())
            ]
        return records

    def _refresh_stats(self):
        stats = db.get_approval_stats()
        self._stat_total.setText(f"全部：{stats['total']}")
        self._stat_pending.setText(f"待审批：{stats['pending']}")
        self._stat_approved.setText(f"已通过：{stats['approved']}")
        self._stat_rejected.setText(f"已驳回：{stats['rejected']}")

    def _refresh_card_list(self):
        for card in self._card_widgets:
            card.deleteLater()
        self._card_widgets.clear()

        records = self._filtered_records()
        for idx, rec in enumerate(records):
            card = ApprovalListItem(idx, rec)
            card.clicked.connect(self._on_card_clicked)
            self._card_widgets.append(card)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        # 默认选中第一条
        if records:
            self._selected_record = records[0]
            self._card_widgets[0].set_selected(True)
            self._show_record_detail(records[0])
        else:
            self._selected_record = None
            self._reset_detail()

    def _on_card_clicked(self, index: int):
        for i, card in enumerate(self._card_widgets):
            card.set_selected(i == index)
        records = self._filtered_records()
        if 0 <= index < len(records):
            self._selected_record = records[index]
            self._show_record_detail(records[index])

    def _on_search_changed(self, text: str):
        self._search_keyword = text.strip().lower()
        self._refresh_card_list()

    def _on_status_changed(self, text: str):
        status_map = {"全部": "", "待审批": "pending", "已通过": "approved", "已驳回": "rejected"}
        self._status_filter_value = status_map.get(text, "")
        self._refresh_card_list()

    # ================================================================
    #  详情展示
    # ================================================================
    def _reset_detail(self):
        self._detail_title.setText("请选择审批单查看详情")
        self._flow_chart.set_flow([], 0, "pending")
        self._cnb_label.setText("当前节点：-  |  处理人：-  |  已等待：-")
        self._current_node_bar.setVisible(False)
        self._ctx_id.setText("-")
        self._ctx_applicant.setText("-")
        self._ctx_type.setText("-")
        self._ctx_amount.setText("-")
        self._ctx_urgency.setText("-")
        self._ctx_reason.setText("-")
        self._ctx_time.setText("-")
        self._risk_scan.analyze("", 0, "pending")
        self._quick_action_bar.setVisible(False)
        self._decision_engine.set_history([])
        self._decision_engine.reset_decision()
        self._decision_engine.set_enabled(False)
        self._confidence_card.setVisible(False)

    def _show_record_detail(self, rec: dict):
        nodes = db.get_workflow_nodes()
        self._detail_title.setText(rec.get("title", "未命名"))
        self._flow_chart.set_flow(nodes, rec.get("node_idx", 0), rec.get("status", "pending"))

        # ---- 当前节点信息条 ----
        status = rec.get("status", "pending")
        if status == "pending" and nodes:
            idx = rec.get("node_idx", 0)
            if idx < len(nodes):
                node = nodes[idx]
                handler = node.get("role", "-")
                # 计算等待时间（从 history 最后一条时间算起）
                history = rec.get("history", [])
                if history:
                    last_time = history[-1].get("time", 0)
                    wait_secs = max(0, int(time.time()) - int(last_time))
                    if wait_secs > 86400:
                        wait_text = f"{wait_secs // 86400}天"
                    elif wait_secs > 3600:
                        wait_text = f"{wait_secs // 3600}小时"
                    else:
                        wait_text = f"{wait_secs // 60}分钟"
                else:
                    wait_text = "刚提交"
                self._cnb_label.setText(
                    f"当前节点：{node.get('name', '-')}  |  处理人角色：{handler}  |  已等待：{wait_text}"
                )
                self._current_node_bar.setVisible(True)
                self._btn_urge.setEnabled(True)
            else:
                self._current_node_bar.setVisible(False)
        else:
            self._current_node_bar.setVisible(False)

        # ---- 上下文卡片增强 ----
        self._ctx_id.setText(rec.get('id', '-'))
        self._ctx_applicant.setText(rec.get('applicant', '-'))
        self._ctx_type.setText(rec.get('type', '-'))
        amount = rec.get("amount", 0)
        self._ctx_amount.setText(f"¥{amount:,.0f}" if amount else "-")
        self._ctx_urgency.setText(rec.get('urgency', '常规') or '常规')
        reason = rec.get('reason', '') or ''
        self._ctx_reason.setText(reason if reason else "未填写")
        created_ts = rec.get("created_at", 0)
        if isinstance(created_ts, (int, float)) and created_ts > 0:
            self._ctx_time.setText(time.strftime('%Y-%m-%d %H:%M', time.localtime(created_ts)))
        else:
            self._ctx_time.setText("-")

        self._risk_scan.analyze(rec.get("type", ""), rec.get("amount", 0), rec.get("status", "pending"))
        self._decision_engine.set_history(rec.get("history", []))
        self._decision_engine.reset_decision()

        # 切换记录时隐藏置信度卡片
        self._confidence_card.setVisible(False)

        enabled = status == "pending"
        self._decision_engine.set_enabled(enabled)
        # 快捷操作栏仅在待审批时显示
        self._quick_action_bar.setVisible(enabled)
        self._btn_quick_approve.setEnabled(enabled)
        self._btn_quick_reject.setEnabled(enabled)

    # ================================================================
    #  新增功能：流程图节点点击 / 催办 / 快速通过驳回
    # ================================================================
    def _on_flow_node_clicked(self, index: int):
        """点击流程图节点，弹出该节点详情"""
        nodes = db.get_workflow_nodes()
        if index < 0 or index >= len(nodes):
            return
        node = nodes[index]
        is_current = (index == self._selected_record.get("node_idx", -1)
                      if self._selected_record else False)
        status = self._selected_record.get("status", "pending") if self._selected_record else "pending"
        if status == "approved" or index < (self._selected_record.get("node_idx", 0) if self._selected_record else 0):
            node_status = "已通过"
        elif is_current and status == "pending":
            node_status = "进行中"
        elif status == "rejected" and is_current:
            node_status = "已驳回"
        else:
            node_status = "待处理"

        # 从 history 找该节点的审批记录
        approver = "—"
        approve_time = "—"
        comment = "—"
        if self._selected_record:
            for h in reversed(self._selected_record.get("history", [])):
                if h.get("node") == node.get("name"):
                    approver = h.get("approver", "—")
                    approve_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(h.get("time", 0)))
                    comment = h.get("comment", "—")
                    break

        info = (
            f"节点 {index + 1}：{node.get('name', '—')}\n"
            f"状态：{node_status}\n"
            f"要求角色：{node.get('role', '—')}\n"
            f"处理人：{approver}\n"
            f"处理时间：{approve_time}\n"
            f"审批意见：{comment}"
        )
        QMessageBox.information(self, "节点详情", info)

    def _on_urge(self):
        """催办当前节点处理人"""
        if not self._selected_record:
            return
        nodes = db.get_workflow_nodes()
        idx = self._selected_record.get("node_idx", 0)
        if idx < len(nodes):
            node = nodes[idx]
            role = node.get("role", "—")
            self._show_toast(f"已向「{role}」发送催办提醒\n（节点：{node.get('name', '—')}）")

    def _on_quick_approve(self):
        """快速通过（使用默认评语，跳过决策分析）"""
        if not self._selected_record:
            QMessageBox.warning(self, "提示", "请先选择审批单")
            return
        if not self._can_approve(self._selected_record):
            node_role = db.get_workflow_nodes()[self._selected_record["node_idx"]].get("role", "")
            QMessageBox.warning(self, "权限不足",
                                 f"当前节点需要角色「{node_role}」审批，您无权操作。")
            return
        dialog = ConfirmDecisionDialog("通过", self._selected_record.get("title", ""), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            db.approve_record(self._selected_record["id"], self._current_role, "同意")
            self._refresh_all()
            self._show_toast("已快速通过")

    def _on_quick_reject(self):
        """快速驳回"""
        if not self._selected_record:
            QMessageBox.warning(self, "提示", "请先选择审批单")
            return
        if not self._can_approve(self._selected_record):
            node_role = db.get_workflow_nodes()[self._selected_record["node_idx"]].get("role", "")
            QMessageBox.warning(self, "权限不足",
                                 f"当前节点需要角色「{node_role}」审批，您无权操作。")
            return
        # 第一步：输入驳回理由
        dialog = QDialog(self)
        dialog.setWindowTitle("快速驳回")
        dialog.setFixedSize(380, 200)
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setSpacing(10)
        lbl = QLabel("请输入驳回理由：")
        dlg_layout.addWidget(lbl)
        reason_input = QTextEdit()
        reason_input.setPlaceholderText("驳回理由...")
        dlg_layout.addWidget(reason_input)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dialog.reject)
        btn_ok = QPushButton("下一步")
        btn_ok.setStyleSheet("background: #0ea5e9; color: white; border: none; border-radius: 4px; padding: 6px 16px;")
        btn_ok.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        dlg_layout.addLayout(btn_row)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        reason = reason_input.toPlainText().strip() or "驳回"

        # 第二步：参照工程风格的确认弹窗
        confirm = ConfirmDecisionDialog("驳回", self._selected_record.get("title", ""), self)
        if confirm.exec() == QDialog.DialogCode.Accepted:
            db.reject_record(self._selected_record["id"], self._current_role, reason)
            self._refresh_all()
            self._show_toast("已驳回")

    # ================================================================
    #  权限校验 & 审批操作
    # ================================================================
    def _can_approve(self, rec: dict) -> bool:
        nodes = db.get_workflow_nodes()
        idx = rec.get("node_idx", 0)
        if idx >= len(nodes):
            return False
        required_role = nodes[idx].get("role", "")
        return self._current_role == "总监" or self._current_role == required_role

    def _on_decision_submitted(self, comment: str, recommend_pass: bool, legal_score: int, editor_score: int):
        """决策标签页提交分析后的回调——执行真实审批动作 + 显示置信度卡片"""
        if not self._selected_record:
            QMessageBox.warning(self, "提示", "请先选择审批单")
            return
        if not self._can_approve(self._selected_record):
            node_role = db.get_workflow_nodes()[self._selected_record["node_idx"]].get("role", "")
            QMessageBox.warning(self, "权限不足",
                                 f"当前节点需要角色「{node_role}」审批，您无权操作。")
            return

        rid = self._selected_record["id"]
        # 将评分记录到 history 中，便于后续审计
        score_note = f"法务合规分{legal_score} / 总编终审分{editor_score}"
        full_comment = f"{comment}\n[{score_note}]"

        # 计算置信度指数（参照工程风格：基于综合评分的百分比）
        weighted_score = legal_score * 0.4 + editor_score * 0.4
        length_factor = min(len(comment) / 50, 1.0) * 20
        total = min(100, max(0, int(weighted_score + length_factor)))
        confidence_pct = round(total * 0.0543 + (legal_score + editor_score) / 200 * 10, 2)
        confidence_color = "#dc2626" if confidence_pct < 60 else "#16a34a" if confidence_pct > 85 else "#d97706"
        status_text = "准予发布" if recommend_pass else "退回修订"

        # 显示外部置信度卡片（参照工程：决策区外独立展示）
        self._confidence_label.setText(
            f"{status_text}置信度指数：<span style='color:{confidence_color};font-size:18px;'>{confidence_pct}%</span>"
        )
        self._confidence_card.setVisible(True)

        if recommend_pass:
            db.approve_record(rid, self._current_role, full_comment)
        else:
            db.reject_record(rid, self._current_role, full_comment)

        self._refresh_all()
        records = self._filtered_records()
        for idx, r in enumerate(records):
            if r["id"] == rid:
                self._card_widgets[idx].set_selected(True)
                self._selected_record = r
                self._show_record_detail(r)
                break

    def _batch_approve(self):
        pending = [r for r in self._filtered_records() if r["status"] == "pending"]
        if not pending:
            QMessageBox.information(self, "提示", "当前列表没有待审批记录")
            return
        reply = QMessageBox.question(
            self, "批量通过",
            f"确定要批量通过 {len(pending)} 条待审批记录吗？\n将使用默认意见「同意」。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for r in pending:
            db.approve_record(r["id"], self._current_role, "批量通过")
        self._refresh_all()
        self._show_toast(f"已批量通过 {len(pending)} 条记录")

    def _batch_reject(self):
        pending = [r for r in self._filtered_records() if r["status"] == "pending"]
        if not pending:
            QMessageBox.information(self, "提示", "当前列表没有待审批记录")
            return
        reply = QMessageBox.question(
            self, "批量驳回",
            f"确定要批量驳回 {len(pending)} 条待审批记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for r in pending:
            db.reject_record(r["id"], self._current_role, "批量驳回")
        self._refresh_all()
        self._show_toast(f"已批量驳回 {len(pending)} 条记录")

    def _export_records(self):
        records = self._filtered_records()
        if not records:
            QMessageBox.information(self, "导出", "当前列表无数据")
            return
        lines = ["=" * 70]
        lines.append(" 流程审批导出报告 ")
        lines.append(f" 导出时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f" 共 {len(records)} 条记录")
        lines.append("-" * 70)
        for r in records:
            status_text = {"pending": "待审批", "approved": "已通过", "rejected": "已驳回"}.get(r["status"], r["status"])
            lines.append(
                f" {r['id']} | {r['title']:<20s} | {r['applicant']:<8s} | "
                f"{r['type']:<8s} | \u00A5{r['amount']:>10,.0f} | {status_text}"
            )
        lines.append("=" * 70)
        QMessageBox.information(self, "导出预览", "\n".join(lines))
        self._show_toast(f"已导出 {len(records)} 条审批记录")

    @staticmethod
    def _show_toast(message: str):
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("操作反馈")
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    # ================================================================
    #  新增申请
    # ================================================================
    def _open_new_approval(self):
        dlg = NewApprovalDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["title"] or not data["applicant"]:
            QMessageBox.warning(self, "提示", "标题和申请人为必填项")
            return
        db.create_approval(data)
        self._refresh_all()

    def cleanup(self):
        pass
