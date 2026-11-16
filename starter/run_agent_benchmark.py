"""Run Agentic RAG benchmark on dev/test split and record full execution traces."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add starter directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agentic import run_agent
from baseline import TfidfIndex
from dense_retriever import PgVectorRetriever
from retrieval_benchmark import HybridRetriever
from controller import GeminiController


def main():
    parser = argparse.ArgumentParser(description="Chạy Agentic RAG benchmark và lưu trace")
    parser.add_argument("--benchmark", default="data/benchmark_24.json", type=Path)
    parser.add_argument("--split", default="test", choices=["dev", "test"])
    parser.add_argument("--retriever", default="hybrid", choices=["dense", "hybrid"])
    parser.add_argument("--output", default="starter/results/test-hybrid-agent", type=Path)
    parser.add_argument("--max_searches", default=3, type=int)
    parser.add_argument("--top_k", default=3, type=int)
    parser.add_argument("--budget", default=2500, type=int)
    args = parser.parse_args()

    print(f"=== BẮT ĐẦU CHẠY AGENTIC RAG (Split: {args.split.upper()} | Retriever: {args.retriever.upper()}) ===")
    
    with open(args.benchmark, "r", encoding="utf-8") as f:
        cases = json.load(f)

    selected = [c for c in cases if c.get("split") == args.split]
    if not selected:
        sys.exit(f"Không có câu hỏi nào cho split {args.split}")

    print(f"Số lượng câu hỏi: {len(selected)}")
    
    dense_retriever = PgVectorRetriever(strategy="strategy_b")
    if args.retriever == "hybrid":
        chunks_file = Path("starter/data/converted/chunks.json")
        chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
        tfidf_index = TfidfIndex(chunks)
        retriever = HybridRetriever(dense_retriever, tfidf_index, k=60)
        retriever_name = "HybridRetriever (Dense + TF-IDF with RRF)"
    else:
        retriever = dense_retriever
        retriever_name = "PgVectorRetriever (Dense)"

    controller = GeminiController()

    traces = []
    answered_count = 0
    abstain_count = 0

    args.output.mkdir(parents=True, exist_ok=True)

    t_start_all = time.time()
    for idx, c in enumerate(selected, start=1):
        cid = c["id"]
        q = c["question"]
        is_ans = c.get("answerable", True)
        filters = c.get("filter")

        print(f"\n[{idx}/{len(selected)}] Đang xử lý câu hỏi: {cid} (answerable: {is_ans})")
        print(f"   Q: {q}")
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

            print(f"   -> Status: {status} | Thời gian: {elapsed:.2f}s")
            print(f"   -> Answer: {res['answer']}")
            print(f"   -> Citations: {res['citations']}")

            traces.append({
                "query_id": cid,
                "split": args.split,
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
            print(f"   ❌ Lỗi khi xử lý {cid}: {e}")
            traces.append({
                "query_id": cid,
                "split": args.split,
                "question": q,
                "answerable": is_ans,
                "status": "error",
                "error": str(e),
                "events": [],
                "citations": [],
            })

    total_time = time.time() - t_start_all

    summary = {
        "split": args.split,
        "total_questions": len(selected),
        "answered": answered_count,
        "abstain": abstain_count,
        "total_time_seconds": total_time,
        "avg_time_per_query": total_time / len(selected) if selected else 0,
        "config": {
            "retriever": retriever_name,
            "embedding_model": "gemini-embedding-001",
            "controller_model": "gemini-flash-lite-latest",
            "max_searches": args.max_searches,
            "top_k": args.top_k,
            "budget": args.budget,
        }
    }

    # Save cases for agent_metrics.py
    cases_for_split = [
        {
            "id": c["id"],
            "split": c["split"],
            "answerable": c["answerable"],
        }
        for c in selected
    ]
    (args.output / "cases.json").write_text(
        json.dumps(cases_for_split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "traces.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("\n=== HOÀN THÀNH CHẠY AGENT ===")
    print(f"Tổng số câu: {len(selected)} (Trả lời: {answered_count}, Từ chối: {abstain_count})")
    print(f"Đã lưu kết quả tại: {args.output}")


if __name__ == "__main__":
    main()
