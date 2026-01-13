"""搜索服务（整合向量搜索和关键词搜索）"""
import sqlite3
from typing import List, Dict, Optional
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database.models import KnowledgeBase
from backend.services.vector_service import VectorService
from backend.utils.config import config

class SearchService:
    """搜索服务，整合向量搜索和关键词搜索"""
    
    def __init__(self, db_manager: KnowledgeBase, 
                 vector_service: Optional[VectorService] = None):
        self.db_manager = db_manager
        self.vector_service = vector_service
        self.config = config.search_config
        self.max_results = self.config.get('max_results', 5)
        self.max_context_length = self.config.get('max_context_length', 500)
    
    def search(self, query: str, use_vector: bool = True, 
              top_k: Optional[int] = None) -> List[Dict]:
        """搜索知识库"""
        if use_vector and self.vector_service and self.vector_service.model:
            return self._vector_search(query, top_k or self.max_results)
        else:
            return self._keyword_search(query, top_k or self.max_results)
    
    def _vector_search(self, query: str, top_k: int) -> List[Dict]:
        """向量搜索"""
        # 使用向量服务搜索
        results = self.vector_service.search(query, top_k)
        
        # 从数据库获取详细信息
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        search_results = []
        for doc_id, source_type, distance in results:
            if source_type == 'web':
                cursor.execute(
                    'SELECT url, title, content FROM web_content WHERE id = ?',
                    (doc_id,)
                )
            else:
                cursor.execute(
                    'SELECT file_path, file_name, content FROM file_index WHERE id = ?',
                    (doc_id,)
                )
            
            row = cursor.fetchone()
            if row:
                if source_type == 'web':
                    search_results.append({
                        'id': doc_id,
                        'type': 'web',
                        'source': row[0],
                        'title': row[1],
                        'content': row[2][:self.max_context_length] if row[2] else '',
                        'similarity': 1.0 / (1.0 + distance)  # 转换为相似度分数
                    })
                else:
                    search_results.append({
                        'id': doc_id,
                        'type': 'file',
                        'source': row[0],
                        'title': row[1],
                        'content': row[2][:self.max_context_length] if row[2] else '',
                        'similarity': 1.0 / (1.0 + distance)
                    })
        
        conn.close()
        return search_results
    
    def _keyword_search(self, query: str, max_results: int) -> List[Dict]:
        """关键词搜索（备用方案）"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # 提取关键词
        keywords = query.split()
        if not keywords:
            return []
        
        # 构建搜索条件
        conditions = []
        params = []
        
        for keyword in keywords:
            conditions.append("(content LIKE ? OR title LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        # 搜索网页内容
        web_sql = f'''
            SELECT id, url, title, content
            FROM web_content
            WHERE {' OR '.join(conditions)}
            LIMIT ?
        '''
        web_params = params + [max_results]
        cursor.execute(web_sql, web_params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'type': 'web',
                'source': row[1],
                'title': row[2],
                'content': (row[3] or '')[:self.max_context_length],
                'similarity': 0.5  # 关键词搜索没有相似度分数
            })
        
        # 搜索文件索引
        file_sql = f'''
            SELECT id, file_path, file_name, content
            FROM file_index
            WHERE {' OR '.join(conditions)}
            LIMIT ?
        '''
        file_params = params + [max_results]
        cursor.execute(file_sql, file_params)
        
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'type': 'file',
                'source': row[1],
                'title': row[2],
                'content': (row[3] or '')[:self.max_context_length],
                'similarity': 0.5
            })
        
        # 按相似度排序（如果有）
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        conn.close()
        return results[:max_results]

