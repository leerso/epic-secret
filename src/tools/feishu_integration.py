from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import json
import os
from typing import Optional


# 飞书配置存储路径
FEISHU_CONFIG = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "config", "feishu_config.json")


def _ensure_config_file():
    """确保配置文件存在"""
    directory = os.path.dirname(FEISHU_CONFIG)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    if not os.path.exists(FEISHU_CONFIG):
        with open(FEISHU_CONFIG, 'w', encoding='utf-8') as f:
            json.dump({"webhook_url": "", "configured": False}, f)


def _load_config() -> dict:
    """加载飞书配置"""
    _ensure_config_file()
    try:
        with open(FEISHU_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"webhook_url": "", "configured": False}


def _save_config(config: dict):
    """保存飞书配置"""
    _ensure_config_file()
    with open(FEISHU_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@tool
def setup_feishu_webhook(webhook_url: str) -> str:
    """配置飞书机器人webhook URL。参数: webhook_url - 飞书机器人的webhook地址"""
    ctx = request_context.get() or new_context(method="setup_feishu_webhook")
    
    try:
        if not webhook_url or not webhook_url.startswith("http"):
            return "❌ 请提供有效的webhook URL（需要以http开头）\n\n获取方式：\n1. 在飞书中创建自定义机器人\n2. 复制webhook地址\n3. 在此处粘贴配置"
        
        config = _load_config()
        config["webhook_url"] = webhook_url
        config["configured"] = True
        config["configured_at"] = new_context().timestamp if hasattr(new_context(), 'timestamp') else str(__import__('datetime').datetime.now())
        _save_config(config)
        
        return "✅ 飞书webhook配置成功！\n\n现在可以使用 send_feishu_message 发送消息到飞书了。"
    except Exception as e:
        return f"❌ 配置飞书webhook时出错: {str(e)}"


@tool
def check_feishu_config() -> str:
    """检查飞书配置状态"""
    ctx = request_context.get() or new_context(method="check_feishu_config")
    
    try:
        config = _load_config()
        
        if not config.get("configured"):
            return "📋 飞书配置状态：未配置\n\n请使用 setup_feishu_webhook 工具配置webhook URL。\n\n获取webhook步骤：\n1. 打开飞书群聊\n2. 添加自定义机器人\n3. 复制webhook地址\n4. 在对话框中告诉我：配置飞书webhook [你的URL]"
        
        return f"✅ 飞书配置状态：已配置\n\n📅 配置时间: {config.get('configured_at', '未知')}\n🔗 Webhook: {config.get('webhook_url', '')[:30]}..."
    except Exception as e:
        return f"❌ 检查配置时出错: {str(e)}"


@tool
def send_feishu_message(text: str, title: Optional[str] = "") -> str:
    """发送消息到飞书。参数: text - 消息内容; title - 消息标题（可选）"""
    ctx = request_context.get() or new_context(method="send_feishu_message")
    
    try:
        config = _load_config()
        
        if not config.get("configured") or not config.get("webhook_url"):
            return "❌ 飞书未配置！\n\n请先使用 setup_feishu_webhook 配置webhook URL。"
        
        import requests
        
        webhook_url = config["webhook_url"]
        
        if title:
            # 富文本消息
            payload = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": [
                                [{"tag": "text", "text": text}]
                            ]
                        }
                    }
                }
            }
        else:
            # 纯文本消息
            payload = {
                "msg_type": "text",
                "content": {"text": text}
            }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            return "✅ 消息已发送到飞书！"
        else:
            return f"❌ 发送失败: {result.get('msg', '未知错误')}"
    except ImportError:
        return "❌ requests库未安装，无法发送飞书消息"
    except Exception as e:
        return f"❌ 发送飞书消息时出错: {str(e)}\n\n请检查webhook URL是否正确，或使用 check_feishu_config 查看配置状态。"


@tool
def send_reminder_to_feishu(reminder_title: str, reminder_content: str) -> str:
    """将提醒发送到飞书。参数: reminder_title - 提醒标题; reminder_content - 提醒内容"""
    ctx = request_context.get() or new_context(method="send_reminder_to_feishu")
    
    try:
        config = _load_config()
        
        if not config.get("configured"):
            return "❌ 飞书未配置，无法发送提醒。\n请先配置飞书webhook。"
        
        full_text = f"⏰ 提醒: {reminder_title}\n\n{reminder_content}\n\n---\n由Epic助手发送"
        
        return send_feishu_message.invoke({"text": full_text, "title": "🔔 新提醒"})
    except Exception as e:
        return f"❌ 发送提醒到飞书时出错: {str(e)}"
