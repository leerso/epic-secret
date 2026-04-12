"""
飞书应用机器人 - 事件处理模块
"""
import hashlib
import base64
import json
from typing import Dict, Any, Optional, Callable
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FeishuEventValidator:
    """飞书事件验证器"""
    
    def __init__(self, verification_token: str, encrypt_key: str = ""):
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
    
    def verify_token(self, request_token: str) -> bool:
        """验证Verification Token"""
        return request_token == self.verification_token
    
    def decrypt(self, encrypt: str) -> Dict[str, Any]:
        """解密飞书加密数据"""
        if not self.encrypt_key:
            raise Exception("encrypt_key未配置，无法解密")
        
        # 生成密钥
        key = hashlib.sha256(self.encrypt_key.encode()).digest()
        
        # Base64解码
        decoded = base64.b64decode(encrypt)
        
        # 提取nonce和密文
        nonce = decoded[:12]
        ciphertext = decoded[12:]
        
        # AES-GCM解密
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return json.loads(plaintext.decode('utf-8'))
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理飞书事件请求"""
        # 检查是否加密
        if "encrypt" in request_data:
            request_data = self.decrypt(request_data["encrypt"])
        
        # 验证token
        token = request_data.get("token") or request_data.get("header", {}).get("token")
        if token and not self.verify_token(token):
            raise Exception("Verification Token验证失败")
        
        # 处理URL验证请求
        if request_data.get("type") == "url_verification":
            return {
                "challenge": request_data.get("challenge")
            }
        
        return request_data


class FeishuEventHandler:
    """飞书事件处理器"""
    
    def __init__(self, validator: FeishuEventValidator):
        self.validator = validator
        self._handlers: Dict[str, Callable] = {}
    
    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self._handlers[event_type] = handler
    
    def handle(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理事件"""
        # 处理请求
        processed = self.validator.process_request(request_data)
        
        # 检查是否是URL验证响应
        if "challenge" in processed:
            return processed
        
        # 获取事件类型
        header = processed.get("header", {})
        event_type = header.get("event_type")
        
        if not event_type:
            return None
        
        # 调用对应的处理器
        if event_type in self._handlers:
            return self._handlers[event_type](processed)
        
        return None
