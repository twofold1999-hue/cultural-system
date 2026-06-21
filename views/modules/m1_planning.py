"""
内容策划模块
============================
MATRIX ENGINE 数字文化内容策划工作台

参考交互原型：
- 文化基因配置 Tab：核心元数据 + 特征向量建模
- 叙事节奏编排 Tab：起承转合结构 + 节奏曲线
- 成本与资源预测 Tab：成本项 + 资源分配 + 投资回报预测
- 文化基因实时图谱
- 全渠道匹配分析
- 策划健康度评分
- 预期效果评估
- 智能策划报告
- 策划案历史库
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QTextEdit, QTabWidget,
    QWidget, QSplitter, QScrollArea, QSizePolicy,
    QDialog, QFormLayout, QLineEdit, QMessageBox, QSlider,
    QListWidget, QListWidgetItem,
    QProgressBar, QPlainTextEdit, QFileDialog, QApplication,
    QGridLayout, QSpinBox, QDoubleSpinBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient
from database.mock_db import db
from views.modules.base_module import BaseBusinessModule
from views.modules.common_widgets import (
    RadarChartWidget, EngineConsoleWidget, EngineLoadWidget, MultiLineDelegate
)


# ============================================================
#  常量与配置
# ============================================================

GENE_LABELS = [
    ("depth", "文化深度", "Culture Depth"),
    ("narrative", "叙事强度", "Narrative Strength"),
    ("visual", "视觉张力", "Visual Tension"),
    ("interact", "受众趣味", "Audience Appeal"),
    ("trend", "流行适配", "Trend Fit"),
]

# 渠道对文化基因的敏感度矩阵
CHANNEL_SENSITIVITY = {
    "社交媒体矩阵":     {"visual": 0.8, "narrative": 0.6, "interact": 0.5, "trend": 1.0, "depth": 0.4},
    "短视频矩阵":       {"visual": 1.0, "narrative": 0.5, "interact": 0.7, "trend": 0.9, "depth": 0.3},
    "中长视频平台":     {"visual": 0.8, "narrative": 1.0, "interact": 0.6, "trend": 0.5, "depth": 0.9},
    "数字博物馆":       {"visual": 0.7, "narrative": 0.7, "interact": 0.8, "trend": 0.4, "depth": 0.9},
    "AR/VR 沉浸式导览": {"visual": 0.9, "narrative": 0.6, "interact": 1.0, "trend": 0.7, "depth": 0.6},
    "线下沉浸式特展":   {"visual": 1.0, "narrative": 0.8, "interact": 0.9, "trend": 0.8, "depth": 0.7},
    "文化研学":         {"visual": 0.4, "narrative": 0.9, "interact": 0.7, "trend": 0.3, "depth": 1.0},
    "IP 授权":          {"visual": 0.8, "narrative": 0.7, "interact": 0.5, "trend": 0.8, "depth": 0.6},
    "高端文创电商":     {"visual": 0.9, "narrative": 0.5, "interact": 0.4, "trend": 0.9, "depth": 0.5},
    "海外文化传播":     {"visual": 0.6, "narrative": 0.8, "interact": 0.5, "trend": 0.6, "depth": 0.9},
}

DEFAULT_COST_ITEMS = [
    ("内容创作", 120000, "图文/视频/设计制作费用"),
    ("技术开发", 80000, "线上展厅/AR/VR/小程序开发"),
    ("渠道投放", 150000, "社交媒体与信息流广告投放"),
    ("线下执行", 100000, "特展布展、场地、执行团队"),
    ("版权授权", 50000, "文物/IP/音乐/字体等版权"),
    ("运营人力", 60000, "策划、运营、客服人力成本"),
]


# ============================================================
#  子组件：文化基因柱状图
# ============================================================

class GeneBarChartWidget(QWidget):
    """文化基因实时图谱：五维度柱状图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GeneBarChartWidget")
        self.setMinimumHeight(160)
        self._values = {key: 50 for key, _, _ in GENE_LABELS}

    def set_values(self, values: dict):
        self._values = values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 36
        margin_bottom = 58
        chart_w = w - margin * 2
        chart_h = h - margin - margin_bottom
        bar_w = chart_w / len(GENE_LABELS) * 0.55
        gap = chart_w / len(GENE_LABELS)

        # 坐标轴
        painter.setPen(QPen(QColor("#cbd5e0"), 1))
        painter.drawLine(margin, h - margin_bottom, w - margin, h - margin_bottom)

        # 柱状
        for i, (key, cn, _) in enumerate(GENE_LABELS):
            val = max(0, min(100, self._values.get(key, 0)))
            x = margin + i * gap + (gap - bar_w) / 2
            bar_h = chart_h * (val / 100)
            y = h - margin_bottom - bar_h

            gradient = QLinearGradient(x, y, x, h - margin_bottom)
            gradient.setColorAt(0, QColor("#00bfff"))
            gradient.setColorAt(1, QColor("#0077b6"))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 4, 4)

            # 数值
            painter.setPen(QColor("#1a202c"))
            painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
            painter.drawText(int(x - 10), int(y - 18), int(bar_w + 20), 16, Qt.AlignmentFlag.AlignCenter, f"{val:.0f}")

            # 标签：分两行居中显示，避免X轴文字挤压重叠
            painter.setPen(QColor("#4a5568"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            label_x = int(x - 8)
            label_w = int(bar_w + 16)
            painter.drawText(label_x, h - margin_bottom + 6, label_w, 18, Qt.AlignmentFlag.AlignCenter, cn[:2])
            painter.drawText(label_x, h - margin_bottom + 22, label_w, 18, Qt.AlignmentFlag.AlignCenter, cn[2:])

        painter.end()


# ============================================================
#  子组件：叙事节奏曲线图
# ============================================================

class RhythmCurveWidget(QWidget):
    """叙事节奏曲线：起承转合四个阶段的张力可视化"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RhythmCurveWidget")
        self.setMinimumHeight(120)
        self._values = [30, 60, 45, 80]

    def set_values(self, values: list):
        self._values = values
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 30
        cw = w - margin * 2
        ch = h - margin * 2
        labels = ["起", "承", "转", "合"]
        n = len(self._values)
        points = []
        for i, v in enumerate(self._values):
            x = margin + cw * i / (n - 1)
            y = h - margin - ch * (v / 100)
            points.append((x, y))

        # 网格
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        for i in range(5):
            y = margin + ch * i / 4
            painter.drawLine(margin, int(y), w - margin, int(y))

        # 曲线
        painter.setPen(QPen(QColor("#00bfff"), 2))
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 节点
        for i, (x, y) in enumerate(points):
            painter.setBrush(QColor("#00bfff"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x) - 5, int(y) - 5, 10, 10)
            painter.setPen(QColor("#4a5568"))
            painter.setFont(QFont("Microsoft YaHei UI", 9))
            painter.drawText(int(x - 20), h - margin + 16, 40, 20, Qt.AlignmentFlag.AlignCenter, labels[i])
            painter.setPen(QColor("#00bfff"))
            painter.setFont(QFont("Microsoft YaHei UI", 8, QFont.Weight.Bold))
            painter.drawText(int(x - 20), int(y - 20), 40, 16, Qt.AlignmentFlag.AlignCenter, f"{self._values[i]:.0f}")

        painter.end()


# ============================================================
#  主模块：内容策划工作台
# ============================================================

class PlanningModule(BaseBusinessModule):
    """
    内容策划模块 —— 数字文化内容创作分析工作台

    参考工程结构：
    ┌──────────────────────────────────────────────────────────────┐
    │  [文化基因配置]  [叙事节奏编排]  [成本与资源预测]              │
    ├──────────────────────────┬───────────────────────────────────┤
    │                          │ 文化基因实时图谱                  │
    │                          │ [柱状图]                          │
    │   Tab 内容（输入区）      │                                   │
    │                          │ 全渠道匹配分析                    │
    │                          │ [表格]                            │
    │                          ├───────────────────────────────────┤
    │                          │ 策划健康度 / 预期效果             │
    │                          ├───────────────────────────────────┤
    │                          │ 智能策划报告                      │
    │                          ├───────────────────────────────────┤
    │                          │ 策划案历史库                      │
    └──────────────────────────┴───────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self._current_history_id = None
        self._gene_values = {"depth": 50, "narrative": 50, "visual": 50, "interact": 50, "trend": 50}
        self._last_results = []
        self._setup_ui()
        self._bind_events()
        self._refresh_history()
        self._run_analysis()
        # 默认显示文化基因配置对应的右侧面板，并初始化成本推演报告
        self._on_tab_changed(0)
        self._update_cost_report()

    def cleanup(self):
        pass

    # ==================== UI 构建 ====================

    def _setup_ui(self):
        """左右分栏布局：各子表格/面板自身支持滚动，不依赖全局横向滚动"""
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(12)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self._build_left_panel())
        main_splitter.addWidget(self._build_right_panel())
        main_splitter.setSizes([460, 760])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        self.layout.addWidget(main_splitter, 1)

    def _build_left_panel(self):
        """左侧使用 TabWidget 组织三个策划维度，切换时联动右侧内容"""
        self.tabs = QTabWidget()
        self.tabs.setObjectName("PlanningTabWidget")
        self.tabs.addTab(self._build_tab_gene(), "文化基因配置")
        self.tabs.addTab(self._build_tab_rhythm(), "叙事节奏编排")
        self.tabs.addTab(self._build_tab_cost(), "成本与资源预测")
        self.tabs.setMinimumWidth(520)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        return self.tabs

    def _build_tab_gene(self):
        """Tab 1：文化基因配置"""
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        panel = QFrame()
        panel.setObjectName("ModulePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(16)

        # 核心元数据
        basic_title = QLabel("核心元数据")
        basic_title.setObjectName("SectionLabel")
        layout.addWidget(basic_title)

        form = QFormLayout()
        form.setSpacing(10)
        self.title_input = QLineEdit("新策划案")
        self.title_input.setPlaceholderText("项目主标题")
        form.addRow("项目主标题", self.title_input)

        self.category_combo = QComboBox()
        self.category_combo.addItems(db.get_culture_categories())
        self.category_combo.setEditable(True)
        form.addRow("文化领域", self.category_combo)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("关键词标签，多个用逗号分隔")
        form.addRow("关键词标签", self.tags_input)
        layout.addLayout(form)

        # 特征向量建模
        gene_title = QLabel("特征向量建模")
        gene_title.setObjectName("SectionLabel")
        layout.addWidget(gene_title)

        self._slider_labels = {}
        self._sliders = {}
        for key, cn, _ in GENE_LABELS:
            row = QHBoxLayout()
            name_lbl = QLabel(f"{cn}")
            name_lbl.setFixedWidth(90)
            name_lbl.setStyleSheet("color: #4a5568; font-size: 12px;")
            row.addWidget(name_lbl)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(50)
            slider.setObjectName("GeneSlider")
            self._sliders[key] = slider
            row.addWidget(slider, 1)

            val_lbl = QLabel("50")
            val_lbl.setFixedWidth(32)
            val_lbl.setStyleSheet("color: #00bfff; font-weight: bold;")
            self._slider_labels[key] = val_lbl
            row.addWidget(val_lbl)
            layout.addLayout(row)

        # 执行按钮
        self.btn_analyze = QPushButton("执行智能推演分析")
        self.btn_analyze.setObjectName("AnalyzeButton")
        self.btn_analyze.setFixedHeight(40)
        self.btn_analyze.setToolTip("根据文化基因维度计算渠道匹配度、推荐指数与策划健康度")
        self.btn_analyze.clicked.connect(self._run_analysis)
        layout.addWidget(self.btn_analyze)

        layout.addStretch()
        scroll.setWidget(panel)
        return scroll

    def _build_tab_rhythm(self):
        """Tab 2：叙事节奏编排"""
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        panel = QFrame()
        panel.setObjectName("ModulePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(16)

        title = QLabel("叙事节奏编排")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)

        # 节奏曲线
        self.rhythm_curve = RhythmCurveWidget()
        self.rhythm_curve.setFixedHeight(140)
        layout.addWidget(self.rhythm_curve)

        # 起承转合
        self.rhythm_inputs = {}
        stages = [
            ("起", "引入：文化背景、用户痛点、钩子设计"),
            ("承", "展开：核心内容、故事铺垫、价值传递"),
            ("转", "高潮：冲突/亮点/情绪峰值、互动爆点"),
            ("合", "收尾：结论升华、行动号召、品牌沉淀"),
        ]
        for stage, hint in stages:
            lbl = QLabel(f"{stage} · {hint.split('：')[0]}")
            lbl.setStyleSheet("color: #4a5568; font-size: 12px; margin-top: 6px;")
            layout.addWidget(lbl)
            edit = QTextEdit()
            edit.setPlaceholderText(hint)
            edit.setMaximumHeight(70)
            self.rhythm_inputs[stage] = edit
            layout.addWidget(edit)

        # 叙事节点列表 / 关键帧
        beats_title = QLabel("叙事节点列表")
        beats_title.setObjectName("SectionLabel")
        layout.addWidget(beats_title)

        beats_toolbar = QHBoxLayout()
        self.btn_add_beat = QPushButton("+ 添加关键帧")
        self.btn_add_beat.setObjectName("BtnCreate")
        self.btn_add_beat.clicked.connect(self._add_beat)
        self.btn_del_beat = QPushButton("删除选中")
        self.btn_del_beat.setObjectName("BtnDelete")
        self.btn_del_beat.clicked.connect(self._del_beat)
        beats_toolbar.addWidget(self.btn_add_beat)
        beats_toolbar.addWidget(self.btn_del_beat)
        beats_toolbar.addStretch()
        layout.addLayout(beats_toolbar)

        self.beats_table = QTableWidget(0, 3)
        self.beats_table.setHorizontalHeaderLabels(["序号", "内容概要", "情感极性"])
        self.beats_table.verticalHeader().setVisible(False)
        self.beats_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.beats_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        self.beats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.beats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.beats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.beats_table.setColumnWidth(0, 50)
        self.beats_table.setColumnWidth(2, 80)
        self.beats_table.setMinimumHeight(120)
        self.beats_table.setMaximumHeight(200)
        layout.addWidget(self.beats_table)

        # 预置示例关键帧
        for idx, text in enumerate(["文化背景引入", "核心价值展开", "情绪高潮爆发", "品牌行动号召"], start=1):
            self._add_beat_row(idx, text, "中性")

        # 节奏强度滑块
        self._rhythm_sliders = {}
        rhythm_title = QLabel("节奏强度")
        rhythm_title.setObjectName("SectionLabel")
        layout.addWidget(rhythm_title)
        for stage in ["起", "承", "转", "合"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(stage))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(50)
            slider.setObjectName("GeneSlider")
            self._rhythm_sliders[stage] = slider
            row.addWidget(slider)
            val_lbl = QLabel("50")
            val_lbl.setFixedWidth(32)
            val_lbl.setStyleSheet("color: #00bfff; font-weight: bold;")
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(str(v)))
            slider.valueChanged.connect(self._update_rhythm_curve)
            row.addWidget(val_lbl)
            layout.addLayout(row)

        # 叙事逻辑纲要
        summary_title = QLabel("叙事逻辑纲要")
        summary_title.setObjectName("SectionLabel")
        layout.addWidget(summary_title)
        self.summary_input = QTextEdit()
        self.summary_input.setPlaceholderText("整合起承转合，描述本次策划的核心叙事逻辑、目标受众、传播策略与预期效果...")
        self.summary_input.setMinimumHeight(80)
        layout.addWidget(self.summary_input)

        # 同步右侧叙事节奏预览
        self.summary_input.textChanged.connect(self._refresh_rhythm_preview)
        self.beats_table.itemChanged.connect(self._refresh_rhythm_preview)

        layout.addStretch()
        scroll.setWidget(panel)
        return scroll

    def _build_tab_cost(self):
        """Tab 3：成本与资源预测——关键指标置顶，布局紧凑，实时计算"""
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        panel = QFrame()
        panel.setObjectName("ModulePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(12)

        title = QLabel("成本与资源预测")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)

        # 顶部关键指标：预算、周期、ROI（2x2 网格，避免截断）
        top_grid = QGridLayout()
        top_grid.setSpacing(8)
        top_grid.setColumnStretch(1, 1)
        top_grid.setColumnStretch(3, 1)
        self.budget_input = QLineEdit("50万")
        self.budget_input.setFixedWidth(90)
        self.cycle_input = QLineEdit("3个月")
        self.cycle_input.setFixedWidth(80)
        self.roi_label = QLabel("ROI：—")
        self.roi_label.setStyleSheet("color: #38a169; font-weight: bold;")
        self.roi_label.setToolTip("根据成本明细与预期收益实时计算")
        top_grid.addWidget(QLabel("总预算："), 0, 0)
        top_grid.addWidget(self.budget_input, 0, 1)
        top_grid.addWidget(QLabel("周期："), 1, 0)
        top_grid.addWidget(self.cycle_input, 1, 1)
        top_grid.addWidget(QLabel("投资回报："), 0, 2)
        top_grid.addWidget(self.roi_label, 0, 3)
        layout.addLayout(top_grid)

        # 成本控制矩阵
        control_title = QLabel("成本控制矩阵")
        control_title.setObjectName("SectionLabel")
        layout.addWidget(control_title)

        control_grid = QGridLayout()
        control_grid.setSpacing(8)
        control_grid.setColumnStretch(1, 1)
        control_grid.setColumnStretch(3, 1)

        self.budget_limit_input = QDoubleSpinBox()
        self.budget_limit_input.setRange(0, 99999999)
        self.budget_limit_input.setValue(50000)
        self.budget_limit_input.setPrefix("¥ ")
        self.budget_limit_input.setDecimals(2)
        self.budget_limit_input.setMaximumWidth(180)
        control_grid.addWidget(QLabel("预算红线："), 0, 0)
        control_grid.addWidget(self.budget_limit_input, 0, 1)

        self.human_input = QSpinBox()
        self.human_input.setRange(1, 9999)
        self.human_input.setValue(1)
        self.human_input.setSuffix(" 人")
        self.human_input.setMaximumWidth(120)
        control_grid.addWidget(QLabel("预估投入人力："), 0, 2)
        control_grid.addWidget(self.human_input, 0, 3)
        layout.addLayout(control_grid)

        # 成本项目表格
        cost_title = QLabel("成本项目明细")
        cost_title.setObjectName("SectionLabel")
        layout.addWidget(cost_title)

        self.cost_table = QTableWidget(0, 3)
        self.cost_table.setHorizontalHeaderLabels(["成本项", "金额（元）", "备注"])
        self.cost_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.cost_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.cost_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.cost_table.horizontalHeader().setStretchLastSection(False)
        self.cost_table.setColumnWidth(0, 110)
        self.cost_table.setColumnWidth(1, 100)
        self.cost_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cost_table.verticalHeader().setDefaultSectionSize(28)
        self.cost_table.verticalHeader().setMinimumSectionSize(26)
        self.cost_table.setMinimumHeight(220)
        self.cost_table.setMaximumHeight(380)
        self.cost_table.setItemDelegateForColumn(2, MultiLineDelegate(self.cost_table))
        self.cost_table.resizeRowsToContents()
        self._load_default_cost_items()
        layout.addWidget(self.cost_table)

        cost_btns = QHBoxLayout()
        self.btn_add_cost = QPushButton("添加成本项")
        self.btn_add_cost.setObjectName("BtnUpdate")
        self.btn_add_cost.setFixedHeight(34)
        self.btn_add_cost.setMinimumWidth(90)
        self.btn_add_cost.clicked.connect(self._add_cost_row)
        cost_btns.addWidget(self.btn_add_cost)

        self.btn_del_cost = QPushButton("删除选中项")
        self.btn_del_cost.setObjectName("BtnDelete")
        self.btn_del_cost.setFixedHeight(34)
        self.btn_del_cost.setMinimumWidth(90)
        self.btn_del_cost.clicked.connect(self._del_cost_row)
        cost_btns.addWidget(self.btn_del_cost)
        cost_btns.addStretch()
        layout.addLayout(cost_btns)

        # 资源分配（3 行 2 列，更紧凑）
        resource_title = QLabel("资源分配（占比 %）")
        resource_title.setObjectName("SectionLabel")
        layout.addWidget(resource_title)

        self._resource_spin = {}
        resource_grid = QGridLayout()
        resource_grid.setSpacing(8)
        resources = [
            ("creative", "内容创作"),
            ("tech", "技术开发"),
            ("promo", "渠道投放"),
            ("offline", "线下执行"),
            ("ops", "运营人力"),
            ("other", "其他预留"),
        ]
        for i, (key, name) in enumerate(resources):
            row, col = divmod(i, 2)
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setValue(20 if i < 5 else 0)
            spin.setSuffix("%")
            spin.setMinimumWidth(70)
            self._resource_spin[key] = spin
            resource_grid.addWidget(QLabel(name), row, col * 2)
            resource_grid.addWidget(spin, row, col * 2 + 1)
        layout.addLayout(resource_grid)

        # 预期收益输入（2x2 网格，避免截断）
        roi_grid = QGridLayout()
        roi_grid.setSpacing(8)
        roi_grid.setColumnStretch(1, 1)
        roi_grid.setColumnStretch(3, 1)
        self.roi_revenue = QLineEdit("200万")
        self.roi_revenue.setFixedWidth(90)
        self.roi_brand = QSpinBox()
        self.roi_brand.setRange(0, 100)
        self.roi_brand.setValue(75)
        self.roi_brand.setSuffix("/100")
        self.roi_brand.setFixedWidth(95)
        roi_grid.addWidget(QLabel("预期收益："), 0, 0)
        roi_grid.addWidget(self.roi_revenue, 0, 1)
        roi_grid.addWidget(QLabel("品牌影响："), 1, 0)
        roi_grid.addWidget(self.roi_brand, 1, 1)
        roi_grid.addWidget(QLabel("总成本："), 0, 2)
        self.cost_total_label = QLabel("—")
        self.cost_total_label.setStyleSheet("color: #3182ce; font-weight: bold;")
        roi_grid.addWidget(self.cost_total_label, 0, 3)
        layout.addLayout(roi_grid)

        # 实时计算 ROI
        self.cost_table.itemChanged.connect(self._calc_roi)
        self.roi_revenue.textChanged.connect(self._calc_roi)
        self.roi_brand.valueChanged.connect(self._calc_roi)
        for spin in self._resource_spin.values():
            spin.valueChanged.connect(self._calc_roi)
        self.budget_limit_input.valueChanged.connect(self._update_cost_report)
        self.human_input.valueChanged.connect(self._update_cost_report)
        self.cost_table.itemChanged.connect(self._update_cost_report)

        layout.addStretch()
        scroll.setWidget(panel)
        return scroll

    def _build_right_panel(self):
        """右侧为分析结果面板，按左侧 Tab 动态显示关联内容"""
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.right_container = QFrame()
        self.right_container.setObjectName("ModulePanel")
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(16, 14, 16, 12)
        self.right_layout.setSpacing(14)

        self.right_panel_gene = self._build_right_gene_panel()
        self.right_panel_rhythm = self._build_right_rhythm_panel()
        self.right_panel_cost = self._build_right_cost_panel()

        self.right_layout.addWidget(self.right_panel_gene)
        self.right_layout.addWidget(self.right_panel_rhythm)
        self.right_layout.addWidget(self.right_panel_cost)

        scroll.setWidget(self.right_container)
        return scroll

    def _build_right_gene_panel(self):
        """右侧：文化基因配置 Tab 关联面板"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. 文化基因实时图谱
        chart_title = QLabel("文化基因实时图谱")
        chart_title.setObjectName("SectionLabel")
        layout.addWidget(chart_title)
        self.gene_chart = GeneBarChartWidget()
        self.gene_chart.setFixedHeight(200)
        layout.addWidget(self.gene_chart)

        # 2. 全渠道匹配分析
        channel_title = QLabel("全渠道匹配分析")
        channel_title.setObjectName("SectionLabel")
        layout.addWidget(channel_title)

        self.channel_table = QTableWidget(0, 4)
        self.channel_table.setHorizontalHeaderLabels(["目标渠道", "受众画像", "适配度得分", "推荐指数"])
        self.channel_table.verticalHeader().setVisible(False)
        self.channel_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.channel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.channel_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.channel_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.channel_table.setColumnWidth(0, 160)
        self.channel_table.setColumnWidth(1, 130)
        self.channel_table.setColumnWidth(2, 90)
        self.channel_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.channel_table.setMinimumHeight(240)
        self.channel_table.setMaximumHeight(300)
        layout.addWidget(self.channel_table)

        # 3. 策划健康度与预期效果
        health_title = QLabel("策划健康度 / 预期效果")
        health_title.setObjectName("SectionLabel")
        layout.addWidget(health_title)

        health_layout = QHBoxLayout()
        self.health_progress = QProgressBar()
        self.health_progress.setRange(0, 100)
        self.health_progress.setValue(0)
        self.health_progress.setTextVisible(True)
        self.health_progress.setFormat("健康度 %v")
        health_layout.addWidget(self.health_progress, 1)

        self.health_label = QLabel("—")
        self.health_label.setStyleSheet("font-weight: bold; color: #00bfff; padding-left: 8px;")
        self.health_label.setFixedWidth(80)
        health_layout.addWidget(self.health_label)
        layout.addLayout(health_layout)

        effect_layout = QHBoxLayout()
        self.exposure_label = QLabel("曝光潜力：—")
        self.engagement_label = QLabel("互动潜力：—")
        self.conversion_label = QLabel("转化潜力：—")
        effect_layout.addWidget(self.exposure_label)
        effect_layout.addWidget(self.engagement_label)
        effect_layout.addWidget(self.conversion_label)
        effect_layout.addStretch()
        layout.addLayout(effect_layout)

        # 4. 智能策划报告
        report_title = QLabel("智能策划报告")
        report_title.setObjectName("SectionLabel")
        layout.addWidget(report_title)

        self.report_editor = QPlainTextEdit()
        self.report_editor.setPlaceholderText('点击"执行智能推演分析"生成可交付的策划报告...')
        self.report_editor.setMinimumHeight(120)
        self.report_editor.setMaximumHeight(220)
        self.report_editor.setReadOnly(True)
        layout.addWidget(self.report_editor)

        report_btns = QHBoxLayout()
        self.btn_copy_report = QPushButton("复制报告")
        self.btn_copy_report.setObjectName("BtnUpdate")
        self.btn_copy_report.setFixedHeight(28)
        self.btn_copy_report.clicked.connect(self._copy_report)
        report_btns.addWidget(self.btn_copy_report)

        self.btn_export_report = QPushButton("导出报告")
        self.btn_export_report.setObjectName("SaveButton")
        self.btn_export_report.setFixedHeight(28)
        self.btn_export_report.clicked.connect(self._export_report)
        report_btns.addWidget(self.btn_export_report)

        self.btn_reset = QPushButton("重置")
        self.btn_reset.setObjectName("BtnDelete")
        self.btn_reset.setFixedHeight(28)
        self.btn_reset.clicked.connect(self._reset_form)
        report_btns.addWidget(self.btn_reset)
        report_btns.addStretch()
        layout.addLayout(report_btns)

        # 5. 策划案历史库
        hist_title = QLabel("策划案历史库（本地缓存）")
        hist_title.setObjectName("SectionLabel")
        layout.addWidget(hist_title)

        hist_row = QHBoxLayout()
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(100)
        self.history_list.itemClicked.connect(self._on_history_selected)
        hist_row.addWidget(self.history_list, 1)

        hist_btns = QVBoxLayout()
        self.btn_load_history = QPushButton("载入")
        self.btn_load_history.setObjectName("BtnUpdate")
        self.btn_load_history.setFixedHeight(26)
        self.btn_load_history.clicked.connect(self._load_history_item)
        hist_btns.addWidget(self.btn_load_history)

        self.btn_save_history = QPushButton("保存当前")
        self.btn_save_history.setObjectName("SaveButton")
        self.btn_save_history.setFixedHeight(26)
        self.btn_save_history.setToolTip("将当前策划保存到本地历史库")
        self.btn_save_history.clicked.connect(self._save_to_history)
        hist_btns.addWidget(self.btn_save_history)

        self.btn_del_history = QPushButton("删除")
        self.btn_del_history.setObjectName("BtnDelete")
        self.btn_del_history.setFixedHeight(26)
        self.btn_del_history.clicked.connect(self._delete_history_item)
        hist_btns.addWidget(self.btn_del_history)
        hist_row.addLayout(hist_btns)
        layout.addLayout(hist_row)

        layout.addStretch()
        return panel

    def _build_right_rhythm_panel(self):
        """右侧：叙事节奏编排 Tab 关联面板"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("叙事节奏分析")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)

        self.rhythm_curve_right = RhythmCurveWidget()
        self.rhythm_curve_right.setFixedHeight(180)
        layout.addWidget(self.rhythm_curve_right)

        beats_title = QLabel("关键帧预览")
        beats_title.setObjectName("SectionLabel")
        layout.addWidget(beats_title)

        self.beats_preview = QPlainTextEdit()
        self.beats_preview.setReadOnly(True)
        self.beats_preview.setMinimumHeight(100)
        self.beats_preview.setMaximumHeight(160)
        self.beats_preview.setPlaceholderText("在左侧添加关键帧后，这里会汇总显示...")
        layout.addWidget(self.beats_preview)

        summary_title = QLabel("叙事逻辑概要预览")
        summary_title.setObjectName("SectionLabel")
        layout.addWidget(summary_title)

        self.summary_preview = QPlainTextEdit()
        self.summary_preview.setReadOnly(True)
        self.summary_preview.setMinimumHeight(100)
        self.summary_preview.setMaximumHeight(180)
        self.summary_preview.setPlaceholderText("左侧叙事逻辑概要的实时预览...")
        layout.addWidget(self.summary_preview)

        layout.addStretch()
        return panel

    def _build_right_cost_panel(self):
        """右侧：成本与资源预测 Tab 关联面板"""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("成本推演结果")
        title.setObjectName("SectionLabel")
        layout.addWidget(title)

        # 成本控制矩阵摘要
        matrix_title = QLabel("成本控制矩阵")
        matrix_title.setObjectName("SectionLabel")
        layout.addWidget(matrix_title)

        self.cost_matrix_preview = QPlainTextEdit()
        self.cost_matrix_preview.setReadOnly(True)
        self.cost_matrix_preview.setMinimumHeight(80)
        self.cost_matrix_preview.setMaximumHeight(100)
        layout.addWidget(self.cost_matrix_preview)

        # 智能成本推演报告
        report_title = QLabel("智能成本推演报告")
        report_title.setObjectName("SectionLabel")
        layout.addWidget(report_title)

        self.cost_report_text = QPlainTextEdit()
        self.cost_report_text.setReadOnly(True)
        self.cost_report_text.setMinimumHeight(120)
        self.cost_report_text.setMaximumHeight(180)
        self.cost_report_text.setObjectName("EngineLogEdit")
        layout.addWidget(self.cost_report_text)

        # 资源分配与投资回报摘要
        roi_title = QLabel("资源分配与投资回报摘要")
        roi_title.setObjectName("SectionLabel")
        layout.addWidget(roi_title)

        self.cost_roi_preview = QPlainTextEdit()
        self.cost_roi_preview.setReadOnly(True)
        self.cost_roi_preview.setMinimumHeight(80)
        self.cost_roi_preview.setMaximumHeight(120)
        layout.addWidget(self.cost_roi_preview)

        layout.addStretch()
        return panel

    # ==================== 事件绑定 ====================

    def _bind_events(self):
        for key, slider in self._sliders.items():
            slider.valueChanged.connect(lambda v, k=key: self._on_slider_changed(k, v))

    def _on_tab_changed(self, index: int):
        """左侧 Tab 切换时，右侧只展示关联内容，避免信息堆叠"""
        self.right_panel_gene.setVisible(index == 0)
        self.right_panel_rhythm.setVisible(index == 1)
        self.right_panel_cost.setVisible(index == 2)
        if index == 1:
            self._refresh_rhythm_preview()
        elif index == 2:
            self._update_cost_report()

    def _on_slider_changed(self, key: str, value: int):
        self._gene_values[key] = value
        self._slider_labels[key].setText(str(value))
        self.gene_chart.set_values(self._gene_values)

    def _update_rhythm_curve(self):
        values = [self._rhythm_sliders[s].value() for s in ["起", "承", "转", "合"]]
        self.rhythm_curve.set_values(values)
        if hasattr(self, "rhythm_curve_right"):
            self.rhythm_curve_right.set_values(values)

    def _refresh_rhythm_preview(self):
        """刷新右侧叙事节奏面板的预览内容"""
        if not hasattr(self, "beats_preview"):
            return

        # 关键帧汇总
        lines = []
        for r in range(self.beats_table.rowCount()):
            idx = self.beats_table.item(r, 0).text()
            summary = self.beats_table.item(r, 1).text()
            polarity = self.beats_table.item(r, 2).text()
            lines.append(f"{idx}. {summary} （{polarity}）")
        self.beats_preview.setPlainText("\n".join(lines) if lines else "暂无关键帧")

        # 叙事逻辑概要
        self.summary_preview.setPlainText(self.summary_input.toPlainText().strip() or "暂无概要")

    def _add_beat_row(self, idx: int, summary: str, polarity: str):
        r = self.beats_table.rowCount()
        self.beats_table.insertRow(r)

        idx_item = QTableWidgetItem(str(idx))
        idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beats_table.setItem(r, 0, idx_item)

        self.beats_table.setItem(r, 1, QTableWidgetItem(summary))
        self.beats_table.setItem(r, 2, QTableWidgetItem(polarity))

    def _add_beat(self):
        idx = self.beats_table.rowCount() + 1
        self._add_beat_row(idx, "新关键帧", "中性")
        self.beats_table.resizeRowsToContents()
        self._refresh_rhythm_preview()

    def _del_beat(self):
        rows = sorted({i.row() for i in self.beats_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.beats_table.removeRow(r)
        # 重新编号
        for r in range(self.beats_table.rowCount()):
            self.beats_table.item(r, 0).setText(str(r + 1))
        self.beats_table.resizeRowsToContents()
        self._refresh_rhythm_preview()

    # ==================== 成本与资源 ====================

    def _load_default_cost_items(self):
        self.cost_table.setRowCount(len(DEFAULT_COST_ITEMS))
        for r, (name, amount, note) in enumerate(DEFAULT_COST_ITEMS):
            self.cost_table.setItem(r, 0, QTableWidgetItem(name))
            amt_item = QTableWidgetItem(str(amount))
            amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cost_table.setItem(r, 1, amt_item)
            self.cost_table.setItem(r, 2, QTableWidgetItem(note))
        self.cost_table.resizeRowsToContents()
        self._adjust_cost_table_height()

    def _adjust_cost_table_height(self):
        """根据内容自动调整成本表格高度，避免内部滚动导致首行被截断"""
        header_height = self.cost_table.horizontalHeader().height()
        rows_height = sum(self.cost_table.rowHeight(r) for r in range(self.cost_table.rowCount()))
        total = header_height + rows_height + 4
        self.cost_table.setFixedHeight(max(180, min(total, 400)))

    def _add_cost_row(self):
        r = self.cost_table.rowCount()
        self.cost_table.insertRow(r)
        self.cost_table.setItem(r, 0, QTableWidgetItem("新成本项"))
        amt_item = QTableWidgetItem("0")
        amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.cost_table.setItem(r, 1, amt_item)
        self.cost_table.setItem(r, 2, QTableWidgetItem(""))
        self.cost_table.resizeRowsToContents()
        self._adjust_cost_table_height()

    def _del_cost_row(self):
        rows = sorted({i.row() for i in self.cost_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.cost_table.removeRow(r)
        self.cost_table.resizeRowsToContents()
        self._adjust_cost_table_height()

    def _calc_total_cost(self) -> int:
        total = 0
        for r in range(self.cost_table.rowCount()):
            try:
                total += int(self.cost_table.item(r, 1).text() or 0)
            except (ValueError, AttributeError):
                pass
        return total

    def _calc_roi(self):
        total = self._calc_total_cost()
        rev_text = self.roi_revenue.text().strip().replace("万", "0000").replace("元", "").replace(",", "")
        try:
            revenue = float(rev_text)
        except ValueError:
            revenue = 0
        roi = (revenue - total) / total * 100 if total else 0
        self.roi_label.setText(f"{roi:+.1f}%")
        self.cost_total_label.setText(f"{total:,.0f} 元")

    def _update_cost_report(self):
        """生成智能成本推演报告：复杂度、预估执行成本、预算状态与资源配比"""
        total = self._calc_total_cost()
        items_count = self.cost_table.rowCount()
        amounts = []
        for r in range(items_count):
            try:
                amounts.append(int(self.cost_table.item(r, 1).text() or 0))
            except (ValueError, AttributeError):
                pass

        # 基础复杂度：项目数 + 金额离散度
        complexity = 0
        if total > 0 and amounts:
            max_ratio = max(amounts) / total
            complexity = min(100, 25 + items_count * 6 + max_ratio * 40)

        # 预估执行成本 = 明细成本 + 人力投入（按每人每月 5000 估算）
        human = self.human_input.value()
        estimated = total + human * 5000

        # 预算状态
        limit = self.budget_limit_input.value()
        if estimated <= limit * 0.9:
            status = "正常"
        elif estimated <= limit:
            status = "接近红线"
        else:
            status = "超支预警"

        # 建议资源配比（取当前分配中占比最高的三项）
        resource_ratios = {
            name: self._resource_spin[key].value()
            for key, name in [
                ("creative", "内容"),
                ("tech", "开发"),
                ("promo", "营销"),
                ("offline", "线下"),
                ("ops", "运营"),
                ("other", "其他"),
            ]
        }
        sorted_res = sorted(resource_ratios.items(), key=lambda x: x[1], reverse=True)
        top3 = [f"{name}{value}%" for name, value in sorted_res if value > 0][:3]
        allocation = "、".join(top3) if top3 else "待配置"

        lines = [
            ">> 成本推演引擎启动...",
            f">> 基础复杂度: {complexity:.1f}%",
            f">> 预估执行成本: ¥ {estimated:,.1f}",
            f">> 预算状态: {status}",
            f">> 建议资源配比: {allocation}",
        ]
        self.cost_report_text.setPlainText("\n".join(lines))

        # 同步右侧成本面板摘要
        if hasattr(self, "cost_matrix_preview"):
            self.cost_matrix_preview.setPlainText(
                f"预算红线: ¥ {limit:,.2f}\n预估投入人力: {human} 人"
            )
        if hasattr(self, "cost_roi_preview"):
            total_text = self.cost_total_label.text() if hasattr(self, "cost_total_label") else "—"
            roi_text = self.roi_label.text() if hasattr(self, "roi_label") else "—"
            self.cost_roi_preview.setPlainText(
                f"总成本: {total_text}\n投资回报: {roi_text}\n资源分配: {allocation}"
            )

    # ==================== 核心算法 ====================

    def _run_analysis(self):
        """根据文化基因维度计算各渠道匹配度、推荐指数、健康度与预期效果"""
        gene = self._gene_values
        avg_gene = sum(gene.values()) / len(gene)

        results = []
        for ch in db.get_channel_templates():
            name = ch["channel"]
            weights = CHANNEL_SENSITIVITY.get(name, {})

            # 按渠道敏感度计算加权基因得分（归一化到 0-1）
            weighted_sum = sum(gene[k] * weights.get(k, 0) for k in gene)
            max_weighted = sum(weights.values()) * 100 if weights else 1
            gene_score = weighted_sum / max_weighted if max_weighted > 0 else 0

            # 基础适配度 + 基因动态加成，让不同渠道真正拉开差距
            base_fit = ch["fit"]
            fit = base_fit * 0.4 + gene_score * 0.6
            fit = max(0, min(1, fit))

            # 推荐指数：1-5 线性映射，保留区分度
            recommend = round(1 + fit * 4, 1)

            results.append({
                "channel": name,
                "audience": ch["audience"],
                "fit": fit,
                "recommend": recommend,
            })

        results.sort(key=lambda x: x["recommend"], reverse=True)
        self._last_results = results
        self._refresh_channel_table(results)
        self._update_health_score(gene, results)
        self._update_effect_forecast(results)
        self._generate_report(results)
        self._calc_roi()

    def _refresh_channel_table(self, results: list):
        self.channel_table.setRowCount(len(results))
        for r, item in enumerate(results):
            self.channel_table.setItem(r, 0, QTableWidgetItem(item["channel"]))
            self.channel_table.setItem(r, 1, QTableWidgetItem(item["audience"]))

            fit_item = QTableWidgetItem(f"{item['fit'] * 100:.1f}%")
            fit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.channel_table.setItem(r, 2, fit_item)

            rec_item = QTableWidgetItem(f"{item['recommend']:.1f}")
            rec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#38a169" if item["recommend"] >= 4.0 else "#d29922" if item["recommend"] >= 3.0 else "#718096"
            rec_item.setForeground(QColor(color))
            self.channel_table.setItem(r, 3, rec_item)

    # ==================== 健康度与效果评估 ====================

    def _update_health_score(self, gene: dict, results: list):
        avg_gene = sum(gene.values()) / len(gene)
        top_fit = results[0]["fit"] if results else 0
        variance = sum((v - avg_gene) ** 2 for v in gene.values()) / len(gene)
        std = variance ** 0.5
        balance_score = max(0, 100 - std * 1.5)

        health = avg_gene * 0.4 + top_fit * 40 + balance_score * 0.2
        health = max(0, min(100, health))
        self.health_progress.setValue(int(health))

        if health >= 85:
            grade, color = "S 级", "#38a169"
        elif health >= 70:
            grade, color = "A 级", "#00bfff"
        elif health >= 55:
            grade, color = "B 级", "#d29922"
        else:
            grade, color = "C 级", "#e53e3e"

        self.health_label.setText(grade)
        self.health_label.setStyleSheet(f"font-weight: bold; color: {color}; padding-left: 8px;")
        self.health_progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")

    def _update_effect_forecast(self, results: list):
        if not results:
            self.exposure_label.setText("曝光潜力：—")
            self.engagement_label.setText("互动潜力：—")
            self.conversion_label.setText("转化潜力：—")
            return

        top3 = results[:3]
        avg_fit = sum(r["fit"] for r in top3) / len(top3)
        gene = self._gene_values

        exposure = avg_fit * (0.7 + gene["trend"] / 200 + gene["visual"] / 200)
        engagement = avg_fit * (0.6 + gene["interact"] / 150 + gene["narrative"] / 300)
        conversion = avg_fit * (0.5 + gene["depth"] / 200 + gene["visual"] / 300)

        self.exposure_label.setText(f"曝光潜力：{exposure * 100:.0f}%")
        self.engagement_label.setText(f"互动潜力：{engagement * 100:.0f}%")
        self.conversion_label.setText(f"转化潜力：{conversion * 100:.0f}%")

    # ==================== 智能策划报告 ====================

    def _generate_report(self, results: list):
        title = self.title_input.text().strip() or "未命名策划案"
        category = self.category_combo.currentText()
        tags = self.tags_input.text().strip()
        cycle = self.cycle_input.text().strip() or "未填写"
        budget = self.budget_input.text().strip() or "未填写"
        summary = self.summary_input.toPlainText().strip()

        gene = self._gene_values
        avg_gene = sum(gene.values()) / len(gene)
        health = self.health_progress.value()
        grade = self.health_label.text()

        lines = []
        lines.append("=" * 52)
        lines.append(f"矩阵引擎 数字文化内容策划报告")
        lines.append("=" * 52)
        lines.append(f"策划名称：{title}")
        lines.append(f"文化领域：{category}")
        lines.append(f"关键词标签：{tags or '无'}")
        lines.append(f"执行周期：{cycle}    预算规模：{budget}")
        lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("一、文化基因建模分析")
        lines.append("-" * 52)
        for key, cn, _ in GENE_LABELS:
            val = gene[key]
            bar = "█" * int(val / 5) + "░" * (20 - int(val / 5))
            lines.append(f"  {cn}: {bar} {val:.0f}")
        lines.append(f"  综合基因均值：{avg_gene:.1f}")
        lines.append("")
        lines.append("二、策划健康度评估")
        lines.append("-" * 52)
        lines.append(f"  健康度得分：{health}/100")
        lines.append(f"  评级：{grade}")
        lines.append(f"  曝光潜力：{self.exposure_label.text().split('：')[1]}")
        lines.append(f"  互动潜力：{self.engagement_label.text().split('：')[1]}")
        lines.append(f"  转化潜力：{self.conversion_label.text().split('：')[1]}")
        lines.append("")
        lines.append("三、叙事节奏编排")
        lines.append("-" * 52)
        for stage in ["起", "承", "转", "合"]:
            val = self._rhythm_sliders[stage].value()
            text = self.rhythm_inputs[stage].toPlainText().strip() or "（未填写）"
            lines.append(f"  {stage}（强度 {val}）：{text[:80]}{'...' if len(text) > 80 else ''}")
        lines.append("")
        lines.append("四、成本与资源预测")
        lines.append("-" * 52)
        lines.append(f"  {self.roi_label.text()}")
        lines.append("  资源分配：")
        resource_names = {"creative": "内容创作", "tech": "技术开发", "promo": "渠道投放",
                          "offline": "线下执行", "ops": "运营人力", "other": "其他预留"}
        for key, name in resource_names.items():
            lines.append(f"    {name}：{self._resource_spin[key].value()}%")
        lines.append("")
        lines.append("五、全渠道匹配分析")
        lines.append("-" * 52)
        lines.append(f"  {'排名':<4}{'渠道':<28}{'适配度':<10}{'推荐指数':<8}")
        for idx, r in enumerate(results, 1):
            lines.append(f"  {idx:<4}{r['channel']:<28}{r['fit'] * 100:>6.1f}%    {r['recommend']:.1f}")
        lines.append("")
        lines.append("六、核心渠道执行策略")
        lines.append("-" * 52)
        for r in results[:3]:
            lines.append(f"  ▶ {r['channel']}（推荐指数 {r['recommend']:.1f}）")
            lines.append(f"    受众画像：{r['audience']}")
            lines.append(f"    执行建议：{self._channel_strategy(r['channel'], r['recommend'])}")
            lines.append("")
        lines.append("七、叙事逻辑纲要")
        lines.append("-" * 52)
        lines.append(summary or "（暂无内容）")
        lines.append("")
        lines.append("=" * 52)
        lines.append("报告由 矩阵引擎 智能策划系统生成")
        lines.append("=" * 52)

        self.report_editor.setPlainText("\n".join(lines))

    def _channel_strategy(self, channel: str, score: float) -> str:
        strategies = {
            "社交媒体矩阵": "围绕热点话题打造话题标签，结合 KOL/KOC 矩阵进行裂变传播。",
            "短视频矩阵": "提炼文化符号制作 15-60 秒视觉短片，配合挑战赛与信息流投放。",
            "中长视频平台": "制作纪录片式深度内容，邀请文化学者或 UP 主进行专业解读。",
            "数字博物馆": "构建 3D 线上展厅，嵌入语音导览与互动答题，沉淀长尾流量。",
            "AR/VR 沉浸式导览": "开发 AR 滤镜或 VR 场景，让游客在现实空间中触发文化叙事。",
            "线下沉浸式特展": "选址核心商圈或文化地标，打造光影、装置、演艺结合的打卡场景。",
            "文化研学": "联合学校与机构开发研学课程，输出标准化课件与师资培训。",
            "IP 授权": "提炼核心视觉符号，与消费品、文旅、时尚品牌进行授权合作。",
            "高端文创电商": "围绕文化 IP 开发限量文创，布局小程序商城与精品电商渠道。",
            "海外文化传播": "适配国际叙事语境，通过使领馆、文化交流机构与海外社媒进行输出。",
        }
        base = strategies.get(channel, "结合渠道特点制定专项传播方案。")
        if score >= 4.5:
            return f"作为核心主渠道重点投入；{base}"
        elif score >= 4.0:
            return f"作为主力渠道配置资源；{base}"
        elif score >= 3.0:
            return f"作为辅助渠道试点投放；{base}"
        else:
            return f"当前匹配度一般，建议谨慎投入；{base}"

    def _copy_report(self):
        text = self.report_editor.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "请先生成策划报告")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "提示", "策划报告已复制到剪贴板")

    def _export_report(self):
        text = self.report_editor.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "请先生成策划报告")
            return
        title = self.title_input.text().strip() or "策划报告"
        filename = f"{title.replace(' ', '_').replace('/', '_')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "导出策划报告", filename, "文本文件 (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "提示", f"报告已导出至：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _reset_form(self):
        self.title_input.setText("新策划案")
        self.category_combo.setCurrentIndex(0)
        self.tags_input.clear()
        self.cycle_input.setText("3个月")
        self.budget_input.setText("50万")
        self.summary_input.clear()
        self.report_editor.clear()
        for key in self._sliders:
            self._sliders[key].setValue(50)
        self._gene_values = {k: 50 for k in self._gene_values}
        self.gene_chart.set_values(self._gene_values)
        for stage in ["起", "承", "转", "合"]:
            self._rhythm_sliders[stage].setValue(50)
            self.rhythm_inputs[stage].clear()
        self._load_default_cost_items()
        self._calc_roi()
        self._run_analysis()

    # ==================== 历史库管理 ====================

    def _refresh_history(self):
        self.history_list.clear()
        for h in db.get_planning_history():
            title = h.get("title", "未命名")
            cat = h.get("category", "-")
            ts = datetime.fromtimestamp(h["created_at"]).strftime("%m-%d %H:%M")
            item = QListWidgetItem(f"[{ts}] {title} ({cat})")
            item.setData(Qt.ItemDataRole.UserRole, h["id"])
            self.history_list.addItem(item)

    def _on_history_selected(self, item: QListWidgetItem):
        self._current_history_id = item.data(Qt.ItemDataRole.UserRole)

    def _load_history_item(self):
        if not self._current_history_id:
            QMessageBox.warning(self, "提示", "请先从历史库中选择一条记录")
            return
        h = None
        for item in db.get_planning_history():
            if item["id"] == self._current_history_id:
                h = item
                break
        if not h:
            return
        self.title_input.setText(h.get("title", "新策划案"))
        self.category_combo.setCurrentText(h.get("category", ""))
        self.tags_input.setText(h.get("tags", ""))
        self.cycle_input.setText(h.get("cycle", "3个月"))
        self.budget_input.setText(h.get("budget", "50万"))
        self.summary_input.setPlainText(h.get("summary", ""))
        gene = h.get("gene", {})
        for key, val in gene.items():
            if key in self._sliders:
                self._sliders[key].setValue(val)
                self._gene_values[key] = val
                self._slider_labels[key].setText(str(val))
        self.gene_chart.set_values(self._gene_values)
        self._run_analysis()

    def _save_to_history(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "请先输入策划名称")
            return
        data = {
            "title": title,
            "category": self.category_combo.currentText(),
            "tags": self.tags_input.text().strip(),
            "cycle": self.cycle_input.text().strip(),
            "budget": self.budget_input.text().strip(),
            "gene": dict(self._gene_values),
            "summary": self.summary_input.toPlainText().strip(),
        }
        db.save_planning_history(data)
        self._refresh_history()
        QMessageBox.information(self, "提示", f"策划方案《{title}》已保存到本地缓存")

    def _delete_history_item(self):
        if not self._current_history_id:
            QMessageBox.warning(self, "提示", "请先从历史库中选择一条记录")
            return
        db.delete_planning_history(self._current_history_id)
        self._current_history_id = None
        self._refresh_history()
