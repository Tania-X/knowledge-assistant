"""文件索引服务（支持增量索引）"""
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database.models import KnowledgeBase
from backend.services.vector_service import VectorService
from backend.utils.config import config

class FileIndexer:
    """文件索引器，支持增量索引"""
    
    def __init__(self, db_manager: KnowledgeBase, 
                 vector_service: Optional[VectorService] = None):
        self.db_manager = db_manager
        self.vector_service = vector_service
        self.config = config.file_indexer_config
        self.supported_extensions = set(
            self.config.get('supported_extensions', ['.txt', '.md', '.py'])
        )
        self.max_content_length = self.config.get('max_content_length', 100000)
    
    def is_supported_file(self, file_path: Path) -> bool:
        """检查文件是否支持索引"""
        return file_path.suffix.lower() in self.supported_extensions
    
    def read_file_content(self, file_path: Path) -> Optional[str]:
        """读取文件内容"""
        try:
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read()
                    # 限制内容长度
                    if len(content) > self.max_content_length:
                        content = content[:self.max_content_length]
                    return content
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，返回None
            return None
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None
    
    def index_file(self, file_path: str) -> Dict:
        """索引单个文件"""
        path = Path(file_path)
        
        if not path.exists():
            return {'status': 'error', 'error': '文件不存在'}
        
        if not path.is_file():
            return {'status': 'error', 'error': '不是文件'}
        
        if not self.is_supported_file(path):
            return {'status': 'skipped', 'reason': '不支持的文件类型'}
        
        try:
            content = self.read_file_content(path)
            if content is None:
                return {'status': 'error', 'error': '无法读取文件内容'}
            
            stat = path.stat()
            
            result = {
                'file_path': str(path.absolute()),
                'file_name': path.name,
                'file_type': path.suffix,
                'file_size': stat.st_size,
                'content': content,
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'status': 'success'
            }
            
            return result
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def index_directory(self, directory: str, recursive: bool = True) -> List[Dict]:
        """索引目录下的所有文件"""
        results = []
        path = Path(directory)
        
        if not path.exists():
            return results
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for file_path in path.glob(pattern):
            if file_path.is_file():
                result = self.index_file(str(file_path))
                results.append(result)
        
        return results
    
    def get_indexed_files(self) -> Set[str]:
        """获取已索引的文件路径集合（用于增量索引）"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_path FROM file_index')
        indexed_paths = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        return indexed_paths
    
    def index_directory_incremental(self, directory: str, recursive: bool = True) -> Dict:
        """增量索引目录（只索引新增或修改的文件）"""
        path = Path(directory)
        
        if not path.exists():
            return {'status': 'error', 'error': '目录不存在'}
        
        # 获取已索引的文件
        indexed_files = self.get_indexed_files()
        
        # 获取目录中的所有文件
        all_files = []
        pattern = '**/*' if recursive else '*'
        for file_path in path.glob(pattern):
            if file_path.is_file() and self.is_supported_file(file_path):
                all_files.append(str(file_path.absolute()))
        
        # 找出需要索引的文件（新增或修改的）
        files_to_index = []
        for file_path in all_files:
            if file_path not in indexed_files:
                files_to_index.append(file_path)
            else:
                # 检查文件是否被修改
                path_obj = Path(file_path)
                if path_obj.exists():
                    stat = path_obj.stat()
                    last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    
                    # 从数据库获取最后修改时间
                    conn = self.db_manager.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT last_modified FROM file_index WHERE file_path = ?',
                        (file_path,)
                    )
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row and row[0] != last_modified:
                        files_to_index.append(file_path)
        
        # 索引需要更新的文件
        results = []
        for file_path in files_to_index:
            result = self.index_file(file_path)
            results.append(result)
        
        return {
            'status': 'success',
            'total_files': len(all_files),
            'indexed_files': len(files_to_index),
            'results': results
        }
    
    def save_to_db(self, indexed_data: Dict, metadata: Optional[Dict] = None) -> int:
        """保存索引结果到数据库"""
        # 生成向量嵌入
        embedding = None
        if self.vector_service and self.vector_service.model and indexed_data.get('content'):
            try:
                embeddings = self.vector_service.encode([indexed_data['content']])
                embedding = embeddings[0].tobytes()
            except Exception as e:
                print(f"生成向量嵌入失败: {e}")
        
        doc_id = self.db_manager.save_file_index(
            file_path=indexed_data['file_path'],
            file_name=indexed_data['file_name'],
            file_type=indexed_data['file_type'],
            file_size=indexed_data['file_size'],
            content=indexed_data.get('content', ''),
            metadata=metadata,
            embedding=embedding,
            last_modified=indexed_data.get('last_modified')
        )
        
        return doc_id

