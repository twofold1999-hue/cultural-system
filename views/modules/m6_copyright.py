"""
版权卫士模块 (CopyrightModule) — 参考工程优化版
=============================================
数字文化内容版权资产监测与链上存证工作台

界面结构（参考工程）：
┌─────────────────────────────────────────────────────────────┐
│ 标题                              [+ 发起版权存证]          │
├─────────────────────────────────────────────────────────────┤
│ ██████████████████████████████████████████████████████████  │
│ STATUS: GLOBAL PIRACY SCANNING IN PROGRESS...   [雷达云图]  │
├───────────────────────────────┬─────────────────────────────┤
│ 节点UID  资产名称  风险指数    │ 存证身份档案                │
│ ...                            │ 版权主标题 / 系统唯一标识   │
│ CPRT-.. 山海经... 17.88%       │ 指纹DNA序列                 │
│ CPRT-.. 故宫VR..  41.00%       │                             │
│                                │ 风险因子动态仿真 (Simulation)│
│                                │ 传播流行热度 ████░░░░░      │
│                                │ 渠道开放程度 ██░░░░░░░░     │
└───────────────────────────────┴─────────────────────────────┘

核心能力：
- 链上存证：发起版权存证，生成 PROTECTED 链上状态与指纹 DNA
- 全网盗扫：模拟 GLOBAL PIRACY SCANNING，动态刷新风险指数
- 风险因子仿真：传播热度 / 渠道开放程度影响风险指数
- 证据导出：生成带时间戳与哈希的电子证据包
"""

import json
import datetime
import random

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QWidget, QComboBox,
    QLineEdit, QMessageBox, QFileDialog, QGroupBox,
    QFormLayout, QDialog, QInputDialog,
    QSizePolicy, QListWidget, QListWidgetItem, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QRadialGradient

from views.modules.base_module import BaseBusinessModule
from database.mock_db import db


# ============================================================
#  工具函数
# ============================================================
def _risk_color(level: str) -> str:
    return {"high": "#ef4444", "medium": "#f59e0b", "low": "#34d399"}.get(level, "#94a3b8")


def _risk_label(level: str) -> str:
    return {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(level, "-")


def _chain_color(status: str) -> str:
    return {"PROTECTED": "#34d399", "PENDING": "#f59e0b", "UNPROTECTED": "#ef4444"}.get(status, "#94a3b8")


def _chain_label(status: str) -> str:
    return {"PROTECTED": "已保护", "PENDING": "待确认", "UNPROTECTED": "未保护"}.get(status, status)


# ============================================================
#  子组件：盗扫雷达可视化
# ============================================================
class PiracyScanWidget(QWidget):
    """
    深色盗扫可视化面板
    - 背景深蓝/黑色
    - 中心蓝色云雾状径向渐变
    - 外围红色闪烁点表示疑似侵权节点
    - 顶部显示扫描状态文字
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dots = []
        self._phase = 0.0
        self._status_text = "全网盗扫监控运行中"
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(80)
        self._init_dots()

    def _init_dots(self):
        self._dots = [
            {
                "x": random.uniform(0.2, 0.8),
                "y": random.uniform(0.3, 0.75),
                "r": random.uniform(2.0, 5.0),
                "speed": random.uniform(0.03, 0.08),
                "offset": random.uniform(0, 6.28),
            }
            for _ in range(18)
        ]

    def _animate(self):
        self._phase += 0.1
        self.update()

    def set_status(self, text: str):
        self._status_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # 深色背景
        painter.fillRect(0, 0, w, h, QColor("#0f172a"))

        # 中心径向云雾渐变
        gradient = QRadialGradient(w // 2, h // 2, max(w, h) // 2)
        gradient.setColorAt(0.0, QColor(56, 189, 248, 90))
        gradient.setColorAt(0.5, QColor(30, 64, 175, 40))
        gradient.setColorAt(1.0, QColor(15, 23, 42, 0))
        painter.fillRect(0, 0, w, h, gradient)

        # 扫描同心圆环
        pen = QPen(QColor(56, 189, 248, 60))
        pen.setWidth(1)
        painter.setPen(pen)
        for r in range(40, min(w, h) // 2, 40):
            painter.drawEllipse(w // 2 - r, h // 2 - r, r * 2, r * 2)

        # 扫描线
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 10
        angle = self._phase % 6.28
        pen = QPen(QColor(56, 189, 248, 120))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(cx, cy, int(cx + radius * cos(angle)), int(cy + radius * sin(angle)))

        # 红色侵权节点
        for dot in self._dots:
            pulse = abs(sin(self._phase * dot["speed"] + dot["offset"]))
            r = dot["r"] + pulse * 2
            alpha = int(120 + pulse * 135)
            color = QColor(239, 68, 68, alpha)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            dx = int(dot["x"] * w)
            dy = int(dot["y"] * h)
            painter.drawEllipse(dx - int(r), dy - int(r), int(r * 2), int(r * 2))

        # 状态文字
        painter.setPen(QColor(56, 189, 248))
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.drawText(20, 24, self._status_text)

        # 底部统计
        painter.setPen(QColor(148, 163, 184))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(20, h - 16, f"疑似侵权节点: {len(self._dots)} | 扫描频率: 实时")

        painter.end()


# 简单三角函数，避免 import math 也能工作
from math import sin, cos


# ============================================================
#  子组件：风险因子仿真控件
# ============================================================
class RiskFactorBar(QWidget):
    """带标签的进度条，用于传播热度 / 渠道开放程度"""

    def __init__(self, label: str, value: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.label = QLabel(label)
        self.label.setMinimumWidth(110)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(value)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("""
            QProgressBar { border-radius: 4px; background: #e2e8f0; height: 10px; }
            QProgressBar::chunk { border-radius: 4px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #38bdf8, stop:1 #818cf8); }
        """)
        self.value_label = QLabel(f"{value}")
        self.value_label.setMinimumWidth(30)
        layout.addWidget(self.label)
        layout.addWidget(self.bar, 1)
        layout.addWidget(self.value_label)

    def set_value(self, value: int):
        self.bar.setValue(value)
        self.value_label.setText(str(value))


# ============================================================
#  子组件：发起版权存证对话框
# ============================================================
class DepositDialog(QDialog):
    """发起版权存证：填写作品信息并生成链上存证"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("发起版权存证")
        self.setMinimumWidth(360)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText("输入作品标题")
        layout.addRow("版权主标题:", self.input_title)

        self.combo_type = QComboBox()
        for t in ["图片", "视频", "音频", "3D模型", "数字藏品", "互动H5", "图文"]:
            self.combo_type.addItem(t)
        layout.addRow("作品类型:", self.combo_type)

        self.input_owner = QLineEdit()
        self.input_owner.setPlaceholderText("输入权利人")
        layout.addRow("权利人:", self.input_owner)

        self.input_reg_no = QLineEdit()
        self.input_reg_no.setPlaceholderText("可选")
        layout.addRow("登记号:", self.input_reg_no)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("提交存证")
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
            "type": self.combo_type.currentText(),
            "owner": self.input_owner.text().strip(),
            "registration_no": self.input_reg_no.text().strip(),
        }


# ============================================================
#  主模块
# ============================================================
class CopyrightModule(BaseBusinessModule):
    """版权卫士主模块 — 参考工程优化版"""

    def __init__(self):
        # 必须在 super().__init__() 之前初始化数据属性，
        # 因为 BaseBusinessModule.__init__() 会调用 setup_ui()
        self._assets = []
        self._current_id = None
        super().__init__("版权卫士")

    def setup_ui(self):
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(12)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                color: #1e293b;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background: #f8fafc;
                color: #1e293b;
            }
            QPushButton {
                padding: 6px 14px;
                border-radius: 6px;
                min-width: 90px;
            }
        """)

        # ---------- 顶部标题栏 ----------
        header_row = QHBoxLayout()
        title = QLabel("🛡️ 版权卫士")
        title.setObjectName("SectionLabel")
        header_row.addWidget(title)
        header_row.addStretch()

        btn_deposit = QPushButton("➕ 发起版权存证")
        btn_deposit.setObjectName("PrimaryButton")
        btn_deposit.clicked.connect(self._on_deposit)
        header_row.addWidget(btn_deposit)
        self.layout.addLayout(header_row)

        # ---------- 盗扫可视化大屏 ----------
        self.scan_widget = PiracyScanWidget()
        self.layout.addWidget(self.scan_widget, stretch=1)

        # ---------- 筛选栏 ----------
        toolbar = QFrame()
        toolbar.setObjectName("ModulePanel")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索节点编号 / 资产名称...")
        self.search_input.setMinimumWidth(220)
        self.search_input.textChanged.connect(self._on_search_debounced)
        tb_layout.addWidget(self.search_input)

        self.combo_risk = QComboBox()
        self.combo_risk.addItem("全部风险", "")
        for r in [("high", "高风险"), ("medium", "中风险"), ("low", "低风险")]:
            self.combo_risk.addItem(r[1], r[0])
        self.combo_risk.currentIndexChanged.connect(self._apply_filters)
        tb_layout.addWidget(self.combo_risk)

        self.combo_chain = QComboBox()
        self.combo_chain.addItem("全部链上状态", "")
        for s in [("PROTECTED", "已保护"), ("PENDING", "待确认"), ("UNPROTECTED", "未保护")]:
            self.combo_chain.addItem(s[1], s[0])
        self.combo_chain.currentIndexChanged.connect(self._apply_filters)
        tb_layout.addWidget(self.combo_chain)

        btn_scan = QPushButton("🔍 全网盗扫")
        btn_scan.setObjectName("PrimaryButton")
        btn_scan.clicked.connect(self._on_scan)
        tb_layout.addWidget(btn_scan)

        self.status_label = QLabel("共 0 项")
        self.status_label.setStyleSheet("color:#64748b;")
        tb_layout.addStretch()
        tb_layout.addWidget(self.status_label)

        self.layout.addWidget(toolbar)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

        # ---------- 主体分割：表格 + 详情 ----------
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左：资产表格
        left_panel = QFrame()
        left_panel.setObjectName("ModulePanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)

        self.asset_table = QTableWidget(0, 4)
        self.asset_table.setHorizontalHeaderLabels(["节点编号", "资产名称", "风险指数", "链上状态"])
        self.asset_table.verticalHeader().setVisible(False)
        self.asset_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in [0, 2, 3]:
            self.asset_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.asset_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.asset_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.asset_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.asset_table.setFont(QFont("Microsoft YaHei UI", 10))
        self.asset_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.asset_table.itemSelectionChanged.connect(self._on_asset_selected)
        self.asset_table.cellClicked.connect(self._on_cell_clicked)
        left_layout.addWidget(self.asset_table)

        main_splitter.addWidget(left_panel)

        # 右：详情面板
        right_panel = QFrame()
        right_panel.setObjectName("ModulePanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(14)

        # 存证身份档案
        archive_group = QGroupBox("存证身份档案")
        archive_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        archive_layout = QFormLayout(archive_group)
        archive_layout.setSpacing(8)

        self.input_title = QLineEdit()
        self.input_title.setReadOnly(True)
        archive_layout.addRow("版权主标题:", self.input_title)

        self.input_uid = QLineEdit()
        self.input_uid.setReadOnly(True)
        archive_layout.addRow("系统唯一标识:", self.input_uid)

        self.input_dna = QLineEdit()
        self.input_dna.setReadOnly(True)
        self.input_dna.setStyleSheet("font-family:Consolas,monospace;color:#0ea5e9;background:#f1f5f9;")
        archive_layout.addRow("指纹DNA序列:", self.input_dna)

        right_layout.addWidget(archive_group)

        # 风险因子动态仿真
        sim_group = QGroupBox("风险因子动态仿真")
        sim_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        sim_layout = QVBoxLayout(sim_group)
        sim_layout.setSpacing(12)

        self.factor_popularity = RiskFactorBar("传播流行热度", 45)
        self.factor_openness = RiskFactorBar("渠道开放程度", 33)
        sim_layout.addWidget(self.factor_popularity)
        sim_layout.addWidget(self.factor_openness)

        self.sim_insight = QLabel("选择资产以查看风险因子仿真结果")
        self.sim_insight.setWordWrap(True)
        self.sim_insight.setStyleSheet("color:#64748b;line-height:1.5;")
        sim_layout.addWidget(self.sim_insight)

        btn_recalc = QPushButton("🎲 重新仿真")
        btn_recalc.setMinimumWidth(120)
        btn_recalc.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0ea5e9, stop:1 #0284c7); "
            "color: white; border: none; border-radius: 6px; padding: 6px 16px; font-weight: 600; }"
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #38bdf8, stop:1 #0ea5e9); }"
        )
        btn_recalc.clicked.connect(self._on_recalc_factors)
        sim_layout.addWidget(btn_recalc, alignment=Qt.AlignmentFlag.AlignLeft)

        right_layout.addWidget(sim_group)

        # 维权操作
        action_group = QGroupBox("维权操作")
        action_group.setStyleSheet("QGroupBox{font-weight:600;color:#1e293b;}")
        action_layout = QHBoxLayout(action_group)
        btn_evidence = QPushButton("📦 生成证据包")
        btn_evidence.setMinimumWidth(120)
        btn_evidence.setStyleSheet("padding: 6px 16px;")
        btn_evidence.clicked.connect(self._on_export_evidence)
        action_layout.addWidget(btn_evidence)
        btn_takedown = QPushButton("🚨 发起下架")
        btn_takedown.setObjectName("DangerButton")
        btn_takedown.setMinimumWidth(120)
        btn_takedown.setStyleSheet("padding: 6px 16px;")
        btn_takedown.clicked.connect(self._on_takedown)
        action_layout.addWidget(btn_takedown)
        action_layout.addStretch()
        right_layout.addWidget(action_group)

        right_layout.addStretch()
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([480, 520])
        self.layout.addWidget(main_splitter, 2)

        # 初始加载
        self._apply_filters()

    # ============================================================
    #  数据刷新
    # ============================================================
    def _get_filters(self) -> dict:
        return {
            "keyword": self.search_input.text(),
            "risk": self.combo_risk.currentData(),
            "chain_status": self.combo_chain.currentData(),
        }

    def _on_search_debounced(self):
        self._search_timer.stop()
        self._search_timer.start(300)

    def _apply_filters(self):
        self._search_timer.stop()
        # 链上状态不在 db.get_copyright_assets 原生支持，这里手动过滤
        base_assets = db.get_copyright_assets({
            "keyword": self.search_input.text(),
            "risk": self.combo_risk.currentData(),
            "status": "",
            "type": "",
        })
        chain = self.combo_chain.currentData()
        self._assets = [a for a in base_assets if not chain or a.get("chain_status") == chain]
        self._refresh_table()
        if self._assets:
            self.asset_table.selectRow(0)
            self._show_asset_detail(self._assets[0]["id"])
        else:
            self._show_asset_detail(None)

    def _refresh_table(self):
        self.asset_table.setRowCount(len(self._assets))
        self.status_label.setText(f"共 {len(self._assets)} 项")
        for i, a in enumerate(self._assets):
            uid_item = QTableWidgetItem(a["id"])
            uid_item.setFont(QFont("Consolas", 9))
            self.asset_table.setItem(i, 0, uid_item)
            self.asset_table.setItem(i, 1, QTableWidgetItem(a["title"]))

            risk_val = a.get("risk_index", 0)
            risk_item = QTableWidgetItem(f"{risk_val:.2%}")
            risk_item.setForeground(QColor(_risk_color(a["risk_level"])))
            risk_item.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
            self.asset_table.setItem(i, 2, risk_item)

            chain = a.get("chain_status", "-")
            chain_item = QTableWidgetItem(_chain_label(chain))
            chain_item.setForeground(QColor(_chain_color(chain)))
            chain_item.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
            self.asset_table.setItem(i, 3, chain_item)

    def _on_asset_selected(self):
        rows = self.asset_table.selectedIndexes()
        if not rows:
            return
        row = rows[0].row()
        if row < len(self._assets):
            self._show_asset_detail(self._assets[row]["id"])

    def _on_cell_clicked(self, row, _col):
        if row < len(self._assets):
            self._show_asset_detail(self._assets[row]["id"])

    def _show_asset_detail(self, aid: str | None):
        self._current_id = aid
        if aid is None:
            self.input_title.setText("")
            self.input_uid.setText("")
            self.input_dna.setText("")
            self.factor_popularity.set_value(0)
            self.factor_openness.set_value(0)
            self.sim_insight.setText("选择资产以查看风险因子仿真结果")
            return

        a = db.get_copyright_asset_by_id(aid)
        if not a:
            self._current_id = None
            return
        self.input_title.setText(a["title"])
        self.input_uid.setText(a["id"])
        self.input_dna.setText(a.get("fingerprint", ""))

        # 根据风险指数反推/模拟两个因子
        base = a.get("risk_index", 0.5)
        popularity = int(base * 60 + random.uniform(-10, 10))
        openness = int(base * 50 + random.uniform(-8, 8))
        popularity = max(5, min(95, popularity))
        openness = max(5, min(95, openness))
        self.factor_popularity.set_value(popularity)
        self.factor_openness.set_value(openness)

        insight = (
            f"当前风险指数 {base:.2%}。"
            f"传播流行热度 {popularity}，渠道开放程度 {openness}。"
        )
        if base >= 0.75:
            insight += "风险极高，建议立即发起下架并生成证据包。"
        elif base >= 0.4:
            insight += "风险中等，建议持续监测并补充授权。"
        else:
            insight += "风险较低，链上状态稳定。"
        self.sim_insight.setText(insight)

    # ============================================================
    #  交互事件
    # ============================================================
    def _on_deposit(self):
        dlg = DepositDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["title"]:
            QMessageBox.warning(self, "校验失败", "版权主标题不能为空")
            return
        if not data["owner"]:
            QMessageBox.warning(self, "校验失败", "权利人不能为空")
            return
        # 生成链上存证信息
        import datetime
        data["status"] = "已登记"
        data["chain_status"] = "PROTECTED"
        data["fingerprint"] = db._generate_copyright_fingerprint()
        data["risk_index"] = round(random.uniform(0.05, 0.25), 2)
        data["risk_level"] = "low"
        data["risk_reason"] = db._generate_risk_reason("已登记", "low", data["risk_index"])
        data["expire_date"] = (datetime.date.today() + datetime.timedelta(days=3650)).isoformat()
        data["last_scan"] = datetime.date.today().isoformat()
        new_id = db.add_copyright_asset(data)
        self._apply_filters()
        QMessageBox.information(self, "存证成功", f"作品 [{data['title']}] 已上链存证\n节点编号: {new_id}\n指纹: {data['fingerprint']}")

    def _on_scan(self):
        self.scan_widget.set_status("全网盗扫进行中...")
        changes = db.scan_copyright_risks()
        self._apply_filters()
        if changes:
            self.scan_widget.set_status(f"扫描完成：检测到 {len(changes)} 项风险变化")
            details = "\n".join(
                f"• [{c['id']}] {c['title']}: {c['old_risk']}({c['old_count']}) → {c['new_risk']}({c['new_count']})"
                for c in changes[:10]
            )
            QMessageBox.information(self, "扫描完成", f"检测到 {len(changes)} 项资产风险变化:\n\n{details}")
        else:
            self.scan_widget.set_status("扫描完成：未发现显著风险变化")
            QMessageBox.information(self, "扫描完成", "暂未发现显著风险变化")

    def _ensure_current_id(self) -> bool:
        """确保 _current_id 有效；如果没有，尝试读取表格当前选中行"""
        if self._current_id:
            return True
        row = self.asset_table.currentRow()
        if 0 <= row < len(self._assets):
            self._show_asset_detail(self._assets[row]["id"])
            return bool(self._current_id)
        return False

    def _on_recalc_factors(self):
        if not self._ensure_current_id():
            QMessageBox.information(self, "提示", "请先选择资产")
            return
        self._show_asset_detail(self._current_id)
        QMessageBox.information(self, "仿真完成", "风险因子已重新计算")

    def _on_export_evidence(self):
        if not self._ensure_current_id():
            QMessageBox.information(self, "提示", "请先选择资产")
            return
        evidence = db.export_copyright_evidence(self._current_id)
        if not evidence:
            QMessageBox.warning(self, "失败", "无法生成证据包")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出证据包", f"{evidence['evidence_id']}.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(evidence, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "完成", f"证据包已导出到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_takedown(self):
        if not self._ensure_current_id():
            QMessageBox.information(self, "提示", "请先选择资产")
            return
        a = db.get_copyright_asset_by_id(self._current_id)
        reply = QMessageBox.question(
            self, "确认下架",
            f"确定为 [{a['title']}] 向 {', '.join(a.get('platforms', []))} 发起下架请求吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        a["infringement_count"] = max(0, a.get("infringement_count", 0) - random.randint(1, 3))
        a["last_scan"] = datetime.date.today().isoformat()
        self._apply_filters()
        QMessageBox.information(self, "完成", "下架请求已提交平台处理")
