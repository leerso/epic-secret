"""
飞书应用机器人 - 认证模块
"""
import os
import json
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class FeishuAuth:
    """飞书应用认证管理"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: Optional[str] = None
        self._token_expire_time: float = 0
    
    def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """获取tenant_access_token，带缓存机制"""
        now = time.time()
        
        # 如果token还有效且不强制刷新，直接返回
        if not force_refresh and self._tenant_access_token and now < self._token_expire_time - 60:
            return self._tenant_access_token
        
        # 请求新token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            raise Exception(f"获取tenant_access_token失败: {data}")
        
        self._tenant_access_token = data["tenant_access_token"]
        expire = data.get("expire", 7200)
        self._token_expire_time = now + expire
        
        return self._tenant_access_token
    
    def get_headers(self) -> Dict[str, str]:
        """获取带认证的请求头"""
        token = self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
