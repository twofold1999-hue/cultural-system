"""
数据透视模块 (AnalyticsModule)
=============================
数字文化内容策划与发布管理系统 - 数据透视 / 归因分析工作台

参考工程风格：
- 顶部过滤引擎 + 搜索 + 全局算法重校准
- 深色实时情感流监测折线图
- 左侧归因分析报告列表
- 右侧报告详情面板（KPI 卡片 + 归因进度条 + 系统洞察）

核心能力：
- 报告筛选与检索
- 动量得分与主要动力分析
- 影响力归因建模（文化内核 / 分发渠道 / 用户自传播）
- 实时情感流模拟监测
- 全局算法重校准
- 单报告 JSON 导出
"""

import json

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QWidget, QComboBox,
    QLineEdit, QMessageBox, QFileDialog, QGroupBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient, QPainterPath

from views.modules.base_module import BaseBusinessModule
from database.mock_db import db


# ============================================================
#  工具函数
# ============================================================
def _format_number(n) -> str:
    """数字格式化：过万显示万，过亿显示亿，其余千分位"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 100000000:
        return f"{n/100000000:.2f}亿"
    if n >= 10000:
        return f"{n/10000:.2f}万"
    if n == int(n):
        return f"{int(n):,}"
    return f"{n:,.2f}"


# ============================================================
#  子组件：暗色实时情感流折线图
# ============================================================
class SentimentFluxChart(QWidget):
    """
    实时情感流监测折线图（深色背景）
    模拟社交媒体情感波动，用于数据透视首页大屏
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # [(index, value), ...]
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: list):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # 深色背景
        painter.fillRect(0, 0, w, h, QColor("#0f172a"))

        if not self._data:
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "暂无数据")
            painter.end()
            return

        padding = {"top": 56, "bottom": 40, "left": 56, "right": 24}
        plot_w = w - padding["left"] - padding["right"]
        plot_h = h - padding["top"] - padding["bottom"]

        # 标题
        painter.setPen(QColor("#e2e8f0"))
        painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.Bold))
        painter.drawText(padding["left"], 18, "LIVE SENTIMENT FLUX MONITORING / 实时情感流监测")

        values = [v for _, v in self._data]
        max_v = max(values) if values else 100
        min_v = min(values) if values else 0
        range_v = max_v - min_v if max_v != min_v else 1

        # 网格线
        painter.setPen(QPen(QColor("#1e293b"), 1))
        for i in range(5):
            y = padding["top"] + plot_h * i / 4
            painter.drawLine(padding["left"], int(y), w - padding["right"], int(y))

        # Y 轴刻度
        painter.setPen(QColor("#64748b"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for i in range(5):
            y = padding["top"] + plot_h * i / 4
            label_val = min_v + range_v * (1 - i / 4)
            painter.drawText(4, int(y) - 8, padding["left"] - 12, 16,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{label_val:.0f}")

        n = len(self._data)
        points = []
        for i, (_, val) in enumerate(self._data):
            x = padding["left"] + plot_w * (i / max(1, n - 1))
            y = padding["top"] + plot_h * (1 - (val - min_v) / range_v)
            points.append((x, y))

        if len(points) > 1:
            # 渐变填充区域
            path = QPainterPath()
            path.moveTo(points[0][0], padding["top"] + plot_h)
            for x, y in points:
                path.lineTo(x, y)
            path.lineTo(points[-1][0], padding["top"] + plot_h)
            path.closeSubpath()
            gradient = QLinearGradient(0, padding["top"], 0, padding["top"] + plot_h)
            gradient.setColorAt(0, QColor(14, 165, 233, 120))
            gradient.setColorAt(1, QColor(14, 165, 233, 0))
            painter.fillPath(path, gradient)

            # 折线
            pen = QPen(QColor("#0ea5e9"))
            pen.setWidthF(2.5)
            painter.setPen(pen)
            for i in range(len(points) - 1):
                painter.drawLine(int(points[i][0]), int(points[i][1]),
                                 int(points[i + 1][0]), int(points[i + 1][1]))

        # 数据点
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#0ea5e9"))
        for x, y in points:
            painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)

        # X 轴标签
        painter.setPen(QColor("#64748b"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        step = max(1, n // 8)
        for i in range(0, n, step):
            x = padding["left"] + plot_w * (i / max(1, n - 1))
            painter.drawText(int(x) - 20, padding["top"] + plot_h + 8, 40, 18,
                             Qt.AlignmentFlag.AlignCenter, str(i))

        painter.end()


# ============================================================
#  子组件：归因进度条
# ============================================================
class AttributionBar(QWidget):
    """
    影响力归因水平进度条
    展示文化内核、分发渠道、用户自传播等维度的贡献占比
    """

    def __init__(self, label: str = "", value: int = 0, color: str = "#6366f1", parent=None):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._color = color
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, label: str, value: int, color: str):
        self._label = label
        self._value = max(0, min(100, value))
        self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#ffffff"))

        if not self._label:
            painter.end()
            return

        label_w = 160
        bar_x, bar_y = label_w + 12, 10
        bar_w = max(60, w - bar_x - 50)
        bar_h = h - 20

        # 标签
        painter.setPen(QColor("#475569"))
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        painter.drawText(0, 4, label_w, h - 8,
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         self._label)

        # 背景条
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e2e8f0"))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 5, 5)

        # 进度
        fill_w = int(bar_w * self._value / 100.0)
        painter.setBrush(QColor(self._color))
        painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 5, 5)

        # 百分比
        painter.setPen(QColor("#1e293b"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        painter.drawText(bar_x + bar_w + 8, 4, 40, h - 8,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"{self._value}%")

        painter.end()


# ============================================================
#  主模块
# ============================================================
class AnalyticsModule(BaseBusinessModule):
    """数据透视与归因分析主模块"""

    def __init__(self):
        super().__init__("数据透视与归因分析")
        self._reports = []
        self._current_uid = None

    def setup_ui(self):
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(12)

        # ---------- 顶部标题 ----------
        header_row = QHBoxLayout()
        title = QLabel("📊 数据透视与归因分析")
        title.setObjectName("SectionLabel")
        header_row.addWidget(title)
        header_row.addStretch()
        self.layout.addLayout(header_row)

        # ---------- 顶部筛选栏（参考工程风格）----------
        self._setup_filter_bar()

        # ---------- 实时情感流监测图 ----------
        self.sentiment_chart = SentimentFluxChart()
        self.layout.addWidget(self.sentiment_chart)

        # ---------- 报告列表 + 详情面板 ----------
        self._setup_detail_area()

        # 初始加载
        self._refresh_all()

    # ============================================================
    #  布局构建
    # ============================================================
    def _setup_filter_bar(self):
        filter_bar = QFrame()
        filter_bar.setObjectName("ModulePanel")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(12)

        self.combo_driver = QComboBox()
        self.combo_driver.addItem("全部维度", "")
        for d in db.get_analytics_report_drivers():
            self.combo_driver.addItem(d, d)
        self.combo_driver.currentIndexChanged.connect(self._on_search)
        filter_layout.addWidget(QLabel("过滤引擎:"))
        filter_layout.addWidget(self.combo_driver)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索报告 UID / 内容标题...")
        self.search_input.setMinimumWidth(260)
        self.search_input.returnPressed.connect(self._on_search)
        self.search_input.textChanged.connect(self._on_search_debounced)
        filter_layout.addWidget(self.search_input)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search)

        btn_search = QPushButton("🔍 搜索")
        btn_search.clicked.connect(self._on_search)
        filter_layout.addWidget(btn_search)

        filter_layout.addStretch()

        self.status_label = QLabel("共 0 份报告")
        self.status_label.setStyleSheet("color:#64748b;font-size:12px;")
        filter_layout.addWidget(self.status_label)

        btn_recalibrate = QPushButton("🔄 全局算法重校准")
        btn_recalibrate.setObjectName("PrimaryButton")
        btn_recalibrate.clicked.connect(self._on_recalibrate)
        filter_layout.addWidget(btn_recalibrate)

        self.layout.addWidget(filter_bar)

    def _setup_detail_area(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左：报告列表
        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_layout.addWidget(QLabel("归因分析报告"))

        self.report_table = QTableWidget(0, 4)
        self.report_table.setHorizontalHeaderLabels(["报告编号", "内容标题", "动量得分", "主要动力"])
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.report_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.report_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.report_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.report_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.report_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.report_table.setFont(QFont("Microsoft YaHei UI", 10))
        self.report_table.itemSelectionChanged.connect(self._on_report_selected)
        self.report_table.cellDoubleClicked.connect(self._on_report_double_clicked)
        left_layout.addWidget(self.report_table)

        splitter.addWidget(left_panel)

        # 右：详情面板
        right_panel = QFrame()
        right_panel.setObjectName("ModulePanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(14)

        self.detail_title = QLabel("请选择报告")
        self.detail_title.setStyleSheet("font-size:18px;font-weight:700;color:#1e293b;")
        right_layout.addWidget(self.detail_title)

        # KPI 卡片
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        self.kpi_exposure = self._create_kpi_card("核心曝光", "#0ea5e9")
        self.kpi_engagement = self._create_kpi_card("互动总量", "#34d399")
        kpi_row.addWidget(self.kpi_exposure)
        kpi_row.addWidget(self.kpi_engagement)
        right_layout.addLayout(kpi_row)

        # 归因分析
        attr_group = QGroupBox("影响力归因推演 (Attribution Modeling)")
        attr_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        attr_layout = QVBoxLayout(attr_group)
        attr_layout.setSpacing(10)
        self.attr_bars = []
        colors = ["#6366f1", "#ec4899", "#f59e0b"]
        for i, color in enumerate(colors):
            bar = AttributionBar("", 0, color)
            self.attr_bars.append(bar)
            attr_layout.addWidget(bar)
        right_layout.addWidget(attr_group)

        # 洞察建议
        insight_group = QGroupBox("系统洞察")
        insight_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        insight_layout = QVBoxLayout(insight_group)
        self.insight_label = QLabel("选择报告后查看系统洞察")
        self.insight_label.setWordWrap(True)
        self.insight_label.setStyleSheet("color:#64748b;line-height:1.6;")
        insight_layout.addWidget(self.insight_label)
        right_layout.addWidget(insight_group)

        # 导出
        export_bar = QHBoxLayout()
        export_bar.addStretch()
        btn_export = QPushButton("📤 导出报告")
        btn_export.clicked.connect(self._on_export)
        export_bar.addWidget(btn_export)
        right_layout.addLayout(export_bar)

        right_layout.addStretch()
        splitter.addWidget(right_panel)
        splitter.setSizes([520, 420])
        self.layout.addWidget(splitter, 1)

    def _create_kpi_card(self, title: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("StatCard")
        card.setStyleSheet("background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        tl = QLabel(title)
        tl.setStyleSheet("color:#64748b;font-size:12px;")
        vl = QLabel("--")
        vl.setStyleSheet(f"color:{color};font-size:22px;font-weight:700;")
        layout.addWidget(tl)
        layout.addWidget(vl)
        card._value_label = vl
        return card

    # ============================================================
    #  数据刷新与交互
    # ============================================================
    def _refresh_all(self):
        self._reports = db.get_analytics_reports(
            keyword=self.search_input.text(),
            driver=self.combo_driver.currentData(),
        )
        self._refresh_report_table()
        self._refresh_sentiment_chart()
        if self._reports:
            self.report_table.selectRow(0)
            self._show_report_detail(self._reports[0]["uid"])
        else:
            self._show_report_detail(None)

    def _on_search_debounced(self):
        self._search_timer.stop()
        self._search_timer.start(300)

    def _on_search(self):
        self._search_timer.stop()
        self._refresh_all()

    def _refresh_report_table(self):
        self.report_table.setRowCount(len(self._reports))
        self.status_label.setText(f"共 {len(self._reports)} 份报告")
        for i, r in enumerate(self._reports):
            self.report_table.setItem(i, 0, QTableWidgetItem(r["uid"]))
            item_title = QTableWidgetItem(r["title"])
            self.report_table.setItem(i, 1, item_title)

            score = r.get("momentum", 0)
            score_item = QTableWidgetItem(f"{score:.2f}")
            if score >= 70:
                score_item.setForeground(QColor("#34d399"))
            elif score >= 40:
                score_item.setForeground(QColor("#f59e0b"))
            else:
                score_item.setForeground(QColor("#ef4444"))
            self.report_table.setItem(i, 2, score_item)

            driver_item = QTableWidgetItem(r.get("driver", "-"))
            driver_item.setForeground(QColor("#0ea5e9"))
            self.report_table.setItem(i, 3, driver_item)

    def _refresh_sentiment_chart(self):
        series = db.get_analytics_sentiment_series()
        self.sentiment_chart.set_data(series)

    def _on_report_selected(self):
        rows = self.report_table.selectedIndexes()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self._reports):
            self._show_report_detail(self._reports[row]["uid"])

    def _on_report_double_clicked(self, row, col):
        if row < len(self._reports):
            self._show_report_detail(self._reports[row]["uid"])

    def _show_report_detail(self, uid: str | None):
        if uid is None:
            self._current_uid = None
            self.detail_title.setText("请选择报告")
            self.kpi_exposure._value_label.setText("--")
            self.kpi_engagement._value_label.setText("--")
            for bar in self.attr_bars:
                bar.set_value("", 0, "#6366f1")
            self.insight_label.setText("选择报告后查看系统洞察")
            return

        r = db.get_analytics_report_by_uid(uid)
        if not r:
            return
        self._current_uid = uid
        self.detail_title.setText(r["title"])

        # KPI
        self.kpi_exposure._value_label.setText(_format_number(r.get("exposure", 0)))
        self.kpi_engagement._value_label.setText(_format_number(r.get("engagement", 0)))

        # 归因条
        attrs = r.get("attribution", {})
        items = list(attrs.items())
        colors = ["#6366f1", "#ec4899", "#f59e0b"]
        for idx, bar in enumerate(self.attr_bars):
            if idx < len(items):
                label, value = items[idx]
                bar.set_value(label, int(value), colors[idx % len(colors)])
            else:
                bar.set_value("", 0, colors[idx % len(colors)])

        # 洞察
        momentum = r.get("momentum", 0)
        driver = r.get("driver", "")
        if momentum >= 70:
            insight = (f"报告 [{r['title']}] 动量得分高达 {momentum:.2f}，"
                       f"主要受「{driver}」驱动，建议加大分发投入并复用该内容模型。")
        elif momentum >= 40:
            insight = (f"报告 [{r['title']}] 动量得分 {momentum:.2f} 处于中等水平，"
                       f"可优化标题与封面以提升转化，当前核心驱动力为「{driver}」。")
        else:
            insight = (f"报告 [{r['title']}] 动量得分仅 {momentum:.2f}，低于平均水平。"
                       f"建议回顾内容契合度，调整分发时段或更换主要动力方向。")
        self.insight_label.setText(insight)

    def _on_recalibrate(self):
        db.recalibrate_reports()
        self._refresh_all()
        QMessageBox.information(self, "完成", "全局算法重校准已完成，报告动量得分与归因已重新计算")

    def _on_export(self):
        if not self._current_uid:
            QMessageBox.information(self, "提示", "请先选择一份报告")
            return
        r = db.get_analytics_report_by_uid(self._current_uid)
        if not r:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出报告", f"{r['uid']}_report.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "完成", f"已导出到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
