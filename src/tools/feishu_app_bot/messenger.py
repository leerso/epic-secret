"""
飞书应用机器人 - 消息收发模块
"""
import requests
import json
from typing import Dict, Any, Optional, List
from .auth import FeishuAuth


class FeishuMessenger:
    """飞书消息发送器"""
    
    def __init__(self, auth: FeishuAuth):
        self.auth = auth
    
    def send_text(self, receive_id: str, text: str, receive_id_type: str = "open_id") -> Dict[str, Any]:
        """发送文本消息"""
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        
        content = json.dumps({"text": text}, ensure_ascii=False)
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": content
        }
        
        response = requests.post(
            url,
            params=params,
            headers=self.auth.get_headers(),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def send_rich_text(self, receive_id: str, title: str, elements: List[Dict], 
                      receive_id_type: str = "open_id") -> Dict[str, Any]:
        """发送富文本消息"""
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        
        content = json.dumps({
            "title": title,
            "content": elements
        }, ensure_ascii=False)
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "post",
            "content": content
        }
        
        response = requests.post(
            url,
            params=params,
            headers=self.auth.get_headers(),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def send_card(self, receive_id: str, card: Dict[str, Any], 
                 receive_id_type: str = "open_id") -> Dict[str, Any]:
        """发送卡片消息"""
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {"receive_id_type": receive_id_type}
        
        content = json.dumps(card, ensure_ascii=False)
        
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": content
        }
        
        response = requests.post(
            url,
            params=params,
            headers=self.auth.get_headers(),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def reply_message(self, message_id: str, text: str) -> Dict[str, Any]:
        """回复消息"""
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
        
        content = json.dumps({"text": text}, ensure_ascii=False)
        
        payload = {
            "msg_type": "text",
            "content": content
        }
        
        response = requests.post(
            url,
            headers=self.auth.get_headers(),
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_message(self, message_id: str) -> Dict[str, Any]:
        """获取消息内容"""
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        
        response = requests.get(
            url,
            headers=self.auth.get_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()


class MessageParser:
    """飞书消息解析器"""
    
    @staticmethod
    def parse_text_content(event: Dict[str, Any]) -> Optional[str]:
        """解析文本消息内容"""
        event_data = event.get("event", {})
        message = event_data.get("message", {})
        
        if message.get("message_type") != "text":
            return None
        
        try:
            content = json.loads(message.get("content", "{}"))
            return content.get("text", "")
        except Exception:
            return None
    
    @staticmethod
    def get_sender_open_id(event: Dict[str, Any]) -> Optional[str]:
        """获取发送者open_id"""
        event_data = event.get("event", {})
        sender = event_data.get("sender", {})
        sender_id = sender.get("sender_id", {})
        return sender_id.get("open_id")
    
    @staticmethod
    def get_message_id(event: Dict[str, Any]) -> Optional[str]:
        """获取消息ID"""
        event_data = event.get("event", {})
        message = event_data.get("message", {})
        return message.get("message_id")
    
    @staticmethod
    def is_mention_bot(event: Dict[str, Any], bot_open_id: Optional[str] = None) -> bool:
        """检查是否@了机器人"""
        event_data = event.get("event", {})
        message = event_data.get("message", {})
        mentions = message.get("mentions", [])
        
        if not mentions:
            return False
        
        for mention in mentions:
            if mention.get("name") == "_all":
                return True
            if bot_open_id and mention.get("id", {}).get("open_id") == bot_open_id:
                return True
        
        return False
