"""文件索引服务（支持增量索引和分块嵌入）"""
import os
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional, Set, Literal
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database.models import KnowledgeBase
from backend.services.vector_service import VectorService
from backend.utils.config import config


class FileIndexer:
    """文件索引器，支持增量索引和分块嵌入"""

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

    def _get_files_in_directory(self, directory: str, recursive: bool = True) -> List[str]:
        """获取目录中的所有文件"""
        path = Path(directory)
        if not path.exists():
            return []

        all_files = []
        pattern = '**/*' if recursive else '*'
        for file_path in path.glob(pattern):
            if file_path.is_file() and self.is_supported_file(file_path):
                all_files.append(str(file_path.absolute()))

        return all_files

    def _is_file_modified(self, file_path: str) -> bool:
        """检查文件是否被修改"""
        path_obj = Path(file_path)
        if not path_obj.exists():
            return False

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

        if not row:
            return True  # 新文件
        return row[0] != last_modified  # 文件已修改

    def index_file_incremental(self, file_path: str) -> Dict:
        """增量索引单个文件（文件级）"""
        path = Path(file_path)

        if not path.exists():
            return {'status': 'error', 'error': '文件不存在'}

        if not path.is_file():
            return {'status': 'error', 'error': '不是文件'}

        # 检查文件是否需要更新
        if not self._is_file_modified(file_path):
            return {'status': 'skipped', 'reason': '文件未修改'}

        if not self.is_supported_file(path):
            return {'status': 'skipped', 'reason': '不支持的文件类型'}

        result = self.index_file(file_path)
        if result['status'] == 'success':
            result['needs_update'] = True
        return result

    def index_directory_incremental(self, directory: str, recursive: bool = True,
                                  mode: Literal['file', 'folder'] = 'folder') -> Dict:
        """
        增量索引目录

        Args:
            directory: 目录路径
            recursive: 是否递归
            mode: 索引模式，'file' 为文件级，'folder' 为文件夹级

        Returns:
            索引结果
        """
        path = Path(directory)

        if not path.exists():
            return {'status': 'error', 'error': '目录不存在'}

        # 获取已索引的文件
        indexed_files = self.get_indexed_files()

        # 获取目录中的所有文件
        all_files = self._get_files_in_directory(directory, recursive)

        if mode == 'folder':
            # 文件夹级增量：找出所有需要索引的文件
            files_to_index = []
            for file_path in all_files:
                if file_path not in indexed_files:
                    files_to_index.append(file_path)
                else:
                    # 检查文件是否被修改
                    if self._is_file_modified(file_path):
                        files_to_index.append(file_path)
        else:  # mode == 'file'
            # 文件级增量：只处理当前目录下的文件，不递归检查子目录
            files_to_index = []
            for file_path in all_files:
                if file_path not in indexed_files:
                    files_to_index.append(file_path)
                else:
                    if self._is_file_modified(file_path):
                        files_to_index.append(file_path)

        # 索引需要更新的文件
        results = []
        for file_path in files_to_index:
            result = self.index_file(file_path)
            if result.get('status') == 'success':
                result['needs_update'] = True
            results.append(result)

        return {
            'status': 'success',
            'mode': mode,
            'total_files': len(all_files),
            'indexed_files': len(files_to_index),
            'results': results
        }

    def save_to_db(self, indexed_data: Dict, metadata: Optional[Dict] = None) -> List[int]:
        """
        保存索引结果到数据库（支持分块）

        Returns:
            保存的文档ID列表
        """
        file_path = indexed_data['file_path']
        file_name = indexed_data['file_name']
        file_type = indexed_data['file_type']
        file_size = indexed_data['file_size']
        content = indexed_data.get('content', '')
        last_modified = indexed_data.get('last_modified')

        doc_ids = []

        # 如果启用了分块嵌入
        if self.vector_service and self.vector_service.model and content:
            chunks = self.vector_service.chunk_text(content)

            # 删除旧的分块记录
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM file_index WHERE file_path = ?', (file_path,))
            conn.commit()
            conn.close()

            # 为每个块创建记录
            for chunk in chunks:
                chunk_content = chunk['content']
                chunk_index = chunk['index']

                # 生成向量嵌入
                embedding = None
                embeddings_array = None
                try:
                    embeddings_array = self.vector_service.encode([chunk_content])
                    embedding = embeddings_array[0].tobytes()
                except Exception as e:
                    print(f"生成向量嵌入失败: {e}")

                # 保存到数据库（带分块索引）
                chunk_metadata = {
                    **(metadata or {}),
                    'chunk_index': chunk_index,
                    'total_chunks': len(chunks)
                }

                doc_id = self._save_chunk_to_db(
                    file_path=file_path,
                    file_name=file_name,
                    file_type=file_type,
                    file_size=file_size,
                    content=chunk_content,
                    metadata=chunk_metadata,
                    embedding=embedding,
                    chunk_index=chunk_index,
                    last_modified=last_modified
                )
                doc_ids.append(doc_id)

                # 添加到FAISS索引
                if self.vector_service and embeddings_array is not None:
                    try:
                        self.vector_service.add_embeddings(
                            embeddings_array,
                            [doc_id],
                            ['file'],
                            [chunk_index]
                        )
                    except Exception as e:
                        print(f"添加到FAISS索引失败: {e}")

        else:
            # 不使用分块，保存整份文档
            embedding = None
            embeddings_array = None
            if self.vector_service and self.vector_service.model:
                try:
                    embeddings_array = self.vector_service.encode([content])
                    embedding = embeddings_array[0].tobytes()
                except Exception as e:
                    print(f"生成向量嵌入失败: {e}")

            doc_id = self._save_chunk_to_db(
                file_path=file_path,
                file_name=file_name,
                file_type=file_type,
                file_size=file_size,
                content=content,
                metadata=metadata,
                embedding=embedding,
                chunk_index=0,
                last_modified=last_modified
            )
            doc_ids.append(doc_id)

            # 添加到FAISS索引
            if self.vector_service and embeddings_array is not None:
                try:
                    self.vector_service.add_embeddings(
                        embeddings_array,
                        [doc_id],
                        ['file'],
                        [0]
                    )
                except Exception as e:
                    print(f"添加到FAISS索引失败: {e}")

        return doc_ids

    def _save_chunk_to_db(self, file_path: str, file_name: str, file_type: str,
                          file_size: int, content: str, metadata: Optional[Dict] = None,
                          embedding: Optional[bytes] = None, chunk_index: int = 0,
                          last_modified: Optional[str] = None) -> int:
        """保存单个文档块到数据库"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        content_hash = self.db_manager.calculate_hash(content)
        metadata_json = json.dumps(metadata) if metadata else None

        # 检查是否已存在（同一文件的同一分块）
        cursor.execute(
            'SELECT id, content_hash FROM file_index WHERE file_path = ? AND chunk_index = ?',
            (file_path, chunk_index)
        )
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
                 metadata, embedding, chunk_index, content_hash, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_path, file_name, file_type, file_size, content,
                  metadata_json, embedding, chunk_index, content_hash, last_modified))
            conn.commit()
            file_id = cursor.lastrowid
            conn.close()
            return file_id
