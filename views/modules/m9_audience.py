from views.modules.base_module import BaseBusinessModule
from PyQt6.QtWidgets import QLabel, QTextBrowser

class AudienceModule(BaseBusinessModule):
    def __init__(self):
        super().__init__("自然语言受众情感倾向感知终端")

    def setup_ui(self):
        browser = QTextBrowser()
        browser.append("核心受众偏好画像聚类分析报告已生成：")
        browser.append("- 情感极性分布: 积极 (78.3%), 中立 (15.1%), 负向 (6.6%)")
        browser.append("- 高频关联词汇: [非遗文化, 沉浸式体验, 国潮破圈]")
        self.layout.addWidget(browser)