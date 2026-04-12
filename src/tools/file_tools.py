from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import os
from typing import Optional


@tool
def read_file(file_path: str) -> str:
    """读取文件内容。参数: file_path - 文件的完整路径"""
    ctx = request_context.get() or new_context(method="read_file")
    
    try:
        if not os.path.exists(file_path):
            return f"错误：文件不存在 - {file_path}"
        
        if not os.path.isfile(file_path):
            return f"错误：不是一个文件 - {file_path}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"文件内容读取成功:\n\n{content}"
    except Exception as e:
        return f"读取文件时出错: {str(e)}"


@tool
def write_file(file_path: str, content: str, overwrite: Optional[bool] = False) -> str:
    """写入文件内容。参数: file_path - 文件路径; content - 要写入的内容; overwrite - 是否覆盖已存在的文件，默认为False"""
    ctx = request_context.get() or new_context(method="write_file")
    
    try:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # 检查文件是否存在
        if os.path.exists(file_path) and not overwrite:
            return f"错误：文件已存在，设置 overwrite=True 以覆盖 - {file_path}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"文件写入成功: {file_path}"
    except Exception as e:
        return f"写入文件时出错: {str(e)}"


@tool
def list_files(directory_path: str) -> str:
    """列出目录中的文件和文件夹。参数: directory_path - 目录路径"""
    ctx = request_context.get() or new_context(method="list_files")
    
    try:
        if not os.path.exists(directory_path):
            return f"错误：目录不存在 - {directory_path}"
        
        if not os.path.isdir(directory_path):
            return f"错误：不是一个目录 - {directory_path}"
        
        items = os.listdir(directory_path)
        files = []
        directories = []
        
        for item in items:
            item_path = os.path.join(directory_path, item)
            if os.path.isfile(item_path):
                files.append(item)
            else:
                directories.append(item)
        
        result = f"目录内容: {directory_path}\n\n"
        if directories:
            result += "文件夹:\n"
            for d in directories:
                result += f"  - {d}/\n"
        
        if files:
            result += "\n文件:\n"
            for f in files:
                result += f"  - {f}\n"
        
        if not directories and not files:
            result += "（空目录）"
        
        return result
    except Exception as e:
        return f"列出目录时出错: {str(e)}"
