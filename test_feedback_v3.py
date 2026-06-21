"""测试舆情反馈模块能否正常加载"""
import sys
from PyQt6.QtWidgets import QApplication
from views.modules.m8_monetization import MonetizationModule

app = QApplication(sys.argv)
mod = MonetizationModule()
print("模块创建成功")
print("反馈总数:", len(mod._feedbacks))
print("过滤后数量:", len(mod._filtered))
print("当前选中:", repr(mod._current_id))
print("表格行数:", mod.feedback_table.rowCount())
print("关键词标签数:", mod.keyword_flow.count() - 1)
print("测试通过")
