"""异步网页抓取服务"""
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database.models import KnowledgeBase
from backend.services.vector_service import VectorService
from backend.utils.config import config

class AsyncWebScraper:
    """异步网页抓取器"""
    
    def __init__(self, db_manager: KnowledgeBase, vector_service: Optional[VectorService] = None):
        self.db_manager = db_manager
        self.vector_service = vector_service
        self.config = config.scraper_config
        self.session = None
    
    async def create_session(self):
        """创建aiohttp会话"""
        timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 10))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
    
    async def close_session(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
    
    async def scrape_url(self, url: str) -> Dict:
        """异步抓取单个URL"""
        if not self.session:
            await self.create_session()
        
        try:
            async with self.session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # 提取标题
                title_tag = soup.find('title')
                title = title_tag.text.strip() if title_tag else url
                
                # 移除script和style标签
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # 提取正文内容
                content = soup.get_text(separator='\n', strip=True)
                
                # 限制内容长度
                max_length = self.config.get('max_content_length', 50000)
                if len(content) > max_length:
                    content = content[:max_length]
                
                # 提取链接
                links = []
                for a in soup.find_all('a', href=True):
                    link = urljoin(url, a.get('href'))
                    if urlparse(link).netloc:  # 只保留有效链接
                        links.append(link)
                    if len(links) >= self.config.get('max_links', 100):
                        break
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'links': links,
                    'status': 'success'
                }
        except asyncio.TimeoutError:
            return {
                'url': url,
                'status': 'error',
                'error': '请求超时'
            }
        except Exception as e:
            return {
                'url': url,
                'status': 'error',
                'error': str(e)
            }
    
    async def scrape_urls(self, urls: List[str]) -> List[Dict]:
        """异步批量抓取多个URL"""
        if not self.session:
            await self.create_session()
        
        max_concurrent = self.config.get('max_concurrent', 5)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'url': urls[i],
                    'status': 'error',
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def scrape_and_save(self, url: str, tags: Optional[List[str]] = None) -> Dict:
        """抓取并保存到数据库"""
        result = await self.scrape_url(url)

        if result['status'] == 'success':
            # 生成向量嵌入
            embedding = None
            embeddings_array = None
            if self.vector_service and self.vector_service.model:
                try:
                    embeddings_array = self.vector_service.encode([result['content']])
                    embedding = embeddings_array[0].tobytes()
                except Exception as e:
                    print(f"生成向量嵌入失败: {e}")

            # 保存到数据库
            doc_id = self.db_manager.save_web_content(
                url=result['url'],
                title=result.get('title', ''),
                content=result.get('content', ''),
                tags=tags,
                embedding=embedding
            )

            # 添加到FAISS索引
            if self.vector_service and embeddings_array is not None:
                try:
                    self.vector_service.add_embeddings(
                        embeddings_array,
                        [doc_id],
                        ['web']
                    )
                except Exception as e:
                    print(f"添加到FAISS索引失败: {e}")

            result['doc_id'] = doc_id

        return result
    
    async def scrape_and_save_batch(self, urls: List[str],
                                   tags: Optional[List[List[str]]] = None) -> List[Dict]:
        """批量抓取并保存"""
        results = await self.scrape_urls(urls)

        # 保存到数据库
        doc_ids = []
        embeddings_to_add = []
        source_types_to_add = []

        for i, result in enumerate(results):
            if result['status'] == 'success':
                tag_list = tags[i] if tags and i < len(tags) else None

                # 生成向量嵌入
                embedding = None
                embeddings_array = None
                if self.vector_service and self.vector_service.model:
                    try:
                        embeddings_array = self.vector_service.encode([result['content']])
                        embedding = embeddings_array[0].tobytes()
                    except Exception as e:
                        print(f"生成向量嵌入失败: {e}")

                doc_id = self.db_manager.save_web_content(
                    url=result['url'],
                    title=result.get('title', ''),
                    content=result.get('content', ''),
                    tags=tag_list,
                    embedding=embedding
                )

                result['doc_id'] = doc_id

                # 收集需要添加到FAISS索引的数据
                if self.vector_service and embeddings_array is not None:
                    doc_ids.append(doc_id)
                    embeddings_to_add.append(embeddings_array[0])
                    source_types_to_add.append('web')

        # 批量添加到FAISS索引
        if self.vector_service and embeddings_to_add:
            try:
                import numpy as np
                embeddings_array = np.vstack(embeddings_to_add)
                self.vector_service.add_embeddings(
                    embeddings_array,
                    doc_ids,
                    source_types_to_add
                )
            except Exception as e:
                print(f"批量添加到FAISS索引失败: {e}")

        return results

