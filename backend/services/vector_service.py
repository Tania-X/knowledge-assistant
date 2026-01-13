"""向量搜索服务"""
import numpy as np
import faiss
import pickle
from typing import List, Tuple, Optional
from pathlib import Path
import sys

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("警告: sentence-transformers未安装，向量搜索功能将不可用")
    SentenceTransformer = None

class VectorService:
    """向量搜索服务，使用sentence-transformers和FAISS"""
    
    def __init__(self, model_name: str, embedding_dim: int, db_path: str):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.db_path = db_path
        self.index_path = Path(db_path).parent / "faiss_index.bin"
        self.metadata_path = Path(db_path).parent / "faiss_metadata.pkl"
        
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
        self.metadata = []  # 存储(id, source_type)的映射
        self.load_index()
    
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
        # 如果数据量大，可以使用IVF或HNSW索引
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
                      source_types: List[str]):
        """添加向量到索引"""
        if self.index is None:
            self.create_new_index()
        
        # 确保embeddings是float32类型
        embeddings = embeddings.astype('float32')
        
        # 添加到FAISS索引
        self.index.add(embeddings)
        
        # 保存元数据
        for i, (doc_id, source_type) in enumerate(zip(ids, source_types)):
            self.metadata.append((doc_id, source_type))
        
        self.save_index()
    
    def search(self, query_text: str, top_k: int = 5) -> List[Tuple[int, str, float]]:
        """搜索相似向量"""
        if not self.model or self.index is None or self.index.ntotal == 0:
            return []
        
        # 编码查询文本
        query_embedding = self.encode([query_text])
        
        # 搜索
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        # 返回结果 (id, source_type, distance)
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                doc_id, source_type = self.metadata[idx]
                results.append((doc_id, source_type, float(dist)))
        
        return results
    
    def rebuild_index(self, db_manager):
        """重建索引（从数据库重新加载所有向量）"""
        self.create_new_index()
        
        # 从数据库获取所有嵌入
        web_embeddings = db_manager.get_all_embeddings('web')
        file_embeddings = db_manager.get_all_embeddings('file')
        
        all_ids = []
        all_types = []
        all_embeddings = []
        
        for doc_id, embedding_bytes in web_embeddings:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            all_ids.append(doc_id)
            all_types.append('web')
            all_embeddings.append(embedding)
        
        for doc_id, embedding_bytes in file_embeddings:
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            all_ids.append(doc_id)
            all_types.append('file')
            all_embeddings.append(embedding)
        
        if all_embeddings:
            embeddings_array = np.vstack(all_embeddings)
            self.add_embeddings(embeddings_array, all_ids, all_types)

