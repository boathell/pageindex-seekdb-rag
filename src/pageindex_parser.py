"""
PageIndex集成模块
负责文档解析、树结构生成
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger
from pydantic import BaseModel


class TreeNode(BaseModel):
    """树节点数据模型"""
    node_id: str
    parent_id: Optional[str] = None
    title: str
    summary: str
    level: int
    start_index: int
    end_index: int
    nodes: List['TreeNode'] = []
    
    class Config:
        # 允许递归引用
        arbitrary_types_allowed = True


class DocumentTree(BaseModel):
    """文档树数据模型"""
    document_id: str
    description: Optional[str] = None
    total_pages: int
    root_nodes: List[TreeNode]


class PageIndexParser:
    """PageIndex文档解析器"""
    
    def __init__(
        self,
        model: str = "gpt-4o-2024-11-20",
        toc_check_pages: int = 20,
        max_pages_per_node: int = 10,
        max_tokens_per_node: int = 20000,
        pageindex_script_path: Optional[str] = None
    ):
        """
        初始化PageIndex解析器
        
        Args:
            model: OpenAI模型名称
            toc_check_pages: TOC检查页数
            max_pages_per_node: 每节点最大页数
            max_tokens_per_node: 每节点最大token数
            pageindex_script_path: PageIndex脚本路径
        """
        self.model = model
        self.toc_check_pages = toc_check_pages
        self.max_pages_per_node = max_pages_per_node
        self.max_tokens_per_node = max_tokens_per_node
        
        # 查找PageIndex脚本
        if pageindex_script_path:
            self.script_path = Path(pageindex_script_path)
        else:
            # 默认路径：项目根目录/external/PageIndex
            self.script_path = Path(__file__).parent.parent / "external" / "PageIndex" / "run_pageindex.py"
        
        if not self.script_path.exists():
            logger.warning(f"PageIndex script not found at {self.script_path}")
    
    def parse_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> DocumentTree:
        """
        解析PDF文档生成树结构
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            document_id: 文档ID
        
        Returns:
            DocumentTree对象
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # 设置输出目录
        if output_dir is None:
            output_dir = pdf_path.parent / "pageindex_output"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文档ID
        if document_id is None:
            document_id = pdf_path.stem
        
        output_file = output_dir / f"{document_id}_tree.json"
        
        logger.info(f"Parsing PDF: {pdf_path}")
        logger.info(f"Output directory: {output_dir}")
        
        # 构建命令（使用绝对路径）
        absolute_pdf_path = pdf_path.resolve()
        cmd = [
            "python3",
            str(self.script_path),
            "--pdf_path", str(absolute_pdf_path),
            "--model", self.model,
            "--toc-check-pages", str(self.toc_check_pages),
            "--max-pages-per-node", str(self.max_pages_per_node),
            "--max-tokens-per-node", str(self.max_tokens_per_node),
            "--if-add-node-id", "yes",
            "--if-add-node-summary", "yes",
            "--if-add-doc-description", "yes"
        ]
        
        try:
            # 设置环境变量（支持自定义 API endpoint）
            env = os.environ.copy()

            # 从 .env 加载配置
            from dotenv import load_dotenv
            load_dotenv()

            # 优先使用 API_KEY，否则使用 OPENAI_API_KEY
            api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
            if api_key:
                env["OPENAI_API_KEY"] = api_key

            # 如果有自定义 BASE_URL，设置 OPENAI_BASE_URL
            base_url = os.getenv("BASE_URL")
            if base_url:
                # 移除 /chat/completions 后缀（如果存在）
                base_url = base_url.replace("/chat/completions", "")
                env["OPENAI_BASE_URL"] = base_url
                logger.info(f"Using custom API endpoint: {base_url}")

            # 执行PageIndex脚本
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.script_path.parent,
                env=env
            )
            
            logger.info(f"PageIndex output: {result.stdout}")
            
            # 查找生成的JSON文件
            # PageIndex通常会在results目录生成 <filename>_structure.json
            pageindex_dir = self.script_path.parent
            results_dir = pageindex_dir / "results"

            # 尝试多个可能的位置和文件名
            possible_locations = [
                results_dir / f"{pdf_path.stem}_structure.json",
                pageindex_dir / f"{pdf_path.stem}_structure.json",
                results_dir / f"{pdf_path.stem}_tree.json",
                pageindex_dir / f"{pdf_path.stem}_tree.json"
            ]

            generated_file = None
            for loc in possible_locations:
                if loc.exists():
                    generated_file = loc
                    break

            if not generated_file:
                # 尝试通过glob查找
                possible_files = list(results_dir.glob(f"*{pdf_path.stem}*.json")) if results_dir.exists() else []
                if not possible_files:
                    possible_files = list(pageindex_dir.glob(f"*{pdf_path.stem}*.json"))

                if possible_files:
                    generated_file = possible_files[0]
                else:
                    raise FileNotFoundError(f"PageIndex output file not found. Searched in: {pageindex_dir}, {results_dir}")
            
            # 移动文件到输出目录
            if generated_file != output_file:
                import shutil
                shutil.move(str(generated_file), str(output_file))
            
            logger.info(f"Tree structure saved to: {output_file}")
            
            # 解析JSON
            tree_data = self._load_tree_json(output_file, document_id)
            return tree_data
            
        except subprocess.CalledProcessError as e:
            logger.error(f"PageIndex execution failed: {e.stderr}")
            raise RuntimeError(f"Failed to parse PDF: {e.stderr}")
    
    def _load_tree_json(self, json_path: Path, document_id: str) -> DocumentTree:
        """加载并解析树结构JSON"""
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # 递归解析树节点
        def parse_node(node_data: Dict[str, Any], parent_id: Optional[str] = None, level: int = 0, counter: List[int] = [0]) -> TreeNode:
            children = node_data.get('nodes', [])

            # 生成 node_id：如果没有 node_id，使用 document_id + 序号
            node_id = node_data.get('node_id', '')
            if not node_id:
                counter[0] += 1
                node_id = f"{document_id}_node_{counter[0]:04d}"

            node = TreeNode(
                node_id=node_id,
                parent_id=parent_id,
                title=node_data.get('title', ''),
                summary=node_data.get('summary', ''),
                level=level,
                start_index=node_data.get('start_index', 0),
                end_index=node_data.get('end_index', 0),
                nodes=[parse_node(child, node_id, level+1, counter) for child in children]
            )
            return node

        # 检查是否是 PageIndex 新格式 (包含 doc_name, doc_description, structure)
        if isinstance(raw_data, dict) and 'structure' in raw_data:
            # PageIndex 新格式：{doc_name, doc_description, structure: [...]}
            description = raw_data.get('doc_description', None)
            structure_data = raw_data['structure']

            if isinstance(structure_data, list):
                counter = [0]  # 重置计数器
                root_nodes = [parse_node(node, counter=counter) for node in structure_data]
                total_pages = max(node.end_index for node in root_nodes) if root_nodes else 0
            else:
                counter = [0]
                root_nodes = [parse_node(structure_data, counter=counter)]
                total_pages = structure_data.get('end_index', 0)

        # 解析根节点列表（旧格式）
        elif isinstance(raw_data, dict):
            # 单根节点情况
            counter = [0]
            root_nodes = [parse_node(raw_data, counter=counter)]
            total_pages = raw_data.get('end_index', 0)
            description = raw_data.get('description', None)
        elif isinstance(raw_data, list):
            # 多根节点情况
            counter = [0]
            root_nodes = [parse_node(node, counter=counter) for node in raw_data]
            total_pages = max(node.end_index for node in root_nodes) if root_nodes else 0
            description = None
        else:
            raise ValueError("Invalid tree structure format")

        return DocumentTree(
            document_id=document_id,
            description=description,
            total_pages=total_pages,
            root_nodes=root_nodes
        )
    
    def flatten_tree(self, tree: DocumentTree) -> List[TreeNode]:
        """
        将树结构展平为节点列表
        
        Args:
            tree: DocumentTree对象
        
        Returns:
            所有节点的列表
        """
        nodes = []
        
        def traverse(node: TreeNode):
            nodes.append(node)
            for child in node.nodes:
                traverse(child)
        
        for root in tree.root_nodes:
            traverse(root)
        
        return nodes
    
    def get_node_path(self, tree: DocumentTree, node_id: str) -> List[str]:
        """
        获取节点的完整路径
        
        Args:
            tree: DocumentTree对象
            node_id: 节点ID
        
        Returns:
            节点路径（标题列表）
        """
        def find_path(nodes: List[TreeNode], target_id: str, current_path: List[str]) -> Optional[List[str]]:
            for node in nodes:
                new_path = current_path + [node.title]
                if node.node_id == target_id:
                    return new_path
                if node.nodes:
                    result = find_path(node.nodes, target_id, new_path)
                    if result:
                        return result
            return None
        
        return find_path(tree.root_nodes, node_id, []) or []


# 测试代码
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pageindex_parser.py <pdf_path>")
        sys.exit(1)
    
    parser = PageIndexParser()
    tree = parser.parse_pdf(sys.argv[1])
    
    print(f"\nDocument ID: {tree.document_id}")
    print(f"Total pages: {tree.total_pages}")
    print(f"Root nodes: {len(tree.root_nodes)}")
    
    all_nodes = parser.flatten_tree(tree)
    print(f"Total nodes: {len(all_nodes)}")
    
    # 打印前5个节点
    print("\nFirst 5 nodes:")
    for node in all_nodes[:5]:
        path = parser.get_node_path(tree, node.node_id)
        print(f"  {' > '.join(path)}")
