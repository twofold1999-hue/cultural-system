import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(BASE_DIR, "views", "modules")

# 菜单注册表：严格对应目标界面菜单顺序与名称
MENU_REGISTRY = {
    "dashboard":      {"class": "DashboardModule", "title": "控制面板"},
    "m1_planning":    {"class": "PlanningModule",  "title": "内容策划"},
    "m2_matrix":      {"class": "MatrixModule",    "title": "资产库"},
    "m3_workflow":    {"class": "WorkflowModule",  "title": "流程审批"},
    "m4_distribute":  {"class": "DistributeModule", "title": "发布渠道"},
    "m7_assets":      {"class": "AssetsModule",    "title": "排期计划"},
    "m5_analytics":   {"class": "AnalyticsModule", "title": "数据透视"},
    "m6_copyright":   {"class": "CopyrightModule", "title": "版权卫士"},
    "m8_monetization":{"class": "MonetizationModule", "title": "反馈管理"},
}
