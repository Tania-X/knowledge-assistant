"""配置管理模块"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """配置管理类"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
        
        # 确保数据目录存在
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    @property
    def db_path(self) -> str:
        """数据库路径"""
        path = self.get('database.path')
        if not os.path.isabs(path):
            base_dir = Path(__file__).parent.parent.parent
            path = str(base_dir / path)
        return path
    
    @property
    def ollama_config(self) -> Dict:
        """Ollama配置"""
        return self.get('ollama', {})
    
    @property
    def scraper_config(self) -> Dict:
        """抓取器配置"""
        return self.get('scraper', {})
    
    @property
    def file_indexer_config(self) -> Dict:
        """文件索引器配置"""
        return self.get('file_indexer', {})
    
    @property
    def vector_search_config(self) -> Dict:
        """向量搜索配置"""
        return self.get('vector_search', {})

# 全局配置实例
config = Config()

