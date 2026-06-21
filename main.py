import sys
import os
import inspect
import traceback
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QLoggingCategory
from views.login_view import LoginWindow
from views.dialogs import CustomTechDialog
from core.theme_manager import ThemeVisualEngine


# ============================================================
#  全局崩溃捕获：把事件循环中的未处理异常写入 crash.log
#  nativeEvent / timer slot 等处的异常不会被 try/except 捕获，
#  必须通过 sys.excepthook 兜底，否则进程直接退出看不到错误
# ============================================================
_CRASH_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")

def _crash_excepthook(exc_type, exc_value, exc_tb):
    """全局异常钩子：写入 crash.log 并打印到控制台"""
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    try:
        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n{tb_text}\n")
    except Exception:
        pass
    print(f"\n[CRASH] {tb_text}")
    # 调用原始钩子
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _crash_excepthook


class _StderrFilter:
    """过滤 libpng iCCP 警告，避免终端/控制台刷屏，不影响其他错误输出。"""

    def __init__(self, stream):
        self._stream = stream

    def write(self, message):
        if "libpng warning: iCCP" not in message:
            self._stream.write(message)

    def flush(self):
        self._stream.flush()

    def __getattr__(self, name):
        return getattr(self._stream, name)


class ApplicationController:
    """
    全系统生命周期核心网关控制器
    """
    def __init__(self):
        self.login_window = None
        self.main_window = None

    def start(self):
        self.login_window = LoginWindow()
        self.login_window.auth_success.connect(self.enter_main_workspace)
        self.login_window.show()

    def enter_main_workspace(self, username, role):
        print(f"[GATEWAY] RUNTIME_GRANTED -> USER: {username} | ROLE: {role}")
        
        dlg = CustomTechDialog(
            self.login_window,
            "网关路由已通过",
            f"安全令牌核验放行！\n工作空间节点初始化完成。\n操作员席位: {username}"
        )
        
        if dlg.exec():
            target_class = None
            try:
                import views.main_window as mw
                if hasattr(mw, 'MasterControlWindow'):
                    target_class = mw.MasterControlWindow
                else:
                    classes = [cls for name, cls in inspect.getmembers(mw, inspect.isclass) if cls.__module__ == mw.__name__]
                    if classes: target_class = classes[0]
            except Exception as e:
                print(f"❌ 导入失败: {e}")

            if target_class:
                try:
                    print("[BOOT] 正在创建主控台窗口...")
                    self.main_window = target_class(username, role)
                    print("[BOOT] 主控台窗口实例化完成，准备显示...")
                    self.main_window.show()
                    print("[BOOT] 主控台窗口已显示，关闭登录窗口...")
                    self.login_window.close()
                    print("[BOOT] 启动流程完成。")
                except Exception as e:
                    print(f"❌ 实例化主界面失败: {e}")
                    traceback.print_exc()
                    # 同时写入 crash.log
                    try:
                        with open(_CRASH_LOG, "a", encoding="utf-8") as f:
                            f.write(f"\n[实例化失败] {traceback.format_exc()}\n")
                    except Exception:
                        pass

if __name__ == "__main__":
    # 在最早阶段过滤 libpng iCCP 刷屏警告（来自 Qt 自带图标资源，不影响功能）
    sys.stderr = _StderrFilter(sys.stderr)

    # 高分屏优化
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    # 屏蔽 Qt 内部 png / imageio 警告
    os.environ["QT_LOGGING_RULES"] = "qt.png.warning=false;qt.gui.imageio.warning=false"

    app = QApplication(sys.argv)

    # 再次通过 QLoggingCategory 确保 Qt 日志规则生效
    QLoggingCategory.setFilterRules("qt.png.warning=false\nqt.gui.imageio.warning=false")

    # 注入全局 QSS 视觉资产
    ThemeVisualEngine.apply_global_theme(app)

    # 启动控制中心
    controller = ApplicationController()
    controller.start()

    sys.exit(app.exec())