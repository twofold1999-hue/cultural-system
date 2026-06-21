"""
排期计划模块 (AssetsModule)
===========================
数字文化内容生产全生命周期排期工作台

核心能力：
- 多项目甘特图视图：任务、里程碑、依赖关系可视化
- 资源负荷分析：团队/场地/设备冲突自动检测
- 智能排期引擎：基于依赖与资源约束自动推算关键路径
- 排期模板库：短视频、纪录片、沉浸式展览一键套用
- 任务 CRUD 与进度跟踪
- 延期风险预警与成本估算

布局结构：
┌─────────────────────────────────────────────────────────────┐
│ [统计卡片: 总任务 | 进行中 | 已延期 | 已完成 | 预估成本]        │
│ [工具栏: 新建 | 删除 | 应用模板 | 自动排期 | 冲突检测 | 导出]  │
├──────────────┬──────────────────────────────┬───────────────┤
│ 任务列表      │       甘特图时间轴            │  详情/资源    │
│ (表格筛选    │  (QPainter 绘制任务条/依赖线   │  /冲突面板    │
│  双击编辑)   │   状态色/进度条/里程碑)       │               │
└──────────────┴──────────────────────────────┴───────────────┘
"""

import datetime
import json
from collections import defaultdict

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QWidget, QDialog,
    QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QDateEdit, QListWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QScrollArea, QGroupBox,
    QGridLayout, QCheckBox, QSizePolicy, QTabWidget
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

from views.modules.base_module import BaseBusinessModule
from database.mock_db import db


# ============================================================
#  常量与工具
# ============================================================

STATUS_MAP = {
    "not_started": ("未开始", "#94a3b8"),
    "in_progress": ("进行中", "#38bdf8"),
    "delayed":     ("已延期", "#f87171"),
    "completed":   ("已完成", "#34d399"),
}

PRIORITY_MAP = {
    "low":    ("低", "#94a3b8"),
    "medium": ("中", "#fbbf24"),
    "high":   ("高", "#fb923c"),
    "critical": ("紧急", "#ef4444"),
}

PHASE_MAP = {
    "pre_production": ("前期策划", "#818cf8"),
    "production":     ("制作执行", "#34d399"),
    "post_production":("后期制作", "#fbbf24"),
    "release":        ("发布运营", "#f472b6"),
}

RESOURCE_TYPE_ICON = {
    "team":      "👥",
    "venue":     "🏢",
    "equipment": "🖥",
}


def _parse_date(s: str) -> datetime.date:
    return datetime.date.fromisoformat(s)


def _fmt_date(d: datetime.date) -> str:
    return d.isoformat()


def _add_days(d: datetime.date, days: int) -> datetime.date:
    return d + datetime.timedelta(days=days)


def _date_range_overlap(s1, e1, s2, e2) -> bool:
    return max(s1, s2) <= min(e1, e2)


# ============================================================
#  子组件：甘特图视图
# ============================================================
class GanttChartWidget(QWidget):
    """
    自定义甘特图组件
    - 横向时间轴，任务按行排列
    - 支持状态色、进度条、依赖连线
    - 点击任务行发出 task_selected 信号
    """

    task_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = []
        self._selected_task_id = None
        self._row_height = 36
        self._header_height = 32
        self._left_label_width = 0  # 甘特图内部不画左侧标签
        self._day_width = 28
        self._start_date = None
        self._end_date = None
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_tasks(self, tasks: list):
        self._tasks = tasks
        self._update_date_range()
        days = (self._end_date - self._start_date).days + 1
        needed_width = days * self._day_width + self._left_label_width + 20
        self.setMinimumWidth(max(260, needed_width))
        self.update()

    def set_selected_task(self, task_id: str):
        self._selected_task_id = task_id
        self.update()

    def _update_date_range(self):
        if not self._tasks:
            today = datetime.date.today()
            self._start_date = today
            self._end_date = _add_days(today, 14)
            return
        dates = []
        for t in self._tasks:
            dates.append(_parse_date(t["start"]))
            dates.append(_parse_date(t["end"]))
        min_d = min(dates)
        max_d = max(dates)
        self._start_date = _add_days(min_d, -2)
        self._end_date = _add_days(max_d, 5)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # 背景
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        days = (self._end_date - self._start_date).days + 1
        total_width = max(w, days * self._day_width + self._left_label_width + 20)

        # 表头：日期
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawLine(0, self._header_height, total_width, self._header_height)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        for i in range(days):
            d = _add_days(self._start_date, i)
            x = self._left_label_width + i * self._day_width
            # 周末背景
            if d.weekday() >= 5:
                painter.fillRect(x, self._header_height, self._day_width, h - self._header_height,
                                 QColor("#f8fafc"))
            # 日期文字
            painter.setPen(QColor("#64748b"))
            painter.drawText(x + 2, 4, self._day_width - 4, self._header_height - 8,
                             Qt.AlignmentFlag.AlignCenter,
                             f"{d.month}/{d.day}")
            # 竖线
            painter.setPen(QPen(QColor("#e2e8f0"), 1))
            painter.drawLine(x, 0, x, h)

        # 今天标记线
        today = datetime.date.today()
        if self._start_date <= today <= self._end_date:
            x_today = self._left_label_width + (today - self._start_date).days * self._day_width
            painter.setPen(QPen(QColor("#ef4444"), 2))
            painter.drawLine(x_today, self._header_height, x_today, h)

        # 任务条
        for idx, t in enumerate(self._tasks):
            y = self._header_height + 10 + idx * (self._row_height + 8)
            self._draw_task_bar(painter, t, y)

        # 依赖线（在任务条上方）
        self._draw_dependencies(painter)

        painter.end()

    def _draw_task_bar(self, painter: QPainter, task: dict, y: int):
        start = _parse_date(task["start"])
        end = _parse_date(task["end"])
        offset = (start - self._start_date).days
        duration = (end - start).days + 1
        x = self._left_label_width + offset * self._day_width
        bar_w = max(duration * self._day_width - 4, 4)
        bar_h = self._row_height

        status_key = task.get("status", "not_started")
        status_name, base_color = STATUS_MAP.get(status_key, STATUS_MAP["not_started"])
        phase_name, phase_color = PHASE_MAP.get(task.get("phase", "production"), PHASE_MAP["production"])

        # 选中高亮外框
        if task["id"] == self._selected_task_id:
            painter.setPen(QPen(QColor("#0ea5e9"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(x - 2, y - 2, bar_w + 4, bar_h + 4, 6, 6)

        # 任务条底色（按阶段）
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(phase_color))
        painter.drawRoundedRect(x, y, bar_w, bar_h, 5, 5)

        # 进度条（按状态色叠加）
        progress = min(100, max(0, task.get("progress", 0)))
        if progress > 0:
            pw = int(bar_w * progress / 100)
            painter.setBrush(QColor(base_color))
            painter.drawRoundedRect(x, y, pw, bar_h, 5, 5)

        # 任务名称
        painter.setPen(QColor("#1e293b"))
        painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
        text = f"{task['name']} ({status_name})"
        painter.drawText(x + 6, y + 4, bar_w - 12, bar_h - 8,
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         text)

    def _draw_dependencies(self, painter: QPainter):
        # 建立任务 -> 行索引映射
        idx_map = {t["id"]: i for i, t in enumerate(self._tasks)}
        pen = QPen(QColor("#94a3b8"))
        pen.setWidthF(1.5)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        for t in self._tasks:
            if not t.get("dependencies"):
                continue
            dep_idx = idx_map.get(t["id"])
            if dep_idx is None:
                continue
            for dep_id in t["dependencies"]:
                src_idx = idx_map.get(dep_id)
                if src_idx is None:
                    continue
                src_task = self._tasks[src_idx]
                src_end = _parse_date(src_task["end"])
                tgt_start = _parse_date(t["start"])
                x1 = self._left_label_width + (src_end - self._start_date).days * self._day_width + self._day_width
                y1 = self._header_height + 10 + src_idx * (self._row_height + 8) + self._row_height // 2
                x2 = self._left_label_width + (tgt_start - self._start_date).days * self._day_width
                y2 = self._header_height + 10 + dep_idx * (self._row_height + 8) + self._row_height // 2
                painter.drawLine(x1, y1, x2, y2)
                # 箭头
                painter.drawLine(x2, y2, x2 - 5, y2 - 3)
                painter.drawLine(x2, y2, x2 - 5, y2 + 3)

    def mousePressEvent(self, event):
        # 根据 y 坐标判断点击了哪一行任务
        y = event.position().y()
        if y < self._header_height:
            return
        row = int((y - self._header_height - 10) / (self._row_height + 8))
        if 0 <= row < len(self._tasks):
            self._selected_task_id = self._tasks[row]["id"]
            self.task_selected.emit(self._selected_task_id)
            self.update()


# ============================================================
#  子组件：任务编辑对话框
# ============================================================
class TaskEditDialog(QDialog):
    """任务新建/编辑对话框"""

    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self._task = task or {}
        self.setWindowTitle("编辑任务" if task else "新建任务")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.input_name = QLineEdit(self._task.get("name", ""))
        self.input_name.setPlaceholderText("任务名称")
        layout.addRow("任务名称:", self.input_name)

        self.input_project = QLineEdit(self._task.get("project", ""))
        self.input_project.setPlaceholderText("所属项目")
        layout.addRow("所属项目:", self.input_project)

        self.input_owner = QLineEdit(self._task.get("owner", ""))
        self.input_owner.setPlaceholderText("负责人")
        layout.addRow("负责人:", self.input_owner)

        self.combo_status = QComboBox()
        for k, (name, _) in STATUS_MAP.items():
            self.combo_status.addItem(name, userData=k)
        self.combo_status.setCurrentIndex(self.combo_status.findData(self._task.get("status", "not_started")))
        layout.addRow("状态:", self.combo_status)

        self.combo_priority = QComboBox()
        for k, (name, _) in PRIORITY_MAP.items():
            self.combo_priority.addItem(name, userData=k)
        self.combo_priority.setCurrentIndex(self.combo_priority.findData(self._task.get("priority", "medium")))
        layout.addRow("优先级:", self.combo_priority)

        self.combo_phase = QComboBox()
        for k, (name, _) in PHASE_MAP.items():
            self.combo_phase.addItem(name, userData=k)
        self.combo_phase.setCurrentIndex(self.combo_phase.findData(self._task.get("phase", "production")))
        layout.addRow("阶段:", self.combo_phase)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.fromString(self._task.get("start", datetime.date.today().isoformat()), Qt.DateFormat.ISODate))
        layout.addRow("开始日期:", self.date_start)

        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(1, 365)
        self.spin_duration.setValue(self._task.get("duration", 3))
        layout.addRow("持续天数:", self.spin_duration)

        self.spin_progress = QSpinBox()
        self.spin_progress.setRange(0, 100)
        self.spin_progress.setSuffix("%")
        self.spin_progress.setValue(self._task.get("progress", 0))
        layout.addRow("完成进度:", self.spin_progress)

        # 资源多选
        self.resource_checks = []
        res_group = QGroupBox("占用资源")
        res_layout = QGridLayout(res_group)
        resources = db.get_schedule_resources()
        selected = set(self._task.get("resources", []))
        for i, r in enumerate(resources):
            cb = QCheckBox(f"{RESOURCE_TYPE_ICON.get(r['type'], '')} {r['name']}")
            cb.setProperty("rid", r["id"])
            cb.setChecked(r["id"] in selected)
            self.resource_checks.append(cb)
            res_layout.addWidget(cb, i // 2, i % 2)
        layout.addRow(res_group)

        # 依赖选择
        self.combo_dependency = QComboBox()
        self.combo_dependency.addItem("无", userData="")
        for t in db.get_schedule_tasks():
            if t["id"] != self._task.get("id"):
                self.combo_dependency.addItem(f"{t['name']} ({t['id']})", userData=t["id"])
        deps = self._task.get("dependencies", [])
        if deps:
            idx = self.combo_dependency.findData(deps[0])
            if idx >= 0:
                self.combo_dependency.setCurrentIndex(idx)
        layout.addRow("前置依赖:", self.combo_dependency)

        # 按钮
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("保存")
        btn_ok.setObjectName("PrimaryButton")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        start = self.date_start.date().toString(Qt.DateFormat.ISODate)
        start_d = _parse_date(start)
        end_d = _add_days(start_d, self.spin_duration.value() - 1)
        resources = [cb.property("rid") for cb in self.resource_checks if cb.isChecked()]
        dep_id = self.combo_dependency.currentData()
        dependencies = [dep_id] if dep_id else []
        return {
            "name": self.input_name.text().strip(),
            "project": self.input_project.text().strip(),
            "owner": self.input_owner.text().strip(),
            "status": self.combo_status.currentData(),
            "priority": self.combo_priority.currentData(),
            "phase": self.combo_phase.currentData(),
            "start": start,
            "end": _fmt_date(end_d),
            "duration": self.spin_duration.value(),
            "progress": self.spin_progress.value(),
            "resources": resources,
            "dependencies": dependencies,
        }


# ============================================================
#  子组件：发布节点时间轴
# ============================================================
class PublishTimelineWidget(QWidget):
    """
    发布节点流量共振时间轴
    - X 轴：00:00 ~ 24:00
    - 红色圆点标记已排期节点位置，上方显示共振指数
    - 灰色曲线模拟全天流量趋势
    """

    node_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes = []
        self._selected_id = None
        self._padding_top = 40
        self._padding_bottom = 40
        self._padding_lr = 48
        self.setMinimumHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_nodes(self, nodes: list):
        self._nodes = nodes
        self.update()

    def set_selected_node(self, nid: str):
        self._selected_id = nid
        self.update()

    def _time_to_x(self, time_str: str, width: int) -> float:
        import re
        m = re.search(r"(\d+):(\d+)", time_str)
        if not m:
            return self._padding_lr
        h = int(m.group(1)) + int(m.group(2)) / 60.0
        ratio = max(0.0, min(24.0, h)) / 24.0
        plot_w = width - self._padding_lr * 2
        return self._padding_lr + plot_w * ratio

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        plot_h = h - self._padding_top - self._padding_bottom
        plot_y = self._padding_top
        plot_w = w - self._padding_lr * 2

        # 基线
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawLine(self._padding_lr, plot_y + plot_h, w - self._padding_lr, plot_y + plot_h)

        # 全天流量趋势曲线（模拟正弦叠加）
        import math
        points = []
        for i in range(0, plot_w + 1, 4):
            ratio = i / plot_w
            hour = ratio * 24
            # 早高峰、午高峰、晚高峰
            y_ratio = (
                0.15 * math.sin((hour - 8) * math.pi / 4) +
                0.25 * math.sin((hour - 12) * math.pi / 3) +
                0.35 * math.sin((hour - 20) * math.pi / 5) +
                0.25
            )
            y_ratio = max(0.05, min(0.95, y_ratio))
            x = self._padding_lr + i
            y = plot_y + plot_h * (1 - y_ratio)
            points.append((x, y))

        if len(points) > 1:
            pen = QPen(QColor("#cbd5e1"))
            pen.setWidthF(2)
            painter.setPen(pen)
            for i in range(len(points) - 1):
                painter.drawLine(int(points[i][0]), int(points[i][1]),
                                 int(points[i + 1][0]), int(points[i + 1][1]))

        # 坐标刻度
        painter.setPen(QColor("#94a3b8"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for hour in range(0, 25, 3):
            x = self._padding_lr + (hour / 24.0) * plot_w
            painter.drawLine(int(x), plot_y + plot_h, int(x), plot_y + plot_h + 5)
            painter.drawText(int(x) - 14, plot_y + plot_h + 18, 28, 14,
                             Qt.AlignmentFlag.AlignCenter, f"{hour:02d}:00")

        # 节点红点
        for n in self._nodes:
            x = self._time_to_x(n.get("time", "12:00"), w)
            score = n.get("resonance", 50.0)
            y = plot_y + plot_h * (1 - score / 100.0)

            # 选中放大
            radius = 8 if n["id"] == self._selected_id else 5
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#ef4444"))
            painter.drawEllipse(int(x) - radius, int(y) - radius, radius * 2, radius * 2)

            # 指数文字
            painter.setPen(QColor("#ef4444"))
            painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
            painter.drawText(int(x) - 24, int(y) - radius - 16, 48, 14,
                             Qt.AlignmentFlag.AlignCenter, f"{score:.2f}%")

        painter.end()

    def mousePressEvent(self, event):
        x = event.position().x()
        best, best_dist = None, 1e9
        for n in self._nodes:
            nx = self._time_to_x(n.get("time", "12:00"), self.width())
            dist = abs(nx - x)
            if dist < best_dist and dist < 20:
                best_dist = dist
                best = n
        if best:
            self._selected_id = best["id"]
            self.node_selected.emit(best["id"])
            self.update()


# ============================================================
#  子组件：发布节点编辑对话框
# ============================================================
class NodeEditDialog(QDialog):
    """发布节点新建/编辑对话框"""

    def __init__(self, node=None, parent=None):
        super().__init__(parent)
        self._node = node or {}
        self.setWindowTitle("编辑排期节点" if node else "插入排期节点")
        self.setMinimumWidth(360)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.input_title = QLineEdit(self._node.get("title", ""))
        self.input_title.setPlaceholderText("方案标题")
        layout.addRow("方案标题:", self.input_title)

        self.input_content = QLineEdit(self._node.get("content", ""))
        self.input_content.setPlaceholderText("内容方案")
        layout.addRow("内容方案:", self.input_content)

        self.combo_platform = QComboBox()
        platforms = ["WeChat/朋友圈", "抖音/TikTok", "小红书/RED", "微博/Weibo", "Bilibili", "知乎/Zhihu"]
        for p in platforms:
            self.combo_platform.addItem(p)
        current = self._node.get("platform", "抖音/TikTok")
        idx = self.combo_platform.findText(current)
        if idx >= 0:
            self.combo_platform.setCurrentIndex(idx)
        layout.addRow("分发渠道:", self.combo_platform)

        self.time_edit = QLineEdit(self._node.get("time", "12:00"))
        self.time_edit.setPlaceholderText("如 21:00")
        layout.addRow("发布时间:", self.time_edit)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("保存")
        btn_ok.setObjectName("PrimaryButton")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

    def get_data(self) -> dict:
        return {
            "title": self.input_title.text().strip(),
            "content": self.input_content.text().strip(),
            "platform": self.combo_platform.currentText(),
            "time": self.time_edit.text().strip(),
        }


# ============================================================
#  主模块
# ============================================================
class AssetsModule(BaseBusinessModule):
    """排期计划主模块：包含内容生产排期与发布节点排期"""

    def __init__(self):
        super().__init__("内容生产排期与资源调度")

    def setup_ui(self):
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(12)

        # ---------- 顶部标题 ----------
        header_row = QHBoxLayout()
        title = QLabel("📅 内容生产排期与资源调度")
        title.setObjectName("SectionLabel")
        header_row.addWidget(title)
        header_row.addStretch()
        self.layout.addLayout(header_row)

        # ---------- 标签页 ----------
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.layout.addWidget(self.tab_widget, 1)

        # ==================== Tab 1: 内容生产排期 ====================
        self._setup_production_tab()

        # ==================== Tab 2: 发布节点排期（参考工程风格） ====================
        self._setup_publish_tab()

        self._refresh_all()

    def _setup_production_tab(self):
        """内容生产排期页：保留原有甘特图能力"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 8, 0, 0)
        tab_layout.setSpacing(12)

        # 统计卡片
        self._stat_labels = {}
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        for key, label, color in [
            ("total", "总任务", "#64748b"),
            ("in_progress", "进行中", "#38bdf8"),
            ("delayed", "已延期", "#f87171"),
            ("completed", "已完成", "#34d399"),
            ("total_cost", "预估成本", "#a78bfa"),
        ]:
            card = QFrame()
            card.setObjectName("StatCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 10, 14, 10)
            tl = QLabel(label)
            tl.setObjectName("StatCardTitle")
            vl = QLabel("--")
            vl.setObjectName("StatCardValue")
            vl.setStyleSheet(f"color: {color};")
            self._stat_labels[key] = vl
            cl.addWidget(tl)
            cl.addWidget(vl)
            stats_row.addWidget(card, 1)
        tab_layout.addLayout(stats_row)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_new = QPushButton("➕ 新建任务")
        btn_new.setObjectName("BtnCreate")
        btn_new.clicked.connect(self._on_new_task)
        toolbar.addWidget(btn_new)

        btn_delete = QPushButton("🗑 删除任务")
        btn_delete.clicked.connect(self._on_delete_task)
        toolbar.addWidget(btn_delete)

        btn_template = QPushButton("📋 应用模板")
        btn_template.clicked.connect(self._on_apply_template)
        toolbar.addWidget(btn_template)

        btn_auto = QPushButton("🧠 自动排期")
        btn_auto.setObjectName("PrimaryButton")
        btn_auto.clicked.connect(self._on_auto_schedule)
        toolbar.addWidget(btn_auto)

        btn_conflict = QPushButton("⚠ 冲突检测")
        btn_conflict.clicked.connect(self._on_detect_conflicts)
        toolbar.addWidget(btn_conflict)

        btn_export = QPushButton("📤 导出排期")
        btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(btn_export)

        toolbar.addStretch()
        tab_layout.addLayout(toolbar)

        # 主体三栏
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_layout.addWidget(QLabel("任务列表"))

        self.task_table = QTableWidget(0, 6)
        self.task_table.setHorizontalHeaderLabels(["ID", "任务", "负责人", "开始", "结束", "状态"])
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.task_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.task_table.cellDoubleClicked.connect(self._on_edit_task)
        left_layout.addWidget(self.task_table)
        main_splitter.addWidget(left_panel)

        center_panel = QFrame()
        center_panel.setObjectName("ModulePanel")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(8)
        center_layout.addWidget(QLabel("甘特图时间轴"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.gantt = GanttChartWidget()
        self.gantt.task_selected.connect(self._on_gantt_task_selected)
        scroll.setWidget(self.gantt)
        center_layout.addWidget(scroll)
        main_splitter.addWidget(center_panel)

        right_panel = QFrame()
        right_panel.setObjectName("ModulePanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)

        detail_group = QGroupBox("任务详情")
        detail_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        detail_layout = QFormLayout(detail_group)
        detail_layout.setSpacing(6)
        self.detail_name = QLabel("请选择任务")
        self.detail_project = QLabel("-")
        self.detail_owner = QLabel("-")
        self.detail_phase = QLabel("-")
        self.detail_priority = QLabel("-")
        self.detail_progress = QLabel("-")
        detail_layout.addRow("名称:", self.detail_name)
        detail_layout.addRow("项目:", self.detail_project)
        detail_layout.addRow("负责人:", self.detail_owner)
        detail_layout.addRow("阶段:", self.detail_phase)
        detail_layout.addRow("优先级:", self.detail_priority)
        detail_layout.addRow("进度:", self.detail_progress)
        right_layout.addWidget(detail_group)

        res_group = QGroupBox("资源占用")
        res_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        res_layout = QVBoxLayout(res_group)
        self.res_list = QListWidget()
        self.res_list.setMaximumHeight(120)
        res_layout.addWidget(self.res_list)
        right_layout.addWidget(res_group)

        conflict_group = QGroupBox("冲突预警")
        conflict_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        conflict_layout = QVBoxLayout(conflict_group)
        self.conflict_list = QListWidget()
        self.conflict_list.setMaximumHeight(140)
        conflict_layout.addWidget(self.conflict_list)
        right_layout.addWidget(conflict_group)

        right_layout.addStretch()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([280, 560, 280])
        tab_layout.addWidget(main_splitter, 1)

        self.tab_widget.addTab(tab, "内容生产排期")

    def _setup_publish_tab(self):
        """发布节点排期页：参考工程风格，含时间轴与 CPS 推演"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 8, 0, 0)
        tab_layout.setSpacing(12)

        # 顶部操作按钮
        top_row = QHBoxLayout()
        top_row.addStretch()
        btn_insert = QPushButton("➕ 插入排期节点")
        btn_insert.setObjectName("PrimaryButton")
        btn_insert.clicked.connect(self._on_insert_node)
        top_row.addWidget(btn_insert)
        tab_layout.addLayout(top_row)

        # 流量共振时间轴
        timeline_panel = QFrame()
        timeline_panel.setObjectName("ModulePanel")
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.setContentsMargins(12, 12, 12, 12)
        timeline_layout.addWidget(QLabel("流量共振时间轴"))
        self.timeline = PublishTimelineWidget()
        self.timeline.node_selected.connect(self._on_timeline_node_selected)
        timeline_layout.addWidget(self.timeline)
        tab_layout.addWidget(timeline_panel)

        # 下方：节点表格 + 详情
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左：节点表格
        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.addWidget(QLabel("节点排期表"))

        self.node_table = QTableWidget(0, 5)
        self.node_table.setHorizontalHeaderLabels(["节点ID", "内容方案", "目标平台", "时序位置", "共振指数"])
        self.node_table.verticalHeader().setVisible(False)
        self.node_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.node_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.node_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.node_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.node_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.node_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.node_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.node_table.itemSelectionChanged.connect(self._on_node_table_selection_changed)
        self.node_table.cellDoubleClicked.connect(self._on_edit_node)
        left_layout.addWidget(self.node_table)

        # 表格下方小工具栏
        node_toolbar = QHBoxLayout()
        btn_edit_node = QPushButton("编辑节点")
        btn_edit_node.clicked.connect(self._on_edit_node_from_toolbar)
        node_toolbar.addWidget(btn_edit_node)
        btn_del_node = QPushButton("删除节点")
        btn_del_node.clicked.connect(self._on_delete_node)
        node_toolbar.addWidget(btn_del_node)
        node_toolbar.addStretch()
        left_layout.addLayout(node_toolbar)

        bottom_splitter.addWidget(left_panel)

        # 右：节点排期校准 + CPS 报告
        right_panel = QFrame()
        right_panel.setObjectName("ModulePanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)

        calib_group = QGroupBox("节点排期校准")
        calib_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        calib_layout = QFormLayout(calib_group)
        calib_layout.setSpacing(8)
        self.node_detail_title = QLineEdit()
        self.node_detail_title.setEnabled(False)
        self.node_detail_platform = QComboBox()
        self.node_detail_platform.addItems(["微信朋友圈", "抖音短视频", "小红书", "微博", "哔哩哔哩", "知乎"])
        self.node_detail_time = QLineEdit()
        calib_layout.addRow("方案标题:", self.node_detail_title)
        calib_layout.addRow("分发渠道:", self.node_detail_platform)
        calib_layout.addRow("发布时间:", self.node_detail_time)
        right_layout.addWidget(calib_group)

        report_group = QGroupBox("引擎推演报告")
        report_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        report_layout = QVBoxLayout(report_group)
        self.report_score = QLabel("流量共振指数: --")
        self.report_score.setStyleSheet("font-size:18px;font-weight:700;color:#0ea5e9;")
        self.report_warning = QLabel("请选择节点查看推演报告")
        self.report_warning.setWordWrap(True)
        self.report_warning.setStyleSheet("color:#64748b;line-height:1.5;")
        report_layout.addWidget(self.report_score)
        report_layout.addWidget(self.report_warning)
        right_layout.addWidget(report_group)

        # 提交校准按钮
        btn_submit = QPushButton("💾 提交排期校准")
        btn_submit.setObjectName("PrimaryButton")
        btn_submit.clicked.connect(self._on_submit_node_calibration)
        right_layout.addWidget(btn_submit)
        right_layout.addStretch()

        bottom_splitter.addWidget(right_panel)
        bottom_splitter.setSizes([500, 360])
        tab_layout.addWidget(bottom_splitter, 1)

        self.tab_widget.addTab(tab, "发布节点排期")

    # ============================================================
    #  数据刷新
    # ============================================================
    def _refresh_all(self):
        # 内容生产排期
        self._tasks = db.get_schedule_tasks()
        self._refresh_stats()
        self._refresh_task_table()
        self.gantt.set_tasks(self._tasks)
        self._detect_conflicts_internal()
        # 发布节点排期
        self._nodes = db.get_publish_nodes()
        self._refresh_node_table()
        self.timeline.set_nodes(self._nodes)
        self._show_node_detail(None)

    def _refresh_node_table(self):
        self.node_table.setRowCount(len(self._nodes))
        for r, n in enumerate(self._nodes):
            self.node_table.setItem(r, 0, QTableWidgetItem(n["id"]))
            self.node_table.setItem(r, 1, QTableWidgetItem(n.get("content", "")))
            self.node_table.setItem(r, 2, QTableWidgetItem(n.get("platform", "")))
            self.node_table.setItem(r, 3, QTableWidgetItem(n.get("time", "")))
            score = n.get("resonance", 0.0)
            item = QTableWidgetItem(f"{score:.2f}%")
            item.setForeground(QColor("#ef4444"))
            self.node_table.setItem(r, 4, item)

    def _refresh_stats(self):
        stats = db.get_schedule_stats()
        self._stat_labels["total"].setText(str(stats["total"]))
        self._stat_labels["in_progress"].setText(str(stats["in_progress"]))
        self._stat_labels["delayed"].setText(str(stats["delayed"]))
        self._stat_labels["completed"].setText(str(stats["completed"]))
        self._stat_labels["total_cost"].setText(f"¥{stats['total_cost']:,}")

    def _refresh_task_table(self):
        self.task_table.setRowCount(len(self._tasks))
        for r, t in enumerate(self._tasks):
            self.task_table.setItem(r, 0, QTableWidgetItem(t["id"]))
            self.task_table.setItem(r, 1, QTableWidgetItem(t["name"]))
            self.task_table.setItem(r, 2, QTableWidgetItem(t.get("owner", "-")))
            self.task_table.setItem(r, 3, QTableWidgetItem(t["start"]))
            self.task_table.setItem(r, 4, QTableWidgetItem(t["end"]))
            status_key = t.get("status", "not_started")
            status_name, color = STATUS_MAP.get(status_key, STATUS_MAP["not_started"])
            item = QTableWidgetItem(status_name)
            item.setForeground(QColor(color))
            self.task_table.setItem(r, 5, item)

    def _show_task_detail(self, task_id: str):
        task = db.get_schedule_task_by_id(task_id)
        if not task:
            return
        self.detail_name.setText(task["name"])
        self.detail_project.setText(task.get("project", "-"))
        self.detail_owner.setText(task.get("owner", "-"))
        phase_name, _ = PHASE_MAP.get(task.get("phase", "production"), PHASE_MAP["production"])
        self.detail_phase.setText(phase_name)
        priority_name, pcolor = PRIORITY_MAP.get(task.get("priority", "medium"), PRIORITY_MAP["medium"])
        self.detail_priority.setText(f"<span style='color:{pcolor};'>{priority_name}</span>")
        self.detail_progress.setText(f"{task.get('progress', 0)}%")

        self.res_list.clear()
        for rid in task.get("resources", []):
            r = db.get_schedule_resource_by_id(rid)
            if r:
                icon = RESOURCE_TYPE_ICON.get(r["type"], "")
                self.res_list.addItem(f"{icon} {r['name']}  ¥{r['cost_per_day']}/天")
        if not task.get("resources"):
            self.res_list.addItem("未分配资源")

    # ============================================================
    #  交互事件
    # ============================================================
    def _on_table_selection_changed(self):
        rows = self.task_table.selectedIndexes()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self._tasks):
            task_id = self._tasks[row]["id"]
            self._selected_task_id = task_id
            self.gantt.set_selected_task(task_id)
            self._show_task_detail(task_id)

    def _on_gantt_task_selected(self, task_id: str):
        self._selected_task_id = task_id
        self.gantt.set_selected_task(task_id)
        self._show_task_detail(task_id)
        # 同步高亮表格
        for r, t in enumerate(self._tasks):
            if t["id"] == task_id:
                self.task_table.selectRow(r)
                break

    def _on_new_task(self):
        dlg = TaskEditDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "校验失败", "任务名称不能为空")
            return
        db.add_schedule_task(data)
        self._refresh_all()

    def _on_edit_task(self, row, col):
        if row < 0 or row >= len(self._tasks):
            return
        task = self._tasks[row]
        dlg = TaskEditDialog(task=task, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        db.update_schedule_task(task["id"], data)
        self._refresh_all()

    def _on_delete_task(self):
        rows = self.task_table.selectedIndexes()
        if not rows:
            QMessageBox.information(self, "提示", "请先选择要删除的任务")
            return
        row = rows[0].row()
        task = self._tasks[row]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除任务 [{task['name']}] 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        db.delete_schedule_task(task["id"])
        self._refresh_all()

    # ============================================================
    #  模板、自动排期、冲突检测、导出
    # ============================================================
    def _on_apply_template(self):
        templates = db.get_schedule_templates()
        items = [t["name"] for t in templates]
        if not items:
            QMessageBox.information(self, "提示", "暂无可用模板")
            return
        # 简单弹窗选择
        dlg = QDialog(self)
        dlg.setWindowTitle("选择排期模板")
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("请选择一个模板快速生成任务序列:"))
        list_widget = QListWidget()
        for name in items:
            list_widget.addItem(name)
        layout.addWidget(list_widget)
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("应用")
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        selected = list_widget.currentRow()
        if selected < 0:
            return
        tpl = templates[selected]
        # 以今天为起点生成任务链
        import datetime
        cursor = datetime.date.today()
        for task_tpl in tpl["tasks"]:
            duration = task_tpl["duration"]
            end = _add_days(cursor, duration - 1)
            db.add_schedule_task({
                "name": task_tpl["name"],
                "project": tpl["name"],
                "owner": "待分配",
                "start": _fmt_date(cursor),
                "end": _fmt_date(end),
                "duration": duration,
                "status": "not_started",
                "priority": "medium",
                "phase": task_tpl["phase"],
                "progress": 0,
                "resources": [],
                "dependencies": [],
            })
            cursor = _add_days(end, 1)
        self._refresh_all()
        QMessageBox.information(self, "完成", f"已应用模板：{tpl['name']}")

    def _on_auto_schedule(self):
        """
        智能排期：
        1. 按依赖关系拓扑排序
        2. 前置任务结束后第二天开始
        3. 保持持续天数不变
        """
        tasks = db.get_schedule_tasks()
        if not tasks:
            QMessageBox.information(self, "提示", "当前没有任务可排期")
            return

        # 建立 ID -> 任务索引映射
        id_to_idx = {t["id"]: i for i, t in enumerate(tasks)}
        # 简单拓扑：反复找没有未处理依赖的任务
        remaining = set(range(len(tasks)))
        ordered = []
        while remaining:
            progressed = False
            for idx in list(remaining):
                deps = tasks[idx].get("dependencies", [])
                if all(d in id_to_idx and id_to_idx[d] not in remaining for d in deps):
                    ordered.append(idx)
                    remaining.remove(idx)
                    progressed = True
            if not progressed:
                # 有循环依赖，按原顺序处理剩余
                ordered.extend(sorted(remaining, key=lambda i: tasks[i]["start"]))
                break

        base = datetime.date.today()
        for idx in ordered:
            t = tasks[idx]
            deps = t.get("dependencies", [])
            if deps:
                # 取前置任务最大结束日 + 1
                max_end = base
                for dep_id in deps:
                    dep = db.get_schedule_task_by_id(dep_id)
                    if dep:
                        dep_end = _parse_date(dep["end"])
                        if dep_end > max_end:
                            max_end = dep_end
                new_start = _add_days(max_end, 1)
            else:
                new_start = base
            new_end = _add_days(new_start, t["duration"] - 1)
            db.update_schedule_task(t["id"], {
                "start": _fmt_date(new_start),
                "end": _fmt_date(new_end),
            })
        self._refresh_all()
        QMessageBox.information(self, "完成", "已按依赖关系重新推算排期")

    def _on_detect_conflicts(self):
        conflicts = self._detect_conflicts_internal()
        if not conflicts:
            QMessageBox.information(self, "冲突检测", "未检测到资源冲突或依赖异常")
        else:
            QMessageBox.warning(self, "冲突检测", f"检测到 {len(conflicts)} 项冲突，请查看右侧面板")

    def _detect_conflicts_internal(self):
        """
        冲突检测逻辑：
        1. 同一资源在同一时间段被多个任务占用（按 capacity 判断）
        2. 任务开始日期早于前置依赖结束日期
        3. 已延期任务预警
        """
        self.conflict_list.clear()
        conflicts = []
        tasks = db.get_schedule_tasks()
        today = datetime.date.today()

        # 资源时段占用
        resource_usage = defaultdict(list)  # rid -> [(start, end, task_name)]
        for t in tasks:
            s = _parse_date(t["start"])
            e = _parse_date(t["end"])
            for rid in t.get("resources", []):
                resource_usage[rid].append((s, e, t["name"], t["id"]))

        for rid, usages in resource_usage.items():
            r = db.get_schedule_resource_by_id(rid)
            if not r:
                continue
            capacity = r.get("capacity", 1)
            # 检查每一天的占用是否超过容量
            for i in range(len(usages)):
                for j in range(i + 1, len(usages)):
                    s1, e1, name1, _ = usages[i]
                    s2, e2, name2, _ = usages[j]
                    if _date_range_overlap(s1, e1, s2, e2):
                        # 简单模型：只处理 capacity=1 的资源冲突
                        if capacity == 1:
                            msg = f"资源冲突：{r['name']} 在 {max(s1,s2)} ~ {min(e1,e2)} 被 [{name1}] 和 [{name2}] 同时占用"
                            conflicts.append(msg)
                            self.conflict_list.addItem(msg)

        # 依赖异常
        for t in tasks:
            s = _parse_date(t["start"])
            for dep_id in t.get("dependencies", []):
                dep = db.get_schedule_task_by_id(dep_id)
                if not dep:
                    msg = f"依赖异常：[{t['name']}] 依赖的任务 {dep_id} 不存在"
                    conflicts.append(msg)
                    self.conflict_list.addItem(msg)
                    continue
                dep_end = _parse_date(dep["end"])
                if s <= dep_end:
                    msg = f"依赖异常：[{t['name']}] 开始于 {t['start']}，但前置 [{dep['name']}] 结束于 {dep['end']}"
                    conflicts.append(msg)
                    self.conflict_list.addItem(msg)

        # 延期预警
        for t in tasks:
            if t.get("status") == "delayed":
                msg = f"延期预警：[{t['name']}] 当前状态为已延期"
                conflicts.append(msg)
                self.conflict_list.addItem(msg)
            elif t.get("status") in ("not_started", "in_progress"):
                e = _parse_date(t["end"])
                if e < today:
                    msg = f"超期风险：[{t['name']}] 计划结束于 {t['end']}，已过期"
                    conflicts.append(msg)
                    self.conflict_list.addItem(msg)

        if not conflicts:
            self.conflict_list.addItem("暂无冲突")
        return conflicts

    def _on_export(self):
        tasks = db.get_schedule_tasks()
        if not tasks:
            QMessageBox.information(self, "提示", "没有可导出的排期数据")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出排期", "schedule_export.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "export_at": datetime.datetime.now().isoformat(),
                    "tasks": tasks,
                    "stats": db.get_schedule_stats(),
                }, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "完成", f"已导出到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ============================================================
    #  发布节点排期交互
    # ============================================================
    def _on_insert_node(self):
        dlg = NodeEditDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["title"]:
            QMessageBox.warning(self, "校验失败", "方案标题不能为空")
            return
        if not data["content"]:
            data["content"] = data["title"]
        db.add_publish_node(data)
        self._refresh_all()

    def _on_edit_node(self, row, col):
        if row < 0 or row >= len(self._nodes):
            return
        node = self._nodes[row]
        self._edit_node(node)

    def _on_edit_node_from_toolbar(self):
        rows = self.node_table.selectedIndexes()
        if not rows:
            QMessageBox.information(self, "提示", "请先选择要编辑的节点")
            return
        row = rows[0].row()
        if row < len(self._nodes):
            self._edit_node(self._nodes[row])

    def _edit_node(self, node: dict):
        dlg = NodeEditDialog(node=node, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["content"]:
            data["content"] = data["title"]
        db.update_publish_node(node["id"], data)
        self._refresh_all()

    def _on_delete_node(self):
        rows = self.node_table.selectedIndexes()
        if not rows:
            QMessageBox.information(self, "提示", "请先选择要删除的节点")
            return
        row = rows[0].row()
        node = self._nodes[row]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除节点 [{node['id']}] 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        db.delete_publish_node(node["id"])
        self._refresh_all()

    def _on_node_table_selection_changed(self):
        rows = self.node_table.selectedIndexes()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self._nodes):
            nid = self._nodes[row]["id"]
            self._selected_node_id = nid
            self.timeline.set_selected_node(nid)
            self._show_node_detail(nid)

    def _on_timeline_node_selected(self, nid: str):
        self._selected_node_id = nid
        self.timeline.set_selected_node(nid)
        self._show_node_detail(nid)
        for r, n in enumerate(self._nodes):
            if n["id"] == nid:
                self.node_table.selectRow(r)
                break

    def _show_node_detail(self, nid: str | None):
        if nid is None:
            self.node_detail_title.setText("")
            self.node_detail_platform.setCurrentIndex(0)
            self.node_detail_time.setText("")
            self.report_score.setText("流量共振指数: --")
            self.report_warning.setText("请选择节点查看推演报告")
            return
        node = db.get_publish_node_by_id(nid)
        if not node:
            return
        self.node_detail_title.setText(node.get("title", ""))
        idx = self.node_detail_platform.findText(node.get("platform", ""))
        if idx >= 0:
            self.node_detail_platform.setCurrentIndex(idx)
        self.node_detail_time.setText(node.get("time", ""))

        report = db.get_resonance_report(node)
        self.report_score.setText(f"流量共振指数: {report['score']:.2f}%")
        color = {"high": "#34d399", "medium": "#fbbf24", "low": "#f87171"}.get(report["level"], "#64748b")
        self.report_score.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};")
        self.report_warning.setText(report["warning"])

    def _on_submit_node_calibration(self):
        """根据右侧校准面板更新节点"""
        if not hasattr(self, "_selected_node_id") or self._selected_node_id is None:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return
        data = {
            "title": self.node_detail_title.text().strip(),
            "platform": self.node_detail_platform.currentText(),
            "time": self.node_detail_time.text().strip(),
        }
        if not data["time"]:
            QMessageBox.warning(self, "校验失败", "发布时间不能为空")
            return
        db.update_publish_node(self._selected_node_id, data)
        self._refresh_all()
        QMessageBox.information(self, "完成", "排期校准已提交")
