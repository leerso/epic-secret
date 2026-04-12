from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


# 记忆数据存储路径
MEMORY_FILE = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "long_term_memory.json")


def _ensure_memory_file():
    """确保记忆文件和目录存在"""
    directory = os.path.dirname(MEMORY_FILE)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)


def _load_memories() -> List[Dict]:
    """加载记忆列表"""
    _ensure_memory_file()
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def _save_memories(memories: List[Dict]):
    """保存记忆列表"""
    _ensure_memory_file()
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


@tool
def save_memory(content: str, importance: Optional[str] = "medium", category: Optional[str] = "general", keywords: Optional[str] = "") -> str:
    """保存一条记忆到长期记忆库。参数: content - 记忆内容; importance - 重要程度: low/medium/high/critical，默认为medium; category - 分类标签，如: personal, work, project, preference等，默认为general; keywords - 关键词，用逗号分隔，便于检索"""
    ctx = request_context.get() or new_context(method="save_memory")
    
    try:
        memories = _load_memories()
        
        # 处理关键词
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        
        # 创建新记忆
        memory = {
            "id": str(len(memories) + 1),
            "content": content,
            "importance": importance,
            "category": category,
            "keywords": keyword_list,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "access_count": 0,
            "last_accessed": None
        }
        
        memories.append(memory)
        _save_memories(memories)
        
        importance_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(importance, "⚪")
        
        return f"记忆保存成功！\n🆔 ID: {memory['id']}\n{importance_emoji} 重要度: {importance}\n📂 分类: {category}\n📝 内容: {content[:100]}{'...' if len(content) > 100 else ''}"
    except Exception as e:
        return f"保存记忆时出错: {str(e)}"


@tool
def search_memories(query: Optional[str] = "", category: Optional[str] = "", importance: Optional[str] = "", limit: Optional[int] = 10) -> str:
    """搜索长期记忆。参数: query - 搜索关键词，可选; category - 按分类筛选，可选; importance - 按重要度筛选，可选; limit - 返回结果数量限制，默认10条"""
    ctx = request_context.get() or new_context(method="search_memories")
    
    try:
        memories = _load_memories()
        
        if not memories:
            return "长期记忆库为空"
        
        results = memories
        
        # 按分类筛选
        if category:
            results = [m for m in results if m.get("category", "").lower() == category.lower()]
        
        # 按重要度筛选
        if importance:
            results = [m for m in results if m.get("importance", "") == importance]
        
        # 按关键词搜索
        if query:
            query_lower = query.lower()
            filtered = []
            for m in results:
                content = m.get("content", "").lower()
                keywords = [k.lower() for k in m.get("keywords", [])]
                if query_lower in content or query_lower in keywords:
                    filtered.append(m)
            results = filtered
        
        if not results:
            return "未找到匹配的记忆"
        
        # 排序：按重要度和访问次数
        importance_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        results.sort(key=lambda x: (
            importance_order.get(x.get("importance", "medium"), 999),
            -x.get("access_count", 0),
            x.get("created_at", "")
        ))
        
        # 限制数量
        results = results[:limit]
        
        # 更新访问次数
        for m in results:
            m["access_count"] = m.get("access_count", 0) + 1
            m["last_accessed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        _save_memories(memories)
        
        result_text = f"找到 {len(results)} 条记忆:\n\n"
        for m in results:
            importance_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(m.get("importance", "medium"), "⚪")
            
            result_text += f"{importance_emoji} [ID: {m['id']}] {m.get('category', 'general')}\n"
            result_text += f"   📝 {m['content']}\n"
            if m.get("keywords"):
                result_text += f"   🏷️ {', '.join(m['keywords'])}\n"
            result_text += f"   📅 创建: {m.get('created_at', '未知')} | 👁️ 访问: {m.get('access_count', 0)}次\n\n"
        
        return result_text
    except Exception as e:
        return f"搜索记忆时出错: {str(e)}"


@tool
def list_all_categories() -> str:
    """列出所有记忆分类"""
    ctx = request_context.get() or new_context(method="list_all_categories")
    
    try:
        memories = _load_memories()
        
        if not memories:
            return "长期记忆库为空"
        
        categories = {}
        for m in memories:
            cat = m.get("category", "general")
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        result = "记忆分类统计:\n\n"
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            result += f"📂 {cat}: {count} 条记忆\n"
        
        return result
    except Exception as e:
        return f"获取分类时出错: {str(e)}"


@tool
def delete_memory(memory_id: str) -> str:
    """删除一条记忆。参数: memory_id - 记忆ID"""
    ctx = request_context.get() or new_context(method="delete_memory")
    
    try:
        memories = _load_memories()
        
        memory_to_delete = None
        for m in memories:
            if m["id"] == memory_id:
                memory_to_delete = m
                break
        
        if not memory_to_delete:
            return f"错误：找不到ID为 {memory_id} 的记忆"
        
        memories = [m for m in memories if m["id"] != memory_id]
        _save_memories(memories)
        
        return f"记忆已删除！\nID: {memory_id}\n内容: {memory_to_delete['content'][:100]}{'...' if len(memory_to_delete['content']) > 100 else ''}"
    except Exception as e:
        return f"删除记忆时出错: {str(e)}"


@tool
def get_relevant_memories(context: str, limit: Optional[int] = 5) -> str:
    """根据当前上下文获取相关记忆（智能检索）。参数: context - 当前对话或上下文内容; limit - 返回记忆数量，默认5条"""
    ctx = request_context.get() or new_context(method="get_relevant_memories")
    
    try:
        memories = _load_memories()
        
        if not memories:
            return "长期记忆库为空"
        
        # 简单的关键词匹配（实际项目中可以使用向量检索）
        context_lower = context.lower()
        scored_memories = []
        
        for m in memories:
            score = 0
            content = m.get("content", "").lower()
            keywords = [k.lower() for k in m.get("keywords", [])]
            
            # 内容匹配
            for word in context_lower.split():
                if len(word) > 2 and word in content:
                    score += 2
                if len(word) > 2 and word in keywords:
                    score += 3
            
            # 重要度加成
            importance_bonus = {"critical": 10, "high": 5, "medium": 2, "low": 0}
            score += importance_bonus.get(m.get("importance", "medium"), 0)
            
            # 访问次数加成
            score += min(m.get("access_count", 0), 5)
            
            if score > 0:
                scored_memories.append((score, m))
        
        if not scored_memories:
            return "未找到相关记忆"
        
        # 按分数排序
        scored_memories.sort(key=lambda x: (-x[0], x[1].get("created_at", "")))
        results = [m for _, m in scored_memories[:limit]]
        
        # 更新访问次数
        memory_dict = {m["id"]: m for m in memories}
        for m in results:
            memory_dict[m["id"]]["access_count"] = memory_dict[m["id"]].get("access_count", 0) + 1
            memory_dict[m["id"]]["last_accessed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        _save_memories(list(memory_dict.values()))
        
        result_text = f"找到 {len(results)} 条相关记忆:\n\n"
        for m in results:
            importance_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(m.get("importance", "medium"), "⚪")
            
            result_text += f"{importance_emoji} [ID: {m['id']}] {m.get('category', 'general')}\n"
            result_text += f"   📝 {m['content']}\n\n"
        
        return result_text
    except Exception as e:
        return f"获取相关记忆时出错: {str(e)}"
