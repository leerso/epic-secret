from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# 记忆数据存储路径
MEMORY_FILE = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "long_term_memory.json")
ARCHIVE_FILE = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), "assets", "memory_archive.json")


def _ensure_file(file_path: str):
    """确保文件和目录存在"""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f)


def _load_memories(file_path: str = MEMORY_FILE) -> List[Dict]:
    """加载记忆列表"""
    _ensure_file(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def _save_memories(memories: List[Dict], file_path: str = MEMORY_FILE):
    """保存记忆列表"""
    _ensure_file(file_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def _get_memory_size(memories: List[Dict]) -> int:
    """估算记忆库大小（字节）"""
    return len(json.dumps(memories, ensure_ascii=False))


@tool
def analyze_storage_status() -> str:
    """分析存储空间使用状态，返回统计信息和优化建议"""
    ctx = request_context.get() or new_context(method="analyze_storage_status")
    
    try:
        memories = _load_memories()
        archives = _load_memories(ARCHIVE_FILE) if os.path.exists(ARCHIVE_FILE) else []
        
        total_size = _get_memory_size(memories)
        archive_size = _get_memory_size(archives)
        
        # 按重要度统计
        importance_stats = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for m in memories:
            imp = m.get("importance", "medium")
            if imp in importance_stats:
                importance_stats[imp] += 1
        
        # 按时间统计（判断是否超过6个月）
        six_months_ago = datetime.now() - timedelta(days=180)
        old_memories = []
        for m in memories:
            created_at = m.get("created_at", "")
            try:
                created_date = datetime.strptime(created_at.split()[0], "%Y-%m-%d")
                if created_date < six_months_ago:
                    old_memories.append(m)
            except:
                pass
        
        # 访问频率统计
        low_access = [m for m in memories if m.get("access_count", 0) < 2]
        
        result = "📊 存储空间分析报告\n"
        result += "=" * 50 + "\n\n"
        result += f"📚 当前记忆数: {len(memories)} 条\n"
        result += f"📦 归档记忆数: {len(archives)} 条\n"
        result += f"💾 当前库大小: ~{total_size / 1024:.1f} KB\n"
        result += f"📦 归档库大小: ~{archive_size / 1024:.1f} KB\n\n"
        
        result += "🎯 重要度分布:\n"
        imp_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        for imp, count in importance_stats.items():
            result += f"   {imp_emoji[imp]} {imp}: {count} 条\n"
        
        result += "\n🔍 优化建议:\n"
        
        suggestions = []
        if len(old_memories) > 0:
            suggestions.append(f"  ⏰ 有 {len(old_memories)} 条记忆超过6个月，可考虑归档")
        
        if len(low_access) > 3:
            suggestions.append(f"  👁️ 有 {len(low_access)} 条记忆访问次数<2，可考虑摘要化")
        
        if importance_stats["low"] > 5:
            suggestions.append(f"  🟢 有 {importance_stats['low']} 条low重要度记忆，可优先归档")
        
        if total_size > 500 * 1024:  # 超过500KB
            suggestions.append(f"  ⚠️ 存储空间较大(>{total_size/1024:.0f}KB)，建议优化")
        
        if not suggestions:
            result += "   ✨ 当前状态良好，无需优化\n"
        else:
            for s in suggestions:
                result += f"{s}\n"
        
        return result
    except Exception as e:
        return f"分析存储空间时出错: {str(e)}"


@tool
def optimize_storage(dry_run: Optional[bool] = True) -> str:
    """执行存储空间优化（方案B：智能压缩+重要度筛选）。参数: dry_run - 是否为试运行，True表示只显示计划不执行，False表示真正执行"""
    ctx = request_context.get() or new_context(method="optimize_storage")
    
    try:
        memories = _load_memories()
        
        if not memories:
            return "记忆库为空，无需优化"
        
        # 优化策略
        six_months_ago = datetime.now() - timedelta(days=180)
        one_year_ago = datetime.now() - timedelta(days=365)
        
        to_archive = []  # 要归档的记忆
        to_summarize = []  # 要摘要化的记忆
        to_keep = []  # 保留的记忆
        
        for m in memories:
            importance = m.get("importance", "medium")
            access_count = m.get("access_count", 0)
            created_at = m.get("created_at", "")
            
            # 时间判断
            is_old = False
            is_very_old = False
            try:
                created_date = datetime.strptime(created_at.split()[0], "%Y-%m-%d")
                if created_date < six_months_ago:
                    is_old = True
                if created_date < one_year_ago:
                    is_very_old = True
            except:
                pass
            
            # 决策逻辑
            if importance == "critical":
                # 重要记忆永久保留
                to_keep.append(m)
            elif importance == "high":
                # 高重要度，除非非常老且访问少
                if is_very_old and access_count < 3:
                    to_archive.append(m)
                else:
                    to_keep.append(m)
            elif importance == "medium":
                # 中等重要度，老的或访问少的归档
                if is_old or access_count < 2:
                    to_archive.append(m)
                else:
                    to_keep.append(m)
            else:  # low
                # 低重要度，优先处理
                if is_old or access_count < 1:
                    to_archive.append(m)
                elif len(m.get("content", "")) > 200:
                    # 长内容摘要化
                    to_summarize.append(m)
                else:
                    to_keep.append(m)
        
        result = "📋 存储优化计划\n"
        result += "=" * 50 + "\n\n"
        result += f"📊 优化前: {len(memories)} 条\n"
        result += f"✅ 保留: {len(to_keep)} 条\n"
        result += f"📦 归档: {len(to_archive)} 条\n"
        result += f"📝 摘要化: {len(to_summarize)} 条\n\n"
        
        if to_archive:
            result += "📦 拟归档的记忆:\n"
            for m in to_archive[:5]:  # 只显示前5条
                result += f"   - [ID:{m.get('id')}] {m.get('title', '无标题')[:30]}...\n"
            if len(to_archive) > 5:
                result += f"   ... 还有 {len(to_archive)-5} 条\n"
            result += "\n"
        
        if dry_run:
            result += "⚠️  这是试运行，未实际执行。\n"
            result += "如需执行，请调用: optimize_storage(dry_run=False)\n"
            return result
        
        # 实际执行
        # 1. 归档
        if to_archive:
            archives = _load_memories(ARCHIVE_FILE) if os.path.exists(ARCHIVE_FILE) else []
            archives.extend(to_archive)
            _save_memories(archives, ARCHIVE_FILE)
        
        # 2. 摘要化（简化实现，实际可用LLM生成）
        for m in to_summarize:
            content = m.get("content", "")
            if len(content) > 100:
                m["original_content"] = content
                m["content"] = content[:100] + "..."
                m["summarized"] = True
            to_keep.append(m)
        
        # 3. 保存
        _save_memories(to_keep)
        
        result += "✅ 优化执行完成！\n"
        result += f"📦 已归档 {len(to_archive)} 条到 memory_archive.json\n"
        result += f"📝 已摘要化 {len(to_summarize)} 条\n"
        result += f"✅ 最终保留 {len(to_keep)} 条\n"
        
        return result
    except Exception as e:
        return f"优化存储时出错: {str(e)}"


@tool
def restore_from_archive(memory_id: Optional[str] = "", restore_all: Optional[bool] = False) -> str:
    """从归档恢复记忆。参数: memory_id - 要恢复的记忆ID; restore_all - 是否恢复所有归档记忆"""
    ctx = request_context.get() or new_context(method="restore_from_archive")
    
    try:
        if not os.path.exists(ARCHIVE_FILE):
            return "归档文件不存在"
        
        memories = _load_memories()
        archives = _load_memories(ARCHIVE_FILE)
        
        if not archives:
            return "归档为空"
        
        if restore_all:
            # 恢复所有
            memories.extend(archives)
            _save_memories(memories)
            _save_memories([], ARCHIVE_FILE)
            return f"✅ 已从归档恢复全部 {len(archives)} 条记忆"
        
        if not memory_id:
            # 显示归档列表
            result = "📦 归档记忆列表:\n\n"
            for m in archives[:10]:
                result += f"[ID:{m.get('id')}] {m.get('title', '无标题')}\n"
            if len(archives) > 10:
                result += f"... 还有 {len(archives)-10} 条\n"
            result += "\n使用 restore_from_archive(memory_id='xxx') 恢复指定记忆\n"
            result += "使用 restore_from_archive(restore_all=True) 恢复全部\n"
            return result
        
        # 恢复单个
        to_restore = None
        remaining = []
        for m in archives:
            if m.get("id") == memory_id:
                to_restore = m
            else:
                remaining.append(m)
        
        if not to_restore:
            return f"找不到ID为 {memory_id} 的归档记忆"
        
        memories.append(to_restore)
        _save_memories(memories)
        _save_memories(remaining, ARCHIVE_FILE)
        
        return f"✅ 已恢复记忆 [ID:{memory_id}]: {to_restore.get('title', '无标题')}"
    except Exception as e:
        return f"从归档恢复时出错: {str(e)}"
