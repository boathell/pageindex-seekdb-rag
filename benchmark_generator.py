"""
评测数据集准备脚本
准备用于对比实验的标准数据集
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class BenchmarkQuery:
    """评测查询"""
    query_id: str
    query_text: str
    document_id: str
    ground_truth_chunks: List[str]  # 正确答案的chunk_id列表
    expected_answer: str
    category: str  # "factual", "conceptual", "procedural", "mixed"
    difficulty: str  # "easy", "medium", "hard"


@dataclass
class BenchmarkDataset:
    """评测数据集"""
    name: str
    description: str
    documents: List[Dict[str, Any]]  # 文档列表
    queries: List[BenchmarkQuery]


def create_finance_benchmark() -> BenchmarkDataset:
    """
    创建金融文档评测数据集
    基于FinanceBench风格的问题
    """
    
    # 定义测试查询
    queries = [
        BenchmarkQuery(
            query_id="fin_001",
            query_text="公司2024年第一季度的总收入是多少？",
            document_id="annual_report_2024",
            ground_truth_chunks=["0001.1_chunk_0", "0001.1_chunk_1"],
            expected_answer="$1.5 billion",
            category="factual",
            difficulty="easy"
        ),
        BenchmarkQuery(
            query_id="fin_002",
            query_text="描述公司的主要风险因素及其对业务的潜在影响",
            document_id="annual_report_2024",
            ground_truth_chunks=["0003.2_chunk_0", "0003.2_chunk_1", "0003.2_chunk_2"],
            expected_answer="主要风险包括市场波动、监管变化和技术中断...",
            category="conceptual",
            difficulty="medium"
        ),
        BenchmarkQuery(
            query_id="fin_003",
            query_text="相比去年同期，毛利率有什么变化？原因是什么？",
            document_id="annual_report_2024",
            ground_truth_chunks=["0001.2_chunk_1", "0001.3_chunk_0"],
            expected_answer="毛利率从45%上升到48%，主要因为成本控制和产品组合优化",
            category="mixed",
            difficulty="hard"
        ),
        BenchmarkQuery(
            query_id="fin_004",
            query_text="公司的并购策略是什么？",
            document_id="annual_report_2024",
            ground_truth_chunks=["0004.1_chunk_2"],
            expected_answer="专注于收购互补技术和扩大市场份额的公司",
            category="conceptual",
            difficulty="medium"
        ),
        BenchmarkQuery(
            query_id="fin_005",
            query_text="管理层讨论分析部分提到了哪些关键绩效指标？",
            document_id="annual_report_2024",
            ground_truth_chunks=["0002.1_chunk_0", "0002.1_chunk_1"],
            expected_answer="包括收入增长、EBITDA利润率、客户获取成本等",
            category="factual",
            difficulty="easy"
        ),
    ]
    
    documents = [
        {
            "document_id": "annual_report_2024",
            "title": "Annual Report 2024",
            "path": "data/benchmark/finance/annual_report_2024.pdf",
            "category": "finance",
            "metadata": {
                "company": "Example Corp",
                "year": 2024,
                "pages": 120
            }
        }
    ]
    
    return BenchmarkDataset(
        name="Finance Benchmark",
        description="金融文档问答评测集，包含事实性、概念性和程序性问题",
        documents=documents,
        queries=queries
    )


def create_technical_benchmark() -> BenchmarkDataset:
    """
    创建技术文档评测数据集
    适用于技术手册、API文档等
    """
    
    queries = [
        BenchmarkQuery(
            query_id="tech_001",
            query_text="如何配置系统的日志级别？",
            document_id="user_manual_v2",
            ground_truth_chunks=["0005.2_chunk_1"],
            expected_answer="在config.yaml中设置log_level参数",
            category="procedural",
            difficulty="easy"
        ),
        BenchmarkQuery(
            query_id="tech_002",
            query_text="系统支持哪些认证方式？",
            document_id="user_manual_v2",
            ground_truth_chunks=["0003.1_chunk_0", "0003.1_chunk_1"],
            expected_answer="支持OAuth 2.0、API Key和JWT令牌",
            category="factual",
            difficulty="easy"
        ),
        BenchmarkQuery(
            query_id="tech_003",
            query_text="解释系统架构中各组件之间的交互流程",
            document_id="user_manual_v2",
            ground_truth_chunks=["0002.1_chunk_0", "0002.2_chunk_0", "0002.3_chunk_0"],
            expected_answer="客户端通过API网关连接到后端服务，经过负载均衡器分发到应用服务器...",
            category="conceptual",
            difficulty="hard"
        ),
        BenchmarkQuery(
            query_id="tech_004",
            query_text="如何排查数据库连接失败的问题？",
            document_id="user_manual_v2",
            ground_truth_chunks=["0008.3_chunk_1", "0008.3_chunk_2"],
            expected_answer="检查连接字符串、网络配置、数据库服务状态和防火墙规则",
            category="procedural",
            difficulty="medium"
        ),
    ]
    
    documents = [
        {
            "document_id": "user_manual_v2",
            "title": "System User Manual v2.0",
            "path": "data/benchmark/technical/user_manual_v2.pdf",
            "category": "technical",
            "metadata": {
                "version": "2.0",
                "pages": 85
            }
        }
    ]
    
    return BenchmarkDataset(
        name="Technical Benchmark",
        description="技术文档问答评测集，侧重流程和配置类问题",
        documents=documents,
        queries=queries
    )


def create_legal_benchmark() -> BenchmarkDataset:
    """
    创建法律文档评测数据集
    适用于合同、法规等
    """
    
    queries = [
        BenchmarkQuery(
            query_id="legal_001",
            query_text="合同的终止条款是什么？",
            document_id="service_agreement",
            ground_truth_chunks=["0012.1_chunk_0"],
            expected_answer="任何一方可提前30天书面通知终止",
            category="factual",
            difficulty="easy"
        ),
        BenchmarkQuery(
            query_id="legal_002",
            query_text="知识产权归属如何规定？",
            document_id="service_agreement",
            ground_truth_chunks=["0007.2_chunk_0", "0007.2_chunk_1"],
            expected_answer="甲方保留所有预先存在的知识产权，合作产生的新知识产权双方共有",
            category="factual",
            difficulty="medium"
        ),
        BenchmarkQuery(
            query_id="legal_003",
            query_text="发生争议时的解决机制是什么？",
            document_id="service_agreement",
            ground_truth_chunks=["0015.1_chunk_0"],
            expected_answer="首先通过友好协商，协商不成提交仲裁",
            category="procedural",
            difficulty="medium"
        ),
    ]
    
    documents = [
        {
            "document_id": "service_agreement",
            "title": "Service Agreement",
            "path": "data/benchmark/legal/service_agreement.pdf",
            "category": "legal",
            "metadata": {
                "contract_type": "service",
                "pages": 45
            }
        }
    ]
    
    return BenchmarkDataset(
        name="Legal Benchmark",
        description="法律文档问答评测集，关注条款和程序",
        documents=documents,
        queries=queries
    )


def save_benchmark(dataset: BenchmarkDataset, output_dir: Path):
    """
    保存评测数据集
    
    Args:
        dataset: 评测数据集
        output_dir: 输出目录
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存为JSON
    output_file = output_dir / f"{dataset.name.replace(' ', '_').lower()}.json"
    
    data = {
        "name": dataset.name,
        "description": dataset.description,
        "documents": dataset.documents,
        "queries": [asdict(q) for q in dataset.queries]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved benchmark to: {output_file}")
    print(f"  Documents: {len(dataset.documents)}")
    print(f"  Queries: {len(dataset.queries)}")


def create_readme(output_dir: Path):
    """创建数据集README"""
    
    readme_content = """# 评测数据集

本目录包含用于评测RAG系统的标准数据集。

## 数据集列表

### 1. Finance Benchmark (金融文档)
- **文件**: `finance_benchmark.json`
- **文档**: 年度报告、财务分析
- **查询数**: 5个
- **难度分布**: Easy (2), Medium (2), Hard (1)

### 2. Technical Benchmark (技术文档)
- **文件**: `technical_benchmark.json`
- **文档**: 用户手册、API文档
- **查询数**: 4个
- **难度分布**: Easy (2), Medium (1), Hard (1)

### 3. Legal Benchmark (法律文档)
- **文件**: `legal_benchmark.json`
- **文档**: 合同协议
- **查询数**: 3个
- **难度分布**: Easy (1), Medium (2)

## 数据格式

每个数据集JSON包含以下字段：

```json
{
  "name": "数据集名称",
  "description": "数据集描述",
  "documents": [
    {
      "document_id": "文档ID",
      "title": "文档标题",
      "path": "文档路径",
      "category": "文档类别",
      "metadata": {}
    }
  ],
  "queries": [
    {
      "query_id": "查询ID",
      "query_text": "查询文本",
      "document_id": "所属文档ID",
      "ground_truth_chunks": ["chunk_001", "chunk_002"],
      "expected_answer": "期望答案",
      "category": "factual/conceptual/procedural/mixed",
      "difficulty": "easy/medium/hard"
    }
  ]
}
```

## 评测指标

- **Recall@K**: 前K个结果中正确chunks的比例
- **MRR**: 第一个正确结果的倒数排名
- **NDCG**: 归一化折损累积增益

## 使用方法

```python
from benchmark_utils import load_benchmark, evaluate_system

# 加载数据集
dataset = load_benchmark("data/benchmark/finance_benchmark.json")

# 运行评测
results = evaluate_system(
    search_engine=your_search_engine,
    dataset=dataset,
    top_k=10
)

print(f"Recall@10: {results['recall_at_10']:.3f}")
print(f"MRR: {results['mrr']:.3f}")
```

## 添加新数据集

1. 在 `benchmark_generator.py` 中创建新函数
2. 定义文档和查询
3. 运行脚本生成JSON文件
"""
    
    readme_file = output_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"Created README: {readme_file}")


def main():
    """主函数"""
    
    # 输出目录
    output_dir = Path("data/benchmark")
    
    # 创建数据集
    print("Creating benchmark datasets...")
    
    datasets = [
        create_finance_benchmark(),
        create_technical_benchmark(),
        create_legal_benchmark()
    ]
    
    # 保存数据集
    for dataset in datasets:
        save_benchmark(dataset, output_dir)
    
    # 创建README
    create_readme(output_dir)
    
    print("\n✅ All benchmark datasets created successfully!")
    print(f"Total queries: {sum(len(d.queries) for d in datasets)}")


if __name__ == "__main__":
    main()
