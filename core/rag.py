"""
RAG 简历匹配引擎
- 简历切块 → TF-IDF 向量化 → 余弦相似度检索 → LLM 精准分析
- 零外部依赖：用 Python 标准库 + 自实现 TF-IDF
"""

import re
import math
from collections import Counter
from typing import List, Tuple


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
    """将文本按语义边界切块"""
    # 按段落/换行/句号切分
    segments = re.split(r'\n{2,}|(?<=[。！？\.\!\?])\s*', text)
    chunks = []
    current = ""

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if len(current) + len(seg) <= chunk_size:
            current += ("\n" if current else "") + seg
        else:
            if current:
                chunks.append(current)
            current = seg

    if current:
        chunks.append(current)

    # 如果块太少（简历很短），用滑动窗口补充
    if len(chunks) <= 2 and len(text) > chunk_size:
        chunks = []
        words = text
        for i in range(0, len(words), chunk_size - overlap):
            chunk = words[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())

    return chunks


def _tokenize(text: str) -> List[str]:
    """中英文混合分词（简单实现：英文按空格，中文按字/词）"""
    tokens = []
    # 英文单词
    tokens.extend(re.findall(r'[a-zA-Z][a-zA-Z0-9+#]{1,}', text))
    # 中文2-4字词（简单 n-gram）
    chinese = re.findall(r'[一-鿿]+', text)
    for seg in chinese:
        for n in [2, 3, 4]:
            for i in range(len(seg) - n + 1):
                tokens.append(seg[i:i+n])
        # 也加单字
        tokens.extend(list(seg))
    return [t.lower() for t in tokens]


class TFIDFIndex:
    """轻量 TF-IDF 向量检索"""

    def __init__(self):
        self.docs: List[str] = []
        self.tf: List[Counter] = []
        self.idf: dict = {}
        self.vocab: set = set()

    def add_documents(self, docs: List[str]):
        self.docs = docs
        self.tf = []
        all_tokens = []

        for doc in docs:
            tokens = _tokenize(doc)
            tf = Counter(tokens)
            total = len(tokens) or 1
            self.tf.append({t: c / total for t, c in tf.items()})
            all_tokens.append(set(tokens))
            self.vocab.update(tokens)

        N = len(docs) or 1
        for token in self.vocab:
            df = sum(1 for doc_tokens in all_tokens if token in doc_tokens)
            self.idf[token] = math.log((N + 1) / (df + 1)) + 1

    def search(self, query: str, top_k: int = 3) -> List[Tuple[int, float, str]]:
        """检索最相关的 top_k 个文档块，返回 (index, score, text)"""
        q_tokens = _tokenize(query)
        q_tf = Counter(q_tokens)
        q_total = len(q_tokens) or 1
        q_vec = {t: (c / q_total) * self.idf.get(t, 1) for t, c in q_tf.items()}

        scores = []
        for i, doc_tf in enumerate(self.tf):
            doc_vec = {t: tf * self.idf.get(t, 1) for t, tf in doc_tf.items()}
            score = self._cosine(q_vec, doc_vec)
            scores.append((i, score, self.docs[i]))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    @staticmethod
    def _cosine(a: dict, b: dict) -> float:
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        dot = sum(a[k] * b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def rag_match(resume_text: str, job_title: str, job_company: str) -> dict:
    """
    RAG 增强的简历匹配：
    1. 简历切块 → TF-IDF 索引
    2. 用岗位标题检索最相关的简历段落
    3. 只把相关段落 + 岗位信息送 LLM 分析
    """
    from core.llm import _call_llm
    from core.config import get_llm_config

    if not get_llm_config()["api_key"]:
        return {"error": "未配置 LLM API"}

    if not resume_text.strip():
        return {"error": "简历内容为空"}

    # Step 1: 切块 + 建索引
    chunks = chunk_text(resume_text)
    index = TFIDFIndex()
    index.add_documents(chunks)

    # Step 2: 检索最相关段落
    query = f"{job_company} {job_title}"
    results = index.search(query, top_k=3)
    relevant_text = "\n\n".join(f"[相关段落 {i+1}] (相似度: {score:.2f})\n{text}" for i, (_, score, text) in enumerate(results))

    # Step 3: LLM 精准分析
    prompt = f"""基于简历中与目标岗位最相关的段落，分析匹配情况。

## 目标岗位
公司：{job_company}
岗位：{job_title}

## 简历相关段落（已通过 RAG 检索）
{relevant_text}

请输出：
1. **匹配度**：高/中/低，附理由
2. **命中技能**（3-5个）
3. **缺失技能**（2-3个）
4. **简历优化建议**（2-3条，针对此岗位）
5. **面试准备方向**（2-3个技术点）"""

    analysis = _call_llm(prompt, system="你是资深技术面试官，基于RAG检索结果精准分析候选人匹配度。")

    return {
        "analysis": analysis,
        "job": f"{job_company} - {job_title}",
        "chunks_total": len(chunks),
        "chunks_used": len(results),
        "retrieval": [{"score": f"{s:.2f}", "preview": t[:80]} for _, s, t in results],
    }
