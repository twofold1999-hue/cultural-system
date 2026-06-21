"""
通用 UI 组件
===========
被 dashboard 等多个模块复用的图表和控制台组件。
"""

import math
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QProgressBar, QTextEdit, QStyledItemDelegate,
    QWidget, QSizePolicy, QStyleOptionViewItem, QStyle,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QSize
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor,
    QFont, QLinearGradient, QRadialGradient, QPolygonF, QTextOption,
    QTextDocument
)
from database.mock_db import db


RADAR_LABELS = ["内容深度", "传播广度", "受众精准度", "技术融合度", "商业转化率"]
RADAR_AXIS_COUNT = len(RADAR_LABELS)


class RadarChartWidget(QWidget):
    """内容维度分析雷达图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RadarChartWidget")
        self.setMinimumHeight(220)
        self._values = [60, 75, 55, 80, 65]

    def set_values(self, values):
        self._values = values[:RADAR_AXIS_COUNT]
        self.update()

    def set_data(self, data: dict):
        """兼容 dashboard 的字典格式调用"""
        values = [data.get(label, 0) for label in RADAR_LABELS]
        self.set_values(values)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 + 8
        radius = min(w, h) / 2 - 36

        # 网格
        levels = 4
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        for i in range(1, levels + 1):
            r = radius * i / levels
            polygon = QPolygonF()
            for j in range(RADAR_AXIS_COUNT):
                angle = math.pi * 2 * j / RADAR_AXIS_COUNT - math.pi / 2
                polygon.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
            painter.drawPolygon(polygon)

        # 轴线
        for j in range(RADAR_AXIS_COUNT):
            angle = math.pi * 2 * j / RADAR_AXIS_COUNT - math.pi / 2
            painter.drawLine(
                QPointF(cx, cy),
                QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            )

        # 数据区域
        data_polygon = QPolygonF()
        for j, val in enumerate(self._values):
            angle = math.pi * 2 * j / RADAR_AXIS_COUNT - math.pi / 2
            r = radius * val / 100
            data_polygon.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))

        painter.setBrush(QColor(0, 191, 255, 80))
        painter.setPen(QPen(QColor("#00bfff"), 2))
        painter.drawPolygon(data_polygon)

        # 标签
        painter.setPen(QColor("#2d3748"))
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
        for j, label in enumerate(RADAR_LABELS):
            angle = math.pi * 2 * j / RADAR_AXIS_COUNT - math.pi / 2
            x = cx + (radius + 22) * math.cos(angle)
            y = cy + (radius + 22) * math.sin(angle)
            rect = QRectF(x - 40, y - 10, 80, 20)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.end()


class EngineConsoleWidget(QFrame):
    """引擎状态控制台"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EngineConsoleWidget")
        self.setMinimumHeight(140)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("引擎日志")
        title.setObjectName("SectionLabel")
        header.addWidget(title)
        header.addStretch()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #38a169; font-weight: bold;")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setObjectName("EngineLogEdit")
        layout.addWidget(self.log_edit)

        self._boot_logs()
        QTimer.singleShot(1000, self._start_updates)

    def _boot_logs(self):
        boot_lines = [
            "[Theme Engine] 全局 QSS 视觉资产已成功注入应用程序。",
            "[GATEWAY] RUNTIME_GRANTED -> USER: admin | ROLE: Director",
            "[Database] Mock data store initialized with 8 modules.",
            "[Workflow] Approval engine online.",
        ]
        for line in boot_lines:
            self.log_edit.append(line)

    def _start_updates(self):
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._append_random_log)
        self._update_timer.start(6000)

    def _append_random_log(self):
        messages = [
            "[Analytics] 实时数据流接入正常，采样周期 5s。",
            "[Distribute] 渠道 A/B 测试任务已分发。",
            "[Copyright] 版权指纹比对完成，无异常。",
            "[Monetization] 收益模型更新：转化率 +2.3%。",
            "[Assets] 资源库同步完成，新增 14 项元数据。",
        ]
        msg = messages[int(time.time()) % len(messages)]
        self.log_edit.append(msg)
        self.status_label.setText("运行中")

    def load_logs(self, logs):
        """兼容 dashboard 的批量日志加载"""
        self.log_edit.clear()
        for log in logs:
            self.log_edit.append(log)


class EngineLoadWidget(QFrame):
    """引擎负载指示器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EngineLoadWidget")
        self.setMinimumHeight(110)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("引擎负载")
        title.setObjectName("SectionLabel")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        value_row = QHBoxLayout()
        self.load_label = QLabel("45%")
        self.load_label.setObjectName("LoadValueLabel")
        value_row.addWidget(self.load_label)
        value_row.addStretch()
        layout.addLayout(value_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("EngineLoadBar")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(45)
        layout.addWidget(self.progress_bar)

        sub_row = QHBoxLayout()
        sub_labels = [("CPU", "#38a169"), ("MEM", "#805ad5"), ("GPU", "#dd6b20")]
        for name, color in sub_labels:
            lbl = QLabel(f"{name}: --")
            lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
            sub_row.addWidget(lbl)
        sub_row.addStretch()
        layout.addLayout(sub_row)

        self._load_value = 45.0
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_load)
        self._update_timer.start(3000)

    def _update_load(self):
        raw_load = db.get_engine_load()
        self._load_value = self._load_value * 0.6 + raw_load * 0.4
        display_val = round(self._load_value, 1)

        self.progress_bar.setValue(int(display_val))
        self.load_label.setText(f"{display_val:.0f}%")

        if display_val < 50:
            bar_color = "#38a169"
        elif display_val < 75:
            bar_color = "#d29922"
        else:
            bar_color = "#e53e3e"
        self.progress_bar.setStyleSheet(
            f"QProgressBar#EngineLoadBar {{ border: none; border-radius: 9px; background: #edf2f7; }} "
            f"QProgressBar#EngineLoadBar::chunk {{ border-radius: 9px; background: {bar_color}; }}"
        )


class MultiLineDelegate(QStyledItemDelegate):
    """支持多行文本显示与多行编辑的表格委托"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        # 绘制背景/选中状态
        style = options.widget.style() if options.widget else QApplication.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelItemViewItem, options, painter, options.widget)

        # 文本区域
        rect = QRectF(options.rect.adjusted(6, 4, -6, -4))
        painter.setPen(QPen(options.palette.text().color()))
        painter.setFont(options.font)

        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
        text_option.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        painter.drawText(rect, options.text, text_option)

    def sizeHint(self, option: QStyleOptionViewItem, index):
        # 根据列宽和文本计算高度
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if not text:
            return QSize(option.rect.width(), 32)

        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        # 可用宽度
        width = option.rect.width() - 12
        if width <= 0:
            width = 200

        doc = QTextDocument()
        doc.setDefaultFont(options.font)
        doc.setTextWidth(width)
        doc.setPlainText(str(text))
        height = int(doc.size().height()) + 12
        return QSize(option.rect.width(), max(32, height))

    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setFrameShape(QFrame.Shape.NoFrame)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.EditRole) or index.data(Qt.ItemDataRole.DisplayRole) or ""
        editor.setPlainText(str(text))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
