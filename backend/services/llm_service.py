"""LLM服务集成（Ollama）"""
import aiohttp
import asyncio
from typing import List, Dict, Optional
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.utils.config import config

class LLMService:
    """LLM服务，集成Ollama"""
    
    def __init__(self):
        self.config = config.ollama_config
        
        # 必须配置项，如果缺失则抛出异常
        self.base_url = self.config.get('base_url')
        if not self.base_url:
            raise ValueError("配置错误：config.yaml中缺少ollama.base_url配置")
        
        self.model_name = self.config.get('model_name')
        if not self.model_name:
            raise ValueError("配置错误：config.yaml中缺少ollama.model_name配置")
        
        self.timeout = self.config.get('timeout')
        if self.timeout is None or not isinstance(self.timeout, (int, float)) or self.timeout <= 0:
            raise ValueError("配置错误：config.yaml中缺少ollama.timeout配置或配置值无效（必须为正数）")
        
        self.session = None
    
    async def create_session(self):
        """创建aiohttp会话"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close_session(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
    
    async def generate(self, prompt: str, context: Optional[List[str]] = None) -> str:
        """异步调用本地大模型生成回复"""
        if not self.session:
            await self.create_session()
        
        try:
            # 构建完整提示词
            full_prompt = prompt
            if context:
                context_text = "\n\n".join([
                    f"[上下文{i+1}]\n{ctx}" for i, ctx in enumerate(context)
                ])
                full_prompt = f"{context_text}\n\n问题：{prompt}\n\n请基于以上上下文回答问题："
            
            # 调用Ollama API
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False
                }
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                return result.get('response', '')
        except asyncio.TimeoutError:
            return "错误：请求超时，请检查Ollama服务是否运行"
        except aiohttp.ClientError as e:
            return f"错误：无法连接到Ollama服务 ({str(e)})"
        except Exception as e:
            return f"错误：{str(e)}"
    
    async def generate_stream(self, prompt: str, context: Optional[List[str]] = None):
        """流式生成（用于实时显示）"""
        if not self.session:
            await self.create_session()
        
        try:
            # 构建完整提示词
            full_prompt = prompt
            if context:
                context_text = "\n\n".join([
                    f"[上下文{i+1}]\n{ctx}" for i, ctx in enumerate(context)
                ])
                full_prompt = f"{context_text}\n\n问题：{prompt}\n\n请基于以上上下文回答问题："
            
            # 调用Ollama流式API
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                
                async for line in response.content:
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except:
                            continue
        except Exception as e:
            yield f"错误：{str(e)}"

