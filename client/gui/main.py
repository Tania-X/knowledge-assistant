"""GUI主程序"""
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import threading
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database.models import KnowledgeBase
from backend.services.web_scraper import AsyncWebScraper
from backend.services.file_indexer import FileIndexer
from backend.services.llm_service import LLMService
from backend.services.search_service import SearchService
from backend.services.vector_service import VectorService
from backend.utils.config import config

class KnowledgeBaseClient:
    """知识库客户端GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("个人知识库助手")
        self.root.geometry("1400x900")

        # 初始化服务
        self.db_manager = KnowledgeBase(config.db_path)

        # 初始化向量服务
        try:
            vector_config = config.vector_search_config
            chunking_config = vector_config.get('chunking', {})
            self.vector_service = VectorService(
                model_name=vector_config.get('model_name'),
                embedding_dim=vector_config.get('embedding_dim', 384),
                db_path=config.db_path,
                chunking_config=chunking_config
            )
        except Exception as e:
            print(f"向量服务初始化失败: {e}")
            self.vector_service = None

        # 初始化其他服务
        self.scraper = AsyncWebScraper(self.db_manager, self.vector_service)
        self.indexer = FileIndexer(self.db_manager, self.vector_service)
        self.llm = LLMService()
        self.search_service = SearchService(self.db_manager, self.vector_service)

        # 创建事件循环（用于异步操作）
        self.loop = None
        self.loop_thread = None
        self.start_event_loop()

        self.setup_ui()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_event_loop(self):
        """在新线程中启动事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

    def run_async(self, coro):
        """在事件循环中运行异步函数"""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=300)  # 5分钟超时

    def setup_ui(self):
        """设置UI"""
        # 创建Notebook（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 网页抓取标签页
        self.web_frame = ttk.Frame(notebook)
        notebook.add(self.web_frame, text="网页抓取")
        self.setup_web_tab()

        # 文件索引标签页
        self.file_frame = ttk.Frame(notebook)
        notebook.add(self.file_frame, text="文件索引")
        self.setup_file_tab()

        # 索引管理标签页
        self.index_manage_frame = ttk.Frame(notebook)
        notebook.add(self.index_manage_frame, text="索引管理")
        self.setup_index_manage_tab()

        # 智能问答标签页
        self.qa_frame = ttk.Frame(notebook)
        notebook.add(self.qa_frame, text="智能问答")
        self.setup_qa_tab()

        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_web_tab(self):
        """设置网页抓取标签页"""
        # URL输入区域
        url_frame = ttk.Frame(self.web_frame)
        url_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_frame, width=70)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        ttk.Button(url_frame, text="抓取", command=self.scrape_url).pack(side=tk.LEFT, padx=5)
        ttk.Button(url_frame, text="批量抓取", command=self.batch_scrape).pack(side=tk.LEFT, padx=5)

        # 结果显示区域
        result_frame = ttk.Frame(self.web_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.web_result = scrolledtext.ScrolledText(result_frame, height=25, wrap=tk.WORD)
        self.web_result.pack(fill=tk.BOTH, expand=True)

    def setup_file_tab(self):
        """设置文件索引标签页"""
        # 文件选择区域
        file_frame = ttk.Frame(self.file_frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(file_frame, text="选择文件", command=self.select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="选择目录", command=self.select_directory).pack(side=tk.LEFT, padx=5)

        # 增量索引选项
        ttk.Label(file_frame, text="|").pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="增量索引(文件夹)", command=self.incremental_index_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="增量索引(文件级)", command=self.incremental_index_file).pack(side=tk.LEFT, padx=5)

        self.file_label = ttk.Label(file_frame, text="未选择文件")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # 结果显示区域
        result_frame = ttk.Frame(self.file_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.file_result = scrolledtext.ScrolledText(result_frame, height=25, wrap=tk.WORD)
        self.file_result.pack(fill=tk.BOTH, expand=True)

    def setup_index_manage_tab(self):
        """设置索引管理标签页"""
        # 索引信息显示
        info_frame = ttk.Frame(self.index_manage_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(info_frame, text="索引管理", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5)

        # 操作按钮
        action_frame = ttk.Frame(self.index_manage_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(action_frame, text="重建索引", command=self.rebuild_index).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="清空索引", command=self.clear_index).pack(side=tk.LEFT, padx=5)

        # 索引统计信息
        stats_frame = ttk.Frame(self.index_manage_frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(stats_frame, text="索引统计:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.index_stats_label = ttk.Label(stats_frame, text="点击刷新查看统计")
        self.index_stats_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(stats_frame, text="刷新", command=self.refresh_index_stats).pack(side=tk.LEFT, padx=5)

        # 结果显示区域
        result_frame = ttk.Frame(self.index_manage_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.index_result = scrolledtext.ScrolledText(result_frame, height=20, wrap=tk.WORD)
        self.index_result.pack(fill=tk.BOTH, expand=True)

    def setup_qa_tab(self):
        """设置智能问答标签页"""
        # 问题输入区域
        query_frame = ttk.Frame(self.qa_frame)
        query_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(query_frame, text="问题:").pack(side=tk.LEFT, padx=5)
        self.query_entry = ttk.Entry(query_frame, width=70)
        self.query_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.query_entry.bind('<Return>', lambda e: self.ask_question())

        ttk.Button(query_frame, text="提问", command=self.ask_question).pack(side=tk.LEFT, padx=5)

        # 回答显示区域
        answer_frame = ttk.Frame(self.qa_frame)
        answer_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.answer_text = scrolledtext.ScrolledText(answer_frame, height=30, wrap=tk.WORD)
        self.answer_text.pack(fill=tk.BOTH, expand=True)

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def scrape_url(self):
        """抓取单个URL"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入URL")
            return

        def do_scrape():
            self.update_status(f"正在抓取: {url}...")
            self.web_result.insert(tk.END, f"正在抓取: {url}...\n")
            self.web_result.update()

            try:
                result = self.run_async(self.scraper.scrape_and_save(url))

                if result['status'] == 'success':
                    self.web_result.insert(tk.END, f"✓ 抓取成功\n")
                    self.web_result.insert(tk.END, f"标题: {result.get('title')}\n")
                    self.web_result.insert(tk.END, f"内容长度: {len(result.get('content', ''))} 字符\n")
                    self.web_result.insert(tk.END, f"文档ID: {result.get('doc_id')}\n\n")
                    self.update_status("抓取完成")
                else:
                    self.web_result.insert(tk.END, f"✗ 抓取失败: {result.get('error')}\n\n")
                    self.update_status("抓取失败")
            except Exception as e:
                self.web_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_scrape, daemon=True).start()

    def batch_scrape(self):
        """批量抓取"""
        urls_text = tk.simpledialog.askstring("批量抓取", "请输入URL列表（每行一个）:")
        if not urls_text:
            return

        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            messagebox.showwarning("警告", "请输入至少一个URL")
            return

        def do_batch_scrape():
            self.update_status(f"正在批量抓取 {len(urls)} 个URL...")
            self.web_result.insert(tk.END, f"开始批量抓取 {len(urls)} 个URL...\n\n")
            self.web_result.update()

            try:
                results = self.run_async(self.scraper.scrape_and_save_batch(urls))

                success_count = sum(1 for r in results if r['status'] == 'success')
                self.web_result.insert(tk.END, f"完成！成功: {success_count}/{len(urls)}\n\n")

                for result in results:
                    if result['status'] == 'success':
                        self.web_result.insert(tk.END, f"✓ {result['url']}\n")
                    else:
                        self.web_result.insert(tk.END, f"✗ {result['url']}: {result.get('error')}\n")

                self.update_status(f"批量抓取完成: {success_count}/{len(urls)}")
            except Exception as e:
                self.web_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_batch_scrape, daemon=True).start()

    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_label.config(text=f"已选择: {file_path}")
            self.index_file(file_path)

    def select_directory(self):
        """选择目录"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.file_label.config(text=f"已选择目录: {dir_path}")
            self.index_directory(dir_path)

    def index_file(self, file_path: str):
        """索引文件"""
        def do_index():
            self.update_status(f"正在索引: {file_path}...")
            self.file_result.insert(tk.END, f"正在索引: {file_path}...\n")
            self.file_result.update()

            try:
                result = self.indexer.index_file(file_path)

                if result['status'] == 'success':
                    doc_ids = self.indexer.save_to_db(result)
                    chunk_count = len(doc_ids)
                    self.file_result.insert(tk.END, f"✓ 索引成功\n")
                    self.file_result.insert(tk.END, f"文件: {result['file_name']}\n")
                    self.file_result.insert(tk.END, f"大小: {result['file_size']} 字节\n")
                    self.file_result.insert(tk.END, f"分块数: {chunk_count}\n")
                    self.file_result.insert(tk.END, f"文档ID: {doc_ids[0]}\n\n")
                    self.update_status("索引完成")
                elif result['status'] == 'skipped':
                    self.file_result.insert(tk.END, f"⊘ 跳过: {result.get('reason')}\n\n")
                    self.update_status("文件已跳过")
                else:
                    self.file_result.insert(tk.END, f"✗ 索引失败: {result.get('error')}\n\n")
                    self.update_status("索引失败")
            except Exception as e:
                self.file_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_index, daemon=True).start()

    def index_directory(self, dir_path: str):
        """索引目录"""
        def do_index():
            self.update_status(f"正在索引目录: {dir_path}...")
            self.file_result.insert(tk.END, f"正在索引目录: {dir_path}...\n")
            self.file_result.update()

            try:
                results = self.indexer.index_directory(dir_path)
                success_count = 0
                total_chunks = 0

                for result in results:
                    if result['status'] == 'success':
                        doc_ids = self.indexer.save_to_db(result)
                        success_count += 1
                        total_chunks += len(doc_ids)

                self.file_result.insert(tk.END,
                    f"✓ 完成，成功索引 {success_count}/{len(results)} 个文件\n"
                    f"生成 {total_chunks} 个文档块\n\n")
                self.update_status(f"索引完成: {success_count}/{len(results)}")
            except Exception as e:
                self.file_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_index, daemon=True).start()

    def incremental_index_folder(self):
        """增量索引（文件夹级）"""
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        def do_incremental():
            self.update_status(f"正在增量索引: {dir_path}...")
            self.file_result.insert(tk.END, f"正在增量索引(文件夹级): {dir_path}...\n")
            self.file_result.update()

            try:
                result = self.indexer.index_directory_incremental(dir_path, mode='folder')

                if result['status'] == 'success':
                    indexed_count = result['indexed_files']
                    total_count = result['total_files']
                    total_chunks = 0

                    for item in result['results']:
                        if item['status'] == 'success':
                            doc_ids = self.indexer.save_to_db(item)
                            total_chunks += len(doc_ids)

                    self.file_result.insert(tk.END,
                        f"✓ 增量索引完成（文件夹级）\n"
                        f"总文件数: {total_count}\n"
                        f"新增/更新: {indexed_count}\n"
                        f"生成块数: {total_chunks}\n\n")
                    self.update_status(f"增量索引完成: {indexed_count} 个文件")
                else:
                    self.file_result.insert(tk.END, f"✗ 错误: {result.get('error')}\n\n")
                    self.update_status("增量索引失败")
            except Exception as e:
                self.file_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_incremental, daemon=True).start()

    def incremental_index_file(self):
        """增量索引（文件级）"""
        dir_path = filedialog.askdirectory()
        if not dir_path:
            return

        def do_incremental():
            self.update_status(f"正在增量索引: {dir_path}...")
            self.file_result.insert(tk.END, f"正在增量索引(文件级): {dir_path}...\n")
            self.file_result.update()

            try:
                result = self.indexer.index_directory_incremental(dir_path, mode='file')

                if result['status'] == 'success':
                    indexed_count = result['indexed_files']
                    total_count = result['total_files']
                    total_chunks = 0

                    for item in result['results']:
                        if item['status'] == 'success':
                            doc_ids = self.indexer.save_to_db(item)
                            total_chunks += len(doc_ids)

                    self.file_result.insert(tk.END,
                        f"✓ 增量索引完成（文件级）\n"
                        f"总文件数: {total_count}\n"
                        f"新增/更新: {indexed_count}\n"
                        f"生成块数: {total_chunks}\n\n")
                    self.update_status(f"增量索引完成: {indexed_count} 个文件")
                else:
                    self.file_result.insert(tk.END, f"✗ 错误: {result.get('error')}\n\n")
                    self.update_status("增量索引失败")
            except Exception as e:
                self.file_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_incremental, daemon=True).start()

    def rebuild_index(self):
        """重建索引"""
        if not messagebox.askyesno("确认", "确定要重建索引吗？\n这将从数据库重新加载所有嵌入向量。"):
            return

        def do_rebuild():
            self.update_status("正在重建索引...")
            self.index_result.insert(tk.END, "开始重建索引...\n")
            self.index_result.update()

            try:
                if self.vector_service:
                    self.vector_service.rebuild_index(self.db_manager)
                    self.index_result.insert(tk.END, "✓ 索引重建完成\n\n")
                    self.refresh_index_stats()
                    self.update_status("索引重建完成")
                else:
                    self.index_result.insert(tk.END, "✗ 向量服务未初始化\n\n")
                    self.update_status("索引重建失败")
            except Exception as e:
                self.index_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_rebuild, daemon=True).start()

    def clear_index(self):
        """清空索引"""
        if not messagebox.askyesno("确认", "确定要清空索引吗？\n这将删除所有FAISS索引数据和数据库中的嵌入向量。"):
            return

        def do_clear():
            self.update_status("正在清空索引...")
            self.index_result.insert(tk.END, "开始清空索引...\n")
            self.index_result.update()

            try:
                # 清空FAISS索引
                if self.vector_service:
                    self.vector_service.clear_index()
                    self.index_result.insert(tk.END, "✓ FAISS索引已清空\n")

                # 清空数据库嵌入
                self.db_manager.clear_embeddings()
                self.index_result.insert(tk.END, "✓ 数据库嵌入已清空\n\n")

                self.refresh_index_stats()
                self.update_status("索引清空完成")
            except Exception as e:
                self.index_result.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_clear, daemon=True).start()

    def refresh_index_stats(self):
        """刷新索引统计信息"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()

            # 统计文件索引
            cursor.execute('SELECT COUNT(*) FROM file_index WHERE embedding IS NOT NULL')
            file_count = cursor.fetchone()[0]

            # 统计网页内容
            cursor.execute('SELECT COUNT(*) FROM web_content WHERE embedding IS NOT NULL')
            web_count = cursor.fetchone()[0]

            # 统计FAISS索引
            faiss_count = 0
            if self.vector_service and self.vector_service.index:
                faiss_count = self.vector_service.index.ntotal

            conn.close()

            stats_text = (
                f"文件索引: {file_count} 条 | "
                f"网页内容: {web_count} 条 | "
                f"FAISS索引: {faiss_count} 条"
            )
            self.index_stats_label.config(text=stats_text)

            # 在结果区域显示详细信息
            self.index_result.insert(tk.END, f"索引统计信息:\n")
            self.index_result.insert(tk.END, f"  文件索引块数: {file_count}\n")
            self.index_result.insert(tk.END, f"  网页内容块数: {web_count}\n")
            self.index_result.insert(tk.END, f"  FAISS索引向量数: {faiss_count}\n")
            self.index_result.insert(tk.END, f"  总计: {file_count + web_count} 条\n\n")

            self.update_status("统计信息已更新")
        except Exception as e:
            self.index_stats_label.config(text=f"统计失败: {str(e)}")
            self.update_status("统计信息获取失败")

    def ask_question(self):
        """提问"""
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("警告", "请输入问题")
            return

        def do_ask():
            self.update_status("正在搜索相关知识...")
            self.answer_text.insert(tk.END, f"问题: {query}\n")
            self.answer_text.insert(tk.END, "正在搜索相关知识...\n\n")
            self.answer_text.update()

            try:
                # 搜索相关知识
                search_results = self.search_service.search(query)

                if search_results:
                    self.answer_text.insert(tk.END, f"找到 {len(search_results)} 条相关结果\n\n")

                    # 提取上下文
                    contexts = [r['content'] for r in search_results[:3]]

                    self.update_status("正在生成回答...")
                    self.answer_text.insert(tk.END, "正在生成回答...\n\n")
                    self.answer_text.update()

                    # 调用LLM生成回答
                    answer = self.run_async(self.llm.generate(query, contexts))

                    self.answer_text.insert(tk.END, f"回答:\n{answer}\n\n")
                    self.answer_text.insert(tk.END, f"参考来源:\n")
                    for i, source in enumerate(search_results[:3], 1):
                        source_type = "网页" if source['type'] == 'web' else "文件"
                        self.answer_text.insert(tk.END,
                            f"{i}. [{source_type}] {source['title']}\n")
                    self.answer_text.insert(tk.END, "\n" + "="*60 + "\n\n")

                    # 保存对话历史
                    context_ids = [str(s['id']) for s in search_results[:3]]
                    self.db_manager.save_conversation(
                        query, answer, context_ids, self.llm.model_name
                    )

                    self.update_status("回答生成完成")
                else:
                    self.answer_text.insert(tk.END,
                        "未找到相关知识，将使用通用回答...\n\n")
                    self.answer_text.update()

                    answer = self.run_async(self.llm.generate(query))
                    self.answer_text.insert(tk.END, f"回答:\n{answer}\n\n")
                    self.answer_text.insert(tk.END, "\n" + "="*60 + "\n\n")

                    self.update_status("回答生成完成")
            except Exception as e:
                self.answer_text.insert(tk.END, f"✗ 错误: {str(e)}\n\n")
                self.update_status("发生错误")

        threading.Thread(target=do_ask, daemon=True).start()

    def on_closing(self):
        """窗口关闭事件"""
        # 关闭异步会话
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.scraper.close_session(), self.loop
            )
            asyncio.run_coroutine_threadsafe(
                self.llm.close_session(), self.loop
            )
            self.loop.call_soon_threadsafe(self.loop.stop)

        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = KnowledgeBaseClient(root)
    root.mainloop()
