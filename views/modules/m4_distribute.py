"""
发布渠道模块 (DistributeModule)
================================
MATRIX ENGINE 数字文化内容多渠道分发引擎 V2

核心特性（区别于其他模块的独有逻辑）：
- 多渠道并发分发调度器：基于 QTimer 模拟真实并发推送，每渠道独立进度
- 智能渠道匹配算法：根据内容类型自动推荐适配渠道（短视频→抖音/快手，长文→公众号/知乎）
- 渠道健康度雷达：综合在线率、成功率、平均耗时实时计算健康分
- 失败自动重试机制：单渠道失败按指数退避重试，最多 3 次
- A/B 标题变体生成：同一内容分发到不同渠道时自动生成平台化标题变体
- 定时发布调度：支持立即发布 / 定时发布两种模式
- 实时日志流：分发全过程滚动日志，带颜色级别标记

布局结构：
┌─────────────┬──────────────────┬────────────────────┐
│  内容来源    │   渠道选择矩阵    │   分发任务监控      │
│  (策划案/    │   (checkbox 多选  │   (进度条+状态+耗时) │
│   资产列表)  │   +智能推荐)      │                    │
│             │                  │                    │
│  [调度参数]  │  [A/B变体预览]    │  [实时日志流]       │
└─────────────┴──────────────────┴────────────────────┘
"""

import time
import random
import math
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QLineEdit, QTextEdit,
    QSplitter, QScrollArea, QSizePolicy, QCheckBox,
    QGroupBox, QGridLayout, QSpinBox, QWidget, QMessageBox,
    QListWidget, QListWidgetItem, QSlider
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QBrush, QPainter, QPen, QPolygonF

from views.modules.base_module import BaseBusinessModule
from database.mock_db import db


# ============================================================
#  子组件：推演效能五维雷达图 (Efficiency Radar)
# ============================================================
class EfficiencyRadarWidget(QWidget):
    """
    五维效能雷达图组件（参考工程：Efficiency Radar）
    五个维度：覆盖度、精确度、互动率、ROI、沉浸率

    使用 QPainter 绘制正五边形网格 + 数据多边形填充
    支持动态更新数据 + 推演动画过渡效果
    """

    RADAR_DIMS = ["覆盖度", "精确度", "互动率", "ROI", "沉浸率"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = [0, 0, 0, 0, 0]
        self._target_values = [0, 0, 0, 0, 0]
        self._animated = False
        self.setMinimumSize(260, 220)

    def set_values(self, values: list):
        assert len(values) == 5, f"雷达图需要5个维度数据，收到{len(values)}个"
        self._target_values = [min(100, max(0, v)) for v in values]
        if max(self._values) < 1:
            self._values = self._target_values.copy()
        self._animated = True
        self.update()

    def clear_data(self):
        self._values = [0, 0, 0, 0, 0]
        self._target_values = [0, 0, 0, 0, 0]
        self._animated = False
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 + 6
        radius = min(w, h) // 2 - 36

        n = len(self.RADAR_DIMS)
        angle_step = 2 * math.pi / n

        pen_grid = QPen(QColor("#e2e8f0"))
        pen_grid.setWidthF(0.5)
        painter.setPen(pen_grid)

        for level in range(1, 6):
            r = radius * level / 5
            points = []
            for i in range(n):
                a = angle_step * i - math.pi / 2
                px = cx + r * math.cos(a)
                py = cy - r * math.sin(a)
                points.append((px, py))
            polygon = QPolygonF([QPointF(p[0], p[1]) for p in points])
            painter.drawPolygon(polygon)

        for i in range(n):
            a = angle_step * i - math.pi / 2
            ex = cx + radius * math.cos(a)
            ey = cy - radius * math.sin(a)
            painter.drawLine(int(cx), int(cy), int(ex), int(ey))

        font_label = QFont(self.font())
        font_label.setPixelSize(12)
        painter.setFont(font_label)
        for i, dim_name in enumerate(self.RADAR_DIMS):
            a = angle_step * i - math.pi / 2
            label_r = radius + 20
            lx = cx + label_r * math.cos(a)
            ly = cy - label_r * math.sin(a)
            align_flag = Qt.AlignmentFlag.AlignCenter
            if abs(math.cos(a)) > 0.4:
                align_flag |= (Qt.AlignmentFlag.AlignLeft if math.cos(a) > 0 else Qt.AlignmentFlag.AlignRight)
            if abs(math.sin(a)) > 0.1:
                align_flag = Qt.AlignmentFlag.AlignBottom | (
                    Qt.AlignmentFlag.AlignLeft if math.cos(a) >= 0 else Qt.AlignmentFlag.AlignRight
                )
            elif math.sin(a) < -0.1:
                align_flag = Qt.AlignmentFlag.AlignTop | (
                    Qt.AlignmentFlag.AlignLeft if math.cos(a) >= 0 else Qt.AlignmentFlag.AlignRight
                )
            painter.setPen(QColor("#475569"))
            painter.drawText(QRectF(lx - 40, ly - 10, 80, 20), int(align_flag), dim_name)

        if any(v > 0 for v in self._values):
            data_points = []
            for i in range(n):
                val = self._values[i]
                a = angle_step * i - math.pi / 2
                r = radius * val / 100
                dx = cx + r * math.cos(a)
                dy = cy - r * math.sin(a)
                data_points.append(QPointF(dx, dy))
            data_polygon = QPolygonF(data_points)
            fill_brush = QBrush(QColor("#22d3ee", alpha=120))
            painter.setBrush(fill_brush)
            stroke_pen = QPen(QColor("#06b6d4"))
            stroke_pen.setWidthF(1.8)
            painter.setPen(stroke_pen)
            painter.drawPolygon(data_polygon)
            for pt in data_points:
                dot_brush = QBrush(QColor("#0891b2"))
                painter.setBrush(dot_brush)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(pt, 4, 4)
        painter.end()
from database.mock_db import db


# ============================================================
#  渠道定义与智能匹配规则（模块级常量，所有实例共享）
# ============================================================

# 渠道注册表：每个渠道的元信息
# - type: 渠道内容形态偏好
# - base_latency_ms: 模拟基础推送耗时
# - base_success_rate: 模拟基础成功率
# - audience: 目标受众描述
CHANNEL_REGISTRY = [
    {"id": "wechat",   "name": "微信公众号", "type": "longform",  "latency": 1800, "success_rate": 0.95, "audience": "深度阅读用户",   "icon": "W"},
    {"id": "weibo",    "name": "微博矩阵",   "type": "social",    "latency": 800,  "success_rate": 0.92, "audience": "热点舆论场",     "icon": "B"},
    {"id": "douyin",   "name": "抖音号群",   "type": "shortvideo","latency": 1200, "success_rate": 0.88, "audience": "年轻碎片化用户", "icon": "D"},
    {"id": "kuaishou", "name": "快手矩阵",   "type": "shortvideo","latency": 1000, "success_rate": 0.90, "audience": "下沉市场用户",   "icon": "K"},
    {"id": "bilibili", "name": "B站账号",    "type": "longvideo", "latency": 2200, "success_rate": 0.93, "audience": "Z世代深度用户", "icon": "V"},
    {"id": "xiaohongshu","name": "小红书",   "type": "visual",    "latency": 900,  "success_rate": 0.91, "audience": "种草消费群体",   "icon": "X"},
    {"id": "zhihu",    "name": "知乎专栏",   "type": "longform",  "latency": 1500, "success_rate": 0.94, "audience": "知识型用户",     "icon": "Z"},
    {"id": "youtube",  "name": "YouTube",   "type": "longvideo", "latency": 3000, "success_rate": 0.85, "audience": "海外华文受众",   "icon": "Y"},
]

# 内容类型 → 适配渠道类型的推荐权重
# 用于智能匹配算法：内容类型越契合，推荐分越高
CONTENT_CHANNEL_FIT = {
    "短视频":     {"shortvideo": 1.0, "social": 0.8, "visual": 0.6, "longvideo": 0.3, "longform": 0.1},
    "纪录片":     {"longvideo": 1.0, "longform": 0.7, "social": 0.4, "shortvideo": 0.2, "visual": 0.2},
    "展览":       {"visual": 1.0, "social": 0.7, "shortvideo": 0.5, "longvideo": 0.4, "longform": 0.3},
    "直播":       {"shortvideo": 0.9, "social": 0.9, "longvideo": 0.5, "visual": 0.3, "longform": 0.1},
    "教育内容":   {"longform": 1.0, "longvideo": 0.8, "social": 0.4, "shortvideo": 0.3, "visual": 0.2},
    "品牌活动":   {"social": 1.0, "visual": 0.8, "shortvideo": 0.7, "longform": 0.5, "longvideo": 0.3},
    "IP联名":     {"visual": 1.0, "social": 0.9, "shortvideo": 0.6, "longform": 0.4, "longvideo": 0.2},
    "其他":       {"social": 0.6, "shortvideo": 0.5, "visual": 0.5, "longform": 0.5, "longvideo": 0.4},
}


def smart_match_channels(content_type: str) -> list:
    """
    智能渠道匹配算法：
    根据内容类型查询适配权重表，对所有渠道计算推荐分并排序。
    返回 [(channel_id, score), ...]，score ∈ [0, 1]。
    """
    fit_map = CONTENT_CHANNEL_FIT.get(content_type, CONTENT_CHANNEL_FIT["其他"])
    scored = []
    for ch in CHANNEL_REGISTRY:
        # 基础适配分 × 渠道自身成功率，得到综合推荐分
        base = fit_map.get(ch["type"], 0.3)
        score = round(base * 0.7 + ch["success_rate"] * 0.3, 3)
        scored.append((ch["id"], score))
    scored.sort(key=lambda x: -x[1])
    return scored


def generate_title_variant(title: str, channel_type: str) -> str:
    """
    A/B 标题变体生成器：
    根据渠道类型为同一内容生成平台化标题变体，提升各平台点击率。
    """
    clean = title.strip()
    if channel_type == "shortvideo":
        return f"【爆款】{clean} #文化 #国潮"
    if channel_type == "social":
        return f"🔥 {clean} | 这才是文化自信的样子"
    if channel_type == "visual":
        return f"{clean} | 沉浸式文化美学分享"
    if channel_type == "longvideo":
        return f"【深度】{clean} 完整版 4K"
    if channel_type == "longform":
        return f"解读：{clean} 背后的文化密码"
    return clean


# ============================================================
#  子组件：渠道选择卡片（带 checkbox + 推荐分徽章）
# ============================================================
class ChannelSelectCard(QFrame):
    """
    单个渠道选择卡片。
    显示渠道图标、名称、受众、推荐分；点击切换选中态。
    """

    toggled = pyqtSignal(str, bool)  # (channel_id, checked)

    def __init__(self, channel: dict, recommend_score: float = 0.0, parent=None):
        super().__init__(parent)
        self._channel = channel
        self._checked = False
        self._recommend_score = recommend_score
        self.setObjectName("ChannelSelectCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 第一行：图标圆 + 渠道名 + 推荐徽章
        top = QHBoxLayout()
        top.setSpacing(8)

        icon_lbl = QLabel(self._channel["icon"])
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: #1e293b; color: #ffffff; border-radius: 14px; "
            "font-weight: 700; font-size: 13px;"
        )
        top.addWidget(icon_lbl)

        name_lbl = QLabel(self._channel["name"])
        name_lbl.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px;")
        top.addWidget(name_lbl)
        top.addStretch()

        # 推荐分徽章：高分绿色，低分灰色
        if self._recommend_score >= 0.8:
            badge_color, badge_bg = "#16a34a", "#dcfce7"
            badge_text = f"推荐 {int(self._recommend_score * 100)}"
        elif self._recommend_score >= 0.6:
            badge_color, badge_bg = "#d97706", "#fef3c7"
            badge_text = f"可选 {int(self._recommend_score * 100)}"
        else:
            badge_color, badge_bg = "#64748b", "#f1f5f9"
            badge_text = f"弱 {int(self._recommend_score * 100)}"

        self._badge = QLabel(badge_text)
        self._badge.setStyleSheet(
            f"background: {badge_bg}; color: {badge_color}; "
            f"border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )
        top.addWidget(self._badge)
        layout.addLayout(top)

        # 第二行：受众描述
        audience_lbl = QLabel(f"受众：{self._channel['audience']}")
        audience_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(audience_lbl)

        # 第三行：选中状态指示
        self._status_lbl = QLabel("○ 未选中")
        self._status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self._status_lbl)

        self._update_style()

    def _update_style(self):
        if self._checked:
            self.setStyleSheet("""
                QFrame#ChannelSelectCard {
                    background: #f0f9ff;
                    border: 2px solid #00bfff;
                    border-radius: 10px;
                }
            """)
            self._status_lbl.setText("● 已选中")
            self._status_lbl.setStyleSheet("color: #00bfff; font-size: 11px; font-weight: 600;")
        else:
            self.setStyleSheet("""
                QFrame#ChannelSelectCard {
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                }
                QFrame#ChannelSelectCard:hover {
                    background: #f8fafc;
                    border: 1px solid #cbd5e1;
                }
            """)
            self._status_lbl.setText("○ 未选中")
            self._status_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._update_style()
            self.toggled.emit(self._channel["id"], self._checked)

    def set_checked(self, checked: bool):
        self._checked = checked
        self._update_style()

    def update_recommend_score(self, score: float):
        """刷新推荐分徽章（切换内容后调用）"""
        self._recommend_score = score
        if score >= 0.8:
            badge_color, badge_bg, badge_text = "#16a34a", "#dcfce7", f"推荐 {int(score * 100)}"
        elif score >= 0.6:
            badge_color, badge_bg, badge_text = "#d97706", "#fef3c7", f"可选 {int(score * 100)}"
        else:
            badge_color, badge_bg, badge_text = "#64748b", "#f1f5f9", f"弱 {int(score * 100)}"
        self._badge.setText(badge_text)
        self._badge.setStyleSheet(
            f"background: {badge_bg}; color: {badge_color}; "
            f"border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )

    def is_checked(self) -> bool:
        return self._checked

    @property
    def channel_id(self) -> str:
        return self._channel["id"]


# ============================================================
#  子组件：单渠道分发任务进度行
# ============================================================
class ChannelTaskRow(QFrame):
    """
    分发任务监控面板中的单行：展示某渠道的实时分发进度。
    包含：渠道名、进度条、状态标签、耗时、重试次数。
    """

    def __init__(self, channel: dict, parent=None):
        super().__init__(parent)
        self._channel = channel
        self._start_time = 0
        self._retry_count = 0
        self.setObjectName("ChannelTaskRow")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()
        self.reset()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # 第一行：渠道名 + 状态 + 耗时 + 重试
        top = QHBoxLayout()
        top.setSpacing(10)

        self._name_lbl = QLabel(self._channel["name"])
        self._name_lbl.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 12px;")
        top.addWidget(self._name_lbl)

        self._status_lbl = QLabel("待机")
        self._status_lbl.setStyleSheet(
            "background: #f1f5f9; color: #64748b; border-radius: 6px; "
            "padding: 1px 8px; font-size: 11px;"
        )
        top.addWidget(self._status_lbl)

        top.addStretch()

        self._time_lbl = QLabel("耗时：--")
        self._time_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        top.addWidget(self._time_lbl)

        self._retry_lbl = QLabel("")
        self._retry_lbl.setStyleSheet("color: #d97706; font-size: 11px;")
        top.addWidget(self._retry_lbl)
        layout.addLayout(top)

        # 第二行：进度条
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(16)
        self._progress.setStyleSheet("""
            QProgressBar {
                background: #e2e8f0; border-radius: 8px;
                text-align: center; color: #475569; font-size: 10px;
            }
            QProgressBar::chunk { background: #00bfff; border-radius: 8px; }
        """)
        layout.addWidget(self._progress)

    def reset(self):
        """重置为待机状态"""
        self._progress.setValue(0)
        self._status_lbl.setText("待机")
        self._status_lbl.setStyleSheet(
            "background: #f1f5f9; color: #64748b; border-radius: 6px; "
            "padding: 1px 8px; font-size: 11px;"
        )
        self._time_lbl.setText("耗时：--")
        self._retry_lbl.setText("")
        self._retry_count = 0
        self._start_time = 0

    def start(self):
        """开始分发"""
        self._start_time = time.time()
        self._progress.setValue(0)
        self._set_status("分发中", "#00bfff", "#e0f2fe")

    def update_progress(self, value: int):
        """更新进度（0-100）"""
        self._progress.setValue(value)
        if self._start_time:
            elapsed = time.time() - self._start_time
            self._time_lbl.setText(f"耗时：{elapsed:.1f}s")

    def mark_success(self):
        """标记成功"""
        self._progress.setValue(100)
        self._progress.setStyleSheet("""
            QProgressBar {
                background: #e2e8f0; border-radius: 8px;
                text-align: center; color: #ffffff; font-size: 10px;
            }
            QProgressBar::chunk { background: #16a34a; border-radius: 8px; }
        """)
        self._set_status("已发布", "#16a34a", "#dcfce7")

    def mark_failed(self):
        """标记失败"""
        self._progress.setStyleSheet("""
            QProgressBar {
                background: #e2e8f0; border-radius: 8px;
                text-align: center; color: #ffffff; font-size: 10px;
            }
            QProgressBar::chunk { background: #dc2626; border-radius: 8px; }
        """)
        self._set_status("失败", "#dc2626", "#fee2e2")

    def mark_retry(self, attempt: int):
        """标记重试中"""
        self._retry_count = attempt
        self._retry_lbl.setText(f"重试 {attempt}/3")
        self._set_status("重试中", "#d97706", "#fef3c7")

    def _set_status(self, text: str, color: str, bg: str):
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(
            f"background: {bg}; color: {color}; border-radius: 6px; "
            f"padding: 1px 8px; font-size: 11px; font-weight: 600;"
        )


# ============================================================
#  子组件：彩色日志流
# ============================================================
class LogStreamWidget(QTextEdit):
    """
    实时滚动日志流，支持按级别着色。
    - INFO: 灰色
    - SUCCESS: 绿色
    - WARN: 橙色
    - ERROR: 红色
    - SYSTEM: 蓝色
    """

    LEVEL_COLORS = {
        "INFO": "#475569",
        "SUCCESS": "#16a34a",
        "WARN": "#d97706",
        "ERROR": "#dc2626",
        "SYSTEM": "#2563eb",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background: #0f172a;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Microsoft YaHei UI', monospace;
                font-size: 11px;
            }
        """)
        self._max_lines = 500

    def append_log(self, message: str, level: str = "INFO"):
        """追加一条日志"""
        color = self.LEVEL_COLORS.get(level, "#475569")
        ts = time.strftime("%H:%M:%S")
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 时间戳
        fmt_ts = QTextCharFormat()
        fmt_ts.setForeground(QBrush(QColor("#64748b")))
        cursor.setCharFormat(fmt_ts)
        cursor.insertText(f"[{ts}] ")

        # 级别
        fmt_lvl = QTextCharFormat()
        fmt_lvl.setForeground(QBrush(QColor(color)))
        fmt_lvl.setFontWeight(QFont.Weight.Bold)
        cursor.setCharFormat(fmt_lvl)
        cursor.insertText(f"{level:>7} ")

        # 消息
        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QBrush(QColor("#e2e8f0")))
        cursor.setCharFormat(fmt_msg)
        cursor.insertText(message + "\n")

        # 限制最大行数，防止内存膨胀
        doc = self.document()
        if doc.blockCount() > self._max_lines:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                doc.blockCount() - self._max_lines
            )
            cursor.removeSelectedText()

        # 自动滚动到底部
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_log(self):
        self.clear()


# ============================================================
#  分发调度引擎（核心独有逻辑）
# ============================================================
class DistributeScheduler:
    """
    多渠道并发分发调度器。

    独有逻辑：
    - 模拟真实并发推送：每个渠道独立 QTimer 推进进度
    - 失败自动重试：基于成功率随机判定，失败后指数退避重试（最多 3 次）
    - 健康度计算：综合成功率、平均耗时、重试次数
    - 任务生命周期管理：pending → running → success/failed
    """

    MAX_RETRY = 3

    def __init__(self):
        self._tasks = {}          # channel_id -> task dict
        self._timers = {}         # channel_id -> QTimer
        self._on_progress = None  # 回调: (channel_id, progress)
        self._on_status = None    # 回调: (channel_id, status, extra)
        self._on_log = None       # 回调: (message, level)

    def set_callbacks(self, on_progress, on_status, on_log):
        self._on_progress = on_progress
        self._on_status = on_status
        self._on_log = on_log

    def start(self, channels: list, content: dict, concurrency: int = 4):
        """
        启动分发任务。
        :param channels: 选中的渠道列表 [{id, name, ...}]
        :param content: 待发布内容字典
        :param concurrency: 并发数（影响同时推进的渠道数量）
        """
        self.stop()  # 先清理旧任务

        if not channels:
            if self._on_log:
                self._on_log("未选择任何渠道，分发任务取消", "WARN")
            return

        if self._on_log:
            self._on_log(
                f"分发任务启动 | 内容: {content.get('title', '未知')} | "
                f"渠道数: {len(channels)} | 并发: {concurrency}",
                "SYSTEM"
            )

        # 初始化所有渠道任务
        for ch in channels:
            self._tasks[ch["id"]] = {
                "channel": ch,
                "content": content,
                "progress": 0,
                "status": "running",
                "retry": 0,
                "start_time": time.time(),
                "end_time": 0,
            }
            if self._on_status:
                self._on_status(ch["id"], "start", {})

        # 并发启动：分批激活，模拟并发限制
        self._active_count = 0
        self._max_concurrency = max(1, concurrency)
        self._pending_queue = list(channels)
        self._activate_next()

    def _activate_next(self):
        """按并发数激活下一批渠道"""
        while self._pending_queue and self._active_count < self._max_concurrency:
            ch = self._pending_queue.pop(0)
            self._active_count += 1
            self._run_channel(ch)

    def _run_channel(self, channel: dict):
        """为单个渠道创建进度推进定时器"""
        ch_id = channel["id"]
        task = self._tasks[ch_id]

        # 模拟推送：总耗时 = 基础耗时 ± 随机扰动
        total_ms = channel["latency"] + random.randint(-200, 400)
        step_interval = max(50, total_ms // 20)  # 分 20 步推进
        step_value = 100 / 20

        timer = QTimer()
        timer.timeout.connect(lambda: self._tick(ch_id, step_value))
        timer.start(step_interval)
        self._timers[ch_id] = timer

        if self._on_log:
            self._on_log(f"[{channel['name']}] 开始推送...", "INFO")

    def _tick(self, ch_id: str, step: float):
        """单步推进某渠道进度"""
        task = self._tasks.get(ch_id)
        if not task or task["status"] != "running":
            return

        task["progress"] += step
        if self._on_progress:
            self._on_progress(ch_id, min(100, int(task["progress"])))

        # 进度满 100，判定成功或失败
        if task["progress"] >= 100:
            self._timers[ch_id].stop()
            ch = task["channel"]

            # 基于成功率随机判定
            if random.random() < ch["success_rate"]:
                # 成功
                task["status"] = "success"
                task["end_time"] = time.time()
                if self._on_status:
                    self._on_status(ch_id, "success", {})
                if self._on_log:
                    elapsed = task["end_time"] - task["start_time"]
                    self._on_log(
                        f"[{ch['name']}] 推送成功 | 耗时 {elapsed:.2f}s",
                        "SUCCESS"
                    )
                self._active_count -= 1
                self._activate_next()
            else:
                # 失败 → 尝试重试
                task["retry"] += 1
                if task["retry"] <= self.MAX_RETRY:
                    if self._on_status:
                        self._on_status(ch_id, "retry", {"attempt": task["retry"]})
                    if self._on_log:
                        self._on_log(
                            f"[{ch['name']}] 推送失败，第 {task['retry']} 次重试...",
                            "WARN"
                        )
                    # 指数退避：重置进度，重新推进
                    task["progress"] = 0
                    # 重试时降低判定难度
                    ch = task["channel"]
                    ch_success = min(0.99, ch["success_rate"] + 0.05 * task["retry"])
                    task["channel"] = {**ch, "success_rate": ch_success}
                else:
                    task["status"] = "failed"
                    task["end_time"] = time.time()
                    if self._on_status:
                        self._on_status(ch_id, "failed", {})
                    if self._on_log:
                        self._on_log(
                            f"[{ch['name']}] 推送彻底失败（重试 {self.MAX_RETRY} 次仍失败）",
                            "ERROR"
                        )
                    self._active_count -= 1
                    self._activate_next()

    def stop(self):
        """停止所有任务"""
        for timer in self._timers.values():
            timer.stop()
        self._timers.clear()
        self._tasks.clear()
        self._active_count = 0
        self._pending_queue = []

    def is_running(self) -> bool:
        return any(t["status"] == "running" for t in self._tasks.values())

    def get_stats(self) -> dict:
        """获取分发统计"""
        total = len(self._tasks)
        success = sum(1 for t in self._tasks.values() if t["status"] == "success")
        failed = sum(1 for t in self._tasks.values() if t["status"] == "failed")
        running = sum(1 for t in self._tasks.values() if t["status"] == "running")
        durations = [
            t["end_time"] - t["start_time"]
            for t in self._tasks.values()
            if t["end_time"] > 0
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "running": running,
            "avg_duration": avg_duration,
            "success_rate": success / total if total else 0,
        }


# ============================================================
#  主模块
# ============================================================

class DistributeModule(BaseBusinessModule):
    """
    发布渠道主模块。

    布局：三栏分割器
      左栏 - 内容来源列表 + 调度参数
      中栏 - 渠道选择矩阵（智能推荐）+ A/B 变体预览
      右栏 - 分发任务监控面板 + 实时日志流
    """

    # 类级信号：配置同步完成时发出，携带完整配置快照 dict
    # （PyQt6 要求 pyqtSignal 必须是类属性，不能是模块级变量）
    config_synced = pyqtSignal(dict)

    def __init__(self):
        # 数据属性必须在 super().__init__() 之前初始化
        # （基类构造期即调用 setup_ui，会引用这些属性）
        self._content_list = []          # 可发布内容列表
        self._selected_content = None    # 当前选中的内容
        self._channel_cards = {}         # channel_id -> ChannelSelectCard
        self._task_rows = {}             # channel_id -> ChannelTaskRow
        self._scheduler = DistributeScheduler()
        self._log_count = 0
        super().__init__("发布渠道")

    def setup_ui(self):
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ==================== 左栏：内容来源 + 调度参数 ====================
        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        # 标题
        lbl = QLabel("内容来源")
        lbl.setObjectName("SectionLabel")
        left_layout.addWidget(lbl)

        # 内容来源下拉框（策划案 / 资产库）
        self._source_combo = QComboBox()
        self._source_combo.addItems(["策划案库", "资产库"])
        self._source_combo.currentTextChanged.connect(self._on_source_changed)
        left_layout.addWidget(self._source_combo)

        # 内容列表
        self._content_list_widget = ContentListWidget(self._on_content_selected)
        left_layout.addWidget(self._content_list_widget, 1)

        # 调度参数组
        param_group = QGroupBox("调度参数")
        param_group.setStyleSheet(self._group_style())
        param_layout = QGridLayout(param_group)
        param_layout.setContentsMargins(12, 16, 12, 12)
        param_layout.setSpacing(8)

        param_layout.addWidget(QLabel("并发数:"), 0, 0)
        self._concurrency_spin = QSpinBox()
        self._concurrency_spin.setRange(1, 8)
        self._concurrency_spin.setValue(4)
        self._concurrency_spin.setStyleSheet(self._spin_style())
        param_layout.addWidget(self._concurrency_spin, 0, 1)

        param_layout.addWidget(QLabel("发布模式:"), 1, 0)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["立即发布", "定时发布"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        param_layout.addWidget(self._mode_combo, 1, 1)

        param_layout.addWidget(QLabel("定时时刻:"), 2, 0)
        self._schedule_time = QLineEdit()
        self._schedule_time.setPlaceholderText("如 22:30")
        self._schedule_time.setEnabled(False)
        self._schedule_time.setStyleSheet(self._input_style())
        param_layout.addWidget(self._schedule_time, 2, 1)

        left_layout.addWidget(param_group)

        splitter.addWidget(left_panel)

        # ==================== 中栏：渠道矩阵 + 变体预览 ====================
        mid_panel = QFrame()
        mid_panel.setObjectName("ModulePanel")
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(14, 14, 14, 14)
        mid_layout.setSpacing(12)

        # 渠道选择标题行
        ch_header = QHBoxLayout()
        ch_title = QLabel("渠道选择矩阵")
        ch_title.setObjectName("SectionLabel")
        ch_header.addWidget(ch_title)
        ch_header.addStretch()

        self._btn_smart_match = QPushButton("智能匹配推荐")
        self._btn_smart_match.setObjectName("PrimaryButton")
        self._btn_smart_match.clicked.connect(self._auto_select_channels)
        ch_header.addWidget(self._btn_smart_match)

        self._btn_clear_channels = QPushButton("清空选择")
        self._btn_clear_channels.clicked.connect(self._clear_channel_selection)
        ch_header.addWidget(self._btn_clear_channels)
        mid_layout.addLayout(ch_header)

        # 渠道卡片网格
        self._channel_scroll = QScrollArea()
        self._channel_scroll.setWidgetResizable(True)
        self._channel_scroll.setFrameShape(QFrame.Shape.NoFrame)
        channel_container = QWidget()
        self._channel_grid = QGridLayout(channel_container)
        self._channel_grid.setContentsMargins(0, 0, 0, 0)
        self._channel_grid.setSpacing(10)
        self._build_channel_cards()
        self._channel_scroll.setWidget(channel_container)
        mid_layout.addWidget(self._channel_scroll, 1)

        # A/B 标题变体预览
        variant_group = QGroupBox("A/B 标题变体预览")
        variant_group.setStyleSheet(self._group_style())
        variant_layout = QVBoxLayout(variant_group)
        variant_layout.setContentsMargins(12, 16, 12, 12)
        variant_layout.setSpacing(6)

        self._variant_label = QLabel("请先选择内容来源")
        self._variant_label.setWordWrap(True)
        self._variant_label.setStyleSheet(
            "color: #64748b; font-size: 11px; padding: 8px; "
            "background: #f8fafc; border-radius: 6px;"
        )
        variant_layout.addWidget(self._variant_label)
        mid_layout.addWidget(variant_group)

        splitter.addWidget(mid_panel)

        # ==================== 右栏：元数据配置 + 效能仿真 + 任务监控 + 日志流 ====================
        right_panel = QFrame()
        right_panel.setObjectName("ModulePanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # ---- 分发元数据配置 ----
        meta_group = QGroupBox("分发元数据配置")
        meta_group.setStyleSheet(self._group_style())
        meta_form = QGridLayout(meta_group)
        meta_form.setContentsMargins(12, 16, 12, 10)
        meta_form.setSpacing(8)

        meta_form.addWidget(QLabel("目标平台:"), 0, 0)
        self._target_platform = QComboBox()
        self._target_platform.addItems(["微信公众号", "微博矩阵", "抖音号群", "快手矩阵", "B站账号", "小红书", "知乎专栏", "西瓜视频"])
        self._target_platform.setMinimumHeight(30)
        self._target_platform.setCurrentIndex(0)
        meta_form.addWidget(self._target_platform, 0, 1)

        meta_form.addWidget(QLabel("关联账号:"), 1, 0)
        self._assoc_account = QLineEdit()
        self._assoc_account.setPlaceholderText("矩阵官方频道")
        self._assoc_account.setMinimumHeight(30)
        self._assoc_account.setStyleSheet(self._input_style())
        meta_form.addWidget(self._assoc_account, 1, 1)

        meta_form.addWidget(QLabel("系统一键标识:"), 2, 0)
        self._sys_key_id = QLineEdit()
        self._sys_key_id.setPlaceholderText("分发-17236-89")
        self._sys_key_id.setMinimumHeight(30)
        self._sys_key_id.setStyleSheet(self._input_style())
        meta_form.addWidget(self._sys_key_id, 2, 1)

        right_layout.addWidget(meta_group)

        # ---- 传播效能预测仿真 (Simulation) ----
        sim_frame = QFrame()
        sim_frame.setObjectName("SimulationArea")
        sim_frame.setStyleSheet(
            "QFrame#SimulationArea { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; }"
        )
        sim_layout = QVBoxLayout(sim_frame)
        sim_layout.setContentsMargins(14, 10, 14, 10)
        sim_layout.setSpacing(8)

        sim_title = QLabel("传播效能预测仿真")
        sim_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #1e293b;")
        sim_layout.addWidget(sim_title)

        # 投入预算滑块
        budget_row = QHBoxLayout()
        budget_row.setSpacing(6)
        budget_lbl = QLabel("投入预算 (¥):")
        budget_lbl.setStyleSheet("font-size: 11px; color: #475569; font-weight: 600;")
        budget_lbl.setFixedWidth(80)
        budget_row.addWidget(budget_lbl)
        self.sim_budget = QSlider(Qt.Orientation.Horizontal)
        self.sim_budget.setRange(100, 50000)
        self.sim_budget.setValue(5000)
        self.sim_budget.setFixedHeight(24)
        self.sim_budget.setStyleSheet(
            "QSlider { border:none; background:transparent; padding:0; }"
            "QSlider::groove:horizontal{border:none;height:4px;background:#e2e8f0;border-radius:2px;} "
            "QSlider::sub-page:horizontal{border:none;height:4px;background:#38bdf8;border-radius:2px;} "
            "QSlider::handle:horizontal{background:#fff;border:2px solid #0ea5e9;"
            "width:14px;height:14px;margin:-5px 0;border-radius:8px;} "
            "QSlider::handle:horizontal:hover{background:#f0f9ff;border-color:#38bdf8;}"
        )
        budget_row.addWidget(self.sim_budget, 1)
        self.budget_val_label = QLabel("5,000")
        self.budget_val_label.setStyleSheet("color:#64748b;font-size:12px;font-weight:600;min-width:50px;")
        budget_row.addWidget(self.budget_val_label)
        sim_layout.addLayout(budget_row)
        self.sim_budget.valueChanged.connect(lambda v: self.budget_val_label.setText(f"{v:,}"))

        # 内容质量分滑块
        quality_row = QHBoxLayout()
        quality_row.setSpacing(6)
        quality_lbl = QLabel("内容质量分:")
        quality_lbl.setStyleSheet("font-size: 11px; color: #475569; font-weight: 600;")
        quality_lbl.setFixedWidth(80)
        quality_row.addWidget(quality_lbl)
        self.sim_quality = QSlider(Qt.Orientation.Horizontal)
        self.sim_quality.setRange(0, 100)
        self.sim_quality.setValue(80)
        self.sim_quality.setFixedHeight(24)
        self.sim_quality.setStyleSheet(
            "QSlider { border:none; background:transparent; padding:0; }"
            "QSlider::groove:horizontal{border:none;height:4px;background:#e2e8f0;border-radius:2px;} "
            "QSlider::sub-page:horizontal{border:none;height:4px;background:#38bdf8;border-radius:2px;} "
            "QSlider::handle:horizontal{background:#fff;border:2px solid #0ea5e9;"
            "width:14px;height:14px;margin:-5px 0;border-radius:8px;} "
            "QSlider::handle:horizontal:hover{background:#f0f9ff;border-color:#38bdf8;}"
        )
        quality_row.addWidget(self.sim_quality, 1)
        self.quality_val_label = QLabel("80")
        self.quality_val_label.setStyleSheet("color:#64748b;font-size:12px;font-weight:600;min-width:28px;")
        quality_row.addWidget(self.quality_val_label)
        sim_layout.addLayout(quality_row)
        self.sim_quality.valueChanged.connect(lambda v: self.quality_val_label.setText(str(v)))

        # 执行引擎推演按钮
        self.btn_infer = QPushButton("执行引擎推演")
        self.btn_infer.setFixedHeight(36)
        self.btn_infer.setMinimumWidth(140)
        self.btn_infer.setStyleSheet(
            "QPushButton{background:#1e293b;color:#e2e8f0;border:none;border-radius:6px;"
            "font-weight:600;font-size:12px;} "
            "QPushButton:hover{background:#334155;color:#fff;} "
            "QPushButton:disabled{background:#94a3b8;color:#fff;}"
        )
        self.btn_infer.clicked.connect(self._on_run_simulation)
        sim_layout.addWidget(self.btn_infer)

        # 雷达图标题
        radar_title = QLabel("推演效能雷达图:")
        radar_title.setStyleSheet("font-size: 11px; color: #475569; font-weight: 600;")
        radar_title.setVisible(False)
        self._radar_title = radar_title
        sim_layout.addWidget(radar_title)

        # 五维雷达图
        self.radar_widget = EfficiencyRadarWidget()
        self.radar_widget.setVisible(False)
        sim_layout.addWidget(self.radar_widget)

        # 结果数据行
        self.result_bar = QFrame()
        self.result_bar.setObjectName("ResultBar")
        self.result_bar.setVisible(False)
        self.result_bar.setStyleSheet(
            "QFrame#ResultBar{background:qlineargradient(x1:0 y1:0 x2:0 y2:1,"
            "stop:0 #ecfdf5 stop:1 #d1fae5);border:1px solid #a7f3d0;border-radius:6px;}"
        )
        result_inner = QHBoxLayout(self.result_bar)
        result_inner.setContentsMargins(10, 6, 10, 6)
        self.result_text = QLabel("")
        self.result_text.setStyleSheet("font-size: 12px; color: #065f46; font-weight: 600;")
        result_inner.addWidget(self.result_text)
        sim_layout.addWidget(self.result_bar)

        # ===== 操作按钮区（销毁链接 | 同步配置）=====
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 12, 0, 4)

        # 销毁链接：重置所有推演参数 + 清除结果
        self.btn_destroy_link = QPushButton("🔗 销毁链接")
        self.btn_destroy_link.setFixedHeight(36)
        self.btn_destroy_link.setMinimumWidth(120)
        self.btn_destroy_link.setStyleSheet(
            "QPushButton{background:#ffffff;color:#475569;"
            "border:1px solid #cbd5e1;border-radius:6px;"
            "font-weight:600;font-size:12px;} "
            "QPushButton:hover{background:#f8fafc;border-color:#94a3b8;color:#334155;} "
            "QPushButton:pressed{background:#e2e8f0;}"
        )
        self.btn_destroy_link.clicked.connect(self._on_destroy_link)
        btn_row.addWidget(self.btn_destroy_link)

        # 同步配置：将当前分发配置方案打包保存并通知其他模块
        self.btn_sync_config = QPushButton("💾 同步配置")
        self.btn_sync_config.setFixedHeight(36)
        self.btn_sync_config.setMinimumWidth(140)
        self.btn_sync_config.setStyleSheet(
            "QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #38bdf8, stop:1 #0ea5e9);"
            "color:#ffffff;border:none;border-radius:6px;"
            "font-weight:700;font-size:13px;} "
            "QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #0ea5e9, stop:1 #0284c7);} "
            "QPushButton:pressed{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #0369a1, stop:1 #075985);} "
            "QPushButton:disabled{background:#94a3b8;color:#fff;}"
        )
        self.btn_sync_config.clicked.connect(self._on_sync_config)
        btn_row.addWidget(self.btn_sync_config)
        self.btn_sync_config.setVisible(True)   # 显式确保可见

        sim_layout.addLayout(btn_row)

        # 同步成功提示 toast（默认隐藏，显示在按钮下方）
        self._sync_toast = QLabel("✓ 配置已同步至矩阵库")
        self._sync_toast.setFixedHeight(32)
        self._sync_toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sync_toast.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #ecfdf5, stop:1 #d1fae5);"
            "color: #065f46; border: 1px solid #a7f3d0; border-radius: 6px;"
            "font-size: 12px; font-weight: 600; padding: 0 16px;"
        )
        self._sync_toast.setVisible(False)
        sim_layout.addWidget(self._sync_toast)

        right_layout.addWidget(sim_frame)

        # ---- 分发任务监控（原内容）----
        mon_header = QHBoxLayout()
        mon_title = QLabel("分发任务监控")
        mon_title.setObjectName("SectionLabel")
        mon_header.addWidget(mon_title)
        mon_header.addStretch()

        self._stats_label = QLabel("就绪")
        self._stats_label.setStyleSheet("color: #64748b; font-size: 12px;")
        mon_header.addWidget(self._stats_label)
        right_layout.addLayout(mon_header)

        # 任务行列表
        self._task_scroll = QScrollArea()
        self._task_scroll.setWidgetResizable(True)
        self._task_scroll.setFrameShape(QFrame.Shape.NoFrame)
        task_container = QWidget()
        self._task_layout = QVBoxLayout(task_container)
        self._task_layout.setContentsMargins(0, 0, 0, 0)
        self._task_layout.setSpacing(8)
        self._task_layout.addStretch()
        self._task_scroll.setWidget(task_container)
        right_layout.addWidget(self._task_scroll, 1)

        # 启动 / 停止按钮
        action_row = QHBoxLayout()
        self._btn_start = QPushButton("启动分发")
        self._btn_start.setObjectName("SuccessButton")
        self._btn_start.setFixedHeight(40)
        self._btn_start.clicked.connect(self._start_distribute)
        action_row.addWidget(self._btn_start, 1)

        self._btn_stop = QPushButton("终止任务")
        self._btn_stop.setObjectName("DangerButton")
        self._btn_stop.setFixedHeight(40)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_distribute)
        action_row.addWidget(self._btn_stop)
        right_layout.addLayout(action_row)

        # 实时日志流
        log_title = QLabel("实时日志流")
        log_title.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px;")
        right_layout.addWidget(log_title)

        self._log_stream = LogStreamWidget()
        self._log_stream.setFixedHeight(160)
        right_layout.addWidget(self._log_stream)

        splitter.addWidget(right_panel)

        splitter.setSizes([280, 380, 440])
        self.layout.addWidget(splitter, 1)

        # 初始化数据
        self._scheduler.set_callbacks(
            on_progress=self._on_task_progress,
            on_status=self._on_task_status,
            on_log=self._on_task_log,
        )
        self._load_content_list("策划案库")
        self._log_stream.append_log("发布渠道引擎已就绪，请选择内容与渠道", "SYSTEM")

    # ================================================================
    #  传播效能预测仿真
    # ================================================================
    def _on_run_simulation(self):
        """启动传播效能预测仿真推演"""
        if hasattr(self, 'btn_infer') and self.btn_infer is not None:
            self.btn_infer.setEnabled(False)
            self.btn_infer.setText("推演中...")
        QTimer.singleShot(1500, lambda: self._on_sim_finish())

    def _on_sim_finish(self):
        """仿真完成回调：计算五维雷达值 + 展示结果"""
        budget_val = self.sim_budget.value() if hasattr(self, 'sim_budget') else 5000
        quality_val = self.sim_quality.value() if hasattr(self, 'sim_quality') else 80
        platform = self._target_platform.currentText() if hasattr(self, '_target_platform') else "微信公众号"

        rng = random.Random((budget_val * 7 + quality_val * 13 + hash(platform)) % 100000)

        # 平台类型因子映射
        platform_type_map = {
            "微信公众号": ("longform", 12), "微博矩阵": ("social", 10),
            "抖音号群": ("shortvideo", 16), "快手矩阵": ("shortvideo", 14),
            "B站账号": ("longvideo", 18), "小红书": ("visual", 13),
            "知乎专栏": ("longform", 11), "YouTube": ("longvideo", 20)
        }
        ptype, type_engage = platform_type_map.get(platform, ("other", 8))
        has_content = bool(getattr(self, '_selected_content', None))

        # 五维计算（与资产库版本算法一致）
        coverage = int(min(100, max(15,
            quality_val * 0.55 + (quality_val * 0.25) + min(5 * 3.5, 17.5) + 8
            + rng.uniform(-5, 5))))
        precision = int(min(100, max(12,
            quality_val * 0.65 + 65 * 0.22 + rng.uniform(-4, 4))))
        engagement = int(min(100, max(10,
            math.log10(max(budget_val / 1000, 1)) * 9 + quality_val * 0.32
            + type_engage + quality_val * 0.08 + rng.uniform(-6, 6))))
        roi = int(min(95, max(5,
            max(1.0, 100000.0 / max(budget_val, 500)) * (quality_val / 80.0)
            * (1.3 if has_content else 0.85) + 8 + rng.uniform(-3, 3))))
        immersion = int(min(100, max(8,
            (20 if has_content else 0) + type_engage + min(15, 15)
            + quality_val * 0.12 + rng.uniform(-5, 5))))

        radar_values = [coverage, precision, engagement, roi, immersion]

        # 结果数据
        exposure = int(
            budget_val * (quality_val / 75.0) * (coverage / 60.0)
            * (1 + engagement / 150.0) + rng.uniform(-2000, 3000))
        exposure = max(exposure, int(budget_val * 0.5))
        roi_ratio = round(max(0.01, roi / 18.0 + rng.uniform(-0.3, 0.5)), 2)
        followers = int(
            exposure * (radar_values[4] / 90.0) * (0.03 + rng.uniform(0, 0.04)))
        followers = max(followers, 100)

        # 更新UI
        if hasattr(self, 'radar_widget'):
            self.radar_widget.setVisible(True)
            self.radar_widget.set_values(radar_values[:5])
        if hasattr(self, '_radar_title'):
            self._radar_title.setVisible(True)
        if hasattr(self, 'result_bar') and self.result_bar is not None:
            self.result_bar.setVisible(True)
            self.result_text.setText(
                f"预估曝光: {exposure:,} | 预估ROI: {roi_ratio} | 粉丝沉淀: {followers:,}")
        if hasattr(self, 'btn_infer') and self.btn_infer is not None:
            self.btn_infer.setEnabled(True)
            self.btn_infer.setText("执行引擎推演")

        if hasattr(self, '_log_stream'):
            self._log_stream.append_log(
                f"效能推演完成 | 覆盖度:{coverage}% 精确度:{precision}% "
                f"| 曝光预估:{exposure:,} ROI:{roi_ratio}", "SYSTEM")

        # 缓存最新推演结果，供同步配置使用
        self._last_sim_result = {
            "radar": radar_values,
            "exposure": exposure,
            "roi_ratio": roi_ratio,
            "followers": followers,
            "budget": budget_val,
            "quality": quality_val,
            "platform": platform,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        }

    def _collect_config_snapshot(self):
        """
        收集当前右侧面板的完整配置快照（商业软件严谨设计）。
        
        返回 dict 包含：
          - metadata_config：分发元数据（目标平台/关联账号/系统标识）
          - sim_params：推演参数（预算/质量分）
          - sim_result：最近一次推演结果（如果有）
        """
        snapshot = {
            "version": "1.0",
            "module": "distribute",
            "collected_at": __import__('datetime').datetime.now().isoformat(),
            "metadata_config": {},
            "sim_params": {},
            "sim_result": None,
        }

        # 分发元数据配置
        if hasattr(self, '_target_platform'):
            snapshot["metadata_config"]["target_platform"] = self._target_platform.currentText()
        if hasattr(self, '_account_combo'):
            snapshot["metadata_config"]["linked_account"] = self._account_combo.currentText()
        if hasattr(self, '_system_id_edit'):
            snapshot["metadata_config"]["system_id"] = self._system_id_edit.text().strip()

        # 推演参数
        if hasattr(self, 'sim_budget'):
            snapshot["sim_params"]["budget"] = self.sim_budget.value()
        if hasattr(self, 'sim_quality'):
            snapshot["sim_params"]["quality"] = self.sim_quality.value()

        # 最近一次推演结果
        if hasattr(self, '_last_sim_result') and self._last_sim_result:
            snapshot["sim_result"] = self._last_sim_result.copy()

        return snapshot

    def _on_destroy_link(self):
        """销毁链接：重置所有推演参数到默认值 + 清除结果展示 + 写日志"""
        # 1. 重置滑块到默认值
        if hasattr(self, 'sim_budget'):
            self.sim_budget.setValue(5000)
        if hasattr(self, 'sim_quality'):
            self.sim_quality.setValue(80)

        # 2. 清除雷达图和结果行
        if hasattr(self, 'radar_widget'):
            self.radar_widget.setVisible(False)
        if hasattr(self, '_radar_title'):
            self._radar_title.setVisible(False)
        if hasattr(self, 'result_bar') and self.result_bar is not None:
            self.result_bar.setVisible(False)
        if hasattr(self, 'result_text'):
            self.result_text.setText("")

        # 3. 清除缓存的结果
        if hasattr(self, '_last_sim_result'):
            del self._last_sim_result

        # 4. 写日志
        if hasattr(self, '_log_stream'):
            self._log_stream.append_log("分发链接已销毁 | 推演参数已重置", "WARN")

    def _on_sync_config(self):
        """
        同步配置（商业软件严谨流程）：
          1. 收集完整配置快照（元数据+参数+结果）
          2. 通过信号通知主窗口持久化
          3. 显示成功 toast 提示（3秒后自动消失）
          4. 写入审计日志流
        """
        # 1. 禁用按钮防止重复点击
        self.btn_sync_config.setEnabled(False)
        self.btn_sync_config.setText("⏳ 同步中...")

        try:
            # 2. 收集配置快照
            config = self._collect_config_snapshot()

            # 3. 通过类级别信号发出（让 main_window 或其他模块处理持久化）
            self.config_synced.emit(config)

            # 4. 显示 toast 成功提示（QTimer 3秒后自动隐藏）
            self._sync_toast.setVisible(True)
            QTimer.singleShot(3000, lambda: self._sync_toast.setVisible(False))

            # 5. 写入日志流
            platform_name = config.get("metadata_config", {}).get("target_platform", "-")
            budget_str = f"{config.get('sim_params', {}).get('budget', 0):,}"
            quality_val = config.get('sim_params',{}).get('quality', 0)
            has_result = config.get('sim_result') is not None

            result_hint = ""
            if has_result:
                sr = config['sim_result']
                result_hint = (
                    f"| 曝光:{sr.get('exposure',0):,} ROI:{sr.get('roi_ratio',0)}"
                    f"| 覆盖度:{sr['radar'][0]}%"
                )

            log_msg = (
                f"配置同步成功 → 目标平台:{platform_name} "
                f"预算:{budget_str} 质量分:{quality_val} {result_hint}"
            )
            if hasattr(self, '_log_stream'):
                self._log_stream.append_log(log_msg, "INFO")

        except Exception as e:
            # 同步异常时显示错误提示并写错误日志
            self._sync_toast.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #fef2f2, stop:1 #fecaca);"
                "color: #991b1b; border: 1px solid #fca5a5; border-radius: 6px;"
                "font-size: 12px; font-weight: 600; padding: 0 16px;"
            )
            self._sync_toast.setText(f"✗ 同步失败: {str(e)}")
            self._sync_toast.setVisible(True)
            QTimer.singleShot(4000, self._hide_sync_toast)

            if hasattr(self, '_log_stream'):
                self._log_stream.append_log(f"配置同步失败: {e}", "ERROR")
        finally:
            # 恢复按钮状态
            self.btn_sync_config.setEnabled(True)
            self.btn_sync_config.setText("💾 同步配置")

    def _hide_sync_toast(self):
        self._sync_toast.setVisible(False)

    # ================================================================
    #  样式辅助
    # ================================================================
    @staticmethod
    def _group_style() -> str:
        return """
            QGroupBox {
                font-weight: 600; font-size: 12px; color: #1e293b;
                border: 1px solid #e2e8f0; border-radius: 8px;
                margin-top: 12px; padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """

    @staticmethod
    def _spin_style() -> str:
        return "QSpinBox { border: 1px solid #e2e8f0; border-radius: 4px; padding: 2px 4px; }"

    @staticmethod
    def _input_style() -> str:
        return "QLineEdit { border: 1px solid #e2e8f0; border-radius: 4px; padding: 3px 6px; }"

    # ================================================================
    #  渠道卡片构建
    # ================================================================
    def _build_channel_cards(self):
        """构建渠道选择卡片网格（2 列）"""
        for i, ch in enumerate(CHANNEL_REGISTRY):
            card = ChannelSelectCard(ch, recommend_score=0.5)
            card.toggled.connect(self._on_channel_toggled)
            self._channel_cards[ch["id"]] = card
            self._channel_grid.addWidget(card, i // 2, i % 2)

    # ================================================================
    #  内容来源加载
    # ================================================================
    def _load_content_list(self, source: str):
        """加载可发布内容列表"""
        self._content_list.clear()
        if source == "策划案库":
            plans = db.read_all_plans()
            for p in plans:
                self._content_list.append({
                    "id": p["id"],
                    "title": p["name"],
                    "type": p.get("type", "其他"),
                    "source": "plan",
                    "raw": p,
                })
        else:
            assets = db.read_all_assets()
            for a in assets:
                self._content_list.append({
                    "id": a["id"],
                    "title": a["name"],
                    "type": "短视频" if a.get("type") == "video" else "其他",
                    "source": "asset",
                    "raw": a,
                })
        self._content_list_widget.set_items(self._content_list)
        self._update_smart_match_scores()

    def _on_source_changed(self, text: str):
        self._selected_content = None
        self._load_content_list(text)
        self._variant_label.setText("请先选择内容来源")
        # 切换来源后重新计算渠道推荐分
        self._update_smart_match_scores()

    def _on_content_selected(self, content: dict):
        """选中某条内容后更新变体预览 + 渠道推荐分"""
        self._selected_content = content
        self._update_smart_match_scores()
        self._update_variant_preview()

    def _update_smart_match_scores(self):
        """根据当前内容类型刷新所有渠道卡片的推荐分徽章"""
        if not self._selected_content:
            for card in self._channel_cards.values():
                card.update_recommend_score(0.5)
            return

        content_type = self._selected_content.get("type", "其他")
        scores = smart_match_channels(content_type)
        score_map = dict(scores)
        for ch_id, card in self._channel_cards.items():
            card.update_recommend_score(score_map.get(ch_id, 0.3))

    def _update_variant_preview(self):
        """更新 A/B 标题变体预览"""
        if not self._selected_content:
            self._variant_label.setText("请先选择内容来源")
            return

        title = self._selected_content["title"]
        variants = []
        for ch in CHANNEL_REGISTRY[:4]:  # 展示前 4 个渠道的变体
            variant = generate_title_variant(title, ch["type"])
            variants.append(f"<b style='color:#1e293b;'>{ch['name']}:</b> {variant}")
        self._variant_label.setText("<br>".join(variants))

    # ================================================================
    #  渠道选择交互
    # ================================================================
    def _on_channel_toggled(self, channel_id: str, checked: bool):
        if checked:
            self._log_stream.append_log(f"已选中渠道: {self._get_channel_name(channel_id)}", "INFO")
        else:
            self._log_stream.append_log(f"已取消渠道: {self._get_channel_name(channel_id)}", "INFO")

    def _auto_select_channels(self):
        """智能匹配：自动勾选推荐分 ≥ 0.7 的渠道"""
        if not self._selected_content:
            QMessageBox.information(self, "提示", "请先选择内容来源")
            return

        content_type = self._selected_content.get("type", "其他")
        scores = smart_match_channels(content_type)
        selected_count = 0
        for ch_id, score in scores:
            if score >= 0.7:
                self._channel_cards[ch_id].set_checked(True)
                selected_count += 1
            else:
                self._channel_cards[ch_id].set_checked(False)

        self._log_stream.append_log(
            f"智能匹配完成 | 内容类型: {content_type} | 自动选中 {selected_count} 个渠道",
            "SYSTEM"
        )

    def _clear_channel_selection(self):
        for card in self._channel_cards.values():
            card.set_checked(False)
        self._log_stream.append_log("已清空所有渠道选择", "INFO")

    def _get_selected_channels(self) -> list:
        """获取当前选中的渠道字典列表"""
        result = []
        for ch in CHANNEL_REGISTRY:
            card = self._channel_cards.get(ch["id"])
            if card and card.is_checked():
                result.append(ch)
        return result

    def _get_channel_name(self, ch_id: str) -> str:
        for ch in CHANNEL_REGISTRY:
            if ch["id"] == ch_id:
                return ch["name"]
        return ch_id

    # ================================================================
    #  调度参数交互
    # ================================================================
    def _on_mode_changed(self, text: str):
        self._schedule_time.setEnabled(text == "定时发布")

    # ================================================================
    #  分发任务控制
    # ================================================================
    def _start_distribute(self):
        """启动分发任务"""
        if not self._selected_content:
            QMessageBox.warning(self, "提示", "请先选择要发布的内容")
            return

        channels = self._get_selected_channels()
        if not channels:
            QMessageBox.warning(self, "提示", "请至少选择一个发布渠道")
            return

        mode = self._mode_combo.currentText()
        if mode == "定时发布":
            schedule = self._schedule_time.text().strip()
            if not schedule:
                QMessageBox.warning(self, "提示", "请输入定时发布时刻")
                return
            self._log_stream.append_log(f"已设定定时发布 | 目标时刻: {schedule}", "SYSTEM")
            QMessageBox.information(self, "定时发布", f"已设定定时发布任务，目标时刻 {schedule}\n（演示版将立即执行模拟）")

        # 构建任务行
        self._clear_task_rows()
        for ch in channels:
            row = ChannelTaskRow(ch)
            self._task_rows[ch["id"]] = row
            self._task_layout.insertWidget(self._task_layout.count() - 1, row)
            row.start()

        # 启动调度器
        concurrency = self._concurrency_spin.value()
        self._scheduler.start(channels, self._selected_content, concurrency)

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._stats_label.setText("分发中...")

    def _stop_distribute(self):
        """终止分发任务"""
        self._scheduler.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._log_stream.append_log("分发任务已被手动终止", "WARN")
        self._stats_label.setText("已终止")

    def _clear_task_rows(self):
        """清空旧任务行"""
        for row in self._task_rows.values():
            row.setParent(None)
            row.deleteLater()
        self._task_rows.clear()

    # ================================================================
    #  调度器回调
    # ================================================================
    def _on_task_progress(self, ch_id: str, progress: int):
        row = self._task_rows.get(ch_id)
        if row:
            row.update_progress(progress)

    def _on_task_status(self, ch_id: str, status: str, extra: dict):
        row = self._task_rows.get(ch_id)
        if not row:
            return
        if status == "start":
            row.start()
        elif status == "success":
            row.mark_success()
        elif status == "failed":
            row.mark_failed()
        elif status == "retry":
            row.mark_retry(extra.get("attempt", 1))

        # 检查是否全部完成，更新统计
        self._check_completion()

    def _on_task_log(self, message: str, level: str):
        self._log_stream.append_log(message, level)
        self._log_count += 1

    def _check_completion(self):
        """检查任务是否全部完成"""
        stats = self._scheduler.get_stats()
        if stats["running"] == 0 and stats["total"] > 0:
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)
            summary = (
                f"完成 | 成功 {stats['success']}/{stats['total']} | "
                f"失败 {stats['failed']} | 平均耗时 {stats['avg_duration']:.2f}s | "
                f"成功率 {stats['success_rate']*100:.0f}%"
            )
            self._stats_label.setText(summary)
            self._log_stream.append_log("=" * 50, "SYSTEM")
            self._log_stream.append_log(summary, "SYSTEM")

    # ================================================================
    #  清理钩子
    # ================================================================
    def cleanup(self):
        """热重载前停止所有定时器，避免 C++ 对象悬空崩溃"""
        self._scheduler.stop()


# ============================================================
#  辅助：内容列表组件（封装 QListWidget + 点击信号）
# ============================================================
class ContentListWidget(QFrame):
    """
    简易内容列表封装，对外暴露 on_selected 回调。
    避免主模块直接操作 QListWidget 的样式与信号细节。
    """

    def __init__(self, on_selected_callback, parent=None):
        super().__init__(parent)
        self._on_selected = on_selected_callback
        self._items = []
        self.setObjectName("ContentListHelper")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: #ffffff; border: 1px solid #e2e8f0;
                border-radius: 8px; padding: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px 10px; border-radius: 6px;
                color: #334155;
            }
            QListWidget::item:hover { background: #f1f5f9; }
            QListWidget::item:selected {
                background: #e0f2fe; color: #0369a1;
                font-weight: 600;
            }
        """)
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

    def set_items(self, items: list):
        self._items = items
        self._list.clear()
        for item in items:
            wi = QListWidgetItem(f"[{item['id']}] {item['title']}")
            wi.setToolTip(f"类型: {item.get('type', '-')}")
            self._list.addItem(wi)
        if items:
            self._list.setCurrentRow(0)

    def _on_row_changed(self, row: int):
        if 0 <= row < len(self._items):
            self._on_selected(self._items[row])
