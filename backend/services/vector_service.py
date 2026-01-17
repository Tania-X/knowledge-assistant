"""向量搜索服务"""
import numpy as np
import faiss
import pickle
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import sys

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("警告: sentence-transformers未安装，向量搜索功能将不可用")
    SentenceTransformer = None


class ChunkingStrategy:
    """分块策略基类"""

    def chunk(self, text: str) -> List[Dict[str, any]]:
        """将文本分块，返回块列表"""
        raise NotImplementedError


class SmartChunkingStrategy(ChunkingStrategy):
    """智能分块策略 - 按段落/章节分块"""

    def __init__(self, min_size: int = 200, max_size: int = 1000,
                 delimiters: List[str] = None):
        self.min_size = min_size
        self.max_size = max_size
        self.delimiters = delimiters or ["\n\n", "\r\n\r\n"]

    def chunk(self, text: str) -> List[Dict[str, any]]:
        """智能分块"""
        if not text or len(text) <= self.max_size:
            return [{'content': text, 'index': 0}]

        chunks = []
        # 尝试按段落分隔
        remaining_text = text
        chunk_index = 0

        for delimiter in self.delimiters:
            if delimiter in text:
                paragraphs = text.split(delimiter)
                current_chunk = ""
                chunk_index = 0

                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue

                    # 如果当前块加上新段落超过最大大小，先保存当前块
                    if len(current_chunk) + len(para) > self.max_size and current_chunk:
                        if len(current_chunk) >= self.min_size:
                            chunks.append({'content': current_chunk, 'index': chunk_index})
                            chunk_index += 1
                        current_chunk = para
                    else:
                        if current_chunk:
                            current_chunk += "\n\n"
                        current_chunk += para

                # 保存最后一个块
                if current_chunk and len(current_chunk) >= self.min_size:
                    chunks.append({'content': current_chunk, 'index': chunk_index})

                if chunks:
                    return chunks

        # 如果没有合适的分隔符，使用降级策略
        if len(text) > self.max_size:
            chunks = []
            start = 0
            index = 0
            while start < len(text):
                end = min(start + self.max_size, len(text))
                chunk_text = text[start:end]
                if len(chunk_text) >= self.min_size:
                    chunks.append({'content': chunk_text, 'index': index})
                    index += 1
                start = end - (self.max_size // 4)  # 少量重叠

        if not chunks and text:
            return [{'content': text, 'index': 0}]

        return chunks


class SemanticChunkingStrategy(ChunkingStrategy):
    """语义分块策略 - 固定大小带重叠"""

    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[Dict[str, any]]:
        """语义分块"""
        if not text:
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append({'content': chunk_text, 'index': index})
            index += 1
            start = end - self.overlap

        return chunks


class FixedChunkingStrategy(ChunkingStrategy):
    """固定分块策略"""

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[Dict[str, any]]:
        """固定分块"""
        if not text:
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append({'content': chunk_text, 'index': index})
            index += 1
            start = end - self.overlap

        return chunks


class VectorService:
    """向量搜索服务，使用sentence-transformers和FAISS"""

    def __init__(self, model_name: str, embedding_dim: int, db_path: str,
                 chunking_config: Optional[Dict] = None):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.db_path = db_path
        self.index_path = Path(db_path).parent / "faiss_index.bin"
        self.metadata_path = Path(db_path).parent / "faiss_metadata.pkl"

        # 分块策略
        self.chunking_config = chunking_config or {}
        self.chunking_enabled = self.chunking_config.get('enabled', True)
        self.chunking_strategy = None
        self._init_chunking_strategy()

        # 初始化模型
        if SentenceTransformer:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                print(f"加载向量模型失败: {e}")
                self.model = None
        else:
            self.model = None

        # FAISS索引
        self.index = None
        self.metadata = []  # 存储(id, source_type, chunk_index)的映射
        self.load_index()

    def _init_chunking_strategy(self):
        """初始化分块策略"""
        if not self.chunking_enabled:
            return

        strategy = self.chunking_config.get('strategy', 'smart')

        if strategy == 'smart':
            config = self.chunking_config.get('smart', {})
            self.chunking_strategy = SmartChunkingStrategy(
                min_size=config.get('min_chunk_size', 200),
                max_size=config.get('max_chunk_size', 1000),
                delimiters=config.get('paragraph_delimiters')
            )
        elif strategy == 'semantic':
            config = self.chunking_config.get('semantic', {})
            self.chunking_strategy = SemanticChunkingStrategy(
                chunk_size=config.get('chunk_size', 500),
                overlap=config.get('overlap', 100)
            )
        elif strategy == 'fixed':
            config = self.chunking_config.get('fixed', {})
            self.chunking_strategy = FixedChunkingStrategy(
                chunk_size=config.get('chunk_size', 512),
                overlap=config.get('overlap', 50)
            )

    def chunk_text(self, text: str) -> List[Dict[str, any]]:
        """分块文本"""
        if not self.chunking_enabled or not self.chunking_strategy:
            return [{'content': text, 'index': 0}]
        return self.chunking_strategy.chunk(text)

    def load_index(self):
        """加载FAISS索引"""
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
            except Exception as e:
                print(f"加载索引失败: {e}，将创建新索引")
                self.create_new_index()
        else:
            self.create_new_index()

    def create_new_index(self):
        """创建新的FAISS索引"""
        # 使用L2距离的Flat索引（适合小规模数据）
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.metadata = []

    def save_index(self):
        """保存FAISS索引"""
        if self.index:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)

    def encode(self, texts: List[str]) -> np.ndarray:
        """将文本编码为向量"""
        if not self.model:
            raise RuntimeError("向量模型未加载")

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.astype('float32')

    def add_embeddings(self, embeddings: np.ndarray, ids: List[int],
                      source_types: List[str], chunk_indices: Optional[List[int]] = None):
        """添加向量到索引"""
        if self.index is None:
            self.create_new_index()

        # 确保embeddings是float32类型
        embeddings = embeddings.astype('float32')

        # 添加到FAISS索引
        self.index.add(embeddings)

        # 保存元数据
        if chunk_indices is None:
            chunk_indices = [0] * len(ids)

        for i, (doc_id, source_type, chunk_idx) in enumerate(zip(ids, source_types, chunk_indices)):
            self.metadata.append((doc_id, source_type, chunk_idx))

        self.save_index()

    def search(self, query_text: str, top_k: int = 5) -> List[Tuple[int, str, int, float]]:
        """搜索相似向量"""
        if not self.model or self.index is None or self.index.ntotal == 0:
            return []

        # 编码查询文本
        query_embedding = self.encode([query_text])

        # 搜索
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        # 返回结果 (id, source_type, chunk_index, distance)
        results = []
        seen_docs = set()  # 用于去重（按文档ID）

        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                doc_id, source_type, chunk_index = self.metadata[idx]
                # 如果需要去重，可以在这里过滤
                # 目前保留所有结果以便看到最相关的块
                results.append((doc_id, source_type, chunk_index, float(dist)))

        return results

    def clear_index(self):
        """清空索引"""
        self.create_new_index()
        self.save_index()
        print("索引已清空")

    def rebuild_index(self, db_manager):
        """重建索引（从数据库重新加载所有向量）"""
        self.create_new_index()

        # 从数据库获取所有嵌入
        web_embeddings = db_manager.get_all_embeddings('web')
        file_embeddings = db_manager.get_all_embeddings('file')

        all_ids = []
        all_types = []
        all_chunk_indices = []
        all_embeddings = []

        for doc_id, embedding_bytes, chunk_idx in web_embeddings:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            all_ids.append(doc_id)
            all_types.append('web')
            all_chunk_indices.append(chunk_idx)
            all_embeddings.append(embedding)

        for doc_id, embedding_bytes, chunk_idx in file_embeddings:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            all_ids.append(doc_id)
            all_types.append('file')
            all_chunk_indices.append(chunk_idx)
            all_embeddings.append(embedding)

        if all_embeddings:
            embeddings_array = np.vstack(all_embeddings)
            self.add_embeddings(embeddings_array, all_ids, all_types, all_chunk_indices)
