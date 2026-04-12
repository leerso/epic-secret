"""
飞书应用机器人 - 配置模块
"""
import os
import json
from typing import Optional, Dict, Any


class FeishuBotConfig:
    """飞书机器人配置管理"""
    
    DEFAULT_CONFIG = {
        "app_id": "",
        "app_secret": "",
        "verification_token": "",
        "encrypt_key": "",
        "bot_name": "Epic",
        "host": "0.0.0.0",
        "port": 9000,
        "domain": ""
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"),
            "config",
            "feishu_bot_config.json"
        )
        self._config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self._config.update(saved)
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        directory = os.path.dirname(self.config_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
    
    @property
    def app_id(self) -> str:
        return self._config.get("app_id", "")
    
    @app_id.setter
    def app_id(self, value: str):
        self._config["app_id"] = value
    
    @property
    def app_secret(self) -> str:
        return self._config.get("app_secret", "")
    
    @app_secret.setter
    def app_secret(self, value: str):
        self._config["app_secret"] = value
    
    @property
    def verification_token(self) -> str:
        return self._config.get("verification_token", "")
    
    @verification_token.setter
    def verification_token(self, value: str):
        self._config["verification_token"] = value
    
    @property
    def encrypt_key(self) -> str:
        return self._config.get("encrypt_key", "")
    
    @encrypt_key.setter
    def encrypt_key(self, value: str):
        self._config["encrypt_key"] = value
    
    @property
    def bot_name(self) -> str:
        return self._config.get("bot_name", "Epic")
    
    @bot_name.setter
    def bot_name(self, value: str):
        self._config["bot_name"] = value
    
    @property
    def host(self) -> str:
        return self._config.get("host", "0.0.0.0")
    
    @host.setter
    def host(self, value: str):
        self._config["host"] = value
    
    @property
    def port(self) -> int:
        return self._config.get("port", 9000)
    
    @port.setter
    def port(self, value: int):
        self._config["port"] = value
    
    @property
    def domain(self) -> str:
        return self._config.get("domain", "")
    
    @domain.setter
    def domain(self, value: str):
        self._config["domain"] = value
    
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return bool(self.app_id and self.app_secret and self.verification_token)
