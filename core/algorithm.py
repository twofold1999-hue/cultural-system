import math

class ContentEngineAlgorithm:
    """
    数字文化内容传播热度引擎核心算法
    包含基于牛顿冷却定律改良的衰减模型，以及多平台智能排期优化器
    """
    
    # 全局运行时动态衰减系数（支持通过UI交互实时微调）
    _decay_alpha = 0.045 

    @classmethod
    def set_decay_alpha(cls, new_alpha: float):
        """
        [算法控制接口] 动态调整全局传播衰减系数
        """
        cls._decay_alpha = new_alpha

    @classmethod
    def calculate_decay_heat(cls, base_score: float, hours: float, platform_coeff: float) -> float:
        """
        [算法核心逻辑] 基于实时衰减系数计算内容热度曲线
        公式: H(t) = S_base * e^(-alpha * t) * gamma_platform
        """
        decay_term = math.exp(-cls._decay_alpha * hours)
        return round(base_score * decay_term * platform_coeff, 2)

    @classmethod
    def optimize_distribution_schedule(cls, platforms: list, content_attr: dict) -> list:
        """
        [排期协同算法] 根据内容本身的标签属性，计算全渠道的最佳发布时段与初始预测热度
        """
        schedules = []
        tags = content_attr.get("tags", [])
        
        # 基础权重根据标签数量动态联动
        weight = len(tags) * 1.2 if tags else 1.0
        
        for platform in platforms:
            # 针对特定平台和特定文化标签进行交叉系数加权（核心交互映射）
            coeff = 1.0
            if platform == "抖音" and "短视频" in tags:
                coeff = 1.5
            elif platform == "快手" and "娱乐" in tags:
                coeff = 1.3
            elif "国潮" in tags:
                coeff = 1.2  # 文化溢价系数
                
            raw_score = 75.0 * weight
            
            # 预测24小时内的黄金发布时段
            best_hour = 19 if "娱乐" in tags or "短视频" in tags else 10
            
            # 调用上方的热度衰减算法计算初始（0小时）热度值
            predicted_heat = cls.calculate_decay_heat(raw_score, 0, coeff)
            
            schedules.append({
                "platform": platform,
                "best_hour": f"{best_hour}:00",
                "predicted_heat": predicted_heat,
                "confidence": "高" if coeff > 1.2 else "中"
            })
        return schedules