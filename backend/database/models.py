"""数据库模型定义"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import hashlib

class KnowledgeBase:
    """知识库数据库管理"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        # 确保数据库目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 网页内容表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS web_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                content TEXT,
                summary TEXT,
                tags TEXT,
                embedding BLOB,  -- 存储向量嵌入（二进制）
                chunk_index INTEGER DEFAULT 0,  -- 分块索引
                content_hash TEXT,  -- 内容哈希，用于增量更新
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 本地文件索引表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT,
                file_type TEXT,
                file_size INTEGER,
                content TEXT,
                metadata TEXT,
                embedding BLOB,  -- 存储向量嵌入
                chunk_index INTEGER DEFAULT 0,  -- 分块索引
                content_hash TEXT,  -- 内容哈希，用于增量更新
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP,
                UNIQUE(file_path, chunk_index)  -- 组合唯一约束
            )
        ''')
        
        # 对话历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                response TEXT,
                context_ids TEXT,
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 知识关联表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                target_type TEXT NOT NULL,
                relation_type TEXT,
                similarity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_web_url ON web_content(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_web_hash ON web_content(content_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_path ON file_index(file_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON file_index(content_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at)')

        conn.commit()
        conn.close()
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def calculate_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def save_web_content(self, url: str, title: str, content: str, 
                        tags: Optional[List[str]] = None, 
                        embedding: Optional[bytes] = None) -> int:
        """保存网页内容"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        content_hash = self.calculate_hash(content)
        tags_json = json.dumps(tags) if tags else None
        
        # 检查是否已存在
        cursor.execute('SELECT id, content_hash FROM web_content WHERE url = ?', (url,))
        existing = cursor.fetchone()
        
        if existing:
            existing_id, existing_hash = existing
            # 如果内容未变化，不更新
            if existing_hash == content_hash:
                conn.close()
                return existing_id
            
            # 更新现有记录
            cursor.execute('''
                UPDATE web_content 
                SET title = ?, content = ?, tags = ?, embedding = ?, 
                    content_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (title, content, tags_json, embedding, content_hash, existing_id))
            conn.commit()
            conn.close()
            return existing_id
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO web_content 
                (url, title, content, tags, embedding, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url, title, content, tags_json, embedding, content_hash))
            conn.commit()
            content_id = cursor.lastrowid
            conn.close()
            return content_id
    
    def save_file_index(self, file_path: str, file_name: str, file_type: str,
                       file_size: int, content: str, metadata: Optional[Dict] = None,
                       embedding: Optional[bytes] = None, last_modified: Optional[str] = None) -> int:
        """保存文件索引"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        content_hash = self.calculate_hash(content)
        metadata_json = json.dumps(metadata) if metadata else None
        
        # 检查是否已存在
        cursor.execute('SELECT id, content_hash FROM file_index WHERE file_path = ?', (file_path,))
        existing = cursor.fetchone()
        
        if existing:
            existing_id, existing_hash = existing
            # 如果内容未变化，不更新
            if existing_hash == content_hash:
                conn.close()
                return existing_id
            
            # 更新现有记录
            cursor.execute('''
                UPDATE file_index 
                SET file_name = ?, file_type = ?, file_size = ?, content = ?,
                    metadata = ?, embedding = ?, content_hash = ?,
                    last_modified = ?, indexed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (file_name, file_type, file_size, content, metadata_json,
                  embedding, content_hash, last_modified, existing_id))
            conn.commit()
            conn.close()
            return existing_id
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO file_index 
                (file_path, file_name, file_type, file_size, content, 
                 metadata, embedding, content_hash, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, file_name, file_type, file_size, content,
                  metadata_json, embedding, content_hash, last_modified))
            conn.commit()
            file_id = cursor.lastrowid
            conn.close()
            return file_id
    
    def get_all_embeddings(self, source_type: str = 'web') -> List[tuple]:
        """获取所有嵌入向量（用于构建FAISS索引）"""
        conn = self.get_connection()
        cursor = conn.cursor()

        table = 'web_content' if source_type == 'web' else 'file_index'
        cursor.execute(f'SELECT id, embedding, chunk_index FROM {table} WHERE embedding IS NOT NULL')

        results = []
        for row in cursor.fetchall():
            if row[1]:  # embedding不为空
                results.append((row[0], row[1], row[2] if row[2] else 0))

        conn.close()
        return results

    def clear_embeddings(self):
        """清空所有嵌入数据"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 清空web_content的嵌入
        cursor.execute('UPDATE web_content SET embedding = NULL, chunk_index = 0')
        # 清空file_index的嵌入
        cursor.execute('UPDATE file_index SET embedding = NULL, chunk_index = 0')

        conn.commit()
        conn.close()
        print("数据库嵌入数据已清空")
    
    def save_conversation(self, query: str, response: str, 
                         context_ids: List[str], model_name: str):
        """保存对话历史"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        context_ids_json = json.dumps(context_ids)
        
        cursor.execute('''
            INSERT INTO conversations (query, response, context_ids, model_name)
            VALUES (?, ?, ?, ?)
        ''', (query, response, context_ids_json, model_name))
        
        conn.commit()
        conn.close()

