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


def _generate_summary(content: str, max_length: int = 50) -> str:
    """生成内容摘要"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + "..."


@tool
def save_memory_v2(title: str, content: str, importance: Optional[str] = "medium", 
                   category: Optional[str] = "general", keywords: Optional[str] = "") -> str:
    """【优化版】保存一条记忆到长期记忆库（支持标题和摘要）。参数: title - 记忆标题/简短描述; content - 详细记忆内容; importance - 重要程度: low/medium/high/critical，默认为medium; category - 分类标签，如: personal, work, project, preference等，默认为general; keywords - 关键词，用逗号分隔，便于检索"""
    ctx = request_context.get() or new_context(method="save_memory_v2")
    
    try:
        memories = _load_memories()
        
        # 处理关键词
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        
        # 生成摘要
        summary = _generate_summary(content, max_length=80)
        
        # 创建新记忆
        memory = {
            "id": str(len(memories) + 1),
            "title": title,
            "summary": summary,
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
        
        return f"记忆保存成功！\n🆔 ID: {memory['id']}\n{importance_emoji} 重要度: {importance}\n📂 分类: {category}\n📌 标题: {title}\n📝 摘要: {summary}"
    except Exception as e:
        return f"保存记忆时出错: {str(e)}"


@tool
def search_memories_compact(query: Optional[str] = "", category: Optional[str] = "", 
                          importance: Optional[str] = "", page: int = 1, 
                          page_size: int = 10) -> str:
    """【优化版】轻量搜索记忆（只返回标题和摘要，支持分页）。参数: query - 搜索关键词，可选; category - 按分类筛选，可选; importance - 按重要度筛选，可选; page - 页码，从1开始，默认1; page_size - 每页数量，默认10"""
    ctx = request_context.get() or new_context(method="search_memories_compact")
    
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
                title = m.get("title", "").lower()
                content = m.get("content", "").lower()
                keywords = [k.lower() for k in m.get("keywords", [])]
                if query_lower in title or query_lower in content or query_lower in keywords:
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
        
        # 分页计算
        total = len(results)
        total_pages = (total + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = results[start_idx:end_idx]
        
        # 更新访问次数（只更新当前页的）
        memory_dict = {m["id"]: m for m in memories}
        for m in page_results:
            memory_dict[m["id"]]["access_count"] = memory_dict[m["id"]].get("access_count", 0) + 1
            memory_dict[m["id"]]["last_accessed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        _save_memories(list(memory_dict.values()))
        
        # 生成紧凑型输出（只有标题和摘要）
        result_text = f"找到 {total} 条记忆 (第 {page}/{total_pages} 页):\n\n"
        for m in page_results:
            importance_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(m.get("importance", "medium"), "⚪")
            
            result_text += f"{importance_emoji} [ID: {m['id']}] {m.get('category', 'general')}\n"
            result_text += f"   📌 {m.get('title', '无标题')}\n"
            result_text += f"   💡 {m.get('summary', '')}\n\n"
        
        if total_pages > 1:
            result_text += f"---\n提示: 使用 get_memory_detail 查看完整内容，修改 page 参数翻页\n"
        
        return result_text
    except Exception as e:
        return f"搜索记忆时出错: {str(e)}"


@tool
def get_memory_detail(memory_id: str) -> str:
    """【优化版】获取单条记忆的完整详情。参数: memory_id - 记忆ID"""
    ctx = request_context.get() or new_context(method="get_memory_detail")
    
    try:
        memories = _load_memories()
        
        memory = None
        for m in memories:
            if m["id"] == memory_id:
                memory = m
                break
        
        if not memory:
            return f"错误：找不到ID为 {memory_id} 的记忆"
        
        # 更新访问次数
        memory["access_count"] = memory.get("access_count", 0) + 1
        memory["last_accessed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save_memories(memories)
        
        importance_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(memory.get("importance", "medium"), "⚪")
        
        result = f"记忆详情 [ID: {memory['id']}]\n"
        result += f"{importance_emoji} 重要度: {memory.get('importance', 'medium')}\n"
        result += f"📂 分类: {memory.get('category', 'general')}\n"
        result += f"📌 标题: {memory.get('title', '无标题')}\n"
        if memory.get("keywords"):
            result += f"🏷️ 关键词: {', '.join(memory['keywords'])}\n"
        result += f"📅 创建: {memory.get('created_at', '未知')}\n"
        result += f"👁️ 访问: {memory.get('access_count', 0)}次\n"
        result += "=" * 50 + "\n"
        result += f"📝 完整内容:\n{memory.get('content', '')}"
        
        return result
    except Exception as e:
        return f"获取记忆详情时出错: {str(e)}"


@tool
def get_memory_stats() -> str:
    """获取记忆库统计信息"""
    ctx = request_context.get() or new_context(method="get_memory_stats")
    
    try:
        memories = _load_memories()
        
        if not memories:
            return "长期记忆库为空"
        
        # 分类统计
        categories = {}
        for m in memories:
            cat = m.get("category", "general")
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        # 重要度统计
        importance_stats = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for m in memories:
            imp = m.get("importance", "medium")
            if imp in importance_stats:
                importance_stats[imp] += 1
        
        # 访问统计
        total_accesses = sum(m.get("access_count", 0) for m in memories)
        top_accessed = sorted(memories, key=lambda x: -x.get("access_count", 0))[:5]
        
        result = "📊 记忆库统计\n"
        result += "=" * 40 + "\n"
        result += f"📚 总记忆数: {len(memories)}\n"
        result += f"👁️ 总访问次数: {total_accesses}\n\n"
        
        result += "📂 分类分布:\n"
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            result += f"   {cat}: {count} 条\n"
        
        result += "\n🎯 重要度分布:\n"
        imp_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        for imp, count in importance_stats.items():
            if count > 0:
                result += f"   {imp_emoji[imp]} {imp}: {count} 条\n"
        
        if top_accessed:
            result += "\n🔥 最常访问的记忆:\n"
            for m in top_accessed:
                if m.get("access_count", 0) > 0:
                    result += f"   [ID:{m['id']}] {m.get('title', '无标题')} ({m.get('access_count', 0)}次)\n"
        
        return result
    except Exception as e:
        return f"获取统计信息时出错: {str(e)}"
