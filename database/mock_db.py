import uuid
import time


class MockDatabase:
    """
    内存数据库，模拟物理数据库的事务与 ACID 特性
    针对高交互特征，实现完整的增删改查(CRUD)底层
    """
    def __init__(self):
        self._users = {"admin": {"password": "admin123", "role": "Director"}}
        self._content_pool = {}
        self._asset_pool = {}  # 资产库数据存储
        self._init_sample_assets()

    def _init_sample_assets(self):
        """初始化示例资产数据，让界面开箱即有内容"""
        sample_data = [
            {"name": "故宫夜景延时摄影_4K.mp4", "type": "video", "category": "视频素材",
             "tags": ["故宫", "夜景", "延时"], "size_mb": 256.8,
             "status": "approved", "description": "北京故宫博物院夜间灯光延时摄影，4K分辨率",
             "path": "/assets/videos/gugong_night_4k.mp4"},
            {"name": "国潮插画-龙腾盛世.png", "type": "image", "category": "设计图稿",
             "tags": ["国潮", "插画", "龙"], "size_mb": 12.5,
             "status": "approved", "description": "中国传统龙纹元素与现代潮流结合的商业插画",
             "path": "/assets/images/dragon_chic.png"},
            {"name": "2026年度传播策略报告.pdf", "type": "document", "category": "文档资料",
             "tags": ["策略", "年度报告", "传播"], "size_mb": 3.2,
             "status": "published", "description": "包含全年文化传播策略规划及预算分配方案",
             "path": "/assets/docs/strategy_2026.pdf"},
            {"name": "敦煌飞天舞曲配乐.wav", "type": "audio", "category": "音频素材",
             "tags": ["敦煌", "音乐", "古风"], "size_mb": 45.6,
             "status": "draft", "description": "基于敦煌壁画灵感创作的电子古风背景音乐",
             "path": "/assets/audio/dunhuang_flying.wav"},
            {"name": "非遗传承人访谈录.mp4", "type": "video", "category": "视频素材",
             "tags": ["非遗", "访谈", "纪录片"], "size_mb": 512.0,
             "status": "reviewing", "description": "对三位国家级非遗传承人的深度访谈记录",
             "path": "/assets/videos/heritage_interview.mp4"},
            {"name": "春节IP形象设计套件.zip", "type": "document", "category": "设计图稿",
             "tags": ["春节", "IP", "品牌"], "size_mb": 88.9,
             "status": "approved", "description": "含主视觉、延展物料、表情包全套矢量源文件",
             "path": "/assets/design/spring_ip_kit.zip"},
            {"name": "江南水乡航拍全景.jpg", "type": "image", "category": "摄影图片",
             "tags": ["航拍", "水乡", "风景"], "size_mb": 18.3,
             "status": "published", "description": "苏州周庄古镇春季航拍高清全景照片",
             "path": "/assets/photos/jiangnan_aerial.jpg"},
            {"name": "博物馆数字化展厅导览音频.mp3", "type": "audio", "category": "音频素材",
             "tags": ["博物馆", "导览", "语音"], "size_mb": 22.1,
             "status": "approved", "description": "国家博物馆数字展厅多语言智能导览音频包",
             "path": "/assets/audio/museum_guide.mp3"},
            {"name": "丝绸之路VR体验素材包", "type": "document", "category": "三维资产",
             "tags": ["丝路", "VR", "3D"], "size_mb": 1024.5,
             "status": "archived", "description": "丝绸之路沿线12个文化节点的高精度3D扫描模型集",
             "path": "/assets/3d/silkroad_vr_pack.7z"},
            {"name": "茶道文化微纪录片片段.mov", "type": "video", "category": "视频素材",
             "tags": ["茶道", "纪录片", "文化"], "size_mb": 388.7,
             "status": "reviewing", "description": "中国茶道从采摘到冲泡全流程的微距拍摄素材",
             "path": "/assets/videos/tea_ceremony.mov"},
            {"name": "京剧脸谱矢量图标集.svg", "type": "image", "category": "设计图稿",
             "tags": ["京剧", "脸谱", "矢量"], "size_mb": 2.1,
             "status": "published", "description": "24款经典京剧脸谱的扁平化矢量图标，支持无损缩放",
             "path": "/assets/images/opera_masks.svg"},
            {"name": "民族乐器采样音色库", "type": "audio", "category": "音频素材",
             "tags": ["乐器", "采样", "音效"], "size_mb": 368.4,
             "status": "draft", "description": "古琴、琵琶、二胡等16种传统乐器的多力度采样音色",
             "path": "/assets/audio/instrument_samples.flac"},
        ]
        now = int(time.time())
        for i, item in enumerate(sample_data):
            aid = f"AST{i+1:04d}"
            item["id"] = aid
            item["created_at"] = now - (i * 3600)
            item["updated_at"] = now - (i * 1800)
            self._asset_pool[aid] = item

    # ========== 用户管理 ==========

    def authenticate(self, username, password):
        if username in self._users and self._users[username]["password"] == password:
            return True, self._users[username]["role"]
        return False, None

    def register_user(self, username, password, role="Editor"):
        if username in self._users:
            return False, "用户已存在"
        self._users[username] = {"password": password, "role": role}
        return True, "注册成功"

    # ========== 内容策划 CRUD ==========

    def create_content(self, data: dict) -> str:
        content_id = str(uuid.uuid4())[:8]
        data["id"] = content_id
        self._content_pool[content_id] = data
        return content_id

    def read_all_content(self) -> list:
        return list(self._content_pool.values())

    def update_content(self, content_id: str, new_data: dict) -> bool:
        if content_id in self._content_pool:
            self._content_pool[content_id].update(new_data)
            return True
        return False

    def delete_content(self, content_id: str) -> bool:
        if content_id in self._content_pool:
            del self._content_pool[content_id]
            return True
        return False

    # ========== 资产库 CRUD ==========

    def create_asset(self, data: dict) -> str:
        """创建新资产"""
        aid = f"AST{len(self._asset_pool)+1:04d}"
        data["id"] = aid
        data["created_at"] = int(time.time())
        data["updated_at"] = int(time.time())
        if "status" not in data:
            data["status"] = "draft"
        self._asset_pool[aid] = data
        return aid

    def read_all_assets(self) -> list:
        """读取全部资产列表"""
        return list(self._asset_pool.values())

    def get_asset_by_id(self, aid: str) -> dict | None:
        """按ID查询单个资产"""
        return self._asset_pool.get(aid)

    def update_asset(self, aid: str, data: dict) -> bool:
        """更新资产信息"""
        if aid in self._asset_pool:
            data["updated_at"] = int(time.time())
            self._asset_pool[aid].update(data)
            return True
        return False

    def delete_asset(self, aid: str) -> bool:
        """删除单个资产"""
        if aid in self._asset_pool:
            del self._asset_pool[aid]
            return True
        return False

    def delete_assets_batch(self, ids: list) -> int:
        """批量删除资产，返回成功删除数量"""
        count = 0
        for aid in ids:
            if aid in self._asset_pool:
                del self._asset_pool[aid]
                count += 1
        return count

    def search_assets(self, keyword: str = "", asset_type: str = "",
                      category: str = "", status: str = "") -> list:
        """
        多条件组合搜索资产
        支持关键词（名称/描述/标签）、类型、分类、状态筛选
        """
        results = []
        for asset in self._asset_pool.values():
            # 关键词匹配：名称、描述、标签
            if keyword:
                kw_lower = keyword.lower()
                name_match = kw_lower in asset.get("name", "").lower()
                desc_match = kw_lower in asset.get("description", "").lower()
                tag_match = any(kw_lower in t.lower() for t in asset.get("tags", []))
                if not (name_match or desc_match or tag_match):
                    continue
            # 类型过滤
            if asset_type and asset.get("type") != asset_type:
                continue
            # 分类过滤
            if category and asset.get("category") != category:
                continue
            # 状态过滤
            if status and asset.get("status") != status:
                continue
            results.append(asset)
        return results

    def get_asset_statistics(self) -> dict:
        """
        返回资产统计摘要：
        总数、各类型计数、各状态计数、总存储大小(MB)、分类列表、标签云
        """
        total = len(self._asset_pool)
        total_size = sum(a.get("size_mb", 0) for a in self._asset_pool.values())
        type_counts = {}
        status_counts = {}
        categories = set()
        all_tags = {}

        for a in self._asset_pool.values():
            t = a.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
            s = a.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
            categories.add(a.get("category", ""))
            for tag in a.get("tags", []):
                all_tags[tag] = all_tags.get(tag, 0) + 1

        return {
            "total": total,
            "total_size_mb": round(total_size, 1),
            "by_type": type_counts,
            "by_status": status_counts,
            "categories": sorted(categories),
            "tag_cloud": sorted(all_tags.items(), key=lambda x: -x[1]),
        }

    # ========== 内容策划数据 ==========

    def __init__(self):
        self._users = {"admin": {"password": "admin123", "role": "Director"}}
        self._content_pool = {}
        self._asset_pool = {}  # 资产库数据存储
        self._planning_pool = {}  # 策划案数据
        self._engine_runtime_hours = 724.0  # 引擎运行时长
        self._node_logs = []  # 节点日志
        self._workflow_nodes = []  # 审批流程节点
        self._approval_records = []  # 审批记录
        self._approval_templates = []  # 审批模板
        self._culture_categories = []  # 文化分类
        self._channel_templates = []  # 渠道匹配模板
        self._planning_history = []  # 策划案历史库
        self._schedule_tasks = []  # 排期任务
        self._schedule_resources = []  # 排期资源
        self._schedule_templates = []  # 排期模板
        self._publish_nodes = []  # 发布节点
        self._analytics_records = []  # 数据透视记录
        self._analytics_reports = []  # 数据透视报告
        self._copyright_assets = []  # 版权资产
        self._init_sample_assets()
        self._init_sample_plans()
        self._init_node_logs()
        self._init_workflow_data()
        self._init_planning_assistant_data()
        self._init_schedule_data()
        self._init_publish_nodes()
        self._init_analytics_data()
        self._init_analytics_reports()
        self._init_copyright_data()

    def _init_sample_plans(self):
        """初始化示例策划案数据"""
        plans = [
            {"name": "丝路之韵数字复现",     "influence": 92.5,
             "status": "pending",   "category": "数字遗产",   "type": "IP联名",     "decay_factor": 0.04},
            {"name": "三星堆VR体验",         "influence": 88.0,
             "status": "pending",   "category": "沉浸式展览", "type": "展览",       "decay_factor": 0.05},
            {"name": "敦煌壁画修复",         "influence": 76.4,
             "status": "pending",   "category": "文物数字化", "type": "纪录片",     "decay_factor": 0.06},
            {"name": "故宫节气海报",         "influence": 82.1,
             "status": "pending",   "category": "社交媒体",   "type": "短视频",     "decay_factor": 0.03},
            {"name": "吴灵堂道教数字化",      "influence": 65.8,
             "status": "pending",   "category": "宗教文化",   "type": "其他",       "decay_factor": 0.07},
            {"name": "茶马古道纪录片系列",    "influence": 94.2,
             "status": "running",   "category": "影视内容",   "type": "纪录片",     "decay_factor": 0.02},
            {"name": "京剧脸谱AR互动展",     "influence": 71.3,
             "status": "completed", "category": "增强现实",   "type": "展览",       "decay_factor": 0.08},
            {"name": "二十四节气文创产品线",  "influence": 85.6,
             "status": "completed", "category": "文创开发",   "type": "品牌活动",   "decay_factor": 0.03},
            {"name": "黄河流域非遗地图",      "influence": 79.8,
             "status": "paused",    "category": "地理信息",   "type": "其他",       "decay_factor": 0.05},
            {"name": "苗族刺绣数字档案",      "influence": 68.4,
             "status": "paused",    "category": "民族工艺",   "type": "其他",       "decay_factor": 0.06},
            {"name": "长城无人机航拍计划",    "influence": 90.1,
             "status": "running",   "category": "航拍内容",   "type": "短视频",     "decay_factor": 0.02},
            {"name": "甲骨文科普动画系列",    "influence": 73.9,
             "status": "pending",   "category": "教育内容",   "type": "教育内容",   "decay_factor": 0.04},
            {"name": "苏州园林全景VR漫游",    "influence": 86.7,
             "status": "running",   "category": "虚拟游览",   "type": "展览",       "decay_factor": 0.02},
            {"name": "川剧变脸特效素材包",    "influence": 62.3,
             "status": "completed", "category": "视觉特效",   "type": "短视频",     "decay_factor": 0.09},
            {"name": "唐三彩3D打印复原项目",  "influence": 77.5,
             "status": "pending",   "category": "文物复原",   "type": "纪录片",     "decay_factor": 0.05},
            {"name": "端午龙舟赛直播矩阵",    "influence": 91.8,
             "status": "pending",   "category": "活动直播",   "type": "直播",       "decay_factor": 0.01},
            {"name": "皮影戏AI生成实验",      "influence": 55.2,
             "status": "reviewing", "category": "AI创作",     "type": "其他",       "decay_factor": 0.10},
            {"name": "云冈石窟数字孪生",      "influence": 96.3,
             "status": "running",   "category": "数字孪生",   "type": "展览",       "decay_factor": 0.02},
            {"name": "汉服穿搭指南短视频",    "influence": 83.4,
             "status": "completed", "category": "短视频",     "type": "短视频",     "decay_factor": 0.03},
            {"name": "中医经络交互图谱",       "influence": 70.6,
             "status": "reviewing", "category": "健康文化",   "type": "其他",       "decay_factor": 0.06},
            {"name": "青花瓷纹样NFT系列",     "influence": 87.9,
             "status": "pending",   "category": "数字藏品",   "type": "内容发布",   "decay_factor": 0.02},
            {"name": "傣族泼水节全景记录",    "influence": 74.1,
             "status": "paused",    "category": "民族节庆",   "type": "品牌活动",   "decay_factor": 0.05},
            {"name": "兵马俑微距摄影集",      "influence": 93.7,
             "status": "running",   "category": "摄影艺术",   "type": "短视频",     "decay_factor": 0.01},
            {"name": "昆曲名段音频修复工程",  "influence": 66.9,
             "status": "reviewing", "category": "音频修复",   "type": "其他",       "decay_factor": 0.07},
        ]
        now = int(time.time())
        for i, p in enumerate(plans):
            pid = f"PLN{i+1:04d}"
            p["id"] = pid
            p["created_at"] = now - (i * 7200)
            p["updated_at"] = now - (i * 3600)
            p["views"] = int(p["influence"] * 1200 + (i % 7) * 300)
            p["engagement"] = round(2.0 + (p["influence"] % 7) * 0.4, 1)
            p["heat"] = round(p["influence"] * 1.08, 1)
            self._planning_pool[pid] = p

    def _init_node_logs(self):
        """初始化引擎节点日志"""
        logs = [
            (16, 20, 41, "接入8部节点设备: 用户覆盖 |8| 数据就绪确认"),
            (16, 20, 39, "载入9部节点设备: 用户覆盖 |40| 数据融合验证"),
            (16, 20, 37, "衰减系数已同步至全部边缘节点 \u03b1=0.045"),
            (16, 20, 35, "丝路之韵数字复现 [PLN0001] 排期计算完成"),
            (16, 20, 33, "三星堆VR体验 [PLN0002] 热度预测值: 88.0 pts"),
            (16, 20, 30, "系统心跳检测正常 | 延迟 < 12ms"),
            (16, 20, 28, "敦煌壁画修复 [PLN0003] 资源依赖检查通过"),
            (16, 20, 25, "故宫节气海报 [PLN0004] 已加入待发布队列"),
            (16, 20, 22, "全局影响力指数刷新: 735.1 (+2.3%)"),
            (16, 20, 19, "茶马古道纪录片 [PLN0006] 正在执行分发任务"),
            (16, 20, 15, "引擎负载监控: CPU 34% | MEM 58% | GPU 12%"),
            (16, 20, 12, "新增资产入库通知: 敦煌飞天舞曲配乐.wav"),
            (16, 20, 9, "用户 admin 登录控制台 | 权限: Director"),
            (16, 20, 6, "系统初始化完成 | 矩阵引擎 v1.0 启动"),
            (16, 20, 3, "连接分布式存储集群 | 节点数: 24/24 在线"),
        ]
        for h, m, s, msg in logs:
            ts = f"[{h:02d}:{m:02d}:{s:02d}]"
            self._node_logs.append(f"{ts} {msg}")

    def get_planning_stats(self) -> dict:
        plans = list(self._planning_pool.values())
        active_count = sum(1 for p in plans if p["status"] in ("pending", "running"))
        influence_total = sum(p["influence"] for p in plans if p["status"] != "archived")
        asset_value = sum(a.get("size_mb", 0) for a in self._asset_pool.values()) * 1180  # 模拟估值

        # 雷达图维度得分 (模拟算法)
        radar = {
            "内容深度": min(95, 60 + len(plans) * 1.2),
            "传播广度": min(98, 55 + active_count * 2.5),
            "受众精准度": min(92, 50 + influence_total / 10),
            "技术融合度": min(88, 45 + len(self._asset_pool) * 3),
            "商业转化率": min(85, 40 + active_count * 1.8),
        }

        return {
            "influence_index": round(influence_total / len(plans) * 8 + 200, 1) if plans else 0,
            "active_plans": active_count,
            "asset_value_yuan": f"{asset_value / 10000:.1f}M",
            "runtime_hours": f"{int(self._engine_runtime_hours)}h",
            "radar_data": radar,
            "total_plans": len(plans),
        }

    def read_all_plans(self) -> list:
        """获取全部策划案"""
        return list(self._planning_pool.values())

    def get_planning_list(self, status_filter="") -> list:
        """获取策划案列表，支持状态过滤"""
        plans = list(self._planning_pool.values())
        if status_filter:
            plans = [p for p in plans if p["status"] == status_filter]
        return sorted(plans, key=lambda x: -x["influence"])

    def update_plan_status(self, plan_id: str, new_status: str) -> bool:
        """更新策划案状态"""
        if plan_id in self._planning_pool:
            self._planning_pool[plan_id]["status"] = new_status
            self._planning_pool[plan_id]["updated_at"] = int(time.time())
            return True
        return False

    def create_plan(self, data: dict) -> str:
        """创建新策划案"""
        pid = f"PLN{len(self._planning_pool)+1:04d}"
        data["id"] = pid
        data["created_at"] = int(time.time())
        data["updated_at"] = int(time.time())
        data["node_idx"] = 0
        if "status" not in data:
            data["status"] = "pending"
        self._planning_pool[pid] = data
        return pid

    def delete_plan(self, plan_id: str) -> bool:
        """删除策划案"""
        if plan_id in self._planning_pool:
            del self._planning_pool[plan_id]
            return True
        return False

    def update_plan(self, plan_id: str, data: dict) -> bool:
        """更新策划案信息"""
        if plan_id in self._planning_pool:
            data["updated_at"] = int(time.time())
            self._planning_pool[plan_id].update(data)
            return True
        return False

    def set_decay_factor(self, plan_id: str, factor: float) -> bool:
        """设置策划案传播衰减系数"""
        if plan_id in self._planning_pool:
            self._planning_pool[plan_id]["decay_factor"] = factor
            self._planning_pool[plan_id]["updated_at"] = int(time.time())
            return True
        return False

    def get_plan_by_id(self, plan_id: str) -> dict | None:
        """按 ID 查询策划案"""
        return self._planning_pool.get(plan_id)

    def schedule_plan(self, plan_id: str) -> dict:
        """
        智能排期：根据影响力、衰减系数、当前队列计算建议发布时间
        返回包含建议时间和预期热度的字典
        """
        import random
        plan = self._planning_pool.get(plan_id)
        if not plan:
            return {}
        influence = plan.get("influence", 50)
        decay = plan.get("decay_factor", 0.04)
        base_hour = 10
        # 影响力越高，建议越早发布；衰减越低，长尾效应越好
        recommended_hour = max(6, min(22, int(base_hour + (100 - influence) / 10)))
        expected_heat = round(influence * (1 - decay * 5) + random.uniform(-3, 5), 1)
        return {
            "recommended_hour": recommended_hour,
            "expected_heat": expected_heat,
            "slot": "黄金时段" if recommended_hour <= 12 else "常规时段",
        }

    def get_node_logs(self, limit=30) -> list:
        """获取最新的节点日志"""
        return self._node_logs[-limit:]

    def add_node_log(self, message: str):
        """添加新的日志条目"""
        now = time.localtime()
        ts = f"[{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}]"
        self._node_logs.append(f"{ts} {message}")
        # 保持日志不超过500条
        if len(self._node_logs) > 500:
            self._node_logs = self._node_logs[-500:]

    def get_engine_load(self) -> float:
        """获取当前引擎负载百分比（模拟）"""
        import random
        return random.uniform(25, 75)

    # ---------- 流程审批 ----------
    def _init_workflow_data(self):
        """初始化示例审批流程与待办记录"""
        self._workflow_nodes = [
            {"id": "WF001", "name": "内容初审", "role": "编辑", "order": 1},
            {"id": "WF002", "name": "合规审查", "role": "审核员", "order": 2},
            {"id": "WF003", "name": "总监审批", "role": "总监", "order": 3},
            {"id": "WF004", "name": "法务归档", "role": "法务", "order": 4},
        ]

        samples = [
            {"title": "故宫夜游直播策划案", "applicant": "张伟", "type": "内容发布", "amount": 120000, "node_idx": 0, "status": "pending"},
            {"title": "敦煌壁画NFT授权协议", "applicant": "李娜", "type": "版权授权", "amount": 850000, "urgency": "紧急", "reason": "需赶在文博会前完成授权签约，确保数字藏品准时上线", "node_idx": 1, "status": "pending"},
            {"title": "端午龙舟赛全国直播预算", "applicant": "王强", "type": "预算申请", "amount": 560000, "urgency": "常规", "reason": "端午系列直播活动设备租赁与流量采购费用申请", "node_idx": 0, "status": "pending"},
            {"title": "三星堆VR展合作方案", "applicant": "赵敏", "type": "商务合作", "amount": 2300000, "urgency": "加急", "reason": "与四川博物院联合举办三星堆VR沉浸展，需尽快敲定合作框架", "node_idx": 2, "status": "pending"},
            {"title": "非遗传承人访谈纪录片", "applicant": "刘洋", "type": "内容制作", "amount": 320000, "urgency": "常规", "reason": "录制10期非遗传承人访谈纪录片，用于短视频平台传播", "node_idx": 3, "status": "pending"},
            {"title": "春节IP联名营销计划", "applicant": "陈晨", "type": "营销推广", "amount": 1500000, "urgency": "紧急", "reason": "春节档期IP联名营销投放，需提前锁定渠道资源", "node_idx": 1, "status": "approved"},
            {"title": "博物馆导览音频采购", "applicant": "周杰", "type": "物资采购", "amount": 180000, "urgency": "常规", "reason": "为多馆区导览系统采购多语种音频授权包", "node_idx": 2, "status": "rejected"},
            {"title": "丝绸之路研学路线开发", "applicant": "吴芳", "type": "产品开发", "amount": 420000, "urgency": "加急", "reason": "暑期研学季前完成丝路主题路线产品开发与上架", "node_idx": 0, "status": "pending"},
        ]
        now = int(time.time())
        for i, s in enumerate(samples):
            self._approval_records.append({
                "id": f"APP{i+1:04d}",
                "title": s["title"],
                "applicant": s["applicant"],
                "type": s["type"],
                "amount": s["amount"],
                "node_idx": s["node_idx"],
                "status": s["status"],
                "created_at": now - (i * 3600 * 3),
                "updated_at": now - (i * 1800),
                "history": [],
                "attachment": f"附件_{i+1}.pdf",
            })

        self._approval_templates = [
            {"name": "标准内容发布审批", "nodes": ["WF001", "WF002", "WF003"]},
            {"name": "大额采购审批", "nodes": ["WF001", "WF002", "WF003", "WF004"]},
            {"name": "版权授权快速通道", "nodes": ["WF002", "WF003"]},
        ]

    def get_workflow_nodes(self) -> list:
        """获取审批流程节点"""
        return self._workflow_nodes

    def add_workflow_node(self, name: str, role: str) -> dict:
        """新增审批节点"""
        new_id = f"WF{len(self._workflow_nodes)+1:03d}"
        node = {"id": new_id, "name": name, "role": role, "order": len(self._workflow_nodes) + 1}
        self._workflow_nodes.append(node)
        return node

    def delete_workflow_node(self, node_id: str) -> bool:
        """删除审批节点"""
        for i, n in enumerate(self._workflow_nodes):
            if n["id"] == node_id:
                del self._workflow_nodes[i]
                for idx, n in enumerate(self._workflow_nodes):
                    n["order"] = idx + 1
                return True
        return False

    def get_approval_records(self, status: str = "") -> list:
        """获取审批记录，支持状态过滤"""
        records = self._approval_records
        if status:
            records = [r for r in records if r["status"] == status]
        return records

    def get_approval_stats(self) -> dict:
        """获取审批统计"""
        total = len(self._approval_records)
        pending = sum(1 for r in self._approval_records if r["status"] == "pending")
        approved = sum(1 for r in self._approval_records if r["status"] == "approved")
        rejected = sum(1 for r in self._approval_records if r["status"] == "rejected")
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "amount_pending": sum(r["amount"] for r in self._approval_records if r["status"] == "pending"),
            "amount_approved": sum(r["amount"] for r in self._approval_records if r["status"] == "approved"),
        }

    def approve_record(self, record_id: str, approver: str, comment: str) -> bool:
        """通过审批：推进到下一节点或结束"""
        for r in self._approval_records:
            if r["id"] == record_id:
                r["history"].append({
                    "node": self._workflow_nodes[r["node_idx"]]["name"] if r["node_idx"] < len(self._workflow_nodes) else "结束",
                    "action": "通过",
                    "approver": approver,
                    "comment": comment,
                    "time": int(time.time()),
                })
                if r["node_idx"] < len(self._workflow_nodes) - 1:
                    r["node_idx"] += 1
                else:
                    r["status"] = "approved"
                r["updated_at"] = int(time.time())
                return True
        return False

    def reject_record(self, record_id: str, approver: str, comment: str) -> bool:
        """驳回审批"""
        for r in self._approval_records:
            if r["id"] == record_id:
                r["history"].append({
                    "node": self._workflow_nodes[r["node_idx"]]["name"] if r["node_idx"] < len(self._workflow_nodes) else "结束",
                    "action": "驳回",
                    "approver": approver,
                    "comment": comment,
                    "time": int(time.time()),
                })
                r["status"] = "rejected"
                r["updated_at"] = int(time.time())
                return True
        return False

    def create_approval(self, data: dict) -> str:
        """创建新的审批申请"""
        aid = f"APP{len(self._approval_records)+1:04d}"
        data["id"] = aid
        data["node_idx"] = 0
        data["status"] = "pending"
        data["created_at"] = int(time.time())
        data["updated_at"] = int(time.time())
        data["history"] = []
        self._approval_records.append(data)
        return aid

    # ---------- 内容策划助手 ----------
    def _init_planning_assistant_data(self):
        """初始化内容策划助手基础数据"""
        self._culture_categories = [
            "视觉艺术", "传统戏剧", "民族音乐", "非遗技艺", "历史文物",
            "节庆民俗", "方言文学", "饮食文化", "服饰文化", "建筑遗产",
            "宗教文化", "数字文创"
        ]

        self._channel_templates = [
            # 线上社交传播
            {"channel": "社交媒体矩阵",     "audience": "大众舆论 / 热点发酵",        "fit": 0.86, "recommend": 4.5, "category": "社交传播"},
            {"channel": "短视频矩阵",       "audience": "年轻大众 / 碎片化消费",       "fit": 0.90, "recommend": 4.7, "category": "短视频"},
            {"channel": "中长视频平台",     "audience": "Z世代 / 知识型深度用户",     "fit": 0.82, "recommend": 4.2, "category": "长视频"},
            # 数字空间体验
            {"channel": "数字博物馆",       "audience": "文博爱好者 / 教育用户",       "fit": 0.78, "recommend": 4.0, "category": "数字空间"},
            {"channel": "AR/VR 沉浸式导览", "audience": "科技尝鲜者 / 亲子教育",       "fit": 0.75, "recommend": 3.8, "category": "沉浸体验"},
            # 线下实体场景
            {"channel": "线下沉浸式特展",   "audience": "城市中产 / 打卡消费群体",     "fit": 0.72, "recommend": 3.7, "category": "线下特展"},
            {"channel": "文化研学",         "audience": "K12 / 高校 / 政企培训",       "fit": 0.68, "recommend": 3.5, "category": "教育研学"},
            # 商业变现
            {"channel": "IP 授权",          "audience": "品牌方 / 消费品牌",           "fit": 0.70, "recommend": 3.6, "category": "商业授权"},
            {"channel": "高端文创电商",     "audience": "文化消费者 / 礼品采购",       "fit": 0.65, "recommend": 3.3, "category": "文创电商"},
            {"channel": "海外文化传播",     "audience": "国际受众 / 使领馆 / 文旅机构", "fit": 0.60, "recommend": 3.0, "category": "海外传播"},
        ]

        # 预置几条历史策划
        self._planning_history = [
            {
                "id": "HIS0001",
                "title": "故宫纹样二十四节气海报",
                "category": "视觉艺术",
                "gene": {"depth": 72, "narrative": 68, "visual": 90, "interact": 45, "trend": 82},
                "summary": "以故宫建筑纹样为视觉核心，结合二十四节气叙事，制作系列国风海报。",
                "channels": ["微信公众号", "小红书", "微博"],
                "created_at": int(time.time()) - 86400 * 3,
            },
            {
                "id": "HIS0002",
                "title": "昆曲名段数字化传播",
                "category": "传统戏剧",
                "gene": {"depth": 88, "narrative": 85, "visual": 62, "interact": 55, "trend": 58},
                "summary": "将昆曲经典唱段进行可视化拆解，配合字幕与身段标注，降低欣赏门槛。",
                "channels": ["B站中长视频", "知乎", "微信公众号"],
                "created_at": int(time.time()) - 86400 * 7,
            },
            {
                "id": "HIS0003",
                "title": "苗族银饰锻造技艺纪录",
                "category": "非遗技艺",
                "gene": {"depth": 80, "narrative": 78, "visual": 88, "interact": 70, "trend": 75},
                "summary": "记录苗族银饰锻造全流程，突出匠人故事与纹样寓意，适合短视频传播。",
                "channels": ["抖音短视频", "快手", "B站中长视频"],
                "created_at": int(time.time()) - 86400 * 12,
            },
        ]

    def get_culture_categories(self) -> list:
        return self._culture_categories

    def get_channel_templates(self) -> list:
        return self._channel_templates

    def get_planning_history(self) -> list:
        """按时间倒序返回策划历史"""
        return sorted(self._planning_history, key=lambda x: x["created_at"], reverse=True)

    def save_planning_history(self, data: dict) -> str:
        """保存策划方案到历史库"""
        hid = f"HIS{len(self._planning_history)+1:04d}"
        data["id"] = hid
        data["created_at"] = int(time.time())
        self._planning_history.append(data)
        return hid

    def delete_planning_history(self, hid: str) -> bool:
        for i, h in enumerate(self._planning_history):
            if h["id"] == hid:
                del self._planning_history[i]
                return True
        return False

    # ---------- 版权存证 ----------
    def read_certificates(self) -> list:
        """读取版权存证记录"""
        return getattr(self, "_certificates", [])

    def add_certificate(self, seed: str, asset_name: str):
        """新增一条国密 SM2 链上存证记录"""
        import hashlib, time
        if not hasattr(self, "_certificates"):
            self._certificates = []
        fingerprint = hashlib.sha256(f"{seed}:{asset_name}:{time.time()}".encode()).hexdigest()
        self._certificates.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "asset": asset_name,
            "hash": fingerprint,
        })
        return fingerprint

    # ---------- 排期计划 ----------
    def _init_schedule_data(self):
        """初始化示例排期任务、资源与模板"""
        self._schedule_resources = [
            {"id": "R01", "name": "文案组", "type": "team", "capacity": 3, "cost_per_day": 2000},
            {"id": "R02", "name": "拍摄组", "type": "team", "capacity": 2, "cost_per_day": 3500},
            {"id": "R03", "name": "后期组", "type": "team", "capacity": 2, "cost_per_day": 2800},
            {"id": "R04", "name": "设计组", "type": "team", "capacity": 2, "cost_per_day": 2500},
            {"id": "R05", "name": "运营组", "type": "team", "capacity": 4, "cost_per_day": 1800},
            {"id": "R06", "name": "演播厅A", "type": "venue", "capacity": 1, "cost_per_day": 5000},
            {"id": "R07", "name": "外景场地", "type": "venue", "capacity": 2, "cost_per_day": 3000},
            {"id": "R08", "name": "剪辑工作站", "type": "equipment", "capacity": 3, "cost_per_day": 800},
        ]

        self._schedule_templates = [
            {
                "name": "短视频标准排期",
                "tasks": [
                    {"name": "脚本创意", "duration": 3, "phase": "pre_production"},
                    {"name": "拍摄执行", "duration": 2, "phase": "production"},
                    {"name": "剪辑包装", "duration": 3, "phase": "post_production"},
                    {"name": "发布运营", "duration": 5, "phase": "release"},
                ],
            },
            {
                "name": "纪录片制作排期",
                "tasks": [
                    {"name": "选题调研", "duration": 5, "phase": "pre_production"},
                    {"name": "脚本分镜", "duration": 5, "phase": "pre_production"},
                    {"name": "实地拍摄", "duration": 10, "phase": "production"},
                    {"name": "素材整理", "duration": 3, "phase": "post_production"},
                    {"name": "精剪配音", "duration": 7, "phase": "post_production"},
                    {"name": "宣发上线", "duration": 7, "phase": "release"},
                ],
            },
            {
                "name": "沉浸式展览排期",
                "tasks": [
                    {"name": "空间设计", "duration": 7, "phase": "pre_production"},
                    {"name": "内容制作", "duration": 10, "phase": "production"},
                    {"name": "技术联调", "duration": 5, "phase": "production"},
                    {"name": "布展调试", "duration": 4, "phase": "post_production"},
                    {"name": "开幕运营", "duration": 14, "phase": "release"},
                ],
            },
        ]

        import datetime
        base = datetime.date(2026, 6, 15)
        sample_tasks = [
            {"name": "故宫夜游脚本撰写", "project": "故宫夜游直播策划案", "owner": "张伟",
             "start_offset": 0, "duration": 5, "progress": 80, "status": "in_progress",
             "priority": "high", "resources": ["R01", "R04"], "dependencies": [], "phase": "pre_production"},
            {"name": "故宫夜游场景拍摄", "project": "故宫夜游直播策划案", "owner": "王强",
             "start_offset": 5, "duration": 3, "progress": 30, "status": "in_progress",
             "priority": "high", "resources": ["R02", "R06"], "dependencies": [0], "phase": "production"},
            {"name": "故宫夜游后期剪辑", "project": "故宫夜游直播策划案", "owner": "李娜",
             "start_offset": 8, "duration": 4, "progress": 0, "status": "not_started",
             "priority": "medium", "resources": ["R03", "R08"], "dependencies": [1], "phase": "post_production"},
            {"name": "丝路之韵前期调研", "project": "丝路之韵数字复现", "owner": "赵敏",
             "start_offset": -3, "duration": 6, "progress": 100, "status": "completed",
             "priority": "medium", "resources": ["R01"], "dependencies": [], "phase": "pre_production"},
            {"name": "丝路之韵三维建模", "project": "丝路之韵数字复现", "owner": "刘洋",
             "start_offset": 3, "duration": 10, "progress": 45, "status": "in_progress",
             "priority": "critical", "resources": ["R04", "R08"], "dependencies": [3], "phase": "production"},
            {"name": "端午龙舟赛直播筹备", "project": "端午龙舟赛全国直播", "owner": "陈晨",
             "start_offset": 10, "duration": 7, "progress": 10, "status": "not_started",
             "priority": "critical", "resources": ["R02", "R05", "R07"], "dependencies": [], "phase": "pre_production"},
            {"name": "敦煌壁画素材修复", "project": "敦煌壁画修复", "owner": "周杰",
             "start_offset": 2, "duration": 8, "progress": 60, "status": "delayed",
             "priority": "high", "resources": ["R03", "R04"], "dependencies": [], "phase": "post_production"},
        ]
        for i, t in enumerate(sample_tasks):
            start = base + datetime.timedelta(days=t["start_offset"])
            end = start + datetime.timedelta(days=t["duration"] - 1)
            self._schedule_tasks.append({
                "id": f"TSK{i+1:04d}",
                "name": t["name"],
                "project": t["project"],
                "owner": t["owner"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "duration": t["duration"],
                "progress": t["progress"],
                "status": t["status"],
                "priority": t["priority"],
                "resources": t["resources"],
                "dependencies": t["dependencies"],
                "phase": t["phase"],
            })

    def _init_publish_nodes(self):
        """初始化示例发布节点数据"""
        sample = [
            {"title": "三星堆3D文物修复记录", "platform": "WeChat/朋友圈", "time": "13:00", "content": "三星堆3D文物修复记录"},
            {"title": "二十四节气：清明特辑", "platform": "抖音/TikTok", "time": "14:00", "content": "二十四节气：清明特辑"},
            {"title": "三星堆3D文物修复记录", "platform": "抖音/TikTok", "time": "17:00", "content": "三星堆3D文物修复记录"},
            {"title": "故宫数字创意大赛发布", "platform": "小红书/RED", "time": "21:00", "content": "故宫数字创意大赛发布"},
            {"title": "故宫数字创意大赛发布", "platform": "抖音/TikTok", "time": "19:30", "content": "故宫数字创意大赛发布"},
        ]
        for s in sample:
            self.add_publish_node(s)

    def get_schedule_tasks(self) -> list:
        """获取全部排期任务"""
        return self._schedule_tasks

    def get_schedule_task_by_id(self, task_id: str) -> dict | None:
        """按 ID 查询任务"""
        for t in self._schedule_tasks:
            if t["id"] == task_id:
                return t
        return None

    def add_schedule_task(self, data: dict) -> str:
        """新增排期任务"""
        tid = f"TSK{len(self._schedule_tasks)+1:04d}"
        data["id"] = tid
        if "progress" not in data:
            data["progress"] = 0
        if "status" not in data:
            data["status"] = "not_started"
        if "dependencies" not in data:
            data["dependencies"] = []
        if "resources" not in data:
            data["resources"] = []
        self._schedule_tasks.append(data)
        return tid

    def update_schedule_task(self, task_id: str, data: dict) -> bool:
        """更新排期任务"""
        for t in self._schedule_tasks:
            if t["id"] == task_id:
                t.update(data)
                return True
        return False

    def delete_schedule_task(self, task_id: str) -> bool:
        """删除排期任务"""
        for i, t in enumerate(self._schedule_tasks):
            if t["id"] == task_id:
                del self._schedule_tasks[i]
                # 清理依赖该任务的依赖索引
                for other in self._schedule_tasks:
                    other["dependencies"] = [d for d in other["dependencies"] if d != task_id]
                return True
        return False

    def get_schedule_resources(self) -> list:
        """获取排期资源列表"""
        return self._schedule_resources

    def get_schedule_resource_by_id(self, rid: str) -> dict | None:
        """按 ID 查询资源"""
        for r in self._schedule_resources:
            if r["id"] == rid:
                return r
        return None

    def get_schedule_templates(self) -> list:
        """获取排期模板"""
        return self._schedule_templates

    def get_schedule_stats(self) -> dict:
        """获取排期统计"""
        tasks = self._schedule_tasks
        total = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "completed")
        delayed = sum(1 for t in tasks if t["status"] == "delayed")
        in_progress = sum(1 for t in tasks if t["status"] == "in_progress")
        not_started = sum(1 for t in tasks if t["status"] == "not_started")
        total_cost = 0
        for t in tasks:
            for rid in t.get("resources", []):
                r = self.get_schedule_resource_by_id(rid)
                if r:
                    total_cost += r["cost_per_day"] * t["duration"]
        return {
            "total": total,
            "completed": completed,
            "delayed": delayed,
            "in_progress": in_progress,
            "not_started": not_started,
            "total_cost": total_cost,
        }

    # ---------- 发布节点排期 ----------
    def get_publish_nodes(self) -> list:
        """获取发布节点列表"""
        return getattr(self, "_publish_nodes", [])

    def get_publish_node_by_id(self, nid: str) -> dict | None:
        """按 ID 查询发布节点"""
        for n in self.get_publish_nodes():
            if n["id"] == nid:
                return n
        return None

    def add_publish_node(self, data: dict) -> str:
        """新增发布节点"""
        if not hasattr(self, "_publish_nodes"):
            self._publish_nodes = []
        nid = f"9CH-{len(self._publish_nodes)+17470:05d}"
        data["id"] = nid
        data.setdefault("resonance", self._estimate_resonance(data.get("time", "12:00"), data.get("platform", "")))
        self._publish_nodes.append(data)
        return nid

    def update_publish_node(self, nid: str, data: dict) -> bool:
        """更新发布节点"""
        for n in self._publish_nodes:
            if n["id"] == nid:
                if "time" in data or "platform" in data:
                    t = data.get("time", n.get("time", "12:00"))
                    p = data.get("platform", n.get("platform", ""))
                    data["resonance"] = self._estimate_resonance(t, p)
                n.update(data)
                return True
        return False

    def delete_publish_node(self, nid: str) -> bool:
        """删除发布节点"""
        for i, n in enumerate(self._publish_nodes):
            if n["id"] == nid:
                del self._publish_nodes[i]
                return True
        return False

    def _estimate_resonance(self, time_str: str, platform: str) -> float:
        """
        CPS 引擎：根据发布时间和平台估算流量共振指数
        不同平台在不同时段存在流量脉冲峰值区
        """
        import re
        m = re.search(r"(\d+):(\d+)", time_str)
        if not m:
            return 50.0
        hour = int(m.group(1)) + int(m.group(2)) / 60.0

        # 平台基础热度
        base = {
            "WeChat/朋友圈": 55,
            "抖音/TikTok": 78,
            "小红书/RED": 72,
            "微博/Weibo": 68,
            "Bilibili": 65,
            "知乎/Zhihu": 50,
        }.get(platform, 55)

        # 时段脉冲加成：早晚高峰（7-9, 12-13, 18-22）为峰值区
        peak_bonus = 0
        if 7 <= hour <= 9:
            peak_bonus = 18
        elif 11.5 <= hour <= 13:
            peak_bonus = 15
        elif 18 <= hour <= 22:
            peak_bonus = 22
        elif 0 <= hour <= 6:
            peak_bonus = -25
        else:
            peak_bonus = -5

        score = base + peak_bonus
        return round(min(99.9, max(10.0, score)), 2)

    def get_resonance_report(self, node: dict) -> dict:
        """生成 CPS 引擎推演报告"""
        score = node.get("resonance", 50.0)
        time_str = node.get("time", "12:00")
        platform = node.get("platform", "")
        if score >= 70:
            level = "high"
            warning = "当前时位处于平台流量高峰区，建议按原计划发布。"
        elif score >= 50:
            level = "medium"
            warning = "当前时位流量中等，可考虑微调至更高峰值区以提升传播效果。"
        else:
            level = "low"
            # 推荐最近峰值区
            candidates = ["07:00", "08:00", "12:00", "18:00", "20:00", "21:00"]
            best = max(candidates, key=lambda t: self._estimate_resonance(t, platform))
            warning = f"当前时位处于平台流量洼地，建议延后至最近的脉冲峰值区（如 {best}）。"
        return {
            "score": score,
            "level": level,
            "warning": warning,
            "platform": platform,
        }


    # ---------- 数据透视 ----------
    def _init_analytics_data(self):
        """初始化示例运营数据，用于多维透视分析"""
        import datetime, random
        projects = ["故宫夜游直播", "丝路之韵数字复现", "三星堆VR体验", "敦煌壁画修复", "端午龙舟赛直播"]
        platforms = ["抖音/TikTok", "小红书/RED", "WeChat/朋友圈", "微博/Weibo", "Bilibili"]
        content_types = ["短视频", "直播", "图文", "纪录片", "互动H5"]
        categories = ["历史文化", "非遗技艺", "数字展览", "节气民俗", "IP联名"]
        base_date = datetime.date(2026, 5, 1)
        for i in range(120):
            date = base_date + datetime.timedelta(days=i % 60)
            project = projects[i % len(projects)]
            platform = platforms[i % len(platforms)]
            ctype = content_types[i % len(content_types)]
            category = categories[i % len(categories)]
            # 平台基础流量 + 日期波动 + 随机噪声
            base_views = {"抖音/TikTok": 80000, "小红书/RED": 45000, "WeChat/朋友圈": 30000,
                          "微博/Weibo": 55000, "Bilibili": 60000}[platform]
            seasonal = 1 + 0.3 * (1 if date.weekday() < 5 else 1.4)
            noise = random.uniform(0.7, 1.3)
            views = int(base_views * seasonal * noise)
            likes = int(views * random.uniform(0.04, 0.09))
            shares = int(views * random.uniform(0.01, 0.04))
            comments = int(views * random.uniform(0.005, 0.02))
            followers = int(views * random.uniform(0.02, 0.06))
            conversion = round(random.uniform(0.5, 4.5), 2)
            self._analytics_records.append({
                "id": f"REC{i+1:05d}",
                "date": date.isoformat(),
                "project": project,
                "platform": platform,
                "content_type": ctype,
                "category": category,
                "views": views,
                "likes": likes,
                "shares": shares,
                "comments": comments,
                "followers": followers,
                "conversion": conversion,
            })

    def get_analytics_records(self, filters: dict = None) -> list:
        """按条件筛选数据记录"""
        records = self._analytics_records
        if not filters:
            return records
        result = []
        for r in records:
            ok = True
            if "project" in filters and filters["project"] and r["project"] != filters["project"]:
                ok = False
            if "platform" in filters and filters["platform"] and r["platform"] != filters["platform"]:
                ok = False
            if "content_type" in filters and filters["content_type"] and r["content_type"] != filters["content_type"]:
                ok = False
            if "category" in filters and filters["category"] and r["category"] != filters["category"]:
                ok = False
            if "start_date" in filters and filters["start_date"] and r["date"] < filters["start_date"]:
                ok = False
            if "end_date" in filters and filters["end_date"] and r["date"] > filters["end_date"]:
                ok = False
            if ok:
                result.append(r)
        return result

    # ---------- 数据透视报告 / 归因分析 ----------
    def _init_analytics_reports(self):
        """初始化示例透视报告，用于归因分析工作台"""
        import random
        reports = [
            {"uid": "ANL-17589-32", "title": "敦煌AR展厅传播分析", "driver": "文化导向"},
            {"uid": "ANL-17589-51", "title": "非遗传承纪录片放量", "driver": "文化导向"},
            {"uid": "ANL-17589-49", "title": "敦煌AR展厅传播分析", "driver": "文化导向"},
            {"uid": "ANL-17589-35", "title": "故宫雪景专题归因", "driver": "文化导向"},
            {"uid": "ANL-17589-20", "title": "敦煌AR展厅传播分析", "driver": "文化导向"},
            {"uid": "ANL-17589-95", "title": "敦煌AR展厅传播分析", "driver": "文化导向"},
            {"uid": "ANL-17589-13", "title": "历史文化街市扫描", "driver": "风格导向"},
            {"uid": "ANL-17589-57", "title": "故宫雪景专题归因", "driver": "文化导向"},
        ]
        for r in reports:
            exposure = random.randint(25000, 120000)
            engagement = int(exposure * random.uniform(0.008, 0.025))
            momentum = round(random.uniform(20, 100), 2)
            r["exposure"] = exposure
            r["engagement"] = engagement
            r["momentum"] = momentum
            r["attribution"] = {
                "文化内核驱动贡献度": random.randint(45, 85),
                "分发渠道营销贡献度": random.randint(15, 55),
                "用户自传播贡献度": random.randint(5, 30),
            }
        self._analytics_reports = reports

    def get_analytics_reports(self, keyword: str = "", driver: str = "") -> list:
        """按关键词和主要动力筛选报告"""
        result = []
        kw = keyword.strip().lower()
        for r in self._analytics_reports:
            if driver and r.get("driver") != driver:
                continue
            if kw and kw not in r.get("title", "").lower() and kw not in r.get("uid", "").lower():
                continue
            result.append(r)
        return result

    def get_analytics_report_by_uid(self, uid: str) -> dict | None:
        """按 UID 获取报告"""
        for r in self._analytics_reports:
            if r["uid"] == uid:
                return r
        return None

    def get_analytics_report_drivers(self) -> list:
        """获取主要动力去重值"""
        return sorted({r.get("driver", "") for r in self._analytics_reports if r.get("driver")})

    def get_analytics_sentiment_series(self, points: int = 48) -> list:
        """
        模拟实时情感流监测数据
        返回 [(index, value), ...]，用于折线图
        """
        import random, math
        series = []
        base = 50
        for i in range(points):
            t = i / points * math.pi * 4
            val = base + 30 * math.sin(t) + 15 * math.sin(t * 2.5) + random.uniform(-8, 8)
            series.append((i, round(max(10, min(100, val)), 2)))
        return series

    def recalibrate_reports(self):
        """全局算法重校准：重新计算所有报告的动量得分和归因"""
        import random
        for r in self._analytics_reports:
            delta = random.uniform(-10, 10)
            r["momentum"] = round(max(0, min(100, r["momentum"] + delta)), 2)
            r["attribution"] = {
                "文化内核驱动贡献度": random.randint(45, 85),
                "分发渠道营销贡献度": random.randint(15, 55),
                "用户自传播贡献度": random.randint(5, 30),
            }

    def get_analytics_dimension_values(self, dimension: str) -> list:
        """获取某维度的去重值"""
        return sorted({r.get(dimension, "") for r in self._analytics_records if r.get(dimension)})

    def get_analytics_kpis(self, records: list = None) -> dict:
        """计算核心 KPI"""
        if records is None:
            records = self._analytics_records
        if not records:
            return {"total_views": 0, "total_likes": 0, "total_shares": 0,
                    "total_comments": 0, "avg_conversion": 0, "total_records": 0,
                    "engagement_rate": 0}
        total_views = sum(r["views"] for r in records)
        total_likes = sum(r["likes"] for r in records)
        total_shares = sum(r["shares"] for r in records)
        total_comments = sum(r["comments"] for r in records)
        avg_conversion = sum(r["conversion"] for r in records) / len(records)
        engagement = total_views and ((total_likes + total_shares + total_comments) / total_views * 100)
        return {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
            "avg_conversion": round(avg_conversion, 2),
            "total_records": len(records),
            "engagement_rate": round(engagement, 2),
        }

    def pivot_analytics(self, records: list, row_dim: str, col_dim: str, metric: str, agg: str = "sum") -> dict:
        """
        简易透视：按行维度、列维度聚合指标
        返回 {"rows": [...], "cols": [...], "data": {...}, "totals": {...}}
        """
        import functools
        rows = sorted({r.get(row_dim, "") for r in records if r.get(row_dim)})
        cols = sorted({r.get(col_dim, "") for r in records if r.get(col_dim)})
        data = {}
        for r in records:
            rv = r.get(row_dim, "")
            cv = r.get(col_dim, "")
            if rv not in data:
                data[rv] = {}
            if cv not in data[rv]:
                data[rv][cv] = []
            data[rv][cv].append(r.get(metric, 0))

        def agg_values(vals):
            if agg == "sum":
                return sum(vals)
            if agg == "avg":
                return round(sum(vals) / len(vals), 2) if vals else 0
            if agg == "max":
                return max(vals) if vals else 0
            if agg == "min":
                return min(vals) if vals else 0
            if agg == "count":
                return len(vals)
            return sum(vals)

        result = {rv: {cv: agg_values(data.get(rv, {}).get(cv, [])) for cv in cols} for rv in rows}
        row_totals = {rv: agg_values(functools.reduce(lambda a, b: a + b, data.get(rv, {}).values(), [])) for rv in rows}
        col_totals = {cv: agg_values(sum((data.get(rv, {}).get(cv, []) for rv in rows), [])) for cv in cols}
        all_values = [v for rv in rows for cv in cols for v in data.get(rv, {}).get(cv, [])]
        grand_total = agg_values(all_values)
        return {"rows": rows, "cols": cols, "data": result,
                "row_totals": row_totals, "col_totals": col_totals, "grand_total": grand_total}

    def get_analytics_trend(self, records: list, metric: str = "views") -> list:
        """按日期聚合指标，返回 [(date, value), ...]"""
        from collections import defaultdict
        groups = defaultdict(list)
        for r in records:
            groups[r["date"]].append(r.get(metric, 0))
        return sorted((d, sum(v)) for d, v in groups.items())

    def detect_anomalies(self, records: list, metric: str = "views", threshold: float = 2.0) -> list:
        """基于均值+标准差识别异常值"""
        import statistics, math
        vals = [r.get(metric, 0) for r in records]
        if len(vals) < 3:
            return []
        mean = statistics.mean(vals)
        std = statistics.stdev(vals) if len(vals) > 1 else 0
        anomalies = []
        for r in records:
            v = r.get(metric, 0)
            z = (v - mean) / std if std else 0
            if abs(z) >= threshold:
                anomalies.append({
                    "record": r,
                    "metric": metric,
                    "value": v,
                    "z_score": round(z, 2),
                    "direction": "high" if z > 0 else "low",
                })
        return sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True)

    def get_analytics_correlation(self, records: list) -> dict:
        """计算 views/likes/shares/comments/followers/conversion 两两相关系数"""
        import statistics, math
        metrics = ["views", "likes", "shares", "comments", "followers", "conversion"]
        result = {}
        for i, m1 in enumerate(metrics):
            result[m1] = {}
            for m2 in metrics[i:]:
                x = [r.get(m1, 0) for r in records]
                y = [r.get(m2, 0) for r in records]
                if len(x) < 2:
                    result[m1][m2] = 0.0
                    continue
                mx, my = statistics.mean(x), statistics.mean(y)
                sx = statistics.stdev(x) if len(x) > 1 else 0
                sy = statistics.stdev(y) if len(y) > 1 else 0
                if sx == 0 or sy == 0:
                    result[m1][m2] = 0.0
                    continue
                cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) - 1)
                result[m1][m2] = round(cov / (sx * sy), 3)
        return result

    # ---------- 版权卫士 ----------
    def _init_copyright_data(self):
        """初始化示例版权资产与监测数据"""
        import random, datetime
        base_date = datetime.date(2026, 1, 15)
        samples = [
            {"title": "故宫雪景专题海报", "type": "图片", "owner": "故宫博物院", "status": "已登记"},
            {"title": "敦煌飞天数字壁画", "type": "数字藏品", "owner": "敦煌研究院", "status": "已登记"},
            {"title": "三星堆青铜面具3D模型", "type": "3D模型", "owner": "三星堆博物馆", "status": "审核中"},
            {"title": "二十四节气清明短片", "type": "视频", "owner": "央视网", "status": "已登记"},
            {"title": "丝路之韵民族音乐", "type": "音频", "owner": "国家大剧院", "status": "未保护"},
            {"title": "故宫数字创意大赛H5", "type": "互动H5", "owner": "故宫出版社", "status": "已过期"},
            {"title": "非遗剪纸技艺纪录片", "type": "视频", "owner": "中国民间文艺家协会", "status": "已登记"},
            {"title": "长城无人机航拍素材", "type": "视频", "owner": "中国长城学会", "status": "审核中"},
        ]
        statuses = ["已登记", "审核中", "未保护", "已过期"]
        for i, s in enumerate(samples):
            create_date = base_date + datetime.timedelta(days=i * 12)
            expire_date = create_date + datetime.timedelta(days=365 * 10)
            status = s.get("status", random.choice(statuses))
            # 风险指数 0~1，未保护作品风险更高
            risk_index = round(random.uniform(0.05, 0.95), 2)
            if status == "未保护":
                risk_index = round(max(risk_index, 0.65), 2)
                risk = "high"
            elif status == "已过期":
                risk_index = round(min(risk_index, 0.35), 2)
                risk = "medium"
            elif risk_index >= 0.75:
                risk = "high"
            elif risk_index >= 0.4:
                risk = "medium"
            else:
                risk = "low"
            # 链上状态
            if status == "已登记":
                chain_status = "PROTECTED"
            elif status in ("审核中", "未保护"):
                chain_status = "PENDING"
            else:
                chain_status = "UNPROTECTED"
            self._copyright_assets.append({
                "id": f"CPRT-17841-{i+1:03d}",
                "title": s["title"],
                "type": s["type"],
                "owner": s["owner"],
                "status": status,
                "registration_no": f"国作登字-2026-F-{i+1:04d}" if status in ("已登记", "已过期") else "",
                "create_date": create_date.isoformat(),
                "expire_date": expire_date.isoformat(),
                "risk_index": risk_index,
                "similarity_score": risk_index,
                "risk_level": risk,
                "risk_reason": self._generate_risk_reason(status, risk, risk_index),
                "chain_status": chain_status,
                "fingerprint": self._generate_copyright_fingerprint(),
                "infringement_count": random.randint(0, 12) if risk != "low" else 0,
                "platforms": random.sample(["抖音", "小红书", "微博", "B站", "知乎", "微信"], k=random.randint(1, 4)),
                "last_scan": (datetime.date.today() - datetime.timedelta(days=random.randint(0, 5))).isoformat(),
                "license_count": random.randint(0, 5),
                "evidence_count": random.randint(1, 8),
            })

    def _generate_risk_reason(self, status: str, risk: str, risk_index: float) -> str:
        if status == "未保护":
            return "作品尚未进行版权登记，存在被侵权后难以举证的风险"
        if status == "已过期":
            return "版权保护期已届满，作品进入公有领域"
        if risk == "high":
            return f"风险指数 {risk_index:.2%}，检测到多个疑似侵权链接"
        if risk == "medium":
            return f"风险指数 {risk_index:.2%}，建议持续监测"
        return "暂未发现明显侵权风险"

    def _generate_copyright_fingerprint(self) -> str:
        """生成指纹 DNA 序列（模拟哈希）"""
        import random
        return "".join(random.choice("0123456789ABCDEF") for _ in range(24))

    def get_copyright_assets(self, filters: dict = None) -> list:
        """按条件筛选版权资产"""
        if filters is None:
            return self._copyright_assets
        result = []
        kw = filters.get("keyword", "").strip().lower()
        status = filters.get("status", "")
        risk = filters.get("risk", "")
        ctype = filters.get("type", "")
        for a in self._copyright_assets:
            if status and a["status"] != status:
                continue
            if risk and a["risk_level"] != risk:
                continue
            if ctype and a["type"] != ctype:
                continue
            if kw and kw not in a["title"].lower() and kw not in a["id"].lower():
                continue
            result.append(a)
        return result

    def get_copyright_asset_by_id(self, aid: str) -> dict | None:
        """按 ID 查询版权资产"""
        for a in self._copyright_assets:
            if a["id"] == aid:
                return a
        return None

    def get_copyright_stats(self) -> dict:
        """版权资产统计"""
        total = len(self._copyright_assets)
        if total == 0:
            return {}
        high = sum(1 for a in self._copyright_assets if a["risk_level"] == "high")
        medium = sum(1 for a in self._copyright_assets if a["risk_level"] == "medium")
        low = sum(1 for a in self._copyright_assets if a["risk_level"] == "low")
        registered = sum(1 for a in self._copyright_assets if a["status"] == "已登记")
        unprotected = sum(1 for a in self._copyright_assets if a["status"] == "未保护")
        expired = sum(1 for a in self._copyright_assets if a["status"] == "已过期")
        pending = sum(1 for a in self._copyright_assets if a["status"] == "审核中")
        total_infringements = sum(a.get("infringement_count", 0) for a in self._copyright_assets)
        return {
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
            "registered": registered,
            "unprotected": unprotected,
            "expired": expired,
            "pending": pending,
            "total_infringements": total_infringements,
        }

    def scan_copyright_risks(self) -> list:
        """重新扫描全部资产风险并返回变更列表"""
        import random, datetime
        changes = []
        for a in self._copyright_assets:
            old_risk = a["risk_level"]
            old_count = a.get("infringement_count", 0)
            # 模拟扫描：风险指数波动，侵权数变化
            delta = random.uniform(-0.08, 0.08)
            a["risk_index"] = round(max(0.0, min(0.99, a["risk_index"] + delta)), 2)
            a["similarity_score"] = a["risk_index"]
            a["infringement_count"] = max(0, a["infringement_count"] + random.randint(-2, 3))
            a["last_scan"] = datetime.date.today().isoformat()
            # 重新判定风险
            if a["status"] == "未保护":
                a["risk_level"] = "high"
            elif a["status"] == "已过期":
                a["risk_level"] = "medium"
            elif a["risk_index"] >= 0.75 or a["infringement_count"] >= 5:
                a["risk_level"] = "high"
            elif a["risk_index"] >= 0.4 or a["infringement_count"] >= 2:
                a["risk_level"] = "medium"
            else:
                a["risk_level"] = "low"
            a["risk_reason"] = self._generate_risk_reason(a["status"], a["risk_level"], a["risk_index"])
            if old_risk != a["risk_level"] or old_count != a["infringement_count"]:
                changes.append({
                    "id": a["id"],
                    "title": a["title"],
                    "old_risk": old_risk,
                    "new_risk": a["risk_level"],
                    "old_count": old_count,
                    "new_count": a["infringement_count"],
                })
        return changes

    def add_copyright_asset(self, data: dict) -> str:
        """新增版权资产"""
        import datetime
        aid = f"CR{len(self._copyright_assets)+1:04d}"
        data["id"] = aid
        data.setdefault("status", "未保护")
        data.setdefault("risk_level", "high")
        data.setdefault("similarity_score", 0.0)
        data.setdefault("infringement_count", 0)
        data.setdefault("platforms", [])
        data.setdefault("last_scan", datetime.date.today().isoformat())
        data.setdefault("license_count", 0)
        data.setdefault("evidence_count", 0)
        data.setdefault("risk_reason", self._generate_risk_reason(data["status"], data["risk_level"], data["similarity_score"]))
        self._copyright_assets.append(data)
        return aid

    def update_copyright_asset(self, aid: str, data: dict) -> bool:
        """更新版权资产"""
        for a in self._copyright_assets:
            if a["id"] == aid:
                a.update(data)
                return True
        return False

    def delete_copyright_asset(self, aid: str) -> bool:
        """删除版权资产"""
        for i, a in enumerate(self._copyright_assets):
            if a["id"] == aid:
                del self._copyright_assets[i]
                return True
        return False

    def export_copyright_evidence(self, aid: str) -> dict:
        """生成单份资产的维权证据包"""
        import datetime
        a = self.get_copyright_asset_by_id(aid)
        if not a:
            return {}
        return {
            "evidence_id": f"EV-{aid}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "asset_id": aid,
            "title": a["title"],
            "owner": a["owner"],
            "registration_no": a.get("registration_no", ""),
            "similarity_score": a.get("similarity_score", 0),
            "infringement_count": a.get("infringement_count", 0),
            "platforms": a.get("platforms", []),
            "generated_at": datetime.datetime.now().isoformat(),
            "blockchain_hash": f"0x{a['id'].encode().hex()}{datetime.datetime.now().strftime('%H%M%S')}",
            "evidence_items": [
                {"type": "作品源文件", "desc": f"{a['title']} 原始创作文件"},
                {"type": "登记证书", "desc": f"登记号 {a.get('registration_no', '暂无')}"},
                {"type": "侵权截图", "desc": f"共 {a.get('infringement_count', 0)} 条疑似侵权链接快照"},
                {"type": "时间戳证书", "desc": "可信时间戳保全"},
            ],
        }


db = MockDatabase()