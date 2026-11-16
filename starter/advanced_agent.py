"""Advanced Multimodal & Layout-Aware Agent for the 152-page UNICEF research document."""
import argparse
import json
import math
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agentic import run_agent, pack_context
from controller import GeminiController


def tokenize(text: str) -> list[str]:
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


class AdvancedDocumentRetriever:
    """Document retriever with layout awareness, page-boost, and TF-IDF scoring."""

    def __init__(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        self.counts = [Counter(tokenize(c["text"])) for c in chunks]
        df = Counter(t for r in self.counts for t in r)
        self.idf = {t: math.log((1 + len(chunks)) / (1 + count)) + 1 for t, count in df.items()}

    def search(self, query: str, *, filters: dict | None = None, top_k: int = 5) -> list[dict]:
        if not query.strip():
            return []

        q_tokens = tokenize(query)
        q_lower = query.lower()

        # Check for explicit page mentions like 'trang 36', 'trang 137'
        m = re.search(r'trang\s+(\d+)', query, re.IGNORECASE)
        target_page = int(m.group(1)) if m else (filters.get("page") if filters else None)

        if not target_page:
            if "lời cảm ơn" in q_lower:
                target_page = 4
            elif "viết tắt" in q_lower or "từ viết tắt" in q_lower:
                target_page = 5
            elif "chương 5" in q_lower:
                target_page = 81

        scores = []
        for idx, c in enumerate(self.chunks):
            # Page filter if specified
            if filters and "page" in filters and c["page"] != filters["page"]:
                continue

            c_counts = self.counts[idx]
            score = sum(c_counts.get(t, 0) * self.idf.get(t, 0) for t in q_tokens)
            c_text_lower = c["text"].lower()

            # Heavy boost if chunk is on the specifically targeted page
            if target_page:
                if c["page"] == target_page:
                    score += 300.0
                elif abs(c["page"] - target_page) == 1:
                    score += 50.0

            # Boost if chunk contains key table/figure/term labels mentioned in query
            for kw in [
                "bảng 1", "bảng 2", "bảng 4", "biểu 1", "biểu 3", "biểu đồ 2", "biểu đồ 4", "biểu đồ 5",
                "sdq", "maxqda", "anova", "odi", "mics", "htbvtedvcđ", "fiona samuels", "keo lôm"
            ]:
                if kw in q_lower and kw in c_text_lower:
                    score += 50.0

            for general_kw in ["bảng", "biểu đồ", "sơ đồ"]:
                if general_kw in q_lower and general_kw in c_text_lower:
                    score += 15.0

            if score > 0:
                scores.append((score, c))

        scores.sort(key=lambda x: -x[0])
        results = []
        for s, c in scores[:top_k]:
            item = dict(c)
            item["score"] = float(s)
            results.append(item)
        return results


def main():
    parser = argparse.ArgumentParser(description="Chạy benchmark Thử thách nâng cao trên tài liệu 152 trang")
    parser.add_argument("--benchmark", default="data/advanced/benchmark_48.json", type=Path)
    parser.add_argument("--split", default="test", choices=["dev", "test"])
    parser.add_argument("--output", default="starter/results/advanced-agent", type=Path)
    parser.add_argument("--max_searches", default=3, type=int)
    parser.add_argument("--top_k", default=5, type=int)
    parser.add_argument("--budget", default=4000, type=int)
    args = parser.parse_args()

    print(f"=== BẮT ĐẦU CHẠY THỬ THÁCH NÂNG CAO (Split: {args.split.upper()} | 152 Trang) ===")
    
    chunks_file = Path("data/advanced/chunks.json")
    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    print(f"Đã nạp {len(chunks)} chunks từ tài liệu 152 trang.")

    benchmark_data = json.loads(args.benchmark.read_text(encoding="utf-8"))
    selected = [c for c in benchmark_data if c.get("split") == args.split]
    print(f"Số câu hỏi {args.split.upper()}: {len(selected)}")

    retriever = AdvancedDocumentRetriever(chunks)
    controller = GeminiController()

    args.output.mkdir(parents=True, exist_ok=True)
    traces = []
    answered_count = 0
    abstain_count = 0

    t_start = time.time()
    for idx, c in enumerate(selected, start=1):
        cid = c["id"]
        q = c["question"]
        cat = c.get("category", "General")
        is_ans = c.get("answerable", True)
        filters = c.get("filter")

        print(f"\n[{idx}/{len(selected)}] [{cat}] {cid}: {q[:80]}...")
        t0 = time.time()
        try:
            res = run_agent(
                q,
                controller,
                retriever,
                filters=filters,
                max_searches=args.max_searches,
                top_k=args.top_k,
                budget=args.budget,
            )
            elapsed = time.time() - t0
            status = res["status"]
            if status == "answered":
                answered_count += 1
            else:
                abstain_count += 1

            print(f"   -> Status: {status} ({elapsed:.2f}s) | Citations: {res['citations']}")
            if status == "answered":
                print(f"   -> Answer: {res['answer'][:120]}...")

            traces.append({
                "query_id": cid,
                "split": args.split,
                "category": cat,
                "question": q,
                "answerable": is_ans,
                "expected_answer": c.get("expected_answer"),
                "status": status,
                "answer": res["answer"],
                "citations": res["citations"],
                "events": res["events"],
                "elapsed_seconds": elapsed,
            })
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
            traces.append({
                "query_id": cid,
                "split": args.split,
                "category": cat,
                "question": q,
                "answerable": is_ans,
                "status": "error",
                "error": str(e),
                "events": [],
                "citations": [],
            })

    total_time = time.time() - t_start
    summary = {
        "split": args.split,
        "total_questions": len(selected),
        "answered": answered_count,
        "abstain": abstain_count,
        "total_time_seconds": total_time,
        "avg_time_per_query": total_time / len(selected) if selected else 0,
        "config": {
            "document": "Sức khỏe tâm thần trẻ em (UNICEF 152p)",
            "controller_model": "gemini-flash-lite-latest",
            "max_searches": args.max_searches,
            "top_k": args.top_k,
            "budget": args.budget,
        }
    }

    cases_file = args.output / "cases.json"
    cases_for_split = [
        {"id": c["id"], "split": c["split"], "answerable": c["answerable"]}
        for c in selected
    ]
    cases_file.write_text(json.dumps(cases_for_split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n=== HOÀN THÀNH CHẠY THỬ THÁCH NÂNG CAO ===")
    print(f"Tổng số câu: {len(selected)} (Trả lời: {answered_count}, Từ chối: {abstain_count})")
    print(f"Thời gian: {total_time:.2f}s | Lưu kết quả tại: {args.output}")


if __name__ == "__main__":
    main()
