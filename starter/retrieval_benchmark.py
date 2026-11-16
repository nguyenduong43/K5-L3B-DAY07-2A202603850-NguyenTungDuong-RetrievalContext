"""Benchmark and compare multiple retrieval methods on the dev split.

Methods:
1. Lexical Retrieval (TF-IDF)
2. Dense Retrieval (PostgreSQL pgvector + gemini-embedding-001)
3. Hybrid Retrieval (Dense + TF-IDF with Reciprocal Rank Fusion - RRF)
"""
import json
import math
import os
import sys
import time
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv

# Ensure starter is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline import tokenize, hit, pack_context, TfidfIndex
from dense_retriever import PgVectorRetriever

load_dotenv()


class HybridRetriever:
    """Combines Dense Retrieval and Lexical TF-IDF using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, dense_retriever: PgVectorRetriever, tfidf_index: TfidfIndex, k: int = 60) -> None:
        self.dense = dense_retriever
        self.tfidf = tfidf_index
        self.k = k

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 3, candidate_k: int = 10) -> list[dict]:
        # 1. Get candidates from Dense
        dense_results = self.dense.search(query, filters=filters, top_k=candidate_k)

        # 2. Get candidates from TF-IDF
        tfidf_results = self.tfidf.search(query, top_k=candidate_k)
        if filters:
            if "section" in filters:
                tfidf_results = [c for c in tfidf_results if c.get("metadata", {}).get("section") == filters["section"] or c.get("section") == filters["section"]]
            if "page" in filters:
                tfidf_results = [c for c in tfidf_results if c.get("page") == filters["page"]]

        # 3. Calculate RRF score for all unique chunks
        all_chunks: dict[str, dict] = {}
        rrf_scores: dict[str, float] = {}

        # Dense ranks
        for rank, c in enumerate(dense_results, start=1):
            cid = c["id"]
            all_chunks[cid] = c
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (self.k + rank)

        # TF-IDF ranks
        for rank, c in enumerate(tfidf_results, start=1):
            cid = c["id"]
            if cid not in all_chunks:
                all_chunks[cid] = c
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (self.k + rank)

        # Sort by RRF score descending
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
        final_results = []
        for cid in sorted_ids[:top_k]:
            c = dict(all_chunks[cid])
            c["score"] = rrf_scores[cid]
            c["strategy"] = "hybrid_rrf"
            final_results.append(c)

        return final_results


def evaluate_retriever(name: str, search_fn, questions: list[dict], budget: int = 2500) -> dict:
    traces = []
    t_start = time.perf_counter()

    for q in questions:
        q_start = time.perf_counter()
        results = search_fn(q["question"], filters=q.get("filter"), top_k=3)
        context, ids = pack_context(results, budget=budget)
        elapsed_ms = (time.perf_counter() - q_start) * 1000

        marked = [{**c, "hit": hit(c, q["gold"])} for c in results]
        h1 = bool(marked and marked[0]["hit"])
        h3 = any(c["hit"] for c in marked)
        ctx_hit = any(c["hit"] and c["id"] in ids for c in marked)

        traces.append({
            "query_id": q["id"],
            "question": q["question"],
            "gold": q["gold"],
            "results": marked,
            "context_ids": ids,
            "hit1": h1,
            "hit3": h3,
            "context_hit": ctx_hit,
            "elapsed_ms": elapsed_ms,
        })

    total_time = time.perf_counter() - t_start
    n = len(questions)
    hit1_cnt = sum(1 for t in traces if t["hit1"])
    hit3_cnt = sum(1 for t in traces if t["hit3"])
    ctx_cnt = sum(1 for t in traces if t["context_hit"])

    return {
        "method": name,
        "n": n,
        "hit1": hit1_cnt,
        "hit1_rate": hit1_cnt / n if n else 0,
        "hit3": hit3_cnt,
        "hit3_rate": hit3_cnt / n if n else 0,
        "context_evidence_rate": ctx_cnt / n if n else 0,
        "context_evidence_count": ctx_cnt,
        "budget_chars": budget,
        "total_time_seconds": total_time,
        "median_latency_ms": sorted([t["elapsed_ms"] for t in traces])[n // 2] if n else 0,
        "traces": traces,
    }


def main():
    print("=================================================================")
    print("       SO SÁNH CÁC PHƯƠNG PHÁP RETRIEVAL TRÊN TẬP DEV (MỐC 3)    ")
    print("=================================================================\n")

    chunks_file = Path("starter/data/converted/chunks.json")
    questions_file = Path("starter/data/converted/questions.json")

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    with open(questions_file, "r", encoding="utf-8") as f:
        questions = [q for q in json.load(f) if q.get("split") == "dev"]

    print(f"Số lượng chunks: {len(chunks)}")
    print(f"Số câu hỏi dev có đáp án: {len(questions)}\n")

    # 1. Khởi tạo các Retriever
    print("Khởi tạo index và kết nối:")
    tfidf_index = TfidfIndex(chunks)
    dense_retriever = PgVectorRetriever(strategy="strategy_b")
    hybrid_retriever = HybridRetriever(dense_retriever, tfidf_index, k=60)

    configs = [
        # Baseline: TF-IDF với budget nhỏ 800
        ("Baseline (TF-IDF, budget=800)", lambda q, filters, top_k: tfidf_index.search(q, top_k=top_k), 800),
        # Cải thiện 1: TF-IDF với budget 2500 (chữa lỗi tràn context)
        ("TF-IDF (budget=2500)", lambda q, filters, top_k: tfidf_index.search(q, top_k=top_k), 2500),
        # Phương pháp 2: Dense Retrieval (pgvector)
        ("Dense Retrieval (pgvector, budget=2500)", lambda q, filters, top_k: dense_retriever.search(q, filters=filters, top_k=top_k), 2500),
        # Phương pháp 3: Hybrid Retrieval (Dense + TF-IDF với RRF)
        ("Hybrid Retrieval (RRF, budget=2500)", lambda q, filters, top_k: hybrid_retriever.search(q, filters=filters, top_k=top_k), 2500),
    ]

    all_results = []
    output_dir = Path("starter/results/retrieval_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, search_fn, budget in configs:
        print(f"🔄 Đang đánh giá: {name}...")
        res = evaluate_retriever(name, search_fn, questions, budget=budget)
        all_results.append(res)
        print(f"   -> Hit@1: {res['hit1']}/{res['n']} ({res['hit1_rate']*100:.1f}%) | "
              f"Hit@3: {res['hit3']}/{res['n']} ({res['hit3_rate']*100:.1f}%) | "
              f"Context Rate: {res['context_evidence_count']}/{res['n']} ({res['context_evidence_rate']*100:.1f}%) | "
              f"Latency: {res['median_latency_ms']:.2f}ms")

    # Lưu kết quả so sánh
    summary_data = [
        {k: v for k, v in r.items() if k != "traces"}
        for r in all_results
    ]
    (output_dir / "summary.json").write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "all_traces.json").write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=================================================================")
    print("                    BẢNG TỔNG HỢP SO SÁNH                        ")
    print("=================================================================")
    print(f"{'Cấu hình / Phương pháp':<40} | {'Hit@1':<8} | {'Hit@3':<8} | {'Context Rate':<12} | {'Latency':<10}")
    print("-" * 85)
    for r in all_results:
        print(f"{r['method']:<40} | {r['hit1']}/{r['n']:<6} | {r['hit3']}/{r['n']:<6} | {r['context_evidence_count']}/{r['n']:<10} | {r['median_latency_ms']:.1f} ms")
    print("=================================================================\n")


if __name__ == "__main__":
    main()
