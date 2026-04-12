#!/bin/bash
# 飞书机器人快速启动脚本（测试用）

echo "🚀 Epic飞书机器人 - 测试启动"
echo "================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查配置文件
if [ ! -f "config/feishu_bot_config.json" ]; then
    echo "⚠️  配置文件不存在，从示例复制..."
    if [ -f "config/feishu_bot_config.example.json" ]; then
        cp config/feishu_bot_config.example.json config/feishu_bot_config.json
        echo "✅ 已创建配置文件，请编辑 config/feishu_bot_config.json"
        echo "   填入你的飞书应用凭证后重新运行此脚本"
        exit 0
    else
        echo "❌ 未找到示例配置文件"
        exit 1
    fi
fi

echo "✅ 启动机器人服务..."
echo "📍 监听地址: http://0.0.0.0:9000"
echo "🔗 回调地址: http://feishu.epicarena.cn/webhook/event"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务
python3 -m tools.feishu_app_bot.server
