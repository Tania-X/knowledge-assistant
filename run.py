"""项目启动脚本"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from client.gui.main import KnowledgeBaseClient
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = KnowledgeBaseClient(root)
    root.mainloop()

