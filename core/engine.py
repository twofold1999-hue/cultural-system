import importlib
import sys
from config import MENU_REGISTRY

class RuntimeModuleEngine:
    """
    动态模块加载与热更新核心引擎
    无需重启应用，通过清除 sys.modules 缓存迫使 Python 重新解析文件
    """

    # 模块依赖链：重载目标模块时，先重载其依赖可确保新代码生效
    MODULE_DEPENDENCIES = {
        "dashboard":   ["database.mock_db", "views.modules.base_module", "views.modules.common_widgets"],
        "m1_planning": ["database.mock_db", "views.modules.base_module"],
        "m2_matrix":   ["database.mock_db", "views.modules.base_module"],
        "m3_workflow": ["database.mock_db", "views.modules.base_module"],
        "m4_distribute": ["database.mock_db", "views.modules.base_module"],
        "m5_analytics": ["database.mock_db", "views.modules.base_module"],
        "m6_copyright": ["database.mock_db", "views.modules.base_module"],
        "m7_assets":   ["database.mock_db", "views.modules.base_module"],
    }

    @staticmethod
    def reload_module(module_key: str):
        if module_key not in MENU_REGISTRY:
            return None

        module_name = f"views.modules.{module_key}"
        class_name = MENU_REGISTRY[module_key]["class"]

        try:
            # 先重载依赖模块，保证目标模块能导入到最新代码
            for dep in RuntimeModuleEngine.MODULE_DEPENDENCIES.get(module_key, []):
                if dep in sys.modules:
                    importlib.reload(sys.modules[dep])

            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)

            mod = sys.modules[module_name]
            cls = getattr(mod, class_name)
            return cls
        except Exception as e:
            print(f"[Engine Error] 模块 {module_key} 热重载失败: {e}")
            return None
