"""
控制面板模块 (DashboardModule)
=============================
MATRIX ENGINE 核心控制面板 —— 系统概览与内容维度分析

布局结构（参照设计稿）：
┌──────────────────────────────────────────────────────┐
│ [统计卡片] 影响力指数 | 活跃案数 | 资产估值 | 运行时间 │
├──────────────────────┬───────────────────────────────┤
│  [雷达图区域]         │   [优先级分发计划表格]          │
│  Influence Radar     │   策划案 | 影响力 | 状态       │
│  (5维能力评估)        │   ...                        │
│                      │                               │
├──────────────────────┴───────────────────────────────┤
│ [引擎控制台 - 深色]              │ [引擎负载进度条]     │
│ [HH:MM:SS] 日志流...            │ ████████░░ 58%      │
└───────────────────────────────────────────────────────┘
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QSplitter, QWidget
)
from PyQt6.QtCore import Qt, QTimer

from views.modules.base_module import BaseBusinessModule
from views.modules.common_widgets import RadarChartWidget, EngineConsoleWidget, EngineLoadWidget
from database.mock_db import db


class DashboardModule(BaseBusinessModule):
    """
    控制面板主界面 — MATRIX ENGINE 系统概览
    """

    def __init__(self):
        super().__init__("控制面板")

    def setup_ui(self):
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)

        # ---------- 顶部统计卡片 ----------
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        stat_items = [
            ("全网核心影响力指数", "influence_index", "#00bfff"),
            ("活跃内容策划案", "active_plans", "#38a169"),
            ("数字资产估值 (¥)", "asset_value", "#d29922"),
            ("引擎运行时间", "runtime_hours", "#e53e3e"),
        ]

        self._dash_values = {}
        for title_text, key, color in stat_items:
            card = QFrame()
            card.setObjectName("StatCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 18, 20, 18)
            card_layout.setSpacing(8)

            title = QLabel(title_text)
            title.setObjectName("StatCardTitle")
            value = QLabel("--")
            value.setObjectName("StatCardValue")
            value.setStyleSheet(f"color: {color};")
            self._dash_values[key] = value

            card_layout.addWidget(title)
            card_layout.addWidget(value)
            cards_row.addWidget(card, 1)

        self.layout.addLayout(cards_row)

        # ---------- 中间区域：雷达图 + 优先级分发计划 ----------
        mid_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧雷达图
        radar_panel = QFrame()
        radar_panel.setObjectName("ModulePanel")
        rp_layout = QVBoxLayout(radar_panel)
        rp_layout.setContentsMargins(14, 12, 14, 12)
        radar_title = QLabel("内容维度分析矩阵")
        radar_title.setObjectName("SectionLabel")
        rp_layout.addWidget(radar_title)

        self._dash_radar = RadarChartWidget()
        rp_layout.addWidget(self._dash_radar, 1)
        mid_splitter.addWidget(radar_panel)

        # 右侧优先级表格
        table_panel = QFrame()
        table_panel.setObjectName("ModulePanel")
        tp_layout = QVBoxLayout(table_panel)
        tp_layout.setContentsMargins(14, 12, 14, 12)

        table_header = QHBoxLayout()
        table_title = QLabel("高优先级分发计划")
        table_title.setObjectName("SectionLabel")
        table_header.addWidget(table_title)
        table_header.addStretch()
        self._dash_status_filter = QComboBox()
        self._dash_status_filter.addItems(["全部", "待执行", "执行中", "已完成", "已暂停", "审核中"])
        self._dash_status_filter.currentTextChanged.connect(self._refresh_table)
        table_header.addWidget(self._dash_status_filter)
        tp_layout.addLayout(table_header)

        self._dash_table = QTableWidget(0, 3)
        self._dash_table.setHorizontalHeaderLabels(["策划案名称", "影响力预估", "状态"])
        self._dash_table.verticalHeader().setVisible(False)
        self._dash_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._dash_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tp_layout.addWidget(self._dash_table, 1)
        mid_splitter.addWidget(table_panel)

        mid_splitter.setSizes([420, 500])
        self.layout.addWidget(mid_splitter, 3)

        # ---------- 底部区域：控制台 + 负载 ----------
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._dash_console = EngineConsoleWidget()
        bottom_splitter.addWidget(self._dash_console)

        self._dash_load = EngineLoadWidget()
        bottom_splitter.addWidget(self._dash_load)

        bottom_splitter.setSizes([600, 160])
        self.layout.addWidget(bottom_splitter, 1)

        self._refresh_all()

        # 定时刷新（每 5 秒）
        self._dash_timer = QTimer(self)
        self._dash_timer.timeout.connect(self._refresh_all)
        self._dash_timer.start(5000)

    def _refresh_all(self):
        """刷新控制面板全部数据"""
        plan_stats = db.get_planning_stats()

        # 统计卡片
        self._dash_values["influence_index"].setText(str(plan_stats.get("influence_index", 0)))
        self._dash_values["active_plans"].setText(str(plan_stats.get("active_plans", 0)))
        self._dash_values["asset_value"].setText(plan_stats.get("asset_value_yuan", "0"))
        self._dash_values["runtime_hours"].setText(plan_stats.get("runtime_hours", "0"))

        # 雷达图
        radar_data = plan_stats.get("radar_data", {})
        if radar_data:
            self._dash_radar.set_data(radar_data)

        # 优先级表格
        self._refresh_table()

        # 控制台日志
        self._dash_console.load_logs(db.get_node_logs(limit=20))

    def _refresh_table(self):
        """刷新优先级分发计划表格"""
        status_map = {
            "全部": "",
            "待执行": "pending",
            "执行中": "running",
            "已完成": "completed",
            "已暂停": "paused",
            "审核中": "reviewing",
        }
        label_map = {
            "pending": "待执行",
            "running": "执行中",
            "completed": "已完成",
            "paused": "已暂停",
            "reviewing": "审核中",
        }
        text = self._dash_status_filter.currentText()
        plans = db.get_planning_list(status_filter=status_map.get(text, ""))
        self._dash_table.setRowCount(min(len(plans), 10))
        for r, p in enumerate(plans[:10]):
            self._dash_table.setItem(r, 0, QTableWidgetItem(p.get("name", "-")))
            self._dash_table.setItem(r, 1, QTableWidgetItem(f"{p.get('influence', 0)} 分"))
            status_item = QTableWidgetItem(label_map.get(p.get("status"), p.get("status", "-")))
            self._dash_table.setItem(r, 2, status_item)

    def cleanup(self):
        """热重载前停止定时器"""
        if hasattr(self, "_dash_timer") and self._dash_timer:
            self._dash_timer.stop()
            self._dash_timer.deleteLater()
