from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import json
import os
from datetime import datetime
from typing import Optional, List, Dict


# 提醒数据存储路径
REMINDER_FILE = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "reminders.json")


def _ensure_reminder_file():
    """确保提醒文件和目录存在"""
    directory = os.path.dirname(REMINDER_FILE)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    if not os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)


def _load_reminders() -> List[Dict]:
    """加载提醒列表"""
    _ensure_reminder_file()
    try:
        with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def _save_reminders(reminders: List[Dict]):
    """保存提醒列表"""
    _ensure_reminder_file()
    with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


@tool
def add_reminder(title: str, description: Optional[str] = "", reminder_time: Optional[str] = "", priority: Optional[str] = "medium") -> str:
    """添加一个新的提醒。参数: title - 提醒标题; description - 提醒描述（可选）; reminder_time - 提醒时间，格式: YYYY-MM-DD HH:MM（可选）; priority - 优先级: low/medium/high，默认为medium"""
    ctx = request_context.get() or new_context(method="add_reminder")
    
    try:
        reminders = _load_reminders()
        
        # 创建新提醒
        reminder = {
            "id": str(len(reminders) + 1),
            "title": title,
            "description": description,
            "reminder_time": reminder_time,
            "priority": priority,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "completed": False
        }
        
        reminders.append(reminder)
        _save_reminders(reminders)
        
        return f"提醒添加成功！\nID: {reminder['id']}\n标题: {title}\n优先级: {priority}\n{'提醒时间: ' + reminder_time if reminder_time else ''}"
    except Exception as e:
        return f"添加提醒时出错: {str(e)}"


@tool
def list_reminders(show_completed: Optional[bool] = False) -> str:
    """列出所有提醒。参数: show_completed - 是否显示已完成的提醒，默认为False"""
    ctx = request_context.get() or new_context(method="list_reminders")
    
    try:
        reminders = _load_reminders()
        
        if not reminders:
            return "暂无提醒"
        
        # 过滤提醒
        if not show_completed:
            reminders = [r for r in reminders if not r.get("completed", False)]
        
        if not reminders:
            return "暂无待处理提醒"
        
        # 排序：按优先级和时间
        priority_order = {"high": 0, "medium": 1, "low": 2}
        reminders.sort(key=lambda x: (priority_order.get(x.get("priority", "medium"), 999), x.get("created_at", "")))
        
        result = "提醒列表:\n\n"
        for r in reminders:
            status = "✅" if r.get("completed", False) else "⏰"
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(r.get("priority", "medium"), "⚪")
            
            result += f"{status} {priority_emoji} [ID: {r['id']}] {r['title']}\n"
            if r.get("description"):
                result += f"   {r['description']}\n"
            if r.get("reminder_time"):
                result += f"   ⏰ 提醒时间: {r['reminder_time']}\n"
            result += f"   创建时间: {r.get('created_at', '未知')}\n\n"
        
        return result
    except Exception as e:
        return f"获取提醒列表时出错: {str(e)}"


@tool
def complete_reminder(reminder_id: str) -> str:
    """将提醒标记为已完成。参数: reminder_id - 提醒ID"""
    ctx = request_context.get() or new_context(method="complete_reminder")
    
    try:
        reminders = _load_reminders()
        
        found = False
        for r in reminders:
            if r["id"] == reminder_id:
                r["completed"] = True
                r["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                found = True
                break
        
        if not found:
            return f"错误：找不到ID为 {reminder_id} 的提醒"
        
        _save_reminders(reminders)
        return f"提醒已标记为完成！\nID: {reminder_id}"
    except Exception as e:
        return f"更新提醒时出错: {str(e)}"


@tool
def delete_reminder(reminder_id: str) -> str:
    """删除提醒。参数: reminder_id - 提醒ID"""
    ctx = request_context.get() or new_context(method="delete_reminder")
    
    try:
        reminders = _load_reminders()
        
        reminder_to_delete = None
        for r in reminders:
            if r["id"] == reminder_id:
                reminder_to_delete = r
                break
        
        if not reminder_to_delete:
            return f"错误：找不到ID为 {reminder_id} 的提醒"
        
        reminders = [r for r in reminders if r["id"] != reminder_id]
        _save_reminders(reminders)
        
        return f"提醒已删除！\nID: {reminder_id}\n标题: {reminder_to_delete['title']}"
    except Exception as e:
        return f"删除提醒时出错: {str(e)}"
