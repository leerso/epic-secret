"""
飞书应用机器人 - 主服务
"""
import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# 导入Agent相关模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from agents.agent import build_agent
from langchain_core.messages import HumanMessage
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

from .auth import FeishuAuth
from .config import FeishuBotConfig
from .event_handler import FeishuEventValidator, FeishuEventHandler
from .messenger import FeishuMessenger, MessageParser


class FeishuBotServer:
    """飞书机器人主服务"""
    
    def __init__(self, config: Optional[FeishuBotConfig] = None):
        self.config = config or FeishuBotConfig()
        self.auth: Optional[FeishuAuth] = None
        self.validator: Optional[FeishuEventValidator] = None
        self.event_handler: Optional[FeishuEventHandler] = None
        self.messenger: Optional[FeishuMessenger] = None
        self.agent = None
        self.app: Optional[FastAPI] = None
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        if self.config.is_valid():
            self.auth = FeishuAuth(self.config.app_id, self.config.app_secret)
            self.validator = FeishuEventValidator(
                self.config.verification_token,
                self.config.encrypt_key
            )
            self.event_handler = FeishuEventHandler(self.validator)
            self.messenger = FeishuMessenger(self.auth)
            
            # 注册事件处理器
            self.event_handler.register_handler("im.message.receive_v1", self._handle_message)
    
    def load_agent(self):
        """加载Epic Agent"""
        if not self.agent:
            ctx = new_context(method="feishu_bot")
            self.agent = build_agent(ctx)
        return self.agent
    
    async def _call_agent(self, user_input: str, thread_id: str) -> str:
        """调用Epic Agent"""
        try:
            agent = self.load_agent()
            ctx = new_context(method="agent_call")
            
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            # 调用Agent
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config
            )
            
            # 获取最后一条消息
            messages = result.get("messages", [])
            if messages:
                return messages[-1].content
            
            return "抱歉，我现在无法回复。"
            
        except Exception as e:
            print(f"调用Agent出错: {e}")
            return f"处理出错了: {str(e)}"
    
    def _handle_message(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理收到的消息事件"""
        try:
            # 解析消息
            text = MessageParser.parse_text_content(event)
            sender_open_id = MessageParser.get_sender_open_id(event)
            message_id = MessageParser.get_message_id(event)
            
            if not text or not sender_open_id:
                return None
            
            # 清理@提及
            if "@_user" in text or "@_all" in text:
                import re
                text = re.sub(r'@_\w+', '', text).strip()
            
            if not text:
                return None
            
            print(f"收到消息 - 发送者: {sender_open_id}, 内容: {text}")
            
            # 异步调用Agent并回复
            asyncio.create_task(self._process_and_reply(sender_open_id, message_id, text))
            
            return None
            
        except Exception as e:
            print(f"处理消息出错: {e}")
            return None
    
    async def _process_and_reply(self, open_id: str, message_id: str, text: str):
        """处理消息并回复"""
        try:
            # 调用Agent
            response = await self._call_agent(text, f"feishu_{open_id}")
            
            # 回复消息
            if self.messenger:
                self.messenger.reply_message(message_id, response)
                print(f"已回复: {response[:50]}...")
            
        except Exception as e:
            print(f"回复消息出错: {e}")
            if self.messenger:
                try:
                    self.messenger.reply_message(message_id, f"抱歉，处理出错了: {str(e)}")
                except Exception:
                    pass
    
    def create_app(self) -> FastAPI:
        """创建FastAPI应用"""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动时初始化
            self.load_agent()
            print("🚀 飞书机器人服务启动成功！")
            yield
            # 关闭时清理
            print("👋 飞书机器人服务已停止")
        
        self.app = FastAPI(lifespan=lifespan)
        
        @self.app.post("/webhook/event")
        async def webhook(request: Request):
            """飞书事件回调"""
            try:
                body = await request.json()
                print(f"收到事件: {body.get('header', {}).get('event_type', 'unknown')}")
                
                if not self.event_handler:
                    raise HTTPException(status_code=500, detail="服务未初始化")
                
                result = self.event_handler.handle(body)
                
                if result:
                    return JSONResponse(content=result)
                
                return JSONResponse(content={"code": 0, "msg": "success"})
                
            except Exception as e:
                print(f"处理事件出错: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {"status": "ok", "bot": self.config.bot_name}
        
        return self.app
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """启动服务"""
        host = host or self.config.host
        port = port or self.config.port
        
        app = self.create_app()
        
        print(f"🤖 启动飞书机器人: {self.config.bot_name}")
        print(f"📍 监听地址: {host}:{port}")
        if self.config.domain:
            print(f"🌐 回调地址: https://{self.config.domain}/webhook/event")
        print("-" * 50)
        
        uvicorn.run(app, host=host, port=port)


def main():
    """主函数"""
    config = FeishuBotConfig()
    
    if not config.is_valid():
        print("⚠️  配置不完整，请先填写配置文件:")
        print(f"   {config.config_path}")
        print("")
        print("需要配置的字段:")
        print("  - app_id: 飞书应用ID")
        print("  - app_secret: 飞书应用密钥")
        print("  - verification_token: 验证令牌")
        print("  - encrypt_key (可选): 加密密钥")
        print("  - domain (可选): 你的域名")
        return
    
    server = FeishuBotServer(config)
    server.run()


if __name__ == "__main__":
    main()
