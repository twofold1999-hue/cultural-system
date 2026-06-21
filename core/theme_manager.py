import os

class ThemeVisualEngine:
    """
    自定义系统视觉工具 / 样式引擎管理器
    负责统一调度、读取外部 QSS 样式资产
    """
    
    @staticmethod
    def _get_qss_path(qss_file_name="style.qss"):
        """辅助方法：获取 QSS 的绝对路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, ".."))
        return os.path.join(project_root, qss_file_name)

    @staticmethod
    def apply_theme(widget, qss_file_name="style.qss"):
        """为指定的组件或窗口注入样式"""
        qss_path = ThemeVisualEngine._get_qss_path(qss_file_name)
        if not os.path.exists(qss_path):
            print(f"[Theme Engine Warning] 未检测到样式资产: {qss_path}")
            return False
            
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                widget.setStyleSheet(f.read())
            return True
        except Exception as e:
            print(f"[Theme Engine Error] 样式解析故障: {e}")
            return False

    @staticmethod
    def apply_global_theme(app, qss_file_name="style.qss"):
        """【新增】专门为 QApplication 全局应用样式"""
        qss_path = ThemeVisualEngine._get_qss_path(qss_file_name)
        if not os.path.exists(qss_path):
            print(f"[Theme Engine Warning] 未检测到全局样式资产: {qss_path}")
            return False
            
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            print(f"[Theme Engine] 全局 QSS 视觉资产已成功注入应用程序。")
            return True
        except Exception as e:
            print(f"[Theme Engine Error] 全局样式解析故障: {e}")
            return False