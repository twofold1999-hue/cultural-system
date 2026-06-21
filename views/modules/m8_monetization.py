"""
舆情反馈与共振管理模块 (SentimentResonanceModule)
=====================================================
面向数字文化平台的实时舆情监测与运营共振决策工作台。

商业级能力：
- 全网舆情实时汇聚（抖音、小红书、B站、系统内测等）
- 反馈情绪共振强度建模（0–100%）
- 实时反馈共振流动态可视化
- 核心归因与关键词提取
- 系统建议响应策略生成
- 运营共振链建立与忽略机制
"""

import csv
import json
import random
import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QWidget, QComboBox, QLineEdit, QTextEdit, QMessageBox,
    QGroupBox, QFormLayout, QFileDialog, QProgressBar,
    QSizePolicy, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient, QPen

from views.modules.base_module import BaseBusinessModule


# ============================================================
#  工具函数与常量
# ============================================================
SOURCES = ["抖音", "小红书", "B站", "系统内测", "微博", "知乎", "快手"]
USER_ROLES = ["VR体验官", "文创爱好者_01", "历史守望者", "数字漫游者", "国潮设计师", "非遗传承人", "文博研究员"]
KEYWORDS_POOL = [
    "艺术审美", "沉浸感", "文化认同", "互动体验", "画质表现",
    "叙事节奏", "音效氛围", "历史还原", "社交传播", "收藏价值",
    "付费意愿", "UI体验", "加载速度", "内容更新", "IP联名"
]
STRATEGY_TEMPLATES = [
    "用户对该内容艺术审美维度高度关注，建议持续优化视觉叙事并强化艺术家背书。",
    "沉浸感反馈良好，可借势推出线下快闪或VR联名活动，扩大文化共振。",
    "文化认同情绪强烈，建议围绕该主题生产系列化短视频与社群话题。",
    "互动体验受到期待，建议在下一版本增加用户共创与UGC投稿入口。",
    "存在画质与加载体验负向反馈，建议技术侧优先优化高清资源分发策略。",
    "社交传播势能较高，建议配置专属话题标签并联动KOL二次发酵。",
    "付费意愿与收藏价值被反复提及，可考虑推出限量数字藏品或会员专属权益。",
]


def _resonance_color(value: float) -> str:
    """共振指数越高，颜色越向红偏移；低值偏青"""
    if value >= 70:
        return "#ff2a6d"  # 高共振红
    if value >= 45:
        return "#05d9e8"  # 中共振青
    return "#00c8ff"      # 低共振蓝


def _sentiment_label(value: float) -> str:
    if value >= 60:
        return "正向波"
    if value >= 40:
        return "中性波"
    return "负向波"


def _format_time(dt: datetime.datetime) -> str:
    return dt.strftime("%m-%d %H:%M")


# ============================================================
#  自定义组件：实时反馈共振流柱状图
# ============================================================
class ResonanceFluxChart(QWidget):
    """红/青双色实时柱状图，展示舆情反馈共振流"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(130)
        self.setMaximumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._bars: list[tuple[float, bool]] = []  # (value, is_high_resonance)
        self._generate_bars()

    def _generate_bars(self):
        random.seed(datetime.datetime.now().microsecond)
        self._bars = []
        for _ in range(36):
            val = random.uniform(18, 96)
            self._bars.append((val, val >= 65))

    def update_flux(self):
        """模拟实时波动：左移并追加新数据"""
        self._bars.pop(0)
        new_val = random.uniform(18, 96)
        self._bars.append((new_val, new_val >= 65))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # 背景
        painter.fillRect(self.rect(), QColor("#0a0e17"))

        # 网格线
        pen = QPen(QColor("#1e293b"))
        pen.setWidth(1)
        painter.setPen(pen)
        for i in range(1, 5):
            y = int(h * i / 5)
            painter.drawLine(0, y, w, y)

        bar_count = len(self._bars)
        gap = 4
        bar_w = max(2, (w - (bar_count + 1) * gap) // bar_count)
        max_h = h - 24

        for i, (val, is_high) in enumerate(self._bars):
            bh = int(max_h * val / 100)
            x = gap + i * (bar_w + gap)
            y = h - bh - 12

            # 渐变色
            grad = QLinearGradient(x, y + bh, x, y)
            if is_high:
                grad.setColorAt(0.0, QColor("#ff2a6d"))
                grad.setColorAt(1.0, QColor("#b8003c"))
            else:
                grad.setColorAt(0.0, QColor("#05d9e8"))
                grad.setColorAt(1.0, QColor("#0077be"))
            painter.fillRect(x, y, bar_w, bh, grad)

        # 顶部标题
        painter.setPen(QColor("#94a3b8"))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(12, 20, "实时反馈共振流")
        painter.end()


# ============================================================
#  自定义组件：共振强度进度条
# ============================================================
class ResonanceProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setTextVisible(True)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 4px;
                background: #0f172a;
                color: #e2e8f0;
                text-align: center;
                height: 22px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0077be, stop:0.5 #05d9e8, stop:1 #ff2a6d);
                border-radius: 3px;
            }
        """)


# ============================================================
#  主模块
# ============================================================
class MonetizationModule(BaseBusinessModule):
    """舆情反馈与共振管理主模块"""

    def __init__(self):
        # 数据属性必须在 super().__init__() 之前初始化
        self._feedbacks: list[dict] = []
        self._filtered: list[dict] = []
        self._current_id: str | None = None
        self._flux_timer = None
        self._search_timer = None
        super().__init__("舆情反馈与共振管理")

    # ============================================================
    #  数据层
    # ============================================================
    def _generate_mock_data(self):
        """生成模拟舆情反馈数据"""
        random.seed(42)
        now = datetime.datetime.now()
        items = []
        for i in range(50):
            source = random.choice(SOURCES)
            user = random.choice(USER_ROLES)
            resonance = round(random.uniform(22.0, 96.0), 2)
            sentiment = random.uniform(0, 100)
            # 关键词 2-5 个
            keywords = random.sample(KEYWORDS_POOL, k=random.randint(2, 5))
            # 根据关键词和共振强度生成策略
            strategy = random.choice(STRATEGY_TEMPLATES)
            # 负向高共振时策略追加风险提示
            if resonance >= 70 and sentiment < 40:
                strategy = "【高风险预警】" + strategy + " 建议1小时内响应并启动舆情应急预案。"
            elif resonance >= 70:
                strategy = "【高共振机会】" + strategy

            items.append({
                "id": f"FBK-{random.randint(17000, 18000)}-{random.randint(20, 99):02d}",
                "user": user,
                "source": source,
                "content": self._random_content(source, keywords),
                "resonance": resonance,
                "sentiment": sentiment,
                "keywords": keywords,
                "strategy": strategy,
                "ignored": False,
                "linked": False,
                "created_at": now - datetime.timedelta(
                    minutes=random.randint(5, 10080)
                ),
            })
        items.sort(key=lambda x: x["resonance"], reverse=True)
        self._feedbacks = items

    def _random_content(self, source: str, keywords: list) -> str:
        templates = [
            f"在{source}上看到相关内容，对{keywords[0]}印象深刻，",
            f"作为一个{keywords[0]}爱好者，这次体验让我感受到{keywords[1]}，",
            f"{source}评论区很多朋友提到{keywords[0]}，",
            f"整体{keywords[0]}不错，但{keywords[1]}还有提升空间，",
            f"非常认可团队在{keywords[0]}上的投入，",
        ]
        suffix = [
            "希望能持续看到更多优质内容。",
            "期待后续更新和运营活动。",
            "建议尽快优化，避免口碑下滑。",
            "已经转发给身边的朋友。",
            "会考虑参与后续共创计划。",
        ]
        return random.choice(templates) + random.choice(suffix)

    # ============================================================
    #  UI 搭建
    # ============================================================
    def setup_ui(self):
        self.setStyleSheet("""
            QWidget { background: #0b1120; color: #e2e8f0; }
            QFrame#ModulePanel { background: #111827; border: 1px solid #1e293b; border-radius: 8px; }
            QLabel#SectionLabel { color: #f8fafc; font-size: 20px; font-weight: 700; }
            QLabel#SubTitle { color: #94a3b8; font-size: 12px; }
            QPushButton {
                background: #1e293b; color: #e2e8f0; border: 1px solid #334155;
                border-radius: 5px; padding: 6px 12px;
            }
            QPushButton:hover { background: #334155; }
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #05d9e8, stop:1 #0077be);
                color: #0b1120; font-weight: 700; border: none;
            }
            QPushButton#PrimaryButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #67e8f9, stop:1 #0ea5e9); }
            QPushButton#DangerButton { background: #ff2a6d; color: white; border: none; }
            QPushButton#DangerButton:hover { background: #ff5c8a; }
            QTableWidget {
                background: #111827; border: 1px solid #1e293b; gridline-color: #1e293b;
                color: #e2e8f0; selection-background-color: #0057d9;
            }
            QHeaderView::section { background: #0f172a; color: #94a3b8; padding: 8px; border: 1px solid #1e293b; }
            QLineEdit, QComboBox {
                background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 5px; padding: 6px;
            }
            QTextEdit { background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 5px; }
            QGroupBox { color: #94a3b8; border: 1px solid #334155; border-radius: 6px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
        """)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(12)

        # ---------- 顶部标题栏 ----------
        header_col = QVBoxLayout()
        header_col.setSpacing(2)
        title = QLabel("舆情反馈与共振管理")
        title.setObjectName("SectionLabel")
        header_col.addWidget(title)

        header_row = QHBoxLayout()
        header_row.addLayout(header_col)
        header_row.addStretch()

        btn_sync = QPushButton("⚡ 同步全网舆情")
        btn_sync.setObjectName("PrimaryButton")
        btn_sync.clicked.connect(self._on_sync)
        header_row.addWidget(btn_sync)

        self.layout.addLayout(header_row)

        # ---------- 实时反馈共振流图表 ----------
        self.flux_chart = ResonanceFluxChart()
        self.layout.addWidget(self.flux_chart, 1)

        # 启动实时波动
        self._flux_timer = QTimer(self)
        self._flux_timer.timeout.connect(self.flux_chart.update_flux)
        self._flux_timer.start(2500)

        # ---------- KPI 概览 ----------
        self.layout.addLayout(self._build_kpi_cards())

        # ---------- 筛选工具栏 ----------
        toolbar = QFrame()
        toolbar.setObjectName("ModulePanel")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索反馈ID / 用户 / 来源 / 关键词...")
        self.search_input.setMinimumWidth(240)
        self.search_input.textChanged.connect(self._on_search_debounced)
        tb_layout.addWidget(self.search_input)

        self.combo_source = QComboBox()
        self.combo_source.addItem("全部来源", "")
        for s in SOURCES:
            self.combo_source.addItem(s, s)
        self.combo_source.currentIndexChanged.connect(self._apply_filters)
        tb_layout.addWidget(self.combo_source)

        self.combo_wave = QComboBox()
        self.combo_wave.addItem("全部波形", "")
        self.combo_wave.addItem("正向波", "positive")
        self.combo_wave.addItem("负向波", "negative")
        self.combo_wave.addItem("中性波", "neutral")
        self.combo_wave.currentIndexChanged.connect(self._apply_filters)
        tb_layout.addWidget(self.combo_wave)

        self.chk_high_resonance = QCheckBox("仅看高共振")
        self.chk_high_resonance.setStyleSheet("color:#e2e8f0;")
        self.chk_high_resonance.stateChanged.connect(self._apply_filters)
        tb_layout.addWidget(self.chk_high_resonance)

        self.status_label = QLabel("共 0 项")
        self.status_label.setStyleSheet("color:#94a3b8;")
        tb_layout.addStretch()
        tb_layout.addWidget(self.status_label)

        self.layout.addWidget(toolbar)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

        # ---------- 主体：表格 + 详情 ----------
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左：反馈列表
        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        self.feedback_table = QTableWidget(0, 5)
        self.feedback_table.setHorizontalHeaderLabels(
            ["ID标识", "反馈用户", "来源", "共振指数", "波形"]
        )
        self.feedback_table.verticalHeader().setVisible(False)
        self.feedback_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for col in [0, 1, 2, 4]:
            self.feedback_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.feedback_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.feedback_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.feedback_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.feedback_table.setFont(QFont("Microsoft YaHei UI", 10))
        self.feedback_table.itemSelectionChanged.connect(self._on_feedback_selected)
        left_layout.addWidget(self.feedback_table)

        main_splitter.addWidget(left_panel)

        # 右：共振详情面板（放入滚动区域，防止内容过多被截断）
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        right_container = QFrame()
        right_container.setObjectName("ModulePanel")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(14, 12, 14, 12)
        right_layout.setSpacing(10)

        detail_title = QLabel("共振详情")
        detail_title.setObjectName("SectionLabel")
        detail_title.setStyleSheet("font-size:16px;color:#f8fafc;margin-bottom:4px;")
        right_layout.addWidget(detail_title)

        # 综合共振强度
        strength_header = QLabel("综合共振强度")
        strength_header.setStyleSheet("color:#94a3b8;font-size:11px;")
        right_layout.addWidget(strength_header)

        self.lbl_resonance_value = QLabel("-")
        self.lbl_resonance_value.setStyleSheet("color:#f8fafc;font-size:22px;font-weight:700;")
        right_layout.addWidget(self.lbl_resonance_value)

        self.resonance_progress = ResonanceProgressBar()
        self.resonance_progress.setMinimumHeight(22)
        right_layout.addWidget(self.resonance_progress)

        self.lbl_resonance_summary = QLabel("请选择一条反馈查看共振分析")
        self.lbl_resonance_summary.setStyleSheet("color:#94a3b8;font-size:11px;")
        self.lbl_resonance_summary.setWordWrap(True)
        right_layout.addWidget(self.lbl_resonance_summary)

        # 核心归因 / 关键词
        keyword_header = QLabel("核心归因 / 关键词")
        keyword_header.setStyleSheet("color:#94a3b8;font-size:11px;margin-top:6px;")
        right_layout.addWidget(keyword_header)

        self.keyword_widget = QWidget()
        self.keyword_flow = QHBoxLayout(self.keyword_widget)
        self.keyword_flow.setSpacing(6)
        self.keyword_flow.setContentsMargins(0, 0, 0, 0)
        self.keyword_flow.addStretch()
        right_layout.addWidget(self.keyword_widget)

        # 反馈原文
        content_header = QLabel("反馈原文")
        content_header.setStyleSheet("color:#94a3b8;font-size:11px;margin-top:6px;")
        right_layout.addWidget(content_header)

        self.d_content = QLabel("-")
        self.d_content.setWordWrap(True)
        self.d_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.d_content.setStyleSheet("color:#e2e8f0;background:#0f172a;border:1px solid #334155;border-radius:5px;padding:6px;")
        right_layout.addWidget(self.d_content)

        # 系统建议响应策略
        strategy_header = QLabel("系统建议响应策略")
        strategy_header.setStyleSheet("color:#94a3b8;font-size:11px;margin-top:6px;")
        right_layout.addWidget(strategy_header)

        self.d_strategy = QLabel("-")
        self.d_strategy.setWordWrap(True)
        self.d_strategy.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.d_strategy.setStyleSheet("color:#05d9e8;background:#0f172a;border:1px solid #334155;border-radius:5px;padding:6px;font-size:12px;line-height:1.4;")
        right_layout.addWidget(self.d_strategy)

        # 元信息
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(10)
        self.d_id = QLabel("ID: -")
        self.d_source = QLabel("来源: -")
        self.d_time = QLabel("时间: -")
        for lbl in (self.d_id, self.d_source, self.d_time):
            lbl.setStyleSheet("color:#94a3b8;font-size:11px;")
            meta_layout.addWidget(lbl)
        meta_layout.addStretch()
        right_layout.addLayout(meta_layout)

        # 操作按钮
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        self.btn_ignore = QPushButton("忽略")
        self.btn_ignore.setObjectName("DangerButton")
        self.btn_ignore.clicked.connect(self._on_ignore)
        action_layout.addWidget(self.btn_ignore)

        self.btn_link = QPushButton("🔗 建立运营共振链")
        self.btn_link.setObjectName("PrimaryButton")
        self.btn_link.clicked.connect(self._on_link)
        action_layout.addWidget(self.btn_link)

        action_layout.addStretch()
        right_layout.addLayout(action_layout)

        right_layout.addStretch()
        right_scroll.setWidget(right_container)

        main_splitter.addWidget(right_scroll)
        main_splitter.setSizes([480, 540])
        self.layout.addWidget(main_splitter, 2)

        # 初始数据
        self._generate_mock_data()
        self._apply_filters()

    # ============================================================
    #  KPI 卡片
    # ============================================================
    def _build_kpi_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        self.kpi_labels = {}
        kpi_defs = [
            ("共振峰值", "peak", "#ff2a6d"),
            ("正向波", "positive", "#05d9e8"),
            ("负向波", "negative", "#f59e0b"),
            ("平均共振指数", "avg", "#3b82f6"),
        ]
        for title, key, color in kpi_defs:
            card = QFrame()
            card.setObjectName("ModulePanel")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            cl.setSpacing(1)
            tl = QLabel(title)
            tl.setStyleSheet("color:#94a3b8;font-size:10px;")
            vl = QLabel("-")
            vl.setStyleSheet(f"color:{color};font-size:18px;font-weight:700;")
            cl.addWidget(tl)
            cl.addWidget(vl)
            row.addWidget(card, 1)
            self.kpi_labels[key] = vl
        return row

    def _update_kpi(self):
        if not self._feedbacks:
            for k in self.kpi_labels.values():
                k.setText("-")
            return
        active = [f for f in self._feedbacks if not f["ignored"]]
        peak = max(f["resonance"] for f in active) if active else 0
        positive = sum(1 for f in active if f["sentiment"] >= 60)
        negative = sum(1 for f in active if f["sentiment"] < 40)
        avg = round(sum(f["resonance"] for f in active) / len(active), 2) if active else 0

        self.kpi_labels["peak"].setText(f"{peak:.1f}%")
        self.kpi_labels["positive"].setText(str(positive))
        self.kpi_labels["negative"].setText(str(negative))
        self.kpi_labels["avg"].setText(f"{avg:.1f}%")

    # ============================================================
    #  数据刷新
    # ============================================================
    def _get_filters(self) -> dict:
        return {
            "keyword": self.search_input.text().strip().lower(),
            "source": self.combo_source.currentData(),
            "wave": self.combo_wave.currentData(),
            "high_only": self.chk_high_resonance.isChecked(),
        }

    def _on_search_debounced(self):
        self._search_timer.stop()
        self._search_timer.start(300)

    def _apply_filters(self):
        self._search_timer.stop()
        filters = self._get_filters()
        kw = filters["keyword"]
        self._filtered = [
            f for f in self._feedbacks
            if not f["ignored"]
            and (not filters["source"] or f["source"] == filters["source"])
            and (not filters["wave"] or self._match_wave(f, filters["wave"]))
            and (not filters["high_only"] or f["resonance"] >= 65)
            and (not kw or kw in f["id"].lower() or kw in f["user"].lower()
                 or kw in f["source"].lower() or any(kw in k.lower() for k in f["keywords"]))
        ]
        self._refresh_table()
        self._update_kpi()
        if self._filtered:
            self.feedback_table.selectRow(0)
            self._show_feedback_detail(self._filtered[0]["id"])
        else:
            self._show_feedback_detail(None)

    def _match_wave(self, f: dict, wave: str) -> bool:
        s = f["sentiment"]
        if wave == "positive":
            return s >= 60
        if wave == "negative":
            return s < 40
        return 40 <= s < 60

    def _refresh_table(self):
        self.feedback_table.setRowCount(len(self._filtered))
        self.status_label.setText(f"共 {len(self._filtered)} 项")
        for i, f in enumerate(self._filtered):
            id_item = QTableWidgetItem(f["id"])
            id_item.setFont(QFont("Consolas", 9))
            id_item.setForeground(QColor("#94a3b8"))
            self.feedback_table.setItem(i, 0, id_item)

            self.feedback_table.setItem(i, 1, QTableWidgetItem(f["user"]))
            self.feedback_table.setItem(i, 2, QTableWidgetItem(f["source"]))

            res_text = f"{f['resonance']:.2f}%"
            res_item = QTableWidgetItem(res_text)
            color = _resonance_color(f["resonance"])
            res_item.setForeground(QColor(color))
            res_item.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
            self.feedback_table.setItem(i, 3, res_item)

            wave_text = _sentiment_label(f["sentiment"])
            wave_item = QTableWidgetItem(wave_text)
            wave_item.setForeground(QColor("#05d9e8") if f["sentiment"] >= 60 else QColor("#f59e0b") if f["sentiment"] >= 40 else QColor("#ff2a6d"))
            self.feedback_table.setItem(i, 4, wave_item)

            # 高共振行高亮
            if f["resonance"] >= 70:
                for col in range(5):
                    self.feedback_table.item(i, col).setBackground(QColor("#27050d"))

    # ============================================================
    #  详情展示
    # ============================================================
    def _on_feedback_selected(self):
        rows = self.feedback_table.selectedIndexes()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self._filtered):
            self._show_feedback_detail(self._filtered[row]["id"])

    def _find_feedback(self, fid: str | None) -> dict | None:
        if not fid:
            return None
        for f in self._feedbacks:
            if f["id"] == fid:
                return f
        return None

    def _clear_keywords(self):
        """清空关键词标签"""
        while self.keyword_flow.count() > 1:
            item = self.keyword_flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_keyword_tag(self, text: str):
        """添加一个关键词标签"""
        lbl = QLabel(text)
        lbl.setStyleSheet("""
            QLabel {
                background: #0f172a; color: #05d9e8; border: 1px solid #334155;
                border-radius: 10px; padding: 4px 10px;
            }
        """)
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # 插入到 stretch 之前
        self.keyword_flow.insertWidget(self.keyword_flow.count() - 1, lbl)

    def _show_feedback_detail(self, fid: str | None):
        self._current_id = fid
        f = self._find_feedback(fid)
        if f is None:
            self.resonance_progress.setValue(0)
            self.resonance_progress.setFormat("-")
            self.lbl_resonance_value.setText("-")
            self.lbl_resonance_summary.setText("请选择一条反馈查看共振分析")
            self._clear_keywords()
            self.d_content.setText("-")
            self.d_strategy.setText("-")
            self.d_id.setText("ID: -")
            self.d_source.setText("来源: -")
            self.d_time.setText("时间: -")
            self.btn_ignore.setEnabled(False)
            self.btn_link.setEnabled(False)
            return

        self.resonance_progress.setValue(int(f["resonance"]))
        self.resonance_progress.setFormat(f"{f['resonance']:.2f}%")
        self.lbl_resonance_value.setText(f"{f['resonance']:.2f}%")
        self.lbl_resonance_value.setStyleSheet(
            f"color:{_resonance_color(f['resonance'])};font-size:24px;font-weight:700;"
        )
        wave = _sentiment_label(f["sentiment"])
        self.lbl_resonance_summary.setText(
            f"{wave} · 情绪分 {f['sentiment']:.1f} · {f['source']} · {_format_time(f['created_at'])}"
        )

        self._clear_keywords()
        for kw in f["keywords"]:
            self._add_keyword_tag(kw)

        self.d_content.setText(f"[{f['user']}] {f['content']}")
        self.d_strategy.setText(f"{f['strategy']}")

        self.d_id.setText(f"ID: {f['id']}")
        self.d_source.setText(f"来源: {f['source']}")
        self.d_time.setText(f"时间: {_format_time(f['created_at'])}")

        self.btn_ignore.setEnabled(True)
        self.btn_link.setEnabled(True)
        self.btn_link.setText("🔗 已建立运营共振链" if f["linked"] else "🔗 建立运营共振链")

    # ============================================================
    #  交互事件
    # ============================================================
    def _on_sync(self):
        """同步全网舆情：刷新数据并更新图表"""
        # 模拟新增 3-8 条反馈
        count = random.randint(3, 8)
        now = datetime.datetime.now()
        for _ in range(count):
            source = random.choice(SOURCES)
            user = random.choice(USER_ROLES)
            resonance = round(random.uniform(25.0, 98.0), 2)
            sentiment = random.uniform(0, 100)
            keywords = random.sample(KEYWORDS_POOL, k=random.randint(2, 5))
            strategy = random.choice(STRATEGY_TEMPLATES)
            if resonance >= 70 and sentiment < 40:
                strategy = "【高风险预警】" + strategy + " 建议1小时内响应并启动舆情应急预案。"
            elif resonance >= 70:
                strategy = "【高共振机会】" + strategy
            self._feedbacks.insert(0, {
                "id": f"FBK-{random.randint(17000, 18000)}-{random.randint(20, 99):02d}",
                "user": user,
                "source": source,
                "content": self._random_content(source, keywords),
                "resonance": resonance,
                "sentiment": sentiment,
                "keywords": keywords,
                "strategy": strategy,
                "ignored": False,
                "linked": False,
                "created_at": now,
            })
        self.flux_chart.update_flux()
        self._apply_filters()
        QMessageBox.information(self, "同步完成", f"已同步 {count} 条全网舆情反馈")

    def _on_ignore(self):
        if not self._current_id:
            QMessageBox.information(self, "提示", "请先选择一条反馈")
            return
        f = self._find_feedback(self._current_id)
        if not f:
            return
        f["ignored"] = True
        self._apply_filters()
        QMessageBox.information(self, "完成", f"已忽略反馈 {f['id']}")

    def _on_link(self):
        if not self._current_id:
            QMessageBox.information(self, "提示", "请先选择一条反馈")
            return
        f = self._find_feedback(self._current_id)
        if not f:
            return
        f["linked"] = not f["linked"]
        self._show_feedback_detail(f["id"])
        status = "已建立" if f["linked"] else "已取消"
        QMessageBox.information(self, "完成", f"{status}运营共振链：{f['id']}")

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出舆情共振报表",
            f"resonance_report_{datetime.date.today().isoformat()}.csv",
            "CSV (*.csv);;JSON (*.json)"
        )
        if not path:
            return
        try:
            if path.endswith(".json"):
                export_data = []
                for f in self._filtered:
                    export_data.append({
                        **f,
                        "created_at": _format_time(f["created_at"]),
                    })
                with open(path, "w", encoding="utf-8") as fp:
                    json.dump(export_data, fp, ensure_ascii=False, indent=2)
            else:
                with open(path, "w", encoding="utf-8-sig", newline="") as fp:
                    writer = csv.writer(fp)
                    writer.writerow(["ID", "用户", "来源", "共振指数", "情绪分", "波形", "关键词", "策略", "时间"])
                    for f in self._filtered:
                        writer.writerow([
                            f["id"], f["user"], f["source"], f"{f['resonance']:.2f}%",
                            f"{f['sentiment']:.1f}", _sentiment_label(f["sentiment"]),
                            ";".join(f["keywords"]), f["strategy"], _format_time(f["created_at"])
                        ])
            QMessageBox.information(self, "完成", f"报表已导出到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def cleanup(self):
        """模块切换时停止实时刷新，释放资源"""
        if self._flux_timer and self._flux_timer.isActive():
            self._flux_timer.stop()
