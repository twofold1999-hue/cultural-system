import glob
import os
import sys

from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QListWidget,
                             QStackedWidget, QPushButton, QVBoxLayout, QLabel, QFrame,
                             QScrollArea, QSizePolicy, QMessageBox, QSizeGrip)
from PyQt6.QtCore import Qt, QTimer, QFileSystemWatcher, QRect
from config import MENU_REGISTRY
from core.engine import RuntimeModuleEngine
from core.theme_manager import ThemeVisualEngine
from database.mock_db import db


# Windows 命中测试（hit-test）常量，用于无边框窗口的边缘拖拽缩放
# 仅在 Windows 平台生效；其他平台通过窗口管理器默认行为处理
# 注意：ctypes / wintypes 采用懒加载（在 nativeEvent 内部 import），
# 避免顶层 import 失败导致整个 main_window 模块不可用，
# 也避免在非 Windows 平台加载不必要的 Windows 专用模块。
WM_NCHITTEST = 0x0084
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17
# 边缘可拖拽缩放的热区宽度（像素）
_RESIZE_MARGIN = 6


class MasterControlWindow(QMainWindow):

    def __init__(self, username, role):
        super().__init__()
        self._drag_position = None
        self.setObjectName("MainWindow")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(1440, 900)
        # 允许手动缩放，但限制最小尺寸避免内容被挤压变形
        self.setMinimumSize(1200, 720)

        # ====== 边缘八方向缩放状态（纯 Python 实现，不碰 nativeEvent）======
        # 参考：https://blog.csdn.net/qq_48719062/article/details/147549468
        # 原理：setMouseTracking + mouseMoveEvent 判断边缘热区 + setGeometry 手动调整
        # 完全绕开 nativeEvent，避免 PyQt6 下重写 nativeEvent 的段错误问题
        self._resize_border_width = 7  # 边缘热区宽度（像素）
        self._resize_start = None      # 缩放起始状态 {pos, geometry}
        self._is_resizing = False      # 是否正在缩放
        self._resize_direction = (False, False, False, False)  # (top, bottom, left, right)
        # 启用鼠标跟踪，使鼠标未按下时也能触发 mouseMoveEvent（用于切换光标形状）
        self.setMouseTracking(True)

        # 主容器
        self.main_widget = QWidget()
        self.main_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.main_widget)

        self.core_layout = QHBoxLayout(self.main_widget)
        self.core_layout.setContentsMargins(0, 0, 0, 0)
        self.core_layout.setSpacing(0)

        # ========== 左侧边栏 ==========
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setObjectName("Sidebar")
        self.sidebar_widget.setFixedWidth(200)
        sidebar_outer_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_outer_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_outer_layout.setSpacing(0)

        # Logo 区域（固定顶部，不滚动）
        self.logo_label = QLabel("矩阵引擎")
        self.logo_label.setObjectName("SidebarLogo")
        sidebar_outer_layout.addWidget(self.logo_label)

        # 可滚动区域：包含菜单 + 重载按钮
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setObjectName("SidebarScroll")
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_content.setObjectName("SidebarScrollContent")
        scroll_content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sidebar_layout = QVBoxLayout(scroll_content)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        # 菜单列表
        self.menu_list = QListWidget()
        self.menu_list.setObjectName("MenuSidebar")
        for key, info in MENU_REGISTRY.items():
            self.menu_list.addItem(info["title"])
        self.sidebar_layout.addWidget(self.menu_list)

        # 底部重载按钮（紧跟菜单，不留大段空白）
        self.btn_hot_reload = QPushButton("重新加载模块")
        self.btn_hot_reload.setObjectName("PrimaryButton")
        self.btn_hot_reload.clicked.connect(self.trigger_current_reload)
        self.sidebar_layout.addSpacing(8)
        self.sidebar_layout.addWidget(self.btn_hot_reload)

        sidebar_scroll.setWidget(scroll_content)
        sidebar_scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        sidebar_outer_layout.addWidget(sidebar_scroll, 1)

        self.core_layout.addWidget(self.sidebar_widget)

        # ========== 右侧内容区 ==========
        content_container = QWidget()
        content_container.setObjectName("DashboardContainer")
        self.content_layout = QVBoxLayout(content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 标题栏（含页面标题 + 窗口控制按钮）
        title_bar = QFrame()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(24, 0, 8, 0)
        title_bar_layout.setSpacing(0)

        self.page_title = QLabel("系统概览")
        self.page_title.setObjectName("PageTitle")
        title_bar_layout.addWidget(self.page_title)

        title_bar_layout.addStretch()

        # 窗口控制按钮
        btn_min = QPushButton()
        btn_min.setObjectName("WinCtrlBtn")
        btn_min.setText("\u2014")
        btn_min.setFixedSize(44, 32)
        btn_min.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(btn_min)

        btn_max = QPushButton()
        btn_max.setObjectName("WinCtrlBtn")
        btn_max.setText("\u25A1")
        btn_max.setFixedSize(44, 32)
        btn_max.clicked.connect(self._toggle_maximize)
        title_bar_layout.addWidget(btn_max)

        btn_close = QPushButton()
        btn_close.setObjectName("WinCloseBtn")
        btn_close.setText("\u2715")
        btn_close.setFixedSize(44, 32)
        btn_close.clicked.connect(self.close)
        title_bar_layout.addWidget(btn_close)

        self.content_layout.addWidget(title_bar)

        # 页面内容区
        content_body = QWidget()
        content_body.setObjectName("DashboardContainer")
        self.body_layout = QVBoxLayout(content_body)
        self.body_layout.setContentsMargins(16, 12, 16, 12)
        self.body_layout.setSpacing(12)

        # 页面堆栈
        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName("ViewStack")
        self.body_layout.addWidget(self.view_stack, 1)

        # 右下角缩放手柄（QSizeGrip 是 Qt 原生组件，无崩溃风险）
        # 无边框窗口下用于手动调整窗口大小，替代有崩溃风险的 nativeEvent 方案
        # 注意：QSizeGrip 的父对象必须是它所在的 widget，不能是顶级窗口，
        # 否则在 show() 时会触发 C++ 层段错误
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        self._size_grip = QSizeGrip(content_body)
        self._size_grip.setFixedSize(16, 16)
        self._size_grip.setStyleSheet("QSizeGrip { background: transparent; }")
        grip_row.addWidget(self._size_grip)
        self.body_layout.addLayout(grip_row)

        self.content_layout.addWidget(content_body, 1)

        self.core_layout.addWidget(content_container, 1)

        # 首页：控制面板 Dashboard 立即加载
        self._loaded_modules = {"dashboard"}
        self.add_module_to_stack("dashboard")

        # 业务模块页面：先占槽，按需懒加载，降低启动内存占用
        for key in MENU_REGISTRY.keys():
            if key == "dashboard":
                continue
            placeholder = QLabel("加载中...")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #64748b; font-size: 14px;")
            self.view_stack.addWidget(placeholder)

        # 自动热重载：监听业务模块文件变化
        self._dirty_modules = set()
        self._module_watcher = QFileSystemWatcher(self)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._do_auto_reload)

        # 主题样式热重载：独立的防抖定时器，与业务模块重载解耦
        # 改 style.qss 时只重新 setStyleSheet，不重建控件树、不丢用户状态
        self._theme_reload_timer = QTimer(self)
        self._theme_reload_timer.setSingleShot(True)
        self._theme_reload_timer.timeout.connect(self._reload_theme_only)
        self._qss_path = ""  # 在 _setup_module_watcher 中赋值

        # 轮询兜底：QFileSystemWatcher 在某些编辑器/Windows 环境下可能漏报，
        # 用 mtime+size 轮询作为双保险
        self._module_file_stats = {}
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_module_changes)
        self._setup_module_watcher()

        self.menu_list.currentRowChanged.connect(self._on_page_changed)
        self._on_page_changed(0)  # 默认选中第一项

        ThemeVisualEngine.apply_theme(self)

    def add_module_to_stack(self, key):
        cls = RuntimeModuleEngine.reload_module(key)
        if cls:
            module_instance = cls()
            card = QFrame()
            card.setObjectName("DataCard")
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

            layout = QVBoxLayout(card)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(module_instance)
            self.view_stack.addWidget(card)
        else:
            self.view_stack.addWidget(QLabel("加载异常"))

    def _load_module_at_index(self, key: str, idx: int):
        """懒加载指定模块，替换对应索引的占位 QLabel"""
        if key in self._loaded_modules:
            return
        cls = RuntimeModuleEngine.reload_module(key)
        if not cls:
            return

        new_module = cls()
        new_card = QFrame()
        new_card.setObjectName("DataCard")
        new_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(new_card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(new_module)

        # 移除占位页并插入真实模块，保持索引稳定
        old_placeholder = self.view_stack.widget(idx)
        self.view_stack.insertWidget(idx, new_card)
        self.view_stack.removeWidget(old_placeholder)
        old_placeholder.deleteLater()
        self.view_stack.setCurrentIndex(idx)
        self._loaded_modules.add(key)

    def _on_page_changed(self, row):
        """菜单切换时同步更新标题和页面；未加载模块按需懒加载；若目标模块已脏则自动热重载"""
        titles = list(MENU_REGISTRY.values())
        if row < len(titles):
            self.page_title.setText(titles[row]["title"])

        key = list(MENU_REGISTRY.keys())[row]

        # 懒加载：占位 QLabel 时首次创建真实模块
        if key not in self._loaded_modules:
            self._load_module_at_index(key, row)
            # 刚加载的模块已是最新代码，清空脏标记避免无意义二次重载
            self._dirty_modules.discard(key)
        else:
            self.view_stack.setCurrentIndex(row)

        if key in self._dirty_modules:
            self._dirty_modules.discard(key)
            QTimer.singleShot(50, self.trigger_current_reload)

    def _setup_module_watcher(self):
        """监听 views/modules 下所有 .py 文件（含公共组件）+ style.qss，并启动轮询兜底"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        modules_dir = os.path.join(base_dir, "views", "modules")
        for path in glob.glob(os.path.join(modules_dir, "*.py")):
            self._module_watcher.addPath(path)
            self._module_file_stats[path] = self._get_file_stat(path)

        # 监听全局样式表 style.qss：改样式时走轻量主题重载路径，不重建窗口
        self._qss_path = os.path.join(base_dir, "style.qss")
        if os.path.exists(self._qss_path):
            self._module_watcher.addPath(self._qss_path)
            self._module_file_stats[self._qss_path] = self._get_file_stat(self._qss_path)

        self._module_watcher.fileChanged.connect(self._on_module_file_changed)
        self._poll_timer.start(300)  # 300ms 轮询一次

    @staticmethod
    def _get_file_stat(path: str) -> tuple:
        """返回文件的 (mtime, size)，用于检测是否发生变化"""
        try:
            st = os.stat(path)
            return (int(st.st_mtime * 1000), st.st_size)
        except Exception:
            return (0, 0)

    def _poll_module_changes(self):
        """轮询检测文件变化，作为 QFileSystemWatcher 的兜底机制"""
        for path, old_stat in list(self._module_file_stats.items()):
            new_stat = self._get_file_stat(path)
            if new_stat != old_stat:
                self._module_file_stats[path] = new_stat
                # style.qss 走独立的主题重载路径，不触发业务模块重载
                if path == self._qss_path:
                    self._schedule_theme_reload()
                    continue
                key = os.path.basename(path)[:-3]
                if key in MENU_REGISTRY:
                    self._mark_module_dirty(key)
                else:
                    self._mark_all_modules_dirty()

    def _mark_module_dirty(self, key: str):
        """标记单个业务模块为脏并启动防抖重载"""
        self._dirty_modules.add(key)
        self._reload_timer.stop()
        self._reload_timer.start(400)

    def _mark_all_modules_dirty(self):
        """公共组件变化时，标记所有业务模块为脏并启动防抖重载"""
        for key in MENU_REGISTRY.keys():
            self._dirty_modules.add(key)
        self._reload_timer.stop()
        self._reload_timer.start(400)

    def _schedule_theme_reload(self):
        """调度一次轻量主题重载（防抖 300ms），与业务模块重载互不干扰"""
        self._theme_reload_timer.stop()
        self._theme_reload_timer.start(300)

    def _reload_theme_only(self):
        """
        轻量主题热重载：仅重新读取 style.qss 并 setStyleSheet。
        - 不重建控件树、不丢失用户状态（输入内容、滚动位置、选中项全部保留）
        - QSS 语法错误时不应用，保留旧样式并打印警告
        - 通过 unpolish/polish 触发子控件重绘，避免部分样式不刷新
        """
        if not self._qss_path or not os.path.exists(self._qss_path):
            return
        try:
            with open(self._qss_path, "r", encoding="utf-8") as f:
                new_qss = f.read()
            # 先校验非空，避免误删现有样式
            if not new_qss.strip():
                print("[Theme Reload] style.qss 内容为空，跳过应用以保留现有样式")
                return
            # 刷新 stat，避免轮询重复触发
            self._module_file_stats[self._qss_path] = self._get_file_stat(self._qss_path)
            # 重新应用样式：apply_theme 内部会 setStyleSheet
            ThemeVisualEngine.apply_theme(self)
            # 触发样式重绘：某些子控件设过独立样式后不响应全局刷新，需手动 polish
            from PyQt6.QtWidgets import QStyle
            style = self.style()
            style.unpolish(self)
            style.polish(self)
            print(f"[Theme Reload] 样式已热重载 ({len(new_qss)} bytes)")
        except Exception as e:
            # QSS 解析失败时 Qt 会打印警告但不抛异常；文件读取异常在此兜底
            # 绝不让异常逃逸到事件循环导致闪退，保留旧样式即可
            print(f"[Theme Reload] 样式热重载失败，保留现有样式: {e}")

    def _on_module_file_changed(self, path: str):
        """模块源文件变化时标记为脏，并启动防抖重载；style.qss 变化走独立主题重载路径"""
        # 某些编辑器会替换文件，导致 watcher 丢失监听，重新注册
        if path not in self._module_watcher.files():
            self._module_watcher.addPath(path)

        # style.qss 变化：只重新应用样式，不重建任何控件
        if path == self._qss_path:
            self._schedule_theme_reload()
            return

        key = os.path.basename(path)[:-3]
        if key in MENU_REGISTRY:
            self._mark_module_dirty(key)
        else:
            # 公共组件（如 common_widgets.py / base_module.py）变化时，
            # 所有业务模块都可能需要重载以获取最新组件
            self._mark_all_modules_dirty()

    def _do_auto_reload(self):
        """执行当前显示模块的热重载"""
        current_idx = self.menu_list.currentRow()
        if current_idx < 0:
            return
        current_key = list(MENU_REGISTRY.keys())[current_idx]
        if current_key in self._dirty_modules:
            self._dirty_modules.discard(current_key)
            self.trigger_current_reload()

    def trigger_current_reload(self):
        idx = self.menu_list.currentRow()
        if idx < 0:
            return
        key = list(MENU_REGISTRY.keys())[idx]
        try:
            cls = RuntimeModuleEngine.reload_module(key)
            if not cls:
                return

            # 先创建新模块实例，失败则保留旧页面，避免页面丢失/闪退
            new_module = cls()

            old_card = self.view_stack.widget(idx)

            # 安全清理旧模块实例：停止定时器、断开资源，再安排删除
            # 注意：不要手动 setParent(None)，让 old_card.deleteLater() 级联删除子模块，
            # 否则旧模块会从 C++ 父子链脱离，仅依赖 Python GC，容易造成内存堆积。
            if old_card is not None:
                if old_card.layout() and old_card.layout().count() > 0:
                    item = old_card.layout().itemAt(0)
                    if item and item.widget():
                        old_module = item.widget()
                        if hasattr(old_module, "cleanup"):
                            try:
                                old_module.cleanup()
                            except Exception:
                                pass
                self.view_stack.removeWidget(old_card)
                old_card.deleteLater()

            new_card = QFrame()
            new_card.setObjectName("DataCard")
            new_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            layout = QVBoxLayout(new_card)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(new_module)
            self.view_stack.insertWidget(idx, new_card)
            self.view_stack.setCurrentIndex(idx)

            # 重载成功后刷新该文件的 stat，避免轮询再次触发
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_dir, "views", "modules", f"{key}.py")
            if path in self._module_file_stats:
                self._module_file_stats[path] = self._get_file_stat(path)
        except Exception as e:
            # 热重载失败时不闪退，弹出错误并保留当前页面
            import traceback
            msg = (f"模块 {key} 重新加载时出错，程序不会退出。\n\n"
                   f"错误信息:\n{str(e)}\n\n"
                   f"详细堆栈:\n{traceback.format_exc()}")
            # 双重保护：即使弹窗本身出错，也绝不能让异常逃逸到 Qt 事件循环导致闪退
            try:
                QMessageBox.critical(self, f"热重载失败: {key}", msg)
            except Exception:
                print(f"[热重载失败] {key}: {e}\n{traceback.format_exc()}")

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # ============================================================
    #  鼠标事件：边缘八方向缩放 + 标题栏拖拽
    #
    #  优先级：边缘缩放 > 标题栏拖拽
    #  - 鼠标在窗口边缘 7px 热区内 → 缩放（改光标 + setGeometry）
    #  - 鼠标在标题栏区域（y <= 40）且不在边缘 → 窗口拖拽
    #  - 其他区域 → 不处理
    #
    #  纯 Python 实现，不碰 nativeEvent，避免 PyQt6 段错误
    # ============================================================

    def _is_in_resize_area(self, pos):
        """判断鼠标是否在窗口边缘缩放热区，返回 (top, bottom, left, right)"""
        rect = self.rect()
        bw = self._resize_border_width
        top = pos.y() < bw
        bottom = pos.y() > rect.height() - bw
        left = pos.x() < bw
        right = pos.x() > rect.width() - bw
        return top, bottom, left, right

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint()
        top, bottom, left, right = self._is_in_resize_area(pos)

        # 优先：鼠标在边缘热区 → 启动缩放
        if top or bottom or left or right:
            self._resize_start = {
                "pos": event.globalPosition().toPoint(),
                "geometry": self.geometry()
            }
            self._is_resizing = True
            self._resize_direction = (top, bottom, left, right)
            self._drag_position = None  # 取消拖拽
            event.accept()
            return

        # 其次：鼠标在标题栏区域（y <= 40）→ 窗口拖拽
        if pos.y() <= 40:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        # 正在缩放 → 执行缩放逻辑
        if self._is_resizing and self._resize_start:
            self._do_resize(event)
            return

        # 正在拖拽 → 执行拖拽逻辑
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return

        # 鼠标未按下 → 根据位置切换光标形状
        if event.buttons() == Qt.MouseButton.NoButton:
            pos = event.position().toPoint()
            top, bottom, left, right = self._is_in_resize_area(pos)

            if top and left:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif top and right:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif bottom and left:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif bottom and right:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif left or right:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif top or bottom:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        # 重置缩放和拖拽状态
        self._resize_start = None
        self._is_resizing = False
        self._resize_direction = (False, False, False, False)
        self._drag_position = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _do_resize(self, event):
        """执行窗口缩放，根据方向调整 geometry"""
        delta = event.globalPosition().toPoint() - self._resize_start["pos"]
        geo = self._resize_start["geometry"]
        top, bottom, left, right = self._resize_direction

        min_w = self.minimumSize().width()
        min_h = self.minimumSize().height()
        max_w = self.maximumSize().width()
        max_h = self.maximumSize().height()

        new_geo = QRect(geo)

        # 上边
        if top:
            new_top = geo.top() + delta.y()
            new_h = geo.height() - delta.y()
            if min_h <= new_h <= max_h:
                new_geo.setTop(new_top)
        # 下边
        if bottom:
            new_h = geo.height() + delta.y()
            if min_h <= new_h <= max_h:
                new_geo.setBottom(geo.bottom() + delta.y())
        # 左边
        if left:
            new_left = geo.left() + delta.x()
            new_w = geo.width() - delta.x()
            if min_w <= new_w <= max_w:
                new_geo.setLeft(new_left)
        # 右边
        if right:
            new_w = geo.width() + delta.x()
            if min_w <= new_w <= max_w:
                new_geo.setRight(geo.right() + delta.x())

        self.setGeometry(new_geo)

    # ============================================================
    #  注意：边缘缩放曾尝试用 nativeEvent 拦截 WM_NCHITTEST 实现，
    #  但在 PyQt6 中子类重写 nativeEvent（即使只调用 super）也会
    #  在 show() 阶段触发 C++ 段错误。因此彻底不重写 nativeEvent，
    #  改用 QSizeGrip（右下角缩放手柄）实现手动缩放。
    # ============================================================
