"""
资产库模块 (MatrixModule)
========================
数字文化资产管理中心 —— 支持多媒体资产的完整生命周期管理：
- 资产录入（图片/视频/文档/音频/三维模型）
- 多维度检索（关键词、类型、分类、状态、标签）
- 资产详情预览与编辑
- 批量操作（删除、状态变更、导出清单）
- 存储统计与标签云分析
"""

import time
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QTextEdit, QDoubleSpinBox,
    QMessageBox, QScrollArea, QWidget, QSizePolicy, QCheckBox, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter, QApplication, QMenu, QProgressBar,
    QTabWidget, QStackedWidget, QSlider, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF, QSize, QPoint, QRect
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QPen, QBrush, QFontMetrics
from database.mock_db import db
from views.modules.base_module import BaseBusinessModule


# ============================================================
#  常量定义：资产类型、状态码、类型图标映射
# ============================================================
ASSET_TYPES = {
    "image": {"label": "图片", "icon": "\U0001F5BC", "color": "#38a169"},
    "video": {"label": "视频", "icon": "\U0001F3AC", "color": "#e53e3e"},
    "audio": {"label": "音频", "icon": "\U0001F3B5", "color": "#805ad5"},
    "document": {"label": "文档", "icon": "\U0001F4C4", "color": "#dd6b20"},
}

STATUS_MAP = {
    "draft":      {"label": "草稿",   "color": "#a0aec0", "bg": "#f7fafc"},
    "reviewing":  {"label": "审核中", "color": "#dd6b20", "bg": "#fffaf0"},
    "approved":   {"label": "已通过", "color": "#38a169", "bg": "#f0fff4"},
    "published":  {"label": "已发布", "color": "#00bfff", "bg": "#ebf8ff"},
    "archived":   {"label": "已归档", "color": "#718096", "bg": "#edf2f7"},
}


def _format_size(size_mb):
    """将MB数格式化为人类可读的存储大小字符串"""
    if size_mb >= 1024:
        return f"{size_mb/1024:.1f} GB"
    return f"{size_mb:.1f} MB"


def _format_timestamp(ts):
    """Unix时间戳转为本地可读时间"""
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _get_type_label(asset_type):
    """获取资产类型的显示文本"""
    info = ASSET_TYPES.get(asset_type, {})
    icon = info.get("icon", "?")
    label = info.get("label", asset_type)
    return f"{icon} {label}"


def _get_status_badge(status):
    """生成带颜色的状态徽章HTML/文本"""
    info = STATUS_MAP.get(status, {"label": status, "color": "#718096"})
    return info["label"]


def _calc_asset_heat(asset: dict) -> int:
    """
    计算资产使用热度分（0-100）。
    综合考虑：状态权重、最近更新距今天数、文件大小、标签数量。
    """
    now = time.time()
    updated_at = asset.get("updated_at") or asset.get("created_at") or now
    days_old = max(0, (now - updated_at) / 86400)

    status_weight = {
        "published": 1.0,
        "approved": 0.85,
        "reviewing": 0.55,
        "draft": 0.3,
        "archived": 0.15,
    }.get(asset.get("status", "draft"), 0.3)

    # 越新分数越高，30 天内几乎满分，超过 180 天衰减到 0.2
    time_score = max(0.2, 1 - (days_old / 180))

    # 文件大小贡献（1GB 以上算满分，过小文件分数低）
    size_mb = asset.get("size_mb", 0)
    size_score = min(1.0, size_mb / 512)

    # 标签数量贡献
    tag_count = len(asset.get("tags", []))
    tag_score = min(1.0, tag_count / 5)

    heat = int((status_weight * 0.5 + time_score * 0.25 + size_score * 0.15 + tag_score * 0.1) * 100)
    return min(100, max(0, heat))


def _find_similar_assets(asset: dict, top_n: int = 5) -> list:
    """
    基于标签重合度与类型/分类相似度，找出相似资产。
    返回 [(similarity_score, other_asset), ...]。
    """
    target_tags = set(asset.get("tags", []))
    target_type = asset.get("type", "")
    target_category = asset.get("category", "")
    target_id = asset.get("id")

    scored = []
    for other in db.read_all_assets():
        if other.get("id") == target_id:
            continue
        other_tags = set(other.get("tags", []))
        union = target_tags | other_tags
        jaccard = len(target_tags & other_tags) / len(union) if union else 0.0

        type_bonus = 0.25 if other.get("type") == target_type else 0.0
        category_bonus = 0.15 if other.get("category") == target_category else 0.0

        score = jaccard * 0.6 + type_bonus + category_bonus
        if score > 0:
            scored.append((score, other))

    scored.sort(key=lambda x: -x[0])
    return scored[:top_n]


# ============================================================
#  子组件：标签云
# ============================================================

class _FlowLayout(QLayout):
    """
    PyQt6 流式布局 —— 自动将子控件按行排列，宽度不够时换行。
    类似 CSS flex-wrap: wrap / HTML 的流式布局。
    高度根据内容自适应，解决固定高度截断问题。
    """
    def __init__(self, parent=None, margin=0, h_spacing=6, v_spacing=6):
        super().__init__(parent)
        self._h_space = h_spacing
        self._v_space = v_spacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)  # 不向任何方向扩展

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        """根据给定宽度计算所需高度"""
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        # 用一个合理的默认宽度(400)估算最佳尺寸
        return QSize(400, self.heightForWidth(400))

    def minimumSize(self):
        # 最小宽度=单按钮宽度，最小高度=一行按钮高度
        # 用较窄的宽度(200)计算，确保不会太小
        h = max(self.heightForWidth(200), 40)
        return QSize(100, h)

    def _do_layout(self, rect, test_only):
        """核心布局算法：逐个放置子控件，超出右边界时换行

        test_only=True 时（heightForWidth调用），不跳过隐藏控件，
        确保高度预估准确。
        """
        m = self.contentsMargins()
        effective_rect = rect.adjusted(+m.left(), +m.top(), -m.right(), -m.bottom())
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()
            # test_only 模式下不跳过隐藏控件（需要准确的高度预估）
            if widget is None:
                continue
            if not test_only and not widget.isVisible():
                continue

            # 直接用构造时设置的固定间距，不再调用 QLayout.spacing()
            # （PyQt6 中 spacing() 返回 int 不是 QSize，调 .isValid() 会 AttributeError）
            space_x = self._h_space
            space_y = self._v_space

            # 用 sizeHint() 获取尺寸（test_only 模式下也有效）
            item_w = item.sizeHint().width()
            item_h = item.sizeHint().height()

            next_x = x + item_w + space_x
            if next_x - space_x > effective_rect.right() and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + space_y
                next_x = x + item_w + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item_h)

        return y + line_height - rect.y() + m.bottom()


class TagCloudWidget(QFrame):
    """
    可交互的标签云 —— 基于 QPushButton 控件组合（非 QPainter 绘制）。
    
    设计原则变更：
    - ❌ 旧方案：QPainter 自定义绘制 → painter 泄漏雪崩、颜色不可见、高度截断三大坑
    - ✅ 新方案：每个标签 = 一个 QPushButton（圆角胶囊样式）+ FlowLayout 流式布局
    
    优势：
    1. 零 QPainter → 零 painter 崩溃风险
    2. QPushButton 自带 hover/press 样式和点击事件 → 零坐标命中 bug
    3. FlowLayout 高度自适应 → 零截断问题
    """

    tag_clicked = pyqtSignal(str)

    # 5 档主题 QSS 样式模板（bg, text, border），对比度 > 3:1
    _TAG_STYLES = [
        ("#f1f5f9", "#475569", "#cbd5e1"),   # 浅灰 (最低频)
        ("#dbeafe", "#1e40af", "#93c5fd"),   # 浅蓝
        ("#d1fae5", "#065f46", "#6ee7b7"),   # 浅绿
        ("#fef3c7", "#92400e", "#fcd34d"),   # 浅琥珀
        ("#e0e7ff", "#3730a3", "#a5b4fc"),   # 靛蓝 (最高频)
    ]

    # 胶囊按钮基础 QSS 模板（{bg}/{text}/{border}/{radius} 在运行时填充）
    _PILL_QSS_TEMPLATE = """
        QPushButton {{
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            border-radius: {radius}px;
            padding: 4px 12px;
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            font-size: {size}px;
            font-weight: {weight};
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
            border-color: {hover_border};
        }}
        QPushButton:pressed {{
            background-color: {press_bg};
        }}
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TagCloudWidget")
        self._tags = []           # [(tag_name, count), ...]
        self._max_count = 1
        self._buttons = []        # 缓存创建的 QPushButton 引用（用于 rebuild 时清理）

        # 流式布局容器
        self._flow_layout = _FlowLayout(self, margin=8, h_spacing=6, v_spacing=6)
        self.setLayout(self._flow_layout)

        # 移除所有固定高度限制，让 FlowLayout 自适应内容高度
        self.setMinimumHeight(48)

    def set_tags(self, tags: list):
        """tags: [(tag_name, count), ...] — 重建所有按钮"""
        self._tags = tags or []
        self._max_count = max((c for _, c in self._tags), default=1)
        self._rebuild_buttons()

    def clear(self):
        self._tags = []
        self._max_count = 1
        self._rebuild_buttons()

    def _rebuild_buttons(self):
        """销毁旧按钮，根据当前 _tags 创建新按钮"""
        # 清理旧按钮
        for btn in self._buttons:
            btn.deleteLater()
        self._buttons.clear()

        if not self._tags:
            # 空状态提示
            hint = QLabel("暂无标签数据")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 8px;")
            self._flow_layout.addWidget(hint)
            self._buttons.append(hint)  # 方便下次清理
            return

        for idx, (tag_text, count) in enumerate(self._tags):
            btn = QPushButton(tag_text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

            # 计算样式参数
            ratio = count / max(self._max_count, 1)
            palette_idx = min(int(ratio * len(self._TAG_STYLES)), len(self._TAG_STYLES) - 1)
            bg_color, text_color, border_color = self._TAG_STYLES[palette_idx]

            font_size = 11 + int(ratio * 2)     # 11 ~ 13
            weight = "bold" if ratio > 0.55 else "normal"
            radius = 14                          # 固定圆角

            # hover/press 变体色
            bg_q = QColor(bg_color)
            bdr_q = QColor(border_color)
            hover_bg = bg_q.darker(108).name()
            hover_border = bdr_q.darker(120).name()
            press_bg = bg_q.darker(116).name()

            # 组装 QSS
            qss = self._PILL_QSS_TEMPLATE.format(
                bg=bg_color, text=text_color, border=border_color,
                radius=int(radius), size=font_size, weight=weight,
                hover_bg=hover_bg, hover_border=hover_border,
                press_bg=press_bg,
            )
            btn.setStyleSheet(qss)

            # 点击信号
            btn.clicked.connect(lambda checked=False, t=tag_text: self.tag_clicked.emit(t))

            # 加入布局
            self._flow_layout.addWidget(btn)
            self._buttons.append(btn)


# ============================================================
#  子组件：新增 / 编辑资产对话框
# ============================================================
class AssetEditDialog(QDialog):
    """
    资产编辑弹窗
    支持新建和编辑两种模式，通过 is_edit 参数区分
    包含表单验证逻辑：名称必填、大小必须为正数、标签非空检查
    """

    def __init__(self, parent=None, asset_data=None, categories=None):
        super().__init__(parent)
        self.asset_data = asset_data  # None=新建模式，有值=编辑模式
        self.categories = categories or []
        self.is_edit = asset_data is not None
        self.setWindowTitle("编辑资产" if self.is_edit else "新增资产")
        self.setFixedSize(480, 520)
        self.setModal(True)

        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # 表单主体
        form_container = QFrame()
        form_container.setObjectName("DialogCard")
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(24, 24, 24, 16)

        title_text = "编辑资产信息" if self.is_edit else "录入新资产"
        title_lbl = QLabel(title_text)
        title_lbl.setObjectName("DialogTitle")
        form_layout.addWidget(title_lbl)
        form_layout.addSpacing(12)

        form_body = QFormLayout()
        form_body.setSpacing(12)
        form_body.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # --- 名称输入 ---
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("请输入资产名称（含扩展名）")
        self.input_name.setMinimumHeight(34)
        form_body.addRow("资产名称 *", self.input_name)

        # --- 类型选择 ---
        self.combo_type = QComboBox()
        self.combo_type.setMinimumHeight(34)
        for key, val in ASSET_TYPES.items():
            self.combo_type.addItem(f"{val['icon']} {val['label']}", userData=key)
        form_body.addRow("资产类型 *", self.combo_type)

        # --- 分类选择 ---
        self.combo_category = QComboBox()
        self.combo_category.setMinimumHeight(34)
        self.combo_category.setEditable(True)  # 允许自定义输入新分类
        self.combo_category.setPlaceholderText("选择或输入分类...")
        for cat in self.categories:
            self.combo_category.addItem(cat)
        form_body.addRow("所属分类 *", self.combo_category)

        # --- 标签输入 ---
        self.input_tags = QLineEdit()
        self.input_tags.setPlaceholderText("多个标签以英文逗号分隔，如: 国潮,插画,龙")
        self.input_tags.setMinimumHeight(34)
        form_body.addRow("标签集", self.input_tags)

        # --- 文件大小 ---
        self.spin_size = QDoubleSpinBox()
        self.spin_size.setRange(0.01, 999999)
        self.spin_size.setSuffix(" MB")
        self.spin_size.setDecimals(1)
        self.spin_size.setMinimumHeight(34)
        form_body.addRow("文件大小(MB)", self.spin_size)

        # --- 状态选择 ---
        self.combo_status = QComboBox()
        self.combo_status.setMinimumHeight(34)
        for key, val in STATUS_MAP.items():
            self.combo_status.addItem(val["label"], userData=key)
        form_body.addRow("当前状态", self.combo_status)

        # --- 描述文本域 ---
        self.text_desc = QTextEdit()
        self.text_desc.setPlaceholderText("详细描述资产的用途、来源、版权说明等...")
        self.text_desc.setMaximumHeight(80)
        form_body.addRow("描述说明", self.text_desc)

        # --- 存储路径 ---
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("/资源/...")
        self.input_path.setMinimumHeight(34)
        form_body.addRow("存储路径", self.input_path)

        form_layout.addLayout(form_body)

        # 底部按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("BtnUpdate")
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_submit = QPushButton("确认保存" if self.is_edit else "创建资产")
        btn_submit.setObjectName("BtnCreate")
        btn_submit.setFixedWidth(100)
        btn_submit.clicked.connect(self._on_submit)
        btn_row.addWidget(btn_submit)

        form_layout.addLayout(btn_row)
        outer_layout.addWidget(form_container)

    def _load_data(self):
        """编辑模式下回填现有数据到表单"""
        d = self.asset_data
        self.input_name.setText(d.get("name", ""))
        # 设置类型下拉框
        t = d.get("type", "document")
        idx = self.combo_type.findData(t)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)
        # 分类
        cat = d.get("category", "")
        cidx = self.combo_category.findText(cat)
        if cidx >= 0:
            self.combo_category.setCurrentIndex(cidx)
        else:
            self.combo_category.setCurrentText(cat)
        # 标签
        tags_str = ",".join(d.get("tags", []))
        self.input_tags.setText(tags_str)
        # 大小
        self.spin_size.setValue(d.get("size_mb", 0))
        # 状态
        s = d.get("status", "draft")
        sidx = self.combo_status.findData(s)
        if sidx >= 0:
            self.combo_status.setCurrentIndex(sidx)
        # 描述
        self.text_desc.setPlainText(d.get("description", ""))
        # 路径
        self.input_path.setText(d.get("path", ""))

    def get_form_data(self):
        """收集表单数据并返回字典，供外部调用"""
        tags_raw = self.input_tags.text().strip()
        tag_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

        return {
            "name": self.input_name.text().strip(),
            "type": self.combo_type.currentData(),
            "category": self.combo_category.currentText().strip(),
            "tags": tag_list,
            "size_mb": self.spin_size.value(),
            "status": self.combo_status.currentData(),
            "description": self.text_desc.toPlainText().strip(),
            "path": self.input_path.text().strip(),
        }

    def _validate(self):
        """表单校验，返回 (是否通过, 错误消息)"""
        name = self.input_name.text().strip()
        if not name:
            return False, "资产名称不能为空"
        if len(name) < 2:
            return False, "资产名称至少需要2个字符"
        if not self.combo_type.currentData():
            return False, "请选择资产类型"
        category = self.combo_category.currentText().strip()
        if not category:
            return False, "请选择或输入所属分类"
        if self.spin_size.value() <= 0:
            return False, "文件大小必须大于0"
        return True, ""

    def _on_submit(self):
        ok, msg = self._validate()
        if not ok:
            QMessageBox.warning(self, "表单校验", msg)
            return
        self.accept()


# ============================================================
#  子组件：资产详情编辑面板（参考工程风格）
# ============================================================
class AssetDetailPanel(QFrame):
    """
    右侧资产详情编辑面板
    - 四标签页：核心元数据 / 价值维度 / 操作日志 / 相似推荐
    - 核心元数据支持直接编辑
    - 底部蓝色大按钮：提交更改并同步
    - 底部白色按钮：永久抹除资源
    - 相似推荐页基于标签重合度+类型相似度自动推荐
    """

    edit_requested = pyqtSignal(dict)   # 发出完整编辑对话框请求
    sync_requested = pyqtSignal(dict)   # 发出同步请求，附带当前面板编辑后的数据
    purge_requested = pyqtSignal(dict)  # 发出永久抹除请求
    similar_asset_clicked = pyqtSignal(str)  # 相似资产推荐点击跳转

    def __init__(self):
        super().__init__()
        self.setObjectName("ModulePanel")
        self._current_asset = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # 标签页（参考工程：元数据视图 | 价值算法矩阵 | 审计日志流）
        self.tab_widget = QTabWidget()
        self.tab_widget.setVisible(False)

        # 标签页 1：元数据视图
        self.tab_metadata = QScrollArea()
        self.tab_metadata.setWidgetResizable(True)
        self.metadata_widget = QWidget()
        self.metadata_layout = QVBoxLayout(self.metadata_widget)
        self.metadata_layout.setSpacing(10)
        self.tab_metadata.setWidget(self.metadata_widget)
        self.tab_widget.addTab(self.tab_metadata, "元数据视图")

        # 标签页 2：价值算法矩阵（参考工程：4个滑块 + 推演按钮）
        self.tab_value = QScrollArea()
        self.tab_value.setWidgetResizable(True)
        self.value_widget = QWidget()
        self.value_layout = QVBoxLayout(self.value_widget)
        self.value_layout.setSpacing(16)
        self.tab_value.setWidget(self.value_widget)
        self.tab_widget.addTab(self.tab_value, "价值算法矩阵")

        # 标签页 3：审计日志流
        self.tab_logs = QTextEdit()
        self.tab_logs.setReadOnly(True)
        self.tab_logs.setStyleSheet(
            "QTextEdit { border: none; background: #f7fafc; padding: 10px; font-size: 12px; color: #4a5568; }"
        )
        self.tab_widget.addTab(self.tab_logs, "审计日志流")

        # 标签页 4：相似资产推荐（接入 _find_similar_assets）
        self.tab_similar = QScrollArea()
        self.tab_similar.setWidgetResizable(True)
        self.similar_widget = QWidget()
        self.similar_layout = QVBoxLayout(self.similar_widget)
        self.similar_layout.setSpacing(10)
        self.tab_similar.setWidget(self.similar_widget)
        self.tab_widget.addTab(self.tab_similar, "相似推荐")

        layout.addWidget(self.tab_widget, 1)

        # 空状态提示（叠加在标签页上方）
        self.empty_hint = QLabel("\u27A4 请在左侧选择一个资产\n   以查看或编辑详细信息")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setStyleSheet(
            "color: #a0aec0; font-size: 13px; padding: 40px; background: transparent;"
        )
        layout.addWidget(self.empty_hint)
        self.empty_hint.raise_()  # 置顶显示

        # 底部操作按钮区（参考工程：销毁粉红 + 提交变更至矩阵库蓝色）
        self.action_bar_frame = QFrame()
        self.action_bar_frame.setVisible(False)
        self.action_bar = QVBoxLayout(self.action_bar_frame)
        self.action_bar.setContentsMargins(0, 0, 0, 0)
        self.action_bar.setSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_purge = QPushButton("销毁")
        self.btn_purge.setObjectName("BtnDelete")
        self.btn_purge.setFixedHeight(38)
        self.btn_purge.setMinimumWidth(80)
        self.btn_purge.setStyleSheet(
            "QPushButton { background: #fff1f2; color: #be123c; border: 1px solid #fecdd3; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background: #ffe4e6; }"
        )
        self.btn_purge.clicked.connect(self._emit_purge)
        btn_row.addWidget(self.btn_purge)

        self.btn_sync = QPushButton("提交变更至矩阵库")
        self.btn_sync.setObjectName("BtnCreate")
        self.btn_sync.setFixedHeight(38)
        self.btn_sync.setStyleSheet(
            "QPushButton { background: #0284c7; color: white; border: none; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background: #0ea5e9; }"
        )
        self.btn_sync.clicked.connect(self._emit_sync)
        btn_row.addWidget(self.btn_sync, 1)

        self.action_bar.addLayout(btn_row)
        layout.addWidget(self.action_bar_frame)

    @staticmethod
    def _build_slider_section(title: str, value: int) -> QVBoxLayout:
        """构建参考工程风格的滑块行：标签 + 水平滑块"""
        box = QVBoxLayout()
        box.setSpacing(6)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 12px; color: #475569; font-weight: 600;")
        box.addWidget(lbl)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(value)
        slider.setFixedHeight(28)
        slider.setStyleSheet(
            # 整体滑块容器：无边框透明背景
            "QSlider { border: none; background: transparent; padding: 0px; }"
            # 轨道槽（未填充部分）：浅灰圆角条
            "QSlider::groove:horizontal {"
            "  border: none;"
            "  height: 6px;"
            "  background: #e2e8f0;"
            "  border-radius: 3px;"
            "}"
            # 已填充部分（左侧蓝色条）
            "QSlider::sub-page:horizontal {"
            "  border: none;"
            "  height: 6px;"
            "  background: #0ea5e9;"
            "  border-radius: 3px;"
            "}"
            # 滑块手柄（白色圆圈+蓝色边框）
            "QSlider::handle:horizontal {"
            "  background: #ffffff;"
            "  border: 2px solid #0ea5e9;"
            "  width: 18px; height: 18px;"
            "  margin: -7px 0;"
            "  border-radius: 10px;"
            "}"
            # 手柄悬停效果
            "QSlider::handle:horizontal:hover {"
            "  background: #f0f9ff;"
            "  border-color: #38bdf8;"
            "}"
        )
        slider_row.addWidget(slider, 1)

        val_lbl = QLabel(f"{value}")
        val_lbl.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; min-width: 30px;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider_row.addWidget(val_lbl)

        box.addLayout(slider_row)
        return box

    def _make_form_field(self, label: str, widget: QWidget) -> QVBoxLayout:
        """构建表单字段：标签 + 控件"""
        box = QVBoxLayout()
        box.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; color: #64748b; font-weight: 600;")
        box.addWidget(lbl)
        box.addWidget(widget)
        return box

    def _generate_operation_logs(self, asset: dict) -> str:
        """根据资产信息生成模拟操作日志"""
        lines = []
        created = _format_timestamp(asset.get("created_at"))
        updated = _format_timestamp(asset.get("updated_at"))
        lines.append(f"[{created}] 资产「{asset.get('name', '-')}」创建入库")
        lines.append(f"[{updated}] 元数据更新，状态: {_get_status_badge(asset.get('status', 'draft'))}")
        if asset.get("status") in ("approved", "published"):
            lines.append(f"[{updated}] 通过审核并进入可用状态")
        lines.append(f"[{updated}] 系统完成热度与相似度分析")
        return "\n".join(lines)

    def show_asset(self, asset: dict | None):
        """加载并显示资产详情（分四个标签页：元数据/价值矩阵/审计日志/相似推荐）"""
        # 清除旧内容（元数据、价值矩阵、相似推荐）
        for layout in (self.metadata_layout, self.value_layout, self.similar_layout):
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    while child.layout().count():
                        sub = child.layout().takeAt(0)
                        if sub.widget():
                            sub.widget().deleteLater()

        if not asset:
            self._current_asset = None
            self.empty_hint.setVisible(True)
            self.tab_widget.setVisible(False)
            self.action_bar_frame.setVisible(False)
            return

        self._current_asset = asset
        self.empty_hint.setVisible(False)
        self.tab_widget.setVisible(True)
        self.action_bar_frame.setVisible(True)

        # ========== 核心元数据标签页（可编辑） ==========
        self.edit_name = QLineEdit(asset.get("name", ""))
        self.edit_name.setMinimumHeight(30)
        self.metadata_layout.addLayout(self._make_form_field("资源名称", self.edit_name))

        self.edit_id = QLineEdit(asset.get("id", ""))
        self.edit_id.setReadOnly(True)
        self.edit_id.setMinimumHeight(30)
        self.edit_id.setStyleSheet("background: #f1f5f9; color: #64748b;")
        self.metadata_layout.addLayout(self._make_form_field("系统编号", self.edit_id))

        self.edit_category = QComboBox()
        self.edit_category.setMinimumHeight(30)
        self.edit_category.addItem("未分类", userData="未分类")
        for cat in db.get_asset_statistics().get("categories", []):
            self.edit_category.addItem(cat, userData=cat)
        idx = self.edit_category.findData(asset.get("category", "未分类"))
        self.edit_category.setCurrentIndex(max(0, idx))
        self.metadata_layout.addLayout(self._make_form_field("资源分类", self.edit_category))

        self.edit_status = QComboBox()
        self.edit_status.setMinimumHeight(30)
        for key, val in STATUS_MAP.items():
            self.edit_status.addItem(val["label"], userData=key)
        idx = self.edit_status.findData(asset.get("status", "draft"))
        self.edit_status.setCurrentIndex(max(0, idx))
        self.metadata_layout.addLayout(self._make_form_field("当前状态", self.edit_status))

        self.edit_tags = QLineEdit(", ".join(asset.get("tags", [])))
        self.edit_tags.setMinimumHeight(30)
        self.edit_tags.setPlaceholderText("多个标签用逗号分隔")
        self.metadata_layout.addLayout(self._make_form_field("关联标签", self.edit_tags))

        self.edit_path = QLineEdit(asset.get("path", ""))
        self.edit_path.setMinimumHeight(30)
        self.metadata_layout.addLayout(self._make_form_field("存储路径", self.edit_path))

        self.edit_desc = QTextEdit(asset.get("description", ""))
        self.edit_desc.setMinimumHeight(80)
        self.edit_desc.setPlaceholderText("请输入资产描述...")
        self.metadata_layout.addLayout(self._make_form_field("资源描述", self.edit_desc))

        meta_info = QLabel(
            f"创建时间：{_format_timestamp(asset.get('created_at'))}  "
            f"更新时间：{_format_timestamp(asset.get('updated_at'))}  "
            f"大小：{_format_size(asset.get('size_mb', 0))}"
        )
        meta_info.setStyleSheet("color: #94a3b8; font-size: 11px; padding-top: 6px;")
        self.metadata_layout.addWidget(meta_info)
        self.metadata_layout.addStretch()

        # ========== 价值算法矩阵标签页（参考工程：4个滑块 + 引擎推演按钮） ==========
        heat = _calc_asset_heat(asset)
        completeness = min(100, max(0, 60 + len(asset.get("tags", [])) * 8 + (1 if asset.get("description") else 0) * 15))
        value_score = int((heat * 0.5 + completeness * 0.3 + (100 if asset.get("status") == "published" else 60) * 0.2))
        pub_maturity = 100 if asset.get("status") == "published" else 55

        self.value_layout.addLayout(self._build_slider_section("文化稀缺度:", heat))
        self.value_layout.addLayout(self._build_slider_section("技术规格指标:", int(completeness)))
        self.value_layout.addLayout(self._build_slider_section("文物底蕴分值:", value_score))
        self.value_layout.addLayout(self._build_slider_section("二次开发潜力:", pub_maturity))

        # 启动引擎推演深色按钮（原始简单版本）
        self.btn_infer = QPushButton("启动引擎推演")
        self.btn_infer.setFixedHeight(40)
        self.btn_infer.setMinimumWidth(160)
        self.btn_infer.setStyleSheet(
            "QPushButton { background: #1e293b; color: #e2e8f0; border: none; border-radius: 6px; font-weight: 600; font-size: 13px; }"
            "QPushButton:hover { background: #334155; color: #ffffff; }"
            "QPushButton:disabled { background: #94a3b8; color: #fff; }"
        )
        self.btn_infer.clicked.connect(self._on_infer_engine)
        self.value_layout.addWidget(self.btn_infer)

        self.value_layout.addStretch()

        # ========== 操作日志标签页 ==========
        self.tab_logs.setText(self._generate_operation_logs(asset))

        # ========== 相似资产推荐标签页（接入 _find_similar_assets）==========
        self._build_similar_assets_tab(asset)

    def _build_similar_assets_tab(self, asset: dict):
        """构建相似资产推荐标签页内容"""
        # 说明标题
        hint_lbl = QLabel(
            "基于标签重合度（Jaccard 系数）与类型/分类相似度自动推荐，"
            "点击卡片可跳转查看详情。"
        )
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #64748b; font-size: 12px; padding: 4px 0;")
        self.similar_layout.addWidget(hint_lbl)

        # 调用 _find_similar_assets 获取推荐列表
        similar_list = _find_similar_assets(asset, top_n=5)

        if not similar_list:
            empty_lbl = QLabel("暂无相似资产推荐\n\n可能原因：\n• 当前资产没有标签\n• 资产库中没有标签重合的其他资产")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #a0aec0; font-size: 13px; padding: 30px;")
            self.similar_layout.addWidget(empty_lbl)
            self.similar_layout.addStretch()
            return

        # 标题行
        title_lbl = QLabel(f"共找到 {len(similar_list)} 个相似资产")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155; padding: 4px 0;")
        self.similar_layout.addWidget(title_lbl)

        # 逐个构建相似资产卡片
        for score, other in similar_list:
            self.similar_layout.addWidget(self._build_similar_card(other, score))

        self.similar_layout.addStretch()

    def _build_similar_card(self, other: dict, score: float) -> QFrame:
        """构建单个相似资产推荐卡片"""
        card = QFrame()
        card.setObjectName("SimilarCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        pct = int(score * 100)
        border_c = "#22c55e" if pct >= 40 else "#f59e0b" if pct >= 20 else "#cbd5e1"
        card.setStyleSheet(
            f"QFrame#SimilarCard {{ border: 1px solid {border_c}; border-radius: 8px; background: #ffffff; }}"
            f"QFrame#SimilarCard:hover {{ border: 2px solid #0ea5e9; }}"
        )

        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(12)

        # 左侧：类型色块缩略
        type_info = ASSET_TYPES.get(other.get("type", "other"), {"icon": "?", "label": "其他", "color": "#64748b"})
        thumb = QLabel(f"{type_info['icon']}")
        thumb.setFixedSize(40, 40)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet(
            f"background: {type_info['color']}22; border-radius: 8px; font-size: 20px;"
        )
        row.addWidget(thumb)

        # 中间：名称 + 标签
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(other.get("name", "-"))
        name_lbl.setStyleSheet("font-weight: 600; color: #1e293b; font-size: 13px;")
        info_col.addWidget(name_lbl)

        tags = other.get("tags", [])
        tags_text = ", ".join(tags[:4]) + ("..." if len(tags) > 4 else "")
        tags_lbl = QLabel(f"🏷 {tags_text}" if tags_text else "无标签")
        tags_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(tags_lbl)
        row.addLayout(info_col, 1)

        # 右侧：相似度百分比
        score_lbl = QLabel(f"{pct}%")
        score_color = "#22c55e" if pct >= 40 else "#f59e0b" if pct >= 20 else "#94a3b8"
        score_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {score_color}; min-width: 45px;"
        )
        score_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(score_lbl)

        # 点击跳转
        other_id = other.get("id", "")
        card.mousePressEvent = lambda ev, _id=other_id: self.similar_asset_clicked.emit(_id)

        return card

    def switch_to_similar_tab(self):
        """切换到相似推荐标签页（供右键菜单"查看相似资产"调用）"""
        self.tab_widget.setCurrentWidget(self.tab_similar)

    def _collect_edited_data(self) -> dict:
        """收集面板中编辑后的数据"""
        if not self._current_asset:
            return {}
        tags_text = self.edit_tags.text().strip()
        tags = [t.strip() for t in tags_text.split(",") if t.strip()]
        return {
            "id": self._current_asset.get("id"),
            "name": self.edit_name.text().strip(),
            "category": self.edit_category.currentData() or "未分类",
            "status": self.edit_status.currentData() or "draft",
            "tags": tags,
            "path": self.edit_path.text().strip(),
            "description": self.edit_desc.toPlainText().strip(),
            "type": self._current_asset.get("type"),
            "size_mb": self._current_asset.get("size_mb"),
        }

    def _emit_sync(self):
        if self._current_asset:
            self.sync_requested.emit(self._collect_edited_data())

    def _emit_purge(self):
        if self._current_asset:
            self.purge_requested.emit(self._current_asset)

    def _on_infer_engine(self):
        """启动引擎推演：模拟价值矩阵分析推演过程"""
        if not self._current_asset:
            return
        if hasattr(self, 'btn_infer') and self.btn_infer is not None:
            self.btn_infer.setEnabled(False)
            self.btn_infer.setText("推演中...")
        QTimer.singleShot(1200, lambda: self._on_infer_finish())

    def _on_infer_finish(self):
        """推演完成回调"""
        if hasattr(self, 'btn_infer') and self.btn_infer is not None:
            self.btn_infer.setEnabled(True)
            self.btn_infer.setText("启动引擎推演")
        self.sync_requested.emit(self._collect_edited_data())


# ============================================================
#  子组件：资产卡片网格视图
# ============================================================
class AssetCardGrid(QScrollArea):
    """
    卡片网格视图：以缩略图卡片形式展示资产。
    - 单击选中，双击编辑，右键弹出操作菜单
    - 支持批量选择模式（checkbox 切换）
    """

    card_clicked = pyqtSignal(str)      # 发出资产 id
    card_double_clicked = pyqtSignal(str)
    card_context_menu = pyqtSignal(str, QPointF)  # 右键菜单信号（资产id, 全局坐标）
    selection_changed = pyqtSignal(set)  # 批量模式选中集合变更

    TYPE_PREVIEW_COLORS = {
        "image":   "#2d3748",
        "video":   "#1a202c",
        "audio":   "#744210",
        "document":"#2c5282",
        "model3d": "#285e61",
        "design":  "#702459",
        "data":    "#276749",
        "other":   "#4a5568",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AssetCardGrid")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._assets = []
        self._selected_id = None
        self._batch_mode = False
        self._batch_selected = set()  # 批量模式下选中的资产 id 集合
        self._setup_ui()

    def _setup_ui(self):
        container = QWidget()
        self.setWidget(container)
        self._grid = QGridLayout(container)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setSpacing(12)

    def set_assets(self, assets: list):
        """刷新卡片网格"""
        self._assets = assets
        self._refresh_grid()

    def _refresh_grid(self):
        # 清空旧卡片
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not self._assets:
            hint = QLabel("暂无资产，请点击「资源接入」录入")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setStyleSheet("color: #a0aec0; padding: 40px; font-size: 14px;")
            self._grid.addWidget(hint, 0, 0, 1, 2)
            return

        cols = 2  # 参考工程：双列布局
        for idx, asset in enumerate(self._assets):
            row, col = divmod(idx, cols)
            card = self._build_card(asset)
            self._grid.addWidget(card, row, col)

    def set_batch_mode(self, enabled: bool):
        """开启/关闭批量选择模式"""
        self._batch_mode = enabled
        if not enabled:
            self._batch_selected.clear()
            self.selection_changed.emit(set())
        self._refresh_grid()

    def _build_card(self, asset: dict) -> QFrame:
        aid = asset.get("id", "")
        is_selected = aid == self._selected_id
        is_batch_checked = aid in self._batch_selected

        card = QFrame()
        card.setObjectName("AssetCard")
        card.setProperty("asset_id", aid)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        # 选中/批量勾选边框样式
        if self._batch_mode and is_batch_checked:
            border_color = "#f59e0b"
            border_width = "2px"
        elif is_selected:
            border_color = "#0ea5e9"
            border_width = "2px"
        else:
            border_color = "#e2e8f0"
            border_width = "1px"

        card.setStyleSheet(
            f"QFrame#AssetCard {{ border: {border_width} solid {border_color}; border-radius: 8px; background: #ffffff; }}"
            f"QFrame#AssetCard:hover {{ border: 2px solid #38bdf8; }}"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 预览色块区域（参考工程：纯色深绿/深蓝块，占主要空间）
        preview = QFrame()
        preview.setFixedHeight(120)
        bg_color = self.TYPE_PREVIEW_COLORS.get(asset.get("type", "other"), "#1a3a2a")

        # 批量模式下在预览区左上角叠加 checkbox 指示
        if self._batch_mode:
            check_mark = "✓" if is_batch_checked else "○"
            check_color = "#fbbf24" if is_batch_checked else "rgba(255,255,255,0.6)"
            preview.setStyleSheet(
                f"background: {bg_color};"
                f"border-top-left-radius: 8px; border-top-right-radius: 8px;"
            )
            # 叠加选择标记
            overlay = QLabel(check_mark, preview)
            overlay.setStyleSheet(
                f"color: {check_color}; font-size: 24px; font-weight: bold; background: transparent;"
            )
            overlay.setGeometry(8, 6, 30, 30)
        else:
            preview.setStyleSheet(
                f"background: {bg_color};"
                f"border-top-left-radius: 8px; border-top-right-radius: 8px;"
            )

        # 热度角标（右上角小标签）
        heat = _calc_asset_heat(asset)
        heat_text = QLabel(f"{heat}", preview)
        heat_text.setStyleSheet(
            f"background: rgba(0,0,0,0.5); color: {'#4ade80' if heat >= 60 else '#fbbf24' if heat >= 30 else '#94a3b8'};"
            f"font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;"
        )
        heat_text.setGeometry(preview.width() - 40, 8, 32, 18) if preview.width() > 50 else None

        layout.addWidget(preview)

        # 信息区（名称 + 类型标签 + 底部细条）
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(10, 8, 10, 6)
        info_layout.setSpacing(4)

        # 名称
        name_lbl = QLabel(asset.get("name", "-"))
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet("font-weight: 500; color: #1e293b; font-size: 12px;")
        info_layout.addWidget(name_lbl)

        # 类型 + 状态标签行（新增：增加可读性）
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        type_info = ASSET_TYPES.get(asset.get("type", "other"), {})
        type_lbl = QLabel(f"{type_info.get('icon', '?')} {type_info.get('label', '其他')}")
        type_lbl.setStyleSheet(f"font-size: 10px; color: {type_info.get('color', '#64748b')}; font-weight: 600;")
        meta_row.addWidget(type_lbl)

        status_info = STATUS_MAP.get(asset.get("status", "draft"), {"label": "草稿", "color": "#a0aec0"})
        status_lbl = QLabel(f"● {status_info['label']}")
        status_lbl.setStyleSheet(f"font-size: 10px; color: {status_info['color']};")
        meta_row.addWidget(status_lbl)
        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        info_layout.addStretch()

        # 底部细进度条（热度指示，参考工程底部蓝色细线）
        heat_bar = QProgressBar()
        heat_bar.setRange(0, 100)
        heat_bar.setValue(heat)
        heat_bar.setTextVisible(False)
        heat_bar.setFixedHeight(3)
        heat_bar.setStyleSheet(
            "QProgressBar { border: none; background: #e2e8f0; border-radius: 2px; }"
            "QProgressBar::chunk { background: #0ea5e9; border-radius: 2px; }"
        )
        info_layout.addWidget(heat_bar)

        layout.addWidget(info)

        # 鼠标事件：批量模式下点击切换选中，普通模式下单击选中
        card.mousePressEvent = lambda ev, _aid=aid: self._on_card_click(_aid)
        card.mouseDoubleClickEvent = lambda ev, _aid=aid: self._on_card_double_click(_aid)

        # 右键上下文菜单
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, _aid=aid: self._on_context_menu(_aid, pos)
        )

        return card

    def _on_context_menu(self, aid: str, pos):
        """卡片右键 → 发出上下文菜单信号"""
        # pos 是相对于 card 的坐标，转换为相对于 grid 的坐标
        card = self.sender()
        if card:
            global_pos = card.mapToParent(pos)
            self.card_context_menu.emit(aid, global_pos)
        else:
            self.card_context_menu.emit(aid, pos)

    def _on_card_click(self, aid: str):
        """卡片点击：批量模式下切换选中，普通模式下选中并联动详情"""
        if self._batch_mode:
            if aid in self._batch_selected:
                self._batch_selected.discard(aid)
            else:
                self._batch_selected.add(aid)
            self._refresh_grid()
            self.selection_changed.emit(self._batch_selected.copy())
        else:
            self._selected_id = aid
            self._refresh_grid()
            self.card_clicked.emit(aid)

    def _on_card_double_click(self, aid: str):
        self.card_double_clicked.emit(aid)

    def set_selected_id(self, aid: str):
        self._selected_id = aid
        self._refresh_grid()


# ============================================================
#  主模块：数字文化资产库
# ============================================================
class MatrixModule(BaseBusinessModule):
    """
    数字文化资产库主模块
    
    功能矩阵：
    ┌─────────────────────────────────────────────┐
    │ [统计卡片栏] 总量 | 存储 | 待审 | 已发布     │
    ├──────────┬──────────────────────────────────┤
    │ [筛选工具]│                                  │
    │ 搜索框    │     [资产列表表格]               │
    │ 类型筛选  │  编号 | 名称 | 类型 | 大小...  │
    │ 分类筛选  │                                  │
    │ 状态筛选  ├──────────────────────────────────┤
    │          │     [资产详情预览面板]            │
    │ [操作栏]  │     名称、类型、描述...          │
    │ 新增|批量删│                                │
    └──────────┴──────────────────────────────────┘
    
    交互特性：
    - 实时搜索防抖（300ms延迟）
    - 多条件组合过滤（AND逻辑）
    - 表格排序（点击表头）
    - 行选中联动详情面板
    - 双击行快速编辑
    - 右键上下文菜单（待扩展）
    """

    def __init__(self):
        # 注意：BaseBusinessModule.__init__() 内部会调用 setup_ui()
        # 因此所有实例属性必须在 super().__init__() 之前完成初始化
        self._search_timer = None       # 搜索防抖定时器
        self._current_filter = {
            "keyword": "",
            "type": "",
            "category": "",
            "status": "",
        }
        self._selected_ids = set()      # 当前选中的资产编号集合
        self._batch_mode = False        # 批量选择模式开关
        self._tag_cloud = None          # 标签云组件引用
        self._stats_labels = {}         # 统计条 label 引用
        self._batch_bar = None          # 批量操作工具条
        super().__init__()

    def cleanup(self):
        """模块卸载/热重载前停止可能存在的定时器，释放资源"""
        if self._search_timer is not None:
            try:
                self._search_timer.stop()
            except Exception:
                pass
            self._search_timer = None

    # ==================== UI 构建 ====================

    def setup_ui(self):
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 主分割器：左侧资产网格 + 右侧详情
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- 左侧区域 ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 12, 8, 12)
        left_layout.setSpacing(8)

        # 1) 紧凑统计条（总量 | 存储 | 待审 | 已发布）
        left_layout.addWidget(self._build_stats_bar())

        # 2) 顶部筛选行（筛选器 + 领域下拉 + 状态下拉 + 搜索 + 资源接入 + 导入/导出）
        left_layout.addWidget(self._build_filter_toolbar())

        # 3) 批量操作工具条（默认隐藏，进入批量模式时显示）
        self._batch_bar = self._build_batch_bar()
        self._batch_bar.setVisible(False)
        left_layout.addWidget(self._batch_bar)

        # 4) 资产卡片网格视图（参考工程：2列紧凑布局）
        self.card_grid = AssetCardGrid()
        self.card_grid.card_clicked.connect(self._on_card_clicked)
        self.card_grid.card_double_clicked.connect(self._on_card_double_clicked)
        self.card_grid.selection_changed.connect(self._on_selection_changed)
        self.card_grid.card_context_menu.connect(self._on_card_context_menu)
        left_layout.addWidget(self.card_grid, 1)

        # 5) 标签云面板（底部紧凑条，点击标签快速筛选）
        self._tag_cloud = TagCloudWidget()
        self._tag_cloud.tag_clicked.connect(self._on_tag_clicked)
        self._tag_cloud.setMinimumHeight(48)
        left_layout.addWidget(self._tag_cloud)

        splitter.addWidget(left_panel)

        # ---- 右侧详情面板 ----
        self.detail_panel = AssetDetailPanel()
        self.detail_panel.edit_requested.connect(self._open_edit_dialog)
        self.detail_panel.sync_requested.connect(self._sync_asset_to_db)
        self.detail_panel.purge_requested.connect(self._purge_asset)
        self.detail_panel.similar_asset_clicked.connect(self._on_similar_asset_clicked)
        splitter.addWidget(self.detail_panel)

        # 设置分割比例（左 : 右 = 58% : 42%）
        splitter.setSizes([650, 450])

        self.layout.addWidget(splitter)

        # 初始加载数据
        self.refresh_all_data()

    # ---------- 紧凑统计条 ----------

    def _build_stats_bar(self):
        """构建顶部紧凑统计条：总量 | 总存储 | 待审 | 已发布（4格横排）"""
        bar = QFrame()
        bar.setObjectName("ModulePanel")
        bar.setStyleSheet(
            "QFrame#ModulePanel { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 8, 16, 8)
        row.setSpacing(0)

        metrics = [
            ("total", "资产总量", "0", "#0ea5e9"),
            ("storage", "存储占用", "0 MB", "#805ad5"),
            ("pending", "待审核", "0", "#dd6b20"),
            ("published", "已发布", "0", "#38a169"),
        ]
        for key, label, default_val, color in metrics:
            cell = QVBoxLayout()
            cell.setSpacing(2)

            val_lbl = QLabel(default_val)
            val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color};")
            self._stats_labels[key] = val_lbl
            cell.addWidget(val_lbl)

            name_lbl = QLabel(label)
            name_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
            cell.addWidget(name_lbl)

            wrapper = QWidget()
            wrapper.setLayout(cell)
            row.addWidget(wrapper, 1)

            if key != "published":
                sep = QFrame()
                sep.setFixedWidth(1)
                sep.setStyleSheet("background: #e2e8f0;")
                row.addWidget(sep)

        return bar

    # ---------- 批量操作工具条 ----------

    def _build_batch_bar(self):
        """构建批量操作工具条：选中数提示 + 批量删除 + 批量导出 + 退出批量"""
        bar = QFrame()
        bar.setObjectName("BatchBar")
        bar.setStyleSheet(
            "QFrame#BatchBar { background: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px; }"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(10)

        self._batch_count_lbl = QLabel("已选中 0 项")
        self._batch_count_lbl.setStyleSheet("font-size: 12px; color: #92400e; font-weight: 600;")
        row.addWidget(self._batch_count_lbl)
        row.addStretch()

        btn_del = QPushButton("批量删除")
        btn_del.setObjectName("BtnDelete")
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet(
            "QPushButton { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 4px; font-size: 12px; padding: 0 10px; }"
            "QPushButton:hover { background: #fecaca; }"
        )
        btn_del.clicked.connect(self._batch_delete_selected)
        row.addWidget(btn_del)

        btn_export = QPushButton("导出选中")
        btn_export.setFixedHeight(28)
        btn_export.setStyleSheet(
            "QPushButton { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; border-radius: 4px; font-size: 12px; padding: 0 10px; }"
            "QPushButton:hover { background: #bfdbfe; }"
        )
        btn_export.clicked.connect(self._export_current_list)
        row.addWidget(btn_export)

        btn_exit = QPushButton("退出批量")
        btn_exit.setFixedHeight(28)
        btn_exit.setStyleSheet(
            "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 12px; padding: 0 10px; }"
            "QPushButton:hover { background: #e2e8f0; }"
        )
        btn_exit.clicked.connect(self._exit_batch_mode)
        row.addWidget(btn_exit)

        return bar

    # ---------- 筛选工具栏 ----------

    def _build_filter_toolbar(self):
        """构建参考工程风格的顶部筛选行：筛选器标签 + 领域下拉 + 状态下拉 + 搜索框 + 资源接入/导入/导出"""
        toolbar = QFrame()
        toolbar.setObjectName("ModulePanel")
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(8)

        # 筛选器标签（参考工程："筛选器:"）
        dim_label = QLabel("筛选器:")
        dim_label.setStyleSheet("font-size: 13px; color: #334155; font-weight: 600;")
        row.addWidget(dim_label)

        # 领域下拉（参考工程："全部资产领域 ▼"）
        self.filter_dimension = QComboBox()
        self.filter_dimension.setMinimumHeight(32)
        self.filter_dimension.setMinimumWidth(130)
        self.filter_dimension.addItem("全部资产领域", userData="all")
        for cat in getattr(self, "_category_options", []):
            if cat:
                self.filter_dimension.addItem(cat, userData=cat)
        self.filter_dimension.currentIndexChanged.connect(self._on_filter_changed)
        row.addWidget(self.filter_dimension)

        # 状态下拉（新增：全部状态 / 草稿 / 审核中 / 已通过 / 已发布 / 已归档）
        self.filter_status = QComboBox()
        self.filter_status.setMinimumHeight(32)
        self.filter_status.setMinimumWidth(100)
        self.filter_status.addItem("全部状态", userData="")
        for key, val in STATUS_MAP.items():
            self.filter_status.addItem(val["label"], userData=key)
        self.filter_status.currentIndexChanged.connect(self._on_filter_changed)
        row.addWidget(self.filter_status)

        # 搜索框（参考工程：宽搜索输入）
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("轻量资产唯一识别码或语义名称...")
        self.search_input.setMinimumHeight(32)
        self.search_input.textChanged.connect(self._on_search_changed)
        row.addWidget(self.search_input, 1)

        # 批量模式切换按钮（新增）
        self.btn_batch_mode = QPushButton("批量")
        self.btn_batch_mode.setFixedHeight(32)
        self.btn_batch_mode.setFixedWidth(48)
        self.btn_batch_mode.setCheckable(True)
        self.btn_batch_mode.setStyleSheet(
            "QPushButton { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; font-weight: 600; }"
            "QPushButton:checked { background: #fef3c7; color: #92400e; border-color: #fcd34d; }"
            "QPushButton:hover { background: #e2e8f0; }"
        )
        self.btn_batch_mode.clicked.connect(self._toggle_batch_mode)
        row.addWidget(self.btn_batch_mode)

        # 重置筛选按钮（接入 _reset_filters 死代码）
        btn_reset = QPushButton("重置")
        btn_reset.setFixedHeight(32)
        btn_reset.setFixedWidth(48)
        btn_reset.setStyleSheet(
            "QPushButton { background: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background: #e2e8f0; }"
        )
        btn_reset.clicked.connect(self._reset_filters)
        row.addWidget(btn_reset)

        # 批量导入按钮（接入 _import_assets_from_json 死代码）
        btn_import = QPushButton("导入")
        btn_import.setFixedHeight(32)
        btn_import.setFixedWidth(48)
        btn_import.setStyleSheet(
            "QPushButton { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background: #dcfce7; }"
        )
        btn_import.clicked.connect(self._import_assets_from_json)
        row.addWidget(btn_import)

        # 导出清单按钮（接入 _export_current_list 死代码）
        btn_export = QPushButton("导出")
        btn_export.setFixedHeight(32)
        btn_export.setFixedWidth(48)
        btn_export.setStyleSheet(
            "QPushButton { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background: #dbeafe; }"
        )
        btn_export.clicked.connect(self._export_current_list)
        row.addWidget(btn_export)

        # 资源接入按钮（参考工程：右侧"+ 资源接入"蓝色按钮）
        btn_add_new = QPushButton("+ 资源接入")
        btn_add_new.setObjectName("BtnCreate")
        btn_add_new.setFixedHeight(34)
        btn_add_new.setMinimumWidth(90)
        btn_add_new.clicked.connect(self._open_create_dialog)
        row.addWidget(btn_add_new)

        return toolbar

    def _on_card_clicked(self, aid: str):
        """卡片网格单击选中，联动详情面板"""
        self._selected_ids = {aid}
        self.card_grid.set_selected_id(aid)
        asset = db.get_asset_by_id(aid)
        self.detail_panel.show_asset(asset)

    def _on_card_double_clicked(self, aid: str):
        """卡片网格双击打开编辑"""
        asset = db.get_asset_by_id(aid)
        if asset:
            self._open_edit_dialog(asset)

    # ==================== 数据刷新逻辑 ====================

    def refresh_all_data(self):
        """全量刷新：分类选项 + 统计条 + 卡片网格 + 标签云"""
        self._refresh_category_options()
        self._refresh_card_data()
        self._refresh_stats()
        self._refresh_tag_cloud()

    def _refresh_stats(self):
        """刷新顶部紧凑统计条数据"""
        stats = db.get_asset_statistics()
        if "total" in self._stats_labels:
            self._stats_labels["total"].setText(str(stats.get("total", 0)))
        total_mb = stats.get("total_size_mb", 0)
        if "storage" in self._stats_labels:
            self._stats_labels["storage"].setText(_format_size(total_mb))
        # 统计待审核和已发布数量
        all_assets = db.read_all_assets()
        pending = sum(1 for a in all_assets if a.get("status") in ("draft", "reviewing"))
        published = sum(1 for a in all_assets if a.get("status") == "published")
        if "pending" in self._stats_labels:
            self._stats_labels["pending"].setText(str(pending))
        if "published" in self._stats_labels:
            self._stats_labels["published"].setText(str(published))

    def _refresh_tag_cloud(self):
        """刷新标签云：统计所有资产的标签频次"""
        all_assets = db.read_all_assets()
        tag_counts = {}
        for asset in all_assets:
            for tag in asset.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        # 按频次降序取前 15 个
        sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:15]
        if self._tag_cloud:
            self._tag_cloud.set_tags(sorted_tags)

    def _refresh_category_options(self):
        """刷新分类下拉框的选项列表（去重）"""
        stats = db.get_asset_statistics()
        self._category_options = [""] + stats["categories"]
        # 同步更新领域下拉选项
        self.filter_dimension.blockSignals(True)
        current = self.filter_dimension.currentText()
        self.filter_dimension.clear()
        self.filter_dimension.addItem("全部资产领域", userData="all")
        for cat in getattr(self, "_category_options", []):
            if cat:
                self.filter_dimension.addItem(cat, userData=cat)
        restore_idx = self.filter_dimension.findText(current)
        if restore_idx >= 0:
            self.filter_dimension.setCurrentIndex(restore_idx)
        self.filter_dimension.blockSignals(False)
    def _refresh_card_data(self):
        """根据当前筛选条件查询并填充卡片网格"""
        results = db.search_assets(
            keyword=self._current_filter["keyword"],
            asset_type=self._current_filter["type"],
            category=self._current_filter["category"],
            status=self._current_filter["status"],
        )

        self.card_grid.set_assets(results)
        self.card_grid.set_selected_id(None)

        # 清空选中状态
        self._selected_ids.clear()
        self.detail_panel.show_asset(None)

    # ==================== 事件处理 ====================

    def _on_search_changed(self, text):
        """搜索框文字变化时触发防抖搜索"""
        if self._search_timer:
            self._search_timer.stop()
        self._search_timer = QTimer.singleShot(300, self._apply_search)

    def _apply_search(self):
        """执行实际搜索并刷新卡片"""
        self._current_filter["keyword"] = self.search_input.text().strip()
        self._refresh_card_data()

    def _on_filter_changed(self):
        """筛选条件变化时触发（领域下拉 + 状态下拉）"""
        dim_val = self.filter_dimension.currentData() or ""
        status_val = self.filter_status.currentData() or ""
        self._current_filter = {
            "keyword": self.search_input.text().strip(),
            "type": "",
            "category": str(dim_val) if dim_val and dim_val != "all" else "",
            "status": str(status_val) if status_val else "",
        }
        self._refresh_card_data()

    def _on_tag_clicked(self, tag: str):
        """标签云点击 → 将标签填入搜索框触发筛选"""
        self.search_input.setText(tag)
        self._current_filter["keyword"] = tag
        self._refresh_card_data()

    def _on_selection_changed(self, selected_ids: set):
        """卡片网格选中状态变更（批量模式下）"""
        self._selected_ids = selected_ids
        if hasattr(self, "_batch_count_lbl"):
            self._batch_count_lbl.setText(f"已选中 {len(selected_ids)} 项")

    def _on_card_context_menu(self, aid: str, pos):
        """卡片右键上下文菜单：编辑 / 查看相似 / 导出 / 删除"""
        asset = db.get_asset_by_id(aid)
        if not asset:
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 24px; border-radius: 4px; font-size: 13px; }"
            "QMenu::item:selected { background: #f1f5f9; }"
        )

        act_edit = menu.addAction("✎  编辑资产")
        menu.addSeparator()
        act_similar = menu.addAction("◆  查看相似资产")
        act_export = menu.addAction("↧  导出此资产")
        menu.addSeparator()
        act_delete = menu.addAction("✕  永久抹除")

        action = menu.exec(self.card_grid.mapToGlobal(pos))
        if action == act_edit:
            self._open_edit_dialog(asset)
        elif action == act_similar:
            self.detail_panel.show_asset(asset)
            self.detail_panel.switch_to_similar_tab()
        elif action == act_export:
            self._export_single_asset(asset)
        elif action == act_delete:
            self._purge_asset(asset)

    def _on_similar_asset_clicked(self, aid: str):
        """详情面板相似资产推荐 → 点击跳转"""
        asset = db.get_asset_by_id(aid)
        if asset:
            self._on_card_clicked(aid)

    def _export_single_asset(self, asset: dict):
        """导出单个资产信息"""
        lines = ["=" * 55]
        lines.append(" 资产详情导出 ")
        lines.append(f" 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("-" * 55)
        lines.append(f" 编号:   {asset.get('id', '-')}")
        lines.append(f" 名称:   {asset.get('name', '-')}")
        lines.append(f" 类型:   {_get_type_label(asset.get('type', 'other'))}")
        lines.append(f" 分类:   {asset.get('category', '-')}")
        lines.append(f" 状态:   {_get_status_badge(asset.get('status', 'draft'))}")
        lines.append(f" 大小:   {_format_size(asset.get('size_mb', 0))}")
        lines.append(f" 标签:   {', '.join(asset.get('tags', []))}")
        lines.append(f" 路径:   {asset.get('path', '-')}")
        lines.append(f" 描述:   {asset.get('description', '-')}")
        lines.append(f" 创建:   {_format_timestamp(asset.get('created_at'))}")
        lines.append(f" 更新:   {_format_timestamp(asset.get('updated_at'))}")
        lines.append(f" 热度:   {_calc_asset_heat(asset)} / 100")
        lines.append("=" * 55)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"导出预览 - {asset.get('name', '')}")
        dlg.setFixedSize(500, 420)
        dlg_layout = QVBoxLayout(dlg)
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setFont(QFont("Consolas", 10))
        text_area.setText("\n".join(lines))
        dlg_layout.addWidget(text_area)
        btn = QPushButton("关闭")
        btn.setFixedWidth(80)
        btn.clicked.connect(dlg.close)
        dlg_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        dlg.exec()

    # ---------- 批量模式 ----------

    def _toggle_batch_mode(self):
        """切换批量选择模式"""
        self._batch_mode = self.btn_batch_mode.isChecked()
        self.card_grid.set_batch_mode(self._batch_mode)
        self._batch_bar.setVisible(self._batch_mode)
        if not self._batch_mode:
            self._selected_ids.clear()
            if hasattr(self, "_batch_count_lbl"):
                self._batch_count_lbl.setText("已选中 0 项")

    def _exit_batch_mode(self):
        """退出批量模式"""
        self.btn_batch_mode.setChecked(False)
        self._toggle_batch_mode()

    def _reset_filters(self):
        """重置所有筛选条件为初始状态"""
        self.search_input.clear()
        self.filter_dimension.setCurrentIndex(0)
        self._current_filter = {
            "keyword": "", "type": "",
            "category": "", "status": "",
        }
        self._refresh_card_data()

    # ==================== CRUD 操作 ====================

    def _open_create_dialog(self):
        """打开新增资产对话框"""
        stats = db.get_asset_statistics()
        dlg = AssetEditDialog(
            parent=self,
            asset_data=None,
            categories=stats["categories"],
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_form_data()
            aid = db.create_asset(data)
            self.refresh_all_data()
            self._show_toast(f"资产已创建: {aid}")

    def _open_edit_dialog(self, asset: dict):
        """打开编辑资产对话框"""
        stats = db.get_asset_statistics()
        dlg = AssetEditDialog(
            parent=self,
            asset_data=asset,
            categories=stats["categories"],
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_data = dlg.get_form_data()
            ok = db.update_asset(asset["id"], new_data)
            if ok:
                self.refresh_all_data()
                self._show_toast(f"资产已更新: {asset['id']}")
            else:
                QMessageBox.warning(
                    self, "更新失败",
                    f"无法找到资产 {asset['id']}，可能已被删除。"
                )

    def _batch_delete_selected(self):
        """批量删除选中的资产（需二次确认）"""
        count = len(self._selected_ids)
        if count == 0:
            return

        reply = QMessageBox.question(
            self, "确认批量删除",
            f"确定要删除选中的 {count} 个资产吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted = db.delete_assets_batch(list(self._selected_ids))
        self.refresh_all_data()
        self._show_toast(f"已成功删除 {deleted} 个资产")

    def _sync_asset_to_db(self, new_data: dict):
        """
        「提交更改并同步至数据库」。
        先把右侧面板编辑后的数据更新到内存数据库，再模拟远程同步。
        """
        aid = new_data.get("id")
        if not aid:
            return

        # 更新本地数据
        update_payload = {
            "name": new_data.get("name"),
            "category": new_data.get("category"),
            "status": new_data.get("status"),
            "tags": new_data.get("tags", []),
            "path": new_data.get("path"),
            "description": new_data.get("description"),
        }
        db.update_asset(aid, update_payload)

        self._show_toast(f"正在同步资产 {aid} 到数据库...")
        # 模拟远程同步延迟
        QTimer.singleShot(600, lambda: self._do_sync_finish(aid))

    def _do_sync_finish(self, aid: str):
        """同步完成后的回调"""
        asset = db.get_asset_by_id(aid)
        if asset:
            asset["last_sync_at"] = datetime.now().isoformat()
            self.refresh_all_data()
            if aid in self._selected_ids:
                self.detail_panel.show_asset(asset)
            self._show_toast(f"资产 {aid} 已同步至数据库")

    def _purge_asset(self, asset: dict):
        """永久抹除单个资产（不可恢复，需二次确认）"""
        aid = asset.get("id")
        reply = QMessageBox.warning(
            self, "永久抹除资源",
            f"确定要永久抹除资产「{asset.get('name', aid)}」吗？\n"
            "此操作会立即从数据库中移除该资源，且不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok = db.delete_asset(aid)
        if ok:
            self._selected_ids.discard(aid)
            self.refresh_all_data()
            self._show_toast(f"资产 {aid} 已永久抹除")
        else:
            QMessageBox.warning(
                self, "抹除失败",
                f"无法找到资产 {aid}，可能已被删除。"
            )

    def _export_current_list(self):
        """导出当前筛选结果的摘要信息（模拟导出）"""
        results = db.search_assets(
            keyword=self._current_filter["keyword"],
            asset_type=self._current_filter["type"],
            category=self._current_filter["category"],
            status=self._current_filter["status"],
        )

        if not results:
            QMessageBox.information(
                self, "导出提示", "当前列表无数据可导出。"
            )
            return

        # 生成模拟导出文本
        lines = ["=" * 55]
        lines.append(" 资产库导出报告 ")
        lines.append(f" 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f" 筛选条件: 关键词={self._current_filter['keyword']!r} "
                     f"| 类型={self._current_filter['type']!r} "
                     f"| 分类={self._current_filter['category']!r} "
                     f"| 状态={self._current_filter['status']!r}")
        lines.append(f" 共 {len(results)} 条记录")
        lines.append("-" * 55)
        for a in results:
            lines.append(
                f" [{a['id']}] {a['name']:<30s} "
                f"{_get_type_label(a['type']):<8s} "
                f"{_format_size(a['size_mb']):>10s} "
                f"{_get_status_badge(a['status'])}"
            )
        lines.append("=" * 55)

        # 显示在对话框中模拟导出效果
        export_dlg = QDialog(self)
        export_dlg.setWindowTitle("导出预览")
        export_dlg.setFixedSize(600, 420)
        layout = QVBoxLayout(export_dlg)

        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setFont(QFont("Consolas", 10))
        text_area.setText("\n".join(lines))
        layout.addWidget(text_area)

        btn_close = QPushButton("关闭")
        btn_close.setObjectName("BtnUpdate")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(export_dlg.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        export_dlg.exec()
        self._show_toast(f"已导出 {len(results)} 条资产记录")

    def _import_assets_from_json(self):
        """
        批量导入资产（模拟从 JSON 文本导入）。
        实际项目中可替换为 QFileDialog 选择本地 JSON/CSV。
        """
        import_dlg = QDialog(self)
        import_dlg.setWindowTitle("批量导入资产")
        import_dlg.setFixedSize(560, 420)
        layout = QVBoxLayout(import_dlg)

        hint = QLabel(
            "请在下方粘贴 JSON 数组，每条资产至少包含 name、type、size_mb 字段。\n"
            "示例：[{\"name\":\"新资产\",\"type\":\"image\",\"size_mb\":12.5}]"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(hint)

        text_area = QTextEdit()
        text_area.setFont(QFont("Consolas", 10))
        layout.addWidget(text_area, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_confirm = QPushButton("确认导入")
        btn_confirm.setObjectName("BtnCreate")
        btn_confirm.setFixedHeight(34)
        def do_import():
            raw = text_area.toPlainText().strip()
            if not raw:
                return
            try:
                data_list = json.loads(raw)
                if not isinstance(data_list, list):
                    raise ValueError("导入内容必须是 JSON 数组")
                created = 0
                for item in data_list:
                    if not isinstance(item, dict) or "name" not in item:
                        continue
                    # 补全默认值
                    payload = {
                        "name": item.get("name", "未命名资产"),
                        "type": item.get("type", "other"),
                        "category": item.get("category", "未分类"),
                        "size_mb": float(item.get("size_mb", 0)),
                        "status": item.get("status", "draft"),
                        "tags": item.get("tags", []),
                        "description": item.get("description", ""),
                        "path": item.get("path", ""),
                    }
                    db.create_asset(payload)
                    created += 1
                self.refresh_all_data()
                self._show_toast(f"成功导入 {created} 个资产")
                import_dlg.close()
            except Exception as e:
                QMessageBox.warning(import_dlg, "导入失败", f"JSON 解析错误：{e}")

        btn_confirm.clicked.connect(do_import)
        btn_layout.addWidget(btn_confirm)

        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("BtnUpdate")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(import_dlg.close)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)
        import_dlg.exec()

    @staticmethod
    def _show_toast(message: str):
        """显示轻量级操作成功提示（使用QMessageBox模拟Toast）"""
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("操作反馈")
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

