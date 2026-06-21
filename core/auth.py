import hashlib
import time
from database.mock_db import db

class AuthenticationCore:
    """
    负责系统鉴权与注册的核心逻辑
    移除了 UI 交互，纯逻辑处理
    """
    
    # 鉴权尝试次数限制，防止暴力破解
    _login_attempts = {}
    _MAX_ATTEMPTS = 5
    _LOCKOUT_TIME = 60 * 5 # 5分钟

    @classmethod
    def process_login(cls, username, password):
        """
        执行完整登录流程
        """
        if cls.is_locked_out(username):
            return False, None, f"账户 {username} 已被临时锁定。"

        # 1. 查找用户
        # 模拟哈希校验过程
        # password_hash = hashlib.sha256(password.encode()).hexdigest()
        # success, role = db.authenticate_secure(username, password_hash)
        
        # 暂时使用 mockdb 的简单登录
        success, role = db.authenticate(username, password)
        
        # 2. 更新尝试次数
        cls._record_attempt(username, success)
        
        if success:
            return True, role, "登录成功"
        else:
            return False, None, "凭证不正确，请重新输入。"

    @classmethod
    def process_registration(cls, username, password, role="Editor"):
        """
        执行完整注册流程
        """
        if len(password) < 8:
            return False, "密码长度必须大于8个字符"
            
        # password_hash = hashlib.sha256(password.encode()).hexdigest()
        # db.register_user_secure(username, password_hash, role)
        
        return db.register_user(username, password, role)

    @classmethod
    def is_locked_out(cls, username):
        """
        检查用户是否被锁定
        """
        if username not in cls._login_attempts:
            return False
            
        attempt_info = cls._login_attempts[username]
        if attempt_info["consecutive_failures"] >= cls._MAX_ATTEMPTS:
            if time.time() - attempt_info["last_failure_time"] < cls._LOCKOUT_TIME:
                return True
            else:
                # 锁定时间已过，重置尝试次数
                attempt_info["consecutive_failures"] = 0
        return False

    @classmethod
    def _record_attempt(cls, username, success):
        """
        记录登录尝试，更新失败计数
        """
        current_time = time.time()
        if username not in cls._login_attempts:
            cls._login_attempts[username] = {"consecutive_failures": 0, "last_failure_time": 0}
            
        if success:
            cls._login_attempts[username]["consecutive_failures"] = 0
        else:
            cls._login_attempts[username]["consecutive_failures"] += 1
            cls._login_attempts[username]["last_failure_time"] = current_time